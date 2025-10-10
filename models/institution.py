from sqlalchemy import Column, String
from SPTOVZ.database import Base

class Institution(Base):
    __tablename__ = "institutions"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    # school | college | university
    education_type = Column(String, nullable=False)
