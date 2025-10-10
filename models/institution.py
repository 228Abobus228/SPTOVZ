# SPTOVZ/models/institution.py
from sqlalchemy import Column, String
from sqlalchemy.orm import relationship
from SPTOVZ.database import Base


class Institution(Base):
    """
    Учреждение (школа / колледж / вуз).
    К каждому учреждению привязан ровно один пользователь (учитель/админ).
    """
    __tablename__ = "institutions"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)                   # Название учреждения
    education_type = Column(String, nullable=False)          # school | college | university

    # связи
    user = relationship("User", back_populates="institution", uselist=False)
    classes = relationship("Class", back_populates="institution")
