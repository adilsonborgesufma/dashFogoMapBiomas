import streamlit as st
import geemap.foliumap as geemap
import ee
import json
import pandas as pd
import geopandas as gpd
import tempfile
import os
import plotly.express as px
import matplotlib.pyplot as plt

# Inicialização do Earth Engine
try:
    ee.Initialize(project='ee-adilsonborges')
except:
    try:
        ee.Authenticate()
        ee.Initialize(project='ee-adilsonborges')
    except:
        st.warning("Falha na autenticação do Earth Engine. Verifique suas credenciais.")

st.set_page_config(layout='wide')
st.title("\U0001F331 APP MAPBIOMAS LAGEOS/LAB - MARANHÃO")
st.write("Análise de cobertura do solo para municípios do Maranhão usando MapBiomas Collection 9")

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

CLASS_CONFIG = {
    'codes': [0, 1, 3, 4, 5, 6, 49, 10, 11, 12, 32, 29, 50, 14, 15, 18, 19, 39, 20, 40, 62, 41, 36, 46, 47, 35, 48, 9, 21, 22, 23, 24, 30, 25, 26, 33, 31, 27],
    'new_classes': [0, 1, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 3, 4, 4, 4, 4, 4, 4, 5, 5, 5, 6],
    'names': {
        0: "Não Observado",
        1: "Floresta",
        2: "Vegetação Herbácea",
        3: "Agropecuária",
        4: "Área não Vegetada",
        5: "Corpo D'água",
        6: "Não Observado"
    }
}

custom_colors = {
    "Floresta": "#1f8d49",
    "Vegetação Herbácea": "#d6bc74",
    "Agropecuária": "#ffefc3",
    "Área não Vegetada": "#d4271e",
    "Corpo D'água": "#2532e4",
    "Não Observado": "#ffffff"
}
RECLASS_PALETTE = [
    custom_colors["Não Observado"],
    custom_colors["Floresta"],
    custom_colors["Vegetação Herbácea"],
    custom_colors["Agropecuária"],
    custom_colors["Área não Vegetada"],
    custom_colors["Corpo D'água"],
    custom_colors["Não Observado"]
]

mapbiomas_image = ee.Image('projects/mapbiomas-public/assets/brazil/lulc/collection9/mapbiomas_collection90_integration_v1')

def reclassify_bands(image, codes, new_classes):
    return ee.Image.cat([
        image.select(f'classification_{year}').remap(codes, new_classes).rename(f'classification_{year}')
        for year in range(1985, 2024)
    ])

remapped_image = reclassify_bands(mapbiomas_image, CLASS_CONFIG['codes'], CLASS_CONFIG['new_classes'])

years = list(range(1985, 2024))
selected_years = st.multiselect('Selecione o(s) ano(s)', years, default=[2023])

geometry = None
area_name = "Área Carregada"

with st.expander('Defina a área de estudo', expanded=True):
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
            for file in uploaded_files:
                with open(os.path.join(temp_dir, file.name), "wb") as f:
                    f.write(file.getbuffer())
            shp_files = [f for f in os.listdir(temp_dir) if f.endswith('.shp')]
            if shp_files:
                gdf = gpd.read_file(os.path.join(temp_dir, shp_files[0]))
                geojson = json.loads(gdf.to_json())
                geometry = ee.Geometry(geojson['features'][0]['geometry'])
                area_name = geojson['features'][0]['properties'].get('name') or 'Área Carregada'
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
    remapped_image = remapped_image.clip(geometry)

for year in selected_years:
    band_name = f"classification_{year}"
    m.addLayer(
        remapped_image.select(band_name),
        {'min': 0, 'max': 6, 'palette': RECLASS_PALETTE},
        f"Classificação {year}"
    )
m.to_streamlit(height=600)

if geometry and selected_years:
    st.subheader(f"\U0001F4CA ESTATÍSTICAS DE ÁREA POR CLASSE - {area_name.upper()}")
    stats_data = []
    with st.spinner("Calculando estatísticas..."):
        for year in selected_years:
            band = remapped_image.select(f"classification_{year}")
            masks = [band.eq(i).rename(f'class_{i}') for i in range(7)]
            areas = ee.Image.cat(*masks).multiply(ee.Image.pixelArea()).reduceRegion(
                reducer=ee.Reducer.sum().repeat(7),
                geometry=geometry,
                scale=30,
                maxPixels=1e13
            )
            try:
                areas_dict = areas.getInfo()
                if 'sum' in areas_dict:
                    for i in range(7):
                        area_km2 = areas_dict['sum'][i] / 1e6 if i < len(areas_dict['sum']) else 0
                        stats_data.append({
                            "Ano": year,
                            "Classe": i,
                            "Nome da Classe": CLASS_CONFIG['names'].get(i, f"Classe {i}"),
                            "Área (km²)": round(area_km2, 2)
                        })
            except Exception as e:
                st.error(f"Erro {year}: {str(e)}")

    if not stats_data:
        st.warning("Nenhum dado encontrado.")
        st.stop()

    df = pd.DataFrame(stats_data)
    df_agg = df.groupby(['Ano', 'Nome da Classe'])['Área (km²)'].sum().reset_index()

    st.subheader("\U0001F4CA DISTRIBUIÇÃO PERCENTUAL DAS CLASSES (GRÁFICO EMPILHADO)")
    pivot_df = df_agg.pivot(index='Ano', columns='Nome da Classe', values='Área (km²)').fillna(0)
    pivot_percent = pivot_df.div(pivot_df.sum(axis=1), axis=0) * 100
    class_order = pivot_percent.mean().sort_values(ascending=False).index.tolist()
    pivot_percent = pivot_percent[class_order]
    color_list_ordered = [custom_colors.get(classe, "#999999") for classe in class_order]

    fig, ax = plt.subplots(figsize=(12, 8))
    pivot_percent.plot.barh(stacked=True, ax=ax, color=color_list_ordered, width=0.8)
    ax.set_title(f'Distribuição Percentual das Classes - {area_name}', pad=20)
    ax.set_xlabel('Percentual (%)')
    ax.set_ylabel('Ano')
    ax.set_xlim(0, 100)
    ax.grid(axis='x', linestyle='--', alpha=0.7)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', title='Classes')
    plt.tight_layout()
    st.pyplot(fig)

    st.subheader(f"EVOLUÇÃO DAS CLASSES DE COBERTURA - {area_name.upper()}")
    bar_fig = px.bar(
        df_agg.sort_values("Ano"),
        x="Ano",
        y="Área (km²)",
        color="Nome da Classe",
        color_discrete_map=custom_colors,
        barmode='group',
        height=550
    )
    st.plotly_chart(bar_fig, use_container_width=True)

    st.subheader("\U0001F355 DISTRIBUIÇÃO PERCENTUAL POR CLASSE")
    selected_year = st.selectbox("Selecione o ano para análise:", sorted(selected_years, reverse=True), index=0)
    year_df = df_agg[df_agg['Ano'] == selected_year]
    total_area = year_df['Área (km²)'].sum()
    year_df['Porcentagem'] = (year_df['Área (km²)'] / total_area) * 100
    pie_fig = px.pie(
        year_df,
        names="Nome da Classe",
        values="Porcentagem",
        title=f"Distribuição Percentual {selected_year}",
        color="Nome da Classe",
        color_discrete_map=custom_colors,
        hole=0.4,
        height=500
    )
    pie_fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate="<b>%{label}</b><br>%{percent:.1f}%<br>Área: %{value:.2f} km²",
        marker=dict(line=dict(color='white', width=1))
    )
    st.plotly_chart(pie_fig, use_container_width=True)

    st.subheader("\U0001F4CB TABELA DE DADOS COMPLETA")
    st.dataframe(
        df_agg.pivot(index='Ano', columns='Nome da Classe', values='Área (km²)')
        .style.format("{:.2f}")
        .set_properties(**{'background-color': '#f8f9fa', 'border': '1px solid #dee2e6'})
        .highlight_max(axis=0, color='#d4edda')
        .highlight_min(axis=0, color='#f8d7da')
    )