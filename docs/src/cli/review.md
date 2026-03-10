# Review Commands

The `review` command group helps you review local code against framework controls.

## Run a Review

```bash
# Uses active context for system/framework
pretorin review run --control-id ac-02 --path ./src

# Explicit system/framework override
pretorin review run --control-id ac-02 --framework-id nist-800-53-r5 --path ./src
```

`pretorin review run` does not push narratives or evidence to the platform. In normal mode, it fetches control requirements and current implementation details for comparison. In `--local` mode, it writes a markdown review artifact under `.pretorin/reviews/` or the path specified with `--output-dir`.

## Check Implementation Status

```bash
$ pretorin review status --control-id ac-02
╭─────────────────── Control AC-02 Status ───────────────────────╮
│ Status: in_progress                                             │
│ Evidence items: 3                                               │
│ Narrative: This control is implemented through centralized     │
│ account management using Azure AD...                           │
╰─────────────────────────────────────────────────────────────────╯
```
