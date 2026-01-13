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
    .metric-card {
        background-color: #f0f2f6; padding: 10px; border-radius: 10px; text-align: center; margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- SIDEBAR (DATOS FIJOS) ---
with st.sidebar:
    st.header("⚙️ Tu Billetera")
    capital = st.number_input("Capital Total ($)", value=1000.0, step=100.0)
    riesgo_pct = st.slider("Riesgo Máximo (%)", 0.5, 5.0, 2.0, 0.1)
    
    # Cálculo del dinero en riesgo (Ej. $20)
    dinero_en_riesgo = capital * (riesgo_pct / 100)
    
    st.info(f"🛡️ Cinturón de Seguridad: **${dinero_en_riesgo:.2f}**")
    st.caption("Nota: Este es el dinero máximo que perderás si la operación sale mal.")

# --- TÍTULO ---
st.title("🩸 Swing Lab | Dr. Cruz")

# --- BÚSQUEDA Y ANÁLISIS ---
col_tick, col_btn = st.columns([3, 1])
with col_tick:
    ticker = st.text_input("Ticker", value="MSFT").upper()

# Variables para sugerencias
if 'sug_tecnico' not in st.session_state: st.session_state['sug_tecnico'] = 0.0
if 'sug_financiero' not in st.session_state: st.session_state['sug_financiero'] = 0.0

with col_btn:
    st.write("")
    st.write("")
    if st.button("🔍 Analizar"):
        try:
            with st.spinner("Escaneando paciente..."):
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1mo")
                precio_actual = hist['Close'].iloc[-1]
                
                # 1. Stop Técnico (Mínimo 14 días)
                stop_tecnico = hist['Low'].tail(14).min()
                
                # 2. Stop Financiero (Matemático)
                # Fórmula: Precio * (1 - %Riesgo)
                # Esto pone el stop exactamente al 2% de distancia para permitir inversión total.
                stop_financiero = precio_actual * (1 - (riesgo_pct/100))
                
                # Guardar valores
                st.session_state['input_entrada'] = float(round(precio_actual, 2))
                st.session_state['sug_tecnico'] = float(round(stop_tecnico, 2))
                st.session_state['sug_financiero'] = float(round(stop_financiero, 2))
                
                # Por defecto, ponemos el financiero si el usuario quiere maximizar riesgo
                st.session_state['input_stop'] = float(round(stop_financiero, 2))
                
        except Exception as e:
            st.error(f"Error: {e}")

# --- VISUALIZADOR DE OPCIONES ---
if st.session_state['sug_tecnico'] > 0:
    st.markdown("### 🧠 Opciones de Stop Loss Detectadas")
    c_tec, c_fin = st.columns(2)
    
    with c_tec:
        st.info(f"📉 **Técnico (Gráfico)**\n# ${st.session_state['sug_tecnico']}\n(Mínimo de 14 días)")
        if st.button("Usar Técnico"):
            st.session_state['input_stop'] = st.session_state['sug_tecnico']
            
    with c_fin:
        st.success(f"💰 **Financiero (2%)**\n# ${st.session_state['sug_financiero']}\n(Permite invertir los ${capital:.0f})")
        if st.button("Usar Financiero"):
            st.session_state['input_stop'] = st.session_state['sug_financiero']

st.markdown("---")

# --- INPUTS FINALES ---
col1, col2 = st.columns(2)
with col1:
    if 'input_entrada' not in st.session_state: st.session_state['input_entrada'] = 0.0
    entrada = st.number_input("Precio Entrada ($)", step=0.1, key='input_entrada')
with col2:
    if 'input_stop' not in st.session_state: st.session_state['input_stop'] = 0.0
    stop_loss = st.number_input("Stop Loss Seleccionado ($)", step=0.1, key='input_stop')

# --- CÁLCULO DE LA DOSIS ---
if st.button("CALCULAR DOSIS 💊", use_container_width=True):
    riesgo_por_accion = entrada - stop_loss
    
    if entrada <= 0 or stop_loss <= 0:
        st.warning("⚠️ Faltan datos.")
    elif stop_loss >= entrada:
        st.error("⚠️ El Stop Loss debe ser menor a la entrada.")
    else:
        # Cálculos Maestros
        acciones_riesgo = dinero_en_riesgo / riesgo_por_accion
        acciones_capital = capital / entrada
        
        # Elegimos el límite real
        acciones_finales = min(acciones_riesgo, acciones_capital)
        
        costo_total = acciones_finales * entrada
        riesgo_real = acciones_finales * riesgo_por_accion
        take_profit = entrada + (riesgo_por_accion * 2)

        # --- RESULTADOS ---
        st.success(f"✅ Receta Generada para {ticker}")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Comprar (Acciones)", f"{acciones_finales:.2f}")
        m2.metric("Inversión Total", f"${costo_total:.2f}")
        m3.metric("Riesgo Real", f"${riesgo_real:.2f}", 
                  delta="Objetivo Cumplido" if abs(riesgo_real - dinero_en_riesgo) < 1 else f"Debajo del objetivo (-${dinero_en_riesgo - riesgo_real:.2f})")

        st.table(pd.DataFrame({
            "Escenario": ["🔴 Stop Loss", "🟢 Take Profit (2:1)"],
            "Precio": [f"${stop_loss:.2f}", f"${take_profit:.2f}"],
            "P/L ($)": [f"-${riesgo_real:.2f}", f"+${riesgo_real*2:.2f}"]
        }))
        
        if acciones_riesgo > acciones_capital:
             st.caption(f"ℹ️ Nota: Para arriesgar los ${dinero_en_riesgo} exactos con este Stop Loss, necesitarías ${acciones_riesgo*entrada:.0f}. Se ajustó a tu capital disponible (${capital}).")
