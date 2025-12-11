"""OAuth integration endpoints for Figma."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
import logging

from app.models.schemas import (
    OAuthStatusResponse,
    OAuthAuthorizationResponse,
    OAuthTokenResponse,
    OAuthRefreshResponse,
    OAuthLogoutResponse
)
from app.services.figma_oauth import figma_oauth
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


@router.get("/oauth/status", response_model=OAuthStatusResponse)
async def get_oauth_status() -> OAuthStatusResponse:
    """Get the current Figma OAuth status."""
    status = figma_oauth.get_oauth_status()
    return OAuthStatusResponse(
        configured=status.get("configured", False),
        authenticated=status.get("authenticated", False),
        message=status.get("message", "")
    )


@router.get("/oauth/authorize", response_model=OAuthAuthorizationResponse)
async def start_oauth_flow() -> OAuthAuthorizationResponse:
    """Start the Figma OAuth authorization flow."""
    try:
        auth_data = figma_oauth.generate_auth_url()
        return OAuthAuthorizationResponse(
            authorization_url=auth_data["url"],
            state=auth_data["state"],
            message="Redirect the user to the authorization_url to complete OAuth"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/oauth/callback")
async def oauth_callback(code: str = Query(...), state: str = Query(...)):
    """
    Handle the OAuth callback from Figma.
    
    This endpoint receives the authorization code after the user
    authorizes the application on Figma.
    """
    try:
        token_data = figma_oauth.exchange_code_for_token(code)
        
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}?oauth=success&user_id={token_data.get('user_id_string', 'unknown')}",
            status_code=302
        )
    except ValueError as e:
        logger.error(f"OAuth callback error: {e}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}?oauth=error&message={str(e)}",
            status_code=302
        )
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        return RedirectResponse(
            url=f"{settings.FRONTEND_URL}?oauth=error&message=Authentication failed",
            status_code=302
        )


@router.post("/oauth/refresh", response_model=OAuthRefreshResponse)
async def refresh_oauth_token() -> OAuthRefreshResponse:
    """Manually refresh the OAuth token."""
    token_data = figma_oauth.token_storage.get_default_token()
    if not token_data:
        raise HTTPException(status_code=400, detail="No token to refresh")
    
    refresh_token = token_data.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=400, detail="No refresh token available")
    
    try:
        new_token = figma_oauth.refresh_token(refresh_token)
        return OAuthRefreshResponse(
            success=True,
            expires_at=new_token.get("expires_at"),
            message="Token refreshed successfully"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/oauth/logout", response_model=OAuthLogoutResponse)
async def oauth_logout() -> OAuthLogoutResponse:
    """Log out from Figma OAuth (delete stored tokens)."""
    users = figma_oauth.token_storage.list_users()
    for user_id in users:
        figma_oauth.token_storage.delete_token(user_id)
    
    return OAuthLogoutResponse(success=True, message="Logged out successfully")


@router.get("/oauth/token", response_model=OAuthTokenResponse)
async def get_oauth_token() -> OAuthTokenResponse:
    """Get the current OAuth access token (for use in comparisons)."""
    access_token = figma_oauth.get_valid_access_token()
    if not access_token:
        raise HTTPException(
            status_code=401, 
            detail="No valid OAuth token. Please authenticate with Figma first."
        )
    
    return OAuthTokenResponse(
        access_token=access_token,
        token_type="bearer"
    )
