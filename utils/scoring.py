from __future__ import annotations
from typing import Dict, Any, List

def _reverse(value: int, min_v: int, max_v: int) -> int:
    # 1..10 → 10..1 (формула симметрична для любых границ)
    return min_v + (max_v - value)

def compute_result(answers: Dict[str, int], questions: List[Dict[str, Any]], scoring_cfg: Dict[str, Any]) -> Dict[str, Any]:
    """
    answers: {question_id: int 1..10}
    questions: список вопросов из TestContent.questions
    scoring_cfg: meta.scoring из YAML
    Возвращает JSON с общим и по субшкалам: avg и sum.
    """
    scale_min = int(scoring_cfg.get("scale_min", 1))
    scale_max = int(scoring_cfg.get("scale_max", 10))
    mode = scoring_cfg.get("mode", "avg")
    subscales = scoring_cfg.get("subscales", [])

    # словарь вопрос -> reverse
    qmap = {q["id"]: bool(q.get("reverse", False)) for q in questions}

    # валидируем ответы и применяем реверс где надо
    vals_all: List[int] = []
    norm_answers: Dict[str, int] = {}

    missing = [qid for qid in qmap.keys() if qid not in answers]
    if missing:
        raise ValueError(f"Нет ответов на вопросы: {', '.join(missing)}")

    for qid, rev in qmap.items():
        v = answers[qid]
        if not (scale_min <= v <= scale_max):
            raise ValueError(f"Ответ вне диапазона 1..10 для {qid}: {v}")
        if rev:
            v = _reverse(v, scale_min, scale_max)
        norm_answers[qid] = v
        vals_all.append(v)

    overall_sum = sum(vals_all)
    overall_avg = overall_sum / len(vals_all) if vals_all else 0.0

    # считаем субшкалы (если заданы)
    sub_results: Dict[str, Dict[str, float]] = {}
    for s in subscales:
        ids = s.get("items", [])
        if not ids:
            continue
        vs = [norm_answers[i] for i in ids if i in norm_answers]
        if not vs:
            continue
        sub_results[s["id"]] = {
            "sum": float(sum(vs)),
            "avg": float(sum(vs) / len(vs)),
            "title": s.get("title", s["id"]),
        }

    result = {
        "overall": {
            "sum": float(overall_sum),
            "avg": float(overall_avg),
            "mode": mode,
            "scale_min": scale_min,
            "scale_max": scale_max,
        },
        "subscales": sub_results,
        "normalized_answers": norm_answers,  # ответы с учетом реверса (для отчёта)
    }
    return result
