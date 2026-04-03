"""Observability MCP server — tools for querying VictoriaLogs and VictoriaTraces."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field


# --- Settings ---

class Settings:
    def __init__(self) -> None:
        self.victorialogs_url = os.environ.get(
            "NANOBOT_VICTORIALOGS_URL", "http://localhost:42010"
        ).rstrip("/")
        self.victoriatraces_url = os.environ.get(
            "NANOBOT_VICTORIATRACES_URL", "http://localhost:42011"
        ).rstrip("/")


# --- Tool schemas ---

class LogsSearchArgs(BaseModel):
    query: str = Field(description="LogsQL query string, e.g. 'severity:ERROR'")
    limit: int = Field(default=20, ge=1, le=200, description="Max log entries to return")


class LogsErrorCountArgs(BaseModel):
    minutes: int = Field(default=60, ge=1, description="Time window in minutes")


class TracesListArgs(BaseModel):
    service: str = Field(description="Service name, e.g. 'Learning Management Service'")
    limit: int = Field(default=10, ge=1, le=100, description="Max traces to return")


class TracesGetArgs(BaseModel):
    trace_id: str = Field(description="Trace ID to fetch")


# --- Handlers ---

async def _logs_search(_client: Any, args: LogsSearchArgs) -> str:
    settings = Settings()
    url = f"{settings.victorialogs_url}/select/logsql/query"
    query = args.query
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.post(url, params={"query": query, "limit": args.limit})
        if resp.status_code != 200:
            return f"VictoriaLogs error: {resp.status_code} {resp.text}"
        # Response is newline-delimited JSON
        lines = resp.text.strip().split("\n")
        entries = []
        for line in lines[: args.limit]:
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    entries.append({"raw": line})
        if not entries:
            return "No log entries found for the given query."
        return json.dumps(entries, ensure_ascii=False, indent=2)


async def _logs_error_count(_client: Any, args: LogsErrorCountArgs) -> str:
    settings = Settings()
    query = f'_time:{args.minutes}m severity:ERROR'
    url = f"{settings.victorialogs_url}/select/logsql/query"
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.post(url, params={"query": query, "limit": 1000})
        if resp.status_code != 200:
            return f"VictoriaLogs error: {resp.status_code} {resp.text}"
        lines = resp.text.strip().split("\n")
        errors_by_service: dict[str, int] = {}
        for line in lines:
            if line.strip():
                try:
                    entry = json.loads(line)
                    svc = entry.get("service.name", entry.get("service", "unknown"))
                    errors_by_service[svc] = errors_by_service.get(svc, 0) + 1
                except json.JSONDecodeError:
                    errors_by_service["unknown"] = errors_by_service.get("unknown", 0) + 1
        if not errors_by_service:
            return f"No errors found in the last {args.minutes} minutes."
        result = {"time_window_minutes": args.minutes, "errors_by_service": errors_by_service, "total": sum(errors_by_service.values())}
        return json.dumps(result, ensure_ascii=False, indent=2)


async def _traces_list(_client: Any, args: TracesListArgs) -> str:
    settings = Settings()
    url = f"{settings.victoriatraces_url}/select/jaeger/api/traces"
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.get(url, params={"service": args.service, "limit": args.limit})
        if resp.status_code != 200:
            return f"VictoriaTraces error: {resp.status_code} {resp.text}"
        try:
            data = resp.json()
        except json.JSONDecodeError:
            return f"VictoriaTraces returned non-JSON: {resp.text[:500]}"
        traces = data.get("data", [])
        if not traces:
            return f"No traces found for service '{args.service}'."
        summary = []
        for t in traces[: args.limit]:
            summary.append({
                "traceID": t.get("traceID"),
                "startTime": t.get("startTime"),
                "duration": t.get("duration"),
                "spans": len(t.get("spans", [])),
            })
        return json.dumps({"traces": summary}, ensure_ascii=False, indent=2)


async def _traces_get(_client: Any, args: TracesGetArgs) -> str:
    settings = Settings()
    url = f"{settings.victoriatraces_url}/select/jaeger/api/traces/{args.trace_id}"
    async with httpx.AsyncClient(timeout=30) as http:
        resp = await http.get(url)
        if resp.status_code != 200:
            return f"VictoriaTraces error: {resp.status_code} {resp.text}"
        try:
            data = resp.json()
        except json.JSONDecodeError:
            return f"VictoriaTraces returned non-JSON: {resp.text[:500]}"
        traces = data.get("data", [])
        if not traces:
            return f"No trace found with ID '{args.trace_id}'."
        trace = traces[0]
        spans = []
        for s in trace.get("spans", []):
            tags = {t["key"]: t["value"] for t in s.get("tags", []) if isinstance(t, dict) and "key" in t}
            spans.append({
                "spanID": s.get("spanID"),
                "operationName": s.get("operationName"),
                "duration": s.get("duration"),
                "statusCode": tags.get("status.code"),
                "statusMessage": tags.get("status.message"),
            })
        return json.dumps({
            "traceID": trace.get("traceID"),
            "startTime": trace.get("startTime"),
            "duration": trace.get("duration"),
            "spans": spans,
        }, ensure_ascii=False, indent=2)


# --- Server ---

TOOL_SPECS = [
    ("mcp_obs_logs_search", "Search VictoriaLogs by LogsQL query. Use query like 'severity:ERROR' or '_time:10m service.name:Learning Management Service severity:ERROR'.", LogsSearchArgs, _logs_search),
    ("mcp_obs_logs_error_count", "Count error logs per service over a time window. Returns error counts grouped by service name.", LogsErrorCountArgs, _logs_error_count),
    ("mcp_obs_traces_list", "List recent traces for a service. Use service name like 'Learning Management Service'.", TracesListArgs, _traces_list),
    ("mcp_obs_traces_get", "Fetch a specific trace by ID. Use trace_id from log entries.", TracesGetArgs, _traces_get),
]


def create_server() -> Server:
    server = Server("observability")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(name=name, description=desc, inputSchema=model.model_json_schema())
            for name, desc, model, _handler in TOOL_SPECS
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
        for tool_name, _, model, handler in TOOL_SPECS:
            if name == tool_name:
                try:
                    args = model.model_validate(arguments or {})
                    result = await handler(None, args)
                    return [TextContent(type="text", text=str(result))]
                except Exception as exc:
                    return [TextContent(type="text", text=f"Error: {type(exc).__name__}: {exc}")]
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

    _ = list_tools, call_tool
    return server


async def main() -> None:
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        init_options = server.create_initialization_options()
        await server.run(read_stream, write_stream, init_options)


if __name__ == "__main__":
    asyncio.run(main())
