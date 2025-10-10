from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from SPTOVZ.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)

    # 1:1 — у учреждения один учитель
    institution_id = Column(String, ForeignKey("institutions.id"), unique=True, nullable=False)
    institution = relationship("Institution", backref="teacher", uselist=False)

    classes = relationship("Class", back_populates="teacher", cascade="all, delete-orphan")
