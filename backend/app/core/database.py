from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, Text
from datetime import datetime
from .config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class AnalysisResult(Base):
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    quality_score = Column(Float, nullable=False)
    quality_label = Column(String(50), nullable=False)
    issues = Column(JSON, nullable=False)
    statistics = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "quality_score": self.quality_score,
            "quality_label": self.quality_label,
            "issues": self.issues,
            "statistics": self.statistics,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db():
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()