from __future__ import annotations

import asyncio
import re
from pathlib import Path
from shutil import which

from portable_av.engine.interfaces import EngineResult

_MATCH_RE = re.compile(r"^(.+?)\s+(.+)$")


class YaraAdapter:
    def __init__(self, rules_dir: Path) -> None:
        self._rules_dir = rules_dir
        self._rules_file: Path | None = None

    def load_rules(self) -> bool:
        self._rules_dir.mkdir(parents=True, exist_ok=True)
        rule_files = sorted(self._rules_dir.glob("*.yar")) + sorted(self._rules_dir.glob("*.yara"))
        if not rule_files:
            return False
        self._rules_file = rule_files[0]
        return True

    async def scan_file(self, path: Path, timeout_sec: int) -> list[EngineResult]:
        if self._rules_file is None and not self.load_rules():
            return []
        executable = which("yara")
        if executable is None or self._rules_file is None:
            return []

        try:
            proc = await asyncio.create_subprocess_exec(
                executable,
                "-s",
                str(self._rules_file),
                str(path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
        except TimeoutError:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()
            return [
                EngineResult(
                    engine="yara",
                    clean=True,
                    signature=None,
                    raw_output="",
                    timed_out=True,
                    error=f"Timed out after {timeout_sec}s",
                )
            ]

        output = (stdout or b"").decode("utf-8", errors="replace")
        if stderr:
            output += (stderr or b"").decode("utf-8", errors="replace")
        if proc.returncode not in (0, 1):
            return [
                EngineResult(
                    engine="yara",
                    clean=True,
                    signature=None,
                    raw_output=output,
                    error=f"Exit code {proc.returncode}",
                )
            ]

        results: list[EngineResult] = []
        for line in output.splitlines():
            match = _MATCH_RE.match(line.strip())
            if not match:
                continue
            results.append(
                EngineResult(
                    engine="yara",
                    clean=False,
                    signature=match.group(1).strip(),
                    raw_output=line,
                )
            )
        return results
