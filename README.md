# Agentic Fabriq SDK

`agentic-fabriq-sdk` provides a Python SDK and CLI tool for interacting with Agentic Fabriq.

**What's included:**
- 🐍 **Python SDK**: High-level client (`af_sdk.FabriqClient`) and DX layer
- 🛠️ **CLI Tool**: `afctl` command for authentication and management
- 🔐 **OAuth2/PKCE**: Secure browser-based authentication with token storage

## Install

```bash
pip install agentic-fabriq-sdk
```

This installs both the Python library and the `afctl` CLI tool.

## Quickstart

### CLI Tool

Authenticate and manage your Agentic Fabriq resources:

```bash
# Login with OAuth2 (browser opens automatically)
afctl auth login

# Check authentication status
afctl auth status

# List available tools
afctl tools list

# List agents
afctl agents list

# Get help
afctl --help
```

### Python SDK

```python
from af_sdk.fabriq_client import FabriqClient

TOKEN = "..."  # Bearer JWT for the Fabriq Gateway
BASE = "https://dashboard.agenticfabriq.com"

async def main():
    async with FabriqClient(base_url=BASE, auth_token=TOKEN) as af:
        # List tools and agents
        tools = await af.list_tools()
        agents = await af.list_agents()
        
        # Invoke Slack tools
        result = await af.invoke_connection("my-slack", method="get_channels")
        
        # Post a Slack message
        await af.invoke_connection(
            "my-slack",
            method="post_message",
            parameters={"channel": "test", "text": "Hello from SDK!"}
        )
        
        # Get Gmail emails
        result = await af.invoke_connection(
            "gmail_work",
            method="get_emails",
            parameters={"max_results": 10, "q": "is:unread"}
        )
        emails = result.get("emails", [])
        
        # Send an email
        await af.invoke_connection(
            "gmail_work",
            method="send_email",
            parameters={
                "to": "recipient@example.com",
                "subject": "Hello from SDK",
                "body": "This email was sent via Agentic Fabric SDK!"
            }
        )
```

DX orchestration:

```python
from af_sdk.dx import ToolFabric, AgentFabric, Agent, tool

slack = ToolFabric(provider="slack", base_url="https://dashboard.agenticfabriq.com", access_token=TOKEN, tenant_id=TENANT)
agents = AgentFabric(base_url="https://dashboard.agenticfabriq.com", access_token=TOKEN, tenant_id=TENANT)

@tool
def echo(x: str) -> str:
    return x

bot = Agent(
    system_prompt="demo",
    tools=[echo],
    agents=agents.get_agents(["summarizer"]),
    base_url="https://dashboard.agenticfabriq.com",
    access_token=TOKEN,
    tenant_id=TENANT,
    provider_fabrics={"slack": slack},
)
print(bot.run("Summarize my Slack messages"))
```

## License

Apache-2.0
