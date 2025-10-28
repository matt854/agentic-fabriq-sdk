"""
Tool management commands for the Agentic Fabric CLI.
"""


import typer

from af_cli.core.client import get_client
from af_cli.core.output import debug, error, info, print_output, success, warning

app = typer.Typer(help="Tool management commands")


@app.command()
def list(
    format: str = typer.Option("table", "--format", help="Output format"),
    page: int = typer.Option(1, "--page", help="Page number (starts from 1)", min=1),
    page_size: int = typer.Option(None, "--page-size", help="Number of items per page (1-100). When specified, becomes the new default.", min=1, max=100),
    search: str = typer.Option(None, "--search", help="Search query (searches tool IDs from registry like 'gmail', 'slack', and user connection names)"),
    tool_filter: str = typer.Option(None, "--tool", help="Filter by tool type from registry (e.g., 'gmail' shows Gmail connections, 'google' shows all Google tools)"),
):
    """List your tool connections (configured and connected tools).

    The command supports pagination and search to help you navigate large numbers
    of connections efficiently.

    Examples:
      # List all connections (default: page 1, 20 per page)
      afctl tools list

      # List first page with 10 items per page
      afctl tools list --page 1 --page-size 10

      # Search for tool types (exact match against registry - shows all connections of that type)
      afctl tools list --search gmail     # Shows all Gmail connections
      afctl tools list --search google    # Shows all Google Workspace tools
      afctl tools list --search slack     # Shows all Slack connections
      afctl tools list --search notion    # Shows all Notion connections
      afctl tools list --search github    # Shows all GitHub connections

      # Filter by tool type (shows all connections of that tool)
      afctl tools list --tool gmail       # Shows all Gmail connections
      afctl tools list --tool google      # Shows all Google Workspace tools
      afctl tools list --tool slack       # Shows all Slack connections

      # Search and paginate together
      afctl tools list --search google --page 1 --page-size 5

      # Find connections by name (fallback search)
      afctl tools list --search work      # Connections with "work" in name
      afctl tools list --search personal # Connections with "personal" in name

      # Combined search and filtering (AND logic - must match both)
      afctl tools list --tool google --search gmail     # Google tools containing "gmail"
      afctl tools list --search drive --tool google     # Google tools with "drive"
      afctl tools list --search team --tool slack       # Slack connections with "team"

    Pagination:
      - Pages start from 1
      - Page size range: 1-100 items
      - Shows helpful tips when more results are available

    Search:
      - **Primary**: Searches available tool IDs from registry (e.g., "gmail" matches "gmail", "google" matches "google_drive")
      - **Secondary**: Searches user connection IDs and display names (e.g., "gmail" matches "gmail_work")
      - Case-insensitive matching
      - Shows all connections matching the search criteria

    Tool Filtering:
      - Filters by tool type from connector registry
      - Shows all user connections for that tool type
      - "google" shows all Google Workspace tools (Drive, Docs, Sheets, Gmail, etc.)
      - "gmail" shows only Gmail connections
      - "slack" shows only Slack connections
      - Combines with search and pagination
    """
    try:
        from af_cli.core.config import get_config
        config = get_config()
        
        # Use provided page_size, or fall back to configured default
        if page_size is None:
            page_size = config.page_size
        else:
            # Save the new page_size as default
            config.page_size = page_size
            config.save()
        
        with get_client() as client:
            # Build query parameters - always include all params for clarity
            params = {
                "page": page,
                "page_size": page_size,
            }
            if search:
                params["search"] = search
            if tool_filter:
                params["tool_filter"] = tool_filter
            
            debug(f"Requesting connections with params: {params}")
            connections = client.get("/api/v1/user-connections", params=params)
            
            debug(f"Received {len(connections) if connections else 0} connections from API")

            if not connections:
                if page > 1:
                    # User requested a page beyond available data
                    error(f"Page {page} is out of range.")
                    info(f"Try 'afctl tools list --page 1' to see available connections.")
                    if search or tool_filter:
                        info(f"Or adjust your search/filter criteria to see more results.")
                elif search or tool_filter:
                    warning(f"No tool connections found matching your criteria. Try adjusting your search or filter.")
                else:
                    warning("No tool connections found. Add connections in the dashboard UI.")
                return
            
            # Format for better display
            display_data = []
            for conn in connections:
                # Format tool name nicely (e.g., "google_docs" -> "Google Docs")
                tool_name = conn.get("tool", "N/A").replace("_", " ").title()
                
                # Status indicator
                status = "✓ Connected" if conn.get("connected") else "○ Configured"
                
                display_data.append({
                    "Tool": tool_name,
                    "ID": conn.get("connection_id", "N/A"),
                    "Name": conn.get("display_name") or conn.get("connection_id", "N/A"),
                    "Status": status,
                    "Method": conn.get("method", "oauth"),
                    "Added": conn.get("created_at", "N/A")[:10] if conn.get("created_at") else "N/A",
                })
            
            # Show pagination and filter info
            total_info = ""
            if page != 1 or page_size != 20 or search or tool_filter:
                total_info = f" (Page {page}, {len(connections)} shown"
                if search:
                    total_info += f", Search: '{search}'"
                if tool_filter:
                    total_info += f", Tool: '{tool_filter}'"
                total_info += ")"
            
            # Add summary info if filters are active
            if search or tool_filter:
                filter_parts = []
                if search:
                    filter_parts.append(f"search='{search}'")
                if tool_filter:
                    filter_parts.append(f"tool='{tool_filter}'")
                info(f"🔍 Filtered results: {' AND '.join(filter_parts)}")

            print_output(
                display_data,
                format_type=format,
                title=f"Your Tool Connections{total_info}"
            )

            # Show helpful tips for pagination
            if len(connections) == page_size:
                info(f"💡 Showing {len(connections)} results. Use --page {page + 1} to see more results")
            
            if not search and not tool_filter:
                info(f"💡 Tip: Use --search <term> to search, or --tool <type> to filter by tool type")
            
    except Exception as e:
        error(f"Failed to list tool connections: {e}")
        raise typer.Exit(1)


@app.command()
def get(
    connection_id: str = typer.Argument(..., help="Connection ID (e.g., 'google', 'slack')"),
    format: str = typer.Option("table", "--format", help="Output format"),
):
    """Get tool connection details."""
    try:
        with get_client() as client:
            # Get all user connections and find the matching one
            connections = client.get("/api/v1/user-connections")
            
            # Find the specific connection
            connection = None
            for conn in connections:
                if conn.get("connection_id") == connection_id or conn.get("tool") == connection_id:
                    connection = conn
                    break
            
            if not connection:
                error(f"Connection '{connection_id}' not found")
                info("Available connections:")
                for conn in connections:
                    info(f"  - {conn.get('tool')} (ID: {conn.get('connection_id')})")
                raise typer.Exit(1)
            
            # Format tool name nicely
            tool_name = connection.get("tool", "N/A").replace("_", " ").title()
            
            # Format the connection details for display
            details = {
                "Tool": tool_name,
                "Connection ID": connection.get("connection_id", "N/A"),
                "Display Name": connection.get("display_name") or connection.get("connection_id", "N/A"),
                "Status": "✓ Connected" if connection.get("connected") else "○ Configured",
                "Method": connection.get("method", "oauth"),
                "Created": connection.get("created_at", "N/A"),
                "Updated": connection.get("updated_at", "N/A"),
            }
            
            # Add tool-specific fields if present
            if connection.get("team_name"):
                details["Team Name"] = connection.get("team_name")
            if connection.get("team_id"):
                details["Team ID"] = connection.get("team_id")
            if connection.get("bot_user_id"):
                details["Bot User ID"] = connection.get("bot_user_id")
            if connection.get("email"):
                details["Email"] = connection.get("email")
            if connection.get("login"):
                details["GitHub Login"] = connection.get("login")
            if connection.get("workspace_name"):
                details["Workspace Name"] = connection.get("workspace_name")
            if connection.get("scopes"):
                details["Scopes"] = ", ".join(connection.get("scopes", []))
            
            print_output(
                details,
                format_type=format,
                title=f"{tool_name} Connection Details"
            )
            
    except Exception as e:
        error(f"Failed to get tool connection: {e}")
        raise typer.Exit(1)


@app.command()
def invoke(
    connection_id: str = typer.Argument(..., help="Connection ID (e.g., 'slacker', 'gurt')"),
    method: str = typer.Option(..., "--method", help="Tool method to invoke"),
    params: str = typer.Option(None, "--params", help="JSON string of method parameters (e.g., '{\"channel\": \"test\", \"text\": \"Hello\"}')"),
    format: str = typer.Option("json", "--format", help="Output format (json, table, yaml)"),
):
    """Invoke a tool using its connection ID.
    
    The connection ID identifies which specific tool connection to use.
    Run 'afctl tools list' to see your connection IDs.
    
    SUPPORTED TOOLS & METHODS:
    
    📧 Gmail (gmail):
      • get_emails         - Get emails (params: max_results, q, label_ids)
      • send_email         - Send email (params: to, subject, body, cc, bcc)
      • get_email          - Get specific email (params: message_id)
      • delete_email       - Delete email (params: message_id)
      • create_draft       - Create draft (params: to, subject, body)
      • get_labels         - Get all labels
      • create_label       - Create label (params: name)
    
    💬 Slack (slack):
      • get_channels       - List channels
      • post_message       - Post message (params: channel, text, thread_ts)
      • get_messages       - Get channel messages (params: channel, limit)
      • get_users          - List workspace users
      • upload_file        - Upload file (params: channels, file, title)
      • add_reaction       - Add reaction (params: channel, timestamp, name)
    
    📝 Notion (notion):
      • list_pages         - List all pages
      • get_page           - Get page (params: page_id)
      • create_page        - Create page (params: title, content, parent_id)
      • update_page        - Update page (params: page_id, title, content)
      • search             - Search (params: query)
      • list_databases     - List databases
      • query_database     - Query database (params: database_id, filter)
    
    🐙 GitHub (github):
      • list_repos         - List repositories (params: visibility, sort)
      • get_repo           - Get repository (params: owner, repo)
      • create_issue       - Create issue (params: owner, repo, title, body)
      • list_issues        - List issues (params: owner, repo, state)
      • create_pr          - Create pull request (params: owner, repo, title, head, base)
      • list_prs           - List pull requests (params: owner, repo, state)
      • get_file           - Get file content (params: owner, repo, path)
    
    📁 Google Drive (google_drive):
      • list_files         - List files (params: page_size, query)
      • get_file           - Get file (params: file_id)
      • create_file        - Create file (params: name, mime_type, content)
      • update_file        - Update file (params: file_id, content)
      • delete_file        - Delete file (params: file_id)
      • search_files       - Search files (params: query)
      • share_file         - Share file (params: file_id, email, role)
    
    📄 Google Docs (google_docs):
      • get_document       - Get document (params: document_id)
      • create_document    - Create document (params: title)
      • update_document    - Update document (params: document_id, content)
      • append_text        - Append text (params: document_id, text)
    
    📊 Google Sheets (google_sheets):
      • get_spreadsheet    - Get spreadsheet (params: spreadsheet_id)
      • create_spreadsheet - Create spreadsheet (params: title)
      • get_values         - Get cell values (params: spreadsheet_id, range)
      • update_values      - Update cells (params: spreadsheet_id, range, values)
      • append_values      - Append rows (params: spreadsheet_id, range, values)
    
    🎨 Google Slides (google_slides):
      • get_presentation   - Get presentation (params: presentation_id)
      • create_presentation - Create presentation (params: title)
      • add_slide          - Add slide (params: presentation_id, layout)
      • update_slide       - Update slide (params: presentation_id, slide_id, content)
    
    📅 Google Calendar (google_calendar):
      • list_events        - List events (params: calendar_id, time_min, time_max)
      • get_event          - Get event (params: calendar_id, event_id)
      • create_event       - Create event (params: calendar_id, summary, start, end)
      • update_event       - Update event (params: calendar_id, event_id, ...)
      • delete_event       - Delete event (params: calendar_id, event_id)
    
    Note: Parameter requirements vary by method. Use --params with JSON format.
    
    Examples:
        # Gmail: Get unread emails
        afctl tools invoke gmail_work --method get_emails --params '{"max_results": 10, "q": "is:unread"}'
        
        # Gmail: Send email
        afctl tools invoke gmail_work --method send_email --params '{"to": "user@example.com", "subject": "Hello", "body": "Test"}'
        
        # Slack: Post message
        afctl tools invoke slack_team --method post_message --params '{"channel": "general", "text": "Hello!"}'
        
        # Slack: Get channels
        afctl tools invoke slack_team --method get_channels
        
        # Notion: Search pages
        afctl tools invoke notion_work --method search --params '{"query": "meeting notes"}'
        
        # GitHub: List repositories
        afctl tools invoke github_dev --method list_repos --params '{"visibility": "public"}'
        
        # Google Drive: Search files
        afctl tools invoke drive_work --method search_files --params '{"query": "name contains '\''report'\''"}'
        
        # Google Sheets: Get values
        afctl tools invoke sheets_work --method get_values --params '{"spreadsheet_id": "abc123", "range": "Sheet1!A1:C10"}'
    """
    try:
        # Parse parameters if provided
        parameters = {}
        if params:
            import json as json_lib
            try:
                parameters = json_lib.loads(params)
            except json_lib.JSONDecodeError as e:
                error(f"Invalid JSON in --params: {e}")
                raise typer.Exit(1)
        
        with get_client() as client:
            info(f"Invoking connection '{connection_id}' with method '{method}'...")
            
            # Verify connection exists
            connections = client.get("/api/v1/user-connections")
            connection = next((c for c in connections if c.get("connection_id") == connection_id), None)
            
            if not connection:
                error(f"Connection '{connection_id}' not found")
                info("Available connections:")
                for conn in connections:
                    info(f"  - {conn.get('connection_id')} ({conn.get('tool')})")
                raise typer.Exit(1)
            
            tool_name = connection.get("tool")
            debug(f"Connection '{connection_id}' uses tool '{tool_name}'")
            
            # Use the connection-based invoke endpoint (auto-creates tool if needed)
            data = {
                "method": method,
                "parameters": parameters,
            }
            
            response = client.post(f"/api/v1/tools/connections/{connection_id}/invoke", data)
            
            success("Tool invoked successfully")
            
            # For tool invocations, show the result in a more readable format
            if format == "json":
                import json as json_lib
                print(json_lib.dumps(response, indent=2))
            elif format == "yaml":
                import yaml
                print(yaml.dump(response, default_flow_style=False))
            else:
                # For table format, show just the result field nicely
                result = response.get("result", {})
                print("\n📊 Result:")
                print_output(result, format_type="json")
            
    except Exception as e:
        error(f"Failed to invoke tool: {e}")
        raise typer.Exit(1)


@app.command()
def add(
    tool: str = typer.Argument(..., help="Tool name (google_drive, google_slides, slack, notion, github, etc.)"),
    connection_id: str = typer.Option(..., "--connection-id", help="Unique connection ID"),
    display_name: str = typer.Option(None, "--display-name", help="Human-readable name"),
    method: str = typer.Option(..., "--method", help="Connection method: 'api_credentials', 'oauth3' (Google platform OAuth), or 'oauth'"),
    
    # API credentials method fields (can be either a token OR client_id/secret)
    token: str = typer.Option(None, "--token", help="API token (for simple token-based auth like Notion, Slack bot)"),
    client_id: str = typer.Option(None, "--client-id", help="OAuth client ID (for app-based auth like Google, Slack)"),
    client_secret: str = typer.Option(None, "--client-secret", help="OAuth client secret (for app-based auth)"),
    redirect_uri: str = typer.Option(None, "--redirect-uri", help="OAuth redirect URI (optional, auto-generated)"),
):
    """
    Add a new tool connection with credentials.
    
    Examples:
      # Notion (api_credentials method - single token)
      afctl tools add notion --connection-id notion-work --method api_credentials --token "secret_abc123"
      
      # Google (oauth3 method - uses platform OAuth, no credentials needed)
      afctl tools add google_drive --connection-id google-work --method oauth3
      
      # Slack (oauth3 method - uses platform OAuth, no credentials needed)
      afctl tools add slack --connection-id slack-work --method oauth3
      
      # Notion (oauth3 method - uses platform OAuth, no credentials needed)
      afctl tools add notion --connection-id notion-work --method oauth3
      
      # Google (api_credentials method - your own OAuth app)
      afctl tools add google_drive --connection-id google-work --method api_credentials \\
        --client-id "123.apps.googleusercontent.com" \\
        --client-secret "GOCSPX-abc123"
      
      # Slack bot (api_credentials method - single token)
      afctl tools add slack --connection-id slack-bot --method api_credentials --token "xoxb-123..."
    """
    try:
        from af_cli.core.config import get_config
        
        with get_client() as client:
            # Validate tool name - check for common mistakes
            if tool.lower() == "google":
                error("❌ Invalid tool name: 'google'")
                info("")
                info("Please specify the exact Google Workspace tool:")
                info("  • google_drive    - Google Drive")
                info("  • google_docs     - Google Docs")
                info("  • google_sheets   - Google Sheets")
                info("  • google_slides   - Google Slides")
                info("  • gmail           - Gmail")
                info("  • google_calendar - Google Calendar")
                info("  • google_meet     - Google Meet")
                info("  • google_forms    - Google Forms")
                info("  • google_classroom - Google Classroom")
                info("  • google_people   - Google People (Contacts)")
                info("  • google_chat     - Google Chat")
                info("  • google_tasks    - Google Tasks")
                info("")
                info("Example:")
                info(f"  afctl tools add google_drive --connection-id {connection_id} --method {method}")
                raise typer.Exit(1)
            
            # Validate method
            if method not in ["api_credentials", "oauth3", "oauth"]:
                error("Method must be 'api_credentials', 'oauth3', or 'oauth'")
                raise typer.Exit(1)
            
            # Validate oauth3 method is only for Google, Slack, and Notion tools
            if method == "oauth3":
                if not (tool.startswith("google_") or tool == "gmail" or tool == "slack" or tool == "notion"):
                    error("oauth3 method is only available for Google Workspace tools, Slack, and Notion")
                    info("For other tools, use 'api_credentials' method")
                    raise typer.Exit(1)
            
            # Validate api_credentials method requirements
            if method == "api_credentials":
                # Must have either token OR (client_id + client_secret)
                has_token = bool(token)
                has_oauth_creds = bool(client_id and client_secret)
                
                if not has_token and not has_oauth_creds:
                    error("api_credentials method requires either:")
                    info("  • --token (for simple token auth like Notion, Slack bot)")
                    info("  • --client-id and --client-secret (for OAuth app auth like Google)")
                    info("")
                    info(f"Examples:")
                    info(f"  afctl tools add {tool} --connection-id {connection_id} --method api_credentials --token YOUR_TOKEN")
                    info(f"  afctl tools add {tool} --connection-id {connection_id} --method api_credentials --client-id ID --client-secret SECRET")
                    raise typer.Exit(1)
            
            info(f"Creating connection: {connection_id}")
            info(f"Tool: {tool}")
            info(f"Method: {method}")
            
            # Step 1: Create connection metadata
            connection_data = {
                "tool": tool,
                "connection_id": connection_id,
                "display_name": display_name or connection_id,
                "method": method,
            }
            
            client.post("/api/v1/user-connections", data=connection_data)
            success(f"✅ Connection entry created: {connection_id}")
            
            # Step 2: Store credentials based on method
            if method == "oauth3":
                # OAuth3 uses platform credentials - no need to store user credentials
                success("✅ Connection configured with platform OAuth")
                info("")
                info(f"Next: Run 'afctl tools connect {connection_id}' to authenticate")
            
            elif method == "api_credentials":
                # Determine the API base tool name (Google tools all use "google")
                api_tool_name = "google" if (tool.startswith("google_") or tool == "gmail") else tool
                
                if token:
                    # Simple token-based auth (Notion, Slack bot, etc.)
                    info("Storing API token...")
                    
                    # Tool-specific endpoint and payload mappings
                    if tool == "notion":
                        # Notion uses /config endpoint with integration_token field
                        endpoint = f"/api/v1/tools/{tool}/config?connection_id={connection_id}"
                        cred_payload = {"integration_token": token}
                    else:
                        # Generic tools use /connection endpoint with api_token field
                        endpoint = f"/api/v1/tools/{tool}/connection?connection_id={connection_id}"
                        cred_payload = {"api_token": token}
                    
                    client.post(endpoint, data=cred_payload)
                    success("✅ API token stored")
                    success(f"✅ Connection '{connection_id}' is ready to use!")
                    
                elif client_id and client_secret:
                    # OAuth app credentials (Google, Slack app, etc.)
                    # Auto-generate redirect_uri if not provided
                    if not redirect_uri:
                        config = get_config()
                        redirect_uri = f"{config.gateway_url}/api/v1/tools/{api_tool_name}/oauth/callback"
                        info(f"Using default redirect URI: {redirect_uri}")
                    
                    # Store OAuth app config
                    info("Storing OAuth app credentials...")
                    config_payload = {
                        "client_id": client_id,
                        "client_secret": client_secret,
                    }
                    if redirect_uri:
                        config_payload["redirect_uri"] = redirect_uri
                    
                    # For Google tools, pass tool_type parameter to prevent duplicates
                    tool_type_param = f"&tool_type={tool}" if api_tool_name == "google" else ""
                    
                    client.post(
                        f"/api/v1/tools/{api_tool_name}/config?connection_id={connection_id}{tool_type_param}",
                        data=config_payload
                    )
                    success("✅ OAuth app credentials stored")
                    info("")
                    info(f"Next: Run 'afctl tools connect {connection_id}' to complete OAuth setup")
            
            elif method == "oauth":
                # OAuth flow (legacy, redirect to api_credentials)
                error("The 'oauth' method is deprecated. Please use 'api_credentials' instead.")
                info("All credential storage now uses the 'api_credentials' method.")
                raise typer.Exit(1)
            
            # Show helpful info
            info("")
            info("View your connections:")
            info(f"  • List all: afctl tools list")
            info(f"  • View details: afctl tools get {connection_id}")
            
    except Exception as e:
        error(f"Failed to add connection: {e}")
        raise typer.Exit(1)


@app.command()
def connect(
    connection_id: str = typer.Argument(..., help="Connection ID to connect"),
    yes: bool = typer.Option(False, "--yes", help="Skip confirmation when reconnecting"),
):
    """Complete OAuth connection (open browser for authorization)."""
    try:
        import webbrowser
        import time
        
        with get_client() as client:
            # Get connection info
            connections = client.get("/api/v1/user-connections")
            
            connection = None
            for conn in connections:
                if conn.get("connection_id") == connection_id:
                    connection = conn
                    break
            
            if not connection:
                error(f"Connection '{connection_id}' not found")
                info("Run 'afctl tools list' to see available connections")
                raise typer.Exit(1)
            
            tool = connection["tool"]
            method = connection["method"]
            
            # Check if connection is already set up (has credentials stored)
            if connection.get("connected"):
                warning(f"Connection '{connection_id}' is already connected")
                if not yes:
                    confirm = typer.confirm("Do you want to reconnect (re-authorize)?")
                    if not confirm:
                        return
            
            # Determine the API base tool name
            # - Google tools all use "google" for API credentials, "google_oauth" for oauth3
            # - Notion uses "notion" for API credentials, "notion_oauth" for oauth3
            if tool.startswith("google_") or tool == "gmail":
                api_tool_name = "google_oauth" if method == "oauth3" else "google"
            elif tool == "notion":
                api_tool_name = "notion_oauth" if method == "oauth3" else "notion"
            else:
                api_tool_name = tool
            
            # Initiate OAuth flow
            info(f"Initiating OAuth for {tool}...")
            
            # For Google tools, pass the specific tool_type parameter
            tool_type_param = f"&tool_type={tool}" if (tool.startswith("google_") or tool == "gmail") else ""
            
            # For oauth3 method, pass the method parameter to use platform credentials
            method_param = f"&method={method}" if method == "oauth3" else ""
            
            result = client.post(
                f"/api/v1/tools/{api_tool_name}/connect/initiate?connection_id={connection_id}{tool_type_param}{method_param}",
                data={}
            )
            
            debug(f"Backend response: {result}")
            
            # Different tools use different field names for the auth URL
            auth_url = (
                result.get("authorization_url") or 
                result.get("auth_url") or 
                result.get("oauth_url")
            )
            
            if not auth_url:
                error("Failed to get authorization URL from backend")
                error(f"Response keys: {list(result.keys())}")
                debug(f"Full response: {result}")
                raise typer.Exit(1)
            
            info("Opening browser for authentication...")
            info("")
            info(f"If browser doesn't open, visit: {auth_url}")
            
            # Open browser
            webbrowser.open(auth_url)
            
            info("")
            info("Waiting for authorization...")
            info("(Complete the login in your browser)")
            
            # Poll for connection completion
            max_attempts = 120  # 2 minutes
            for attempt in range(max_attempts):
                time.sleep(1)
                
                # Check connection status
                connections = client.get("/api/v1/user-connections")
                for conn in connections:
                    if conn.get("connection_id") == connection_id:
                        if conn.get("connected"):
                            info("")
                            success(f"✅ Successfully connected to {tool}!")
                            
                            # Show connection details
                            info(f"Connection ID: {connection_id}")
                            if conn.get("email"):
                                info(f"Email: {conn['email']}")
                            if conn.get("team_name"):
                                info(f"Team: {conn['team_name']}")
                            if conn.get("login"):
                                info(f"GitHub: {conn['login']}")
                            
                            return
                        break
            
            # Timeout
            error("")
            error("Timeout: Authorization not completed within 2 minutes")
            info("Please try again or check your browser")
            raise typer.Exit(1)
            
    except Exception as e:
        error(f"Failed to connect: {e}")
        raise typer.Exit(1)


@app.command()
def disconnect(
    connection_id: str = typer.Argument(..., help="Connection ID to disconnect"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
):
    """Disconnect a tool (remove credentials but keep connection entry)."""
    try:
        with get_client() as client:
            # Get connection info
            connections = client.get("/api/v1/user-connections")
            
            connection = None
            for conn in connections:
                if conn.get("connection_id") == connection_id:
                    connection = conn
                    break
            
            if not connection:
                error(f"Connection '{connection_id}' not found")
                raise typer.Exit(1)
            
            tool = connection["tool"]
            tool_display = connection.get("display_name") or connection_id
            
            # Check if connected
            if not connection.get("connected"):
                error(f"Connection '{connection_id}' is already disconnected")
                info(f"Use 'afctl tools get {connection_id}' to view status")
                raise typer.Exit(1)
            
            # Confirm
            if not force:
                warning(f"This will remove OAuth tokens/credentials for '{tool_display}'")
                info("You can reconnect later with 'afctl tools connect'")
                confirm = typer.confirm(f"Disconnect {tool} connection '{connection_id}'?")
                if not confirm:
                    info("Cancelled")
                    return
            
            # Determine the API base tool name (Google tools all use "google")
            api_tool_name = "google" if (tool.startswith("google_") or tool == "gmail") else tool
            
            # For Google tools, pass tool_type parameter
            tool_type_param = f"&tool_type={tool}" if api_tool_name == "google" else ""
            
            # Delete connection credentials
            client.delete(
                f"/api/v1/tools/{api_tool_name}/connection?connection_id={connection_id}{tool_type_param}"
            )
            
            success(f"✅ Disconnected: {connection_id}")
            info("Connection entry preserved.")
            info(f"Run 'afctl tools connect {connection_id}' to reconnect.")
            
    except Exception as e:
        error(f"Failed to disconnect: {e}")
        raise typer.Exit(1)


@app.command()
def remove(
    connection_id: str = typer.Argument(..., help="Connection ID to remove"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
):
    """Remove a tool connection completely (delete entry and credentials)."""
    try:
        with get_client() as client:
            # Get connection info
            connections = client.get("/api/v1/user-connections")
            
            connection = None
            for conn in connections:
                if conn.get("connection_id") == connection_id:
                    connection = conn
                    break
            
            if not connection:
                error(f"Connection '{connection_id}' not found")
                raise typer.Exit(1)
            
            tool = connection["tool"]
            tool_display = connection.get("display_name") or connection_id
            
            # Confirm
            if not force:
                warning("⚠️  This will permanently delete the connection and credentials")
                confirm = typer.confirm(f"Remove {tool} connection '{tool_display}'?")
                if not confirm:
                    info("Cancelled")
                    return
            
            # Delete connection entry (backend will cascade delete credentials)
            client.delete(f"/api/v1/user-connections/{connection_id}")
            
            success(f"✅ Removed: {connection_id}")
            
    except Exception as e:
        error(f"Failed to remove: {e}")
        raise typer.Exit(1) 