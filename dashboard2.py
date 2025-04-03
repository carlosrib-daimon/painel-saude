import streamlit as st
import pandas as pd
import altair as alt
import plotly.express as px
import geopandas as gpd

#######################
# Page configuration
st.set_page_config(
    page_title="Painel de Saúde",
    page_icon=":material/medical_information:",
    layout="wide",
    )

st.title("Painel de Leitos no Brasil")

alt.themes.enable("dark")

#######################
# CSS styling
st.markdown("""
<style>

[data-testid="block-container"] {
    padding-left: 2rem;
    padding-right: 2rem;
    padding-top: 1rem;
    padding-bottom: 0rem;
    margin-bottom: -7rem;
}

[data-testid="stVerticalBlock"] {
    padding-left: 0rem;
    padding-right: 0rem;
}

[data-testid="stMetric"] {
    background-color: #393939;
    text-align: center;
    padding: 15px 0;
}

[data-testid="stMetricLabel"] {
  display: flex;
  justify-content: center;
  align-items: center;
}

[data-testid="stMetricDeltaIcon-Up"] {
    position: relative;
    left: 38%;
    -webkit-transform: translateX(-50%);
    -ms-transform: translateX(-50%);
    transform: translateX(-50%);
}

[data-testid="stMetricDeltaIcon-Down"] {
    position: relative;
    left: 38%;
    -webkit-transform: translateX(-50%);
    -ms-transform: translateX(-50%);
    transform: translateX(-50%);
}

</style>
""", unsafe_allow_html=True)


#######################
# Load data
df = pd.read_csv('dados.csv')
gdf = gpd.read_file("BR_Regionais.shp")
df_regioes = pd.read_csv("regioesSaude.csv")
df_instal = pd.read_csv("tbInstalFisicaParaAssist202502.csv", encoding='latin1', sep=';')
df_uni = pd.read_csv("tiposUnidades.csv", encoding='latin1', sep=';')

#######################
# Dashboard Filters
cols = st.columns([0.7, 0.3], gap='medium')

with cols[0]:
    options = df_uni["DS_NATUREZA_JUR"].unique()
    unity_type = st.multiselect("Tipos de Unidades de Saúde (Opcional)", options, placeholder="Selecione uma ou mais opções")
    selected_codes = df_uni[df_uni["DS_NATUREZA_JUR"].isin(unity_type)]["CO_NATUREZA_JUR"].tolist()

with cols[1]:
    sus_options = ["Todos", "Sim", "Não"]
    sus_attend = st.segmented_control("Atende SUS", sus_options, default="Todos")

# Apply filters to the dataframe
filtered_df = df.copy()

if unity_type:
    filtered_df = filtered_df[filtered_df["CO_NATUREZA_JUR"].isin(selected_codes)]

if sus_attend == "Sim":
    filtered_df = filtered_df[filtered_df["ST_CONTRATO_FORMALIZADO"] == "S"]
elif sus_attend == "Não":
    filtered_df = filtered_df[filtered_df["ST_CONTRATO_FORMALIZADO"] != "S"]

df = filtered_df

#######################
# Manage data
df_macro_people = df_regioes.groupby('Macrorregiao de Saude').agg({
    'Populacao Estimada IBGE 2022': lambda x: x.str.replace('.', '').astype(int).sum()
}).reset_index()
df_macro_people["Populacao Estimada IBGE 2022"] = df_macro_people["Populacao Estimada IBGE 2022"].apply(
    lambda x: f"{x:,.0f}".replace(",", ".")
)

df_regiao_people = df_regioes.groupby('Regiao de Saude').agg({
    'Populacao Estimada IBGE 2022': lambda x: x.str.replace('.', '').astype(int).sum()
}).reset_index()
df_regiao_people["Populacao Estimada IBGE 2022"] = df_regiao_people["Populacao Estimada IBGE 2022"].apply(
    lambda x: f"{x:,.0f}".replace(",", ".")
)

df_macro_leitos = df.groupby('Macrorregiao de Saude')['NU_LEITOS'].sum().reset_index()
df_macro_leitos['NU_LEITOS'] = df_macro_leitos['NU_LEITOS'].astype(float)
df_macro_leitos = df_macro_leitos.sort_values(by='NU_LEITOS', ascending=False)
df_macro_leitos = df_macro_leitos.merge(df_macro_people, on='Macrorregiao de Saude', how='left')

df_regiao_leitos = df.groupby('Regiao de Saude')['NU_LEITOS'].sum().reset_index()
df_regiao_leitos['NU_LEITOS'] = df_regiao_leitos['NU_LEITOS'].astype(float)
df_regiao_leitos = df_regiao_leitos.sort_values(by='NU_LEITOS', ascending=False)
df_regiao_leitos = df_regiao_leitos.merge(df_regiao_people, on='Regiao de Saude', how='left')


df_grouped = df.groupby('Codigo Regiao de Saude', as_index=False)['NU_LEITOS'].sum()
df_grouped.rename(columns={'Codigo Regiao de Saude': 'reg_id'}, inplace=True)
merged_gdf = gdf.merge(df_grouped, on='reg_id', how='left')
merged_gdf['NU_LEITOS'].fillna(0, inplace=True)

if st.button("Gerar"):
    # Dashboard Main Panel
    col = st.columns((1.5, 4.5, 2), gap='medium')

    with col[0]:
        st.markdown('#### Dados Analisados')

        st.metric(label="Macrorregiões de Saúde", value=len(df["Macrorregiao de Saude"].unique()))
        st.metric(label="Regiões de Saúde", value=len(df["Regiao de Saude"].unique()))
        st.metric(label="Número de Leitos", value=int(df["NU_LEITOS"].sum()))

    with col[1]:
        st.markdown('#### Distribuição de Leitos')

        fig = px.bar(df_macro_leitos, 
                 x='Macrorregiao de Saude', 
                 y='NU_LEITOS', 
                 title='Número de Leitos por Macrorregião de Saúde',
                 labels={'Macrorregiao de Saude': 'Macrorregião de Saúde', 'NU_LEITOS': 'Número de Leitos'},
                 color='NU_LEITOS',
                 color_continuous_scale='Viridis')

        fig.update_layout(
            xaxis_tickangle=-45,  
            xaxis=dict(tickfont=dict(size=8)), 
            yaxis=dict(title_font=dict(size=12), tickformat='.'), 
            xaxis_title='Macrorregião de Saúde',
            yaxis_title='Número de Leitos',
            height=600, 
            width=1200,
            bargap=0.2,
        )
        
        with st.expander('Número de Leitos por Macrorregião de Saúde', expanded=True):
            st.plotly_chart(fig, use_container_width=True)

        fig2 = px.bar(df_regiao_leitos, 
                 x='Regiao de Saude', 
                 y='NU_LEITOS', 
                 title='Número de Leitos por Região de Saúde',
                 labels={'Regiao de Saude': 'Região de Saúde', 'NU_LEITOS': 'Número de Leitos'},
                 color='NU_LEITOS',
                 color_continuous_scale='Magma')

        fig2.update_layout(
            xaxis_tickangle=-45,  
            xaxis=dict(tickfont=dict(size=8)), 
            yaxis=dict(title_font=dict(size=12), tickformat='.'), 
            xaxis_title='Região de Saúde',
            yaxis_title='Número de Leitos',
            height=600, 
            width=1200,
            bargap=0.2,
        )

        with st.expander('Número de Leitos por Região de Saúde', expanded=True):
            st.plotly_chart(fig2, use_container_width=True)

        fig3 = px.choropleth(merged_gdf, 
                         geojson=merged_gdf.geometry, 
                         locations=merged_gdf.index, 
                         color='NU_LEITOS',
                         color_continuous_scale="Viridis",
                         labels={'NU_LEITOS': 'Número de Leitos'},
                         title='Número de Leitos por Região de Saúde',
                         hover_data={'nome': True, 'NU_LEITOS': True} 
                        )

        fig3.update_geos(fitbounds="locations", visible=False)
        fig3.update_layout(
            template='plotly_dark',
            plot_bgcolor='rgba(0, 0, 0, 0)',
            paper_bgcolor='rgba(0, 0, 0, 0)',
            margin=dict(l=0, r=0, t=0, b=0),
            height=500
        )

        with st.expander('Mapa de Leitos por Região de Saúde', expanded=True):
            st.plotly_chart(fig3, use_container_width=True)
        
        

    with col[2]:
        st.markdown('#### Top Macrorregiões')

        df_macro_leitos["Leitos por 100k Habitantes"] = (
            df_macro_leitos["NU_LEITOS"] / df_macro_leitos["Populacao Estimada IBGE 2022"].str.replace('.', '').astype(int) * 100000
        ).round(2)

        df_regiao_leitos["Leitos por 100k Habitantes"] = (
            df_regiao_leitos["NU_LEITOS"] / df_regiao_leitos["Populacao Estimada IBGE 2022"].str.replace('.', '').astype(int) * 100000
        ).round(2)

        st.dataframe(df_macro_leitos,
                     column_order=("Macrorregiao de Saude", "NU_LEITOS", "Populacao Estimada IBGE 2022", "Leitos por 100k Habitantes"),
                     hide_index=True,
                     width=None,
                     column_config={
                        "Macrorregiao de Saude": st.column_config.TextColumn(
                            "Macrorregião",
                        ),
                        "NU_LEITOS": st.column_config.ProgressColumn(
                            "Leitos",
                            format="%f",
                            min_value=0,
                            max_value=df_macro_leitos["NU_LEITOS"].max(),
                        ),
                        "Populacao Estimada IBGE 2022": st.column_config.TextColumn(
                            "Populacao Estimada IBGE 2022",
                        ),
                        "Leitos por 100k Habitantes": st.column_config.NumberColumn(
                            "Leitos por 100k Habitantes",
                            format="%.2f",
                        )}
                     )
        
        st.markdown('#### Top Regiões')

        st.dataframe(df_regiao_leitos,
                     column_order=("Regiao de Saude", "NU_LEITOS", "Populacao Estimada IBGE 2022", "Leitos por 100k Habitantes"),
                     hide_index=True,
                     width=None,
                     column_config={
                        "Regiao de Saude": st.column_config.TextColumn(
                            "Região",
                        ),
                        "NU_LEITOS": st.column_config.ProgressColumn(
                            "Leitos",
                            format="%f",
                            min_value=0,
                            max_value=df_regiao_leitos["NU_LEITOS"].max(),
                        ),
                        "Populacao Estimada IBGE 2022": st.column_config.TextColumn(
                            "Populacao Estimada IBGE 2022",
                        ),
                        "Leitos por 100k Habitantes": st.column_config.NumberColumn(
                            "Leitos por 100k Habitantes",
                            format="%.2f",
                        )}
                     )
        
        with st.expander('Fontes', expanded=True):
            st.write('''
                - [CNES](https://cnes.datasus.gov.br/pages/downloads/arquivosBaseDados.jsp)
                - [SAVINIEC, Landir; ROCHA, Alexsandra Bezerra da. Shape das Regiões de Saúde do Brasil. 13 de jul. de 2020.](https://github.com/lansaviniec/shapefile_das_regionais_de_saude_sus)
                ''')