import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Swing Lab | Dr. Cruz", page_icon="🩸", layout="wide")
st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    div.stButton > button:first-child {
        background-color: #D80000; color: white; border-radius: 10px; border: none; font-weight: bold; width: 100%;
    }
    .metric-card { background-color: #f0f2f6; padding: 10px; border-radius: 10px; text-align: center; }
    .filter-pass { color: green; font-weight: bold; }
    .filter-fail { color: red; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- INICIALIZAR SESSION STATE ---
if 'historial_operaciones' not in st.session_state:
    st.session_state['historial_operaciones'] = []
if 'auto_refresh' not in st.session_state:
    st.session_state['auto_refresh'] = False
if 'portfolio_forward_test' not in st.session_state:
    st.session_state['portfolio_forward_test'] = {
        'capital_inicial': 1000.0,
        'capital_actual': 1000.0,
        'trades': []
    }
if 'modo_estricto_tipranks' not in st.session_state:
    st.session_state['modo_estricto_tipranks'] = True
if 'tracking_portfolio_enabled' not in st.session_state:
    st.session_state['tracking_portfolio_enabled'] = True

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

def calcular_volumen_relativo(ticker_obj):
    """Calcula volumen relativo (actual vs promedio 20d)"""
    try:
        hist = ticker_obj.history(period="1mo")
        if len(hist) < 2:
            return None, None
        
        volumen_actual = hist['Volume'].iloc[-1]
        volumen_promedio = hist['Volume'].mean()
        volumen_relativo = (volumen_actual / volumen_promedio) * 100
        
        return round(volumen_relativo, 0), int(volumen_actual)
    except:
        return None, None

def calcular_rsi(ticker_obj, periodo=14):
    """Calcula RSI de 14 períodos"""
    try:
        hist = ticker_obj.history(period="3mo")
        if len(hist) < periodo + 1:
            return None
        
        # Calcular cambios de precio
        delta = hist['Close'].diff()
        
        # Ganancias y pérdidas
        ganancia = delta.where(delta > 0, 0).rolling(window=periodo).mean()
        perdida = -delta.where(delta < 0, 0).rolling(window=periodo).mean()
        
        # RSI
        rs = ganancia / perdida
        rsi = 100 - (100 / (1 + rs))
        
        return round(rsi.iloc[-1], 1)
    except:
        return None


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

def cargar_portfolio():
    """Carga el portfolio de forward testing desde JSON"""
    portfolio_file = 'portfolio_data.json'
    if os.path.exists(portfolio_file):
        try:
            with open(portfolio_file, 'r') as f:
                data = json.load(f)
                st.session_state['portfolio_forward_test'] = data
        except:
            pass

def guardar_portfolio():
    """Guarda el portfolio de forward testing en JSON"""
    portfolio_file = 'portfolio_data.json'
    try:
        with open(portfolio_file, 'w') as f:
            json.dump(st.session_state['portfolio_forward_test'], f, indent=2)
    except:
        pass

def agregar_trade_portfolio(ticker, acciones, entrada, stop, tp1, tp2, inversion, 
                            smart_score, upside, consensus):
    """Agrega trade al portfolio de forward testing"""
    if not st.session_state['tracking_portfolio_enabled']:
        return
    
    trade = {
        'fecha': datetime.now().strftime('%Y-%m-%d %H:%M'),
        'ticker': ticker,
        'acciones': round(acciones, 2),
        'entrada': round(entrada, 2),
        'stop_loss': round(stop, 2),
        'tp_1_2': round(tp1, 2),
        'tp_1_3': round(tp2, 2),
        'inversion': round(inversion, 2),
        'status': 'Activa',
        'precio_actual': round(entrada, 2),
        'pl_actual': 0.0,
        'smart_score': smart_score,
        'upside': upside,
        'consensus': consensus
    }
    
    st.session_state['portfolio_forward_test']['trades'].insert(0, trade)
    st.session_state['portfolio_forward_test']['capital_actual'] -= inversion
    guardar_portfolio()

def validar_filtros_tipranks(smart_score, upside, consensus, volumen_relativo=None, rsi=None):
    """Valida que se cumplan los filtros de TipRanks + Técnicos (Volumen + RSI)"""
    filtros = {
        'smart_score': {
            'pasa': smart_score >= 8,
            'mensaje': f"Smart Score: {smart_score}/10 {'✅' if smart_score >= 8 else '❌'}"
        },
        'upside': {
            'pasa': upside >= 10,
            'mensaje': f"Upside: {upside:.1f}% {'✅' if upside >= 10 else '❌ (mínimo 10%)'}"
        },
        'consensus': {
            'pasa': consensus in ['Strong Buy', 'Moderate Buy'],
            'mensaje': f"Consenso: {consensus} {'✅' if consensus in ['Strong Buy', 'Moderate Buy'] else '❌'}"
        }
    }
    
    # Agregar volumen si está disponible (> 100% = por encima del promedio)
    if volumen_relativo is not None:
        volumen_ok = volumen_relativo >= 100
        filtros['volumen'] = {
            'pasa': volumen_ok,
            'mensaje': f"Volumen: {volumen_relativo:.0f}% {'✅' if volumen_ok else '❌ (bajo promedio)'}"
        }
    
    # Agregar RSI si está disponible (30-65 = zona óptima swing)
    if rsi is not None:
        rsi_optimo = 30 <= rsi <= 65
        filtros['rsi'] = {
            'pasa': rsi_optimo,
            'mensaje': f"RSI: {rsi:.1f} {'✅' if rsi_optimo else '❌ (óptimo 30-65)'}"
        }
    
    todos_pasan = all(f['pasa'] for f in filtros.values())
    return filtros, todos_pasan

def actualizar_precios_portfolio():
    """Actualiza los precios del portfolio de forward testing"""
    for trade in st.session_state['portfolio_forward_test']['trades']:
        if trade['status'] == 'Activa':
            try:
                stock = yf.Ticker(trade['ticker'])
                precio_actual = stock.history(period="1d")['Close'].iloc[-1]
                trade['precio_actual'] = round(precio_actual, 2)
                
                # Calcular P/L
                pl = (precio_actual - trade['entrada']) * trade['acciones']
                trade['pl_actual'] = round(pl, 2)
                
                # Verificar si tocó Stop Loss o Take Profit
                if precio_actual <= trade['stop_loss']:
                    trade['status'] = 'Cerrada (Stop Loss)'
                    # Devolver capital menos pérdida
                    perdida = (trade['entrada'] - precio_actual) * trade['acciones']
                    capital_recuperado = trade['inversion'] - perdida
                    st.session_state['portfolio_forward_test']['capital_actual'] += capital_recuperado
                elif precio_actual >= trade['tp_1_2']:
                    trade['status'] = 'Cerrada (TP 1:2)'
                    # Devolver capital más ganancia
                    ganancia = (precio_actual - trade['entrada']) * trade['acciones']
                    capital_recuperado = trade['inversion'] + ganancia
                    st.session_state['portfolio_forward_test']['capital_actual'] += capital_recuperado
            except:
                pass
    
    guardar_portfolio()

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
    st.subheader("📊 TipRanks")
    modo_estricto = st.checkbox("Modo Estricto", value=True,
                               help="Bloquea operaciones que no cumplan los filtros de TipRanks")
    st.session_state['modo_estricto_tipranks'] = modo_estricto
    
    if modo_estricto:
        st.success("🔒 Filtros activados:\n\n✅ Smart Score ≥ 8\n\n✅ Upside ≥ 10%\n\n✅ Consensus: Buy\n\n✅ Volumen > promedio\n\n✅ RSI 30-65")
    else:
        st.warning("⚠️ Modo permisivo")
    
    st.write("---")
    st.subheader("💼 Forward Testing")
    tracking_enabled = st.checkbox("Tracking Portfolio $1000", value=True,
                                  help="Trackea operaciones aprobadas por TipRanks en portfolio de $1000")
    st.session_state['tracking_portfolio_enabled'] = tracking_enabled
    
    if tracking_enabled:
        # Cargar portfolio al inicio
        cargar_portfolio()
        balance = st.session_state['portfolio_forward_test']['capital_actual']
        inicial = st.session_state['portfolio_forward_test']['capital_inicial']
        pl_portfolio = balance - inicial
        
        st.metric("Balance Actual", f"${balance:.2f}", 
                 delta=f"${pl_portfolio:.2f}")
        st.caption(f"Capital inicial: ${inicial:.2f}")
    
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
                if st.session_state['tracking_portfolio_enabled']:
                    actualizar_precios_portfolio()
            st.success("✅ Precios actualizados")
            st.rerun()
    
    st.write("---")
    st.subheader("📊 Método Stop Loss")
    st.success("**Soporte 20 Días**\n\n✅ Mínimo 4 semanas\n\n✅ Colchón 2%\n\n✅ Ideal Swing Trading")
    
    ajuste_manual = st.checkbox("🔧 Ajuste manual del Stop", value=False)

# --- TABS PRINCIPALES ---
tab1, tab2, tab3, tab4 = st.tabs(["🩸 Nueva Operación", "📊 Historial", "📈 Dashboard", "💼 Portfolio $1000"])

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
                    
                    # 3. Calcular volumen relativo
                    volumen_rel, volumen_actual = calcular_volumen_relativo(stock)
                    
                    # 4. Calcular RSI
                    rsi_actual = calcular_rsi(stock, periodo=14)
                    
                    # 5. Obtener datos fundamentales (puede fallar, usamos valores por defecto)
                    datos_fundamentales = obtener_datos_fundamentales(ticker)
                    
                    if stop_calculado and minimo_base and datos_fundamentales:
                        # Guardar en session state
                        st.session_state['ticker_analizado'] = ticker
                        st.session_state['precio_entrada'] = float(round(precio_actual, 2))
                        st.session_state['stop_loss'] = float(stop_calculado)
                        st.session_state['info_tecnica'] = info
                        st.session_state['minimo_base'] = round(minimo_base, 2)
                        st.session_state['datos_fundamentales'] = datos_fundamentales
                        st.session_state['volumen_relativo'] = volumen_rel
                        st.session_state['rsi_tecnico'] = rsi_actual
                        
                        st.success(f"✅ Análisis técnico completado para {ticker}")
                        
                        # Mostrar resultados técnicos
                        st.markdown("#### 📈 Análisis Técnico")
                        col_t1, col_t2, col_t3, col_t4, col_t5 = st.columns(5)
                        col_t1.metric("💵 Precio Actual", f"${precio_actual:.2f}")
                        col_t2.metric("📉 Soporte 20d", f"${minimo_base:.2f}")
                        col_t3.metric("🛑 Stop Loss", f"${stop_calculado:.2f}")
                        
                        if volumen_rel:
                            vol_emoji = "✅" if volumen_rel >= 100 else "⚠️"
                            col_t4.metric(f"{vol_emoji} Volumen", f"{volumen_rel:.0f}%")
                        else:
                            col_t4.metric("📊 Volumen", "N/A")
                        
                        if rsi_actual:
                            rsi_optimo = 30 <= rsi_actual <= 65
                            rsi_emoji = "✅" if rsi_optimo else "⚠️"
                            col_t5.metric(f"{rsi_emoji} RSI (14)", f"{rsi_actual:.1f}")
                        else:
                            col_t5.metric("📊 RSI", "N/A")
                        
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
        
        # MANUAL TIPRANKS INPUT (PERSISTENTE)
        st.markdown("### 📊 Datos de TipRanks (Entrada Manual)")
        st.info("💡 Busca **" + st.session_state['ticker_analizado'] + "** en TipRanks.com e ingresa los datos:")
        
        col_tr1, col_tr2, col_tr3, col_tr4 = st.columns(4)
        
        with col_tr1:
            smart_score_manual = st.number_input("Smart Score (1-10)", 
                                                min_value=1, max_value=10, value=5,
                                                key="smart_score_input",
                                                help="Busca el Smart Score en TipRanks")
        
        with col_tr2:
            price_target_manual = st.number_input("Price Target ($)", 
                                                 value=float(st.session_state['precio_entrada'] * 1.1),
                                                 step=1.0,
                                                 key="price_target_input",
                                                 help="Average Price Target de TipRanks")
        
        with col_tr3:
            # Calcular upside automáticamente
            precio_actual = st.session_state['precio_entrada']
            upside_calculado = ((price_target_manual - precio_actual) / precio_actual) * 100
            st.metric("Upside Calculado", f"{upside_calculado:.1f}%")
        
        with col_tr4:
            consensus_manual = st.selectbox("Consenso",
                                           ["Strong Buy", "Moderate Buy", "Hold", 
                                            "Moderate Sell", "Strong Sell"],
                                           index=1,
                                           key="consensus_input",
                                           help="Consenso de analistas en TipRanks")
        
        # Validar filtros TipRanks + Volumen + RSI
        volumen_rel = st.session_state.get('volumen_relativo', None)
        rsi_tecnico = st.session_state.get('rsi_tecnico', None)
        filtros, todos_pasan = validar_filtros_tipranks(smart_score_manual, upside_calculado, consensus_manual, volumen_rel, rsi_tecnico)
        
        st.markdown("---")
        st.markdown("#### ✅ Validación de Filtros (TipRanks + Técnicos)")
        
        # Determinar número de columnas según filtros disponibles
        num_filtros = 3 + ('volumen' in filtros) + ('rsi' in filtros)
        cols = st.columns(num_filtros)
        
        # Mostrar filtros básicos
        with cols[0]:
            if filtros['smart_score']['pasa']:
                st.success(filtros['smart_score']['mensaje'])
            else:
                st.error(filtros['smart_score']['mensaje'])
        
        with cols[1]:
            if filtros['upside']['pasa']:
                st.success(filtros['upside']['mensaje'])
            else:
                st.error(filtros['upside']['mensaje'])
        
        with cols[2]:
            if filtros['consensus']['pasa']:
                st.success(filtros['consensus']['mensaje'])
            else:
                st.error(filtros['consensus']['mensaje'])
        
        # Mostrar volumen si existe
        col_idx = 3
        if 'volumen' in filtros:
            with cols[col_idx]:
                if filtros['volumen']['pasa']:
                    st.success(filtros['volumen']['mensaje'])
                else:
                    st.error(filtros['volumen']['mensaje'])
            col_idx += 1
        
        # Mostrar RSI si existe
        if 'rsi' in filtros:
            with cols[col_idx]:
                if filtros['rsi']['pasa']:
                    st.success(filtros['rsi']['mensaje'])
                else:
                    st.error(filtros['rsi']['mensaje'])
        
        # Mensaje final de validación
        if todos_pasan:
            st.success("✅ **¡Acción APROBADA por todos los filtros de TipRanks!**")
            # Guardar datos de TipRanks en session state
            st.session_state['tipranks_data'] = {
                'smart_score': smart_score_manual,
                'price_target': price_target_manual,
                'upside': upside_calculado,
                'consensus': consensus_manual
            }
        else:
            st.warning("⚠️ **La acción NO cumple todos los criterios de TipRanks**")
            
            if st.session_state['modo_estricto_tipranks']:
                st.error("🔒 **Modo Estricto Activado**: No puedes proceder con esta operación")
                st.info("💡 Desactiva el 'Modo Estricto' en el sidebar si quieres continuar de todos modos")
            else:
                st.warning("⚠️ Modo permisivo: Puedes continuar bajo tu propio riesgo")
            
            # Guardar datos de TipRanks en session state (incluso si no pasan)
            st.session_state['tipranks_data'] = {
                'smart_score': smart_score_manual,
                'price_target': price_target_manual,
                'upside': upside_calculado,
                'consensus': consensus_manual
            }
        
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
                
                # LÍMITE DE POSICIÓN: Máximo 25% del capital por operación (Swing Trading)
                max_inversion_permitida = capital * 0.25
                
                if inversion_necesaria > capital:
                    st.warning("⚠️ Capital Insuficiente")
                    acciones = capital / entrada
                    inversion = capital
                    riesgo_real = acciones * riesgo_por_accion
                    st.info(f"✂️ Ajustado a {acciones:.2f} acciones")
                elif inversion_necesaria > max_inversion_permitida:
                    # LIMITADO AL 25% DEL CAPITAL
                    st.warning(f"⚠️ Posición limitada al 25% del capital (${max_inversion_permitida:.2f})")
                    acciones = max_inversion_permitida / entrada
                    inversion = max_inversion_permitida
                    riesgo_real = acciones * riesgo_por_accion
                    st.info(f"✂️ Ajustado a {acciones:.2f} acciones para diversificación")
                    st.caption("💡 **Swing Trading:** Máximo 25% por posición permite 4-5 operaciones simultáneas")
                else:
                    acciones = acciones_ideales
                    inversion = inversion_necesaria
                    riesgo_real = dinero_en_riesgo
                
                # GUARDAR EN SESSION STATE PARA QUE PERSISTA AL PRESIONAR "GUARDAR"
                st.session_state['posicion_calculada'] = {
                    'acciones': acciones,
                    'inversion': inversion,
                    'riesgo_real': riesgo_real,
                    'entrada': entrada,
                    'stop_loss': stop_loss
                }
                
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
                
                # Guardar TPs también en session state
                st.session_state['posicion_calculada']['tp_1_2'] = tp_1_2
                st.session_state['posicion_calculada']['tp_1_3'] = tp_1_3
                
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
                
                if riesgo_real <= dinero_en_riesgo * 1.15:
                    st.success("✅ Operación Aprobada")
                else:
                    st.error(f"❌ Riesgo excesivo")
            
            elif stop_loss >= entrada:
                st.error("❌ Stop Loss debe ser menor que entrada")
            else:
                st.warning("⚠️ Completa todos los campos")
        
        # BOTÓN GUARDAR FUERA DEL BLOQUE DE CALCULAR (para que persista después del rerun)
        if 'posicion_calculada' in st.session_state:
            st.markdown("---")
            if st.button("💾 GUARDAR EN HISTORIAL", use_container_width=True, key="btn_guardar"):
                # Obtener valores calculados desde session_state
                pos = st.session_state['posicion_calculada']
                
                # Obtener datos de TipRanks (usar valores por defecto si no existen)
                if 'tipranks_data' in st.session_state:
                    tipranks = st.session_state['tipranks_data']
                else:
                    # Valores por defecto si no se ingresaron datos de TipRanks
                    st.warning("⚠️ No ingresaste datos de TipRanks. Se guardarán valores por defecto.")
                    tipranks = {
                        'smart_score': 5,
                        'upside': 0,
                        'consensus': 'Hold'
                    }
                
                # Guardar en historial normal
                agregar_a_historial(
                    st.session_state['ticker_analizado'], 
                    pos['acciones'], pos['entrada'], pos['stop_loss'], 
                    pos['tp_1_2'], pos['tp_1_3'],
                    pos['inversion'], pos['riesgo_real'], 
                    tipranks['smart_score'],
                    tipranks['upside'],
                    tipranks['consensus']
                )
                
                # Guardar en portfolio de forward testing si está habilitado
                if st.session_state['tracking_portfolio_enabled']:
                    agregar_trade_portfolio(
                        st.session_state['ticker_analizado'],
                        pos['acciones'], pos['entrada'], pos['stop_loss'], 
                        pos['tp_1_2'], pos['tp_1_3'],
                        pos['inversion'],
                        tipranks['smart_score'],
                        tipranks['upside'],
                        tipranks['consensus']
                    )
                    st.success(f"✅ Operación guardada en historial y portfolio ($1000)")
                else:
                    st.success("✅ Operación guardada en historial")
                
                # Limpiar la posición calculada después de guardar
                del st.session_state['posicion_calculada']
                st.balloons()
                st.rerun()
    
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

# ==================== TAB 4: PORTFOLIO FORWARD TESTING ====================
with tab4:
    st.title("💼 Portfolio Forward Testing ($1000)")
    
    if not st.session_state['tracking_portfolio_enabled']:
        st.warning("⚠️ El tracking de portfolio está desactivado")
        st.info("Activa 'Tracking Portfolio $1000' en el sidebar para usar esta función")
    else:
        # Cargar portfolio
        cargar_portfolio()
        portfolio = st.session_state['portfolio_forward_test']
        
        # Métricas principales
        st.markdown("### 📊 Resumen del Portfolio")
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        
        capital_inicial = portfolio['capital_inicial']
        capital_actual = portfolio['capital_actual']
        pl_total = capital_actual - capital_inicial
        roi = (pl_total / capital_inicial) * 100
        
        col_p1.metric("Capital Inicial", f"${capital_inicial:.2f}")
        col_p2.metric("Capital Actual", f"${capital_actual:.2f}", delta=f"${pl_total:.2f}")
        col_p3.metric("ROI", f"{roi:.1f}%")
        col_p4.metric("Total Trades", len(portfolio['trades']))
        
        # Botón de actualización
        col_ref1, col_ref2 = st.columns([3, 1])
        with col_ref2:
            if st.button("🔄 Actualizar Precios Portfolio", use_container_width=True):
                with st.spinner("Actualizando precios del portfolio..."):
                    actualizar_precios_portfolio()
                st.success("✅ Portfolio actualizado")
                st.rerun()
        
        st.markdown("---")
        
        # Lista de trades
        if len(portfolio['trades']) == 0:
            st.info("📭 No hay trades en el portfolio de forward testing")
            st.caption("💡 Las operaciones que apruebes con TipRanks se agregarán automáticamente aquí")
        else:
            st.markdown("### 📋 Trades del Portfolio")
            
            df_portfolio = pd.DataFrame(portfolio['trades'])
            
            # Calcular métricas
            activas = len(df_portfolio[df_portfolio['status'] == 'Activa'])
            cerradas = len(df_portfolio[df_portfolio['status'] != 'Activa'])
            
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Trades Activos", activas)
            col_m2.metric("Trades Cerrados", cerradas)
            
            if cerradas > 0:
                df_cerradas = df_portfolio[df_portfolio['status'] != 'Activa']
                ganadoras = len(df_cerradas[df_cerradas['pl_actual'] > 0])
                win_rate = (ganadoras / cerradas * 100) if cerradas > 0 else 0
                col_m3.metric("Win Rate", f"{win_rate:.1f}%")
            
            st.markdown("---")
            
            # Tabla de trades
            st.dataframe(df_portfolio[[
                'fecha', 'ticker', 'acciones', 'entrada', 'precio_actual',
                'stop_loss', 'tp_1_2', 'pl_actual', 'status',
                'smart_score', 'upside', 'consensus'
            ]], use_container_width=True, hide_index=True)
            
            # Alertas
            st.markdown("### 🔔 Alertas de Precio (Portfolio)")
            alertas_encontradas = False
            for trade in portfolio['trades']:
                if trade['status'] == 'Activa':
                    dist_stop = ((trade['precio_actual'] - trade['stop_loss']) / trade['entrada']) * 100
                    dist_tp = ((trade['tp_1_2'] - trade['precio_actual']) / trade['entrada']) * 100
                    
                    if dist_stop < 2:
                        st.error(f"🚨 **{trade['ticker']}** muy cerca del Stop Loss ({dist_stop:.1f}%)")
                        alertas_encontradas = True
                    elif dist_tp < 2:
                        st.success(f"🎯 **{trade['ticker']}** muy cerca del TP 1:2 ({dist_tp:.1f}%)")
                        alertas_encontradas = True
            
            if not alertas_encontradas:
                st.info("✅ No hay alertas activas")
            
            st.markdown("---")
            
            # Gráfico de evolución del capital
            if cerradas > 0:
                st.markdown("### 📈 Evolución del Capital")
                
                # Ordenar por fecha
                df_sorted = df_portfolio.sort_values('fecha')
                
                # Calcular capital acumulado (simplificado)
                df_sorted_cerradas = df_sorted[df_sorted['status'] != 'Activa'].copy()
                
                if not df_sorted_cerradas.empty:
                    capital_evolution = [capital_inicial]
                    for _, trade in df_sorted_cerradas.iterrows():
                        capital_evolution.append(capital_evolution[-1] + trade['pl_actual'])
                    
                    fig_capital = go.Figure()
                    fig_capital.add_trace(go.Scatter(
                        x=list(range(len(capital_evolution))),
                        y=capital_evolution,
                        mode='lines+markers',
                        name='Capital',
                        line=dict(color='blue', width=3),
                        fill='tonexty'
                    ))
                    
                    fig_capital.update_layout(
                        title="Evolución del Capital en Portfolio",
                        xaxis_title="Número de Trades Cerrados",
                        yaxis_title="Capital ($)",
                        hovermode='x unified',
                        height=400
                    )
                    
                    st.plotly_chart(fig_capital, use_container_width=True)
            
            st.markdown("---")
            
            # Opciones de exportación
            st.markdown("### 📥 Exportar Datos")
            col_exp1, col_exp2, col_exp3 = st.columns(3)
            
            with col_exp1:
                # Exportar todo a CSV
                csv_all = df_portfolio.to_csv(index=False)
                st.download_button(
                    "📥 Descargar Portfolio Completo",
                    csv_all,
                    "portfolio_forward_test.csv",
                    "text/csv",
                    use_container_width=True
                )
            
            with col_exp2:
                # Exportar trades activos para Stock Master
                df_activos = df_portfolio[df_portfolio['status'] == 'Activa']
                if not df_activos.empty:
                    csv_stock_master = df_activos[['ticker', 'acciones', 'entrada', 'stop_loss', 'tp_1_2', 'tp_1_3']].to_csv(index=False)
                    st.download_button(
                        "📱 Exportar a Stock Master",
                        csv_stock_master,
                        "stock_master_import.csv",
                        "text/csv",
                        use_container_width=True
                    )
                else:
                    st.button("📱 Exportar a Stock Master", disabled=True, use_container_width=True)
            
            with col_exp3:
                # Reiniciar portfolio
                if st.button("🔄 Reiniciar Portfolio", use_container_width=True, type="secondary"):
                    if st.checkbox("⚠️ Confirmar reinicio (se perderán todos los datos)"):
                        st.session_state['portfolio_forward_test'] = {
                            'capital_inicial': 1000.0,
                            'capital_actual': 1000.0,
                            'trades': []
                        }
                        guardar_portfolio()
                        st.success("✅ Portfolio reiniciado")
                        st.rerun()


# --- AUTO-REFRESH (si está activado) ---
if auto_refresh:
    import time
    time.sleep(300)  # 5 minutos
    actualizar_precios_historial()
    st.rerun()

st.markdown("---")
st.caption("🩸 Swing Lab v5.0 | TipRanks Integration + Forward Testing Portfolio")
st.caption("📊 Filtros profesionales TipRanks (Smart Score ≥ 8, Upside ≥ 10%, Consensus Buy) + Portfolio Tracker $1000")