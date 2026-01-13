import streamlit as st
import pandas as pd
import yfinance as yf

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Swing Lab | Dr. Cruz", page_icon="🩸", layout="centered")
st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    div.stButton > button:first-child {
        background-color: #D80000; color: white; border-radius: 10px; border: none; font-weight: bold; width: 100%;
    }
    .metric-card { background-color: #f0f2f6; padding: 10px; border-radius: 10px; text-align: center; }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR (DINERO) ---
with st.sidebar:
    st.header("⚙️ Tu Billetera")
    capital = st.number_input("Capital Total ($)", value=1000.0, step=100.0)
    
    st.write("---")
    riesgo_pct = st.slider("Riesgo de Cuenta (%)", 0.5, 5.0, 2.0, 0.1)
    dinero_en_riesgo = capital * (riesgo_pct / 100)
    
    st.info(f"🛡️ Riesgo Máximo: **${dinero_en_riesgo:.2f}**")
    st.caption("Este es el máximo que puedes perder en UNA operación.")

# --- TÍTULO ---
st.title("🩸 Swing Lab | Regla Estricta")
st.caption("Calcula cuántas acciones comprar según tu Stop Loss técnico")

# --- ANÁLISIS AUTOMÁTICO ---
col_tick, col_btn = st.columns([3, 1])
with col_tick:
    ticker = st.text_input("Ticker", value="MSFT").upper()

with col_btn:
    st.write("")
    st.write("")
    if st.button("🔍 Analizar"):
        try:
            with st.spinner("Obteniendo precio actual..."):
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1d")
                precio_actual = hist['Close'].iloc[-1]
                
                # Solo guardamos el precio de entrada
                st.session_state['input_entrada'] = float(round(precio_actual, 2))
                
                st.toast(f"Precio actual: ${precio_actual:.2f}", icon="✅")
        except:
            st.error("Error buscando ticker.")

# --- INPUTS ---
st.markdown("### 📊 Parámetros de la Operación")

col1, col2, col3 = st.columns(3)
with col1:
    if 'input_entrada' not in st.session_state: 
        st.session_state['input_entrada'] = 477.18
    entrada = st.number_input("💵 Entrada ($)", step=0.01, key='input_entrada')

with col2:
    stop_loss = st.number_input("🛑 Stop Loss ($)", value=453.0, step=0.01)

with col3:
    # Calculamos automáticamente el riesgo por acción
    riesgo_por_accion = entrada - stop_loss if entrada > stop_loss else 0
    st.metric("Riesgo/Acción", f"${riesgo_por_accion:.2f}")

# --- EXPLICACIÓN VISUAL ---
if riesgo_por_accion > 0:
    st.info(f"📏 **Distancia al Stop**: ${riesgo_por_accion:.2f} por acción")

# --- CALCULADORA FINAL ---
st.markdown("<br>", unsafe_allow_html=True)

if st.button("💊 CALCULAR DOSIS", use_container_width=True):
    if entrada > 0 and stop_loss > 0 and stop_loss < entrada:
        # CÁLCULO CORRECTO
        riesgo_por_accion = entrada - stop_loss
        
        # 1. Cuántas acciones puedo comprar con mi riesgo de $20?
        acciones_ideales = dinero_en_riesgo / riesgo_por_accion
        
        # 2. Cuánto dinero necesito para comprar esas acciones?
        inversion_necesaria = acciones_ideales * entrada
        
        # 3. Verificar si tengo suficiente capital
        if inversion_necesaria > capital:
            st.warning(f"⚠️ **Capital Insuficiente**")
            st.write(f"Necesitas ${inversion_necesaria:.2f} pero solo tienes ${capital:.2f}")
            
            # Ajustar al máximo posible
            acciones = capital / entrada
            inversion = capital
            riesgo_real = acciones * riesgo_por_accion
            
            st.info(f"Se ajustó a **{acciones:.2f} acciones** (máximo posible)")
        else:
            acciones = acciones_ideales
            inversion = inversion_necesaria
            riesgo_real = dinero_en_riesgo
        
        # --- RESULTADOS ---
        st.success(f"✅ **Orden de Compra para {ticker}**")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("🔢 Acciones", f"{acciones:.2f}")
        m2.metric("💰 Inversión", f"${inversion:.2f}")
        m3.metric("⚠️ Riesgo Real", f"${riesgo_real:.2f}", 
                 delta=f"{(riesgo_real/capital)*100:.1f}% de tu cuenta")
        
        # --- NIVELES DE SALIDA ---
        st.markdown("### 🎯 Niveles de Salida")
        
        # Take Profit con ratio 1:2
        take_profit = entrada + (riesgo_por_accion * 2)
        ganancia_potencial = acciones * (take_profit - entrada)
        
        df_niveles = pd.DataFrame({
            "Nivel": ["🛑 Stop Loss", "🎯 Take Profit (1:2)"],
            "Precio": [f"${stop_loss:.2f}", f"${take_profit:.2f}"],
            "P/L": [f"-${riesgo_real:.2f}", f"+${ganancia_potencial:.2f}"],
            "% Cuenta": [f"-{(riesgo_real/capital)*100:.1f}%", 
                        f"+{(ganancia_potencial/capital)*100:.1f}%"]
        })
        
        st.dataframe(df_niveles, use_container_width=True, hide_index=True)
        
        # --- RESUMEN PARA STOCK MASTER ---
        st.markdown("---")
        st.markdown("### 📱 Para ingresar en Stock Master:")
        
        col_a, col_b = st.columns(2)
        with col_a:
            st.code(f"""
Symbol: {ticker}
Shares: {acciones:.2f}
Price: ${entrada:.2f}
            """)
        with col_b:
            st.code(f"""
Stop Loss: ${stop_loss:.2f}
Take Profit: ${take_profit:.2f}
Risk/Reward: 1:2
            """)
        
        # --- VALIDACIÓN FINAL ---
        if riesgo_real > dinero_en_riesgo * 1.1:  # 10% de margen
            st.error(f"⚠️ **ALERTA**: Tu riesgo real (${riesgo_real:.2f}) excede tu límite (${dinero_en_riesgo:.2f})")
        else:
            st.success(f"✅ Riesgo dentro del límite permitido")
            
    elif stop_loss >= entrada:
        st.error("❌ El Stop Loss debe ser MENOR que el precio de entrada")
    else:
        st.warning("⚠️ Completa todos los campos correctamente")

# --- FOOTER ---
st.markdown("---")
st.caption("🩸 Swing Lab v2.0 | Gestión de Riesgo Profesional")