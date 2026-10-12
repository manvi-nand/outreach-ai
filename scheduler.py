"""
Follow-up scheduler — run this as a separate process:
    python scheduler.py

Checks every hour for outreach records due for follow-ups,
drafts follow-up emails via Claude, and queues them for human approval.
"""
import time
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

from database.db import init_db, get_session
from database.models import OutreachRecord, EmailDraft, Contact, Company, Resume
from services import claude_service, gmail_service

FOLLOWUP_1_DAYS = int(os.getenv("FOLLOWUP_1_DAYS", 5))
FOLLOWUP_2_DAYS = int(os.getenv("FOLLOWUP_2_DAYS", 10))
CHECK_INTERVAL_SECONDS = 3600  # run every hour


def run_scheduler():
    init_db()
    print(f"[Scheduler] Started. Checking every {CHECK_INTERVAL_SECONDS // 60} minutes.")
    while True:
        try:
            process_followups()
            check_for_replies()
        except Exception as e:
            print(f"[Scheduler] Error: {e}")
        time.sleep(CHECK_INTERVAL_SECONDS)


def process_followups():
    db = get_session()
    now = datetime.utcnow()

    try:
        active_records = db.query(OutreachRecord).filter(OutreachRecord.status == "active").all()
        print(f"[Scheduler] Checking {len(active_records)} active outreach records...")

        for record in active_records:
            contact = db.query(Contact).filter(Contact.id == record.contact_id).first()
            if not contact:
                continue

            company = db.query(Company).filter(Company.id == contact.company_id).first()
            resume = db.query(Resume).filter(Resume.is_active == True).first()

            if not contact or not company or not resume:
                continue

            company_info = {
                "name": company.name,
                "description": company.description,
                "industry": company.industry,
            }
            contact_info = {
                "name": contact.name,
                "email": contact.email,
                "title": contact.title,
            }
            resume_data = resume.parsed_data or {}

            # Fetch original sent email for subject reference
            original_draft = (
                db.query(EmailDraft)
                .filter(EmailDraft.contact_id == contact.id, EmailDraft.email_type == "initial")
                .first()
            )
            original_subject = original_draft.subject if original_draft else "our previous conversation"

            # ── Follow-up 1 ──────────────────────────────────────────────
            if (
                record.followup_1_due_at
                and now >= record.followup_1_due_at
                and not record.followup_1_sent_at
            ):
                existing = db.query(EmailDraft).filter(
                    EmailDraft.contact_id == contact.id,
                    EmailDraft.email_type == "followup_1",
                ).first()
                if not existing:
                    print(f"[Scheduler] Drafting follow-up 1 for {contact.email}")
                    draft_content = claude_service.draft_followup_email(
                        resume_data, company_info, contact_info, 1, original_subject
                    )
                    draft = EmailDraft(
                        contact_id=contact.id,
                        resume_id=resume.id,
                        subject=draft_content["subject"],
                        body=draft_content["body"],
                        email_type="followup_1",
                        status="pending_review",
                    )
                    db.add(draft)
                    db.commit()
                    print(f"[Scheduler] Follow-up 1 queued for approval: {contact.email}")

            # ── Follow-up 2 ──────────────────────────────────────────────
            if (
                record.followup_2_due_at
                and now >= record.followup_2_due_at
                and not record.followup_2_sent_at
                and record.followup_1_sent_at  # only if f/u 1 was sent
            ):
                existing = db.query(EmailDraft).filter(
                    EmailDraft.contact_id == contact.id,
                    EmailDraft.email_type == "followup_2",
                ).first()
                if not existing:
                    print(f"[Scheduler] Drafting follow-up 2 for {contact.email}")
                    draft_content = claude_service.draft_followup_email(
                        resume_data, company_info, contact_info, 2, original_subject
                    )
                    draft = EmailDraft(
                        contact_id=contact.id,
                        resume_id=resume.id,
                        subject=draft_content["subject"],
                        body=draft_content["body"],
                        email_type="followup_2",
                        status="pending_review",
                    )
                    db.add(draft)
                    db.commit()
                    print(f"[Scheduler] Follow-up 2 queued for approval: {contact.email}")

    finally:
        db.close()


def check_for_replies():
    """Check Gmail for replies and update record status."""
    if not gmail_service.is_authenticated():
        return

    db = get_session()
    try:
        active_records = db.query(OutreachRecord).filter(OutreachRecord.status == "active").all()
        for record in active_records:
            contact = db.query(Contact).filter(Contact.id == record.contact_id).first()
            if not contact:
                continue

            original_draft = (
                db.query(EmailDraft)
                .filter(EmailDraft.contact_id == contact.id, EmailDraft.email_type == "initial")
                .first()
            )
            if not original_draft:
                continue

            has_reply = gmail_service.check_for_reply(original_draft.subject, contact.email)
            if has_reply:
                record.status = "replied"
                record.reply_received_at = datetime.utcnow()
                db.commit()
                print(f"[Scheduler] Reply detected from {contact.email} — marked as replied")

    finally:
        db.close()


if __name__ == "__main__":
    run_scheduler()
