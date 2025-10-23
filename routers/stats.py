# SPTOVZ/routers/stats.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
import json

from SPTOVZ.database import get_db
from SPTOVZ.routers.auth import get_current_user
from SPTOVZ.models import User, Key, TestSession

# Попытка импортировать модель класса (Class / SchoolClass)
SchoolClassModel = None
try:
    from SPTOVZ.models import Class as SchoolClassModel
except Exception:
    try:
        from SPTOVZ.models import SchoolClass as SchoolClassModel
    except Exception:
        SchoolClassModel = None


router = APIRouter(prefix="/stats", tags=["Stats"])

# ------------------------------------------------------------
# Константы уровней
# ------------------------------------------------------------
IRP_LEVELS = ["низкий", "средний", "высокий"]
KVERIPO_LEVELS = ["низкий", "высокий"]


# ------------------------------------------------------------
# Вспомогательные функции
# ------------------------------------------------------------
def normalize(rows, levels):
    """
    Преобразует [(level, count)] → {уровень: процент}.
    """
    counts = {lvl: 0 for lvl in levels}
    total = 0

    for lvl, cnt in rows:
        if not lvl:
            continue
        lvl = str(lvl).strip().lower()

        # Унификация формулировок
        if "высочай" in lvl:
            lvl = "высокий"
        elif "высок" in lvl or "выше" in lvl:
            lvl = "высокий"
        elif "сред" in lvl or "норм" in lvl:
            lvl = "средний"
        elif "низ" in lvl or "ниже" in lvl:
            lvl = "низкий"
        else:
            # неизвестные значения пропускаем
            continue

        try:
            n = int(cnt)
        except Exception:
            n = 1

        if lvl in counts:
            counts[lvl] += n
            total += n

    total = max(total, 1)
    return {lvl: round(counts[lvl] * 100.0 / total, 2) for lvl in levels}


def keys_subquery_for_institution(db: Session, institution_id: int):
    """
    Возвращает подзапрос с id ключей, принадлежащих учреждению.
    Поддерживает:
      1) Key.institution_id
      2) Key.class_id -> Class.institution_id
    """
    if hasattr(Key, "institution_id"):
        return db.query(Key.id).filter(Key.institution_id == institution_id).subquery()

    if (
        SchoolClassModel is not None
        and hasattr(Key, "class_id")
        and hasattr(SchoolClassModel, "institution_id")
    ):
        return (
            db.query(Key.id)
            .join(SchoolClassModel, Key.class_id == SchoolClassModel.id)
            .filter(SchoolClassModel.institution_id == institution_id)
            .subquery()
        )

    raise HTTPException(
        status_code=500,
        detail=(
            "Не удалось определить связь Key с учреждением. "
            "Добавьте на Key поле institution_id ИЛИ используйте связь "
            "Key.class_id → Class.institution_id."
        ),
    )


# ------------------------------------------------------------
# Основной эндпоинт
# ------------------------------------------------------------
@router.get("/summary")
def get_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Возвращает статистику по учреждению текущего пользователя:
    - всего ключей
    - завершённых сессий
    - оставшихся
    - распределение IRP/KVERIPO по уровням (%)
    """
    inst_id = getattr(user, "institution_id", None)
    if inst_id is None:
        return {
            "institution": "—",
            "total": 0,
            "completed": 0,
            "remaining": 0,
            "irp_distribution": {k: 0 for k in IRP_LEVELS},
            "kveripo_distribution": {k: 0 for k in KVERIPO_LEVELS},
        }

    # --- Ключи учреждения ---
    keys_sq = keys_subquery_for_institution(db, inst_id)

    # --- Количество ключей и сессий ---
    total_keys = db.query(func.count()).select_from(keys_sq).scalar() or 0

    completed = (
        db.query(func.count(TestSession.id))
        .filter(TestSession.finished_at.isnot(None))
        .filter(TestSession.key_id.in_(select(keys_sq.c.id)))
        .scalar()
        or 0
    )
    remaining = max(total_keys - completed, 0)

    # --- Извлекаем результаты и считаем уровни ---
    sess_results = (
        db.query(TestSession.result)
        .filter(TestSession.finished_at.isnot(None))
        .filter(TestSession.key_id.in_(select(keys_sq.c.id)))
        .all()
    )

    irp_rows = []
    kveripo_rows = []

    for (res,) in sess_results:
        obj = None
        if isinstance(res, dict):
            obj = res
        else:
            try:
                obj = json.loads(res) if isinstance(res, str) else None
            except Exception:
                obj = None

        if not obj:
            continue

        irp_lvl = str(obj.get("irp_interval", "")).strip().lower()
        kver_lvl = str(obj.get("kveripo_interval", "")).strip().lower()

        if irp_lvl:
            irp_rows.append((irp_lvl, 1))
        if kver_lvl:
            kveripo_rows.append((kver_lvl, 1))

    # --- Название учреждения ---
    institution_label = f"ID {inst_id}"
    if hasattr(user, "institution") and getattr(user, "institution") is not None:
        institution_label = getattr(user.institution, "name", institution_label)

    # --- Итоговый ответ ---
    return {
        "institution": institution_label,
        "total": int(total_keys),
        "completed": int(completed),
        "remaining": int(remaining),
        "irp_distribution": normalize(irp_rows, IRP_LEVELS),
        "kveripo_distribution": normalize(kveripo_rows, KVERIPO_LEVELS),
    }
