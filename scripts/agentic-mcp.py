#!/usr/bin/env python3
"""Agent-scoped MCP bridge from OpenClaw to Pengurusan AI workflows."""

import asyncio
import json
import os
import urllib.request

from mcp.server.fastmcp import FastMCP


API_BASE = os.getenv('PENGURUSAN_AI_API_BASE', 'http://127.0.0.1:8080/api/v1/agentic-workflows').rstrip('/')
AGENT_ID = os.environ['PENGURUSAN_AI_AGENT_ID']
TOKEN = os.environ['AGENTIC_MCP_TOKEN']


def request(path: str, payload: dict | None = None):
    body = json.dumps(payload).encode() if payload is not None else None
    operation = urllib.request.Request(
        f'{API_BASE}{path}',
        data=body,
        headers={'Authorization': f'Bearer {TOKEN}', 'Content-Type': 'application/json'},
        method='POST' if payload is not None else 'GET',
    )
    with urllib.request.urlopen(operation, timeout=30) as response:
        return json.load(response)


mcp = FastMCP('Pengurusan AI Agentic Workflows')
catalog = request(f'/tools/catalog/{AGENT_ID}')


def register_tool(item: dict):
    async def run(message: str, job_id: str = '') -> dict:
        """Start a durable ordered OpenClaw agent workflow."""
        return await asyncio.to_thread(
            request,
            f'/tools/{item["name"]}/invoke',
            {'caller_agent_id': AGENT_ID, 'message': message, 'job_id': job_id or None},
        )

    mcp.add_tool(run, name=item['name'], title=item['title'], description=item['description'])


for catalog_item in catalog:
    register_tool(catalog_item)


if __name__ == '__main__':
    mcp.run(transport='stdio')
