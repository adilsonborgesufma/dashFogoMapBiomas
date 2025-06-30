import streamlit as st
import geemap.foliumap as geemap
import ee
import json
import pandas as pd
import tempfile
import os
import plotly.express as px
import matplotlib.pyplot as plt
import shapefile  # pyshp

# Defina a configuração da página primeiro!
st.set_page_config(layout='wide')

# Função para autenticar usando conta de serviço
def initialize_ee():
    try:
        service_account = 'streamlit-ee-service@streamlit-ee-service.iam.gserviceaccount.com'
        json_key = st.secrets["GEE_SERVICE_ACCOUNT_JSON"]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as fp:
            fp.write(json_key)
            key_path = fp.name

        credentials = ee.ServiceAccountCredentials(service_account, key_path)
        ee.Initialize(credentials)
        st.success("✅ Earth Engine autenticado com sucesso!")
    except Exception as e:
        st.error(f"❌ Falha na autenticação do Earth Engine: {e}")

# Inicializa o Earth Engine
initialize_ee()

# Agora você pode usar outros comandos Streamlit
st.title("🔥 APP MAPBIOMAS FOGO - LAGEOS/LAB MARANHÃO")
st.write("Análise de focos de fogo mensais a partir do MapBiomas Fogo Collection 4")

# Carregar GeoJSON com municípios
try:
    with open('assets/municipios_ma.geojson', 'r', encoding='utf-8') as f:
        geojson_data = json.load(f)
        st.success("Arquivo GeoJSON carregado com sucesso!")
except Exception as e:
    st.error(f"Erro ao carregar GeoJSON: {str(e)}")
    geojson_data = None

@st.cache_resource
def load_municipios():
    municipios = {}
    if geojson_data:
        for feature in geojson_data['features']:
            nome = feature['properties'].get('NM_MUNICIP')
            if nome:
                municipios[nome] = feature['geometry']
    return municipios

MUNICIPIOS_MA = load_municipios()

# Paleta MapBiomas Fogo Collection 4
fogo_colors = {
    "Sem Fogo": '#f0f0f0',
    "Fogo": '#e31a1c'
}

# Carrega imagem MapBiomas Fogo Collection 4
fogo_image = ee.Image('projects/mapbiomas-public/assets/brazil/fire/collection4/mapbiomas_fire_collection4_monthly_burned_v1')

anos_disponiveis = list(range(2019, 2025))
anos_selecionados = st.multiselect("Selecione o(s) ano(s) para análise:", anos_disponiveis, default=[2022])

meses = list(range(1, 13))
mes_nomes = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
             'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']

meses_selecionados = st.multiselect("Selecione o(s) mês(es) para visualização no mapa e nos gráficos:", meses, default=[1], format_func=lambda m: mes_nomes[m-1])

geometry = None
area_name = "Área Carregada"

with st.expander("Defina a área de estudo", expanded=True):
    tab1, tab2, tab3 = st.tabs(["Selecionar Município", "Upload Shapefile", "Inserir GeoJSON"])
    with tab1:
        municipio = None
        if MUNICIPIOS_MA:
            municipio = st.selectbox("Selecione um município do Maranhão", sorted(MUNICIPIOS_MA.keys()))
    with tab2:
        uploaded_files = st.file_uploader("Upload do Shapefile", type=['shp', 'dbf', 'shx'], accept_multiple_files=True)
    with tab3:
        geometry_input = st.text_area("Cole seu GeoJSON aqui")

if uploaded_files:
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            file_paths = {}
            for file in uploaded_files:
                file_path = os.path.join(temp_dir, file.name)
                file_paths[file.name.split('.')[-1]] = file_path
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())

            if {'shp', 'dbf', 'shx'}.issubset(file_paths.keys()):
                sf = shapefile.Reader(shp=file_paths['shp'], dbf=file_paths['dbf'], shx=file_paths['shx'])
                shape = sf.shapes()[0]
                geojson_geom = {
                    "type": "Polygon",
                    "coordinates": [shape.points]
                }
                geometry = ee.Geometry(geojson_geom)
                area_name = 'Shapefile Carregado'
                st.success("Shapefile carregado com sucesso!")
    except Exception as e:
        st.error(f"Erro: {str(e)}")

elif geometry_input.strip():
    try:
        geo_data = json.loads(geometry_input)
        if 'geometry' in geo_data:
            geometry = ee.Geometry(geo_data['geometry'])
        elif geo_data['type'] == 'FeatureCollection':
            geometry = ee.Geometry(geo_data['features'][0]['geometry'])
        else:
            geometry = ee.Geometry(geo_data)
        st.success("GeoJSON carregado com sucesso!")
    except Exception as e:
        st.error(f'Erro no GeoJSON: {str(e)}')

elif municipio and municipio in MUNICIPIOS_MA:
    geometry = ee.Geometry(MUNICIPIOS_MA[municipio])
    area_name = municipio
    st.success(f"Município {municipio} carregado com sucesso!")

m = geemap.Map(center=[-5, -45], zoom=6, plugin_Draw=True)
if geometry:
    study_area = ee.FeatureCollection([ee.Feature(geometry)])
    m.centerObject(study_area, zoom=9)
    m.addLayer(study_area, {'color': 'red', 'width': 2}, 'Área de estudo')
    fogo_image = fogo_image.clip(geometry)

for ano in anos_selecionados:
    band_name = f"burned_monthly_{ano}"
    for mes in meses_selecionados:
        monthly_band = fogo_image.select(band_name).eq(mes).rename("Fogo_Mensal")
        m.addLayer(
            monthly_band,
            {'min': 0, 'max': 1, 'palette': [fogo_colors["Sem Fogo"], fogo_colors["Fogo"]]},
            f"Fogo {ano} - {mes_nomes[mes-1]}"
        )
m.to_streamlit(height=600)

if geometry and anos_selecionados:
    st.subheader(f"📊 ESTATÍSTICAS MENSAL E ANUAL - {area_name.upper()}")
    stats = []
    with st.spinner("Calculando estatísticas..."):
        for ano in anos_selecionados:
            total_ano_km2 = 0
            for mes in meses:
                banda = fogo_image.select(f"burned_monthly_{ano}")
                mask = banda.eq(mes)
                area = mask.multiply(ee.Image.pixelArea()).reduceRegion(
                    reducer=ee.Reducer.sum(),
                    geometry=geometry,
                    scale=30,
                    maxPixels=1e13
                )
                try:
                    area_km2 = area.getInfo()[f"burned_monthly_{ano}"] / 1e6
                except:
                    area_km2 = 0
                stats.append({
                    "Ano": ano,
                    "Mês": mes,
                    "Nome da Classe": "Fogo",
                    "Área (km²)": round(area_km2, 2)
                })

    df = pd.DataFrame(stats)
    df_agg = df.groupby(['Ano', 'Mês', 'Nome da Classe'])['Área (km²)'].sum().reset_index()

    if meses_selecionados:
        df_agg = df_agg[df_agg['Mês'].isin(meses_selecionados)]
    else:
        st.info("Nenhum mês selecionado. Exibindo todos os meses.")

    df_agg['Mês Nome'] = df_agg['Mês'].apply(lambda m: mes_nomes[m-1])

    st.subheader("📊 EVOLUÇÃO MENSAL DAS ÁREAS COM FOGO")
    bar_fig = px.bar(
        df_agg,
        x="Mês Nome",
        y="Área (km²)",
        color="Nome da Classe",
        animation_frame="Ano",
        color_discrete_map=fogo_colors,
        barmode='group',
        height=500
    )
    st.plotly_chart(bar_fig, use_container_width=True)

    st.subheader("📊 ACUMULADO ANUAL DAS ÁREAS COM FOGO")
    df_ano = df_agg.groupby(['Ano', 'Nome da Classe'])['Área (km²)'].sum().reset_index()
    df_ano['Ano'] = df_ano['Ano'].astype(str)
    bar_ano = px.bar(
        df_ano,
        x="Ano",
        y="Área (km²)",
        color="Nome da Classe",
        color_discrete_map=fogo_colors,
        barmode='group',
        height=400
    )
    bar_ano.update_layout(xaxis_title="Ano", xaxis_type="category")
    st.plotly_chart(bar_ano, use_container_width=True)

    st.subheader("📋 TABELA MENSAL DE DADOS COMPLETA")
    st.dataframe(
        df_agg.pivot_table(index=['Ano', 'Mês Nome'], columns='Nome da Classe', values='Área (km²)')
        .fillna(0)
        .style.format("{:.2f}")
        .highlight_max(axis=1, color='#d4edda')
        .highlight_min(axis=1, color='#f8d7da')
    )
