from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    education_type = Column(String, nullable=True)

    classes = relationship("Class", back_populates="psychologist")
