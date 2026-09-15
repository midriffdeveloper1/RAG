from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.ids import generate_id


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    upload_id: Mapped[str] = mapped_column(
        ForeignKey("business_document_uploads.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    candidate_name: Mapped[str] = mapped_column(String(255), nullable=True)
    email: Mapped[str] = mapped_column(String(255), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    address: Mapped[str] = mapped_column(Text, nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    total_experience_years: Mapped[float] = mapped_column(Float, nullable=True)
    skills: Mapped[list] = mapped_column(JSON, nullable=True)  # list[str]
    certifications: Mapped[list] = mapped_column(JSON, nullable=True)  # list[str]

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    upload = relationship("BusinessDocumentUpload", back_populates="resume")
    education = relationship(
        "ResumeEducation",
        back_populates="resume",
        cascade="all, delete-orphan",
        order_by="ResumeEducation.position",
    )
    experience = relationship(
        "ResumeExperience",
        back_populates="resume",
        cascade="all, delete-orphan",
        order_by="ResumeExperience.position",
    )


class ResumeEducation(Base):
    __tablename__ = "resume_education"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    resume_id: Mapped[str] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)

    institution: Mapped[str] = mapped_column(String(255), nullable=True)
    degree: Mapped[str] = mapped_column(String(255), nullable=True)
    field: Mapped[str] = mapped_column(String(255), nullable=True)
    start_date: Mapped[str] = mapped_column(String(20), nullable=True)
    end_date: Mapped[str] = mapped_column(String(20), nullable=True)

    resume = relationship("Resume", back_populates="education")


class ResumeExperience(Base):
    __tablename__ = "resume_experience"

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default=generate_id)
    resume_id: Mapped[str] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)

    company: Mapped[str] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=True)
    start_date: Mapped[str] = mapped_column(String(20), nullable=True)
    end_date: Mapped[str] = mapped_column(String(20), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)

    resume = relationship("Resume", back_populates="experience")