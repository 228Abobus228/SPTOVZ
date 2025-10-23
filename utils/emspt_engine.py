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
    path = CONFIG_ROOT / ("keys_A.yaml" if profile.form == "A" else "keys_BC.yaml")
    return _load_yaml(path)


def _load_lie_correction() -> Dict[str, Any]:
    return _load_yaml(CONFIG_ROOT / "lie_correction.yaml")


def _load_norms(profile: Profile) -> Dict[str, Any]:
    """Загружает нормы для формы, нозологии и пола."""
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
    return _load_yaml(path) if path.exists() else {}


# --------------------- Основная функция расчёта ---------------------

def compute_emspt(answers_map: Dict[str, int], profile: Profile) -> Dict[str, Any]:
    """
    Полный расчёт ЕМ СПТ-ОВЗ:
    - суммирует ответы по шкалам
    - применяет коррекцию по ЛЖ
    - считает IRP и KVERIPO по методичке
    - определяет интервалы по norms.yaml
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

    # ---------- 1️⃣ Сырые баллы по шкалам ----------
    scales: Dict[str, float] = {}
    for scale_name, question_ids in keys.items():
        total = sum(answers_map.get(q, answers_map.get(str(q), 0)) for q in question_ids)
        scales[scale_name] = round(total, 2)

    # ---------- 2️⃣ Коррекция по шкале ЛЖ ----------
    lie_raw = scales.get(lie_scale, 0)
    threshold = (lie_cfg.get("threshold") or {}).get(profile.form, 999)
    coeff_value = (
        (lie_cfg.get("coeff") or {})
        .get(profile.form, {})
        .get(profile.impairment, {})
        .get(profile.gender, 0.0)
    )

    lie_applied = False
    if lie_raw >= threshold and coeff_value > 0:
        lie_applied = True
        for k in list(scales.keys()):
            if k != lie_scale:
                scales[k] = round(scales[k] * (1 - coeff_value), 2)

    # ---------- 3️⃣ Индексы IRP и KVERIPO (строго по методичке) ----------
    sum_risk = sum(scales.get(s, 0.0) for s in risk_scales)
    sum_prot = sum(scales.get(s, 0.0) for s in protect_scales)

    # KVERIPO = ΣФР / ΣФЗ  (если ΣФЗ = 0 → очень высокая уязвимость)
    if sum_prot > 0:
        kveripo = round(sum_risk / sum_prot, 2)
    else:
        kveripo = 999.0  # избегаем бесконечности и даем гарантированно "высокий"

    # IRP = ΣФР / (ΣФР + ΣФЗ) × 100
    total_rf = sum_risk + sum_prot
    irp = round((sum_risk / total_rf) * 100.0, 2) if total_rf > 0 else 0.0

    # ---------- 4️⃣ Интервалы из norms.yaml ----------
    # В norms.yaml:
    #   IRP_bands: {низкий:[min,max], средний:[min,max], высокий:[min,max]}
    #   KVERIPO_max: float  (порог "в норме")
    irp_bands = norms.get("IRP_bands", {})
    kveripo_max = norms.get("KVERIPO_max", None)

    def _band_label(value: float, bands: dict) -> str:
        """Возвращает 'низкий'|'средний'|'высокий' по диапазонам; безопасно для пустых норм."""
        if not bands:
            return "—"
        # перебираем по ключам, чтобы не зависеть от порядка в yaml
        for label in ("низкий", "средний", "высокий"):
            rng = bands.get(label)
            if isinstance(rng, (list, tuple)) and len(rng) == 2:
                lo, hi = rng
                if lo <= value <= hi:
                    return label
        # если не попали ни в один диапазон
        try:
            mins = [v[0] for v in bands.values()]
            maxs = [v[1] for v in bands.values()]
            if value < min(mins):
                return "низкий"
            if value > max(maxs):
                return "высокий"
        except Exception:
            pass
        return "средний"

    irp_interval = _band_label(irp, irp_bands)

    if kveripo_max is None:
        # если порог не задан — помечаем неизвестно
        kveripo_interval = "—"
    else:
        # по методичке: ≤ порога — уязвимость низкая (норма), > порога — высокая
        kveripo_interval = "низкий" if kveripo <= float(kveripo_max) else "высокий"

    # ---------- 5️⃣ Перевод в стэны ----------
    sten_result = {}
    for scale, raw_value in scales.items():
        sten_result[scale] = _convert_to_sten(sten_table, scale, raw_value)

    # ---------- 6️⃣ Интерпретации ----------
    interpretations_data = _load_interpretations()
    interpretations_result = {}
    active_scales = set(keys.keys())

    for scale, sten_value in sten_result.items():
        if scale not in active_scales or not sten_value:
            continue
        if 1 <= sten_value <= 3:
            level = "low"
        elif 4 <= sten_value <= 7:
            level = "mid"
        else:
            level = "high"
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
    Формат:
      PPZ:
        - [1,9]
        - [10,15]
        ...
    Возвращает номер интервала (1–10), в который попадает значение.
    """
    if not sten_table or scale not in sten_table:
        return 0

    intervals = sten_table[scale]
    if not isinstance(intervals, list):
        return 0

    for i, rng in enumerate(intervals, start=1):
        if isinstance(rng, list) and len(rng) == 2:
            low, high = rng
            if low <= value <= high:
                return i

    # если выше последнего интервала — присваиваем 10
    if intervals and isinstance(intervals[-1], list):
        return 10

    return 0
