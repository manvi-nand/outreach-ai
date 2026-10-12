import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from database.db import get_session
from database.models import OutreachRecord, EmailDraft, Contact, Company

st.set_page_config(page_title="Dashboard — OutreachAI", page_icon="📊", layout="wide")

st.title("📊 Dashboard")
st.markdown("Track all your outreach activity in one place.")
st.markdown("---")

db = get_session()

# ── Fetch all data ─────────────────────────────────────────────────────────────
records = db.query(OutreachRecord).all()
all_drafts = db.query(EmailDraft).all()
all_contacts = db.query(Contact).all()
all_companies = db.query(Company).all()

# ── Top metrics ────────────────────────────────────────────────────────────────
sent_drafts = [d for d in all_drafts if d.status == "sent"]
pending_drafts = [d for d in all_drafts if d.status == "pending_review"]
replied_records = [r for r in records if r.status == "replied"]
no_response = [r for r in records if r.status == "no_response"]

reply_rate = round(len(replied_records) / len(sent_drafts) * 100, 1) if sent_drafts else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Companies", len(all_companies))
col2.metric("Emails Sent", len(sent_drafts))
col3.metric("Replies", len(replied_records))
col4.metric("Reply Rate", f"{reply_rate}%")
col5.metric("Pending Approval", len(pending_drafts))

st.markdown("---")

# ── Charts ─────────────────────────────────────────────────────────────────────
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.markdown("#### Outreach Status Breakdown")
    status_counts = {"Active": 0, "Replied": 0, "No Response": 0, "Closed": 0}
    for r in records:
        label = r.status.replace("_", " ").title()
        if label in status_counts:
            status_counts[label] += 1
        else:
            status_counts[label] = 1

    if any(status_counts.values()):
        fig = px.pie(
            values=list(status_counts.values()),
            names=list(status_counts.keys()),
            color_discrete_sequence=["#60a5fa", "#4ade80", "#f87171", "#a78bfa"],
            hole=0.4,
        )
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            showlegend=True,
            margin=dict(t=10, b=10, l=10, r=10),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No outreach data yet. Start your first campaign!")

with chart_col2:
    st.markdown("#### Email Types Sent")
    type_counts = {"Initial": 0, "Follow-up 1": 0, "Follow-up 2": 0}
    for d in sent_drafts:
        if d.email_type == "initial":
            type_counts["Initial"] += 1
        elif d.email_type == "followup_1":
            type_counts["Follow-up 1"] += 1
        elif d.email_type == "followup_2":
            type_counts["Follow-up 2"] += 1

    if any(type_counts.values()):
        fig2 = px.bar(
            x=list(type_counts.keys()),
            y=list(type_counts.values()),
            color=list(type_counts.keys()),
            color_discrete_sequence=["#60a5fa", "#fb923c", "#f87171"],
        )
        fig2.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font_color="white",
            showlegend=False,
            margin=dict(t=10, b=10, l=10, r=10),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=False, tickformat="d"),
        )
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No sent emails yet.")

st.markdown("---")

# ── Outreach table ─────────────────────────────────────────────────────────────
st.markdown("#### All Outreach Activity")

if not records:
    st.info("No outreach records yet. Go to **New Outreach** to get started!")
else:
    rows = []
    for record in records:
        contact = db.query(Contact).filter(Contact.id == record.contact_id).first()
        company = db.query(Company).filter(Company.id == contact.company_id).first() if contact else None

        initial_draft = db.query(EmailDraft).filter(
            EmailDraft.contact_id == record.contact_id,
            EmailDraft.email_type == "initial",
        ).first()

        rows.append({
            "Company": company.name if company else "—",
            "Contact": contact.name or contact.email if contact else "—",
            "Email": contact.email if contact else "—",
            "Title": contact.title or "—" if contact else "—",
            "Status": record.status.replace("_", " ").title(),
            "Initial Sent": record.initial_sent_at.strftime("%b %d, %Y") if record.initial_sent_at else "Not sent",
            "F/U 1": "Sent" if record.followup_1_sent_at else ("Due " + record.followup_1_due_at.strftime("%b %d") if record.followup_1_due_at else "—"),
            "F/U 2": "Sent" if record.followup_2_sent_at else ("Due " + record.followup_2_due_at.strftime("%b %d") if record.followup_2_due_at else "—"),
            "Reply": "✅ Yes" if record.reply_received_at else "—",
        })

    df = pd.DataFrame(rows)

    # Status filter
    status_filter = st.multiselect(
        "Filter by status",
        options=["Active", "Replied", "No Response", "Closed"],
        default=["Active", "Replied", "No Response", "Closed"],
    )
    if status_filter:
        df = df[df["Status"].isin(status_filter)]

    st.dataframe(df, use_container_width=True, hide_index=True)

    # Mark reply manually
    st.markdown("---")
    st.markdown("#### Mark a reply received")
    st.markdown("<small>If someone replied outside Gmail or you want to manually update status.</small>", unsafe_allow_html=True)

    contact_emails = [r["Email"] for r in rows if r["Status"] == "Active"]
    if contact_emails:
        selected_email = st.selectbox("Select contact email", contact_emails)
        if st.button("Mark as Replied"):
            contact = db.query(Contact).filter(Contact.email == selected_email).first()
            if contact and contact.outreach:
                contact.outreach.status = "replied"
                contact.outreach.reply_received_at = datetime.utcnow()
                db.commit()
                st.success(f"Marked {selected_email} as replied.")
                st.rerun()
    else:
        st.info("No active outreach to update.")

db.close()
