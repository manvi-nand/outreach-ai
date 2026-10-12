import streamlit as st
from datetime import datetime, timedelta
import os
from database.db import get_session, init_db
from database.models import EmailDraft, Contact, Company, OutreachRecord, Resume
from services import claude_service, gmail_service

st.set_page_config(page_title="Review Drafts — OutreachAI", page_icon="✏️", layout="wide")

init_db()
st.title("✏️ Review Drafts")
st.markdown("Approve, edit, or regenerate email drafts. Nothing sends without your approval.")
st.markdown("---")

db = get_session()

FOLLOWUP_1_DAYS = int(os.getenv("FOLLOWUP_1_DAYS", 5))
FOLLOWUP_2_DAYS = int(os.getenv("FOLLOWUP_2_DAYS", 10))

# ── Gmail auth check ───────────────────────────────────────────────────────────
gmail_connected = gmail_service.is_authenticated()
if not gmail_connected:
    st.warning("⚠️ Gmail not connected. Emails will be saved as 'approved' but not sent. [Connect Gmail →](Settings)")

# ── Filter tabs ────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["⏳ Pending Review", "✅ Approved / Sent", "❌ Rejected"])

def render_draft(draft: EmailDraft, db, gmail_connected: bool, tab_key: str):
    contact = db.query(Contact).filter(Contact.id == draft.contact_id).first()
    company = db.query(Company).filter(Company.id == contact.company_id).first() if contact else None
    resume = db.query(Resume).filter(Resume.id == draft.resume_id).first()

    with st.container():
        st.markdown(f"""
<div style="background:#1e1e2e; border-radius:12px; padding:20px; border:1px solid #313244; margin-bottom:16px;">
""", unsafe_allow_html=True)

        # Header
        col_info, col_type = st.columns([3, 1])
        with col_info:
            name_display = contact.name or contact.email if contact else "Unknown"
            st.markdown(f"**To:** {name_display} `{contact.email if contact else '—'}`")
            title_display = contact.title or "—" if contact else "—"
            company_display = company.name if company else "—"
            st.markdown(f"<small>📋 {title_display} @ {company_display}</small>", unsafe_allow_html=True)
        with col_type:
            type_labels = {
                "initial": "🟦 Initial",
                "followup_1": "🟧 Follow-up 1",
                "followup_2": "🟥 Follow-up 2",
            }
            st.markdown(type_labels.get(draft.email_type, draft.email_type))
            st.markdown(f"<small>Created {draft.created_at.strftime('%b %d, %Y')}</small>", unsafe_allow_html=True)

        st.markdown("---")

        # Editable subject and body
        subject_key = f"subject_{draft.id}_{tab_key}"
        body_key = f"body_{draft.id}_{tab_key}"

        new_subject = st.text_input("Subject", value=draft.subject, key=subject_key)
        new_body = st.text_area("Email Body", value=draft.body, height=250, key=body_key)

        # Action buttons
        if draft.status == "pending_review":
            btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([1.5, 1.5, 1.5, 2])

            with btn_col1:
                if st.button("✅ Approve & Send", key=f"approve_{draft.id}", type="primary"):
                    draft.subject = new_subject
                    draft.body = new_body
                    draft.status = "approved"
                    db.commit()

                    if gmail_connected:
                        success = gmail_service.send_email(contact.email, new_subject, new_body)
                        if success:
                            draft.status = "sent"
                            draft.sent_at = datetime.utcnow()
                            db.commit()

                            # Create or update outreach record
                            record = db.query(OutreachRecord).filter(
                                OutreachRecord.contact_id == contact.id
                            ).first()
                            if not record:
                                record = OutreachRecord(
                                    contact_id=contact.id,
                                    status="active",
                                    initial_sent_at=datetime.utcnow(),
                                    followup_1_due_at=datetime.utcnow() + timedelta(days=FOLLOWUP_1_DAYS),
                                    followup_2_due_at=datetime.utcnow() + timedelta(days=FOLLOWUP_2_DAYS),
                                )
                                db.add(record)
                            elif draft.email_type == "followup_1":
                                record.followup_1_sent_at = datetime.utcnow()
                            elif draft.email_type == "followup_2":
                                record.followup_2_sent_at = datetime.utcnow()
                            db.commit()

                            st.success(f"Email sent to {contact.email}!")
                        else:
                            st.error("Failed to send. Check Gmail connection in Settings.")
                    else:
                        st.info("Gmail not connected. Draft saved as approved. Connect Gmail in Settings to send.")
                    st.rerun()

            with btn_col2:
                if st.button("💾 Save Edits", key=f"save_{draft.id}"):
                    draft.subject = new_subject
                    draft.body = new_body
                    db.commit()
                    st.success("Edits saved.")
                    st.rerun()

            with btn_col3:
                if st.button("🔄 Regenerate", key=f"regen_{draft.id}"):
                    resume_data = resume.parsed_data if resume else {}
                    company_info = {"name": company.name if company else "", "description": company.description if company else "", "industry": company.industry if company else ""}
                    contact_info = {"name": contact.name, "email": contact.email, "title": contact.title} if contact else {}

                    with st.spinner("Regenerating with Claude..."):
                        if draft.email_type == "initial":
                            new_draft = claude_service.draft_initial_email(resume_data, company_info, contact_info)
                        else:
                            followup_num = 1 if draft.email_type == "followup_1" else 2
                            new_draft = claude_service.draft_followup_email(resume_data, company_info, contact_info, followup_num, draft.subject)

                    draft.subject = new_draft["subject"]
                    draft.body = new_draft["body"]
                    db.commit()
                    st.success("Regenerated successfully!")
                    st.rerun()

            with btn_col4:
                if st.button("❌ Reject Draft", key=f"reject_{draft.id}"):
                    draft.status = "rejected"
                    db.commit()
                    st.rerun()

        elif draft.status in ("approved", "sent"):
            sent_time = draft.sent_at.strftime("%b %d, %Y at %I:%M %p") if draft.sent_at else "Approved, not sent"
            if draft.status == "sent":
                st.success(f"✅ Sent on {sent_time}")
            else:
                st.info("Approved — connect Gmail to send.")

        elif draft.status == "rejected":
            if st.button("↩️ Restore to Pending", key=f"restore_{draft.id}"):
                draft.status = "pending_review"
                db.commit()
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("")


# ── Tab 1: Pending Review ──────────────────────────────────────────────────────
with tab1:
    pending = db.query(EmailDraft).filter(EmailDraft.status == "pending_review").order_by(EmailDraft.created_at.desc()).all()
    if not pending:
        st.info("No drafts pending review. Start a new outreach to generate drafts.")
    else:
        st.markdown(f"**{len(pending)} draft(s) awaiting your review**")
        for draft in pending:
            render_draft(draft, db, gmail_connected, "pending")

# ── Tab 2: Approved / Sent ─────────────────────────────────────────────────────
with tab2:
    sent_approved = db.query(EmailDraft).filter(
        EmailDraft.status.in_(["approved", "sent"])
    ).order_by(EmailDraft.sent_at.desc()).all()

    if not sent_approved:
        st.info("No sent or approved emails yet.")
    else:
        st.markdown(f"**{len(sent_approved)} email(s) sent or approved**")
        for draft in sent_approved:
            render_draft(draft, db, gmail_connected, "sent")

# ── Tab 3: Rejected ────────────────────────────────────────────────────────────
with tab3:
    rejected = db.query(EmailDraft).filter(EmailDraft.status == "rejected").order_by(EmailDraft.created_at.desc()).all()
    if not rejected:
        st.info("No rejected drafts.")
    else:
        st.markdown(f"**{len(rejected)} rejected draft(s)**")
        for draft in rejected:
            render_draft(draft, db, gmail_connected, "rejected")

db.close()
