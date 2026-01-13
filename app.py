import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Swing Lab | Dr. Cruz", page_icon="🩸", layout="wide")
st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    div.stButton > button:first-child {
        background-color: #D80000; color: white; border-radius: 10px; border: none; font-weight: bold; width: 100%;
    }
    .metric-card { background-color: #f0f2f6; padding: 10px; border-radius: 10px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAR SESSION STATE ---
if 'historial_operaciones' not in st.session_state:
    st.session_state['historial_operaciones'] = []
if 'auto_refresh' not in st.session_state:
    st.session_state['auto_refresh'] = False

# --- FUNCIONES ---
def calcular_stop_loss_soporte_20d(ticker_obj, precio_actual):
    """Calcula Stop Loss basado en soporte de 20 días"""
    try:
        hist = ticker_obj.history(period="1mo")
        if hist.empty:
            return None, None, None
        
        minimo_20d = hist['Low'].min()
        stop_loss = minimo_20d * 0.98
        dias_datos = len(hist)
        fecha_minimo = hist['Low'].idxmin().strftime('%Y-%m-%d')
        
        return round(stop_loss, 2), round(minimo_20d, 2), {
            'dias': dias_datos,
            'fecha_minimo': fecha_minimo
        }
    except Exception as e:
        return None, None, {'error': str(e)}

def obtener_datos_fundamentales(ticker):
    """Obtiene datos fundamentales de Yahoo Finance (alternativa gratuita a TipRanks)"""
    try:
        stock = yf.Ticker(ticker)
        
        # Obtener precio actual desde history (más confiable)
        hist = stock.history(period="1d")
        if hist.empty:
            return None
        precio_actual = hist['Close'].iloc[-1]
        
        # Intentar obtener info (puede fallar)
        try:
            info = stock.info
        except:
            info = {}
        
        # Recomendaciones de analistas
        recomendacion = info.get('recommendationKey', 'hold')
        num_analistas = info.get('numberOfAnalystOpinions', 0)
        
        # Precio objetivo
        precio_objetivo = info.get('targetMeanPrice', None)
        
        # Si no hay precio objetivo, intentar calcular desde otros datos
        if not precio_objetivo:
            target_high = info.get('targetHighPrice', None)
            target_low = info.get('targetLowPrice', None)
            if target_high and target_low:
                precio_objetivo = (target_high + target_low) / 2
        
        # Calcular upside
        upside = None
        if precio_objetivo and precio_actual:
            upside = ((precio_objetivo - precio_actual) / precio_actual) * 100
        
        # Mapear recomendación a puntuación tipo Smart Score
        score_map = {
            'strong_buy': 10,
            'buy': 8,
            'hold': 5,
            'underperform': 3,
            'sell': 2,
            'strong_sell': 1
        }
        smart_score_aprox = score_map.get(recomendacion, 5)
        
        return {
            'recomendacion': recomendacion.replace('_', ' ').title() if recomendacion else 'Hold',
            'num_analistas': num_analistas if num_analistas else 'N/A',
            'precio_objetivo': round(precio_objetivo, 2) if precio_objetivo else None,
            'upside': round(upside, 2) if upside else 0,
            'smart_score_aprox': smart_score_aprox
        }
    except Exception as e:
        # Si falla completamente, retornar datos por defecto
        return {
            'recomendacion': 'Hold',
            'num_analistas': 'N/A',
            'precio_objetivo': None,
            'upside': 0,
            'smart_score_aprox': 5
        }

def crear_grafico_niveles(ticker, precio_actual, entrada, stop_loss, tp1, tp2):
    """Crea gráfico visual con niveles de Stop y Take Profit"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="3mo")
        
        fig = go.Figure()
        
        # Candlestick chart
        fig.add_trace(go.Candlestick(
            x=hist.index,
            open=hist['Open'],
            high=hist['High'],
            low=hist['Low'],
            close=hist['Close'],
            name='Precio'
        ))
        
        # Precio de entrada
        fig.add_hline(y=entrada, line_dash="dash", line_color="blue", line_width=2,
                     annotation_text=f"Entrada: ${entrada:.2f}", 
                     annotation_position="right")
        
        # Stop Loss
        fig.add_hline(y=stop_loss, line_dash="dash", line_color="red", line_width=2,
                     annotation_text=f"Stop Loss: ${stop_loss:.2f}", 
                     annotation_position="right")
        
        # Take Profits
        fig.add_hline(y=tp1, line_dash="dash", line_color="green", line_width=2,
                     annotation_text=f"TP 1:2: ${tp1:.2f}", 
                     annotation_position="right")
        
        fig.add_hline(y=tp2, line_dash="dash", line_color="darkgreen", line_width=2,
                     annotation_text=f"TP 1:3: ${tp2:.2f}", 
                     annotation_position="right")
        
        # Zonas sombreadas
        fig.add_hrect(y0=stop_loss, y1=entrada, fillcolor="red", opacity=0.1, 
                     line_width=0)
        
        fig.add_hrect(y0=entrada, y1=tp2, fillcolor="green", opacity=0.1, 
                     line_width=0)
        
        fig.update_layout(
            title=f"Análisis Técnico: {ticker}",
            xaxis_title="Fecha",
            yaxis_title="Precio ($)",
            hovermode='x unified',
            height=500,
            showlegend=False,
            xaxis_rangeslider_visible=False
        )
        
        return fig
    except:
        return None

def agregar_a_historial(ticker, acciones, entrada, stop, tp1, tp2, inversion, riesgo, 
                        smart_score, upside, recomendacion):
    """Agrega operación al historial"""
    operacion = {
        'fecha': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'ticker': ticker,
        'acciones': round(acciones, 2),
        'entrada': round(entrada, 2),
        'stop_loss': round(stop, 2),
        'tp_1_2': round(tp1, 2),
        'tp_1_3': round(tp2, 2),
        'inversion': round(inversion, 2),
        'riesgo': round(riesgo, 2),
        'smart_score': smart_score,
        'upside': upside,
        'recomendacion': recomendacion,
        'status': 'Activa',
        'precio_actual': round(entrada, 2),
        'pl_actual': 0.0
    }
    st.session_state['historial_operaciones'].insert(0, operacion)

def actualizar_precios_historial():
    """Actualiza los precios de operaciones activas"""
    for op in st.session_state['historial_operaciones']:
        if op['status'] == 'Activa':
            try:
                stock = yf.Ticker(op['ticker'])
                precio_actual = stock.history(period="1d")['Close'].iloc[-1]
                op['precio_actual'] = round(precio_actual, 2)
                
                # Calcular P/L
                pl = (precio_actual - op['entrada']) * op['acciones']
                op['pl_actual'] = round(pl, 2)
                
                # Verificar si tocó Stop Loss o Take Profit
                if precio_actual <= op['stop_loss']:
                    op['status'] = 'Cerrada (Stop Loss)'
                    op['pl_actual'] = -op['riesgo']
                elif precio_actual >= op['tp_1_2']:
                    op['status'] = 'Cerrada (TP 1:2)'
                    op['pl_actual'] = op['riesgo'] * 2
            except:
                pass

def calcular_metricas_performance():
    """Calcula métricas de performance del historial"""
    if not st.session_state['historial_operaciones']:
        return None
    
    df = pd.DataFrame(st.session_state['historial_operaciones'])
    
    total_ops = len(df)
    activas = len(df[df['status'] == 'Activa'])
    cerradas = total_ops - activas
    
    if cerradas > 0:
        df_cerradas = df[df['status'].str.contains('Cerrada')]
        ganadoras = len(df_cerradas[df_cerradas['pl_actual'] > 0])
        perdedoras = len(df_cerradas[df_cerradas['pl_actual'] < 0])
        win_rate = (ganadoras / cerradas * 100) if cerradas > 0 else 0
        
        total_ganancia = df_cerradas[df_cerradas['pl_actual'] > 0]['pl_actual'].sum()
        total_perdida = abs(df_cerradas[df_cerradas['pl_actual'] < 0]['pl_actual'].sum())
        profit_factor = (total_ganancia / total_perdida) if total_perdida > 0 else 0
        
        pl_total = df_cerradas['pl_actual'].sum()
    else:
        ganadoras = perdedoras = win_rate = profit_factor = pl_total = 0
    
    return {
        'total_ops': total_ops,
        'activas': activas,
        'cerradas': cerradas,
        'ganadoras': ganadoras,
        'perdedoras': perdedoras,
        'win_rate': round(win_rate, 1),
        'profit_factor': round(profit_factor, 2),
        'pl_total': round(pl_total, 2)
    }

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    
    capital = st.number_input("💰 Capital Total ($)", value=1000.0, step=100.0, min_value=100.0)
    
    st.write("---")
    st.subheader("🛡️ Gestión de Riesgo")
    riesgo_pct = st.slider("% de Cuenta en Riesgo", 0.5, 5.0, 2.0, 0.1)
    dinero_en_riesgo = capital * (riesgo_pct / 100)
    st.metric("Riesgo Máximo", f"${dinero_en_riesgo:.2f}")
    
    st.write("---")
    st.subheader("🔄 Auto-actualización")
    auto_refresh = st.checkbox("Actualizar precios cada 5 min", value=False,
                              help="Actualiza automáticamente los precios de operaciones activas")
    
    if auto_refresh:
        st.info("🔄 Auto-actualización activada")
        # Trigger para auto-refresh
        if st.button("🔄 Actualizar Ahora"):
            with st.spinner("Actualizando precios..."):
                actualizar_precios_historial()
            st.success("✅ Precios actualizados")
            st.rerun()
    
    st.write("---")
    st.subheader("📊 Método Stop Loss")
    st.success("**Soporte 20 Días**\n\n✅ Mínimo 4 semanas\n✅ Colchón 2%\n✅ Ideal Swing Trading")
    
    ajuste_manual = st.checkbox("🔧 Ajuste manual del Stop", value=False)

# --- TABS PRINCIPALES ---
tab1, tab2, tab3 = st.tabs(["🩸 Nueva Operación", "📊 Historial", "📈 Dashboard"])

# ==================== TAB 1: NUEVA OPERACIÓN ====================
with tab1:
    st.title("🩸 Swing Lab | Análisis Completo")
    
    # --- BÚSQUEDA Y ANÁLISIS AUTOMÁTICO ---
    st.markdown("### 🔍 Análisis Automático")
    
    col_tick, col_btn = st.columns([3, 1])
    with col_tick:
        ticker = st.text_input("Símbolo (Ticker)", value="MSFT", max_chars=10).upper()
    
    analizar = False
    with col_btn:
        st.write("")
        st.write("")
        analizar = st.button("🔎 ANALIZAR TODO", use_container_width=True, type="primary")
    
    if analizar:
        try:
            with st.spinner(f"🔎 Analizando {ticker} (Fundamentales + Técnico)..."):
                stock = yf.Ticker(ticker)
                
                # 1. Obtener precio actual primero
                hist_actual = stock.history(period="1d")
                
                if hist_actual.empty:
                    st.error(f"❌ No se encontró el ticker '{ticker}'. Verifica que sea correcto.")
                else:
                    precio_actual = hist_actual['Close'].iloc[-1]
                    
                    # 2. Calcular Stop Loss técnico (siempre funciona)
                    stop_calculado, minimo_base, info = calcular_stop_loss_soporte_20d(stock, precio_actual)
                    
                    # 3. Obtener datos fundamentales (puede fallar, usamos valores por defecto)
                    datos_fundamentales = obtener_datos_fundamentales(ticker)
                    
                    if stop_calculado and minimo_base and datos_fundamentales:
                        # Guardar en session state
                        st.session_state['ticker_analizado'] = ticker
                        st.session_state['precio_entrada'] = float(round(precio_actual, 2))
                        st.session_state['stop_loss'] = float(stop_calculado)
                        st.session_state['info_tecnica'] = info
                        st.session_state['minimo_base'] = round(minimo_base, 2)
                        st.session_state['datos_fundamentales'] = datos_fundamentales
                        
                        st.success(f"✅ Análisis completo de {ticker}")
                        
                        # Mostrar resultados fundamentales
                        st.markdown("#### 📊 Análisis Fundamental (Yahoo Finance)")
                        col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                        
                        with col_f1:
                            score = datos_fundamentales['smart_score_aprox']
                            if score >= 8:
                                col_f1.metric("Smart Score", f"{score}/10", delta="Alta")
                            elif score >= 5:
                                col_f1.metric("Smart Score", f"{score}/10", delta="Media")
                            else:
                                col_f1.metric("Smart Score", f"{score}/10", delta="Baja")
                        
                        with col_f2:
                            recom = datos_fundamentales['recomendacion']
                            col_f2.metric("Recomendación", recom)
                        
                        with col_f3:
                            upside = datos_fundamentales['upside']
                            if upside and upside > 0:
                                col_f3.metric("Upside", f"{upside}%", delta="Positivo")
                            else:
                                col_f3.metric("Upside", "N/A")
                        
                        with col_f4:
                            num_analistas = datos_fundamentales['num_analistas']
                            col_f4.metric("Analistas", num_analistas)
                        
                        # Validación de filtros
                        pasa_filtro = (score >= 8 and 
                                      datos_fundamentales['recomendacion'] in ['Strong Buy', 'Buy'] and 
                                      (datos_fundamentales['upside'] or 0) >= 10)
                        
                        if pasa_filtro:
                            st.success("✅ **Acción aprobada por filtros fundamentales**")
                        else:
                            st.warning("⚠️ **La acción NO cumple todos los criterios** (puedes continuar de todos modos)")
                        
                        st.markdown("---")
                        
                        # Mostrar resultados técnicos
                        st.markdown("#### 📈 Análisis Técnico")
                        col_t1, col_t2, col_t3 = st.columns(3)
                        col_t1.metric("💵 Precio Actual", f"${precio_actual:.2f}")
                        col_t2.metric("📉 Soporte 20d", f"${minimo_base:.2f}")
                        col_t3.metric("🛑 Stop Loss", f"${stop_calculado:.2f}")
                        
                        st.caption(f"📅 Datos de {info['dias']} días | Mínimo: {info['fecha_minimo']}")
                        
                    else:
                        st.error(f"❌ Error al calcular el Stop Loss. Verifica el ticker.")
        except Exception as e:
            st.error(f"❌ Error al analizar {ticker}")
            st.caption(f"Detalles técnicos: {str(e)}")
            st.info("💡 **Sugerencias:**\n- Verifica que el ticker sea válido (ej: MSFT, AAPL, GOOGL)\n- Asegúrate de tener conexión a internet\n- Algunos tickers pueden no tener datos completos en Yahoo Finance")
    
    # --- PARÁMETROS Y CÁLCULO ---
    if 'ticker_analizado' in st.session_state:
        st.markdown("---")
        st.markdown("### 💊 Cálculo de Posición")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            entrada = st.number_input("💵 Precio Entrada ($)", 
                                     value=st.session_state['precio_entrada'],
                                     step=0.01, format="%.2f")
        
        with col2:
            if ajuste_manual:
                stop_loss = st.number_input("🛑 Stop Loss ($)", 
                                           value=st.session_state['stop_loss'],
                                           step=0.01, format="%.2f")
            else:
                stop_loss = st.session_state['stop_loss']
                st.metric("🛑 Stop Loss", f"${stop_loss:.2f}")
        
        with col3:
            riesgo_por_accion = entrada - stop_loss if entrada > stop_loss else 0
            st.metric("📏 Riesgo/Acción", f"${riesgo_por_accion:.2f}")
        
        if riesgo_por_accion > 0:
            pct_riesgo = (riesgo_por_accion / entrada) * 100
            if pct_riesgo > 10:
                st.warning(f"⚠️ Stop muy lejano: {pct_riesgo:.1f}%")
            elif pct_riesgo < 2:
                st.warning(f"⚠️ Stop muy cercano: {pct_riesgo:.1f}%")
            else:
                st.success(f"✅ Distancia óptima: {pct_riesgo:.1f}%")
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("💊 CALCULAR POSICIÓN", use_container_width=True, type="primary"):
            if entrada > 0 and stop_loss > 0 and stop_loss < entrada:
                riesgo_por_accion = entrada - stop_loss
                acciones_ideales = dinero_en_riesgo / riesgo_por_accion
                inversion_necesaria = acciones_ideales * entrada
                
                if inversion_necesaria > capital:
                    st.warning("⚠️ Capital Insuficiente")
                    acciones = capital / entrada
                    inversion = capital
                    riesgo_real = acciones * riesgo_por_accion
                    st.info(f"✂️ Ajustado a {acciones:.2f} acciones")
                else:
                    acciones = acciones_ideales
                    inversion = inversion_necesaria
                    riesgo_real = dinero_en_riesgo
                
                st.markdown("---")
                st.success(f"✅ **Orden para {st.session_state['ticker_analizado']}**")
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("🔢 Acciones", f"{acciones:.2f}")
                m2.metric("💰 Inversión", f"${inversion:.2f}")
                m3.metric("⚠️ Riesgo", f"${riesgo_real:.2f}")
                m4.metric("📊 % Capital", f"{(inversion/capital)*100:.0f}%")
                
                # Niveles
                tp_1_2 = entrada + (riesgo_por_accion * 2)
                tp_1_3 = entrada + (riesgo_por_accion * 3)
                ganancia_1_2 = acciones * (tp_1_2 - entrada)
                ganancia_1_3 = acciones * (tp_1_3 - entrada)
                
                st.markdown("### 🎯 Niveles de Salida")
                df_niveles = pd.DataFrame({
                    "Nivel": ["🛑 Stop Loss", "🎯 TP 1:2", "🚀 TP 1:3"],
                    "Precio": [f"${stop_loss:.2f}", f"${tp_1_2:.2f}", f"${tp_1_3:.2f}"],
                    "P/L": [f"-${riesgo_real:.2f}", f"+${ganancia_1_2:.2f}", f"+${ganancia_1_3:.2f}"],
                    "% Cuenta": [
                        f"-{(riesgo_real/capital)*100:.1f}%", 
                        f"+{(ganancia_1_2/capital)*100:.1f}%",
                        f"+{(ganancia_1_3/capital)*100:.1f}%"
                    ]
                })
                st.dataframe(df_niveles, use_container_width=True, hide_index=True)
                
                # Gráfico
                st.markdown("### 📈 Visualización de Niveles")
                fig = crear_grafico_niveles(st.session_state['ticker_analizado'], 
                                           st.session_state['precio_entrada'],
                                           entrada, stop_loss, tp_1_2, tp_1_3)
                if fig:
                    st.plotly_chart(fig, use_container_width=True)
                
                # Para Stock Master
                st.markdown("---")
                st.markdown("### 📱 Para Stock Master")
                col_sm1, col_sm2 = st.columns(2)
                with col_sm1:
                    st.code(f"""Symbol: {st.session_state['ticker_analizado']}
Shares: {acciones:.2f}
Price: ${entrada:.2f}
Stop Loss: ${stop_loss:.2f}""")
                with col_sm2:
                    st.code(f"""Take Profit 1: ${tp_1_2:.2f}
Take Profit 2: ${tp_1_3:.2f}
Risk/Reward: 1:2 y 1:3
Capital: {(inversion/capital)*100:.0f}%""")
                
                # Botón para guardar
                if st.button("💾 GUARDAR EN HISTORIAL", use_container_width=True):
                    datos_fund = st.session_state['datos_fundamentales']
                    agregar_a_historial(
                        st.session_state['ticker_analizado'], 
                        acciones, entrada, stop_loss, tp_1_2, tp_1_3,
                        inversion, riesgo_real, 
                        datos_fund['smart_score_aprox'],
                        datos_fund['upside'],
                        datos_fund['recomendacion']
                    )
                    st.success("✅ Operación guardada")
                    st.balloons()
                
                if riesgo_real <= dinero_en_riesgo * 1.15:
                    st.success("✅ Operación Aprobada")
                else:
                    st.error(f"❌ Riesgo excesivo")
            
            elif stop_loss >= entrada:
                st.error("❌ Stop Loss debe ser menor que entrada")
            else:
                st.warning("⚠️ Completa todos los campos")
    
    else:
        st.info("👆 Ingresa un ticker y presiona ANALIZAR TODO")

# ==================== TAB 2: HISTORIAL ====================
with tab2:
    st.title("📊 Historial de Operaciones")
    
    # Botón de actualización
    col_ref1, col_ref2 = st.columns([3, 1])
    with col_ref2:
        if st.button("🔄 Actualizar Precios", use_container_width=True):
            with st.spinner("Actualizando..."):
                actualizar_precios_historial()
            st.success("✅ Actualizado")
            st.rerun()
    
    if len(st.session_state['historial_operaciones']) == 0:
        st.info("📭 No hay operaciones registradas")
    else:
        metricas = calcular_metricas_performance()
        
        # Resumen
        col_h1, col_h2, col_h3, col_h4 = st.columns(4)
        col_h1.metric("Total Ops", metricas['total_ops'])
        col_h2.metric("Activas", metricas['activas'])
        col_h3.metric("Ganadoras", metricas['ganadoras'], 
                     delta=f"{metricas['win_rate']}% WR")
        col_h4.metric("P/L Total", f"${metricas['pl_total']:.2f}")
        
        st.markdown("---")
        
        # Tabla
        df_historial = pd.DataFrame(st.session_state['historial_operaciones'])
        
        # Colorear P/L
        def colorear_pl(val):
            color = 'green' if val > 0 else 'red' if val < 0 else 'gray'
            return f'color: {color}'
        
        styled_df = df_historial.style.applymap(colorear_pl, subset=['pl_actual'])
        
        st.dataframe(df_historial[[
            'fecha', 'ticker', 'acciones', 'entrada', 'precio_actual', 
            'stop_loss', 'tp_1_2', 'pl_actual', 'status'
        ]], use_container_width=True, hide_index=True)
        
        # Alertas
        st.markdown("### 🔔 Alertas de Precio")
        for op in st.session_state['historial_operaciones']:
            if op['status'] == 'Activa':
                dist_stop = ((op['precio_actual'] - op['stop_loss']) / op['entrada']) * 100
                dist_tp = ((op['tp_1_2'] - op['precio_actual']) / op['entrada']) * 100
                
                if dist_stop < 2:
                    st.error(f"🚨 **{op['ticker']}** muy cerca del Stop Loss ({dist_stop:.1f}%)")
                elif dist_tp < 2:
                    st.success(f"🎯 **{op['ticker']}** muy cerca del TP 1:2 ({dist_tp:.1f}%)")
        
        st.markdown("---")
        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if st.button("🗑️ Limpiar Historial", use_container_width=True):
                st.session_state['historial_operaciones'] = []
                st.rerun()
        
        with col_btn2:
            csv = df_historial.to_csv(index=False)
            st.download_button("📥 Descargar CSV", csv, "historial.csv", 
                             "text/csv", use_container_width=True)

# ==================== TAB 3: DASHBOARD ====================
with tab3:
    st.title("📈 Dashboard de Performance")
    
    if len(st.session_state['historial_operaciones']) == 0:
        st.info("📭 No hay datos para mostrar")
    else:
        metricas = calcular_metricas_performance()
        
        # Métricas principales
        col_d1, col_d2, col_d3, col_d4 = st.columns(4)
        col_d1.metric("Win Rate", f"{metricas['win_rate']}%")
        col_d2.metric("Profit Factor", metricas['profit_factor'])
        col_d3.metric("P/L Total", f"${metricas['pl_total']:.2f}")
        col_d4.metric("Cerradas", f"{metricas['ganadoras']}/{metricas['cerradas']}")
        
        st.markdown("---")
        
        # Gráfico de P/L acumulado
        df = pd.DataFrame(st.session_state['historial_operaciones'])
        df_cerradas = df[df['status'].str.contains('Cerrada')].copy()
        
        if not df_cerradas.empty:
            df_cerradas['pl_acumulado'] = df_cerradas['pl_actual'].cumsum()
            
            fig_pl = go.Figure()
            fig_pl.add_trace(go.Scatter(
                x=df_cerradas['fecha'],
                y=df_cerradas['pl_acumulado'],
                mode='lines+markers',
                name='P/L Acumulado',
                line=dict(color='blue', width=3)
            ))
            
            fig_pl.update_layout(
                title="Curva de P/L Acumulado",
                xaxis_title="Fecha",
                yaxis_title="P/L ($)",
                hovermode='x unified',
                height=400
            )
            
            st.plotly_chart(fig_pl, use_container_width=True)
            
            # Distribución de operaciones
            st.markdown("### 📊 Distribución de Resultados")
            col_chart1, col_chart2 = st.columns(2)
            
            with col_chart1:
                # Pie chart
                fig_pie = go.Figure(data=[go.Pie(
                    labels=['Ganadoras', 'Perdedoras'],
                    values=[metricas['ganadoras'], metricas['perdedoras']],
                    marker=dict(colors=['green', 'red'])
                )])
                fig_pie.update_layout(title="Win/Loss Ratio", height=300)
                st.plotly_chart(fig_pie, use_container_width=True)
            
            with col_chart2:
                # Histograma de P/L
                fig_hist = go.Figure(data=[go.Histogram(
                    x=df_cerradas['pl_actual'],
                    nbinsx=10,
                    marker=dict(
                        color=df_cerradas['pl_actual'],
                        colorscale='RdYlGn',
                        showscale=False
                    )
                )])
                fig_hist.update_layout(
                    title="Distribución de P/L",
                    xaxis_title="P/L ($)",
                    yaxis_title="Frecuencia",
                    height=300
                )
                st.plotly_chart(fig_hist, use_container_width=True)
        
        st.markdown("---")
        
        # Top operaciones
        st.markdown("### 🏆 Top Operaciones")
        
        col_top1, col_top2 = st.columns(2)
        
        with col_top1:
            st.markdown("**🟢 Mejores**")
            if not df_cerradas.empty:
                top_ganadoras = df_cerradas.nlargest(5, 'pl_actual')[['ticker', 'pl_actual', 'fecha']]
                st.dataframe(top_ganadoras, hide_index=True, use_container_width=True)
            else:
                st.info("No hay operaciones cerradas")
        
        with col_top2:
            st.markdown("**🔴 Peores**")
            if not df_cerradas.empty:
                top_perdedoras = df_cerradas.nsmallest(5, 'pl_actual')[['ticker', 'pl_actual', 'fecha']]
                st.dataframe(top_perdedoras, hide_index=True, use_container_width=True)
            else:
                st.info("No hay operaciones cerradas")
        
        st.markdown("---")
        
        # Análisis por ticker
        if not df_cerradas.empty:
            st.markdown("### 📊 Análisis por Ticker")
            
            analisis_ticker = df_cerradas.groupby('ticker').agg({
                'pl_actual': ['sum', 'mean', 'count']
            }).round(2)
            
            analisis_ticker.columns = ['P/L Total', 'P/L Promedio', 'Operaciones']
            analisis_ticker = analisis_ticker.sort_values('P/L Total', ascending=False)
            
            st.dataframe(analisis_ticker, use_container_width=True)

# --- AUTO-REFRESH (si está activado) ---
if auto_refresh:
    import time
    time.sleep(300)  # 5 minutos
    actualizar_precios_historial()
    st.rerun()

st.markdown("---")
st.caption("🩸 Swing Lab v4.0 | Análisis Completo + Dashboard + Auto-actualización")
st.caption("📊 Datos fundamentales de Yahoo Finance (gratuito) | Gestión profesional de riesgo")