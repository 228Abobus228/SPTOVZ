from sqlalchemy import Column, String, Integer, JSON, UniqueConstraint
from SPTOVZ.database import Base

class TestPassport(Base):
    __tablename__ = "test_passports"

    # Уникальный код теста = primary key (например, SCH_HEAR_M_V1)
    id = Column(String, primary_key=True, index=True)

    # Критерии выбора
    institution = Column(String, nullable=False, index=True)  # school | college | university
    impairment  = Column(String, nullable=False, index=True)  # hearing | vision | motor
    gender      = Column(String, nullable=False, index=True)  # male | female

    # Метаданные
    version = Column(Integer, nullable=False)
    title   = Column(String,  nullable=False)
    locale  = Column(String,  nullable=False, default="ru")

    __table_args__ = (
        UniqueConstraint("institution", "impairment", "gender", "version", name="uq_test_quad"),
    )


class TestContent(Base):
    __tablename__ = "test_contents"

    # Совпадает с TestPassport.id
    id = Column(String, primary_key=True)

    # Сырые данные теста из YAML
    questions = Column(JSON, nullable=False)
    scoring   = Column(JSON, nullable=True)
