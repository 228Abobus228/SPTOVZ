# SPTOVZ/utils/test_selector.py
from enum import Enum

class InstitutionType(str, Enum):
    SCHOOL = "school"
    COLLEGE = "college"      # техникум/колледж
    UNIVERSITY = "university"

class Impairment(str, Enum):
    HEARING = "hearing"
    VISION = "vision"
    MOTOR = "motor"

class Gender(str, Enum):
    MALE = "male"
    FEMALE = "female"

# ЯВНАЯ матрица 3×3×2 → код теста (должен совпадать с meta.code в YAML)
MATRIX: dict[tuple[InstitutionType, Impairment, Gender], str] = {
    # SCHOOL
    (InstitutionType.SCHOOL, Impairment.HEARING, Gender.MALE):   "SCH_HEAR_M_V1",
    (InstitutionType.SCHOOL, Impairment.HEARING, Gender.FEMALE): "SCH_HEAR_F_V1",
    (InstitutionType.SCHOOL, Impairment.VISION,  Gender.MALE):   "SCH_VIS_M_V1",
    (InstitutionType.SCHOOL, Impairment.VISION,  Gender.FEMALE): "SCH_VIS_F_V1",
    (InstitutionType.SCHOOL, Impairment.MOTOR,   Gender.MALE):   "SCH_MOT_M_V1",
    (InstitutionType.SCHOOL, Impairment.MOTOR,   Gender.FEMALE): "SCH_MOT_F_V1",

    # COLLEGE
    (InstitutionType.COLLEGE, Impairment.HEARING, Gender.MALE):   "COL_HEAR_M_V1",
    (InstitutionType.COLLEGE, Impairment.HEARING, Gender.FEMALE): "COL_HEAR_F_V1",
    (InstitutionType.COLLEGE, Impairment.VISION,  Gender.MALE):   "COL_VIS_M_V1",
    (InstitutionType.COLLEGE, Impairment.VISION,  Gender.FEMALE): "COL_VIS_F_V1",
    (InstitutionType.COLLEGE, Impairment.MOTOR,   Gender.MALE):   "COL_MOT_M_V1",
    (InstitutionType.COLLEGE, Impairment.MOTOR,   Gender.FEMALE): "COL_MOT_F_V1",

    # UNIVERSITY
    (InstitutionType.UNIVERSITY, Impairment.HEARING, Gender.MALE):   "UNI_HEAR_M_V1",
    (InstitutionType.UNIVERSITY, Impairment.HEARING, Gender.FEMALE): "UNI_HEAR_F_V1",
    (InstitutionType.UNIVERSITY, Impairment.VISION,  Gender.MALE):   "UNI_VIS_M_V1",
    (InstitutionType.UNIVERSITY, Impairment.VISION,  Gender.FEMALE): "UNI_VIS_F_V1",
    (InstitutionType.UNIVERSITY, Impairment.MOTOR,   Gender.MALE):   "UNI_MOT_M_V1",
    (InstitutionType.UNIVERSITY, Impairment.MOTOR,   Gender.FEMALE): "UNI_MOT_F_V1",
}

def select_test_code(institution_type: str, impairment: str, gender: str) -> str:
    try:
        inst = InstitutionType(institution_type)
        imp  = Impairment(impairment)
        gen  = Gender(gender)
    except ValueError as e:
        raise ValueError(f"Недопустимое значение: {e}")

    code = MATRIX.get((inst, imp, gen))
    if not code:
        raise ValueError(f"Комбинация не поддерживается: ({inst.value}, {imp.value}, {gen.value})")
    return code
