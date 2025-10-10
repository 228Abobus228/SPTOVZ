from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass
import yaml

from SPTOVZ.utils.scoring import compute_result


CONFIG_ROOT = Path(__file__).resolve().parents[2] / "config" / "emspt"


@dataclass
class Profile:
    """Профиль тестируемого для подбора таблиц норм и стэнов."""
    form: str        # "A" | "B" | "C"
    impairment: str  # "hearing" | "vision" | "motor"
    gender: str      # "male" | "female"


# --------------------- Вспомогательные функции ---------------------

def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"YAML not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_keys(profile: Profile) -> Dict[str, Any]:
    """Загружает ключ шкал в зависимости от формы."""
    if profile.form == "A":
        path = CONFIG_ROOT / "keys_A.yaml"
    else:
        path = CONFIG_ROOT / "keys_BC.yaml"
    return _load_yaml(path)


def _load_lie_correction() -> Dict[str, Any]:
    return _load_yaml(CONFIG_ROOT / "lie_correction.yaml")


def _load_norms() -> Dict[str, Any]:
    return _load_yaml(CONFIG_ROOT / "norms.yaml")


def _load_sten_table(profile: Profile) -> Dict[str, Any]:
    """Загружает таблицу перевода в стэны по форме/нозологии/полу."""
    path = (
        CONFIG_ROOT.parent / "emspt" / "sten_tables"
        / profile.form / profile.impairment / f"{profile.gender}.yaml"
    )
    return _load_yaml(path)


# --------------------- Основная функция расчёта ---------------------

def compute_emspt(answers_map: Dict[str, int],
                  profile: Profile,
                  questions: list[dict],
                  scoring_cfg: dict) -> Dict[str, Any]:
    """
    Выполняет полный цикл расчёта ЕМ СПТ:
    1. Подсчёт сырых баллов (compute_result)
    2. Коррекция по шкале лжи
    3. Расчёт KVERIPO / IRP
    4. Определение интервалов
    5. Перевод в стэны
    """

    # 1️⃣ Базовые результаты
    raw = compute_result(answers_map, questions, scoring_cfg)
    keys = _load_keys(profile)
    norms = _load_norms()
    sten_table = _load_sten_table(profile)
    lie_cfg = _load_lie_correction()

    # --- вычисление по шкалам из keys_* ---
    scales = {}
    for scale_name, items in keys.items():
        scales[scale_name] = sum(answers_map.get(str(qid), 0) for qid in items)

    # 2️⃣ Коррекция по шкале лжи (если есть "L")
    lie_raw = scales.get("L", 0)
    if lie_raw and lie_cfg:
        limit = lie_cfg.get("limit", 0)
        coeff = lie_cfg.get("coeff", 1)
        if lie_raw >= limit:
            for k in scales:
                if k != "L":
                    scales[k] = round(scales[k] * coeff, 2)

    # 3️⃣ Расчёт KVERIPO и IRP
    irp = round(sum(scales.values()) / max(len(scales), 1), 2)
    kveripo = 100 * irp / 10  # пример нормализации, потом уточним из norms.yaml

    # 4️⃣ Определение интервалов
    irp_interval = _get_interval(irp, norms.get("IRP", []))
    kveripo_interval = _get_interval(kveripo, norms.get("KVERIPO", []))

    # 5️⃣ Перевод в стэны (по таблице формы/пола/нозологии)
    sten_result = {}
    for scale, raw_value in scales.items():
        sten_result[scale] = _convert_to_sten(sten_table, scale, raw_value)

    return {
        "raw": raw,
        "scales": scales,
        "irp": irp,
        "irp_interval": irp_interval,
        "kveripo": kveripo,
        "kveripo_interval": kveripo_interval,
        "sten": sten_result,
        "profile": profile.__dict__,
    }


# --------------------- Вспомогательные функции ---------------------

def _get_interval(value: float, table: list[dict]) -> str:
    """
    Находит интервал по таблице норм:
    [{'min':0,'max':3,'label':'низкий'}, ...]
    """
    for row in table:
        if row["min"] <= value <= row["max"]:
            return row["label"]
    return "вне диапазона"


def _convert_to_sten(sten_table: Dict[str, Any], scale: str, value: float) -> int:
    """
    Находит ближайший стэн по шкале.
    sten_table = { "A": { "hearing": { "male": { "scale1": {raw: sten,...}}}}}
    """
    table = sten_table.get(scale) or {}
    if not table:
        return 0
    # ищем ближайшее значение
    diffs = {abs(int(raw) - value): sten for raw, sten in table.items()}
    return diffs[min(diffs.keys())]
