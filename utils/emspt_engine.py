from __future__ import annotations
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass
import yaml


# --------------------- Константы ---------------------

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_ROOT = BASE_DIR / "config" / "emspt"


# --------------------- Профиль ---------------------

@dataclass
class Profile:
    """Профиль тестируемого для подбора таблиц норм и стэнов."""
    form: str        # "A" | "B" | "C"
    impairment: str  # "hearing" | "vision" | "motor"
    gender: str      # "male" | "female"


# --------------------- Загрузка YAML ---------------------

def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"YAML not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_keys(profile: Profile) -> Dict[str, Any]:
    """Загружает ключи шкал по форме."""
    if profile.form == "A":
        path = CONFIG_ROOT / "keys_A.yaml"
    else:
        path = CONFIG_ROOT / "keys_BC.yaml"
    data = _load_yaml(path)
    return data  # возвращаем весь словарь (risk_scales, protect_scales, lie_scale, keys)


def _load_lie_correction() -> Dict[str, Any]:
    return _load_yaml(CONFIG_ROOT / "lie_correction.yaml")


def _load_norms(profile: Profile) -> Dict[str, Any]:
    data = _load_yaml(CONFIG_ROOT / "norms.yaml")
    return (
        data.get(profile.form, {})
            .get(profile.impairment, {})
            .get(profile.gender, {})
    )


def _load_sten_table(profile: Profile) -> Dict[str, Any]:
    path = CONFIG_ROOT / "sten_tables" / profile.form / profile.impairment / f"{profile.gender}.yaml"
    return _load_yaml(path)

def _load_interpretations() -> Dict[str, Any]:
    """Загружает интерпретации стэнов для шкал."""
    path = CONFIG_ROOT / "interpretations.yaml"
    if not path.exists():
        return {}
    return _load_yaml(path)

# --------------------- Основная функция расчёта ---------------------

def compute_emspt(answers_map: Dict[str, int], profile: Profile) -> Dict[str, Any]:
    """
    Выполняет полный расчёт результатов ЕМ СПТ-ОВЗ:
    - суммирует ответы по шкалам
    - применяет коррекцию по ЛЖ
    - считает IRP и KVERIPO
    - определяет интервалы
    - переводит в стэны
    """
    keys_data = _load_keys(profile)
    lie_cfg = _load_lie_correction()
    norms = _load_norms(profile)
    sten_table = _load_sten_table(profile)

    risk_scales = keys_data["risk_scales"]
    protect_scales = keys_data["protect_scales"]
    lie_scale = keys_data["lie_scale"]
    keys = keys_data["keys"]

    # ---------- 1️⃣ Расчёт сырых баллов по шкалам ----------
    scales: Dict[str, float] = {}
    for scale_name, question_ids in keys.items():
        total = sum(answers_map.get(q, answers_map.get(str(q), 0)) for q in question_ids)
        scales[scale_name] = round(total, 2)

    # ---------- 2️⃣ Коррекция по шкале ЛЖ ----------
    lie_raw = scales.get(lie_scale, 0)
    threshold = lie_cfg["threshold"].get(profile.form, 999)
    coeff_value = (
        lie_cfg["coeff"]
        .get(profile.form, {})
        .get(profile.impairment, {})
        .get(profile.gender, 0.0)
    )

    lie_applied = False
    if lie_raw >= threshold:
        lie_applied = True
        for k in scales:
            if k != lie_scale:
                scales[k] = round(scales[k] * (1 - coeff_value), 2)

    # ---------- 3️⃣ Расчёт индексов IRP и KVERIPO ----------
    sum_risk = sum(scales[s] for s in risk_scales if s in scales)
    sum_prot = sum(scales[s] for s in protect_scales if s in scales)

    irp = round(sum_risk, 2)
    kveripo = round(sum_prot / sum_risk if sum_risk else 0, 2)

    # ---------- 4️⃣ Определение интервалов ----------
    irp_bands = norms.get("IRP_bands", {})
    kveripo_max = norms.get("KVERIPO_max", 1)

    def _band_label(value: float, bands: dict) -> str:
        for label, (min_v, max_v) in bands.items():
            if min_v <= value <= max_v:
                return label
        return "вне диапазона"

    irp_interval = _band_label(irp, irp_bands)
    kveripo_interval = "в норме" if kveripo <= kveripo_max else "выше нормы"

    # ---------- 5️⃣ Перевод в стэны ----------
    sten_result = {}
    for scale, raw_value in scales.items():
        sten_result[scale] = _convert_to_sten(sten_table, scale, raw_value)

    # ---------- 6️⃣ Возврат результата ----------
    interpretations_data = _load_interpretations()
    interpretations_result = {}

    # Берём только те шкалы, которые реально есть в форме теста
    active_scales = set(keys.keys())

    for scale, sten_value in sten_result.items():
        if scale not in active_scales:
            continue  # пропускаем шкалы не из текущего теста
        if not sten_value or sten_value == 0:
            continue

        # Определяем уровень по диапазону стэна
        if 1 <= sten_value <= 3:
            level = "low"
        elif 4 <= sten_value <= 7:
            level = "mid"
        else:
            level = "high"

        # Берём текст интерпретации (если есть)
        text = interpretations_data.get(scale, {}).get(level, "")
        interpretations_result[scale] = {
            "sten": sten_value,
            "level": level,
            "text": text or "(описание не задано)"
        }

    # ---------- 7️⃣ Возврат результата ----------
    return {
        "scales": scales,
        "lie_raw": lie_raw,
        "lie_applied": lie_applied,
        "irp": irp,
        "irp_interval": irp_interval,
        "kveripo": kveripo,
        "kveripo_interval": kveripo_interval,
        "sten": sten_result,
        "interpretations": interpretations_result,
        "profile": profile.__dict__,
    }


# --------------------- Перевод в стэны ---------------------

def _convert_to_sten(sten_table: Dict[str, Any], scale: str, value: float) -> int:
    """
    Перевод "сырых" баллов в стэны.
    Поддерживает формат:
      PPZ:
        - [1,9]
        - [10,15]
        - [16,21]
        ...
    Возвращает номер интервала (1–10), в который попадает значение.
    """
    if not sten_table or scale not in sten_table:
        return 0

    intervals = sten_table[scale]
    if not isinstance(intervals, list):
        return 0

    # проходим по каждому диапазону
    for i, rng in enumerate(intervals, start=1):
        if isinstance(rng, list) and len(rng) == 2:
            low, high = rng
            if low <= value <= high:
                return i

    # если значение выше всех диапазонов → максимальный стэн
    if intervals and isinstance(intervals[-1], list):
        return 10

    return 0

