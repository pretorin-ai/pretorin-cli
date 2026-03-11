# MCP Troubleshooting

## "Not authenticated" Error

Ensure you've logged in:

```bash
pretorin login
pretorin whoami  # Verify authentication
```

## MCP Server Not Found

1. Verify pretorin is installed and in your PATH:

   ```bash
   which pretorin
   pretorin --version
   ```

2. Try using the full path in your configuration:

   ```json
   {
     "mcpServers": {
       "pretorin": {
         "command": "/path/to/pretorin",
         "args": ["mcp-serve"]
       }
     }
   }
   ```

3. For `uv tool` or `pipx` installations, find the path:

   ```bash
   command -v pretorin
   ```

## Server Crashes or Hangs

Check the MCP server logs:

```bash
pretorin mcp-serve 2>&1 | tee mcp-debug.log
```

Ensure your API key is valid:

```bash
pretorin whoami
```

## Framework or Control Not Found

- Verify the framework ID exists: `pretorin frameworks list`
- Verify the control ID exists: `pretorin frameworks controls <framework_id>`
- Check [Control ID Formats](../frameworks/control-ids.md) for correct formatting

## Common ID Mistakes

| Error | Fix |
|-------|-----|
| `ac-1` not found | Use zero-padded: `ac-01` |
| `ac` family not found | Use slug: `access-control` |
| `AC.l2-3.1.1` not found | CMMC is case-sensitive: `AC.L2-3.1.1` |
| `3.1.1` control not found | 800-171 needs leading zeros: `03.01.01` |

## No Systems Found

If `pretorin_list_systems` returns no systems, you need a beta code to create one on the [Pretorin platform](https://platform.pretorin.com). Systems cannot be created through the CLI or MCP. [Sign up for early access](https://pretorin.com/early-access/).

## Rate Limiting

The API uses rate limiting. If you receive `429 Too Many Requests` errors, the client automatically retries with exponential backoff. For persistent issues, reduce request frequency.

## Support

- Documentation: [platform.pretorin.com/api/docs](https://platform.pretorin.com/api/docs)
- Issues: [github.com/pretorin-ai/pretorin-cli/issues](https://github.com/pretorin-ai/pretorin-cli/issues)
- Platform: [platform.pretorin.com](https://platform.pretorin.com)
