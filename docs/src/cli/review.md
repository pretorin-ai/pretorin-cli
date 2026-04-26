# Review Commands

The `review` command group helps you review local code against framework controls.

## Run a Review

```bash
# Uses active context for system/framework
pretorin review run --control-id ac-02 --path ./src

# Explicit system/framework override
pretorin review run --control-id ac-02 --framework-id nist-800-53-r5 --system "My System" --path ./src

# Local-only mode — saves control context as markdown, no system required
pretorin review run --control-id ac-02 --framework-id fedramp-moderate --local

# Custom output directory for local artifacts
pretorin review run --control-id ac-02 --framework-id fedramp-moderate --local --output-dir ./compliance-notes
```

`pretorin review run` does not push narratives or evidence to the platform. In normal mode, it fetches control requirements and current implementation details for comparison. In `--local` mode, it writes a markdown review artifact under `.pretorin/reviews/` or the path specified with `--output-dir`.

### Options

| Option | Description |
|--------|-------------|
| `--control-id` / `-c` | Control ID to review against (required) |
| `--framework-id` / `-f` | Framework ID (uses active context if omitted) |
| `--system` / `-s` | System name or ID (uses active context if omitted) |
| `--path` / `-p` | Path to files to review (default: `.`) |
| `--local` | Force local-only output (no API calls for implementation data) |
| `--output-dir` / `-o` | Output directory for local review artifacts (default: `.pretorin/reviews`) |

## Check Implementation Status

```bash
pretorin review status --control-id ac-02
pretorin review status --control-id sc-07 --framework-id fedramp-moderate --system my-system
```

| Option | Description |
|--------|-------------|
| `--control-id` / `-c` | Control ID (required) |
| `--system` / `-s` | System name or ID (uses active context if omitted) |
| `--framework-id` / `-f` | Framework ID (uses active context if omitted) |
