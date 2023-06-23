from pulp import *
import pandas as pd
from openpyxl import load_workbook, Workbook
import re
import plotly.graph_objs as go
from plotly.subplots import make_subplots
import plotly.express as px
import streamlit as st
from st_aggrid import AgGrid, GridUpdateMode, JsCode
from st_aggrid.grid_options_builder import GridOptionsBuilder

st.title('Compra en Oportunidad') # Diseño

data_file = st.file_uploader("Upload XLSX", type=["XLSX"]) # Diseño

if data_file is not None:
    
    df_input = pd.read_excel(r"Input.xlsx",sheet_name="Semanas") # Se importan datos
    precio3=pd.read_excel(r"Input.xlsx",sheet_name="Precios")
    demanda3=pd.read_excel(r"Input.xlsx",sheet_name="Demanda")
    data=[df_input,precio3,demanda3]
    
    st.subheader('Demanda y Precios por Semana') # Diseño
    st.write(data[0]) #Diseño
    
    # Creación de Conjuntos

    semanas= list(data[0]['Semanas'].unique())
    materiales = list(str(i) for i in data[0].Material.unique().tolist())
    
    # Parametros Precios
    
    precios2 = data[1].values.tolist()
    precios = makeDict([semanas, materiales],precios2,0)
    
    # Parametros Demanda
    
    demanda2 = data[2].values.tolist()
    demanda = makeDict([semanas, materiales],demanda2,0)
    
    
    # Definimos los valores por defecto de los parámetros
    
    # inventarioInicial = 1140000 #kg
    inventarioMaximo = 25 # semanas #Buscar Equilibrio, para que no sea infactible 
    inventarioMinimo = 2 # semanas #Buscar Equilibrio, para que no sea infactible 
    costoKgInventario_INI = 5661 #$/kg
    CostoCapitalNM = 0.22 #tasa porcentaje 
    costoAlmacenamiento_valor = 270 # $/kg mes
    CostoTransporte_valor = 50 # $/kg 
    
    # Clase main (Principal), posible clase frontend
    
    # Clase Modelo (Variables restricciones)
    
    mod_co = LpProblem("Compra Oportunidad", LpMinimize)
    
    
    # Variables Obligatorias
    
    Compra = LpVariable.dicts("Compra",[(s,m) for s in semanas for m in materiales ],0, None)
    Inventario = LpVariable.dicts("Inventario",[(s,m) for s in semanas for m in materiales ],0, None) 
    CostoTotal = LpVariable.dicts("CostoTotal",[(s,m) for s in semanas for m in materiales ],0, None)
    
    # Función Objetivo

    mod_co += lpSum(CostoTotal[(s,m)] for s in semanas for m in materiales)
    
    # Restricciones Obligatorias
    
    # Cumplir la demanda
    
    for m in materiales:
        for s in semanas:
            mod_co += Inventario[(s,m)]  >= demanda[s][m]
            
    # Juego de Inventarios
    
    inventarioInicial = st.slider("Inventario Inicial", 0, 2000000, 1140000)

    cont=-1
    #Inventario[(semanas[cont],m)]indica el inventario de la semana pasada
    for m in materiales:
        for s in semanas:
            if s == semanas[0]:
                mod_co += Inventario[(s,m)]  == inventarioInicial + Compra[(s,m)]  - demanda[s][m]
            else:
                mod_co += Inventario[(s,m)]  == Inventario[(semanas[cont],m)] + Compra[(s,m)]  - demanda[s][m] 
            cont=cont+1
        
    
    # Valores Positivos
    
    for s in semanas:
        mod_co += lpSum([Compra[(s,m)] for m in materiales ])  >= 0

    for s in semanas:
        mod_co += lpSum([Inventario[(s,m)] for m in materiales ])  >= 0


        # Frontend
    def generar_interfaz_opciones_restriccion(restricciones):
        st.sidebar.title("Opciones de restricción")
        # st.sidebar.caption("Elige las restricciones que deseas incluir en el modelo.")
        for restriccion in restricciones:
            restricciones[restriccion] = st.sidebar.checkbox(f"Incluir {restriccion}", value=True)
        return restricciones

    # Creamos un diccionario para almacenar las restricciones
    restricciones = {
        "Politica Inventario Máximo y Mínimo": True,
        "Costo de los Inventarios": True,
        "Costo de Transporte": True
    }
    
        
    # Creamos la interfaz de usuario con Streamlit, para encender o no restricciones 
    restricciones = generar_interfaz_opciones_restriccion(restricciones)
    
    if restricciones["Politica Inventario Máximo y Mínimo"]:
        
        inventarioMaximo = st.slider("Inventario Máximo", 0, 120, 20)
        inventarioMinimo = st.slider("Inventario Minimo", 2, 40, 2)
        LeadTime = st.slider("Lead Time", 2, 40, 1)
        
        

        # Cumplir con politicas de Inventario

        for m in materiales:
            for s in semanas:
                mod_co += Inventario[(s,m)]  <= demanda[s][m]*inventarioMaximo

        for m in materiales:
            for s in semanas:
                mod_co += Inventario[(s,m)] >= demanda[s][m]*inventarioMinimo

        
        
    if restricciones["Costo de los Inventarios"] == True:
        
        costoKgInventario_INI = st.slider("Costo por Kg del Inventario", 0, 10000, 800)
        
        CostoInventario = LpVariable.dicts("CostoInventario",[(s,m) for s in semanas for m in materiales ],0, None)
        
        cont=-1
        for m in materiales:
            for s in semanas:
                if s == semanas[0]:
                    mod_co += CostoInventario[(s,m)]  ==(((inventarioInicial-demanda[s][m]) * costoKgInventario_INI) +(Compra[(s,m)]*precios[s][m])) 
                else:
                    mod_co += CostoInventario[(s,m)]  == (((Inventario[(semanas[cont],m)] -demanda[s][m]) * costoKgInventario_INI) +(Compra[(s,m)]*precios[s][m])) # /2
                cont=cont+1
            

        
    # if restricciones["Costo de Almacenamiento y Capital"]:
        
        costoAlmacenamiento_valor = st.slider("Costo Almacenamiento", 0, 1000, 270)
        
        CostoAlmacenamiento = LpVariable.dicts("CostoAlmacenamiento",[(s,m) for s in semanas for m in materiales ],0, None)
        
        # Costo de almacenamiento

        for m in materiales:
            for s in semanas:
                mod_co += CostoAlmacenamiento[(s,m)] == demanda[s][m]*inventarioMinimo* costoAlmacenamiento_valor
            
        
    # if restricciones["Costo de Capital"]:
        
        CostoCapitalNM = st.slider("Costo Capital", 0.0, 1.0, 0.22)
        
        CostoCapital = LpVariable.dicts("CostoCapital",[(s,m) for s in semanas for m in materiales ],0, None)
        
        # Costo de Capital

        for m in materiales:
            for s in semanas:
                mod_co += CostoCapital[(s,m)] == CostoInventario[(s,m)] * CostoCapitalNM

        
    if restricciones["Costo de Transporte"]:
        
        CostoTransporte_valor = st.slider("Costo Transporte", 0, 500, 50)
        
        CostoTransporte = LpVariable.dicts("CostoTransporte",[(s,m) for s in semanas for m in materiales ],0, None)
        

        for m in materiales:
            for s in semanas:
                mod_co += CostoTransporte[(s,m)] == Compra[(s,m)] * CostoTransporte_valor
        

    for m in materiales:
        for s in semanas:
            if restricciones["Costo de los Inventarios"] and restricciones["Costo de Transporte"]:
                mod_co += CostoTotal[(s,m)] == CostoInventario[(s,m)] + CostoAlmacenamiento[(s,m)] + CostoCapital[(s,m)] + CostoTransporte[(s,m)] # + Compra[(s,m)]*precios[s][m]
            elif restricciones["Costo de Transporte"]:
                mod_co += CostoTotal[(s,m)] == CostoTransporte[(s,m)] + Compra[(s,m)]*precios[s][m]
            elif restricciones["Costo de los Inventarios"]:
                mod_co += CostoTotal[(s,m)] == CostoInventario[(s,m)] + CostoAlmacenamiento[(s,m)] + CostoCapital[(s,m)] # + Compra[(s,m)]*precios[s][m]
            else:
                mod_co += CostoTotal[(s,m)] == Compra[(s,m)]*precios[s][m]
        
    
    # SOLVE

    mod_co.solve(solver = pulp.PULP_CBC_CMD(msg=True, threads=8, warmStart=True, timeLimit=260000, cuts=True, strong=True, presolve=True, gapRel=0.01))
    
    # Estatus Solución
    st.subheader('Resultados de la Optimización')
    
    # dos columnas para los resultados de la optimización
    col0, col1 = st.columns(2)
    
    status = LpStatus[mod_co.status]
    # st.write("Status:", status)
    col0.metric("Estado de la optimización: ", ("Óptimo" if status =="Optimal" else "Inviable"))
    # st.write("Costo Total = ", "${:,.0f}".format(value(mod_co.objective)),  size=50)
    col1.metric("Costo Total: ", "${:,.0f}".format(value(mod_co.objective)))
    
    Resultados2 = []
    i=0
    for v in mod_co.variables():
        variable = re.findall(r"(\w+)_",v.name)[0]
        semana = re.findall(r"(\w+)',",v.name)[0]
        codigo= re.findall(r"s*'(\d+)'",v.name)[0]
        demanda = demanda2[i][0]
        precios = precios2[i][0]
        i+=1
        if i == len(demanda2):
            i=0
        Resultados2.append({"Variable": variable, "Semana": semana, "Codigo": codigo, "Valor":v.varValue, "Demanda":demanda,"Precios":precios})
    
    Resultado = pd.DataFrame(Resultados2)
        
    df_pivot = Resultado.pivot(index=['Semana', 'Codigo'], columns='Variable', values='Valor').reset_index()
    for i in list(df_pivot.columns)[2:]:
        df_pivot[i] = df_pivot[i].apply(lambda x: int('{:.0f}'.format(x)))
    
    st.write(df_pivot)
    
    def convert_df(df):
        return df.to_csv(index=False).encode('utf-8')
    
    csv = convert_df(df_pivot)
    
    st.download_button(
   "Presiona para descargar",
   csv,
   "file.csv",
   "text/csv",
   key='download-csv')
    
    # Creación del Grafico 
    
    st.subheader('Momentos de Compra vs Demanda, Inventario y Precios 📈')
    st.write("En esta gráfica puedes visualizar los momentos óptimos para realizar la compra, junto con el comportamiento de los inventarios, la demanda y los precios.")
    
    
    Resultado_Compras = Resultado[Resultado['Variable']=="Compra"]
    Resultado_Inventario = Resultado[Resultado['Variable']=="Inventario"]
    Resultado_CostoTotal = Resultado[Resultado['Variable']=="CostoTotal"]
    
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(x=Resultado_Compras['Semana'], y=Resultado_Compras['Valor'], name='Compras'))

    fig.add_trace(go.Scatter(x=Resultado_Inventario['Semana'], y=Resultado_Inventario['Valor'], 
                             name='Inventario', mode='lines', line=dict(color='red'), legendrank=True))
    
    fig.add_trace(go.Scatter(x=Resultado_Compras['Semana'], y=Resultado_Compras['Demanda'], 
                             name='Demanda', mode='lines', line=dict(color='green'), legendrank=True))

    fig.add_trace(go.Scatter(x=Resultado_Compras['Semana'], y=Resultado_Compras['Precios'], 
                             name='Precios', mode='lines', line=dict(color='orange'), legendrank=True), secondary_y=True)
    
#     fig.add_trace(go.Scatter(x=Resultado_CostoTotal['Semana'], y=Resultado_CostoTotal['Valor'], 
#                              name='Costo Total', mode='markers', line=dict(color='purple'), legendrank=True), secondary_y=True)
    
#     if restricciones["Costo de los Inventarios"] :
        
#         Resultado_CostoAlmacenamiento = Resultado[Resultado['Variable']=="CostoAlmacenamiento"]
#         Resultado_CostoInventario = Resultado[Resultado['Variable']=="CostoInventario"]
#         Resultado_CostoCapital = Resultado[Resultado['Variable']=="CostoCapital"]
        
#         fig.add_trace(go.Scatter(x=Resultado_CostoAlmacenamiento['Semana'], y=Resultado_CostoAlmacenamiento['Valor'], 
#                                  name='Costo Almacenamiento', mode='lines', line=dict(color='grey'), legendrank=True), secondary_y=True)

#         fig.add_trace(go.Scatter(x=Resultado_CostoInventario['Semana'], y=Resultado_CostoInventario['Valor'], 
#                                  name='Costo Inventario', mode='markers', line=dict(color='pink'), legendrank=True), secondary_y=True)

#         fig.add_trace(go.Scatter(x=Resultado_CostoCapital['Semana'], y=Resultado_CostoCapital['Valor'], 
#                                  name='Costo Capital', mode='markers', line=dict(color='brown'), legendrank=True), secondary_y=True)
    
#     if restricciones["Costo de Transporte"]:

#         Resultado_CostoTransporte = Resultado[Resultado['Variable']=="CostoTransporte"]


#         fig.add_trace(go.Scatter(x=Resultado_CostoTransporte['Semana'], y=Resultado_CostoTransporte['Valor'], 
#                                  name='Costo Transporte', mode='markers', line=dict(color='gold'), legendrank=True), secondary_y=True)


    fig.update_layout(title='Compra de Oportunidad',
                      xaxis=dict(title='Semana'),
                      yaxis=dict(title='Unidades'),
                      yaxis2=dict(title='Precios', overlaying='y', side='right'),
                     legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                ))

    st.write(fig)
    
    # Definir Gráficos de datos acumulados
    
    columnasAcumular = df_pivot.columns[2:]
    
    df_pivot2 = df_pivot.copy()
    
    for i in columnasAcumular:
        df_pivot2[f'{i}Acumulado']= df_pivot2[i].cumsum()
    
    # df_pivot2 = df_pivot2.filter(like='Acumulado')
    
    df_melted = pd.melt(df_pivot2, id_vars='Semana', value_vars=df_pivot2.filter(like='Acumulado').columns)
    
    # Graficar Costo total acumulado
    # fig = go.Figure()
    # fig.add_trace(go.bar(name="Costo Total Acumulado",x = df_melted[df_melted.Variable == 'CostoTotalAcumulado'], y=df_melted[df_melted.Variable == 'CostoTotalAcumulado']['value']))
    
    st.subheader('Costos Acumulados 💰')
    
    
    fig = px.bar(df_melted[df_melted.Variable == 'CostoTotalAcumulado'], x='Semana', y='value', color='Variable', barmode='stack', text_auto='$,.0f')
    
    fig.update_traces(textfont_size=50, textangle=90, textposition="inside", cliponaxis=False)
    
    fig.update_traces(name='Costo total acumulado', textfont_size=50, textangle=90, textposition="inside", cliponaxis=False)
    
    fig.update_layout(title='Acumulado del Costo Total',
                  xaxis=dict(title='Semana'),
                  yaxis=dict(title='Moneda'),
                     legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ))
    
    st.write(fig)
    
    df_melted['Variable'] = df_melted['Variable'].str.replace('([a-z])([A-Z])', r'\1 \2')
    
    csv = convert_df(df_pivot2)
    
    st.download_button(
   "Presiona para descargar el resultado con las variables acumuladas",
   csv,
   "file.csv",
   "text/csv",
   key='download-csv2')
    
    if restricciones["Costo de los Inventarios"] or restricciones["Costo de Transporte"]:

        fig = px.bar(df_melted[~df_melted['Variable'].isin([
            'Costo Total Acumulado',
            'CostoTotalAcumulado',
            'Compra Acumulado',
            'Inventario Acumulado'])]
                        , x='Semana', y='value', color='Variable', barmode='stack', text_auto='$,.0f')


        fig.update_layout(title='Composición del Costo',
                      xaxis=dict(title='Semana'),
                      yaxis=dict(title='Moneda'),
                         legend=dict(
                            orientation="h",
                            yanchor="bottom",
                            y=1.02,
                            xanchor="right",
                            x=0.71
                        ))

        st.write(fig)

        st.write(demanda[0])
        



  
        
    
    
