# SPTOVZ/models/user.py
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.orm import relationship
from SPTOVZ.database import Base


class User(Base):
    """
    Пользователь (учитель / администратор учреждения)
    """
    __tablename__ = "users"

    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    # связь с учреждением
    institution_id = Column(String, ForeignKey("institutions.id"), nullable=True)
    institution = relationship("Institution", back_populates="user")

    # связь с классами, которые создаёт учитель
    classes = relationship("Class", back_populates="teacher")
