"""Google Calendar API with OAuth for personal use."""
import os
import json
import pickle
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Scopes required for calendar operations
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
]

# Token storage path (in project root)
TOKEN_PATH = Path(__file__).parent.parent / 'token.pickle'
CREDENTIALS_PATH = Path(__file__).parent.parent / 'credentials.json'


def get_calendar_api_resource():
    """Get Google Calendar API resource using OAuth.

    This uses OAuth 2.0 for personal calendar access:
    - First time: Opens browser for authorization
    - Subsequent times: Uses saved token from token.pickle
    - Token auto-refreshes when expired

    Returns:
        Google Calendar API service object

    Raises:
        ValueError: If credentials.json is not found
    """
    creds = None

    # Check if we have a saved token
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)

    # If no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh expired token
            creds.refresh(Request())
        else:
            # Need to do full OAuth flow
            if not CREDENTIALS_PATH.exists():
                raise ValueError(
                    f"OAuth credentials not found!\n\n"
                    f"Please download credentials.json from Google Cloud Console:\n"
                    f"1. Go to https://console.cloud.google.com/apis/credentials\n"
                    f"2. Create OAuth 2.0 Client ID (Desktop app)\n"
                    f"3. Download JSON and save as: {CREDENTIALS_PATH}\n\n"
                    f"See README for detailed setup instructions."
                )

            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )
            # Run local server for OAuth callback
            creds = flow.run_local_server(port=0)

        # Save the credentials for next time
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)

    return build('calendar', 'v3', credentials=creds)


def check_auth_status() -> dict:
    """Check if OAuth is configured and valid.

    If not authenticated, this will trigger the OAuth flow (browser will open).

    Returns:
        dict with:
        - authenticated: bool
        - needs_auth: bool (always False after this function succeeds)
        - message: str
    """
    try:
        # Check if credentials.json exists
        if not CREDENTIALS_PATH.exists():
            return {
                "authenticated": False,
                "needs_auth": True,
                "message": f"credentials.json not found at {CREDENTIALS_PATH}. Download from Google Cloud Console. See OAUTH_SETUP.md",
            }

        # Try to get the API resource - this will trigger OAuth flow if needed
        # This ensures we're actually authenticated, not just checking if a token exists
        try:
            get_calendar_api_resource()
            return {
                "authenticated": True,
                "needs_auth": False,
                "message": "OAuth configured successfully",
            }
        except Exception as e:
            return {
                "authenticated": False,
                "needs_auth": True,
                "message": f"Authentication failed: {str(e)}",
            }

    except Exception as e:
        return {
            "authenticated": False,
            "needs_auth": True,
            "message": f"Auth check failed: {str(e)}",
        }
