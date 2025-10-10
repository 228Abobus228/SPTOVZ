from sqlalchemy import Column, String
from SPTOVZ.database import Base
from sqlalchemy.orm import relationship

class Institution(Base):
    __tablename__ = "institutions"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    # school | college | university
    education_type = Column(String, nullable=False)
    users = relationship("User", back_populates="institution")