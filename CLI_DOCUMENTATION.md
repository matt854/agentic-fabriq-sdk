# Agentic Fabriq CLI Documentation

Complete reference for the `afctl` command-line tool.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [Tool Management](#tool-management)
- [Application Management](#application-management)
- [Configuration](#configuration)
- [Global Options](#global-options)
- [Examples](#examples)

---

## Installation

```bash
pip install agentic-fabriq-sdk
```

This installs both the Python SDK and the `afctl` CLI tool.

**Verify installation:**
```bash
afctl --help
afctl version
```

---

## Quick Start

### 1. Authenticate

```bash
# Login with OAuth2 (opens browser automatically)
afctl auth login
```

### 2. List Available Tools

```bash
# View your tool connections
afctl tools list
```

### 3. Add and Connect a Tool

```bash
# Add a Google Drive connection using platform OAuth
afctl tools add google_drive --connection-id my-drive --method oauth3

# Complete the OAuth flow
afctl tools connect my-drive
```

### 4. Invoke a Tool

```bash
# List files from Google Drive
afctl tools invoke my-drive --method list_files

# Post a message to Slack
afctl tools invoke my-slack --method post_message \
  --params '{"channel": "general", "text": "Hello from afctl!"}'
```

---

## Authentication

Agentic Fabriq uses OAuth2/PKCE for secure, browser-based authentication.

### `afctl auth login`

Login to Agentic Fabriq using OAuth2.

**Usage:**
```bash
afctl auth login [OPTIONS]
```

**Options:**
- `--tenant-id TEXT` - Tenant ID (optional, extracted from JWT)
- `--keycloak-url TEXT` - Keycloak URL (default: https://auth.agenticfabriq.com)
- `--yes` - Skip confirmation when already authenticated

**Example:**
```bash
# Standard login (opens browser)
afctl auth login

# Login with specific tenant
afctl auth login --tenant-id my-tenant-id

# Force re-login without confirmation
afctl auth login --yes
```

**What happens:**
1. Opens your default browser
2. Redirects to Keycloak login page
3. After authentication, stores tokens securely
4. Returns you to the terminal

---

### `afctl auth logout`

Logout from Agentic Fabriq and clear local tokens.

**Usage:**
```bash
afctl auth logout [OPTIONS]
```

**Options:**
- `--keycloak-url TEXT` - Keycloak URL override

**Example:**
```bash
afctl auth logout
```

---

### `afctl auth status`

Show current authentication status and token information.

**Usage:**
```bash
afctl auth status
```

**Output includes:**
- Authentication status (authenticated/expired)
- User name and email
- User ID and Tenant ID
- Token expiration time
- Refresh token availability

**Example:**
```bash
afctl auth status
```

```
Authentication Status
─────────────────────
Status      ✓ Authenticated
Name        John Doe
Email       john@example.com
User ID     user-123
Tenant ID   tenant-456
Expires in  45m 30s
```

---

### `afctl auth refresh`

Refresh authentication token using refresh token.

**Usage:**
```bash
afctl auth refresh [OPTIONS]
```

**Options:**
- `--keycloak-url TEXT` - Keycloak URL override

**Example:**
```bash
afctl auth refresh
```

---

### `afctl auth token`

Display current access token.

**Usage:**
```bash
afctl auth token [OPTIONS]
```

**Options:**
- `--full` - Show full token (warning: sensitive information)

**Example:**
```bash
# Show truncated token
afctl auth token

# Show full token
afctl auth token --full
```

---

### `afctl auth whoami`

Display information about the currently authenticated user.

**Usage:**
```bash
afctl auth whoami
```

**Example:**
```bash
afctl auth whoami
```

```
Current User
────────────
Name     John Doe
Email    john@example.com
User ID  user-123
Tenant   tenant-456
```

---

## Tool Management

Manage your tool connections (configured and connected tools).

### `afctl tools list`

List your tool connections with pagination and search.

**Usage:**
```bash
afctl tools list [OPTIONS]
```

**Options:**
- `--format TEXT` - Output format: `table`, `json`, `yaml` (default: table)
- `--page INTEGER` - Page number, starts from 1 (default: 1)
- `--page-size INTEGER` - Items per page, range 1-100 (sets new default when provided)
- `--search TEXT` - Search query (searches tool IDs and connection names)
- `--tool TEXT` - Filter by tool type (e.g., 'gmail', 'slack', 'google')

**Examples:**
```bash
# List all connections (default: page 1, 20 per page)
afctl tools list

# Change page size to 10 items (becomes new default)
afctl tools list --page-size 10

# Navigate to page 2
afctl tools list --page 2

# Search for Gmail connections
afctl tools list --search gmail

# Filter by tool type
afctl tools list --tool google

# Combined search and filter
afctl tools list --tool google --search drive
```

**Tips:**
- Default page size is 20 (configurable with `--page-size`)
- Use `--page` to navigate through results
- Search is case-insensitive and matches tool IDs and names
- Tool filter shows all connections of that type

**Output:**
```
Your Tool Connections
─────────────────────────────────────────────────────────
Tool          ID            Name          Status           Method    Added
─────────────────────────────────────────────────────────
Gmail         gmail_work    Work Gmail    ✓ Connected      oauth3    2024-01-15
Google Drive  drive_work    Work Drive    ✓ Connected      oauth3    2024-01-15
Slack         slack_team    Team Slack    ✓ Connected      oauth3    2024-01-16
Notion        notion_work   Work Notion   ○ Configured     oauth3    2024-01-17
```

---

### `afctl tools get`

Get detailed information about a specific tool connection.

**Usage:**
```bash
afctl tools get <connection_id> [OPTIONS]
```

**Arguments:**
- `connection_id` - Connection ID (e.g., 'gmail_work', 'slack_team')

**Options:**
- `--format TEXT` - Output format: `table`, `json`, `yaml`

**Example:**
```bash
afctl tools get gmail_work
```

**Output:**
```
Gmail Connection Details
────────────────────────────────
Tool             Gmail
Connection ID    gmail_work
Display Name     Work Gmail
Status           ✓ Connected
Method           oauth3
Created          2024-01-15T10:30:00Z
Updated          2024-01-15T10:35:00Z
Email            john@company.com
Scopes           gmail.readonly, gmail.send
```

---

### `afctl tools add`

Add a new tool connection with credentials.

**Usage:**
```bash
afctl tools add <tool> [OPTIONS]
```

**Arguments:**
- `tool` - Tool name (e.g., `google_drive`, `slack`, `notion`, `github`)

**Required Options:**
- `--connection-id TEXT` - Unique connection ID
- `--method TEXT` - Connection method: `oauth3` (platform OAuth) or `api_credentials` (your own credentials)

**Optional Options:**
- `--display-name TEXT` - Human-readable name
- `--token TEXT` - API token (for `api_credentials` method with simple tokens)
- `--client-id TEXT` - OAuth client ID (for `api_credentials` method with OAuth apps)
- `--client-secret TEXT` - OAuth client secret (for `api_credentials` method with OAuth apps)
- `--redirect-uri TEXT` - OAuth redirect URI (auto-generated if not provided)

**Examples:**

**Using Platform OAuth (oauth3) - Recommended:**
```bash
# Google Drive with platform OAuth
afctl tools add google_drive --connection-id my-drive --method oauth3

# Slack with platform OAuth
afctl tools add slack --connection-id my-slack --method oauth3

# Notion with platform OAuth
afctl tools add notion --connection-id my-notion --method oauth3

# Gmail
afctl tools add gmail --connection-id my-gmail --method oauth3
```

**Using Your Own Credentials (api_credentials):**
```bash
# Notion with integration token
afctl tools add notion --connection-id notion-work \
  --method api_credentials \
  --token "secret_abc123..."

# Google with your own OAuth app
afctl tools add google_drive --connection-id drive-work \
  --method api_credentials \
  --client-id "123.apps.googleusercontent.com" \
  --client-secret "GOCSPX-abc123"

# Slack bot with bot token
afctl tools add slack --connection-id slack-bot \
  --method api_credentials \
  --token "xoxb-123..."
```

**Available Tools:**
- **Google Workspace:** `google_drive`, `google_docs`, `google_sheets`, `google_slides`, `gmail`, `google_calendar`, `google_meet`, `google_forms`, `google_classroom`, `google_people`, `google_chat`, `google_tasks`
- **Productivity:** `slack`, `notion`, `github`
- **More coming soon!**

**After adding:**
```bash
# Complete the OAuth flow
afctl tools connect <connection_id>
```

---

### `afctl tools connect`

Complete OAuth connection (opens browser for authorization).

**Usage:**
```bash
afctl tools connect <connection_id> [OPTIONS]
```

**Arguments:**
- `connection_id` - Connection ID to connect

**Options:**
- `--yes` - Skip confirmation when reconnecting

**Example:**
```bash
# Complete OAuth setup
afctl tools connect my-drive

# Reconnect without confirmation
afctl tools connect my-slack --yes
```

**What happens:**
1. Initiates OAuth flow with the service
2. Opens browser for authorization
3. Polls for completion (waits up to 2 minutes)
4. Saves access tokens securely

---

### `afctl tools invoke`

Invoke a tool using its connection ID.

**Usage:**
```bash
afctl tools invoke <connection_id> [OPTIONS]
```

**Arguments:**
- `connection_id` - Connection ID (e.g., 'my-slack', 'my-drive')

**Required Options:**
- `--method TEXT` - Tool method to invoke

**Optional Options:**
- `--params TEXT` - JSON string of method parameters
- `--format TEXT` - Output format: `json`, `table`, `yaml` (default: json)

**💡 To see all supported methods:**
```bash
afctl tools invoke --help
```

This displays a comprehensive list of all available methods for each tool type including Gmail, Slack, Notion, GitHub, Google Drive, Google Docs, Google Sheets, Google Slides, and Google Calendar.

**Examples:**

**Gmail:**
```bash
# Get emails
afctl tools invoke gmail_work --method get_emails \
  --params '{"max_results": 10, "q": "is:unread"}'

# Send email
afctl tools invoke gmail_work --method send_email \
  --params '{"to": "user@example.com", "subject": "Hello", "body": "Test email"}'
```

**Google Drive:**
```bash
# List files
afctl tools invoke drive_work --method list_files

# Search files
afctl tools invoke drive_work --method search_files \
  --params '{"query": "name contains '\''report'\''"}'
```

**Slack:**
```bash
# Get channels
afctl tools invoke slack_team --method get_channels

# Post message
afctl tools invoke slack_team --method post_message \
  --params '{"channel": "general", "text": "Hello from CLI!"}'
```

**Notion:**
```bash
# List pages
afctl tools invoke notion_work --method list_pages

# Create page
afctl tools invoke notion_work --method create_page \
  --params '{"title": "New Page", "content": "Page content"}'
```

---

### `afctl tools disconnect`

Disconnect a tool (removes credentials but keeps connection entry).

**Usage:**
```bash
afctl tools disconnect <connection_id> [OPTIONS]
```

**Arguments:**
- `connection_id` - Connection ID to disconnect

**Options:**
- `--force` - Skip confirmation

**Example:**
```bash
# Disconnect with confirmation
afctl tools disconnect my-slack

# Disconnect without confirmation
afctl tools disconnect my-slack --force
```

**Note:** You can reconnect later with `afctl tools connect <connection_id>`

---

### `afctl tools remove`

Remove a tool connection completely (deletes entry and credentials).

**Usage:**
```bash
afctl tools remove <connection_id> [OPTIONS]
```

**Arguments:**
- `connection_id` - Connection ID to remove

**Options:**
- `--force` - Skip confirmation

**Example:**
```bash
# Remove with confirmation
afctl tools remove my-old-slack

# Remove without confirmation
afctl tools remove my-old-slack --force
```

**Warning:** This permanently deletes the connection. You'll need to add it again with `afctl tools add`.

---

## Application Management

Register and manage applications (for SDK/agent authentication).

### `afctl applications register`

Register a new application and get an activation token.

**Usage:**
```bash
afctl applications register [OPTIONS]
```

**Required Options:**
- `--app-id TEXT` - Application identifier (no spaces)
- `--connections TEXT` - Tool connections in format: `tool1:conn-id,tool2:conn-id`

**Optional Options:**
- `--scopes TEXT` - Scopes in format: `scope1,scope2,scope3`

**Example:**
```bash
# Register application with connections
afctl applications register \
  --app-id my-slack-bot \
  --connections slack:my-slack,gmail:my-gmail \
  --scopes slack:read,slack:write,gmail:read
```

**Output:**
```
✅ Application registered successfully!

📋 App ID: my-slack-bot

🔑 Activation Token:
   act_abc123xyz...

⏰ Token expires: 2024-01-15 11:30:00 UTC
   (Valid for 1 hour)

📋 Next Steps:
   1. Navigate to your project directory
   2. Make sure you're authenticated: afctl auth login
   3. Run the connect command:

      afctl applications connect my-slack-bot --token <activation-token>

⚠️  Save the activation token! It expires in 1 hour and can only be used once.
```

---

### `afctl applications connect`

Activate an application and save credentials locally.

**Usage:**
```bash
afctl applications connect <app_id> [OPTIONS]
```

**Arguments:**
- `app_id` - Application identifier

**Required Options:**
- `--token TEXT` - Activation token from registration

**Example:**
```bash
afctl applications connect my-slack-bot --token act_abc123xyz...
```

**Output:**
```
✅ Application activated successfully!

📋 App ID: my-slack-bot
🔑 Secret Key: sk_abc123xyz...

💾 Credentials saved to: ~/.af/applications/my-slack-bot.json

⚠️  Save the secret key securely! It won't be shown again.

🚀 Your agent can now authenticate with:
   from af_sdk import get_application_client
   client = await get_application_client('my-slack-bot')
```

---

### `afctl applications list`

List all registered applications.

**Usage:**
```bash
afctl applications list [OPTIONS]
```

**Options:**
- `--format TEXT` - Output format: `table`, `json`, `yaml`
- `--sync/--no-sync` - Sync with server and remove orphaned local files (default: enabled)

**Example:**
```bash
afctl applications list
```

**Output:**
```
Registered Applications
────────────────────────────────────────────────────────
App ID          Created      Tool Connections    Config File
────────────────────────────────────────────────────────
my-slack-bot    2024-01-15   2 connection(s)     ~/.af/applications/my-slack-bot.json
email-agent     2024-01-16   1 connection(s)     ~/.af/applications/email-agent.json

📊 Total: 2 application(s)
```

---

### `afctl applications show`

Show details of a registered application.

**Usage:**
```bash
afctl applications show <app_id> [OPTIONS]
```

**Arguments:**
- `app_id` - Application identifier

**Options:**
- `--reveal-secret` - Reveal the secret key

**Example:**
```bash
afctl applications show my-slack-bot
afctl applications show my-slack-bot --reveal-secret
```

**Output:**
```
📋 Application: my-slack-bot
👤 User ID: user-123
🏢 Tenant ID: tenant-456
📅 Created: 2024-01-15T10:30:00Z
🌐 Gateway: https://dashboard.agenticfabriq.com

🔑 Secret Key: ••••••••
   Use --reveal-secret to show

🔌 Tool Connections:
  • my-slack
    Scopes: slack:read, slack:write
  • my-gmail
    Scopes: gmail:read

💾 Config file: ~/.af/applications/my-slack-bot.json
```

---

### `afctl applications delete`

Delete a registered application.

**Usage:**
```bash
afctl applications delete <app_id> [OPTIONS]
```

**Arguments:**
- `app_id` - Application identifier

**Options:**
- `--yes` - Skip confirmation

**Example:**
```bash
# Delete with confirmation
afctl applications delete my-old-bot

# Delete without confirmation
afctl applications delete my-old-bot --yes
```

**What gets deleted:**
- Application registration on server
- Local credentials file
- All active tokens invalidated

---

### `afctl applications test`

Test application authentication.

**Usage:**
```bash
afctl applications test <app_id>
```

**Arguments:**
- `app_id` - Application identifier

**Example:**
```bash
afctl applications test my-slack-bot
```

**Output:**
```
🔄 Testing authentication for 'my-slack-bot'...
✅ Authentication successful!

📋 Application: my-slack-bot
⏱️  Token expires in: 86400 seconds

🎉 Your application can authenticate and make API calls!
```

---

## Configuration

Manage CLI configuration settings.

### `afctl config show`

Show current configuration.

**Usage:**
```bash
afctl config show [OPTIONS]
```

**Options:**
- `--format TEXT` - Output format (overrides configured default): `table`, `json`, `yaml`

**Example:**
```bash
afctl config show
```

**Output:**
```
Configuration
────────────────────────────────────────────────────
gateway_url      https://dashboard.agenticfabriq.com
keycloak_url     https://auth.agenticfabriq.com
tenant_id        tenant-456
authenticated    Yes
config_file      ~/.af/config.json
output_format    table
page_size        20
```

---

### `afctl config set`

Set configuration value.

**Usage:**
```bash
afctl config set <key> <value>
```

**Arguments:**
- `key` - Configuration key
- `value` - Configuration value

**Valid Keys:**
- `gateway_url` - Gateway API URL
- `keycloak_url` - Keycloak authentication URL
- `output_format` - Default output format (`table`, `json`, `yaml`)
- `page_size` - Default page size for list commands (1-100)

**Examples:**
```bash
# Set output format
afctl config set output_format json

# Set page size
afctl config set page_size 50

# Set gateway URL
afctl config set gateway_url https://custom.gateway.com

# Set Keycloak URL
afctl config set keycloak_url https://auth.mycompany.com
```

**Note:** `tenant_id` cannot be set manually—it comes from authentication.

---

### `afctl config get`

Get configuration value.

**Usage:**
```bash
afctl config get <key>
```

**Arguments:**
- `key` - Configuration key

**Valid Keys:**
- `gateway_url`, `keycloak_url`, `keycloak_realm`, `keycloak_client_id`
- `tenant_id`, `output_format`, `page_size`
- `config_file`, `verbose`, `authenticated`

**Example:**
```bash
afctl config get gateway_url
afctl config get page_size
afctl config get authenticated
```

---

### `afctl config reset`

Reset configuration to defaults.

**Usage:**
```bash
afctl config reset [OPTIONS]
```

**Options:**
- `--yes` - Skip confirmation

**Example:**
```bash
# Reset with confirmation
afctl config reset

# Reset without confirmation
afctl config reset --yes
```

**What gets reset:**
- Authentication cleared
- Gateway URL: https://dashboard.agenticfabriq.com
- Tenant ID: cleared
- Output format: table
- Page size: 20

---

## Global Options

These options work with all commands:

### `afctl --help`

Show help for any command.

**Usage:**
```bash
afctl --help
afctl auth --help
afctl tools --help
afctl tools list --help
```

---

### `afctl --config`

Use a custom configuration file.

**Usage:**
```bash
afctl --config /path/to/config.json <command>
```

**Example:**
```bash
afctl --config ./dev-config.json auth login
```

---

### `afctl --gateway-url`

Override gateway URL for a single command.

**Usage:**
```bash
afctl --gateway-url <url> <command>
```

**Example:**
```bash
afctl --gateway-url https://dev.gateway.com tools list
```

---

### `afctl --tenant-id`

Override tenant ID for a single command.

**Usage:**
```bash
afctl --tenant-id <tenant> <command>
```

**Example:**
```bash
afctl --tenant-id my-tenant tools list
```

---

### `afctl --verbose`

Enable verbose output.

**Usage:**
```bash
afctl --verbose <command>
```

**Example:**
```bash
afctl --verbose tools invoke my-slack --method get_channels
```

---

## Additional Commands

### `afctl version`

Show CLI version.

**Usage:**
```bash
afctl version
```

**Output:**
```
Agentic Fabric CLI v0.1.25
```

---

### `afctl status`

Show system status and configuration.

**Usage:**
```bash
afctl status
```

**Output:**
```
Agentic Fabric Status
────────────────────────────────────────────────────────
Component        Status        Details
────────────────────────────────────────────────────────
Gateway          ✅ Online     https://dashboard.agenticfabriq.com
Authentication   ✅ Auth       Tenant: tenant-456
Configuration    ✅ Found      ~/.af/config.json
```

---

### `afctl init`

Initialize CLI configuration.

**Usage:**
```bash
afctl init [OPTIONS]
```

**Options:**
- `--gateway-url TEXT` - Gateway URL (default: https://dashboard.agenticfabriq.com)
- `--tenant-id TEXT` - Tenant ID
- `--yes` - Skip confirmation and overwrite existing config

**Example:**
```bash
# Initialize with defaults
afctl init

# Initialize with custom gateway
afctl init --gateway-url https://custom.gateway.com

# Force overwrite
afctl init --yes
```

---

## Examples

### Complete Workflow: Gmail Integration

```bash
# 1. Authenticate
afctl auth login

# 2. Add Gmail connection
afctl tools add gmail --connection-id work-gmail --method oauth3

# 3. Complete OAuth
afctl tools connect work-gmail

# 4. List unread emails
afctl tools invoke work-gmail --method get_emails \
  --params '{"max_results": 5, "q": "is:unread"}'

# 5. Send an email
afctl tools invoke work-gmail --method send_email \
  --params '{
    "to": "colleague@company.com",
    "subject": "Project Update",
    "body": "Here is the latest update on the project..."
  }'
```

---

### Complete Workflow: Slack Bot Application

```bash
# 1. Authenticate
afctl auth login

# 2. Add Slack connection
afctl tools add slack --connection-id team-slack --method oauth3
afctl tools connect team-slack

# 3. Register application
afctl applications register \
  --app-id slack-notifier \
  --connections slack:team-slack \
  --scopes slack:write

# 4. Activate application (save the token from step 3)
afctl applications connect slack-notifier --token act_abc123...

# 5. Test authentication
afctl applications test slack-notifier

# 6. Your agent can now use the SDK
# (See SDK documentation for Python code)
```

---

### Complete Workflow: Multi-Tool Agent

```bash
# 1. Authenticate
afctl auth login

# 2. Add multiple tools
afctl tools add gmail --connection-id work-gmail --method oauth3
afctl tools add google_calendar --connection-id work-calendar --method oauth3
afctl tools add slack --connection-id team-slack --method oauth3

# 3. Connect all tools
afctl tools connect work-gmail
afctl tools connect work-calendar
afctl tools connect team-slack

# 4. Register multi-tool application
afctl applications register \
  --app-id productivity-agent \
  --connections gmail:work-gmail,google_calendar:work-calendar,slack:team-slack

# 5. Activate and use in SDK
afctl applications connect productivity-agent --token act_...
```

---

## Troubleshooting

### Authentication Issues

**Problem:** Token expired
```bash
# Refresh token
afctl auth refresh

# Or re-login
afctl auth login
```

**Problem:** Not authenticated
```bash
# Check status
afctl auth status

# Login
afctl auth login
```

---

### Tool Connection Issues

**Problem:** Connection not found
```bash
# List all connections
afctl tools list

# Check specific connection
afctl tools get <connection_id>
```

**Problem:** OAuth flow timeout
```bash
# Try connecting again (2 minute timeout)
afctl tools connect <connection_id>

# If still failing, disconnect and reconnect
afctl tools disconnect <connection_id>
afctl tools connect <connection_id>
```

---

### Configuration Issues

**Problem:** Wrong configuration
```bash
# View current config
afctl config show

# Reset to defaults
afctl config reset

# Set specific values
afctl config set gateway_url https://dashboard.agenticfabriq.com
```

---

## Supported Tools & Methods Reference

Complete list of all supported tools and their available methods. Run `afctl tools invoke --help` to see this in the CLI.

> **Note:** Only methods marked as ✅ **Available** are currently production-ready. Methods marked as 🚧 **In Development** will return an "in_development" error message when invoked.

### 📧 Gmail

**✅ Available Methods:**
- `get_emails` - Get emails (params: max_results, q, include_spam_trash)

**🚧 In Development:**
- `send_email` - Send email (params: to, subject, body, cc, bcc)
- `get_email` - Get specific email (params: message_id)
- `delete_email` - Delete email (params: message_id)
- `create_draft` - Create draft (params: to, subject, body)
- `get_labels` - Get all labels
- `create_label` - Create label (params: name)

### 💬 Slack

**✅ Available Methods:**
- `get_channels` - List channels
- `get_messages` - Get channel messages (params: channel, limit)
- `get_users` - List workspace users

**🚧 In Development:**
- `post_message` - Post message (params: channel, text, thread_ts)
- `send_direct_message` - Send direct message (params: user, text)
- `get_channel_history` - Get channel history (params: channel, limit)
- `get_user_info` - Get user info (params: user)
- `upload_file` - Upload file (params: channels, file, title)
- `add_reaction` - Add reaction (params: channel, timestamp, name)
- `search_messages` - Search messages (params: query)

### 📝 Notion

**🚧 All Methods In Development:**
- `create_page` - Create page (params: parent, properties, children)
- `get_page` - Get page (params: page_id)
- `update_page` - Update page (params: page_id, properties)
- `archive_page` - Archive page (params: page_id)
- `query_database` - Query database (params: database_id, filter)
- `get_database` - Get database (params: database_id)
- `create_database` - Create database (params: parent, properties)
- `get_block` - Get block (params: block_id)
- `get_block_children` - Get block children (params: block_id)
- `append_block_children` - Append blocks (params: block_id, children)
- `search` - Search (params: query)
- `list_users` - List users
- `get_user` - Get user (params: user_id)

### 🐙 GitHub

**🚧 All Operations In Development:**
- `list_repositories` - List repositories
- `get_repository` - Get repository (params: owner, repo)
- `create_repository` - Create repository (params: name, description)
- `list_issues` - List issues (params: owner, repo)
- `get_issue` - Get issue (params: owner, repo, number)
- `create_issue` - Create issue (params: owner, repo, title, body)
- `update_issue` - Update issue (params: owner, repo, number, title, body)
- `list_pull_requests` - List pull requests (params: owner, repo)
- `get_pull_request` - Get pull request (params: owner, repo, number)
- `create_pull_request` - Create PR (params: owner, repo, title, head, base)
- `merge_pull_request` - Merge PR (params: owner, repo, number)
- `list_commits` - List commits (params: owner, repo)
- `get_commit` - Get commit (params: owner, repo, sha)
- `create_branch` - Create branch (params: owner, repo, branch, sha)
- `delete_branch` - Delete branch (params: owner, repo, branch)

### 📁 Google Drive

**✅ Available Methods:**
- `get_files` - Get files from Drive (params: query, max_results, order_by)

**🚧 In Development:**
- `list_files` - List files (params: page_size, query)
- `get_file` - Get file (params: file_id)
- `create_file` - Create file (params: name, mime_type, content)
- `update_file` - Update file (params: file_id, content)
- `delete_file` - Delete file (params: file_id)
- `share_file` - Share file (params: file_id, email, role)

### 📄 Google Docs

**✅ Available Methods:**
- `get_documents` - Get Docs documents from Drive (params: query, max_results, order_by)

**🚧 In Development:**
- `get_document` - Get specific document (params: document_id)
- `create_document` - Create document (params: title)
- `update_document` - Update document (params: document_id, requests)

### 📊 Google Sheets

**✅ Available Methods:**
- `get_spreadsheets` - Get Sheets spreadsheets from Drive (params: query, max_results, order_by)

**🚧 In Development:**
- `get_spreadsheet` - Get specific spreadsheet (params: spreadsheet_id)
- `create_spreadsheet` - Create spreadsheet (params: title)
- `update_spreadsheet` - Update spreadsheet (params: spreadsheet_id, requests)
- `get_values` - Get cell values (params: spreadsheet_id, range)
- `append_values` - Append rows (params: spreadsheet_id, range, values)

### 🎨 Google Slides

**✅ Available Methods:**
- `get_presentations` - Get Slides presentations from Drive (params: query, max_results, order_by)

**🚧 In Development:**
- `get_presentation` - Get specific presentation (params: presentation_id)
- `create_presentation` - Create presentation (params: title)

### 📅 Google Calendar

**✅ Available Methods:**
- `get_events` - Get calendar events (params: calendar_id, time_min, time_max, max_results)

**🚧 In Development:**
- `list_events` - List events (params: calendar_id, time_min, time_max)
- `get_event` - Get specific event (params: calendar_id, event_id)
- `create_event` - Create event (params: calendar_id, summary, start, end)
- `update_event` - Update event (params: calendar_id, event_id, summary, start, end)
- `delete_event` - Delete event (params: calendar_id, event_id)

### ✅ Google Tasks

**✅ Available Methods:**
- `get_tasks` - Get tasks from task lists (params: tasklist_id, max_results, show_completed)

### 👥 Google People (Contacts)

**✅ Available Methods:**
- `get_contacts` - Get contacts (params: max_results, page_token)

### 🎓 Google Classroom

**✅ Available Methods:**
- `get_courses` - Get courses (params: student_id, teacher_id, max_results)

### 💬 Google Chat

**🚧 In Development:**
- `get_spaces` - Get Chat spaces (requires bot setup, params: max_results, page_token)

### 📋 Google Forms

**✅ Available Methods:**
- `get_forms` - Get Forms from Drive (params: query, max_results, order_by)

---

## Getting Help

### Command Help

Every command has built-in help:
```bash
afctl --help
afctl auth --help
afctl tools --help
afctl tools list --help
afctl tools invoke --help  # Shows all supported methods
afctl applications --help
```

### Additional Resources

- **SDK Documentation:** See `SDK_DOCUMENTATION.md` for Python SDK usage
- **GitHub:** https://github.com/agentic-fabric/agentic-fabric
- **Website:** https://docs.agentic-fabric.org

---

## License

Apache-2.0

---

*Last updated: 2024-01-15 | Version: 0.1.25*

