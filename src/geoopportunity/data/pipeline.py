"""Explicitly configured ingestion. No download, training, or inferred dataset paths."""

import argparse
import json
from pathlib import Path
import sys

import geopandas as gpd
import pandas as pd

from geoopportunity.config import Settings


class PipelineError(Exception):
    """Input/configuration error safe to show to the CLI caller."""


def ingest(domain: str, settings: Settings) -> dict[str, str | int]:
    if domain not in ('commercial', 'territorial'):
        raise PipelineError(f'Unsupported domain: {domain}')
    configured = (settings.commercial_source if domain == 'commercial'
                  else settings.territorial_source)
    if not configured:
        raise PipelineError(f'No source configured for {domain}')
    source = Path(configured)
    if not source.is_file():
        raise PipelineError(f'Input file does not exist: {source}')
    suffix = source.suffix.lower()
    allowed = ('.csv', '.parquet') if domain == 'commercial' else ('.geojson', '.json', '.parquet')
    if suffix not in allowed:
        raise PipelineError(f'Unsupported {domain} input format: {suffix}')

    target = Path(settings.output_dir) / f'{domain}.parquet'
    if target.exists():
        raise PipelineError(f'Output already exists: {target}')

    try:
        if domain == 'commercial':
            frame = pd.read_csv(source) if suffix == '.csv' else pd.read_parquet(source)
        else:
            frame = gpd.read_parquet(source) if suffix == '.parquet' else gpd.read_file(source)
        if frame.empty:
            raise PipelineError(f'Input contains no rows: {source}')
        target.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(target, index=False)
    except PipelineError:
        raise
    except (OSError, ValueError, RuntimeError) as exc:
        target.unlink(missing_ok=True)
        raise PipelineError(f'Failed to ingest {domain}: {exc}') from exc
    return {'domain': domain, 'rows': len(frame), 'output': str(target)}


def main() -> int:
    parser = argparse.ArgumentParser(description='Ingest a configured source into domain-separated Parquet')
    parser.add_argument('--domain', required=True, choices=['commercial', 'territorial'])
    args = parser.parse_args()
    try:
        result = ingest(args.domain, Settings())
    except PipelineError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    sys.exit(main())
