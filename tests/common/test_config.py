from pathlib import Path

from portable_av.common.config_loader import load_config


def test_load_dev_config() -> None:
    config = load_config(Path("config/dev.config.json"))
    assert config.version == 1
    assert config.scan.default_mode.value == "quick"
