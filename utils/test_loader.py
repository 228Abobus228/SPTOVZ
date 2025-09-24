from __future__ import annotations
from pathlib import Path
from typing import List, Dict, Any, Tuple
import yaml
from sqlalchemy.orm import Session
from SPTOVZ.models.testbank import TestPassport, TestContent

CATALOG_ROOT = Path(__file__).resolve().parents[1] / "tests_catalog"

ALLOWED_INSTITUTIONS = {"school", "college", "university"}
ALLOWED_IMPAIRMENTS = {"hearing", "vision", "motor"}

class CatalogError(Exception):
    pass

def _load_yaml(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        raise CatalogError(f"Ошибка чтения YAML {path}: {e}") from e
    if not isinstance(data, dict):
        raise CatalogError(f"Формат YAML должен быть mapping: {path}")
    return data

def discover_tests(root: Path | None = None) -> List[Path]:
    root = Path(root) if root else CATALOG_ROOT
    if not root.exists():
        return []
    return sorted([p for p in root.rglob("v*.y*ml") if p.is_file()])

def _validate_meta(meta: Dict[str, Any], path: Path) -> Tuple[str, str, str, int, str]:
    """
    Возвращает: (institution, impairment, code, version, form)
    """
    required = ("institution", "impairment", "code", "version", "form")
    missing = [k for k in required if k not in meta]
    if missing:
        raise CatalogError(f"{path}: нет meta полей: {', '.join(missing)}")

    institution = str(meta["institution"]).strip()
    impairment = str(meta["impairment"]).strip()
    code = str(meta["code"]).strip()
    form = str(meta["form"]).strip().upper()
    try:
        version = int(meta["version"])
    except Exception as e:
        raise CatalogError(f"{path}: meta.version должен быть int") from e

    if institution not in ALLOWED_INSTITUTIONS:
        raise CatalogError(f"{path}: institution ∈ {sorted(ALLOWED_INSTITUTIONS)}")
    if impairment not in ALLOWED_IMPAIRMENTS:
        raise CatalogError(f"{path}: impairment ∈ {sorted(ALLOWED_IMPAIRMENTS)}")
    if form not in {"A", "B", "C"}:
        raise CatalogError(f"{path}: form должен быть 'A'|'B'|'C'")
    if not code:
        raise CatalogError(f"{path}: meta.code пуст")

    return institution, impairment, code, version, form

def import_test_file(db: Session, path: Path) -> str:
    data = _load_yaml(path)
    meta = data.get("meta") or {}
    questions = data.get("questions")
    if questions is None or not isinstance(questions, list):
        raise CatalogError(f"{path}: отсутствует корректный раздел 'questions'")

    institution, impairment, code, version, form = _validate_meta(meta, path)
    title = str(meta.get("title") or code)
    locale = str(meta.get("locale") or "ru")
    scoring = meta.get("scoring") or {}

    # upsert
    for model, pk in ((TestPassport, code), (TestContent, code)):
        existed = db.get(model, pk)
        if existed:
            db.delete(existed)
    db.flush()

    passport = TestPassport(
        id=code,
        institution=institution,
        impairment=impairment,
        gender="any",          # <- фиксированное значение, больше не используем при выборе
        version=version,
        title=title,
        locale=locale,
        form=form,
    )
    content = TestContent(
        id=code,
        questions=questions,
        scoring=scoring,
    )

    db.add(passport)
    db.add(content)
    db.commit()
    return code

def import_all(db: Session, root: Path | None = None, stop_on_error: bool = False) -> Dict[str, Any]:
    root = Path(root) if root else CATALOG_ROOT
    files = discover_tests(root)
    imported: List[str] = []
    errors: Dict[str, str] = {}
    for p in files:
        try:
            imported.append(import_test_file(db, p))
        except Exception as e:
            errors[str(p)] = str(e)
            if stop_on_error:
                raise
    return {"imported": imported, "errors": errors, "root": str(root), "count": len(imported)}

if __name__ == "__main__":
    from SPTOVZ.database import SessionLocal
    db = SessionLocal()
    try:
        print(import_all(db))
    finally:
        db.close()
