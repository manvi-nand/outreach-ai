from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String, nullable=False)
    raw_text = Column(Text, nullable=False)
    parsed_data = Column(JSON, nullable=True)  # skills, experience, name, target_roles
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    drafts = relationship("EmailDraft", back_populates="resume")


class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    domain = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    industry = Column(String, nullable=True)
    size = Column(String, nullable=True)
    website = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    contacts = relationship("Contact", back_populates="company")


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=True)
    email = Column(String, nullable=False)
    title = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    source = Column(String, nullable=True)   # apollo / hunter / snov / google
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="contacts")
    drafts = relationship("EmailDraft", back_populates="contact")
    outreach = relationship("OutreachRecord", back_populates="contact", uselist=False)


class EmailDraft(Base):
    __tablename__ = "email_drafts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    email_type = Column(String, default="initial")  # initial / followup_1 / followup_2
    status = Column(String, default="pending_review")  # pending_review / approved / sent / rejected
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contact = relationship("Contact", back_populates="drafts")
    resume = relationship("Resume", back_populates="drafts")


class OutreachRecord(Base):
    __tablename__ = "outreach_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(Integer, ForeignKey("contacts.id"), nullable=False, unique=True)
    status = Column(String, default="active")  # active / replied / no_response / closed
    initial_sent_at = Column(DateTime, nullable=True)
    followup_1_due_at = Column(DateTime, nullable=True)
    followup_2_due_at = Column(DateTime, nullable=True)
    followup_1_sent_at = Column(DateTime, nullable=True)
    followup_2_sent_at = Column(DateTime, nullable=True)
    reply_received_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    contact = relationship("Contact", back_populates="outreach")
