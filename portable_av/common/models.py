from enum import StrEnum


class ScanMode(StrEnum):
    QUICK = "quick"
    FULL = "full"


class ScanState(StrEnum):
    BOOT = "boot"
    IDLE = "idle"
    MOUNTED = "mounted"
    MENU = "menu"
    SCANNING = "scanning"
    THREAT_PROMPT = "threat_prompt"
    COMPLETE = "complete"
    ERROR = "error"


class ScanStage(StrEnum):
    ENUMERATING = "enumerating"
    HASHING = "hashing"
    CLAMAV = "clamav"
    YARA = "yara"
    REPORTING = "reporting"
    COMPLETE = "complete"


class ScanStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class ThreatAction(StrEnum):
    PENDING = "pending"
    CONTINUE = "continue"
    STOP = "stop"
    DETAILS = "details"
