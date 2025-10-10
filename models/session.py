from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from SPTOVZ.database import Base
from datetime import datetime

class TestSession(Base):
    __tablename__ = "test_sessions"

    id = Column(String, primary_key=True)
    key_id = Column(String, ForeignKey("keys.id"))
    key = relationship("Key", back_populates="sessions")

    age = Column(Integer, nullable=False)
    gender = Column(String, nullable=False)
    diagnosis = Column(String, nullable=True)
    form_type = Column(String, nullable=False)
    test_name = Column(String, nullable=False)

    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    finished_at = Column(DateTime, nullable=True)

    answers = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
