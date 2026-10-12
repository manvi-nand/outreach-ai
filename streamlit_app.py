import streamlit as st
from database.db import init_db, get_session
from database.models import OutreachRecord, EmailDraft, Contact, Company, Resume

# ── App config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="OutreachAI",
    page_icon="✉️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Init DB on startup ────────────────────────────────────────────────────────
init_db()

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .metric-card {
        background: #1e1e2e;
        border-radius: 12px;
        padding: 20px;
        border: 1px solid #313244;
    }
    .status-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    .status-active { background: #1e3a5f; color: #60a5fa; }
    .status-replied { background: #1a3a2a; color: #4ade80; }
    .status-no_response { background: #3a1a1a; color: #f87171; }
    .status-pending { background: #3a2a10; color: #fb923c; }
    [data-testid="stSidebar"] { background: #0f0f1a; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar nav ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ✉️ OutreachAI")
    st.markdown("*AI-powered cold outreach*")
    st.markdown("---")
    st.markdown("**Navigation**")
    st.page_link("streamlit_app.py", label="🏠 Home", icon=None)
    st.page_link("pages/1_Dashboard.py", label="📊 Dashboard")
    st.page_link("pages/2_New_Outreach.py", label="🚀 New Outreach")
    st.page_link("pages/3_Review_Drafts.py", label="✏️ Review Drafts")
    st.page_link("pages/4_Settings.py", label="⚙️ Settings")
    st.markdown("---")

# ── Home page ─────────────────────────────────────────────────────────────────
st.title("✉️ OutreachAI")
st.markdown("#### AI-powered job outreach — researches companies, finds contacts, drafts personalized emails. You stay in control.")
st.markdown("---")

# Live stats
db = get_session()
total_sent = db.query(EmailDraft).filter(EmailDraft.status == "sent").count()
pending_review = db.query(EmailDraft).filter(EmailDraft.status == "pending_review").count()
replied = db.query(OutreachRecord).filter(OutreachRecord.status == "replied").count()
total_companies = db.query(Company).count()
active_resume = db.query(Resume).filter(Resume.is_active == True).first()
db.close()

# Stats row
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Companies Researched", total_companies)
with col2:
    st.metric("Emails Sent", total_sent)
with col3:
    st.metric("Replies Received", replied)
with col4:
    st.metric("Awaiting Your Approval", pending_review, delta="Review now" if pending_review > 0 else None)

st.markdown("---")

# Quickstart guide
col_left, col_right = st.columns([1, 1])

with col_left:
    st.markdown("### How it works")
    steps = [
        ("1️⃣", "Upload Resume", "Go to **New Outreach** and upload your PDF resume. Claude parses it once."),
        ("2️⃣", "Add a Company", "Type any company name. We fetch their info and find real contact emails."),
        ("3️⃣", "AI Drafts Email", "Claude writes a personalized cold email based on your resume + company research."),
        ("4️⃣", "You Approve", "Review the draft. Edit, approve, or regenerate. Nothing sends without your OK."),
        ("5️⃣", "Auto Follow-ups", "If no reply in 5 days, Claude drafts a follow-up for your approval. Again at 10 days."),
    ]
    for icon, title, desc in steps:
        st.markdown(f"**{icon} {title}**")
        st.markdown(f"<small>{desc}</small>", unsafe_allow_html=True)
        st.markdown("")

with col_right:
    st.markdown("### Quick status")
    if not active_resume:
        st.warning("⚠️ No resume uploaded yet. [Upload your resume →](New_Outreach)")
    else:
        st.success(f"✅ Resume loaded: **{active_resume.filename}**")

    if pending_review > 0:
        st.warning(f"⚠️ **{pending_review} draft(s)** waiting for your approval.")
        if st.button("Review Drafts Now →", type="primary"):
            st.switch_page("pages/3_Review_Drafts.py")
    else:
        st.info("No drafts pending review.")

    st.markdown("---")
    st.markdown("### Contact discovery sources")
    st.markdown("""
| Source | Role |
|--------|------|
| 🔵 Apollo.io | Primary — contact data + company info |
| 🟡 Hunter.io | Fallback — domain-based search + verifier |
| 🟠 Snov.io | Third fallback |
| 🏢 Clearbit | Extra company enrichment *(optional)* |
""")
