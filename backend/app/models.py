from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    original_filename = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    quality_score = Column(Float, nullable=False)
    quality_label = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    issues = relationship("Issue", back_populates="analysis", cascade="all, delete-orphan")
    statistics = relationship("ImageStatistics", back_populates="analysis", uselist=False, cascade="all, delete-orphan")


class Issue(Base):
    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False)
    type = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    explanation = Column(String, nullable=False)

    analysis = relationship("Analysis", back_populates="issues")


class ImageStatistics(Base):
    __tablename__ = "image_statistics"

    id = Column(Integer, primary_key=True, index=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False)
    sharpness = Column(Float, nullable=False)
    brightness = Column(Float, nullable=False)
    contrast = Column(Float, nullable=False)
    noise = Column(Float, nullable=False)
    dark_pixel_ratio = Column(Float, nullable=False)
    bright_pixel_ratio = Column(Float, nullable=False)
    saturation_ratio = Column(Float, nullable=False)
    edge_density = Column(Float, nullable=False)

    analysis = relationship("Analysis", back_populates="statistics")
