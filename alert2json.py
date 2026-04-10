#!/usr/bin/env python
"""Convert Rubin Observatory alert packets to JSON with extracted FITS cutouts."""

import argparse
import base64
import gzip
import io
import json
import os
import struct
import urllib.request

import fastavro

CUTOUT_FIELDS = {"cutoutDifference", "cutoutScience", "cutoutTemplate"}
DEFAULT_REGISTRY = "https://usdf-alert-schemas-dev.slac.stanford.edu"

# Cache fetched schemas by ID
_schema_cache = {}


def fetch_schema(schema_id, registry_url):
    """Fetch an Avro schema from the Confluent schema registry."""
    if schema_id in _schema_cache:
        return _schema_cache[schema_id]

    url = f"{registry_url}/schemas/ids/{schema_id}"
    with urllib.request.urlopen(url) as resp:
        data = json.loads(resp.read())
    schema = json.loads(data["schema"])
    _schema_cache[schema_id] = schema
    return schema


def read_alert(filepath, schema=None, registry_url=DEFAULT_REGISTRY):
    """Read and deserialize a Confluent Wire Format Avro alert file."""
    opener = gzip.open if filepath.endswith(".gz") else open
    with opener(filepath, "rb") as f:
        raw = f.read()

    # Confluent Wire Format: 1 byte magic (0x00) + 4 bytes schema ID (big-endian)
    if len(raw) < 5:
        raise ValueError(f"File too small to be a valid alert: {filepath}")
    magic = raw[0]
    if magic != 0:
        raise ValueError(
            f"Expected Confluent magic byte 0x00, got {magic:#04x} in {filepath}"
        )
    schema_id = struct.unpack(">I", raw[1:5])[0]
    payload = raw[5:]

    if schema is None:
        schema = fetch_schema(schema_id, registry_url)

    record = fastavro.schemaless_reader(io.BytesIO(payload), schema)
    return record, schema_id


def process_alert(record, output_dir, alert_id):
    """Extract FITS cutouts to files and replace with filenames in the record."""
    os.makedirs(output_dir, exist_ok=True)

    for field in CUTOUT_FIELDS:
        value = record.get(field)
        if value is not None:
            fits_filename = f"{alert_id}.{field}.fits"
            with open(os.path.join(output_dir, fits_filename), "wb") as f:
                f.write(value)
            record[field] = fits_filename

    return record


class AlertEncoder(json.JSONEncoder):
    """JSON encoder that base64-encodes any remaining bytes fields."""

    def default(self, obj):
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode("ascii")
        return super().default(obj)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert Rubin alert packets to JSON with extracted FITS cutouts."
    )
    parser.add_argument(
        "files", metavar="FILE", nargs="+", help=".avro or .avro.gz alert file(s)"
    )
    parser.add_argument(
        "-o", "--outdir", default=".", help="Output directory (default: current directory)"
    )
    parser.add_argument(
        "--schema", help="Local Avro schema JSON file (skip registry fetch)"
    )
    parser.add_argument(
        "--registry-url",
        default=DEFAULT_REGISTRY,
        help=f"Schema registry base URL (default: {DEFAULT_REGISTRY})",
    )
    parser.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON output"
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    schema = None
    if args.schema:
        with open(args.schema) as f:
            schema = json.load(f)

    os.makedirs(args.outdir, exist_ok=True)

    for filepath in args.files:
        basename = os.path.basename(filepath)
        # Strip .avro.gz or .avro extension to get the alert ID
        alert_id = basename.replace(".avro.gz", "").replace(".avro", "")

        record, schema_id = read_alert(
            filepath, schema=schema, registry_url=args.registry_url
        )
        record = process_alert(record, args.outdir, alert_id)

        json_path = os.path.join(args.outdir, f"{alert_id}.json")
        indent = 2 if args.pretty else None
        with open(json_path, "w") as f:
            json.dump(record, f, cls=AlertEncoder, indent=indent)

        print(f"{filepath} -> {json_path}")


if __name__ == "__main__":
    main()
