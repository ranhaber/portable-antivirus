from pathlib import Path


class AppPaths:
    """Deployment paths. Override in tests via constructor arguments."""

    def __init__(
        self,
        *,
        config_file: Path | None = None,
        data: Path | None = None,
        reports: Path | None = None,
        logs: Path | None = None,
        runtime: Path | None = None,
        temp: Path | None = None,
    ) -> None:
        self.config_file = config_file or Path("/etc/portable-av/config.json")
        self.data = data or Path("/var/lib/portable-av")
        self.reports = reports or self.data / "reports"
        self.logs = logs or Path("/var/log/portable-av")
        self.runtime = runtime or Path("/run/portable-av")
        self.temp = temp or Path("/tmp/portable-av")

    @property
    def history_db(self) -> Path:
        return self.data / "history.db"

    @property
    def yara_rules(self) -> Path:
        return self.data / "yara" / "rules"

    def ensure_runtime_dirs(self) -> None:
        for path in (self.data, self.reports, self.logs, self.runtime, self.temp):
            path.mkdir(parents=True, exist_ok=True)
