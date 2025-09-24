from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from SPTOVZ.database import Base

class Class(Base):
    __tablename__ = "classes"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    education_type = Column(String, nullable=False)
    psychologist_id = Column(String, ForeignKey("users.id"), nullable=False)
    psychologist = relationship("User", back_populates="classes")

    groups = relationship("Group", back_populates="class_", cascade="all, delete-orphan")

class Group(Base):
    __tablename__ = "groups"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)

    class_id = Column(String, ForeignKey("classes.id"), nullable=False)
    class_ = relationship("Class", back_populates="groups")

    keys = relationship("Key", back_populates="group", cascade="all, delete-orphan")
    # через keys -> sessions

class Key(Base):
    __tablename__ = "keys"
    id = Column(String, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    used = Column(Boolean, default=False, nullable=False)

    group_id = Column(String, ForeignKey("groups.id"), nullable=False)
    group = relationship("Group", back_populates="keys")

    sessions = relationship("TestSession", back_populates="key")
