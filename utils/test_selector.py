from __future__ import annotations
from enum import Enum
from typing import NamedTuple


# --- Канонические значения (slug-и на латинице) ---
class InstitutionType(str, Enum):
    SCHOOL = "school"          # школа
    KINDERGARTEN = "kindergarten"  # детский сад / дошкольное учреждение
    COLLEGE = "college"        # колледж / техникум


class Impairment(str, Enum):
    HEARING = "hearing"        # нарушение слуха
    VISION = "vision"          # нарушение зрения
    MOTOR = "motor"            # нарушение ОДА


class TestInfo(NamedTuple):
    form_type: str     # условно "A", "B"… или код формы бланка
    test_name: str     # человекочитаемое название теста/набора методик


# --- Матрица выбора теста ---
# Пример: подставь свои реальные коды форм и названия тестов
MATRIX: dict[tuple[InstitutionType, Impairment], TestInfo] = {
    # SCHOOL
    (InstitutionType.SCHOOL, InstitutionType.__members__["SCHOOL"].value and Impairment.HEARING): TestInfo("A", "EAR-SCHOOL"),
    (InstitutionType.SCHOOL, Impairment.VISION):  TestInfo("A", "VISION-SCHOOL"),
    (InstitutionType.SCHOOL, Impairment.MOTOR):   TestInfo("A", "MOTOR-SCHOOL"),

    # COLLEGE
    (InstitutionType.KINDERGARTEN, Impairment.HEARING): TestInfo("B", "EAR-KINDER"),
    (InstitutionType.KINDERGARTEN, Impairment.VISION):  TestInfo("B", "VISION-KINDER"),
    (InstitutionType.KINDERGARTEN, Impairment.MOTOR):   TestInfo("B", "MOTOR-KINDER"),

    # COLLEGE
    (InstitutionType.COLLEGE, Impairment.HEARING): TestInfo("C", "EAR-COLLEGE"),
    (InstitutionType.COLLEGE, Impairment.VISION):  TestInfo("C", "VISION-COLLEGE"),
    (InstitutionType.COLLEGE, Impairment.MOTOR):   TestInfo("C", "MOTOR-COLLEGE"),
}


# --- Основная функция выбора ---
def select_test(institution_type: str | None, impairment: str) -> TestInfo:
    """
    Возвращает (form_type, test_name) по типу учреждения и форме нарушения.
    - institution_type может быть None (если у пользователя не заполнено) — в таком случае кидаем ValueError.
    - impairment обязателен: 'hearing' | 'vision' | 'motor'
    """
    if not institution_type:
        raise ValueError("Тип учреждения не задан для психолога")

    try:
        inst = InstitutionType(institution_type)
    except ValueError as e:
        raise ValueError(f"Неизвестный тип учреждения: {institution_type!r}") from e

    try:
        imp = Impairment(impairment)
    except ValueError as e:
        raise ValueError(f"Неизвестная форма нарушения: {impairment!r}") from e

    info = MATRIX.get((inst, imp))
    if not info:
        # На всякий случай, если матрицу когда-то сократим и выпадет комбинация
        raise ValueError(f"Комбинация не поддерживается: ({inst.value}, {imp.value})")

    return info
