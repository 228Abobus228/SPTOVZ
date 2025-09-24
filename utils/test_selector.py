# SPTOVZ/utils/test_selector.py
from __future__ import annotations

from typing import Tuple
from sqlalchemy.orm import Session

from SPTOVZ.models.testbank import TestPassport, TestContent


ALLOWED_INSTITUTIONS = {"school", "college", "university"}
ALLOWED_IMPAIRMENTS = {"hearing", "vision", "motor"}


def _norm(s: str) -> str:
    return (s or "").strip().lower()


def select_test(
    db: Session,
    institution: str,
    impairment: str,
) -> Tuple[TestPassport, TestContent]:
    """
    Возвращает (passport, content) для теста по паре (institution, impairment).
    Пол НЕ участвует в выборе (используется позже при обработке результатов).

    Правила выбора:
      1) фильтр по institution & impairment;
      2) среди найденных берём максимальную version;
      3) если есть несколько с той же version, отдаём запись с gender == "any"
         (для совместимости со старыми данными), иначе первую попавшуюся.

    Исключения:
      ValueError — если тест не найден или нет контента.
    """
    inst = _norm(institution)
    imp = _norm(impairment)

    if inst not in ALLOWED_INSTITUTIONS:
        raise ValueError(f"institution должен быть одним из {sorted(ALLOWED_INSTITUTIONS)}")
    if imp not in ALLOWED_IMPAIRMENTS:
        raise ValueError(f"impairment должен быть одним из {sorted(ALLOWED_IMPAIRMENTS)}")

    # Все кандидаты по паре (institution, impairment)
    candidates = (
        db.query(TestPassport)
        .filter(
            TestPassport.institution == inst,
            TestPassport.impairment == imp,
        )
        .order_by(TestPassport.version.desc())
        .all()
    )

    if not candidates:
        raise ValueError(f"Тест не найден для ({inst}, {imp})")

    # Лучшая версия
    best_version = candidates[0].version
    same_version = [p for p in candidates if p.version == best_version]

    # Предпочтительно gender == "any" (если есть), иначе берём первую
    passport = next((p for p in same_version if (p.gender or "").lower() == "any"), same_version[0])

    content = db.get(TestContent, passport.id)
    if not content:
        raise ValueError(f"Контент теста '{passport.id}' не найден")

    return passport, content
