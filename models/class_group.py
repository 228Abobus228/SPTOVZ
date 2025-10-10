from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from SPTOVZ.database import Base

class Class(Base):
    __tablename__ = "classes"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)

    teacher_id = Column(String, ForeignKey("users.id"), nullable=False)
    teacher = relationship("User", back_populates="classes")

    institution_id = Column(String, ForeignKey("institutions.id"), nullable=False)
    institution = relationship("Institution")

    keys = relationship("Key", back_populates="class_", cascade="all, delete-orphan")

    @property
    def education_type(self) -> str | None:
        return self.institution.education_type if self.institution else None


class Key(Base):
    __tablename__ = "keys"

    id = Column(String, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    used = Column(Boolean, default=False, nullable=False)

    class_id = Column(String, ForeignKey("classes.id"), nullable=False)
    class_ = relationship("Class", back_populates="keys")

    # «замораживаем» параметры в момент генерации, чтобы потом старт по коду
    education_type = Column(String, nullable=False)  # school|college|university
    form_type = Column(String, nullable=False)       # A|B|C
