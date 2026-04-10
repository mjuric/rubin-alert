# rubin-alert

Convert [Rubin Observatory](https://rubinobservatory.org/) alert packets to JSON with extracted FITS cutout images.

Rubin alerts are serialized as [Apache Avro](https://avro.apache.org/) using the [Confluent Wire Format](https://docs.confluent.io/platform/current/schema-registry/fundamentals/serdes-develop/index.html#wire-format) and contain embedded FITS image cutouts (30x30 pixel postage stamps). This tool deserializes them into human-readable JSON and writes the cutout images as standalone FITS files.

## Setup

Create a conda environment with the required dependencies:

```bash
mamba create -p .venv python=3.13 fastavro -y
```

## Usage

```
.venv/bin/python alert2json.py [options] FILE [FILE ...]
```

Convert one alert:

```bash
.venv/bin/python alert2json.py data/170239611403501631.avro.gz -o output --pretty
```

Convert all alerts in `data/`:

```bash
.venv/bin/python alert2json.py data/*.avro.gz -o output --pretty
```

### Options

| Flag | Description |
|------|-------------|
| `-o`, `--outdir DIR` | Output directory (default: current directory) |
| `--pretty` | Pretty-print JSON output |
| `--schema PATH` | Local Avro schema JSON file (skip registry fetch) |
| `--registry-url URL` | Schema registry base URL (default: USDF dev registry) |

### Output structure

All output files go into a single flat directory, prefixed by alert ID:

```
output/
  170239611403501631.json                    # Alert data as JSON
  170239611403501631.cutoutDifference.fits   # Difference image cutout
  170239611403501631.cutoutScience.fits      # Science image cutout
  170239611403501631.cutoutTemplate.fits     # Template image cutout
```

In the JSON file, cutout fields are replaced with the filenames of the extracted FITS files (or `null` if the cutout was not present in the alert).

## Schema resolution

The tool reads the schema ID from the Confluent Wire Format header embedded in each alert file and fetches the corresponding Avro schema from the [USDF schema registry](https://usdf-alert-schemas-dev.slac.stanford.edu). Schemas are cached in memory so the registry is only queried once per schema ID.

For offline use, pass a local schema file with `--schema`.

## Alert format reference

- [lsst/alert_packet](https://github.com/lsst/alert_packet) -- official Avro schema definitions
- [DMTN-093](https://dmtn-093.lsst.io/) -- design of the LSST Alert Distribution System
- [lsst-dm/sample_alert_info](https://github.com/lsst-dm/sample_alert_info) -- sample alert release notes
