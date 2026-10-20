import json

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, box

from geoopportunity.data.territorial import cafes_from_osm, attach_census, indicators, rank_zones, fetch_osm, TerritorialError


def zones():
    return gpd.GeoDataFrame({'zone_id': ['a', 'b'], 'comuna': ['Valparaíso', 'Viña del Mar']}, geometry=[box(260000, 6340000, 261000, 6341000), box(261000, 6340000, 262000, 6341000)], crs=32719)


def test_osm_identity_polygons_and_duplicate_ids():
    raw = {'elements': [{'type': 'node', 'id': 1, 'lat': -33, 'lon': -71.6, 'tags': {'amenity': 'cafe', 'name': 'A'}}, {'type': 'node', 'id': 1, 'lat': -33, 'lon': -71.6, 'tags': {'amenity': 'cafe'}}, {'type': 'way', 'id': 2, 'geometry': [{'lat': -33, 'lon': -71.6}, {'lat': -33, 'lon': -71.599}, {'lat': -33.001, 'lon': -71.599}, {'lat': -33.001, 'lon': -71.6}, {'lat': -33, 'lon': -71.6}], 'tags': {'amenity': 'cafe'}}]}
    cafes = cafes_from_osm(raw)
    assert cafes.osm_id.tolist() == ['node/1', 'way/2']
    assert cafes.name.iloc[0] == 'A'
    assert cafes.geometry.notna().all() and cafes.crs.to_epsg() == 4326
    assert json.loads(cafes.tags.iloc[0])['amenity'] == 'cafe'
    assert cafes.source_geometry_wkt.iloc[1].startswith('POLYGON')


def test_invalid_geometry_rejected():
    bad = zones()
    bad.loc[0, 'geometry'] = None
    with pytest.raises(TerritorialError, match='Invalid zone geometry'):
        indicators(bad, gpd.GeoDataFrame({'osm_id': []}, geometry=[], crs=4326))


def test_metric_distances_edge_and_missing():
    z = zones()
    cafes = gpd.GeoDataFrame({'osm_id': ['node/1']}, geometry=[Point(261050, 6340500)], crs=32719)
    result = indicators(z, cafes)
    assert result.cafe_count.tolist() == [0, 1]
    assert result.nearest_cafe_m.iloc[0] == pytest.approx(550)
    assert result.cafes_300m.tolist() == [0, 0]
    assert result.cafes_500m.tolist() == [0, 1]
    assert result.cafes_1000m.tolist() == [1, 1]
    assert pd.isna(result.cafes_per_1000_residents.iloc[0])
    assert result.cafe_density_km2.iloc[1] == pytest.approx(1)
    transformed = indicators(z.to_crs(4326), cafes.to_crs(4326))
    assert transformed.nearest_cafe_m.tolist() == pytest.approx(result.nearest_cafe_m.tolist(), abs=.01)


def test_census_join_suppression_and_ids():
    z = zones()
    census = pd.DataFrame({'id': ['a', 'b'], 'people': ['12', '*']})
    result = attach_census(z, census, 'id', 'people')
    assert result.population.iloc[0] == 12
    assert pd.isna(result.population.iloc[1])
    assert result.population_status.tolist() == ['available', 'non_numeric_or_protected']
    assert result.population_raw.iloc[1] == '*'
    with pytest.raises(TerritorialError, match='Duplicate census IDs'):
        attach_census(z, pd.concat([census, census.iloc[[0]]]), 'id', 'people')
    unmatched = attach_census(z, pd.DataFrame({'id': ['a'], 'people': ['12']}), 'id', 'people')
    assert unmatched.population_status.tolist() == ['available', 'unmatched_id']


def test_rank_reproducible_missing_and_sensitivity():
    frame = pd.DataFrame({'zone_id': ['a', 'b'], 'cafe_density_km2': [0, 10], 'population': [100, None]})
    one = rank_zones(frame, {'cafe_density_km2': -1, 'population': 1})
    two = rank_zones(frame, {'cafe_density_km2': -1, 'population': 1})
    pd.testing.assert_frame_equal(one, two)
    assert one.loc[0, 'contribution_cafe_density_km2'] == pytest.approx(.5)
    assert pd.isna(one.loc[1, 'contribution_population'])
    assert one.loc[1, 'indicator_coverage'] == pytest.approx(.5)
    other = rank_zones(frame, {'cafe_density_km2': 1})
    assert other.loc[1, 'score'] > other.loc[0, 'score']
    missing = rank_zones(pd.DataFrame({'zone_id': ['a'], 'population': [None]}), {'population': 1})
    assert pd.isna(missing.score.iloc[0]) and missing.indicator_coverage.iloc[0] == 0


def test_offline_requires_cache_without_network(tmp_path):
    with pytest.raises(TerritorialError, match='No cached OSM'):
        fetch_osm(zones(), tmp_path, offline=True)
    assert list(tmp_path.iterdir()) == []


def test_cache_reused_without_network(tmp_path, monkeypatch):
    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *_):
            pass
        def read(self, *_):
            return b'{"elements": []}'
    import geoopportunity.data.territorial as module
    monkeypatch.setattr(module, 'urlopen', lambda *a, **k: Response())
    monkeypatch.setattr(module.time, 'sleep', lambda _: None)
    first, dates = fetch_osm(zones(), tmp_path)
    assert len(first) == 0 and len(dates) == 2
    monkeypatch.setattr(module, 'urlopen', lambda *a, **k: pytest.fail('network accessed in offline mode'))
    second, cached_dates = fetch_osm(zones(), tmp_path, offline=True)
    assert len(second) == 0 and len(cached_dates) == 2
