import streamlit as st
import os
from datetime import datetime, timedelta
from database.db import get_session, init_db
from database.models import Resume, Company, Contact, EmailDraft, OutreachRecord
from services import claude_service, contact_finder

st.set_page_config(page_title="New Outreach — OutreachAI", page_icon="🚀", layout="wide")

init_db()
st.title("🚀 New Outreach")
st.markdown("Add a company and let AI find contacts and draft personalized emails.")
st.markdown("---")

db = get_session()

# ── Step 1: Resume ─────────────────────────────────────────────────────────────
st.markdown("### Step 1 — Your Resume")
active_resume = db.query(Resume).filter(Resume.is_active == True).first()

if active_resume:
    col1, col2 = st.columns([3, 1])
    with col1:
        st.success(f"✅ Resume loaded: **{active_resume.filename}**")
        parsed = active_resume.parsed_data or {}
        if parsed:
            with st.expander("View parsed resume data"):
                st.markdown(f"**Name:** {parsed.get('name', '—')}")
                st.markdown(f"**Skills:** {', '.join(parsed.get('skills', []))}")
                roles = ', '.join(parsed.get('target_roles', []))
                st.markdown(f"**Target Roles:** {roles or '—'}")
    with col2:
        if st.button("Upload New Resume"):
            db.query(Resume).update({"is_active": False})
            db.commit()
            active_resume = None
            st.rerun()

if not active_resume:
    uploaded = st.file_uploader("Upload your resume (PDF)", type=["pdf"])
    if uploaded:
        os.makedirs("uploads", exist_ok=True)
        save_path = f"uploads/{uploaded.name}"
        with open(save_path, "wb") as f:
            f.write(uploaded.getbuffer())

        with st.spinner("Parsing resume with Claude AI..."):
            raw_text = claude_service.extract_text_from_pdf(save_path)
            parsed_data = claude_service.parse_resume(raw_text)

        db.query(Resume).update({"is_active": False})
        resume = Resume(
            filename=uploaded.name,
            raw_text=raw_text,
            parsed_data=parsed_data,
            is_active=True,
        )
        db.add(resume)
        db.commit()
        db.refresh(resume)
        active_resume = resume

        st.success("Resume parsed successfully!")
        st.json(parsed_data)
        st.rerun()

if not active_resume:
    st.warning("Please upload your resume to continue.")
    db.close()
    st.stop()

st.markdown("---")

# ── Step 2: Company research ───────────────────────────────────────────────────
st.markdown("### Step 2 — Research a Company")

col_name, col_domain = st.columns([2, 1])
with col_name:
    company_name = st.text_input(
        "Company name",
        placeholder="e.g. CultFit, Stripe, OpenAI",
        help="Partial names work fine — e.g. 'Cult' will find CultFit.",
    )
with col_domain:
    manual_domain = st.text_input(
        "🌐 Domain *(optional override)*",
        placeholder="e.g. cult.fit, ibm.com",
        help="If contacts aren't found, enter the company's exact website domain here.",
    )

col_loc, col_role = st.columns(2)

with col_loc:
    location_filter = st.text_input(
        "📍 Location filter *(optional)*",
        placeholder="e.g. United States, San Francisco, London",
        help="Only show contacts based in this location. Leave blank to see all locations.",
    )

with col_role:
    role_options = {
        "Recruiter / Talent Acquisition": ["recruiter", "talent acquisition", "talent"],
        "HR / People Ops": ["hr", "human resources", "people operations", "people ops"],
        "Hiring Manager": ["hiring manager"],
        "Engineering Manager / Lead": ["engineering manager", "engineering lead", "tech lead", "head of engineering"],
        "VP / Director of Engineering": ["vp of engineering", "director of engineering", "vp engineering"],
    }
    selected_roles = st.multiselect(
        "🎯 Target role types",
        options=list(role_options.keys()),
        default=["Recruiter / Talent Acquisition", "HR / People Ops", "Hiring Manager"],
        help="Select predefined role types and/or type your own below.",
    )
    custom_roles = st.text_input(
        "✏️ Add custom roles *(optional)*",
        placeholder="e.g. product manager, data lead, CTO",
        help="Comma-separated. Combined with the role types above. Leave both empty to show all contacts.",
    )

# Build flat keyword list from selected roles + custom typed roles
role_keywords = []
for role in selected_roles:
    role_keywords.extend(role_options[role])
if custom_roles:
    for r in custom_roles.split(","):
        r = r.strip().lower()
        if r:
            role_keywords.append(r)

if company_name and st.button("🔍 Research Company", type="primary"):
    with st.spinner(f"Researching {company_name}... fetching company info and contacts..."):
        company_info, contacts = contact_finder.find_company_and_contacts(
            company_name,
            location=location_filter.strip() if location_filter else None,
            role_filter=role_keywords if role_keywords else None,
            manual_domain=manual_domain.strip() if manual_domain else None,
        )

    # Save or update company
    existing_company = db.query(Company).filter(Company.name.ilike(company_name)).first()
    if existing_company:
        company = existing_company
    else:
        company = Company(
            name=company_info.get("name", company_name),
            domain=company_info.get("domain", ""),
            description=company_info.get("description", ""),
            industry=company_info.get("industry", ""),
            size=str(company_info.get("size", "")),
            website=company_info.get("website", ""),
            linkedin_url=company_info.get("linkedin_url", ""),
        )
        db.add(company)
        db.commit()
        db.refresh(company)

    st.session_state["researched_company"] = company.id
    st.session_state["researched_contacts"] = contacts
    st.session_state["company_info_display"] = company_info

if "researched_company" in st.session_state:
    company = db.query(Company).filter(Company.id == st.session_state["researched_company"]).first()
    contacts_raw = st.session_state.get("researched_contacts", [])
    company_info = st.session_state.get("company_info_display", {})

    # Company info card
    st.markdown("---")
    st.markdown("#### Company Info")
    info_col1, info_col2 = st.columns(2)
    with info_col1:
        st.markdown(f"**{company.name}**")
        st.markdown(f"🏭 {company.industry or '—'}  |  👥 {company.size or '—'} employees")
        domain_display = company.domain or company_info.get("domain", "")
        if domain_display:
            st.markdown(f"🌐 Domain: `{domain_display}`")
        if company.website:
            st.markdown(f"🔗 [{company.website}]({company.website})")
        if not domain_display:
            st.caption("⚠️ Domain not detected — enter it manually above if no contacts are found.")
    with info_col2:
        if company.description:
            st.markdown(company.description)

    st.markdown("---")
    st.markdown(f"#### Contacts Found ({len(contacts_raw)})")

    if not contacts_raw:
        st.warning("No contacts found. Try adding API keys for Apollo, Hunter, or Snov in Settings.")
    else:
        # Display contacts with checkboxes
        st.markdown("Select which contacts to reach out to:")
        selected_contacts = []

        # Column headers
        h1, h2, h3, h4, h5, h6, h7 = st.columns([0.5, 2, 2.5, 2, 1.5, 1, 0.7])
        h1.markdown("**✓**")
        h2.markdown("**Name**")
        h3.markdown("**Email**")
        h4.markdown("**Title**")
        h5.markdown("**Location**")
        h6.markdown("**Source**")
        h7.markdown("**Valid**")
        st.markdown("---")

        for i, contact in enumerate(contacts_raw):
            col_check, col_name, col_email, col_title, col_loc, col_source, col_verified = st.columns([0.5, 2, 2.5, 2, 1.5, 1, 0.7])
            with col_check:
                checked = st.checkbox("Select", key=f"contact_{i}", value=True, label_visibility="hidden")
            with col_name:
                st.markdown(contact.get("name") or "—")
            with col_email:
                st.markdown(f"`{contact.get('email', '—')}`")
            with col_title:
                st.markdown(contact.get("title") or "—")
            with col_loc:
                st.markdown(contact.get("location") or "—")
            with col_source:
                source_colors = {"apollo": "🔵", "hunter": "🟡", "snov": "🟠", "google": "🔴"}
                st.markdown(source_colors.get(contact.get("source", ""), "⚪") + " " + contact.get("source", "—"))
            with col_verified:
                st.markdown("✅" if contact.get("is_verified") else "⚠️")
            if checked:
                selected_contacts.append(contact)

        st.markdown("---")

        # ── Step 3: Draft emails ───────────────────────────────────────────────
        st.markdown("### Step 3 — Draft Personalized Emails")
        st.markdown(f"Claude will write personalized emails for **{len(selected_contacts)}** selected contact(s).")

        FOLLOWUP_1_DAYS = int(os.getenv("FOLLOWUP_1_DAYS", 5))
        FOLLOWUP_2_DAYS = int(os.getenv("FOLLOWUP_2_DAYS", 10))

        if selected_contacts and st.button("✨ Draft Emails with Claude", type="primary"):
            resume_data = active_resume.parsed_data or {}
            company_info_dict = {
                "name": company.name,
                "description": company.description,
                "industry": company.industry,
            }

            draft_count = 0
            skipped = 0

            progress = st.progress(0)
            status_text = st.empty()

            for idx, contact_data in enumerate(selected_contacts):
                progress.progress((idx + 1) / len(selected_contacts))
                status_text.text(f"Drafting email for {contact_data.get('email')}...")

                # Check if contact already exists
                existing_contact = db.query(Contact).filter(Contact.email == contact_data["email"]).first()
                if existing_contact:
                    # Check if already has a pending/sent draft
                    existing_draft = db.query(EmailDraft).filter(
                        EmailDraft.contact_id == existing_contact.id,
                        EmailDraft.email_type == "initial",
                    ).first()
                    if existing_draft:
                        skipped += 1
                        continue
                    contact = existing_contact
                else:
                    contact = Contact(
                        company_id=company.id,
                        name=contact_data.get("name", ""),
                        email=contact_data["email"],
                        title=contact_data.get("title", ""),
                        linkedin_url=contact_data.get("linkedin_url", ""),
                        source=contact_data.get("source", ""),
                        is_verified=contact_data.get("is_verified", False),
                    )
                    db.add(contact)
                    db.commit()
                    db.refresh(contact)

                # Draft email with Claude
                draft_content = claude_service.draft_initial_email(resume_data, company_info_dict, contact_data)

                draft = EmailDraft(
                    contact_id=contact.id,
                    resume_id=active_resume.id,
                    subject=draft_content["subject"],
                    body=draft_content["body"],
                    email_type="initial",
                    status="pending_review",
                )
                db.add(draft)
                db.commit()
                draft_count += 1

            progress.empty()
            status_text.empty()

            if draft_count > 0:
                st.success(f"✅ {draft_count} email draft(s) created and waiting for your review!")
                if skipped > 0:
                    st.info(f"{skipped} contact(s) skipped — already have drafts.")
                if st.button("Go to Review Drafts →", type="primary"):
                    st.switch_page("pages/3_Review_Drafts.py")
            else:
                st.warning("No new drafts created. All selected contacts already have drafts.")

db.close()
