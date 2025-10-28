#!/usr/bin/env python3
"""
Quickstart Example: Using the Agentic Fabric SDK

This script demonstrates the basic usage of the SDK.

Prerequisites:
1. Authenticate: afctl auth login
2. Get your token: cat ~/.agentic-fabric/tokens.json | jq -r '.access_token'
3. Export it: export AF_TOKEN="your_token_here"

Then run:
    python examples/quickstart.py
"""

import asyncio
import os
from af_sdk import FabriqClient


async def main():
    """Main function demonstrating SDK usage."""
    
    # Get token from environment
    token = os.getenv("AF_TOKEN")
    if not token:
        print("❌ Error: AF_TOKEN environment variable not set")
        print("\n📝 To fix this:")
        print("   1. Login: afctl auth login")
        print("   2. Get token: cat ~/.agentic-fabric/tokens.json | jq -r '.access_token'")
        print('   3. Export: export AF_TOKEN="your_token_here"')
        print("   4. Run again: python examples/quickstart.py")
        return
    
    base_url = os.getenv("AF_BASE_URL", "https://dashboard.agenticfabriq.com")
    
    print("🚀 Agentic Fabric SDK - Quickstart Example")
    print("=" * 60)
    print(f"📍 Base URL: {base_url}")
    print()
    
    # Initialize the SDK client
    async with FabriqClient(
        base_url=base_url,
        auth_token=token,
        timeout=30.0,
        retries=3
    ) as client:
        
        # Example 1: List tools
        print("1️⃣  Listing tools...")
        try:
            tools_response = await client.list_tools(page=1, page_size=10)
            total = tools_response.get("total", 0)
            tools = tools_response.get("tools", [])
            
            print(f"   ✅ Found {total} tool(s)")
            for tool in tools[:3]:  # Show first 3
                print(f"      - {tool.get('name', 'Unknown')}: {tool.get('description', 'No description')[:50]}")
            if total > 3:
                print(f"      ... and {total - 3} more")
        except Exception as e:
            print(f"   ❌ Failed: {type(e).__name__}: {e}")
        
        print()
        
        # Example 2: List agents
        print("2️⃣  Listing agents...")
        try:
            agents_response = await client.list_agents()
            agents = agents_response.get("agents", [])
            
            print(f"   ✅ Found {len(agents)} agent(s)")
            for agent in agents[:3]:  # Show first 3
                print(f"      - {agent.get('name', 'Unknown')}: {agent.get('description', 'No description')[:50]}")
            if len(agents) > 3:
                print(f"      ... and {len(agents) - 3} more")
        except Exception as e:
            print(f"   ❌ Failed: {type(e).__name__}: {e}")
        
        print()
        
        # Example 3: List MCP servers
        print("3️⃣  Listing MCP servers...")
        try:
            servers_response = await client.list_mcp_servers()
            servers = servers_response.get("servers", [])
            
            print(f"   ✅ Found {len(servers)} MCP server(s)")
            for server in servers[:3]:  # Show first 3
                print(f"      - {server.get('name', 'Unknown')}: {server.get('base_url', 'No URL')}")
            if len(servers) > 3:
                print(f"      ... and {len(servers) - 3} more")
        except Exception as e:
            print(f"   ❌ Failed: {type(e).__name__}: {e}")
        
        print()
        print("=" * 60)
        print("✅ Quickstart complete!")
        print()
        print("📚 Next steps:")
        print("   • Read SDK-USAGE-GUIDE.md for detailed examples")
        print("   • Try: afctl tools add slack --connection-id test --method api --token <token>")
        print("   • Build your own agent using the SDK")


if __name__ == "__main__":
    asyncio.run(main())

