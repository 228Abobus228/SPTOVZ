from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from SPTOVZ.database import Base

class Class(Base):
    __tablename__ = "classes"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)

    teacher_id = Column(String, ForeignKey("users.id"))
    teacher = relationship("User", back_populates="classes")

    institution_id = Column(String, ForeignKey("institutions.id"))
    institution = relationship("Institution", back_populates="classes")

    keys = relationship("Key", back_populates="class_")

    @property
    def education_type(self) -> str | None:
        return self.institution.education_type if self.institution else None


class Key(Base):
    __tablename__ = "keys"

    id = Column(String, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    used = Column(Boolean, default=False)

    class_id = Column(String, ForeignKey("classes.id"))
    class_ = relationship("Class", back_populates="keys")

    education_type = Column(String, nullable=False)   # school | college | university
    form_type = Column(String, nullable=False)         # A | B | C

    sessions = relationship("TestSession", back_populates="key")