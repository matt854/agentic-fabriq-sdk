# Agentic Fabriq SDK Documentation

Complete reference for the Agentic Fabriq Python SDK.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [Core Client](#core-client-fabriqclient)
- [Building Agents](#building-agents)
- [Building Custom Connectors](#building-custom-connectors)
- [Working with Tools](#working-with-tools)
- [Error Handling](#error-handling)
- [Data Models](#data-models)
- [Complete Examples](#complete-examples)

---

## Installation

```bash
pip install agentic-fabriq-sdk
```

**Requirements:**
- Python 3.11 or higher
- async/await support

**Verify installation:**
```python
import af_sdk
print(af_sdk.__version__)
```

---

## Quick Start

### Minimal Agent Example

```python
from af_sdk import get_application_client

async def my_agent():
    """Minimal agent that accesses tool data."""
    
    # 1. Authenticate as your application
    client = await get_application_client("my-agent-app")
    
    # 2. Access tools and process data
    emails = await client.invoke_connection(
        connection_id="gmail_work",
        method="get_emails",
        parameters={"max_results": 5}
    )
    
    # 3. Process results
    for email in emails.get("emails", []):
        print(f"From: {email['from']}")
        print(f"Subject: {email['subject']}")
    
    # 4. Clean up
    await client.close()

# Run the agent
import asyncio
asyncio.run(my_agent())
```

### Setup Required (One-Time)

Before running your agent, use the CLI to:

```bash
# 1. Authenticate
afctl auth login

# 2. Add tool connections
afctl tools add gmail --connection-id gmail_work --method oauth3
afctl tools connect gmail_work

# 3. Register your application
afctl applications register \
  --app-id my-agent-app \
  --connections gmail:gmail_work

# 4. Activate application (saves credentials locally)
afctl applications connect my-agent-app --token <activation-token>
```

---

## Authentication

### Application Authentication

The recommended way to authenticate SDK applications is using **Application Credentials**.

#### `get_application_client()`

Creates an authenticated client for your application.

**Function Signature:**
```python
async def get_application_client(
    app_id: str,
    config_dir: Optional[Path] = None,
    gateway_url: Optional[str] = None
) -> FabriqClient
```

**Parameters:**
- `app_id` (str): Application identifier
- `config_dir` (Optional[Path]): Custom config directory (default: `~/.af`)
- `gateway_url` (Optional[str]): Gateway URL override (default: from app config)

**Returns:**
- `FabriqClient`: Authenticated client instance

**Raises:**
- `ApplicationNotFoundError`: If application config doesn't exist
- `AuthenticationError`: If authentication fails

**How It Works:**
1. Loads credentials from `~/.af/applications/{app_id}.json`
2. Exchanges credentials for JWT access token
3. Returns authenticated `FabriqClient`

**Example:**
```python
from af_sdk import get_application_client, AuthenticationError

async def main():
    try:
        client = await get_application_client("my-agent-app")
        
        # Client is now authenticated and ready to use
        result = await client.invoke_connection("gmail_work", method="get_emails")
        
        await client.close()
        
    except AuthenticationError as e:
        print(f"Authentication failed: {e}")
```

**Context Manager (Recommended):**
```python
from af_sdk import get_application_client

async def main():
    async with await get_application_client("my-agent-app") as client:
        # Use client
        result = await client.invoke_connection("slack_team", method="get_channels")
        # Automatically closed when exiting context
```

---

### Managing Application Configs

#### `load_application_config()`

Load application config from disk.

```python
from af_sdk import load_application_config

config = load_application_config("my-agent-app")
print(config["app_id"], config["gateway_url"])
```

#### `save_application_config()`

Save application config to disk.

```python
from af_sdk import save_application_config

config = {
    "app_id": "my-bot",
    "secret_key": "sk_...",
    "gateway_url": "https://dashboard.agenticfabriq.com"
}
path = save_application_config("my-bot", config)
```

#### `list_applications()`

List all registered applications.

```python
from af_sdk import list_applications

apps = list_applications()
for app in apps:
    print(f"{app['app_id']}: {app.get('created_at', 'N/A')}")
```

#### `delete_application_config()`

Delete application config from disk.

```python
from af_sdk import delete_application_config

deleted = delete_application_config("my-old-bot")
if deleted:
    print("Deleted successfully")
```

---

## Core Client: FabriqClient

`FabriqClient` is the high-level async client for interacting with Agentic Fabriq Gateway.

### Initialization

**Direct Initialization:**
```python
from af_sdk import FabriqClient

client = FabriqClient(
    base_url="https://dashboard.agenticfabriq.com",
    auth_token="your-jwt-token",
    timeout=30.0,
    retries=3
)
```

**Via Application Auth (Recommended):**
```python
from af_sdk import get_application_client

client = await get_application_client("my-agent-app")
```

**Parameters:**
- `base_url` (str): Gateway base URL
- `auth_token` (Optional[str]): Bearer JWT token
- `api_prefix` (str): API root prefix (default: `/api/v1`)
- `timeout` (float): Request timeout in seconds (default: 30.0)
- `retries` (int): Number of retry attempts (default: 3)
- `backoff_factor` (float): Exponential backoff delay (default: 0.5)
- `trace_enabled` (bool): Enable OpenTelemetry tracing (default: True)
- `extra_headers` (Optional[Dict]): Additional HTTP headers

---

### Tool Methods

#### `invoke_connection()`

Invoke a tool using its connection ID.

**Method Signature:**
```python
async def invoke_connection(
    self,
    connection_id: str,
    *,
    method: str,
    parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

**Parameters:**
- `connection_id` (str): Connection identifier (e.g., 'gmail_work', 'slack_team')
- `method` (str): Tool method to invoke
- `parameters` (Optional[Dict]): Method parameters

**Returns:**
- `Dict[str, Any]`: Tool invocation result

**Example - Gmail:**
```python
# Get emails
result = await client.invoke_connection(
    connection_id="gmail_work",
    method="get_emails",
    parameters={"max_results": 10, "q": "is:unread"}
)
emails = result.get("emails", [])

# Send email
result = await client.invoke_connection(
    connection_id="gmail_work",
    method="send_email",
    parameters={
        "to": "user@example.com",
        "subject": "Hello",
        "body": "Test email from SDK"
    }
)
```

**Example - Google Drive:**
```python
# List files
result = await client.invoke_connection(
    connection_id="drive_work",
    method="list_files"
)

# Search files
result = await client.invoke_connection(
    connection_id="drive_work",
    method="search_files",
    parameters={"query": "name contains 'report'"}
)
```

**Example - Slack:**
```python
# Get channels
result = await client.invoke_connection(
    connection_id="slack_team",
    method="get_channels"
)

# Post message
result = await client.invoke_connection(
    connection_id="slack_team",
    method="post_message",
    parameters={
        "channel": "general",
        "text": "Hello from SDK!"
    }
)
```

**Example - Notion:**
```python
# List pages
result = await client.invoke_connection(
    connection_id="notion_work",
    method="list_pages"
)

# Create page
result = await client.invoke_connection(
    connection_id="notion_work",
    method="create_page",
    parameters={
        "title": "New Page",
        "content": "Page content here"
    }
)
```

---

#### `list_tools()`

List available tools with pagination and search.

**Method Signature:**
```python
async def list_tools(
    self,
    *,
    page: int = 1,
    page_size: int = 20,
    search: Optional[str] = None
) -> Dict[str, Any]
```

**Parameters:**
- `page` (int): Page number (default: 1)
- `page_size` (int): Items per page (default: 20)
- `search` (Optional[str]): Search query

**Returns:**
- `Dict[str, Any]`: List of tools and metadata

**Example:**
```python
# List all tools
tools = await client.list_tools()

# Search for specific tools
gmail_tools = await client.list_tools(search="gmail")

# Pagination
page1 = await client.list_tools(page=1, page_size=10)
page2 = await client.list_tools(page=2, page_size=10)
```

---

### Secret Management

The SDK provides methods to manage secrets via the Gateway-backed Vault API.

#### `get_secret()`

Retrieve a secret by path.

```python
secret = await client.get_secret(path="api-keys/openai")
print(secret["value"])

# Get specific version
secret = await client.get_secret(path="api-keys/openai", version=2)
```

#### `create_secret()`

Create a new secret.

```python
result = await client.create_secret(
    path="api-keys/openai",
    value="sk-...",
    description="OpenAI API key",
    metadata={"env": "production"},
    ttl=86400  # 24 hours
)
```

#### `update_secret()`

Update an existing secret.

```python
result = await client.update_secret(
    path="api-keys/openai",
    value="sk-new-key...",
    description="Updated OpenAI key"
)
```

#### `delete_secret()`

Delete a secret.

```python
result = await client.delete_secret(path="api-keys/openai")
```

---

### Resource Cleanup

Always close the client when done:

**Manual close:**
```python
client = await get_application_client("my-app")
try:
    # Use client
    pass
finally:
    await client.close()
```

**Context manager (recommended):**
```python
async with await get_application_client("my-app") as client:
    # Use client
    pass
# Automatically closed
```

---

## Building Agents

Agents are autonomous programs that use tools to accomplish tasks.

### Complete Agent Example

```python
from af_sdk import get_application_client, AFError
import asyncio
from typing import List, Dict


class EmailProcessorAgent:
    """Agent that processes emails and sends summaries to Slack."""
    
    def __init__(self, app_id: str):
        self.app_id = app_id
        self.client = None
    
    async def start(self):
        """Initialize the agent with authentication."""
        self.client = await get_application_client(self.app_id)
        print(f"✅ Agent authenticated as: {self.app_id}")
    
    async def stop(self):
        """Clean up resources."""
        if self.client:
            await self.client.close()
            print("✅ Agent stopped")
    
    # Tool Access Methods
    
    async def get_emails(self, max_results: int = 10) -> List[Dict]:
        """Get emails from Gmail."""
        try:
            result = await self.client.invoke_connection(
                connection_id="gmail_work",
                method="get_emails",
                parameters={"max_results": max_results}
            )
            return result.get("emails", [])
        except AFError as e:
            print(f"❌ Gmail error: {e}")
            return []
    
    async def send_slack_message(self, channel: str, message: str) -> bool:
        """Send message to Slack."""
        try:
            await self.client.invoke_connection(
                connection_id="slack_team",
                method="post_message",
                parameters={"channel": channel, "text": message}
            )
            return True
        except AFError as e:
            print(f"❌ Slack error: {e}")
            return False
    
    # Agent Intelligence
    
    async def process_emails(self):
        """Main agent logic: process emails and send summary."""
        print("📧 Processing emails...")
        
        # 1. Get emails
        emails = await self.get_emails(max_results=10)
        print(f"   Retrieved {len(emails)} emails")
        
        # 2. Analyze emails
        urgent = [e for e in emails if "urgent" in e.get("subject", "").lower()]
        unread = [e for e in emails if e.get("unread", False)]
        
        # 3. Create summary
        summary = self._create_summary(
            total=len(emails),
            urgent=len(urgent),
            unread=len(unread)
        )
        
        # 4. Send to Slack
        success = await self.send_slack_message("notifications", summary)
        
        if success:
            print("✅ Summary sent to Slack")
        
        return {
            "emails_processed": len(emails),
            "urgent_count": len(urgent),
            "unread_count": len(unread)
        }
    
    def _create_summary(self, total: int, urgent: int, unread: int) -> str:
        """Create formatted summary message."""
        return f"""
📊 **Email Summary**

Total emails: {total}
🚨 Urgent: {urgent}
📬 Unread: {unread}

_Generated by EmailProcessorAgent_
        """.strip()


# Usage
async def main():
    agent = EmailProcessorAgent("email-processor-app")
    
    try:
        await agent.start()
        
        result = await agent.process_emails()
        
        print(f"\n📊 Results:")
        print(f"   Processed: {result['emails_processed']} emails")
        print(f"   Urgent: {result['urgent_count']}")
        print(f"   Unread: {result['unread_count']}")
        
    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
```

**Setup:**
```bash
# Register application with required tools
afctl applications register \
  --app-id email-processor-app \
  --connections gmail:gmail_work,slack:slack_team

afctl applications connect email-processor-app --token <activation-token>
```

---

### Multi-Tool Agent Pattern

```python
from af_sdk import get_application_client, AFError
import asyncio
from datetime import datetime


class ProductivityAgent:
    """Agent that coordinates multiple tools for productivity tasks."""
    
    def __init__(self, app_id: str):
        self.app_id = app_id
        self.client = None
    
    async def start(self):
        self.client = await get_application_client(self.app_id)
    
    async def stop(self):
        if self.client:
            await client.close()
    
    # Tool wrappers
    
    async def get_emails(self, max_results: int = 10):
        """Gmail tool."""
        return await self.client.invoke_connection(
            "gmail_work", method="get_emails",
            parameters={"max_results": max_results}
        )
    
    async def get_calendar_events(self, days_ahead: int = 7):
        """Google Calendar tool."""
        return await self.client.invoke_connection(
            "calendar_work", method="list_events",
            parameters={"days_ahead": days_ahead}
        )
    
    async def send_slack_message(self, channel: str, text: str):
        """Slack tool."""
        return await self.client.invoke_connection(
            "slack_team", method="post_message",
            parameters={"channel": channel, "text": text}
        )
    
    async def create_notion_task(self, title: str, description: str):
        """Notion tool."""
        return await self.client.invoke_connection(
            "notion_work", method="create_page",
            parameters={"title": title, "content": description}
        )
    
    # Agent logic
    
    async def daily_briefing(self):
        """Generate and send daily briefing."""
        # Gather data from multiple tools
        emails = await self.get_emails()
        events = await self.get_calendar_events(days_ahead=1)
        
        # Analyze
        urgent_emails = [e for e in emails if "urgent" in e.get("subject", "").lower()]
        today_events = [e for e in events if self._is_today(e.get("start"))]
        
        # Create briefing
        briefing = f"""
📊 **Daily Briefing - {datetime.now().strftime('%A, %B %d')}**

📧 Emails: {len(emails)} total, {len(urgent_emails)} urgent
📅 Meetings: {len(today_events)} scheduled today

Have a productive day! 🚀
        """.strip()
        
        # Send to Slack
        await self.send_slack_message("daily-briefings", briefing)
        
        # Create follow-up tasks
        if urgent_emails:
            await self.create_notion_task(
                title=f"Review {len(urgent_emails)} Urgent Emails",
                description="High priority emails need attention"
            )
    
    def _is_today(self, timestamp: str) -> bool:
        # Implement date checking logic
        return True


# Usage
async def main():
    agent = ProductivityAgent("productivity-agent")
    
    try:
        await agent.start()
        await agent.daily_briefing()
    finally:
        await agent.stop()


asyncio.run(main())
```

---

## Building Custom Connectors

You can build custom tool and agent connectors using the SDK's base classes.

### Tool Connector

Custom tool connectors extend `ToolConnector` and implement the `invoke()` method.

```python
from af_sdk import ToolConnector, ConnectorContext
from typing import Any


class MyCustomTool(ToolConnector):
    """Custom tool connector example."""
    
    # Required: Set your tool ID
    TOOL_ID = "my-custom-tool"
    
    def __init__(self, ctx: ConnectorContext):
        super().__init__(ctx)
        # Initialize your tool
    
    async def invoke(self, method: str, **kwargs) -> Any:
        """
        Handle tool method invocations.
        
        Args:
            method: Method name to invoke
            **kwargs: Method arguments
        
        Returns:
            Method result
        """
        if method == "hello":
            return await self.hello(**kwargs)
        elif method == "process_data":
            return await self.process_data(**kwargs)
        else:
            raise ValueError(f"Unknown method: {method}")
    
    # Tool methods
    
    async def hello(self, name: str) -> dict:
        """Say hello."""
        return {"message": f"Hello, {name}!"}
    
    async def process_data(self, data: list) -> dict:
        """Process some data."""
        result = [item.upper() for item in data]
        return {"processed": result}
```

**ConnectorContext:**

The `ConnectorContext` object provides access to:
- `tenant_id` (str): Current tenant ID
- `user_id` (Optional[str]): Current user ID
- `http` (httpx.AsyncClient): HTTP client for making requests
- `token_manager` (TokenManager): Token management
- `logger` (logging.Logger): Logger instance
- `metadata` (Dict): Additional metadata

---

### Agent Connector

Custom agent connectors extend `AgentConnector`.

```python
from af_sdk import AgentConnector, ConnectorContext
from typing import Any


class MyCustomAgent(AgentConnector):
    """Custom agent connector example."""
    
    # Required: Set your agent ID
    AGENT_ID = "my-custom-agent"
    
    # Optional: Define capabilities
    SUPPORTS_STREAMING = False
    MAX_TOKENS = 4096
    SUPPORTED_MODELS = ["gpt-4", "gpt-3.5-turbo"]
    
    def __init__(self, ctx: ConnectorContext):
        super().__init__(ctx)
        # Initialize your agent
    
    async def invoke(self, input_text: str, **params) -> str:
        """
        Process agent invocation.
        
        Args:
            input_text: Input text/prompt
            **params: Additional parameters
        
        Returns:
            Agent response
        """
        # Validate input
        if not await self.validate_input(input_text, **params):
            raise ValueError("Invalid input")
        
        # Process the input
        response = await self._process(input_text, **params)
        
        return response
    
    async def _process(self, input_text: str, **params) -> str:
        """Internal processing logic."""
        # Your agent logic here
        return f"Processed: {input_text}"
```

---

## Working with Tools

### Common Tool Patterns

#### Error Handling

```python
from af_sdk import AFError, AuthenticationError, NotFoundError

async def safe_invoke(client, connection_id: str, method: str, parameters: dict):
    """Safely invoke a tool with error handling."""
    try:
        result = await client.invoke_connection(
            connection_id=connection_id,
            method=method,
            parameters=parameters
        )
        return result
        
    except AuthenticationError as e:
        print(f"Authentication failed: {e}")
        # Re-authenticate or refresh token
        
    except NotFoundError as e:
        print(f"Connection not found: {e}")
        # Connection doesn't exist
        
    except AFError as e:
        print(f"Tool invocation failed: {e}")
        # Generic error handling
```

#### Retry Logic

```python
import asyncio

async def invoke_with_retry(client, connection_id: str, method: str, parameters: dict, max_retries: int = 3):
    """Invoke tool with retry logic."""
    for attempt in range(max_retries):
        try:
            result = await client.invoke_connection(
                connection_id=connection_id,
                method=method,
                parameters=parameters
            )
            return result
            
        except AFError as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Attempt {attempt + 1} failed, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
            else:
                raise
```

#### Batch Operations

```python
import asyncio

async def batch_invoke(client, operations: list):
    """Execute multiple tool invocations in parallel."""
    tasks = []
    
    for op in operations:
        task = client.invoke_connection(
            connection_id=op["connection_id"],
            method=op["method"],
            parameters=op.get("parameters", {})
        )
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results
    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]
    
    return {
        "successes": successes,
        "failures": failures,
        "total": len(operations)
    }
```

---

## Error Handling

### Exception Hierarchy

```python
from af_sdk import (
    AFError,                  # Base exception
    AuthenticationError,      # Authentication failed
    AuthorizationError,       # Authorization/permission denied
    ConnectorError,          # Connector-specific errors
    NotFoundError,           # Resource not found
    ValidationError,         # Input validation failed
    ApplicationNotFoundError # Application config not found
)
```

### Exception Usage

```python
from af_sdk import (
    get_application_client,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    AFError
)

async def robust_agent():
    try:
        # Authentication
        client = await get_application_client("my-app")
        
        # Tool invocation
        result = await client.invoke_connection(
            "gmail_work",
            method="send_email",
            parameters={"to": "user@example.com", "subject": "Test"}
        )
        
        await client.close()
        
    except ApplicationNotFoundError as e:
        print(f"❌ Application not registered: {e}")
        print("Run: afctl applications register ...")
        
    except AuthenticationError as e:
        print(f"❌ Authentication failed: {e}")
        print("Check your credentials or re-register the application")
        
    except AuthorizationError as e:
        print(f"❌ Permission denied: {e}")
        print("Check application scopes and tool connections")
        
    except NotFoundError as e:
        print(f"❌ Resource not found: {e}")
        print("Check connection_id exists")
        
    except AFError as e:
        print(f"❌ Error: {e}")
```

---

## Data Models

The SDK provides Pydantic models for structured data.

### ToolInvokeRequest

Request model for tool invocations.

```python
from af_sdk import ToolInvokeRequest

request = ToolInvokeRequest(
    method="send_email",
    parameters={
        "to": "user@example.com",
        "subject": "Hello",
        "body": "Test email"
    }
)
```

### ToolInvokeResult

Result model for tool invocations.

```python
from af_sdk import ToolInvokeResult

# Returned from tool invocations
result = ToolInvokeResult(
    success=True,
    result={"message_id": "msg-123"},
    error=None
)
```

### AuditEvent

Audit event model for logging.

```python
from af_sdk import AuditEvent

event = AuditEvent(
    event_type="tool.invoked",
    user_id="user-123",
    tenant_id="tenant-456",
    resource_id="gmail_work",
    details={"method": "send_email"}
)
```

---

## Complete Examples

### Example 1: Email Summarizer

```python
from af_sdk import get_application_client, AFError
import asyncio


async def email_summarizer():
    """Get emails and send summary to Slack."""
    
    # Authenticate
    client = await get_application_client("email-summarizer")
    
    try:
        # Get emails
        emails = await client.invoke_connection(
            "gmail_work",
            method="get_emails",
            parameters={"max_results": 20, "q": "is:unread"}
        )
        
        # Analyze
        email_list = emails.get("emails", [])
        senders = {}
        for email in email_list:
            sender = email.get("from", "Unknown")
            senders[sender] = senders.get(sender, 0) + 1
        
        # Create summary
        summary = f"📧 **Email Summary**\n\n"
        summary += f"Total unread: {len(email_list)}\n\n"
        summary += "**Top Senders:**\n"
        for sender, count in sorted(senders.items(), key=lambda x: x[1], reverse=True)[:5]:
            summary += f"• {sender}: {count}\n"
        
        # Send to Slack
        await client.invoke_connection(
            "slack_team",
            method="post_message",
            parameters={"channel": "email-summaries", "text": summary}
        )
        
        print("✅ Summary sent!")
        
    except AFError as e:
        print(f"❌ Error: {e}")
    
    finally:
        await client.close()


asyncio.run(email_summarizer())
```

---

### Example 2: Calendar Reminder Bot

```python
from af_sdk import get_application_client
import asyncio
from datetime import datetime, timedelta


async def calendar_reminder():
    """Send Slack reminders for upcoming meetings."""
    
    client = await get_application_client("calendar-bot")
    
    try:
        # Get today's events
        events = await client.invoke_connection(
            "calendar_work",
            method="list_events",
            parameters={"days_ahead": 1}
        )
        
        # Filter upcoming events (next 2 hours)
        now = datetime.now()
        upcoming = []
        
        for event in events.get("events", []):
            event_time = datetime.fromisoformat(event["start"])
            time_until = (event_time - now).total_seconds() / 60
            
            if 0 < time_until <= 120:  # Next 2 hours
                upcoming.append({
                    "title": event["title"],
                    "time": event_time.strftime("%I:%M %p"),
                    "minutes_until": int(time_until)
                })
        
        # Send reminders
        if upcoming:
            for event in upcoming:
                message = f"⏰ **Meeting Reminder**\n\n"
                message += f"📅 {event['title']}\n"
                message += f"🕒 {event['time']} (in {event['minutes_until']} minutes)"
                
                await client.invoke_connection(
                    "slack_team",
                    method="post_message",
                    parameters={"channel": "reminders", "text": message}
                )
            
            print(f"✅ Sent {len(upcoming)} reminders")
        else:
            print("No upcoming meetings")
    
    finally:
        await client.close()


asyncio.run(calendar_reminder())
```

---

### Example 3: Document Sync Agent

```python
from af_sdk import get_application_client, AFError
import asyncio


class DocumentSyncAgent:
    """Sync documents between Google Drive and Notion."""
    
    def __init__(self, app_id: str):
        self.app_id = app_id
        self.client = None
    
    async def start(self):
        self.client = await get_application_client(self.app_id)
    
    async def stop(self):
        if self.client:
            await self.client.close()
    
    async def sync_documents(self):
        """Sync new documents from Drive to Notion."""
        
        # Get recent Drive files
        drive_result = await self.client.invoke_connection(
            "drive_work",
            method="search_files",
            parameters={
                "query": "modifiedDate > '2024-01-01' and mimeType='application/vnd.google-apps.document'"
            }
        )
        
        files = drive_result.get("files", [])
        print(f"Found {len(files)} documents in Drive")
        
        # For each file, check if exists in Notion
        for file in files:
            # Check Notion
            notion_result = await self.client.invoke_connection(
                "notion_work",
                method="search",
                parameters={"query": file["name"]}
            )
            
            notion_pages = notion_result.get("results", [])
            
            if not notion_pages:
                # Create new page in Notion
                print(f"Creating '{file['name']}' in Notion...")
                
                await self.client.invoke_connection(
                    "notion_work",
                    method="create_page",
                    parameters={
                        "title": file["name"],
                        "content": f"Synced from Google Drive\nDrive ID: {file['id']}"
                    }
                )
        
        print("✅ Sync complete")


async def main():
    agent = DocumentSyncAgent("doc-sync-agent")
    
    try:
        await agent.start()
        await agent.sync_documents()
    finally:
        await agent.stop()


asyncio.run(main())
```

---

### Example 4: Scheduled Agent with Secrets

```python
from af_sdk import get_application_client
import asyncio
import schedule
import time


async def scheduled_task():
    """Task that runs on a schedule and uses secrets."""
    
    client = await get_application_client("scheduled-agent")
    
    try:
        # Get API key from secrets
        secret = await client.get_secret(path="api-keys/openai")
        api_key = secret["value"]
        
        # Use the API key for your task
        # ... your logic here ...
        
        # Log to Slack
        await client.invoke_connection(
            "slack_team",
            method="post_message",
            parameters={
                "channel": "bot-logs",
                "text": "✅ Scheduled task completed"
            }
        )
        
    finally:
        await client.close()


def run_scheduled():
    """Run the async task in the scheduler."""
    asyncio.run(scheduled_task())


# Schedule the task
schedule.every().day.at("09:00").do(run_scheduled)
schedule.every().hour.do(run_scheduled)

print("Scheduler started...")
while True:
    schedule.run_pending()
    time.sleep(60)
```

---

## Advanced Topics

### HTTP Client

For low-level HTTP operations, use `HTTPClient`:

```python
from af_sdk import HTTPClient

async with HTTPClient(
    base_url="https://dashboard.agenticfabriq.com/api/v1",
    auth_token="your-token",
    timeout=30.0
) as http:
    # Make raw HTTP requests
    response = await http.get("/tools")
    data = response.json()
```

### Custom Headers

```python
from af_sdk import FabriqClient

client = FabriqClient(
    base_url="https://dashboard.agenticfabriq.com",
    auth_token="your-token",
    extra_headers={
        "X-Custom-Header": "value",
        "X-Request-ID": "req-123"
    }
)
```

### Tracing and Observability

The SDK includes OpenTelemetry instrumentation:

```python
from af_sdk import FabriqClient

client = FabriqClient(
    base_url="https://dashboard.agenticfabriq.com",
    auth_token="your-token",
    trace_enabled=True  # Default
)
```

---

## Best Practices

### 1. Use Context Managers

```python
# ✅ Good
async with await get_application_client("my-app") as client:
    result = await client.invoke_connection(...)

# ❌ Bad (manual cleanup)
client = await get_application_client("my-app")
result = await client.invoke_connection(...)
client.close()  # Easy to forget
```

### 2. Handle Errors Gracefully

```python
from af_sdk import AFError

try:
    result = await client.invoke_connection(...)
except AFError as e:
    # Handle error
    logger.error(f"Tool invocation failed: {e}")
    # Continue or retry
```

### 3. Use Type Hints

```python
from typing import Dict, Any, List
from af_sdk import FabriqClient

async def process_emails(client: FabriqClient, max_results: int) -> List[Dict[str, Any]]:
    result = await client.invoke_connection(
        "gmail_work",
        method="get_emails",
        parameters={"max_results": max_results}
    )
    return result.get("emails", [])
```

### 4. Log Important Operations

```python
import logging

logger = logging.getLogger(__name__)

async def my_agent():
    logger.info("Agent starting...")
    
    client = await get_application_client("my-app")
    logger.info(f"Authenticated as {client._app_id}")
    
    result = await client.invoke_connection(...)
    logger.info(f"Tool invocation successful: {result}")
```

### 5. Use Environment Variables

```python
import os
from af_sdk import FabriqClient

gateway_url = os.getenv("FABRIQ_GATEWAY_URL", "https://dashboard.agenticfabriq.com")
app_id = os.getenv("FABRIQ_APP_ID", "my-app")

client = await get_application_client(app_id, gateway_url=gateway_url)
```

---

## Troubleshooting

### Common Issues

**Issue: ApplicationNotFoundError**
```
Solution: Register your application first
$ afctl applications register --app-id my-app --connections ...
$ afctl applications connect my-app --token <token>
```

**Issue: AuthenticationError**
```
Solution: Check credentials and re-register if needed
$ afctl applications show my-app --reveal-secret
$ afctl applications test my-app
```

**Issue: Connection not found**
```
Solution: Verify connection exists
$ afctl tools list
$ afctl tools get <connection_id>
```

**Issue: Permission denied**
```
Solution: Check application scopes
$ afctl applications show my-app
# Re-register with correct scopes if needed
```

---

## Available Tool Methods

This section lists all tool methods you can use with `client.invoke_connection()`. Only methods marked as ✅ **Available** are production-ready. Methods marked as 🚧 **In Development** will return an "in_development" error when invoked.

### 📧 Gmail

**✅ Available Methods:**
```python
# Get emails
result = await client.invoke_connection(
    connection_id="gmail_work",
    method="get_emails",
    parameters={
        "max_results": 100,  # Optional: default 100
        "q": "is:unread",    # Optional: Gmail search query
        "include_spam_trash": False  # Optional: default False
    }
)
```

**🚧 In Development:**
- `send_email` - Send email (params: to, subject, body, cc, bcc)
- `get_email` - Get specific email (params: message_id)
- `delete_email` - Delete email (params: message_id)
- `create_draft` - Create draft (params: to, subject, body)
- `get_labels` - Get all labels
- `create_label` - Create label (params: name)

### 💬 Slack

**✅ Available Methods:**
```python
# Get channels
result = await client.invoke_connection(
    connection_id="slack_team",
    method="get_channels"
)

# Get messages
result = await client.invoke_connection(
    connection_id="slack_team",
    method="get_messages",
    parameters={
        "channel": "C123456",  # Required
        "limit": 100          # Optional
    }
)

# Get users
result = await client.invoke_connection(
    connection_id="slack_team",
    method="get_users"
)
```

**🚧 In Development:**
- `post_message` - Post message (params: channel, text, thread_ts)
- `send_direct_message` - Send DM (params: user, text)
- `get_channel_history` - Get channel history (params: channel, limit)
- `get_user_info` - Get user info (params: user)
- `upload_file` - Upload file (params: channels, file, title)
- `add_reaction` - Add reaction (params: channel, timestamp, name)
- `search_messages` - Search messages (params: query)

### 📝 Notion

**🚧 All Methods In Development**

All Notion methods currently return an "in_development" error:
- `create_page`, `get_page`, `update_page`, `archive_page`
- `query_database`, `get_database`, `create_database`
- `get_block`, `get_block_children`, `append_block_children`
- `search`, `list_users`, `get_user`

### 🐙 GitHub

**🚧 All Operations In Development**

All GitHub operations currently return an "in_development" error:
- `list_repositories`, `get_repository`, `create_repository`
- `list_issues`, `get_issue`, `create_issue`, `update_issue`
- `list_pull_requests`, `get_pull_request`, `create_pull_request`, `merge_pull_request`
- `list_commits`, `get_commit`
- `create_branch`, `delete_branch`

### 📁 Google Drive

**✅ Available Methods:**
```python
# Get files from Drive
result = await client.invoke_connection(
    connection_id="drive_work",
    method="get_files",
    parameters={
        "query": "name contains 'report'",  # Optional: filter query
        "max_results": 50,                  # Optional: default 100
        "order_by": "modifiedTime desc"     # Optional: sort order
    }
)
```

**🚧 In Development:**
- `list_files`, `get_file`, `create_file`
- `update_file`, `delete_file`, `share_file`

### 📄 Google Docs

**✅ Available Methods:**
```python
# Get Docs documents from Drive
result = await client.invoke_connection(
    connection_id="docs_work",
    method="get_documents",
    parameters={
        "query": "name contains 'meeting'",  # Optional: filter query
        "max_results": 50,                   # Optional: default 100
        "order_by": "modifiedTime desc"      # Optional: sort order
    }
)
```

**🚧 In Development:**
- `get_document`, `create_document`, `update_document`

### 📊 Google Sheets

**✅ Available Methods:**
```python
# Get Sheets spreadsheets from Drive
result = await client.invoke_connection(
    connection_id="sheets_work",
    method="get_spreadsheets",
    parameters={
        "query": "name contains 'budget'",  # Optional: filter query
        "max_results": 50,                  # Optional: default 100
        "order_by": "modifiedTime desc"     # Optional: sort order
    }
)
```

**🚧 In Development:**
- `get_spreadsheet`, `create_spreadsheet`, `update_spreadsheet`
- `get_values`, `append_values`

### 🎨 Google Slides

**✅ Available Methods:**
```python
# Get Slides presentations from Drive
result = await client.invoke_connection(
    connection_id="slides_work",
    method="get_presentations",
    parameters={
        "query": "name contains 'pitch'",  # Optional: filter query
        "max_results": 50,                 # Optional: default 100
        "order_by": "modifiedTime desc"    # Optional: sort order
    }
)
```

**🚧 In Development:**
- `get_presentation`, `create_presentation`

### 📅 Google Calendar

**✅ Available Methods:**
```python
# Get calendar events
result = await client.invoke_connection(
    connection_id="calendar_work",
    method="get_events",
    parameters={
        "calendar_id": "primary",                  # Optional: default "primary"
        "time_min": "2024-01-01T00:00:00Z",       # Optional: start time (ISO 8601)
        "time_max": "2024-12-31T23:59:59Z",       # Optional: end time (ISO 8601)
        "max_results": 100                         # Optional: default 100
    }
)
```

**🚧 In Development:**
- `list_events`, `get_event`, `create_event`
- `update_event`, `delete_event`

### ✅ Google Tasks

**✅ Available Methods:**
```python
# Get tasks
result = await client.invoke_connection(
    connection_id="tasks",
    method="get_tasks",
    parameters={
        "tasklist_id": "@default",    # Optional: default is "@default"
        "max_results": 100,            # Optional: default 100
        "show_completed": True         # Optional: default True
    }
)
```

### 👥 Google People (Contacts)

**✅ Available Methods:**
```python
# Get contacts
result = await client.invoke_connection(
    connection_id="contacts",
    method="get_contacts",
    parameters={
        "max_results": 100,      # Optional: default 100
        "page_token": None       # Optional: for pagination
    }
)
```

### 🎓 Google Classroom

**✅ Available Methods:**
```python
# Get courses
result = await client.invoke_connection(
    connection_id="classroom",
    method="get_courses",
    parameters={
        "student_id": None,      # Optional: filter by student
        "teacher_id": None,      # Optional: filter by teacher
        "max_results": 100       # Optional: default 100
    }
)
```

### 💬 Google Chat

**🚧 In Development:**
- `get_spaces` - Get Chat spaces (requires Google Chat bot setup)

### 📋 Google Forms

**✅ Available Methods:**
```python
# Get Forms from Drive
result = await client.invoke_connection(
    connection_id="forms",
    method="get_forms",
    parameters={
        "query": "name contains 'survey'",  # Optional: filter query
        "max_results": 50,                  # Optional: default 100
        "order_by": "modifiedTime desc"     # Optional: sort order
    }
)
```

---

## API Reference Summary

### Core Functions
- `get_application_client()` - Get authenticated client
- `load_application_config()` - Load app config
- `save_application_config()` - Save app config
- `list_applications()` - List all apps
- `delete_application_config()` - Delete app config

### FabriqClient Methods
- `invoke_connection()` - Invoke a tool
- `list_tools()` - List available tools
- `get_secret()` - Get secret
- `create_secret()` - Create secret
- `update_secret()` - Update secret
- `delete_secret()` - Delete secret
- `close()` - Close client

### Base Classes
- `ToolConnector` - Base for tool connectors
- `AgentConnector` - Base for agent connectors
- `ConnectorContext` - Runtime context

### Exceptions
- `AFError` - Base exception
- `AuthenticationError` - Auth failed
- `AuthorizationError` - Permission denied
- `ConnectorError` - Connector error
- `NotFoundError` - Resource not found
- `ValidationError` - Validation failed
- `ApplicationNotFoundError` - App not found

### Data Models
- `ToolInvokeRequest` - Tool invoke request
- `ToolInvokeResult` - Tool invoke result
- `AuditEvent` - Audit event

---

## Getting Help

### Resources

- **CLI Documentation:** See `CLI_DOCUMENTATION.md`
- **GitHub:** https://github.com/agentic-fabric/agentic-fabric
- **Documentation:** https://docs.agentic-fabric.org

### Support

- Open an issue on GitHub
- Check existing documentation
- Review example code in `/examples`

---

## License

Apache-2.0

---

*Last updated: 2024-01-15 | Version: 0.1.25*

