import streamlit as st
import pandas as pd
import yfinance as yf

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Swing Lab | Dr. Cruz", page_icon="🩸", layout="centered")

# --- ESTILOS CSS (Tu Marca) ---
st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    div.stButton > button:first-child {
        background-color: #D80000; color: white; border-radius: 10px; border: none; font-weight: bold; width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Configuración")
    capital = st.number_input("Capital Total ($)", value=1000.0, step=100.0)
    riesgo_pct = st.slider("Riesgo Máximo (%)", 0.5, 5.0, 2.0, 0.1)
    
    dinero_en_riesgo = capital * (riesgo_pct / 100)
    st.info(f"🛡️ Cinturón de Seguridad: **${dinero_en_riesgo:.2f}**")

# --- TÍTULO ---
st.title("🩸 Swing Lab Calculator")

# --- BÚSQUEDA ---
col_search, col_btn = st.columns([3, 1])
with col_search:
    ticker = st.text_input("Ticker", value="MSFT").upper()
with col_btn:
    st.write("") 
    st.write("")
    if st.button("🔍 Analizar"):
        try:
            with st.spinner("Consultando..."):
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1mo")
                precio_actual = hist['Close'].iloc[-1]
                bajo_14dias = hist['Low'].tail(14).min()
                
                st.session_state['input_entrada'] = float(round(precio_actual, 2))
                st.session_state['input_stop'] = float(round(bajo_14dias, 2))
        except:
            st.error("Error al buscar.")

# --- FORMULARIO ---
col1, col2 = st.columns(2)
with col1:
    if 'input_entrada' not in st.session_state: st.session_state['input_entrada'] = 0.0
    entrada = st.number_input("Precio Entrada ($)", step=0.1, key='input_entrada')
with col2:
    if 'input_stop' not in st.session_state: st.session_state['input_stop'] = 0.0
    stop_loss = st.number_input("Stop Loss ($)", step=0.1, key='input_stop')

# --- CÁLCULO ESTRICTO (TU LÓGICA) ---
st.markdown("<br>", unsafe_allow_html=True)

if st.button("CALCULAR DOSIS 💊"):
    riesgo_por_accion = entrada - stop_loss
    
    if entrada <= 0 or stop_loss <= 0:
        st.warning("⚠️ Faltan precios.")
    elif stop_loss >= entrada:
        st.error("⚠️ El Stop Loss debe ser MENOR a la entrada.")
    else:
        # 1. CÁLCULO DE DOSIS EXACTA (Basado en Riesgo)
        acciones = dinero_en_riesgo / riesgo_por_accion
        
        # 2. VERIFICACIÓN DE SALDO (Solo limita si NO tienes los $1000)
        costo_total = acciones * entrada
        
        if costo_total > capital:
            acciones_ajustadas = capital / entrada
            st.warning(f"⚠️ Saldo insuficiente para la dosis ideal. Se ajustó al máximo posible: {acciones_ajustadas:.2f} acciones.")
            acciones = acciones_ajustadas
            costo_total = acciones * entrada

        # Resultados
        take_profit = entrada + (riesgo_por_accion * 2) # Ratio 1:2
        
        st.success(f"✅ Dosis Exacta para: {ticker}")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Cantidad (Acciones)", f"{acciones:.2f}")  # Aquí saldrá 0.82
        m2.metric("Inversión Total", f"${costo_total:.2f}")  # Aquí saldrá ~$391
        m3.metric("Riesgo Real", f"${(acciones * riesgo_por_accion):.2f}") # Aquí saldrá $20.00
        
        st.markdown("---")
        st.subheader("📋 Plan de Salida")
        datos = {
            "Escenario": ["🔴 Stop Loss", "🟢 Take Profit (2:1)"],
            "Precio Objetivo": [f"${stop_loss:.2f}", f"${take_profit:.2f}"],
            "P/L": [f"-${(acciones * riesgo_por_accion):.2f}", f"+${(acciones * riesgo_por_accion * 2):.2f}"]
        }
        st.table(pd.DataFrame(datos))
