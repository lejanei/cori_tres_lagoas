import streamlit as st
import pandas as pd
import plotly.express as px
import sqlalchemy as sa
import pyodbc
import datetime as dt
import plotly.graph_objects as go

# Configuração do Banco de Dados
engine = sa.create_engine(r'mysql+pymysql://ljsyst02_adm:vinimalu121924@ljsystem.com.br/ljsyst02_Cori_Iot')

conn = engine.connect()


df = pd.read_sql('SELECT * FROM tbl_oee_moinho', conn)

# Streamlit

st.set_page_config(layout='wide')
st.title("Cori Ingredientes Três Lagoas")


st.sidebar.markdown("**Cori 3 Lagoas**",)
st.sidebar.divider()

df['data'] = pd.to_datetime(df['inicio'])
df = df.sort_values("data")

#df['year'] = df['data'].apply(lambda x: str(x.year) )
#df['month'] = df['data'].apply(lambda x: str(x.month) )
df['year'] = df['data'].dt.to_period('Y')
df['month'] = df['data'].dt.to_period('M')

#### FILTROS DO SIDEBAR ####
linha = st.sidebar.multiselect("Linha",df['linha'].unique(), default=1)

df_filtro1 = df[df['linha'].isin(linha)]

year = st.sidebar.selectbox("Ano",df_filtro1['year'].unique(),index=0)

df_filtro2 = df_filtro1[df_filtro1['year'] == year]

month = st.sidebar.selectbox("Mês",df_filtro2['month'].unique(), index=0)

df_filtro3 = df_filtro2[df_filtro2['month'] == month]


#### DADOS DA OEE NA MÉDIA ####
col1, col2, col3, col4 = st.columns(4)

with col1:
    #st.header("A cat")
    st.metric(label="OEE", value= round(float(df_filtro3["oee"].mean())), delta= None, border=True)

with col2:
    #st.header("A dog")
    st.metric(label="PERFORMANCE", value= round(float(df_filtro3["performance"].mean())), delta=None, border=True)

with col3:
    #st.header("An owl")
    st.metric(label="DISPONIBILIDADE", value= round(float(df_filtro3["disponibilidade"].mean())), delta=None, border=True)

with col4:
    #st.header("An owl")
    st.metric(label="QUALIDADE", value= round(float(df_filtro3["qualidade"].mean())), delta=None, border=True)


#### DADOS DE PRODUÇÃO E REJEITO MÉDIA ####
col5, col6= st.columns(2)

with col5:
    st.metric(label="PRODUÇÃO", value= round(float(df_filtro3["producao"].mean())), delta=None, border=True,)

with col6:
    st.metric(label="REJEITO", value= round(float(df_filtro3["rejeito"].mean())), delta=None, border=True)

#### GRÁFICOS GERAIS DA LINHA ####
media_mensal = round(df_filtro1.groupby('month')['producao'].mean().reset_index())
media_mensal['month'] = media_mensal['month'].dt.strftime('%b %Y') 

total_mensal = round(df_filtro1.groupby('month')['producao'].sum().reset_index())
total_mensal['month'] = total_mensal['month'].dt.strftime('%b %Y')


col7, col8= st.columns(2)

with col7:
    fig = px.bar(media_mensal, x='month', y='producao', text="producao",
                labels={'month': 'Mês', 'producao': 'Média Diária'},
                title='Média Diária da Produção por Mês')

    fig.update_layout(
        yaxis=dict(title='Média Diária', range=[0,20000]),
        xaxis=dict(title='Mês'),
        uniformtext_minsize=15,
        uniformtext_mode='hide'
    )

    st.plotly_chart(fig)
with col8:
    fig2 = px.bar(total_mensal, x='month', y='producao', text="producao",
                labels={'month': 'Mês', 'producao': 'Total Mensal'},
                title='Total mensal da Produção')

    fig2.update_layout(
        yaxis=dict(title='Total Mensal', range=[0,300000]),
        xaxis=dict(title='Mês'),
        uniformtext_minsize=15,
        uniformtext_mode='hide'
    )

    st.plotly_chart(fig2)


#### GRÁFICOS DE PRODUÇÃO X REJEITO ####
total_producao = df_filtro3['producao'].sum()
total_rejeito = df_filtro3['rejeito'].sum()
total_performance = df_filtro3['produzindo'].sum()

#Colunas para plotagem
col9, col10, col11 = st.columns(3)

# Prepara dados para o gráfico de pizza


with col9:
    fig3 = go.Figure(data=[
    go.Pie(
        labels=['Produção', 'Rejeito'],
        values=[total_producao, total_rejeito],
        hole=0.4,
        textinfo='label+value',  # Mostra apenas os valores
        textfont_size=16)])

    fig3.update_layout(
        title_text=f'Total de Produção vs Rejeito - {month}')

    st.plotly_chart(fig3)

#### GRÁFICO DE ENVASE X PERFORMANCE(MOINHO RODANDO)
with col10:
    fig4 = go.Figure(data=[
    go.Pie(
        labels=['Produção', 'Perf'],
        values=[total_producao, total_performance],
        hole=0.4,
        textinfo='label+value',  # Mostra apenas os valores
        textfont_size=16)])

    fig4.update_layout(
        title_text=f'Total de Produção vs Performance - {month}')

    st.plotly_chart(fig4)

#### GRÁFICO DE STATUS ####
with col11:
    resumo = df.groupby('month')[['produzindo', 'parada']].sum().reset_index()
    resumo['month'] = resumo['month'].dt.strftime('%b %Y')

    resumo_melt = resumo.melt(
    id_vars='month',
    value_vars=['produzindo', 'parada'],
    var_name='Status',
    value_name='Minutos')

    resumo_melt['Status'] = resumo_melt['Status'].map({
    'produzindo': 'Máquina Rodando',
    'parada': 'Máquina Parada'})

    fig5 = px.bar(
    resumo_melt,
    x='month',
    y='Minutos',
    color='Status',
    barmode='group',
    text='Minutos',
    title='Total Mensal de Máquina Rodando vs Parada (em minutos)',
    labels={'mes': 'Mês', 'Minutos': 'Minutos Totais'})

    # Ajusta o gráfico
    fig5.update_traces(textposition='outside')
    fig5.update_layout(yaxis_range=[0, resumo_melt['Minutos'].max() * 1.1])

    st.plotly_chart(fig5)


df_filtro3




