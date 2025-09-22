from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class TestSession(Base):
    __tablename__ = "test_sessions"

    id = Column(String, primary_key=True, index=True)
    key_id = Column(String, ForeignKey("keys.id"))

    age = Column(Integer)
    gender = Column(String)
    diagnosis = Column(String)
    form_type = Column(String)
    test_name = Column(String)
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    answers = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
