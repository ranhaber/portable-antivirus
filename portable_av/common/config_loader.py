import json
from pathlib import Path

from portable_av.common.config import AppConfig


class ConfigValidationError(ValueError):
    """Raised when configuration cannot be parsed or validated."""


def load_config(path: Path) -> AppConfig:
    if not path.is_file():
        raise ConfigValidationError(f"Config file not found: {path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigValidationError(f"Invalid JSON in {path}: {exc}") from exc
    try:
        return AppConfig.model_validate(raw)
    except Exception as exc:
        raise ConfigValidationError(f"Invalid config in {path}: {exc}") from exc


def save_config(path: Path, config: AppConfig) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(
        json.dumps(config.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    temp_path.replace(path)
