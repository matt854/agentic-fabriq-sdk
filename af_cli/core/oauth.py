"""
OAuth2/PKCE authentication flow for Agentic Fabric CLI.

This module implements the Authorization Code Flow with PKCE (Proof Key for Code Exchange)
for secure authentication without requiring client secrets.
"""

import base64
import hashlib
import secrets
import socket
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Dict, Optional, Tuple
from urllib.parse import parse_qs, urlencode, urlparse

import httpx
from rich.console import Console

console = Console()


class PKCEGenerator:
    """Generate PKCE code verifier and challenge."""
    
    @staticmethod
    def generate_code_verifier(length: int = 128) -> str:
        """
        Generate a cryptographically random code verifier.
        
        Args:
            length: Length of the verifier (43-128 characters)
            
        Returns:
            Base64-URL-encoded random string
        """
        if not 43 <= length <= 128:
            raise ValueError("Code verifier length must be between 43 and 128 characters")
        
        # Generate random bytes
        random_bytes = secrets.token_bytes(96)  # 96 bytes = 128 base64 chars
        
        # Base64-URL encode (no padding)
        verifier = base64.urlsafe_b64encode(random_bytes).decode('utf-8')
        verifier = verifier.rstrip('=')  # Remove padding
        
        return verifier[:length]
    
    @staticmethod
    def generate_code_challenge(verifier: str) -> str:
        """
        Generate a code challenge from the verifier using S256 method.
        
        Args:
            verifier: The code verifier
            
        Returns:
            Base64-URL-encoded SHA256 hash of the verifier
        """
        # SHA256 hash
        digest = hashlib.sha256(verifier.encode('utf-8')).digest()
        
        # Base64-URL encode (no padding)
        challenge = base64.urlsafe_b64encode(digest).decode('utf-8')
        challenge = challenge.rstrip('=')  # Remove padding
        
        return challenge


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """HTTP request handler for OAuth callback."""
    
    # Class variables to share data between handler and server
    authorization_code: Optional[str] = None
    error: Optional[str] = None
    state: Optional[str] = None
    
    def do_GET(self):
        """Handle GET request to callback endpoint."""
        try:
            # Parse query parameters
            parsed_path = urlparse(self.path)
            query_params = parse_qs(parsed_path.query)
            
            # Extract authorization code
            if 'code' in query_params:
                OAuthCallbackHandler.authorization_code = query_params['code'][0]
                OAuthCallbackHandler.state = query_params.get('state', [None])[0]
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                success_html = """
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Authentication Successful</title>
                    <style>
                        body {
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        }
                        .container {
                            background: white;
                            padding: 40px;
                            border-radius: 10px;
                            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                            text-align: center;
                        }
                        h1 { color: #667eea; margin-bottom: 20px; }
                        p { color: #666; font-size: 16px; }
                        .checkmark {
                            width: 80px;
                            height: 80px;
                            margin: 0 auto 20px;
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <svg class="checkmark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52">
                            <circle cx="26" cy="26" r="25" fill="none" stroke="#667eea" stroke-width="2"/>
                            <path fill="none" stroke="#667eea" stroke-width="4" d="M14 27l7 7 16-16"/>
                        </svg>
                        <h1>Authentication Successful!</h1>
                        <p>You have been successfully authenticated.</p>
                        <p>You can now close this window and return to the terminal.</p>
                    </div>
                </body>
                </html>
                """
                self.wfile.write(success_html.encode('utf-8'))
                
            elif 'error' in query_params:
                OAuthCallbackHandler.error = query_params['error'][0]
                error_description = query_params.get('error_description', ['Unknown error'])[0]
                
                # Send error response
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                error_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Authentication Failed</title>
                    <style>
                        body {{
                            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                            height: 100vh;
                            margin: 0;
                            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                        }}
                        .container {{
                            background: white;
                            padding: 40px;
                            border-radius: 10px;
                            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
                            text-align: center;
                        }}
                        h1 {{ color: #f5576c; margin-bottom: 20px; }}
                        p {{ color: #666; font-size: 16px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>Authentication Failed</h1>
                        <p>{error_description}</p>
                        <p>Please try again or contact support.</p>
                    </div>
                </body>
                </html>
                """
                self.wfile.write(error_html.encode('utf-8'))
                
        except Exception as e:
            console.print(f"[red]Error handling callback: {e}[/red]")
            self.send_response(500)
            self.end_headers()
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass


class LocalCallbackServer:
    """Local HTTP server for OAuth callback."""
    
    def __init__(self, port: int = 8089):
        """
        Initialize callback server.
        
        Args:
            port: Port to listen on (default: 8089)
        """
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
    
    def _find_free_port(self) -> int:
        """Find a free port to use."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    def start(self) -> int:
        """
        Start the callback server.
        
        Returns:
            The port the server is listening on
        """
        # Reset handler state before starting
        OAuthCallbackHandler.authorization_code = None
        OAuthCallbackHandler.error = None
        OAuthCallbackHandler.state = None
        
        # Try to bind to the specified port, fall back to a free port if busy
        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                # Create server
                self.server = HTTPServer(('localhost', self.port), OAuthCallbackHandler)
                break
            except OSError as e:
                if attempt < max_attempts - 1:
                    # Port is busy, try next port
                    self.port += 1
                else:
                    raise Exception(f"Could not start server on ports 8089-{self.port}: {e}")
        
        # Start server in background thread
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        
        return self.port
    
    def wait_for_callback(self, timeout: int = 300) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """
        Wait for OAuth callback with authorization code.
        
        Args:
            timeout: Maximum time to wait in seconds (default: 5 minutes)
            
        Returns:
            Tuple of (authorization_code, state, error)
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if OAuthCallbackHandler.authorization_code or OAuthCallbackHandler.error:
                break
            time.sleep(0.1)
        
        # Get results
        code = OAuthCallbackHandler.authorization_code
        state = OAuthCallbackHandler.state
        error = OAuthCallbackHandler.error
        
        # Clean up
        self.stop()
        
        return code, state, error
    
    def stop(self):
        """Stop the callback server."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        
        # Reset handler state
        OAuthCallbackHandler.authorization_code = None
        OAuthCallbackHandler.error = None
        OAuthCallbackHandler.state = None


class OAuth2Client:
    """OAuth2/PKCE client for Keycloak."""
    
    def __init__(
        self,
        keycloak_url: str,
        realm: str,
        client_id: str,
        scopes: Optional[list] = None
    ):
        """
        Initialize OAuth2 client.
        
        Args:
            keycloak_url: Keycloak base URL (e.g., https://auth.agenticfabriq.com or http://localhost:8080 for local)
            realm: Keycloak realm name
            client_id: Client ID for the CLI
            scopes: List of OAuth scopes to request
        """
        self.keycloak_url = keycloak_url.rstrip('/')
        self.realm = realm
        self.client_id = client_id
        self.scopes = scopes or ['openid', 'profile', 'email']
        
        # Endpoints
        self.auth_endpoint = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/auth"
        self.token_endpoint = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/token"
        self.userinfo_endpoint = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/userinfo"
        self.logout_endpoint = f"{self.keycloak_url}/realms/{self.realm}/protocol/openid-connect/logout"
    
    def login(self, open_browser: bool = True, timeout: int = 300, use_hosted_callback: bool = True) -> Dict[str, any]:
        """
        Perform OAuth2/PKCE login flow.
        
        Args:
            open_browser: Whether to automatically open the browser
            timeout: Maximum time to wait for login (seconds)
            use_hosted_callback: Use branded hosted callback page (default: True)
            
        Returns:
            Dictionary containing access_token, refresh_token, expires_in, etc.
            
        Raises:
            Exception: If authentication fails
        """
        # Generate PKCE parameters
        code_verifier = PKCEGenerator.generate_code_verifier()
        code_challenge = PKCEGenerator.generate_code_challenge(code_verifier)
        state = secrets.token_urlsafe(32)
        
        # Start local callback server
        callback_server = LocalCallbackServer()
        callback_port = callback_server.start()
        
        # Determine redirect URI
        # Use hosted page that shows success message and redirects back to localhost
        if use_hosted_callback:
            # Extract base URL from keycloak_url (assumes gateway is on same domain)
            gateway_url = self.keycloak_url.replace('auth.', 'dashboard.')
            redirect_uri = f"{gateway_url}/cli-callback?port={callback_port}"
        else:
            # Direct localhost redirect (fallback)
            redirect_uri = f"http://localhost:{callback_port}/callback"
        
        # Build authorization URL
        auth_params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': redirect_uri,
            'scope': ' '.join(self.scopes),
            'state': state,
            'code_challenge': code_challenge,
            'code_challenge_method': 'S256',
        }
        
        auth_url = f"{self.auth_endpoint}?{urlencode(auth_params)}"
        
        # Display instructions
        console.print("\n[bold cyan]Opening browser for authentication...[/bold cyan]")
        console.print(f"[dim]If browser doesn't open, visit: {auth_url}[/dim]\n")
        
        # Open browser
        if open_browser:
            try:
                webbrowser.open(auth_url)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not open browser: {e}[/yellow]")
                console.print(f"[yellow]Please manually visit: {auth_url}[/yellow]")
        
        console.print("[bold]Waiting for login to complete...[/bold]")
        
        # Wait for callback
        auth_code, returned_state, error = callback_server.wait_for_callback(timeout)
        
        if error:
            raise Exception(f"Authentication failed: {error}")
        
        if not auth_code:
            raise Exception("Authentication timed out. Please try again.")
        
        if returned_state != state:
            raise Exception("State mismatch. Possible CSRF attack.")
        
        # Exchange authorization code for tokens
        console.print("[bold green]✓[/bold green] Authorization received, exchanging for tokens...")
        
        token_data = {
            'grant_type': 'authorization_code',
            'client_id': self.client_id,
            'code': auth_code,
            'redirect_uri': redirect_uri,
            'code_verifier': code_verifier,
        }
        
        try:
            response = httpx.post(
                self.token_endpoint,
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30.0
            )
            response.raise_for_status()
            
            tokens = response.json()
            return tokens
            
        except httpx.HTTPStatusError as e:
            error_detail = e.response.text
            raise Exception(f"Token exchange failed: {error_detail}")
        except Exception as e:
            raise Exception(f"Token exchange error: {e}")
    
    def refresh_token(self, refresh_token: str) -> Dict[str, any]:
        """
        Refresh an expired access token.
        
        Args:
            refresh_token: The refresh token
            
        Returns:
            Dictionary containing new tokens
            
        Raises:
            Exception: If refresh fails
        """
        token_data = {
            'grant_type': 'refresh_token',
            'client_id': self.client_id,
            'refresh_token': refresh_token,
        }
        
        try:
            response = httpx.post(
                self.token_endpoint,
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30.0
            )
            response.raise_for_status()
            
            return response.json()
            
        except httpx.HTTPStatusError as e:
            raise Exception(f"Token refresh failed: {e.response.text}")
        except Exception as e:
            raise Exception(f"Token refresh error: {e}")
    
    def get_user_info(self, access_token: str) -> Dict[str, any]:
        """
        Get user information using access token.
        
        Args:
            access_token: The access token
            
        Returns:
            Dictionary containing user information
        """
        try:
            response = httpx.get(
                self.userinfo_endpoint,
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=30.0
            )
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            raise Exception(f"Failed to get user info: {e}")
    
    def logout(self, refresh_token: str) -> None:
        """
        Logout and revoke tokens.
        
        Args:
            refresh_token: The refresh token to revoke
        """
        try:
            data = {
                'client_id': self.client_id,
                'refresh_token': refresh_token,
            }
            
            response = httpx.post(
                self.logout_endpoint,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                timeout=30.0
            )
            response.raise_for_status()
            
        except Exception:
            # Ignore errors during logout
            pass

