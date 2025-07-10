# 🔥 dashFogoMapBiomas

Dashboard interativo desenvolvido com **Streamlit** e **Google Earth Engine** para visualização das áreas queimadas no Brasil com base no **MapBiomas Fogo – Coleção 4**.

Este aplicativo foi desenvolvido no âmbito do **Laboratório de Geoprocessamento e Sensoriamento Remoto – LAGEOS/UFMA** com foco na análise de dados espaciais de fogo no estado do Maranhão.

## 🔧 Funcionalidades

- Seleção de área de estudo por:
  - Municípios do Maranhão
  - Upload de shapefiles
  - Inserção direta de GeoJSON
- Visualização interativa dos dados de fogo por mês e ano
- Análises gráficas mensais e anuais (km²)
- Tabela interativa com os dados mensais de área queimada
- Cores customizadas com paleta do MapBiomas Fogo

## 🛰️ Fonte dos Dados

- [MapBiomas Fogo - Coleção 4](https://mapbiomas.org/colecoes-de-dados/fogo)

## 📦 Tecnologias Utilizadas

- [Streamlit](https://streamlit.io/)
- [Google Earth Engine](https://earthengine.google.com/)
- [Geemap](https://geemap.org/)
- [Plotly](https://plotly.com/)
- [Pandas](https://pandas.pydata.org/)
- [GeoPandas](https://geopandas.org/)

## ▶️ Como Executar

```bash
git clone https://github.com/adilsonborgesufma/dashFogoMapBiomas.git
cd dashFogoMapBiomas
pip install -r requirements.txt
streamlit run nome_do_arquivo.py
