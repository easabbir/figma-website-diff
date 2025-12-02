"""Figma OAuth 2.0 authentication service."""

import os
import base64
import secrets
import requests
from typing import Optional, Dict
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging
from dotenv import load_dotenv

# Load .env file
load_dotenv(Path(__file__).parent.parent.parent / ".env")

logger = logging.getLogger(__name__)

# OAuth configuration
FIGMA_OAUTH_URL = "https://www.figma.com/oauth"
FIGMA_TOKEN_URL = "https://api.figma.com/v1/oauth/token"

# Token storage file (in production, use a proper database)
TOKEN_STORAGE_FILE = Path(__file__).parent.parent.parent / "data" / "oauth_tokens.json"


class FigmaOAuthConfig:
    """Configuration for Figma OAuth."""
    
    def __init__(self):
        self.client_id = os.getenv("FIGMA_CLIENT_ID", "")
        self.client_secret = os.getenv("FIGMA_CLIENT_SECRET", "")
        self.redirect_uri = os.getenv("FIGMA_REDIRECT_URI", "http://localhost:8000/api/v1/oauth/callback")
        # Figma OAuth scopes - file_content:read for reading file content and rendering images
        self.scopes = "file_content:read"
    
    @property
    def is_configured(self) -> bool:
        """Check if OAuth is properly configured."""
        return bool(self.client_id and self.client_secret)


class TokenStorage:
    """Simple file-based token storage. In production, use a database."""
    
    def __init__(self, storage_file: Path = TOKEN_STORAGE_FILE):
        self.storage_file = storage_file
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self._tokens: Dict[str, Dict] = {}
        self._load()
    
    def _load(self):
        """Load tokens from file."""
        if self.storage_file.exists():
            try:
                with open(self.storage_file, 'r') as f:
                    self._tokens = json.load(f)
            except Exception as e:
                logger.error(f"Error loading tokens: {e}")
                self._tokens = {}
    
    def _save(self):
        """Save tokens to file."""
        try:
            with open(self.storage_file, 'w') as f:
                json.dump(self._tokens, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving tokens: {e}")
    
    def store_token(self, user_id: str, token_data: Dict):
        """Store token data for a user."""
        self._tokens[user_id] = {
            **token_data,
            "stored_at": datetime.now().isoformat()
        }
        self._save()
        logger.info(f"Stored OAuth token for user {user_id}")
    
    def get_token(self, user_id: str) -> Optional[Dict]:
        """Get token data for a user."""
        return self._tokens.get(user_id)
    
    def get_default_token(self) -> Optional[Dict]:
        """Get the most recently stored token (for single-user mode)."""
        if not self._tokens:
            return None
        # Return the most recently stored token
        latest = max(self._tokens.items(), key=lambda x: x[1].get("stored_at", ""))
        return latest[1] if latest else None
    
    def delete_token(self, user_id: str):
        """Delete token for a user."""
        if user_id in self._tokens:
            del self._tokens[user_id]
            self._save()
    
    def list_users(self) -> list:
        """List all users with stored tokens."""
        return list(self._tokens.keys())


class FigmaOAuth:
    """Figma OAuth 2.0 handler."""
    
    def __init__(self, config: Optional[FigmaOAuthConfig] = None):
        self.config = config or FigmaOAuthConfig()
        self.token_storage = TokenStorage()
        self._pending_states: Dict[str, datetime] = {}  # state -> created_at
    
    def generate_auth_url(self, state: Optional[str] = None) -> Dict[str, str]:
        """
        Generate the OAuth authorization URL.
        
        Returns:
            Dict with 'url' and 'state' keys
        """
        if not self.config.is_configured:
            raise ValueError("Figma OAuth is not configured. Set FIGMA_CLIENT_ID and FIGMA_CLIENT_SECRET environment variables.")
        
        # Generate state for CSRF protection
        state = state or secrets.token_urlsafe(32)
        self._pending_states[state] = datetime.now()
        
        # Clean up old states (older than 10 minutes)
        cutoff = datetime.now() - timedelta(minutes=10)
        self._pending_states = {k: v for k, v in self._pending_states.items() if v > cutoff}
        
        params = {
            "client_id": self.config.client_id,
            "redirect_uri": self.config.redirect_uri,
            "state": state,
            "response_type": "code"
        }
        
        # Only add scope if configured
        if self.config.scopes:
            params["scope"] = self.config.scopes
        
        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        auth_url = f"{FIGMA_OAUTH_URL}?{query_string}"
        
        return {
            "url": auth_url,
            "state": state
        }
    
    def validate_state(self, state: str) -> bool:
        """Validate the state parameter from callback."""
        if state in self._pending_states:
            del self._pending_states[state]
            return True
        return False
    
    def exchange_code_for_token(self, code: str) -> Dict:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from OAuth callback
            
        Returns:
            Token response with access_token, refresh_token, expires_in
        """
        if not self.config.is_configured:
            raise ValueError("Figma OAuth is not configured")
        
        # Create Basic Auth header
        credentials = f"{self.config.client_id}:{self.config.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}"
        }
        
        data = {
            "redirect_uri": self.config.redirect_uri,
            "code": code,
            "grant_type": "authorization_code"
        }
        
        try:
            response = requests.post(FIGMA_TOKEN_URL, headers=headers, data=data)
            response.raise_for_status()
            token_data = response.json()
            
            # Store the token
            user_id = token_data.get("user_id_string", token_data.get("user_id", "default"))
            
            # Calculate expiration time
            expires_in = token_data.get("expires_in", 3600)
            token_data["expires_at"] = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
            
            self.token_storage.store_token(str(user_id), token_data)
            
            logger.info(f"Successfully exchanged code for token (user: {user_id})")
            return token_data
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error exchanging code for token: {e.response.text}")
            raise ValueError(f"Failed to exchange code: {e.response.text}")
        except Exception as e:
            logger.error(f"Error exchanging code for token: {e}")
            raise
    
    def refresh_token(self, refresh_token: str) -> Dict:
        """
        Refresh an expired access token.
        
        Args:
            refresh_token: The refresh token
            
        Returns:
            New token response
        """
        if not self.config.is_configured:
            raise ValueError("Figma OAuth is not configured")
        
        # Create Basic Auth header
        credentials = f"{self.config.client_id}:{self.config.client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {encoded_credentials}"
        }
        
        data = {
            "refresh_token": refresh_token,
            "grant_type": "refresh_token"
        }
        
        try:
            response = requests.post(FIGMA_TOKEN_URL, headers=headers, data=data)
            response.raise_for_status()
            token_data = response.json()
            
            # Calculate expiration time
            expires_in = token_data.get("expires_in", 3600)
            token_data["expires_at"] = (datetime.now() + timedelta(seconds=expires_in)).isoformat()
            
            # Store the updated token
            user_id = token_data.get("user_id_string", token_data.get("user_id", "default"))
            self.token_storage.store_token(str(user_id), token_data)
            
            logger.info(f"Successfully refreshed token (user: {user_id})")
            return token_data
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"Error refreshing token: {e.response.text}")
            raise ValueError(f"Failed to refresh token: {e.response.text}")
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            raise
    
    def get_valid_access_token(self, user_id: Optional[str] = None) -> Optional[str]:
        """
        Get a valid access token, refreshing if necessary.
        
        Args:
            user_id: Optional user ID. If not provided, uses the default token.
            
        Returns:
            Valid access token or None
        """
        if user_id:
            token_data = self.token_storage.get_token(user_id)
        else:
            token_data = self.token_storage.get_default_token()
        
        if not token_data:
            return None
        
        # Check if token is expired
        expires_at = token_data.get("expires_at")
        if expires_at:
            expiry = datetime.fromisoformat(expires_at)
            # Refresh if expiring in less than 5 minutes
            if datetime.now() > expiry - timedelta(minutes=5):
                logger.info("Token expired or expiring soon, refreshing...")
                try:
                    refresh_token = token_data.get("refresh_token")
                    if refresh_token:
                        new_token_data = self.refresh_token(refresh_token)
                        return new_token_data.get("access_token")
                except Exception as e:
                    logger.error(f"Failed to refresh token: {e}")
                    return None
        
        return token_data.get("access_token")
    
    def get_oauth_status(self) -> Dict:
        """Get the current OAuth status."""
        token_data = self.token_storage.get_default_token()
        
        if not self.config.is_configured:
            return {
                "configured": False,
                "authenticated": False,
                "message": "OAuth not configured. Set FIGMA_CLIENT_ID and FIGMA_CLIENT_SECRET."
            }
        
        if not token_data:
            return {
                "configured": True,
                "authenticated": False,
                "message": "OAuth configured but not authenticated. Click 'Connect Figma' to authenticate."
            }
        
        # Check if token is valid
        access_token = self.get_valid_access_token()
        if access_token:
            user_id = token_data.get("user_id_string", "unknown")
            return {
                "configured": True,
                "authenticated": True,
                "user_id": user_id,
                "message": f"Authenticated as user {user_id}"
            }
        else:
            return {
                "configured": True,
                "authenticated": False,
                "message": "Token expired and refresh failed. Please re-authenticate."
            }


# Global OAuth instance
figma_oauth = FigmaOAuth()
