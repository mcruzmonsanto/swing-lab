import streamlit as st
import pandas as pd
import yfinance as yf

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Swing Lab | Dr. Cruz",
    page_icon="🩸",
    layout="centered"
)

# --- ESTILOS CSS (Tu Marca) ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            div.stButton > button:first-child {
                background-color: #D80000;
                color: white;
                border-radius: 10px;
                border: none;
                font-weight: bold;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- INICIALIZAR ESTADO (Para que los datos no se borren) ---
if 'entrada' not in st.session_state:
    st.session_state['entrada'] = 0.0
if 'stop_loss' not in st.session_state:
    st.session_state['stop_loss'] = 0.0

# --- TÍTULO ---
st.title("🩸 Swing Lab Calculator v2.0")
st.markdown("---")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Configuración")
    capital = st.number_input("Capital Total ($)", value=1000.0, step=100.0)
    riesgo_pct = st.slider("Riesgo Máximo (%)", 0.5, 5.0, 2.0, 0.1)
    dinero_en_riesgo = capital * (riesgo_pct / 100)
    st.info(f"🛡️ Cinturón de Seguridad: **${dinero_en_riesgo:.2f}**")

# --- SECCIÓN DE BÚSQUEDA AUTOMÁTICA ---
col_search, col_btn = st.columns([3, 1])
with col_search:
    ticker = st.text_input("Ticker (Símbolo)", value="MSFT").upper()
with col_btn:
    st.write("") # Espacio para alinear
    st.write("") 
    if st.button("🔍 Analizar"):
        try:
            with st.spinner(f"Tomando signos vitales de {ticker}..."):
                # 1. Descargar datos
                stock = yf.Ticker(ticker)
                hist = stock.history(period="1mo")
                
                # 2. Obtener valores
                precio_actual = hist['Close'].iloc[-1]
                bajo_14dias = hist['Low'].tail(14).min()
                
                # 3. ACTUALIZACIÓN FORZADA DE LOS CAMPOS (EL FIX)
                # Escribimos directo en la 'key' del widget
                st.session_state['input_entrada'] = float(round(precio_actual, 2))
                st.session_state['input_stop'] = float(round(bajo_14dias, 2))
                
                st.toast(f"✅ {ticker}: ${precio_actual:.2f}", icon="💉")
                
        except Exception as e:
            st.error(f"Error: {e}")

# --- FORMULARIO DE DOSIS ---
col1, col2 = st.columns(2)

with col1:
    # Eliminamos el 'value=' dinámico porque ahora controlamos la key directo
    # Si la key no existe, inicia en 0.0
    if 'input_entrada' not in st.session_state: st.session_state['input_entrada'] = 0.0
    
    entrada = st.number_input("Precio Entrada ($)", step=0.1, key='input_entrada')

with col2:
    if 'input_stop' not in st.session_state: st.session_state['input_stop'] = 0.0
    
    stop_loss = st.number_input("Stop Loss ($)", step=0.1, help="Sugerido: Mínimo de 14 días", key='input_stop')
    
# --- CÁLCULOS ---
riesgo_por_accion = entrada - stop_loss
es_compra_valida = riesgo_por_accion > 0

st.markdown("<br>", unsafe_allow_html=True) # Espacio

if st.button("CALCULAR DOSIS 💊", use_container_width=True):
    if entrada == 0 or stop_loss == 0:
        st.warning("⚠️ Por favor ingresa los precios o usa el botón 'Analizar'.")
    elif not es_compra_valida:
        st.error("⚠️ El Stop Loss debe ser MENOR que la entrada.")
    else:
        # Fórmulas
        acciones = dinero_en_riesgo / riesgo_por_accion
        inversion_total = acciones * entrada
        take_profit = entrada + (riesgo_por_accion * 2)
        
        # Resultados
        st.success(f"✅ Dosis calculada para: {ticker}")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Comprar (Acciones)", f"{acciones:.4f}")
        c2.metric("Inversión Total", f"${inversion_total:.2f}")
        c3.metric("Riesgo Real", f"${dinero_en_riesgo:.2f}")
        
        # Tabla Plan
        st.subheader("📋 Plan de Salida")
        datos = {
            "Escenario": ["🔴 Stop Loss", "🟢 Take Profit (2:1)"],
            "Precio": [f"${stop_loss:.2f}", f"${take_profit:.2f}"],
            "Resultado": [f"-${dinero_en_riesgo:.2f}", f"+${dinero_en_riesgo*2:.2f}"]
        }
        st.table(pd.DataFrame(datos))
