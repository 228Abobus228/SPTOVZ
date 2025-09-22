from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Class(Base):
    __tablename__ = "classes"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    psychologist_id = Column(String, ForeignKey("users.id"))

    psychologist = relationship("User", back_populates="classes")
    groups = relationship("Group", back_populates="class_")

class Group(Base):
    __tablename__ = "groups"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    class_id = Column(String, ForeignKey("classes.id"))

    class_ = relationship("Class", back_populates="groups")
    keys = relationship("Key", back_populates="group")

class Key(Base):
    __tablename__ = "keys"

    id = Column(String, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False)
    used = Column(Boolean, default=False)
    group_id = Column(String, ForeignKey("groups.id"))
    class_id = Column(String, ForeignKey("classes.id"))

    group = relationship("Group", back_populates="keys")
