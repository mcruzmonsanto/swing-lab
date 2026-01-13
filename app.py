import streamlit as st
import pandas as pd

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Swing Lab | Dr. Cruz",
    page_icon="🩸",
    layout="centered"
)

# --- TU MARCA (CSS PERSONALIZADO: BLANCO, NEGRO, ROJO) ---
# Esto oculta el menú de Streamlit y pone botones rojos
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            
            /* Botones Rojos */
            div.stButton > button:first-child {
                background-color: #D80000;
                color: white;
                border-radius: 10px;
                border: none;
                font-weight: bold;
                padding: 10px 20px;
            }
            div.stButton > button:first-child:hover {
                background-color: #A00000;
                color: white;
            }
            /* Títulos y Métricas */
            h1, h2, h3 {
                color: #000000;
            }
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- TÍTULO ---
st.title("🩸 Swing Lab Calculator")
st.markdown("---")

# --- BARRA LATERAL (DATOS DE CUENTA) ---
with st.sidebar:
    st.header("⚙️ Configuración Cuenta")
    capital = st.number_input("Capital Total ($)", value=1000.0, step=100.0)
    riesgo_pct = st.slider("Riesgo Máximo (%)", min_value=0.5, max_value=5.0, value=2.0, step=0.1)
    
    dinero_en_riesgo = capital * (riesgo_pct / 100)
    st.info(f"🛡️ Cinturón de Seguridad: **${dinero_en_riesgo:.2f}**")

# --- PANEL PRINCIPAL (DATOS DEL PACIENTE) ---
col1, col2 = st.columns(2)

with col1:
    ticker = st.text_input("Ticker (Símbolo)", value="MSFT").upper()
    entrada = st.number_input("Precio Entrada ($)", value=477.18, step=0.1)

with col2:
    st.write("") # Espacio
    st.write("") 
    stop_loss = st.number_input("Stop Loss ($)", value=453.00, step=0.1)

# --- CÁLCULOS ---
riesgo_por_accion = entrada - stop_loss
es_compra_valida = riesgo_por_accion > 0

if st.button("CALCULAR DOSIS 💊"):
    if not es_compra_valida:
        st.error("⚠️ El Stop Loss debe ser MENOR que la entrada para compras (Long).")
    else:
        # Fórmula Maestra
        acciones = dinero_en_riesgo / riesgo_por_accion
        inversion_total = acciones * entrada
        take_profit = entrada + (riesgo_por_accion * 2) # Ratio 1:2
        ratio = 2.0
        
        # --- RESULTADOS VISUALES ---
        st.success(f"✅ Paciente: {ticker} | Dosis Calculada")
        
        # Métricas Grandes
        c1, c2, c3 = st.columns(3)
        c1.metric("Comprar (Acciones)", f"{acciones:.4f}")
        c2.metric("Inversión Total", f"${inversion_total:.2f}")
        c3.metric("Riesgo Real", f"${dinero_en_riesgo:.2f}")
        
        st.markdown("---")
        
        # Tabla de Salidas
        st.subheader("📋 Plan de Salida")
        datos_plan = {
            "Escenario": ["🔴 Stop Loss (Pérdida)", "🟢 Take Profit (Ganancia)"],
            "Precio Objetivo": [f"${stop_loss:.2f}", f"${take_profit:.2f}"],
            "Resultado ($)": [f"-${dinero_en_riesgo:.2f}", f"+${dinero_en_riesgo * ratio:.2f}"]
        }
        df = pd.DataFrame(datos_plan)
        st.table(df)

        # Advertencia si falta dinero
        if inversion_total > capital:
            st.warning(f"⚠️ Nota: La inversión requerida (${inversion_total:.2f}) supera tu capital actual.")
