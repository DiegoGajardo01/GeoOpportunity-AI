"""Territorial evidence dashboard; commercial sales inference remains separate."""

import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import geopandas as gpd
import pandas as pd
import pydeck as pdk
import streamlit as st

from geoopportunity.data.territorial import TerritorialError, rank_zones

st.set_page_config(page_title='GeoOpportunity AI', layout='wide')
st.title('GeoOpportunity AI — exploratory territorial coverage')
st.caption('Valparaíso and Viña del Mar · No sales prediction or verified commercial opportunity')
root = Path(os.environ.get('GEOAI_OUTPUT_DIR', 'data/processed'))
zones_file, cafes_file, report_file = (root / name for name in ('zones.geoparquet', 'cafes.geoparquet', 'quality.json'))

if not all(p.is_file() for p in (zones_file, cafes_file, report_file)):
    st.info('No verified territorial dataset loaded. Run the territorial pipeline with official local zones and cached or live OSM data; see README.')
else:
    try:
        zones = gpd.read_parquet(zones_file).to_crs(4326)
        cafes = gpd.read_parquet(cafes_file).to_crs(4326)
        report = json.loads(report_file.read_text(encoding='utf-8'))
        st.caption(f"Zones: {report['zone_source']} · OSM: {report['osm_source']} · retrieved (UTC): {', '.join(report['osm_retrieved_at_utc']) or 'unknown'} · Census: {report['census_source'] or 'not loaded'}")
        st.caption('© OpenStreetMap contributors · ODbL · https://www.openstreetmap.org/copyright · INE Censo 2024: see source metadata and terms')
        st.warning('Low coffee-shop coverage is not proven business opportunity. Residential population is not commercial demand, especially in tourist areas. OSM may be incomplete; zone centroids and borders affect distances.')
        if report['census_source'] is None:
            st.info('Population layer unavailable: no verified INE census table loaded.')
        choices = zones.zone_id.astype(str).tolist()
        selected = st.multiselect('Compare zones', choices, default=choices[:min(2, len(choices))])
        metric = st.selectbox('Zone color', ['cafe_density_km2', 'cafe_count', 'population'])
        colors = zones[metric].fillna(0)
        scale = max(float(colors.max()), 1)
        mapped = zones.copy()
        mapped['fill'] = [[int(230 * min(float(v) / scale, 1)), 80, 140, 90] if pd.notna(v) else [120, 120, 120, 70] for v in zones[metric]]
        layers = [pdk.Layer('GeoJsonLayer', mapped[['zone_id', 'comuna', metric, 'fill', 'geometry']].__geo_interface__, get_fill_color='properties.fill', get_line_color=[40, 40, 40], pickable=True)]
        if len(cafes):
            coords = cafes[['osm_id', 'name']].copy()
            coords['lon'] = cafes.geometry.x
            coords['lat'] = cafes.geometry.y
            layers.append(pdk.Layer('ScatterplotLayer', coords, get_position='[lon, lat]', get_radius=45, get_fill_color=[35, 70, 210], pickable=True))
        st.pydeck_chart(pdk.Deck(layers=layers, initial_view_state=pdk.ViewState(latitude=-33.01, longitude=-71.55, zoom=10), tooltip={'text': '{zone_id} {name}'}))
        visible = ['zone_id', 'comuna', 'cafe_count', 'cafe_density_km2', 'nearest_cafe_m', 'cafes_300m', 'cafes_500m', 'cafes_1000m', 'population', 'cafes_per_1000_residents']
        st.subheader('Territorial comparison')
        st.dataframe(zones[zones.zone_id.astype(str).isin(selected)][visible], hide_index=True)
        st.subheader('Exploratory ranking and weight sensitivity')
        density_weight = st.slider('Coffee density weight (negative favors lower density)', -5, 5, -1)
        population_weight = st.slider('Resident population weight (0 disables)', 0, 5, 1 if report['census_source'] else 0)
        weights = {}
        if density_weight:
            weights['cafe_density_km2'] = density_weight
        if population_weight and report['census_source']:
            weights['population'] = population_weight
        if weights:
            ranked = rank_zones(zones.drop(columns='geometry'), weights).sort_values(['score', 'zone_id'], ascending=[False, True], na_position='last')
            st.dataframe(ranked[['zone_id', 'comuna', 'score', 'indicator_coverage'] + [f'contribution_{col}' for col in weights]], hide_index=True)
            st.caption('Min–max indicators computed over loaded zones; a constant indicator receives 0.5. Signed weights set direction; missing indicators are excluded and coverage is displayed. Change weights above to test sensitivity.')
        else:
            st.info('Set at least one nonzero weight to display a ranking.')
        st.json(report)
    except (OSError, ValueError, KeyError, TerritorialError) as exc:
        st.error(f'Territorial dataset invalid or unavailable: {exc}')

st.divider()
st.subheader('GeoML status (separate domain)')
try:
    with urlopen(os.environ.get('GEOAI_API_URL', 'http://localhost:8000') + '/model/info', timeout=3) as response:
        st.json(json.load(response))
except (HTTPError, URLError, TimeoutError, ValueError) as exc:
    st.error(f'API status unavailable: {type(exc).__name__}')
