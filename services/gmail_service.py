import os
import json
import base64
import pickle
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from dotenv import load_dotenv

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]
TOKEN_PATH = Path("gmail_token.json")


def _get_client_config() -> dict:
    """Build OAuth client config fresh each time so .env changes are picked up."""
    load_dotenv(override=True)
    return {
        "web": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501")],
        }
    }


def get_auth_url() -> str:
    """Generate the Google OAuth authorization URL."""
    config = _get_client_config()
    redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501")
    flow = Flow.from_client_config(config, scopes=SCOPES)
    flow.redirect_uri = redirect_uri
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


def exchange_code_for_token(code: str) -> bool:
    """Exchange OAuth code for credentials and save them."""
    try:
        config = _get_client_config()
        redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501")
        flow = Flow.from_client_config(config, scopes=SCOPES)
        flow.redirect_uri = redirect_uri
        flow.fetch_token(code=code)
        creds = flow.credentials
        _save_credentials(creds)
        return True
    except Exception as e:
        print(f"[Gmail] Token exchange error: {e}")
        return False


def is_authenticated() -> bool:
    """Check if valid Gmail credentials exist."""
    creds = _load_credentials()
    return creds is not None and creds.valid


def get_authenticated_email() -> str:
    """Return the Gmail address of the authenticated user."""
    service = _get_service()
    if not service:
        return ""
    try:
        profile = service.users().getProfile(userId="me").execute()
        return profile.get("emailAddress", "")
    except Exception:
        return ""


def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email via Gmail API. Returns True on success."""
    service = _get_service()
    if not service:
        return False

    try:
        message = MIMEMultipart("alternative")
        message["To"] = to
        message["Subject"] = subject
        part = MIMEText(body, "plain")
        message.attach(part)

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        service.users().messages().send(userId="me", body={"raw": raw}).execute()
        return True
    except HttpError as e:
        print(f"[Gmail] Send error: {e}")
        return False


def check_for_reply(original_subject: str, contact_email: str) -> bool:
    """Check if a reply has been received for a given subject from a contact."""
    service = _get_service()
    if not service:
        return False

    try:
        query = f"from:{contact_email} subject:Re: {original_subject}"
        results = service.users().messages().list(userId="me", q=query, maxResults=1).execute()
        messages = results.get("messages", [])
        return len(messages) > 0
    except Exception as e:
        print(f"[Gmail] Reply check error: {e}")
        return False


def _get_service():
    creds = _load_credentials()
    if not creds:
        return None
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_credentials(creds)
        except Exception as e:
            print(f"[Gmail] Token refresh error: {e}")
            return None
    try:
        return build("gmail", "v1", credentials=creds)
    except Exception as e:
        print(f"[Gmail] Build service error: {e}")
        return None


def _save_credentials(creds: Credentials):
    TOKEN_PATH.write_text(creds.to_json())


def _load_credentials() -> Credentials | None:
    if not TOKEN_PATH.exists():
        return None
    try:
        creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        return creds
    except Exception:
        return None


def has_client_credentials() -> bool:
    """Check if Google OAuth credentials are configured."""
    load_dotenv(override=True)
    return bool(os.getenv("GOOGLE_CLIENT_ID")) and bool(os.getenv("GOOGLE_CLIENT_SECRET"))
