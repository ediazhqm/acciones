import streamlit as st
import yfinance as yf
from yahooquery import Ticker as YQTicker # <-- Importamos la nueva librería
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import re

# === Configuración básica de la página ===
st.set_page_config(page_title="Análisis de Tendencias y Dividendos", page_icon="📈", layout="wide")

st.title("📈 Análisis de Tendencias de Acciones y Dividendos")
st.write("Ingresa los tickers de las acciones, selecciona un rango de fechas y visualiza su rendimiento comparativo junto con sus dividendos anuales.")

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
        with st.spinner("Descargando datos históricos y calculando dividendos..."):
            all_data = []
            dividendos_data = []

            for ticker in tickers_list:
                try:
                    # --- 1. Descarga de Precios con yfinance (Funciona bien para gráficos) ---
                    accion_yf = yf.Ticker(ticker)
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

                    # --- 2. Extracción de Dividendos con YAHOOQUERY (Nueva librería) ---
                    div_rate = "N/A"
                    div_yield_str = "N/A"
                    
                    try:
                        # yq_ticker consulta la info fundamental por otra ruta
                        yq_ticker = YQTicker(ticker)
                        detalles = yq_ticker.summary_detail
                        
                        # yahooquery devuelve un diccionario donde la llave es el ticker
                        if isinstance(detalles, dict) and ticker in detalles:
                            info_accion = detalles[ticker]
                            
                            # Verificamos que no devuelva un string de error (a veces pasa si el ticker no existe)
                            if isinstance(info_accion, dict):
                                div_rate = info_accion.get("dividendRate", "N/A")
                                div_yield = info_accion.get("dividendYield", "N/A")
                                
                                if div_yield != "N/A" and div_yield is not None:
                                    div_yield_str = f"{div_yield * 100:.2f}%"
                                if div_rate is None:
                                    div_rate = "N/A"
                    except Exception as e:
                        # Si yahooquery falla, lo pasamos en silencio
                        pass

                    dividendos_data.append({
                        "Acción": ticker,
                        "Dividendo Anual (Efectivo)": div_rate,
                        "Dividend Yield (%)": div_yield_str
                    })

                except Exception as e:
                    st.error(f"Error grave procesando {ticker}. Revisa el código.")

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

                st.subheader("💰 Resumen de Dividendos Anuales")
                df_dividendos = pd.DataFrame(dividendos_data)
                st.dataframe(df_dividendos, use_container_width=True, hide_index=True)

            else:
                st.error("No se pudieron generar los gráficos. Verifica los tickers y vuelve a intentar.")
