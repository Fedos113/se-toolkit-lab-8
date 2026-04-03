---
name: observability
description: Use observability MCP tools to investigate logs and traces
always: true
---

# Observability Skill

You have access to observability tools that query VictoriaLogs (structured logs) and VictoriaTraces (distributed traces). Use them to investigate system health and errors.

## Available Tools

| Tool | When to Use | Parameters |
|------|-------------|------------|
| `mcp_obs_logs_error_count` | Count errors per service over a time window. Use FIRST when asked about errors or system health. | `minutes` (default 60) |
| `mcp_obs_logs_search` | Search logs by LogsQL query. Use after error_count to inspect specific service errors. | `query`, `limit` |
| `mcp_obs_traces_list` | List recent traces for a service. Use when you need to see request flow. | `service`, `limit` |
| `mcp_obs_traces_get` | Fetch a specific trace by ID. Use when you have a trace_id from logs. | `trace_id` |

## Strategy

### When asked about errors ("Any errors in the last hour?"):
1. Call `mcp_obs_logs_error_count` with an appropriate time window (e.g., `minutes=60`)
2. If errors are found, call `mcp_obs_logs_search` with a scoped query like `_time:10m service.name:"Learning Management Service" severity:ERROR` to inspect details
3. If a `trace_id` appears in the log entries, call `mcp_obs_traces_get` with that ID to see the full request flow
4. Summarize findings concisely — mention which service had errors, what the error was, and any trace evidence

### When asked "What went wrong?" or "Check system health":
1. Call `mcp_obs_logs_error_count` with a fresh recent window (e.g., `minutes=10`)
2. If errors exist, call `mcp_obs_logs_search` scoped to the most likely failing service
3. Extract a `trace_id` from the logs if available
4. Call `mcp_obs_traces_get` for that trace to see the failing request path
5. Provide one short explanation mentioning both log evidence and trace evidence

### Query tips:
- VictoriaLogs field names: `service.name`, `severity`, `event`, `trace_id`
- Good query patterns:
  - `_time:10m severity:ERROR` — errors in last 10 minutes
  - `_time:10m service.name:"Learning Management Service" severity:ERROR` — LMS errors in last 10 minutes
- For VictoriaTraces, use service name exactly as it appears (e.g., "Learning Management Service")

## Response Format
- Keep responses concise — no raw JSON dumps
- Summarize: "Found X errors in the last Y minutes across Z services"
- If citing evidence: "Log entry shows db_query ERROR: <brief error>. Trace shows failure at <operation>."
- If no errors: "No errors found in the last X minutes. The system looks healthy."
