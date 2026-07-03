import asyncio
import httpx
import json

def call_mcp_tool(query: str):
    url = "https://mcp.code4code.eu/mcp"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "recherche_base_parlementaire",
            "arguments": {"query": query}
        }
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    resp = httpx.post(url, json=payload, headers=headers, timeout=15.0)
    print(f"DEBUG MCP STATUS: {resp.status_code}")
    print(f"DEBUG MCP BODY: {resp.text}")

call_mcp_tool("Quel est le dernier amendement à ce jour ?")
