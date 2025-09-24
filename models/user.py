from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from SPTOVZ.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    education_type = Column(String, nullable=True)  # школа/детсад/колледж и т.п.

    classes = relationship("Class", back_populates="psychologist", cascade="all, delete-orphan")
