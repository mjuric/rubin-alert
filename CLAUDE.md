# CLAUDE.md

## What this project does

Python package (`rubin_alert_utils`) with a CLI tool (`rubin-alert2json`) that converts Rubin Observatory alert packets from Avro (Confluent Wire Format) to JSON, extracting embedded FITS image cutouts as separate files.

## Architecture

### Package: `rubin_alert_utils`

Single module package. All logic lives in `src/rubin_alert_utils/alert2json.py`.

**Key functions:**

- `fetch_schema(schema_id, registry_url)` -- fetches Avro schema from Confluent schema registry by ID, caches in `_schema_cache` dict
- `read_alert(filepath, schema, registry_url)` -- decompresses `.avro.gz`, strips 5-byte Confluent Wire Format header (magic byte + 4-byte big-endian schema ID), deserializes with `fastavro.schemaless_reader()`
- `process_alert(record, output_dir, alert_id)` -- extracts `cutoutDifference`, `cutoutScience`, `cutoutTemplate` bytes fields as `{alert_id}.{field}.fits` files, replaces field values with filenames
- `AlertEncoder` -- JSON encoder subclass that base64-encodes any `bytes` values not already handled (safety net)
- `main()` -- CLI entry point using argparse, exposed as `rubin-alert2json` console script

**Data flow:** `.avro.gz` file -> gunzip -> strip 5-byte header -> fetch schema by ID -> `fastavro.schemaless_reader()` -> extract FITS cutouts to files -> write JSON

### Alert format details

- Files use Confluent Wire Format: byte 0 is `0x00` (magic), bytes 1-4 are big-endian uint32 schema ID, bytes 5+ are Avro binary payload
- Schema is fetched from `https://usdf-alert-schemas-dev.slac.stanford.edu/schemas/ids/{id}`
- Three cutout fields contain raw FITS file bytes (can be written directly, no processing needed)

## Development

### Environment setup

```bash
pip install -e .
```

Only external dependency is `fastavro`. Everything else is stdlib.

### Running

```bash
rubin-alert2json data/*.avro.gz -o output --pretty
```

### Testing changes

1. Run on a single file: `rubin-alert2json data/170239611403501631.avro.gz -o output --pretty`
2. Verify JSON is valid: `python -m json.tool output/170239611403501631.json > /dev/null`
3. Verify FITS files exist and have valid headers (start with `SIMPLE  =`)
4. Run on all files: `rubin-alert2json data/*.avro.gz -o output --pretty`

### Project layout

```
pyproject.toml
src/rubin_alert_utils/
    __init__.py
    alert2json.py       # All logic and CLI entry point
data/                   # Sample .avro.gz alert files
output/                 # Generated output (not checked in)
```
