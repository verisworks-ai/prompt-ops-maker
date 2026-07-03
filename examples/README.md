# Examples

## Public web audit

```bash
prompt-ops-maker make-adhoc \
  --name "Public Web Service" \
  --type web-public \
  --task "Launch readiness audit" \
  --risk "secret output, private route exposure, unapproved deploy" \
  --effort high \
  --target-ai codex \
  --environment local \
  --dry-run
```

## MCP operations audit

```bash
prompt-ops-maker make-adhoc \
  --name "MCP tool server" \
  --type automation-pipeline \
  --task "Tool/resource/prompt audit" \
  --risk "missing auth, external API cost, incomplete tool output" \
  --effort high \
  --target-ai mcp \
  --environment mcp \
  --dry-run
```
