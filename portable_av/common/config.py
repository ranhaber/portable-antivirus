from pydantic import BaseModel, Field

from portable_av.common.models import ScanMode


class ApiConfig(BaseModel):
    bind_host: str = "0.0.0.0"
    bind_port: int = 8080
    auth_token_hash: str
    allow_unauthenticated_read: bool = False


class ScanConfig(BaseModel):
    default_mode: ScanMode = ScanMode.QUICK
    clamav_mode: str = Field(default="clamd", pattern="^(clamd|clamscan)$")
    max_file_size_bytes: int = 104_857_600
    per_file_timeout_sec: int = 120
    yara_enabled: bool = True
    yara_max_file_size_bytes: int = 52_428_800
    hash_max_file_size_bytes: int = 104_857_600


class StorageConfig(BaseModel):
    warn_percent: int = 90
    block_percent: int = 95


class DisplayConfig(BaseModel):
    refresh_hz_idle: float = 0.5
    refresh_hz_scanning: float = 2.0
    devices: list[dict] = Field(default_factory=list)


class UpdatesConfig(BaseModel):
    freshclam_schedule: str = "03:00"


class AppConfig(BaseModel):
    version: int = 1
    api: ApiConfig
    scan: ScanConfig = Field(default_factory=ScanConfig)
    display: DisplayConfig = Field(default_factory=DisplayConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    updates: UpdatesConfig = Field(default_factory=UpdatesConfig)
