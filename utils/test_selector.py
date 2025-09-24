from __future__ import annotations
from enum import Enum
from typing import NamedTuple


class InstitutionType(str, Enum):
    SCHOOL = "school"
    COLLEGE = "college"
    UNIVERSITY = "university"


class Impairment(str, Enum):
    HEARING = "hearing"
    VISION = "vision"
    MOTOR = "motor"


class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"


class TestPick(NamedTuple):
    code: str    # уникальный код (например, SCH_HEAR_M_V1)
    title: str   # человекочитаемое название (можно подтянуть из паспорта)


# Хелпер для генерации кодов по конвенции:
#  SCH|COL|UNI  +  HEAR|VIS|MOT  +  M|F  +  _V1
def _code(inst: InstitutionType, imp: Impairment, gen: Gender, version: int = 1) -> str:
    inst_map = {
        InstitutionType.SCHOOL: "SCH",
        InstitutionType.COLLEGE: "COL",
        InstitutionType.UNIVERSITY: "UNI",
    }
    imp_map = {
        Impairment.HEARING: "HEAR",
        Impairment.VISION: "VIS",
        Impairment.MOTOR: "MOT",
    }
    gen_map = {
        Gender.MALE: "M",
        Gender.FEMALE: "F",
    }
    return f"{inst_map[inst]}_{imp_map[imp]}_{gen_map[gen]}_V{version}"


# Матрица 3×3×2 → код теста (версию можно потом менять централизованно)
DEFAULT_VERSION = 1
MATRIX: dict[tuple[InstitutionType, Impairment, Gender], str] = {
    (i, p, g): _code(i, p, g, DEFAULT_VERSION)
    for i in InstitutionType
    for p in Impairment
    for g in Gender
}


def select_test_code(institution_type: str, impairment: str, gender: str) -> str:
    try:
        inst = InstitutionType(institution_type)
    except ValueError as e:
        raise ValueError(f"Неизвестный тип учреждения: {institution_type!r}") from e
    try:
        imp = Impairment(impairment)
    except ValueError as e:
        raise ValueError(f"Неизвестная форма нарушения: {impairment!r}") from e
    try:
        gen = Gender(gender)
    except ValueError as e:
        raise ValueError(f"Неизвестный пол: {gender!r}") from e

    code = MATRIX.get((inst, imp, gen))
    if not code:
        raise ValueError(f"Комбинация не поддерживается: ({inst.value}, {imp.value}, {gen.value})")
    return code
