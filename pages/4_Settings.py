import streamlit as st
import os
from pathlib import Path
from dotenv import load_dotenv, set_key
from services import gmail_service

st.set_page_config(page_title="Settings — OutreachAI", page_icon="⚙️", layout="wide")

load_dotenv()
ENV_PATH = Path(".env")

st.title("⚙️ Settings")
st.markdown("Configure your API keys and Gmail connection.")
st.markdown("---")

# ── Helper to write .env ───────────────────────────────────────────────────────
def save_env_key(key: str, value: str):
    if not ENV_PATH.exists():
        ENV_PATH.touch()
    set_key(str(ENV_PATH), key, value)
    os.environ[key] = value


# ── Gmail OAuth ────────────────────────────────────────────────────────────────
st.markdown("### 📧 Gmail Connection")

# Check if OAuth code is in query params (redirect from Google)
params = st.query_params
if "code" in params:
    code = params["code"]
    with st.spinner("Connecting to Gmail..."):
        success = gmail_service.exchange_code_for_token(code)
    if success:
        st.success("Gmail connected successfully!")
        st.query_params.clear()
        st.rerun()
    else:
        st.error("Failed to connect Gmail. Please try again.")

if gmail_service.is_authenticated():
    email_addr = gmail_service.get_authenticated_email()
    st.success(f"✅ Gmail connected: **{email_addr}**")
    if st.button("Disconnect Gmail"):
        token_path = Path("gmail_token.json")
        if token_path.exists():
            token_path.unlink()
        st.success("Gmail disconnected.")
        st.rerun()
else:
    st.warning("Gmail not connected. Connect to send emails.")

    has_google_creds = gmail_service.has_client_credentials()
    if has_google_creds:
        auth_url = gmail_service.get_auth_url()
        st.markdown(f"""
**Step 1:** Click the link below to authorize Gmail access:

[🔗 Connect Gmail Account]({auth_url})

**Step 2:** After authorizing, you'll be redirected back here automatically.
        """)
        st.info("Make sure `GOOGLE_REDIRECT_URI=http://localhost:8501` is set in your .env file and matches your Google Cloud Console redirect URI.")
    else:
        st.info("Enter your Google OAuth credentials below first, then come back to connect Gmail.")

st.markdown("---")

# ── API Keys ───────────────────────────────────────────────────────────────────
st.markdown("### 🔑 API Keys")
st.markdown("All keys are stored locally in your `.env` file.")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### AI")
    openai_key = st.text_input(
        "OpenAI API Key",
        value=os.getenv("OPENAI_API_KEY", ""),
        type="password",
        help="Get from platform.openai.com → API Keys",
    )

    st.markdown("#### Contact Discovery (Hybrid)")
    apollo_key = st.text_input(
        "Apollo.io API Key (Primary)",
        value=os.getenv("APOLLO_API_KEY", ""),
        type="password",
        help="Get from app.apollo.io → Settings → API",
    )
    hunter_key = st.text_input(
        "Hunter.io API Key (Fallback + Verifier)",
        value=os.getenv("HUNTER_API_KEY", ""),
        type="password",
        help="Get from hunter.io → API",
    )
    snov_client_id = st.text_input(
        "Snov.io Client ID (Third fallback)",
        value=os.getenv("SNOV_CLIENT_ID", ""),
        type="password",
        help="Get from snov.io → API",
    )
    snov_client_secret = st.text_input(
        "Snov.io Client Secret",
        value=os.getenv("SNOV_CLIENT_SECRET", ""),
        type="password",
    )

with col2:
    st.markdown("#### Company Research")
    clearbit_key = st.text_input(
        "Clearbit API Key *(optional)*",
        value=os.getenv("CLEARBIT_API_KEY", ""),
        type="password",
        help="Optional — Apollo already provides company info. Get from clearbit.com → API if you want extra enrichment.",
    )

    st.markdown("#### Google OAuth (for Gmail)")
    google_client_id = st.text_input(
        "Google Client ID",
        value=os.getenv("GOOGLE_CLIENT_ID", ""),
        type="password",
        help="Create at console.cloud.google.com → APIs & Services → Credentials",
    )
    google_client_secret = st.text_input(
        "Google Client Secret",
        value=os.getenv("GOOGLE_CLIENT_SECRET", ""),
        type="password",
    )
    google_redirect_uri = st.text_input(
        "Google Redirect URI",
        value=os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8501"),
        help="Must match exactly what's in Google Cloud Console",
    )

    st.markdown("#### Follow-up Schedule")
    followup_1 = st.number_input(
        "Follow-up 1 — days after initial email",
        min_value=1, max_value=30,
        value=int(os.getenv("FOLLOWUP_1_DAYS", 5)),
    )
    followup_2 = st.number_input(
        "Follow-up 2 — days after initial email",
        min_value=1, max_value=60,
        value=int(os.getenv("FOLLOWUP_2_DAYS", 10)),
    )

if st.button("💾 Save All Settings", type="primary"):
    if openai_key:
        save_env_key("OPENAI_API_KEY", openai_key)
    if apollo_key:
        save_env_key("APOLLO_API_KEY", apollo_key)
    if hunter_key:
        save_env_key("HUNTER_API_KEY", hunter_key)
    if snov_client_id:
        save_env_key("SNOV_CLIENT_ID", snov_client_id)
    if snov_client_secret:
        save_env_key("SNOV_CLIENT_SECRET", snov_client_secret)
    if clearbit_key:
        save_env_key("CLEARBIT_API_KEY", clearbit_key)
    if google_client_id:
        save_env_key("GOOGLE_CLIENT_ID", google_client_id)
    if google_client_secret:
        save_env_key("GOOGLE_CLIENT_SECRET", google_client_secret)
    if google_redirect_uri:
        save_env_key("GOOGLE_REDIRECT_URI", google_redirect_uri)
    save_env_key("FOLLOWUP_1_DAYS", str(followup_1))
    save_env_key("FOLLOWUP_2_DAYS", str(followup_2))
    st.success("✅ Settings saved to .env")

st.markdown("---")

# ── Setup Guide ────────────────────────────────────────────────────────────────
st.markdown("### 📖 Quick Setup Guide")

with st.expander("How to get each API key"):
    st.markdown("""
**OpenAI (GPT-4o)**
1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign in → API Keys → Create new secret key
3. Add billing credits at platform.openai.com/account/billing

**Apollo.io** *(Primary contact source — free tier: 50 exports/month)*
1. Go to [app.apollo.io](https://app.apollo.io)
2. Settings → Integrations → API → Create API Key

**Hunter.io** *(Email fallback + verifier — free tier: 25 searches/month)*
1. Go to [hunter.io](https://hunter.io)
2. Account → API → Copy API Key

**Snov.io** *(Third fallback — free tier: 50 credits/month)*
1. Go to [snov.io](https://snov.io)
2. Account → API → Get Client ID & Secret

**Clearbit** *(Company research)*
1. Go to [clearbit.com](https://clearbit.com)
2. Sign up → Dashboard → API → Copy Key

**Google OAuth (Gmail sending)**
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create project → Enable Gmail API
3. APIs & Services → Credentials → Create OAuth 2.0 Client ID
4. Application type: **Web application**
5. Authorized redirect URIs: `http://localhost:8501`
6. Copy Client ID and Client Secret here
    """)

with st.expander("Running the follow-up scheduler"):
    st.markdown("""
The scheduler checks for pending follow-ups every hour. Run it in a separate terminal:

```bash
python scheduler.py
```

Keep it running in the background while using the app. It will:
- Detect when follow-ups are due (5 days / 10 days after sending)
- Draft follow-up emails using Claude
- Queue them for your approval in the **Review Drafts** tab
- Check your Gmail for replies and auto-update statuses
    """)
