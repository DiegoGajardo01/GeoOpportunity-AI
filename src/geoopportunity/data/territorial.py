"""Explicit, local-first territorial analysis; no synthetic observations or sales model."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon


METRIC_CRS = 'EPSG:32719'  # UTM 19S, Valparaíso metropolitan area
OVERPASS_URL = 'https://overpass-api.de/api/interpreter'


class TerritorialError(ValueError):
    """Invalid source or unavailable territorial data."""


def validate_zones(zones):
    if zones.crs is None:
        raise TerritorialError('Zone CRS is required')
    if not {'zone_id', 'comuna'} <= set(zones.columns):
        raise TerritorialError('Zones require zone_id and comuna')
    if zones.empty or zones.zone_id.isna().any() or zones.zone_id.astype(str).duplicated().any():
        raise TerritorialError('Zone IDs must be nonempty and unique')
    if not zones.comuna.isin(['Valparaíso', 'Viña del Mar']).all():
        raise TerritorialError('Only Valparaíso and Viña del Mar are supported')
    if zones.geometry.isna().any() or zones.geometry.is_empty.any() or not zones.geometry.is_valid.all() or not zones.geom_type.isin(['Polygon', 'MultiPolygon']).all():
        raise TerritorialError('Invalid zone geometry')
    projected = zones.to_crs(METRIC_CRS)
    if (projected.geometry.area <= 0).any():
        raise TerritorialError('Invalid zone geometry: zero area')
    return projected


def cafes_from_osm(payload):
    """Deduplicate only identical OSM type+ID, not proximity or similar names."""
    records = {}
    for element in payload.get('elements', []):
        tags = element.get('tags', {})
        if tags.get('amenity') != 'cafe' or element.get('type') not in ('node', 'way', 'relation'):
            continue
        try:
            osm_id = f"{element['type']}/{element['id']}"
            source_geometry = None
            if element['type'] == 'node':
                geom = Point(element['lon'], element['lat'])
            elif element.get('geometry') and len(element['geometry']) >= 4:
                coords = [(point['lon'], point['lat']) for point in element['geometry']]
                if coords[0] == coords[-1]:
                    polygon = Polygon(coords)
                    if not polygon.is_valid:
                        continue
                    source_geometry = polygon.wkt
                    geom = polygon.representative_point()
                else:
                    center = element['center']
                    geom = Point(center['lon'], center['lat'])
            else:
                center = element['center']
                geom = Point(center['lon'], center['lat'])
            if geom.is_empty or not geom.is_valid or not (-180 <= geom.x <= 180 and -90 <= geom.y <= 90):
                continue
            candidate = {'osm_id': osm_id, 'name': tags.get('name'), 'tags': json.dumps(tags, sort_keys=True, ensure_ascii=False), 'source_geometry_wkt': source_geometry, 'geometry': geom}
            if osm_id not in records or (records[osm_id]['name'] is None and candidate['name'] is not None):
                records[osm_id] = candidate
        except (KeyError, TypeError, ValueError):
            continue
    return gpd.GeoDataFrame([records[key] for key in sorted(records)], columns=['osm_id', 'name', 'tags', 'source_geometry_wkt', 'geometry'], geometry='geometry', crs='EPSG:4326')


def fetch_osm(zones, cache_dir, offline=False, endpoint=OVERPASS_URL):
    """One bounded Overpass query per supplied commune; cached by query, no uncached offline fallback."""
    metric = validate_zones(zones)
    cache_dir = Path(cache_dir)
    results = []
    timestamps = []
    for comuna in ('Valparaíso', 'Viña del Mar'):
        subset = metric[metric.comuna == comuna]
        if subset.empty:
            continue
        # Include 1 km context for radius/nearest distances near the analysis boundary.
        envelope = gpd.GeoSeries([subset.geometry.union_all().buffer(1000)], crs=METRIC_CRS).to_crs(4326).iloc[0]
        south, west, north, east = envelope.bounds[1], envelope.bounds[0], envelope.bounds[3], envelope.bounds[2]
        query = f'[out:json][timeout:45];(node["amenity"="cafe"]({south:.6f},{west:.6f},{north:.6f},{east:.6f});way["amenity"="cafe"]({south:.6f},{west:.6f},{north:.6f},{east:.6f});relation["amenity"="cafe"]({south:.6f},{west:.6f},{north:.6f},{east:.6f}););out center geom;'
        cache = cache_dir / f'osm-{comuna.lower().replace(" ", "-")}-{hashlib.sha256(query.encode()).hexdigest()[:16]}.json'
        if cache.exists():
            payload = json.loads(cache.read_text(encoding='utf-8'))
            timestamps.append(datetime.fromtimestamp(cache.stat().st_mtime, timezone.utc).isoformat())
        elif offline:
            raise TerritorialError(f'No cached OSM response for {comuna}: {cache}')
        else:
            payload = None
            for attempt in range(3):
                try:
                    request = Request(endpoint, data=urlencode({'data': query}).encode(), headers={'User-Agent': 'GeoOpportunityAI/0.1 (territorial research; see repository README)'})
                    with urlopen(request, timeout=60) as response:
                        payload = json.load(response)
                    if 'elements' not in payload:
                        raise TerritorialError('OSM response lacks elements')
                    break
                except (HTTPError, URLError, TimeoutError, OSError, ValueError) as exc:
                    if isinstance(exc, HTTPError) and exc.code not in (429, 502, 503, 504):
                        raise TerritorialError(f'OSM HTTP error: {exc.code}') from exc
                    if attempt == 2:
                        raise TerritorialError(f'OSM unavailable for {comuna}: {exc}') from exc
                    time.sleep(2 * (attempt + 1))
            cache_dir.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
            timestamps.append(datetime.now(timezone.utc).isoformat())
            time.sleep(1)
        if 'elements' not in payload:
            raise TerritorialError('Cached OSM response lacks elements')
        results.extend(payload['elements'])
    return cafes_from_osm({'elements': results}), timestamps


def attach_census(zones, census, id_column, population_column):
    """Official join key must be declared after consulting the INE dictionary."""
    if id_column not in census or population_column not in census:
        raise TerritorialError('Census mapping columns not found')
    ids = census[id_column].astype('string')
    if ids.isna().any() or ids.duplicated().any():
        raise TerritorialError('Duplicate census IDs or missing IDs')
    if zones.zone_id.astype('string').isna().any() or zones.zone_id.astype('string').duplicated().any():
        raise TerritorialError('Duplicate zone IDs or missing IDs')
    values = census[[id_column, population_column]].copy()
    values[id_column] = ids
    values['population_raw'] = values[population_column].astype('string')
    values['population'] = pd.to_numeric(values[population_column], errors='coerce')
    if (values.population.dropna() < 0).any() or (values.population.dropna() % 1 != 0).any():
        raise TerritorialError('Census population must be nonnegative whole persons')
    result = zones.assign(_join_id=zones.zone_id.astype('string')).merge(values[[id_column, 'population', 'population_raw']], left_on='_join_id', right_on=id_column, how='left', validate='one_to_one', indicator='_census_match').drop(columns=['_join_id', id_column])
    result['population_status'] = 'available'
    result.loc[result['_census_match'] == 'left_only', 'population_status'] = 'unmatched_id'
    result.loc[(result['_census_match'] == 'both') & result.population_raw.isna(), 'population_status'] = 'missing'
    result.loc[(result['_census_match'] == 'both') & result.population_raw.notna() & result.population.isna(), 'population_status'] = 'non_numeric_or_protected'
    result = result.drop(columns=['_census_match'])
    return gpd.GeoDataFrame(result, geometry='geometry', crs=zones.crs)


def indicators(zones, cafes):
    metric = validate_zones(zones)
    if cafes.crs is None:
        raise TerritorialError('Cafe CRS is required')
    if cafes.geometry.isna().any() or cafes.geometry.is_empty.any() or not cafes.geometry.is_valid.all():
        raise TerritorialError('Invalid cafe geometry')
    points = cafes.to_crs(METRIC_CRS).geometry
    if not points.geom_type.isin(['Point']).all():
        raise TerritorialError('Cafes must be normalized to points')
    result = metric.copy()
    result['area_km2'] = metric.geometry.area / 1_000_000
    # Representative point is guaranteed inside a polygon, unlike a concave centroid.
    centers = metric.geometry.representative_point()
    result['cafe_count'] = [int(points.intersects(geom).sum()) for geom in metric.geometry]
    result['cafe_density_km2'] = result.cafe_count / result.area_km2
    result['nearest_cafe_m'] = [float(points.distance(p).min()) if len(points) else float('nan') for p in centers]
    for radius in (300, 500, 1000):
        result[f'cafes_{radius}m'] = [int((points.distance(p) <= radius).sum()) for p in centers]
    if 'population' not in result:
        result['population'] = float('nan')
        result['population_status'] = 'not_loaded'
    result['cafes_per_1000_residents'] = result.cafe_count * 1000 / result.population.where(result.population > 0)
    return result


def rank_zones(frame, weights):
    """Per-indicator min/max; negative weights favor low values; renormalize present weights."""
    if not weights or any(not isinstance(w, (int, float)) or not pd.notna(w) or w == 0 for w in weights.values()):
        raise TerritorialError('Weights must be finite and nonzero')
    result = frame.copy()
    denom = sum(abs(w) for w in weights.values())
    contributions = []
    present = []
    for column, weight in weights.items():
        if column not in frame:
            raise TerritorialError(f'Indicator missing: {column}')
        series = pd.to_numeric(frame[column], errors='coerce')
        if (series.dropna() < 0).any():
            raise TerritorialError(f'Negative indicator: {column}')
        low, high = series.min(), series.max()
        normalized = (series - low) / (high - low) if pd.notna(low) and high > low else series.apply(lambda v: .5 if pd.notna(v) else float('nan'))
        if weight < 0:
            normalized = 1 - normalized
        key = f'contribution_{column}'
        result[key] = normalized * abs(weight) / denom
        contributions.append(result[key].fillna(0))
        present.append(series.notna() * abs(weight) / denom)
    result['indicator_coverage'] = sum(present)
    result['score'] = sum(contributions) / result.indicator_coverage.where(result.indicator_coverage > 0)
    result['interpretation'] = 'exploratory coverage only; not proven commercial opportunity'
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description='Build territorial GeoParquet from verified local INE zones and OSM')
    parser.add_argument('--zones', type=Path, required=True, help='Official INE manzana GeoParquet or GeoJSON with zone_id and comuna')
    parser.add_argument('--census', type=Path, help='Local INE statistics CSV or Parquet')
    parser.add_argument('--id-column', help='Verified INE geographic ID column')
    parser.add_argument('--population-column', help='Verified resident population column from INE dictionary')
    parser.add_argument('--cache', type=Path, default=Path('data/raw/osm-cache'))
    parser.add_argument('--output', type=Path, default=Path('data/processed'))
    parser.add_argument('--offline', action='store_true', help='Use cached OSM responses only')
    args = parser.parse_args(argv)
    try:
        if not args.zones.is_file():
            raise TerritorialError(f'Zone file missing: {args.zones}')
        zones = gpd.read_parquet(args.zones) if args.zones.suffix == '.parquet' else gpd.read_file(args.zones)
        zones = validate_zones(zones)
        if args.census:
            if not args.census.is_file() or not args.id_column or not args.population_column:
                raise TerritorialError('Census file and verified ID/population columns required')
            census = pd.read_parquet(args.census) if args.census.suffix == '.parquet' else pd.read_csv(args.census, dtype={args.id_column: 'string'})
            zones = attach_census(zones, census, args.id_column, args.population_column)
        cafes, dates = fetch_osm(zones, args.cache, offline=args.offline)
        enriched = indicators(zones, cafes)
        targets = [args.output / name for name in ('zones.geoparquet', 'cafes.geoparquet', 'quality.json')]
        if any(target.exists() for target in targets):
            raise TerritorialError('Territorial output already exists; archive or remove it explicitly before rebuilding')
        args.output.mkdir(parents=True, exist_ok=True)
        enriched.to_parquet(targets[0], index=False)
        cafes.to_parquet(targets[1], index=False)
        report = {'zones': len(enriched), 'cafes': len(cafes), 'population_status_counts': enriched.population_status.value_counts().to_dict(), 'zones_without_population': int(enriched.population.isna().sum()), 'zones_without_cafes': int((enriched.cafe_count == 0).sum()), 'osm_retrieved_at_utc': dates, 'osm_source': OVERPASS_URL, 'census_source': str(args.census) if args.census else None, 'zone_source': str(args.zones), 'zone_sha256': hashlib.sha256(args.zones.read_bytes()).hexdigest(), 'census_sha256': hashlib.sha256(args.census.read_bytes()).hexdigest() if args.census else None, 'metric_crs': METRIC_CRS, 'limitations': 'OSM is incomplete; residential population is not commercial demand; zones and source boundaries may omit nearby cafes.'}
        targets[2].write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except (TerritorialError, OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
