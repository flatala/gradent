"""Google Calendar API with Service Account - NO OAuth needed!"""
import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Scopes required for calendar operations
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events',
]


def get_calendar_api_resource():
    """Get Google Calendar API resource using Service Account.

    This is MUCH simpler than OAuth:
    - No browser authorization
    - No token.pickle
    - Just environment variables

    Returns:
        Google Calendar API service object

    Raises:
        ValueError: If service account credentials are not configured
    """
    client_email = os.getenv('GOOGLE_CALENDAR_CLIENT_EMAIL')
    private_key = os.getenv('GOOGLE_CALENDAR_PRIVATE_KEY')

    if not client_email or not private_key:
        raise ValueError(
            "Service account credentials not configured!\n\n"
            "Please set in .env:\n"
            "  GOOGLE_CALENDAR_CLIENT_EMAIL=your-service-account@project.iam.gserviceaccount.com\n"
            "  GOOGLE_CALENDAR_PRIVATE_KEY=\"-----BEGIN PRIVATE KEY-----\\n...\\n-----END PRIVATE KEY-----\\n\"\n\n"
            "See SERVICE_ACCOUNT_SETUP.md for 5-minute setup guide."
        )

    # Handle escaped newlines in private key
    if client_email == "your-service-account@your-project.iam.gserviceaccount.com":
        raise ValueError(
            "Please replace placeholder service account credentials in .env\n"
            "See SERVICE_ACCOUNT_SETUP.md for setup instructions."
        )

    # Replace literal \n with actual newlines
    private_key = private_key.replace('\\n', '\n')

    # Create credentials from service account info
    credentials_info = {
        "type": "service_account",
        "client_email": client_email,
        "private_key": private_key,
        "token_uri": "https://oauth2.googleapis.com/token",
    }

    credentials = service_account.Credentials.from_service_account_info(
        credentials_info,
        scopes=SCOPES
    )

    return build('calendar', 'v3', credentials=credentials)


def check_auth_status() -> dict:
    """Check if service account is configured.

    Returns:
        dict with:
        - authenticated: bool
        - needs_auth: bool
        - message: str
    """
    try:
        client_email = os.getenv('GOOGLE_CALENDAR_CLIENT_EMAIL')
        private_key = os.getenv('GOOGLE_CALENDAR_PRIVATE_KEY')

        if not client_email or not private_key:
            return {
                "authenticated": False,
                "needs_auth": True,
                "message": "Service account credentials not set in .env. See SERVICE_ACCOUNT_SETUP.md",
            }

        if client_email == "your-service-account@your-project.iam.gserviceaccount.com":
            return {
                "authenticated": False,
                "needs_auth": True,
                "message": "Please replace placeholder credentials in .env with real service account credentials.",
            }

        # Try to build the service to verify credentials
        try:
            get_calendar_api_resource()
            return {
                "authenticated": True,
                "needs_auth": False,
                "message": "Service account configured successfully",
            }
        except Exception as e:
            return {
                "authenticated": False,
                "needs_auth": True,
                "message": f"Service account credentials invalid: {str(e)}",
            }

    except Exception as e:
        return {
            "authenticated": False,
            "needs_auth": True,
            "message": f"Auth check failed: {str(e)}",
        }
