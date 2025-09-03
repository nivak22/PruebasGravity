import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import io
import requests
import json
from datetime import datetime, timedelta

# Título de la aplicación
st.set_page_config(layout="wide")

# API Key de Gemini
API_KEY = "AIzaSyD8uwobgtxctsUzE2Ug7kcR-PtHR48EVIY"

# --- Función de Limpieza de Datos ---
@st.cache_data
def limpiar_y_procesar_datos(df):
    """
    Realiza la limpieza y el preprocesamiento de un DataFrame de ventas.
    """
    # Manejo de valores nulos
    if 'Payment System Name' in df.columns:
        df['Payment System Name'] = df['Payment System Name'].fillna('Desconocido')
    if 'UtmSource' in df.columns:
        df['UtmSource'] = df['UtmSource'].fillna('Desconocido')
    if 'Cancellation Reason' in df.columns:
        df['Cancellation Reason'] = df['Cancellation Reason'].fillna('No cancelado')
    
    # Eliminar columnas con demasiados valores nulos (más del 90%)
    umbral = len(df) * 0.90
    df.dropna(thresh=umbral, axis=1, inplace=True)
    
    # Conversión de tipos de datos
    if 'Creation Date' in df.columns:
        df['Creation Date'] = pd.to_datetime(df['Creation Date'], errors='coerce', utc=True)
    if 'Last Change Date' in df.columns:
        df['Last Change Date'] = pd.to_datetime(df['Last Change Date'], errors='coerce', utc=True)
    
    # Asegurar que las columnas existan antes de la conversión
    if 'Total Value' in df.columns:
        df['Total Value'] = pd.to_numeric(df['Total Value'].astype(str).str.replace(',', '.'), errors='coerce')
    if 'Quantity_SKU' in df.columns:
        df['Quantity_SKU'] = pd.to_numeric(df['Quantity_SKU'].astype(str), errors='coerce')
    if 'Shipping Value' in df.columns:
        df['Shipping Value'] = pd.to_numeric(df['Shipping Value'].astype(str), errors='coerce')
    if 'Discounts Totals' in df.columns:
        df['Discounts Totals'] = pd.to_numeric(df['Discounts Totals'].astype(str), errors='coerce')
    
    # Creación de nuevas características
    if 'Creation Date' in df.columns:
        df['Mes'] = df['Creation Date'].dt.month
        df['Dia_Semana'] = df['Creation Date'].dt.day_name()
        df['Hora'] = df['Creation Date'].dt.hour
    
    return df

# --- Página de Inicio (UX mejorada) ---
def mostrar_pagina_inicio():
    st.markdown("""
        <div style="text-align:center; padding: 50px; background-color: #f0f2f6; border-radius: 10px;">
            <h1 style="color:#2c3e50;">Hola gravity, bienvenidos a la prueba de Nicolás, desarrollador enfocado en marketing</h1>
            <p style="color:#7f8c8d; font-size: 1.2em;">
                Carga tu archivo de ventas (.csv o .xlsx) para comenzar el análisis y generar el dashboard.
            </p>
            <br>
        </div>
        <br><br>
    """, unsafe_allow_html=True)
    
    uploaded_file = st.file_uploader("Carga tu archivo de ventas (.csv o .xlsx)", type=["csv", "xlsx"])
    return uploaded_file

# --- Flujo de la Aplicación ---
def main():
    uploaded_file = mostrar_pagina_inicio()

    if uploaded_file:
        with st.spinner("Limpiando los datos... por favor espera."):
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file, encoding='latin1')
                else:
                    df = pd.read_excel(uploaded_file, sheet_name='Histórico')
                
                df_limpio = limpiar_y_procesar_datos(df.copy())
                
                st.success("Archivo cargado y datos limpios con éxito.")
                st.markdown("---")
                
                mostrar_dashboard(df_limpio)
                
            except Exception as e:
                st.error(f"Ocurrió un error al procesar el archivo: {e}")
                st.warning("Asegúrate de que el archivo sea del tipo correcto (.csv o .xlsx) y de que la hoja de cálculo de un archivo .xlsx se llame 'Histórico'.")

def mostrar_dashboard(df):
    
    # --- Título del Dashboard ---
    st.header("Dashboard de Métricas de Ventas")

    # --- Filtros Interactivos (Mejorados) ---
    st.sidebar.header("Filtros")
    
    df['Creation Date'] = pd.to_datetime(df['Creation Date'])
    
    min_date_df = pd.to_datetime(df['Creation Date'].min()).date()
    max_date_df = pd.to_datetime(df['Creation Date'].max()).date()
    
    start_date, end_date = st.sidebar.date_input(
        'Selecciona un rango de fechas',
        value=(min_date_df, max_date_df),
        min_value=min_date_df,
        max_value=max_date_df
    )
    
    filtered_df = df[
        (df['Creation Date'].dt.date >= start_date) &
        (df['Creation Date'].dt.date <= end_date)
    ].copy()

    # --- Métricas Clave (KPIs) ---
    total_ventas = filtered_df['Total Value'].sum() if 'Total Value' in filtered_df.columns else 0
    total_unidades = filtered_df['Quantity_SKU'].sum() if 'Quantity_SKU' in filtered_df.columns else 0
    total_ordenes = filtered_df['Order'].nunique()

    col1, col2, col3 = st.columns(3)
    col1.metric("Ventas Totales", f"{total_ventas:,.2f} COP")
    col2.metric("Unidades Vendidas", f"{total_unidades:,.0f}")
    col3.metric("Órdenes Únicas", f"{total_ordenes}")
    
    st.markdown("---")

    # --- Gráficos del Dashboard ---

    # Pregunta 1: ¿En 2021 qué mes fue el que vendió más dinero? ¿Y más unidades?
    st.subheader("1 y 2. Análisis de Ventas por Mes")
    st.markdown("### ¿En qué mes se vendió más dinero? ¿Y más unidades?")
    ventas_por_mes = filtered_df.resample('M', on='Creation Date').agg(
        total_dinero=('Total Value', 'sum'),
        total_unidades=('Quantity_SKU', 'sum')
    ).reset_index()

    fig_mes = go.Figure()
    fig_mes.add_trace(go.Bar(x=ventas_por_mes['Creation Date'], y=ventas_por_mes['total_dinero'],
                            name='Ventas (Dinero)', yaxis='y1'))
    fig_mes.add_trace(go.Scatter(x=ventas_por_mes['Creation Date'], y=ventas_por_mes['total_unidades'],
                                mode='lines+markers', name='Ventas (Unidades)', yaxis='y2'))
    
    fig_mes.update_layout(
        title="Ventas Mensuales (Dinero y Unidades)",
        xaxis_title="Mes",
        yaxis=dict(title="Ventas (COP)", side="left"),
        yaxis2=dict(title="Unidades", overlaying="y", side="right")
    )
    st.plotly_chart(fig_mes, use_container_width=True)
    
    if not ventas_por_mes.empty:
        mes_mas_dinero = ventas_por_mes.loc[ventas_por_mes['total_dinero'].idxmax()]
        mes_mas_unidades = ventas_por_mes.loc[ventas_por_mes['total_unidades'].idxmax()]
        st.info(f"**Respuesta:** El mes que más vendió en dinero fue **{mes_mas_dinero['Creation Date'].strftime('%B')}** y el mes que más vendió en unidades fue **{mes_mas_unidades['Creation Date'].strftime('%B')}**.")
    
    st.markdown("---")
    
    # Pregunta 3: ¿cuál fue el top 5 de productos en dinero y en unidades?
    st.subheader("3. Top 5 de Productos")
    col_top1, col_top2 = st.columns(2)
    with col_top1:
        st.markdown("### Top 5 Productos por Dinero")
        top_dinero = filtered_df.groupby('SKU Name')['Total Value'].sum().nlargest(5)
        fig_dinero = px.bar(top_dinero, x=top_dinero.values, y=top_dinero.index, orientation='h',
                            labels={'x': 'Ventas Totales (COP)', 'y': 'Producto'},
                            title='Top 5 Productos por Ventas (COP)')
        st.plotly_chart(fig_dinero, use_container_width=True)
        st.info(f"**Respuesta:** El top 5 de productos por dinero es:\n{top_dinero.to_markdown()}")
    
    with col_top2:
        st.markdown("### Top 5 Productos por Unidades")
        top_unidades = filtered_df.groupby('SKU Name')['Quantity_SKU'].sum().nlargest(5)
        fig_unidades = px.bar(top_unidades, x=top_unidades.values, y=top_unidades.index, orientation='h',
                            labels={'x': 'Unidades Vendidas', 'y': 'Producto'},
                            title='Top 5 Productos por Unidades')
        st.plotly_chart(fig_unidades, use_container_width=True)
        st.info(f"**Respuesta:** El top 5 de productos por unidades es:\n{top_unidades.to_markdown()}")
    
    st.markdown("---")

    # Pregunta 4: ¿cuántas órdenes únicas tenemos en el año?
    st.subheader("4. Órdenes Únicas")
    st.markdown("### ¿Cuántas órdenes únicas tenemos en el año?")
    st.info(f"**Respuesta:** El número de órdenes únicas en el período seleccionado es de **{total_ordenes}**.")
    
    st.markdown("---")

    # Pregunta 5: ¿cuál es la ciudad que más vende por dinero y por unidades, y cuánto representa del total?
    st.subheader("5. Análisis de Ciudades")
    st.markdown("### ¿Cuál es la ciudad que más vende por dinero y por unidades?")
    col_city_chart, col_city_info = st.columns(2)
    with col_city_chart:
        ventas_ciudad = filtered_df.groupby('City').agg(
            total_dinero=('Total Value', 'sum'),
            total_unidades=('Quantity_SKU', 'sum')
        ).sort_values(by='total_dinero', ascending=False)
        
        fig_ciudad = px.bar(ventas_ciudad.head(10), x=ventas_ciudad.head(10).index, y='total_dinero',
                            labels={'x': 'Ciudad', 'total_dinero': 'Ventas (COP)'},
                            title='Top 10 Ciudades por Ventas')
        st.plotly_chart(fig_ciudad, use_container_width=True)
    with col_city_info:
        if not ventas_ciudad.empty:
            total_ventas_all = ventas_ciudad['total_dinero'].sum()
            ventas_ciudad['Porcentaje'] = (ventas_ciudad['total_dinero'] / total_ventas_all) * 100
            top_city = ventas_ciudad.iloc[0]
            st.info(f"**Respuesta:** La ciudad que más vende es **{top_city.name}**, con un total de **{top_city['total_dinero']:,.2f} COP**, lo que representa el **{top_city['Porcentaje']:.2f}%** del total.")
    
    st.markdown("---")

    # Pregunta 6: ¿Cuál es la categoría/departamento que más se vende?
    st.subheader("6. Análisis por Categoría")
    st.markdown("### ¿Cuál es la categoría/departamento que más se vende?")
    ventas_categoria = filtered_df.groupby('Category Ids Sku').agg(
        total_dinero=('Total Value', 'sum'),
        total_unidades=('Quantity_SKU', 'sum')
    ).sort_values(by='total_dinero', ascending=False)
    
    fig_categoria = px.bar(ventas_categoria.head(10), x=ventas_categoria.head(10).index, y='total_dinero',
                            labels={'x': 'Categoría', 'total_dinero': 'Ventas (COP)'},
                            title='Top 10 Categorías por Ventas')
    st.plotly_chart(fig_categoria, use_container_width=True)
    if not ventas_categoria.empty:
        top_category = ventas_categoria.iloc[0]
        st.info(f"**Respuesta:** La categoría que más vendió es **{top_category.name}**.")

    st.markdown("---")

    # Pregunta 7: ¿Cómo se han movido a través del tiempo la venta de los productos?
    st.subheader("7. Tendencia de Ventas")
    st.markdown("### ¿Cómo se han movido a través del tiempo la venta de los productos?")
    fig_tiempo = px.line(filtered_df.sort_values('Creation Date'), x='Creation Date', y='Total Value', 
                        labels={'Creation Date': 'Fecha', 'Total Value': 'Ventas (COP)'},
                        title="Movimiento de Ventas a lo Largo del Tiempo")
    fig_tiempo.update_traces(hovertemplate='Fecha: %{x|%Y-%m-%d}<br>Ventas: %{y:,.2f} COP')
    st.plotly_chart(fig_tiempo, use_container_width=True)
    st.info("**Respuesta:** El gráfico de líneas muestra los picos y valles de las ventas a lo largo del tiempo, permitiendo identificar la tendencia de venta de los productos.")
    
    st.markdown("---")

    # Pregunta 8: ¿Cuál es el medio de pago más utilizado en las transacciones?
    # Pregunta 9: ¿Por UTM source cuál es la más representativa de cara a las ventas?
    st.subheader("8 y 9. Análisis de Pagos y Tráfico")
    col_ad1, col_ad2 = st.columns(2)
    with col_ad1:
        st.markdown("### ¿Cuál es el medio de pago más utilizado?")
        pago_counts = filtered_df['Payment System Name'].value_counts()
        fig_pago = px.pie(pago_counts, values=pago_counts.values, names=pago_counts.index, 
                          title='Distribución de Medios de Pago')
        st.plotly_chart(fig_pago, use_container_width=True)
        if not pago_counts.empty:
            st.info(f"**Respuesta:** El medio de pago más utilizado es **{pago_counts.index[0]}**.")
        
    with col_ad2:
        st.markdown("### ¿Cuál es el UTM source más representativo?")
        utm_sales = filtered_df.groupby('UtmSource')['Total Value'].sum()
        fig_utm = px.pie(utm_sales, values=utm_sales.values, names=utm_sales.index, 
                         title='Ventas por UTM Source')
        st.plotly_chart(fig_utm, use_container_width=True)
        if not utm_sales.empty:
            st.info(f"**Respuesta:** El UTM Source más representativo es **{utm_sales.idxmax()}**.")

    st.markdown("---")

    # Pregunta 10: ¿Cuál es el día de la semana que más vende?
    # Pregunta 11: ¿En qué horas se vende más o menos?
    st.subheader("10 y 11. Análisis de Horarios y Días")
    col_horas, col_dias = st.columns(2)
    with col_dias:
        st.markdown("### ¿Cuál es el día de la semana que más vende en dinero y en unidades?")
        ventas_dia = filtered_df.groupby('Dia_Semana').agg(
            total_dinero=('Total Value', 'sum'),
            total_unidades=('Quantity_SKU', 'sum')
        ).reset_index()
        orden_dias = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        ventas_dia['Dia_Semana'] = pd.Categorical(ventas_dia['Dia_Semana'], categories=orden_dias, ordered=True)
        ventas_dia = ventas_dia.sort_values('Dia_Semana')
        
        fig_dia = px.bar(ventas_dia, x='Dia_Semana', y='total_dinero',
                        labels={'Dia_Semana': 'Día de la Semana', 'total_dinero': 'Ventas (COP)'},
                        title='Ventas por Día de la Semana')
        st.plotly_chart(fig_dia, use_container_width=True)
        if not ventas_dia.empty:
            dia_mas_dinero = ventas_dia.loc[ventas_dia['total_dinero'].idxmax()]
            dia_mas_unidades = ventas_dia.loc[ventas_dia['total_unidades'].idxmax()]
            st.info(f"**Respuesta:** El día que más vendió en dinero fue **{dia_mas_dinero['Dia_Semana']}** y el día que más vendió en unidades fue **{dia_mas_unidades['Dia_Semana']}**.")
    
    with col_horas:
        st.markdown("### ¿En qué horas se vende más o menos?")
        ventas_hora = filtered_df.groupby('Hora').agg(
            total_dinero=('Total Value', 'sum'),
            total_unidades=('Quantity_SKU', 'sum')
        ).reset_index()
        
        fig_hora = px.bar(ventas_hora, x='Hora', y='total_dinero',
                        labels={'Hora': 'Hora del Día', 'total_dinero': 'Ventas (COP)'},
                        title='Ventas por Hora del Día')
        st.plotly_chart(fig_hora, use_container_width=True)
        if not ventas_hora.empty:
            hora_mas_venta = ventas_hora.loc[ventas_hora['total_dinero'].idxmax()]
            hora_menos_venta = ventas_hora.loc[ventas_hora['total_dinero'].idxmin()]
            st.info(f"**Respuesta:** El pico de ventas se da en la **hora {hora_mas_venta['Hora']}** y la venta mínima es en la **hora {hora_menos_venta['Hora']}**.")

    st.markdown("---")
    
    # Pregunta 12: ¿Qué acciones podrías recomendar para aumentar la venta de productos, categorías, ciudades?
    st.subheader("12. Recomendaciones Estratégicas")
    st.markdown("### ¿Qué acciones podrías recomendar para aumentar la venta de productos, categorías y ciudades?")
    st.info("""
    * **Productos:** Enfócate en campañas para los productos del Top 5, como el Televisor Android o las Neveras.
    * **Ciudades:** Invierte en publicidad digital segmentada para Bogotá y las ciudades en el Top 10 para maximizar el retorno de inversión.
    * **Marketing:** Dado que Google es la fuente más efectiva, optimiza tus campañas de Google Ads y SEO para atraer más clientes.
    * **Horarios:** Lanza promociones o contenido en redes sociales en las horas pico de venta para captar la atención de los usuarios.
    """)

    # Pregunta 13: Sección de IA
    st.markdown("---")
    st.subheader("13. Análisis de Inteligencia Artificial")
    st.info("Haz una pregunta sobre los datos y la IA de Gemini la analizará.")

    user_query = st.text_input("Haz tu pregunta:")

    if st.button("Analizar"):
        if not API_KEY:
            st.warning("Para usar la IA, necesitas una API Key de Gemini válida.")
        elif not user_query:
            st.error("Por favor, ingresa una pregunta.")
        else:
            with st.spinner("Analizando con IA..."):
                url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-05-20:generateContent?key={API_KEY}"
                
                # Construir el prompt con los datos del DataFrame
                prompt = f"""
                Eres un analista de datos experto. Analiza el siguiente conjunto de datos de ventas en formato de tabla para responder a la pregunta del usuario. Los datos tienen las siguientes columnas y su descripción:
                - Order: ID único de la orden.
                - Creation Date: Fecha y hora de creación de la orden.
                - City: Ciudad de la orden.
                - Total Value: Valor total de la orden en COP.
                - Quantity_SKU: Cantidad de unidades vendidas.
                - SKU Name: Nombre del producto.
                - Payment System Name: Medio de pago utilizado.
                - UtmSource: Fuente de marketing de la que provino el cliente.
                
                Datos de ventas (primeras 50 filas):
                {filtered_df.head(50).to_markdown(index=False)}
                
                Pregunta del usuario: {user_query}
                """
                
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "tools": [{"google_search": {}}]
                }
                
                headers = {'Content-Type': 'application/json'}
                
                try:
                    response = requests.post(url, headers=headers, data=json.dumps(payload))
                    response.raise_for_status()
                    result = response.json()
                    
                    ai_response = result['candidates'][0]['content']['parts'][0]['text']
                    st.markdown(f"**Respuesta de la IA:** {ai_response}")
                    
                except requests.exceptions.RequestException as e:
                    st.error(f"Error al conectar con la API de Gemini: {e}")
                except KeyError:
                    st.error("La respuesta de la API no tiene el formato esperado. Intenta con otra pregunta.")

# Seccion principal
if __name__ == "__main__":
    main()
