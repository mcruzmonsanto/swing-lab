# Swing Lab v5.0 🩸

> **Análisis profesional de swing trading con filtros TipRanks y portfolio tracker de Forward Testing**

## 🚀 Novedades v5.0

### ✨ Integración TipRanks
- **Entrada manual de datos** desde TipRanks.com
- **Filtros profesionales automáticos**:
  - Smart Score ≥ 8/10
  - Upside ≥ 10%
  - Consenso: Strong Buy o Moderate Buy
- **Modo estricto/permisivo** configurable desde sidebar

### 💼 Portfolio de Forward Testing
- **Capital inicial: $1000**
- Tracking automático de todas las operaciones aprobadas por TipRanks
- Persistencia de datos en archivo JSON
- Gráficos de evolución del capital
- Exportación a CSV para Stock Master

---

## 📋 Requisitos

```bash
pip install -r requirements.txt
```

**Dependencias:**
- streamlit
- pandas
- yfinance
- plotly

---

## 🎯 Cómo Usar

### 1. Iniciar la Aplicación

```bash
python -m streamlit run app.py
```

La app se abrirá en `http://localhost:8501`

### 2. Configurar Sidebar

**🛡️ Gestión de Riesgo:**
- Define tu capital total (default: $1000)
- Ajusta el % de riesgo por operación (default: 2%)

**📊 TipRanks:**
- ✅ **Modo Estricto** (recomendado): Solo permite guardar operaciones que pasen todos los filtros
- ⚠️ **Modo Permisivo**: Permite continuar aunque no se cumplan los filtros

**💼 Forward Testing:**
- ✅ Activa **Tracking Portfolio $1000** para registrar todas las operaciones aprobadas

### 3. Analizar una Acción (Tab 1)

**Paso 1: Análisis Técnico Automático**
1. Ingresa el ticker (ej: AAPL, MSFT, GOOGL)
2. Click en **🔎 ANALIZAR TODO**
3. La app calculará automáticamente:
   - Precio actual
   - Soporte de 20 días
   - Stop Loss (soporte * 0.98)

**Paso 2: Ingresar Datos de TipRanks**

> 💡 **Importante**: Ve a [TipRanks.com](https://www.tipranks.com), busca el ticker y copia los datos manualmente

4. **Smart Score**: Número del 1 al 10 (busca el círculo de colores)
5. **Price Target**: Promedio de precio objetivo de los analistas ("Average Price Target")
6. **Upside**: Se calcula automáticamente
7. **Consenso**: Selecciona el consenso de analistas (Strong Buy, Moderate Buy, Hold, etc.)

**Paso 3: Validación de Filtros**

La app mostrará 3 indicadores:
- ✅ **Verde**: Filtro aprobado
- ❌ **Rojo**: Filtro reprobado

**Criterios de aprobación:**
- Smart Score ≥ 8
- Upside ≥ 10%
- Consenso = Strong Buy o Moderate Buy

#### Ejemplo de Operación Aprobada:

```
✅ Smart Score: 9/10 ✅
✅ Upside: 15.2% ✅
✅ Consenso: Strong Buy ✅

"¡Acción APROBADA por todos los filtros de TipRanks!"
```

#### Ejemplo de Operación Rechazada (Modo Estricto):

```
❌ Smart Score: 5/10 ❌
✅ Upside: 12.5% ✅
❌ Consenso: Hold ❌

"🔒 Modo Estricto Activado: No puedes proceder con esta operación"
```

### 4. Calcular Posición

1. Ajusta el precio de entrada si es necesario
2. Revisa/ajusta el Stop Loss (si tienes "Ajuste manual" activado en sidebar)
3. Click en **💊 CALCULAR POSICIÓN**

La app te mostrará:
- **Número de acciones** a comprar según tu gestión de riesgo
- **Inversión necesaria**
- **Riesgo real** en dólares
- **Niveles de Take Profit** (1:2 y 1:3)
- **Gráfico visual** con todos los niveles marcados

### 5. Guardar la Operación

Si la operación pasa los filtros (o tienes modo permisivo):

1. Click en **💾 GUARDAR EN HISTORIAL**
2. La operación se guardará en:
   - **Tab 2: Historial** (todas las operaciones)
   - **Tab 4: Portfolio $1000** (si tracking está activado)

### 6. Monitorear el Portfolio (Tab 4)

**Métricas principales:**
- Capital Inicial: $1000.00
- Capital Actual: Actualizado con P/L
- ROI: Retorno sobre inversión
- Total Trades: Número de operaciones

**Funciones:**
- 🔄 **Actualizar Precios**: Obtiene precios actuales de Yahoo Finance
- 🔔 **Alertas**: Te avisa cuando una posición está cerca del Stop Loss o Take Profit
- 📈 **Gráfico de Evolución**: Visualiza cómo ha crecido tu capital
- 📥 **Exportar**: Descarga CSV completo o formato Stock Master

**Auto-cierre de operaciones:**
- Si el precio toca el **Stop Loss** → Operación cerrada automáticamente, capital recuperado menos pérdida
- Si el precio toca el **TP 1:2** → Operación cerrada automáticamente, capital recuperado más ganancia

---

## 📊 Workflow Completo de Forward Testing

1. **Buscar ticker** → Tab 1
2. **Consultar TipRanks.com** manualmente
3. **Ingresar datos** en la app
4. **Validar filtros** (deben pasar los 3)
5. **Calcular posición** según gestión de riesgo
6. **Guardar operación** → Se agrega al portfolio de $1000
7. **Ingresar la operación en Stock Master** (app móvil)
8. **Monitorear** en Tab 4 y actualizar precios periódicamente
9. **Analizar resultados** con métricas y gráficos
10. **Exportar reportes** cuando sea necesario

---

## 🗂️ Estructura de Archivos

```
swing-lab/
├── app.py                    # Aplicación principal
├── requirements.txt          # Dependencias Python
├── portfolio_data.json       # Portfolio guardado (auto-generado)
└── README.md                 # Esta documentación
```

**Nota**: `portfolio_data.json` se crea automáticamente al guardar tu primera operación en el portfolio.

---

## 🔧 Configuración Avanzada

### Personalizar Capital Inicial del Portfolio

Edita en `app.py` línea ~27:

```python
if 'portfolio_forward_test' not in st.session_state:
    st.session_state['portfolio_forward_test'] = {
        'capital_inicial': 1000.0,  # ← Cambia este valor
        'capital_actual': 1000.0,
        'trades': []
    }
```

### Ajustar Filtros de TipRanks

Edita la función `validar_filtros_tipranks()` línea ~311:

```python
filtros = {
    'smart_score': {
        'pasa': smart_score >= 8,  # ← Cambia threshold
        ...
    },
    'upside': {
        'pasa': upside >= 10,  # ← Cambia threshold
        ...
    },
    ...
}
```

---

## 💡 Tips Profesionales

### Para Maximizar Resultados:

1. **Usa siempre Modo Estricto**: Esto garantiza que solo operes acciones de alta calidad según TipRanks
2. **No modifiques el Stop Loss**: El soporte de 20 días con 2% de colchón es óptimo para swing trading
3. **Respeta la gestión de riesgo**: Nunca arriesgues más del 2% por operación
4. **Actualiza precios diariamente**: Click en "🔄 Actualizar Precios Portfolio" cada día
5. **Lleva un journal**: Usa la función de exportación para guardar reportes semanales

### Filtros TipRanks - Explicación:

- **Smart Score 8-10**: Alta probabilidad de superar al mercado (basado en algoritmo de TipRanks)
- **Upside ≥ 10%**: Los analistas creen que la acción está subvalorada al menos 10%
- **Consenso Buy**: La mayoría de analistas de Wall Street recomiendan comprar

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named streamlit"
```bash
python -m pip install -r requirements.txt
```

### "No se encontró el ticker"
- Verifica que el símbolo sea correcto (use mayúsculas: AAPL, no aapl)
- Algunos tickers extranjeros pueden no estar en Yahoo Finance

### "El portfolio no se guarda entre sesiones"
- Verifica que exista el archivo `portfolio_data.json` en la carpeta del proyecto
- Revisa permisos de escritura en la carpeta

### Precios no se actualizan
- Verifica conexión a internet
- Yahoo Finance puede tener límites de rate (espera unos segundos)

---

## 📝 Changelog

### v5.0 (2026-01-13)
- ✨ Integración manual de datos TipRanks
- ✨ Filtros profesionales automáticos (Smart Score, Upside, Consensus)
- ✨ Modo estricto/permisivo configurable
- ✨ Portfolio de Forward Testing con $1000 inicial
- ✨ Persistencia de datos en JSON
- ✨ Auto-cierre de operaciones al tocar SL/TP
- ✨ Gráficos de evolución del capital
- ✨ Exportación a CSV compatible con Stock Master
- ✨ Sistema de alertas de proximidad a niveles

### v4.0
- Dashboard de performance
- Auto-actualización de precios
- Gestión de riesgo automática

### v3.0 y anteriores
- Análisis técnico básico
- Cálculo de Stop Loss por soporte
- Ratios 1:2 y 1:3

---

## 📞 Soporte

Para reportar bugs o sugerir mejoras, abre un issue en el repositorio de GitHub.

---

## 📄 Licencia

Este proyecto es de uso personal para forward testing. No constituye asesoría financiera.

---

**¡Feliz Trading! 🚀📈**
