import streamlit as st
import pandas as pd
import yfinance as yf

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Swing Lab | Dr. Cruz", page_icon="🩸", layout="centered")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    #MainMenu, footer, header {visibility: hidden;}
    div.stButton > button:first-child {
        background-color: #D80000; color: white; border-radius: 10px; border: none; font-weight: bold; width: 100%;
    }
    </style>
    """, unsafe_allow_html=True)

# --- BARRA LATERAL (CONFIGURACIÓN GLOBAL) ---
with st.sidebar:
    st.header("⚙️ Configuración")
    
    # 1. Capital Total
    capital = st.number_input("Capital Total ($)", value=1000.0, step=100.0)
    
    # 2. Riesgo (Cuánto perder si sale mal)
    riesgo_pct = st.slider("Riesgo Máximo por Trade (%)", 0.5, 5.0, 2.0, 0.1)
    dinero_en_riesgo = capital * (riesgo_pct / 100)
    
    st.markdown("---")
    
    # 3. DIVERSIFICACIÓN (NUEVO)
    st.header("🍰 Diversificación")
    max_alloc_pct = st.slider("Tamaño Máximo de Posición (%)", 10, 100, 25, 5, 
                             help="Nunca invertir más de este % del capital en una sola acción.")
    
    max_inversion_permitida = capital * (max_alloc_pct / 100)
    st.info(f"💰 Tope de Inversión: **${max_inversion_permitida:.0f}**\n(Para tener espacio para otras ~{int(100/max_alloc_pct)} operaciones)")

# --- TÍTULO ---
st.title("🩸 Swing Lab Calculator v3.0")
st.caption("Gestión de Riesgo + Diversificación Inteligente")

# --- BÚSQUEDA AUTOMÁTICA ---
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
                
                # Actualizar estados
                st.session_state['input_entrada'] = float(round(precio_actual, 2))
                st.session_state['input_stop'] = float(round(bajo_14dias, 2))
                st.toast(f"Precio actualizado: ${precio_actual}", icon="✅")
        except:
            st.error("Error al buscar ticker.")

# --- FORMULARIO ---
col1, col2 = st.columns(2)
with col1:
    if 'input_entrada' not in st.session_state: st.session_state['input_entrada'] = 0.0
    entrada = st.number_input("Precio Entrada ($)", step=0.1, key='input_entrada')
with col2:
    if 'input_stop' not in st.session_state: st.session_state['input_stop'] = 0.0
    stop_loss = st.number_input("Stop Loss ($)", step=0.1, key='input_stop')

# --- CÁLCULO MAESTRO ---
st.markdown("<br>", unsafe_allow_html=True)

if st.button("CALCULAR DOSIS 💊"):
    riesgo_por_accion = entrada - stop_loss
    
    if entrada <= 0 or stop_loss <= 0:
        st.warning("⚠️ Faltan precios.")
    elif stop_loss >= entrada:
        st.error("⚠️ El Stop Loss debe ser MENOR a la entrada.")
    else:
        # 1. Límite por RIESGO (La Regla de los $20)
        # ¿Cuántas acciones puedo comprar para que, si pierdo, solo pierda $20?
        acciones_riesgo = dinero_en_riesgo / riesgo_por_accion
        
        # 2. Límite por DIVERSIFICACIÓN (La Regla del Tope)
        # ¿Cuántas acciones caben en mi presupuesto máximo (ej. $250)?
        acciones_presupuesto = max_inversion_permitida / entrada
        
        # 3. DECISIÓN FINAL: Elegimos el menor de los dos límites
        acciones_finales = min(acciones_riesgo, acciones_presupuesto)
        
        # Cálculos resultantes
        inversion_real = acciones_finales * entrada
        riesgo_real = acciones_finales * riesgo_por_accion
        take_profit = entrada + (riesgo_por_accion * 2)
        
        # --- REPORTE VISUAL ---
        
        # Determinamos qué limitó la operación para explicárselo al usuario
        motivo_limite = "Riesgo ($20)"
        if acciones_presupuesto < acciones_riesgo:
            motivo_limite = "Diversificación (Presupuesto)"
            st.warning(f"⚠️ **Nota:** Tu riesgo permite comprar más, pero limitamos la compra a **${max_inversion_permitida:.0f}** para no concentrar todo tu capital en una sola acción.")
        
        st.success(f"✅ Dosis Recetada para: {ticker}")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Cantidad (Acciones)", f"{acciones_finales:.4f}")
        m2.metric("Inversión Total", f"${inversion_real:.2f}")
        m3.metric("Riesgo Asumido", f"${riesgo_real:.2f}", delta=f"Límite: {motivo_limite}", delta_color="off")
        
        st.markdown("---")
        st.subheader("📋 Plan de Salida")
        datos = {
            "Escenario": ["🔴 Stop Loss", "🟢 Take Profit (2:1)"],
            "Precio Objetivo": [f"${stop_loss:.2f}", f"${take_profit:.2f}"],
            "Resultado P/L": [f"-${riesgo_real:.2f}", f"+${riesgo_real * 2:.2f}"]
        }
        st.table(pd.DataFrame(datos))
