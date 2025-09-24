from __future__ import annotations

from pathlib import Path
from typing import List, Dict, Any, Tuple

import yaml
from sqlalchemy.orm import Session

from SPTOVZ.models.testbank import TestPassport, TestContent


# Корневая папка с YAML-файлами тестов
CATALOG_ROOT = Path(__file__).resolve().parents[1] / "tests_catalog"

# Допустимые значения для метаданных
ALLOWED_INSTITUTIONS = {"school", "college", "university"}
ALLOWED_IMPAIRMENTS = {"hearing", "vision", "motor"}
ALLOWED_GENDERS = {"male", "female"}


class CatalogError(Exception):
    """Исключение при проблемах с каталогом тестов."""
    pass


def _load_yaml(path: Path) -> Dict[str, Any]:
    """Читает YAML и возвращает dict. Бросает CatalogError при ошибке."""
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception as e:
        raise CatalogError(f"Ошибка чтения YAML {path}: {e}") from e
    if not isinstance(data, dict):
        raise CatalogError(f"Формат YAML должен быть объектом (mapping): {path}")
    return data


def discover_tests(root: Path | None = None) -> List[Path]:
    """
    Ищет все файлы вида v*.yaml / v*.yml в каталоге тестов.
    Возвращает отсортированный список путей.
    """
    root = Path(root) if root else CATALOG_ROOT
    if not root.exists():
        return []
    return sorted([p for p in root.rglob("v*.y*ml") if p.is_file()])


def _validate_meta(meta: Dict[str, Any], path: Path) -> Tuple[str, str, str, str, int]:
    """
    Валидирует метаданные теста и возвращает кортеж:
    (institution, impairment, gender, code, version)
    """
    required = ("institution", "impairment", "gender", "code", "version")
    missing = [k for k in required if k not in meta]
    if missing:
        raise CatalogError(f"{path}: отсутствуют meta поля: {', '.join(missing)}")

    institution = str(meta["institution"]).strip()
    impairment = str(meta["impairment"]).strip()
    gender = str(meta["gender"]).strip()
    code = str(meta["code"]).strip()

    try:
        version = int(meta["version"])
    except Exception as e:
        raise CatalogError(f"{path}: meta.version должен быть целым числом") from e

    if institution not in ALLOWED_INSTITUTIONS:
        raise CatalogError(f"{path}: institution должен быть одним из {sorted(ALLOWED_INSTITUTIONS)}")
    if impairment not in ALLOWED_IMPAIRMENTS:
        raise CatalogError(f"{path}: impairment должен быть одним из {sorted(ALLOWED_IMPAIRMENTS)}")
    if gender not in ALLOWED_GENDERS:
        raise CatalogError(f"{path}: gender должен быть одним из {sorted(ALLOWED_GENDERS)}")
    if not code:
        raise CatalogError(f"{path}: meta.code пуст")

    return institution, impairment, gender, code, version


def import_test_file(db: Session, path: Path) -> str:
    """
    Импортирует один YAML-файл теста в БД (upsert по meta.code).
    Возвращает код теста.
    """
    data = _load_yaml(path)

    meta = data.get("meta") or {}
    questions = data.get("questions")
    if questions is None:
        raise CatalogError(f"{path}: отсутствует раздел 'questions'")
    if not isinstance(questions, list):
        raise CatalogError(f"{path}: 'questions' должен быть массивом")

    institution, impairment, gender, code, version = _validate_meta(meta, path)
    title = str(meta.get("title") or code)
    locale = str(meta.get("locale") or "ru")
    scoring = meta.get("scoring") or {}

    # UPSERT по первичному ключу (code)
    existed_p = db.get(TestPassport, code)
    if existed_p:
        db.delete(existed_p)
    existed_c = db.get(TestContent, code)
    if existed_c:
        db.delete(existed_c)
    db.flush()

    passport = TestPassport(
        id=code,
        institution=institution,
        impairment=impairment,
        gender=gender,
        version=version,
        title=title,
        locale=locale,
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
    """
    Импортирует все тесты из каталога.
    Возвращает словарь: { imported: [codes], errors: {path: error}, root: str, count: int }
    Если stop_on_error=True — при первой ошибке бросает исключение.
    """
    root = Path(root) if root else CATALOG_ROOT
    files = discover_tests(root)
    imported: List[str] = []
    errors: Dict[str, str] = {}

    for p in files:
        try:
            code = import_test_file(db, p)
            imported.append(code)
        except Exception as e:
            errors[str(p)] = str(e)
            if stop_on_error:
                raise

    return {"imported": imported, "errors": errors, "root": str(root), "count": len(imported)}


if __name__ == "__main__":
    # Локальный запуск: python -m SPTOVZ.utils.test_loader
    from SPTOVZ.database import SessionLocal
    db = SessionLocal()
    try:
        result = import_all(db)
        print("Импорт завершён:", result)
    finally:
        db.close()
