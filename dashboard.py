import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import re

# === Configuración básica de la página ===
st.set_page_config(page_title="Análisis de Tendencias y Dividendos", page_icon="📈", layout="wide")

st.title("📈 Análisis de Tendencias de Acciones y Dividendos")
st.write("Ingresa los tickers de las acciones, selecciona un rango de fechas y visualiza su rendimiento comparativo.")

# === 1. Barra Lateral para Inputs ===
with st.sidebar:
    st.header("Parámetros de Análisis")
    
    tickers_input = st.text_area(
        "Códigos de acciones (separados por coma o salto de línea):",
        "BAP\nBBVA.MC\nMO\nPFE"
    )
    
    hoy = datetime.today()
    hace_un_ano = hoy - timedelta(days=365)
    
    fecha_inicio = st.date_input("Fecha Inicial", value=hace_un_ano)
    fecha_fin = st.date_input("Fecha Final", value=hoy)
    
    analizar_btn = st.button("Analizar Rendimiento", type="primary")

# === 2. Lógica Principal ===
if analizar_btn:
    tickers_list = [t.strip().upper() for t in re.split(r'[,\n]+', tickers_input) if t.strip()]
    
    if not tickers_list:
        st.warning("Por favor, ingresa al menos un código de acción.")
    elif fecha_inicio >= fecha_fin:
        st.error("La fecha inicial debe ser menor a la fecha final.")
    else:
        with st.spinner("Descargando historial y calculando dividendos manualmente..."):
            all_data = []
            dividendos_data = []

            for ticker in tickers_list:
                try:
                    accion_yf = yf.Ticker(ticker)
                    
                    # --- 1. Descarga de Precios (Para el gráfico) ---
                    data = accion_yf.history(start=fecha_inicio, end=fecha_fin)

                    if not data.empty and "Close" in data.columns:
                        serie = data["Close"].dropna()
                        
                        if not serie.empty:
                            precio_ini = float(serie.iloc[0])
                            variacion = ((serie - precio_ini) / precio_ini) * 100
                            
                            variacion_df = variacion.reset_index()
                            variacion_df.columns = ['Date', 'Variacion_Pct']
                            variacion_df['Date'] = pd.to_datetime(variacion_df['Date']).dt.tz_localize(None)
                            variacion_df['Accion'] = ticker
                            all_data.append(variacion_df)
                    else:
                        st.warning(f"No se encontraron precios para {ticker}.")

                    # --- 2. Cálculo Manual de Dividendos (Vía Historial, a prueba de bloqueos) ---
                    # Descargamos exactamente el último año para sumar los dividendos pagados (TTM)
                    data_1y = accion_yf.history(period="1y")
                    
                    div_rate = "N/A"
                    div_yield_str = "N/A"
                    
                    if not data_1y.empty and "Dividends" in data_1y.columns and "Close" in data_1y.columns:
                        # Sumar todos los dividendos pagados en los últimos 12 meses
                        total_dividendos_1y = data_1y["Dividends"].sum()
                        
                        # Obtener el último precio de cierre disponible
                        precio_actual = data_1y["Close"].iloc[-1]
                        
                        if total_dividendos_1y > 0 and precio_actual > 0:
                            div_rate = f"{total_dividendos_1y:.2f}"
                            # Calculamos el Yield: (Dividendos totales / Precio actual) * 100
                            div_yield = (total_dividendos_1y / precio_actual) * 100
                            div_yield_str = f"{div_yield:.2f}%"
                        else:
                            div_rate = "0.00"
                            div_yield_str = "0.00%"

                    dividendos_data.append({
                        "Acción": ticker,
                        "Div. Pagado Último Año": div_rate,
                        "Dividend Yield Calculado (%)": div_yield_str
                    })

                except Exception as e:
                    st.error(f"Error procesando {ticker}.")

            # === 3. Visualización de Resultados ===
            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)

                st.subheader("📊 Variación Porcentual de las Acciones")
                fig = px.line(
                    combined_df, 
                    x='Date', 
                    y='Variacion_Pct', 
                    color='Accion',
                    labels={"Date": "Fecha", "Variacion_Pct": "Variación (%)", "Accion": "Ticker"}
                )
                
                fig.update_layout(
                    hovermode="x unified",
                    xaxis_title="Fecha",
                    yaxis_title="Variación (%)",
                    margin=dict(l=0, r=0, t=30, b=0)
                )
                st.plotly_chart(fig, use_container_width=True)

                st.subheader("💰 Resumen de Dividendos (Basado en historial de 1 año)")
                df_dividendos = pd.DataFrame(dividendos_data)
                st.dataframe(df_dividendos, use_container_width=True, hide_index=True)

            else:
                st.error("No se pudieron generar los gráficos.")
