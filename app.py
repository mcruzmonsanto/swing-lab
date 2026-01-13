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
    
    # Aquí definimos los famosos $20
    st.write("---")
    riesgo_pct = st.slider("Riesgo de Cuenta (%)", 0.5, 5.0, 2.0, 0.1)
    dinero_en_riesgo = capital * (riesgo_pct / 100)
    
    st.info(f"🛡️ Tu Riesgo ($): **${dinero_en_riesgo:.2f}**")
    st.caption(f"El Stop Loss se colocará ${dinero_en_riesgo:.2f} por debajo del precio.")

# --- TÍTULO ---
st.title("🩸 Swing Lab | Regla Estricta")

# --- ANÁLISIS AUTOMÁTICO ---
col_tick, col_btn = st.columns([3, 1])
with col_tick:
    ticker = st.text_input("Ticker", value="MSFT").upper()

with col_btn:
    st.write("")
    st.write("")
    if st.button("🔍 Analizar"):
        try:
            with st.spinner("Aplicando tu lógica..."):
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1d")
                precio_actual = hist['Close'].iloc[-1]
                
                # --- TU LÓGICA MAESTRA ---
                # Stop Loss = Precio Actual - Dinero en Riesgo ($20)
                stop_calculado = precio_actual - dinero_en_riesgo
                
                # Guardamos en los inputs
                st.session_state['input_entrada'] = float(round(precio_actual, 2))
                st.session_state['input_stop'] = float(round(stop_calculado, 2))
                
                st.toast(f"Stop Loss ajustado a -${dinero_en_riesgo}", icon="✅")
        except:
            st.error("Error buscando ticker.")

# --- INPUTS ---
col1, col2 = st.columns(2)
with col1:
    if 'input_entrada' not in st.session_state: st.session_state['input_entrada'] = 0.0
    entrada = st.number_input("Precio Entrada ($)", step=0.1, key='input_entrada')

with col2:
    if 'input_stop' not in st.session_state: st.session_state['input_stop'] = 0.0
    stop_loss = st.number_input(f"Stop Loss (Entrada - ${dinero_en_riesgo:.0f})", step=0.1, key='input_stop')

# --- CALCULADORA FINAL ---
st.markdown("<br>", unsafe_allow_html=True)
if st.button("CALCULAR DOSIS 💊"):
    if entrada > 0 and stop_loss > 0:
        riesgo_por_accion = entrada - stop_loss
        
        # 1. Cálculo de Acciones
        # Si el Stop es (Precio - $20), el riesgo por acción es $20.
        # Por tanto: $20 (Total) / $20 (Por Acción) = 1 Acción.
        acciones = dinero_en_riesgo / riesgo_por_accion
        
        inversion = acciones * entrada
        
        # Validar si tienes los $1000
        if inversion > capital:
            acciones_reales = capital / entrada
            st.warning(f"⚠️ No tienes suficiente capital para comprar {acciones:.2f} acciones. Se ajustó al máximo posible.")
            acciones = acciones_reales
            inversion = acciones * entrada
            
        riesgo_real = acciones * riesgo_por_accion
        
        # Resultados
        st.success(f"✅ Resultado para {ticker}")
        m1, m2, m3 = st.columns(3)
        m1.metric("Comprar (Acciones)", f"{acciones:.2f}")
        m2.metric("Inversión", f"${inversion:.2f}")
        m3.metric("Riesgo Latente", f"${riesgo_real:.2f}")
        
        take_profit = entrada + (riesgo_por_accion * 2)
        st.table(pd.DataFrame({
            "Nivel": ["Stop Loss (-$20)", "Take Profit (+$40)"],
            "Precio": [f"${stop_loss:.2f}", f"${take_profit:.2f}"],
            "P/L": [f"-${riesgo_real:.2f}", f"+${riesgo_real*2:.2f}"]
        }))
    else:
        st.warning("Pulsa Analizar primero.")
