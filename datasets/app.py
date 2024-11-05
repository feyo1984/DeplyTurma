#%%
import streamlit as st
import geopandas as gpd
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import folium_static
import matplotlib.pyplot as plt

# Configurar Página
st.set_page_config(layout='wide')
st.sidebar.image(r'C:\Users\fyogi\Desktop\Dashboard\Sabesp.svg.png')

# Função para carregar os dados
@st.cache_data
def load_data():
    df = pd.read_parquet(r'C:\Users\fyogi\Desktop\Dashboard\assets\dados_filtrado.parquet')
    return df

df = load_data()
st.dataframe(df)

# Função para carregar os dados geoespaciais
@st.cache_data
def load_geodata():
    return gpd.read_file(r'C:\Users\fyogi\Desktop\Dashboard\assets\BR_UF_2022_filtrado.geojson')

gdf = load_geodata()

# Tratamento dos dados
col = ['NR_AREA_TOTAL', 'VL_PREMIO_LIQUIDO']
df[col] = df[col].replace(',', '.', regex=True).astype(float)

# Agrupamento dos dados por estado
df_estado = df.groupby('SG_UF_PROPRIEDADE').agg(
    area_total=('NR_AREA_TOTAL', 'sum'),
    valor_total=('VL_PREMIO_LIQUIDO', 'sum'),
    numero_seguros=('NR_APOLICE', 'nunique')
).reset_index()

# Unir o gdf com o df
gdf = gdf.merge(df_estado, left_on='SIGLA_UF', right_on='SG_UF_PROPRIEDADE', how='left')

# Agrupamento dos dados por Razão Social
df_razao_social_estado = df.groupby(['NM_RAZAO_SOCIAL', 'SG_UF_PROPRIEDADE']).agg(
    numero_seguros=('NR_APOLICE', 'nunique'),
    area_total=('NR_AREA_TOTAL', 'sum'),
    valor_total=('VL_PREMIO_LIQUIDO', 'sum'),
    estados=('SG_UF_PROPRIEDADE', 'nunique')
).reset_index()

# Contar o número de estados únicos associados a cada razão social
df_razao_social_estado['contagem_estados'] = df_razao_social_estado['estados']

# Calcular a matriz de correlação entre variáveis selecionadas com arredondamento
correlation_columns = [
    'NR_AREA_TOTAL', 'VL_PREMIO_LIQUIDO', 'VL_LIMITE_GARANTIA',
    'NR_PRODUTIVIDADE_ESTIMADA', 'NR_PRODUTIVIDADE_SEGURADA', 'VL_SUBVENCAO_FEDERAL'
]

for col in correlation_columns:
    df[col] = df[col].replace(',', '.', regex=True).astype(float)

# Gerar Matriz de Correlação
correlation_matrix = df[correlation_columns].corr().round(2)

# Interface Streamlit
st.title('Análise de Seguros Agrícolas - Brasil')
st.markdown('Este site foi construído utilizando [GitHub Pages](https://pages.github.com/).')

st.divider()

with st.sidebar:
    st.subheader('Sistema de Informação da Subvenção ao Seguro Rural. Fonte: [SISSER](https://sistemasweb.agricultura.gov.br/pages/SISSER.html)')
    analise_tipo = st.selectbox("Selecione o tipo de Análise", ["Razão Social", "Estado"])

if analise_tipo == 'Razão Social':
    st.header('Análise por Razão Social')
    metric_options = {
        'Número de Seguros': 'numero_seguros',
        'Contagem de Estados': 'contagem_estados',
        'Área Total': 'area_total'
    }

    # Informações principais por estado
    top_estado_num_apolices = df_estado.loc[df_estado['numero_seguros'].idxmax()]
    top_estado_area_total = df_estado.loc[df_estado['area_total'].idxmax()]
    top_estado_valor_total = df_estado.loc[df_estado['valor_total'].idxmax()]

    with st.sidebar:
        st.markdown(f"**Estado com o maior número de Apólices:** {top_estado_num_apolices['SG_UF_PROPRIEDADE']} "
                    f"com {top_estado_num_apolices['numero_seguros']} apólices.\n\n"
                    f"**Estado com a maior área total assegurada:** {top_estado_area_total['SG_UF_PROPRIEDADE']} "
                    f"com {top_estado_area_total['area_total']:.2f} ha.\n\n"
                    f"**Estado com o maior valor total assegurado:** {top_estado_valor_total['SG_UF_PROPRIEDADE']} "
                    f"com {top_estado_valor_total['valor_total']:.2f}.")

    selected_metric = st.selectbox("Selecione a Métrica", options=list(metric_options.keys()))
    metric_column = metric_options[selected_metric]

    # Ordenação e Gráfico de Barras
    df_sorted = df_razao_social_estado.sort_values(by=metric_column, ascending=False)
    fig_bar = px.bar(df_sorted, x='NM_RAZAO_SOCIAL', y=metric_column,
                     title=f'{selected_metric} por Razão Social',
                     labels={'NM_RAZAO_SOCIAL': 'Razão Social', metric_column: selected_metric})
    st.plotly_chart(fig_bar, use_container_width=True)

    # Métricas Resumo
    max_num_seguros = df_razao_social_estado['numero_seguros'].max()
    mean_num_seguros = df_razao_social_estado['numero_seguros'].mean()
    var_num_seguros = ((max_num_seguros - mean_num_seguros) / mean_num_seguros) * 100
    top_razao_num_seguros = df_razao_social_estado[df_razao_social_estado['numero_seguros'] == max_num_seguros]['NM_RAZAO_SOCIAL'].values[0]

    max_count_estados = df_razao_social_estado['contagem_estados'].max()
    mean_count_estados = df_razao_social_estado['contagem_estados'].mean()
    var_count_estados = ((max_count_estados - mean_count_estados) / mean_count_estados) * 100
    top_razao_count_estados = df_razao_social_estado[df_razao_social_estado['contagem_estados'] == max_count_estados]['NM_RAZAO_SOCIAL'].values[0]

    max_area_total = df_razao_social_estado['area_total'].max()
    mean_area_total = df_razao_social_estado['area_total'].mean()
    var_area_total = ((max_area_total - mean_area_total) / mean_area_total) * 100
    top_razao_area_total = df_razao_social_estado[df_razao_social_estado['area_total'] == max_area_total]['NM_RAZAO_SOCIAL'].values[0]

    col1, col2, col3 = st.columns(3)
    col1.metric(label=f"Máximo Número de Seguros - {top_razao_num_seguros}", value=f"{max_num_seguros:.0f}", delta=f"{var_num_seguros:.2f}% em relação à média")
    col2.metric(label=f"Máximo Contagem de Estados - {top_razao_count_estados}", value=f"{max_count_estados:.0f}", delta=f"{var_count_estados:.2f}% em relação à média")
    col3.metric(label=f"Máxima Área Total (ha) - {top_razao_area_total}", value=f"{max_area_total:.0f}", delta=f"{var_area_total:.2f}% em relação à média")

    st.divider()

    # Mapa de Calor de Correlação
    st.subheader('Correlação entre Parâmetros')
    fig_heatmap = px.imshow(correlation_matrix, text_auto=True, color_continuous_scale='Blues', title='Correlação de Parâmetros')
    st.plotly_chart(fig_heatmap, use_container_width=True)

    # Mapa Folium - Valor Total Assegurado
    st.subheader('Valor Total Assegurado')
    m_valor = folium.Map(location=[-15.78, -47.93], zoom_start=4)
    folium.Choropleth(
        geo_data=gdf,
        name='choropleth',
        data=gdf,
        columns=['SIGLA_UF', 'valor_total'],
        key_on='feature.properties.SIGLA_UF',
        fill_color='Blues',
        fill_opacity=0.7,
        line_opacity=0.2,
        legend_name='Valor Total Assegurado'
    ).add_to(m_valor)
    folium_static(m_valor)

    # Gráfico de Pizza - Distribuição por Razão Social
    fig_pie_valor = px.pie(
        df_razao_social_estado,
        names='NM_RAZAO_SOCIAL',
        values='valor_total',
        title='Distribuição do Valor Total Assegurado por Razão Social'
    )
    fig_pie_valor.update_layout(legend=dict(font=dict(size=9)))
    st.plotly_chart(fig_pie_valor, use_container_width=True)
else:




    st.header('Análise por Estado')

   # Filtragem para análise por Estado
    estado_escolhido = st.sidebar.selectbox("Seleciona um Estado", df['SG_UF_PROPRIEDADE'].unique())
    df_estado = df_razao_social_estado[df_razao_social_estado['SG_UF_PROPRIEDADE'] == estado_escolhido]


    ##st.dataframe(df_estado)

    df_municipio = df[df['SG_UF_PROPRIEDADE'] == estado_escolhido].groupby('NM_MUNICIPIO_PROPRIEDADE').agg(
    area_total=('NR_AREA_TOTAL', 'sum'),
    valor_total=('VL_PREMIO_LIQUIDO', 'sum')
    ).reset_index()

    
   # Filtrar os Top 10 municípios por área e valor total
    df_top_area = df_municipio.nlargest(10, 'area_total')
    df_top_valor = df_municipio.nlargest(10, 'valor_total')

    # Combinar os Top 10 de área e valor para obter uma lista única de municípios
    df_top_combined = pd.concat([df_top_area, df_top_valor]).drop_duplicates()

    # Cálculo da correlação entre área total e valor total para os Top 10 municípios combinados
    correlation_top_municipios = df_top_combined[['area_total', 'valor_total']].corr().iloc[0, 1]

    # Exibir a correlação calculada
    st.sidebar.divider()
    st.sidebar.subheader('Análise exploratória dos dados')
    st.sidebar.markdown(f'Analisando os dados de Área Total e Valor do Prêmio Líquido nota-se uma correlação de {correlation_top_municipios:.2f}')
    st.sidebar.divider()

    # Gráfico de Barras - Top 10 Municípios com Maior Área
    col1, col2 = st.columns(2)
    with col1:
        fig_top_area = px.bar(df_top_area, x='NM_MUNICIPIO_PROPRIEDADE', y='area_total', 
                              title=f'Top 10 Municípios com Maior Área em {estado_escolhido}',
                              labels={'NM_MUNICIPIO_PROPRIEDADE': 'Município', 'area_total': 'Área Total'})
        st.plotly_chart(fig_top_area, use_container_width=True)

    # Gráfico de Barras - Top 10 Municípios com Maior Valor
    with col2:
        fig_top_valor = px.bar(df_top_valor, x='NM_MUNICIPIO_PROPRIEDADE', y='valor_total', 
                               title=f'Top 10 Municípios com Maior Valor Assegurado em {estado_escolhido}',
                               labels={'NM_MUNICIPIO_PROPRIEDADE': 'Município', 'valor_total': 'Valor Total'})
        st.plotly_chart(fig_top_valor, use_container_width=True)

    # Gráfico de Barras - Número de Seguros por Estado e Razão Social
    fig_bar_estado_seguros = px.bar(df_estado, x='NM_RAZAO_SOCIAL', y='numero_seguros', 
                                    title=f'Número de Seguros em {estado_escolhido} por Razão Social',
                                    labels={'NM_RAZAO_SOCIAL': 'Razão Social', 'numero_seguros': 'Número de Seguros'})
    st.plotly_chart(fig_bar_estado_seguros)

    # Gráfico de Pizza - Distribuição da Área Total Assegurada por Razão Social no Estado
    fig_pie_estado_area = px.pie(df_estado, names='NM_RAZAO_SOCIAL', values='area_total', 
                                 title=f'Distribuição da Área Total Assegurada em {estado_escolhido} por Razão Social')
    st.plotly_chart(fig_pie_estado_area)

    # Gráfico de Pizza - Distribuição do Valor Total Assegurado por Razão Social no Estado
    fig_pie_estado_valor = px.pie(df_estado, names='NM_RAZAO_SOCIAL', values='valor_total', 
                                  title=f'Distribuição do Valor Total Assegurado em {estado_escolhido} por Razão Social')
    st.plotly_chart(fig_pie_estado_valor)

# %%
