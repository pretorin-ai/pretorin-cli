# MCP Resources

The MCP server exposes read-only resources for analysis guidance.

## Available Resources

| Resource URI | Description |
|--------------|-------------|
| `analysis://schema` | JSON schema for compliance artifacts |
| `analysis://guide/{framework_id}` | Analysis guide for a specific framework |
| `analysis://control/{framework_id}/{control_id}` | Analysis guidance for a specific control within one framework scope |

## Usage

Access these resources via `ReadMcpResourceTool` with `server: "pretorin"` in your MCP client.

### Analysis Schema

`analysis://schema`

Returns the JSON schema for structured compliance artifacts. Use this when generating artifact JSON to ensure correct structure. See [Artifact Schema](../reference/artifact-schema.md) for documentation.

### Framework Analysis Guide

`analysis://guide/{framework_id}`

Available framework guides:
- `analysis://guide/fedramp-moderate`
- `analysis://guide/nist-800-53-r5`
- `analysis://guide/nist-800-171-r3`

Returns framework-specific analysis guidance including purpose, target audience, scope, and assessment methodology.

### Control Analysis Guidance

`analysis://control/{framework_id}/{control_id}`

Example: `analysis://control/fedramp-moderate/ac-02`

Returns control-specific analysis guidance including search patterns, evidence examples, and assessment criteria for one framework scope.
