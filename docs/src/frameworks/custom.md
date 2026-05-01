# Custom Frameworks

The `pretorin frameworks` command group supports authoring, validating, and uploading **custom and forked compliance frameworks** through the platform's revision-lifecycle endpoints.

The canonical artifact is `unified.json`. **`_index.json` is not an upload format** — it's an internal index file used elsewhere in the data pipeline, but the platform's revision lifecycle expects the full `unified.json`.

## End-to-end workflow

```
init-custom ──► (edit) ──► validate-custom ──► upload-custom [--publish] ──► revisions
                                                          │
build-custom ◄────── (OSCAL or custom catalog as input) ──┘
```

## Starting from scratch

Scaffold a minimal valid `unified.json`:

```bash
pretorin frameworks init-custom acme-soc2-tailored
# → writes unified.json with one sample family + one sample control
```

Edit the file, fill in your metadata, families, and controls, then run a local pre-flight check:

```bash
pretorin frameworks validate-custom unified.json
```

The bundled JSON Schema validator catches structural errors fast. The platform runs the authoritative validator on upload — additional issues may surface there.

## Starting from OSCAL

Already have an OSCAL catalog? Convert it to `unified.json`:

```bash
pretorin frameworks build-custom my-oscal-catalog.json -f acme-iso27001 -o unified.json
```

The CLI auto-detects the input shape. OSCAL → unified preserves the `_oscal` blocks for lossless regeneration; you can round-trip back via `export-oscal`.

## Starting from a custom catalog

Many compliance catalogs ship in custom (non-OSCAL) JSON shapes — `control_families + controls`, CIS-style nested safeguards, ISO `control_themes`, PCI-DSS, CSA-CCM domains, NIST AI RMF governance requirements, FIPS 140-3, DISA STIG wrappers, MITRE ATLAS, and more.

`build-custom` recognizes 12 known custom shapes and normalizes them all to `unified.json`:

```bash
pretorin frameworks build-custom catalog.json -f acme-soc2 -o unified.json
```

If the input shape isn't recognized, the CLI tells you which shapes are supported. Use `init-custom` to scaffold instead and copy your data over manually.

## Uploading

Upload a draft revision to the platform:

```bash
pretorin frameworks upload-custom unified.json
```

The platform validates synchronously. On a validation failure (HTTP 400) the CLI renders the platform's structured `validation_report` as a readable table — you'll see exact paths and messages for what to fix.

To upload and publish in one step:

```bash
pretorin frameworks upload-custom unified.json --publish
```

You can override the framework ID baked into the artifact and add a version label:

```bash
pretorin frameworks upload-custom unified.json -f acme-soc2-v2 -v "2026-Q1"
```

## Linked forks

Fork a Pretorin-managed framework into your own draft. The platform records the lineage so you can rebase later when upstream advances.

```bash
pretorin frameworks fork-framework nist-800-53-r5 acme-nist-tailored
pretorin frameworks fork-framework fedramp-moderate acme-fedramp-mod -v initial
```

The fork starts as a draft anchored on the upstream's current revision. Edit the resulting unified.json (export it from the platform UI or use `revisions` to find the draft), then re-upload via `upload-custom`.

### Rebasing a fork

When upstream has advanced and you want to bring your fork forward:

```bash
pretorin frameworks rebase-fork acme-nist-tailored
```

The platform creates a fresh draft anchored on the latest upstream. You resolve any divergence locally and re-upload.

## Listing revisions

See all drafts and published revisions for a framework:

```bash
pretorin frameworks revisions acme-nist-tailored
```

## Exporting OSCAL

Regenerate an OSCAL catalog from a unified artifact:

```bash
pretorin frameworks export-oscal unified.json -o catalog.json
```

When the unified artifact retains the `_oscal` blocks (i.e., it was originally converted from OSCAL via `build-custom`), regeneration is lossless — props, parts, links, and back-matter are restored verbatim.

## Command reference

| Command | Talks to platform? | Purpose |
|---|---|---|
| `init-custom <id> [-t title] [-o path] [--force]` | No | Scaffold a minimal valid `unified.json` |
| `validate-custom <path>` | No | Local JSON Schema pre-flight |
| `build-custom <input> -f <id> [-o path] [--force]` | No | Normalize OSCAL / custom catalog → `unified.json` |
| `upload-custom <path> [-f id] [-v label] [--publish]` | Yes | Upload draft revision; optionally publish |
| `fork-framework <upstream_id> <new_id> [-v label]` | Yes | Create linked-fork draft |
| `rebase-fork <id> [-v label]` | Yes | Create rebase draft against latest upstream |
| `revisions <id>` | Yes | List drafts + published revisions |
| `export-oscal <path> [-o path] [--force]` | No | Regenerate OSCAL catalog from `unified.json` |

All commands respect the global `--json` flag for machine-readable output.

## Notes for tool authors

The vendored conversion and validation primitives are exposed at `pretorin.frameworks` and can be imported directly:

```python
from pretorin.frameworks import (
    custom_to_unified,
    oscal_to_unified,
    unified_to_oscal,
)
from pretorin.frameworks.validate import validate_unified
from pretorin.frameworks.templates import minimal_unified
```

These are pure-data functions — no I/O, no platform calls. Good for embedding in CI pipelines, agent tools, or your own automation.
