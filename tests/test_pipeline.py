import json
import os
import subprocess
import sys

import duckdb


def run_pipeline(tmp_path, domain, source):
    env = {**os.environ, 'GEOAI_OUTPUT_DIR': str(tmp_path / 'processed'),
           'GEOAI_COMMERCIAL_SOURCE': '', 'GEOAI_TERRITORIAL_SOURCE': ''}
    if source is not None:
        env[f'GEOAI_{domain.upper()}_SOURCE'] = str(source)
    return subprocess.run([sys.executable, '-m', 'geoopportunity.data.pipeline',
                           '--domain', domain], capture_output=True, text=True, env=env)


def test_missing_input_fails_without_creating_output(tmp_path):
    result = run_pipeline(tmp_path, 'commercial', tmp_path / 'absent.csv')
    assert result.returncode == 2
    assert result.stdout == ''
    assert result.stderr == 'Input file does not exist: ' + str(tmp_path / 'absent.csv') + '\n'
    assert not (tmp_path / 'processed').exists()


def test_unconfigured_source_does_not_create_output(tmp_path):
    result = run_pipeline(tmp_path, 'commercial', None)
    assert result.returncode == 2
    assert result.stdout == ''
    assert result.stderr == 'No source configured for commercial\n'
    assert not (tmp_path / 'processed').exists()


def test_empty_source_does_not_create_output(tmp_path):
    source = tmp_path / 'empty.csv'
    source.write_text('store,sales\n', encoding='utf-8')
    result = run_pipeline(tmp_path, 'commercial', source)
    assert result.returncode == 2
    assert result.stdout == ''
    assert result.stderr == f'Input contains no rows: {source}\n'
    assert not (tmp_path / 'processed').exists()


def test_commercial_csv_is_ingested_only_from_configured_source(tmp_path):
    source = tmp_path / 'actual.csv'
    source.write_text('store,sales\nA,42\n', encoding='utf-8')
    result = run_pipeline(tmp_path, 'commercial', source)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ''
    assert json.loads(result.stdout) == {'domain': 'commercial', 'rows': 1,
                                         'output': str(tmp_path / 'processed' / 'commercial.parquet')}
    assert duckdb.sql("SELECT store, sales FROM read_parquet(?)", params=[str(tmp_path / 'processed' / 'commercial.parquet')]).fetchall() == [('A', 42)]


def test_existing_output_is_not_overwritten(tmp_path):
    source = tmp_path / 'actual.csv'
    source.write_text('store\nA\n', encoding='utf-8')
    first = run_pipeline(tmp_path, 'commercial', source)
    assert first.returncode == 0
    target = tmp_path / 'processed' / 'commercial.parquet'
    original = target.read_bytes()
    second = run_pipeline(tmp_path, 'commercial', source)
    assert second.returncode == 2
    assert second.stdout == ''
    assert second.stderr == f'Output already exists: {target}\n'
    assert target.read_bytes() == original


def test_territorial_geojson_retains_geometry(tmp_path):
    source = tmp_path / 'places.geojson'
    source.write_text(json.dumps({'type': 'FeatureCollection', 'features': [
        {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [-71.6, -33.0]},
         'properties': {'name': 'fixture'}}]}), encoding='utf-8')
    result = run_pipeline(tmp_path, 'territorial', source)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ''
    import geopandas as gpd
    frame = gpd.read_parquet(tmp_path / 'processed' / 'territorial.parquet')
    assert frame['name'].tolist() == ['fixture']
    assert frame.geometry.iloc[0].x == -71.6
