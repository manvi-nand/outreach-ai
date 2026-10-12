# ✉️ OutreachAI

AI-powered cold outreach automation — researches companies, finds real contact emails using a hybrid approach (Apollo → Hunter → Snov), drafts personalized emails with OpenAI, and keeps you in the loop for every send.

## Features

- **Resume Parsing** — Upload your PDF once; OpenAI extracts skills, experience, and target roles
- **Company Research** — Type any company name; Clearbit + Apollo fetch industry, size, and description
- **Hybrid Contact Discovery** — Apollo.io (primary) → Hunter.io (fallback) → Snov.io (third fallback) → email verification
- **AI Email Drafting** — OpenAI writes personalized cold emails referencing your resume + company context
- **Human-in-the-Loop** — Every draft goes through your review: Approve, Edit, Regenerate, or Reject
- **Gmail Integration** — Sends via your real Gmail account using Google OAuth (no passwords stored)
- **Automated Follow-ups** — Scheduler drafts follow-ups at Day 5 and Day 10, queued for your approval
- **Reply Detection** — Gmail inbox is checked; replied contacts are auto-updated
- **Analytics Dashboard** — Status tracking, reply rates, follow-up progress

## Quick Start

### 1. Install dependencies

```bash
cd /path/to/project
pip install -r requirements.txt
```

### 2. Set up environment

```bash
cp .env.example .env
# Fill in your API keys in .env (or use the Settings page in the app)
```

### 3. Run the app

```bash
streamlit run streamlit_app.py
```

### 4. (Optional) Run the follow-up scheduler in a separate terminal

```bash
python scheduler.py
```

## API Keys Needed

| Service | Purpose | Free Tier |
|---------|---------|-----------|
| [OpenAI](https://platform.openai.com) | AI (resume parsing, email drafting) | Pay-per-use |
| [Apollo.io](https://app.apollo.io) | Primary contact discovery | 50 exports/month |
| [Hunter.io](https://hunter.io) | Contact fallback + email verification | 25 searches/month |
| [Snov.io](https://snov.io) | Third contact fallback | 50 credits/month |
| [Clearbit](https://clearbit.com) | Company research | Limited free |
| [Google Cloud](https://console.cloud.google.com) | Gmail sending via OAuth | Free |

## Project Structure

```
├── streamlit_app.py          # Main app / Home page
├── scheduler.py              # Follow-up scheduler (run separately)
├── requirements.txt
├── .env.example
├── pages/
│   ├── 1_Dashboard.py        # Analytics + all outreach
│   ├── 2_New_Outreach.py     # Add company, find contacts, draft emails
│   ├── 3_Review_Drafts.py    # Human-in-the-loop email review
│   └── 4_Settings.py         # API keys + Gmail OAuth
├── services/
│   ├── claude_service.py     # Resume parsing + email drafting (OpenAI)
│   ├── contact_finder.py     # Hybrid discovery orchestrator
│   ├── apollo_service.py     # Apollo.io integration
│   ├── hunter_service.py     # Hunter.io integration
│   ├── snov_service.py       # Snov.io integration
│   ├── clearbit_service.py   # Company research
│   └── gmail_service.py      # Gmail OAuth + sending
├── database/
│   ├── models.py             # SQLAlchemy models
│   └── db.py                 # DB connection + session
└── uploads/                  # Resume PDFs stored here
```

## How the Hybrid Contact Discovery Works

```
Company name entered
       ↓
① Apollo.io — best quality (name, title, LinkedIn, email)
       ↓ if < 5 results
② Hunter.io — domain-based fallback
       ↓ if still < 5 results
③ Snov.io — third fallback
       ↓
Deduplicate by email
       ↓
Verify all emails via Hunter
       ↓
Show ranked contact list
```

## Gmail OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project
3. Enable the **Gmail API**
4. Go to **APIs & Services → Credentials → Create OAuth 2.0 Client ID**
5. Application type: **Web application**
6. Authorized redirect URIs: `http://localhost:8501`
7. Copy **Client ID** and **Client Secret** into Settings

## Follow-up Flow

```
Initial email sent
       ↓ Day 5
Scheduler drafts Follow-up 1 → queued for your approval
       ↓ You approve → sends
       ↓ Day 10
Scheduler drafts Follow-up 2 → queued for your approval
       ↓ You approve → sends
       ↓
Marked "No Response" (or "Replied" if reply detected)
```
