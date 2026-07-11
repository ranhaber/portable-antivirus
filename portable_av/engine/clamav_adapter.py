from __future__ import annotations

import asyncio
import re
from pathlib import Path
from shutil import which

from portable_av.engine.interfaces import EngineResult

_FOUND_RE = re.compile(r":\s+(.+?)\s+FOUND\s*$", re.MULTILINE)


class ClamAvAdapter:
    def __init__(self, mode: str = "clamd") -> None:
        self._mode = mode

    async def scan_file(self, path: Path, timeout_sec: int) -> EngineResult:
        command = self._build_command(path)
        if command is None:
            return EngineResult(
                engine="clamav",
                clean=True,
                signature=None,
                raw_output="",
                error="ClamAV executable not found",
            )
        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
        except TimeoutError:
            if proc.returncode is None:
                proc.kill()
                await proc.wait()
            return EngineResult(
                engine="clamav",
                clean=True,
                signature=None,
                raw_output="",
                timed_out=True,
                error=f"Timed out after {timeout_sec}s",
            )

        output = (stdout or b"").decode("utf-8", errors="replace")
        if stderr:
            output += (stderr or b"").decode("utf-8", errors="replace")
        signature = self._parse_signature(output)
        return EngineResult(
            engine="clamav",
            clean=signature is None,
            signature=signature,
            raw_output=output,
            error=None if proc.returncode in (0, 1) else f"Exit code {proc.returncode}",
        )

    def _build_command(self, path: Path) -> list[str] | None:
        if self._mode == "clamd":
            executable = which("clamdscan")
            if executable is None:
                return None
            # --fdpass hands the open descriptor to the daemon so it can scan
            # files the clamav user could not otherwise read (e.g. user-owned
            # paths). The daemon keeps the DB resident, so this avoids reloading
            # ~600 MB of signatures per file.
            return [executable, "--no-summary", "--fdpass", str(path)]
        executable = which("clamscan")
        if executable is None:
            return None
        return [executable, "--no-summary", str(path)]

    @staticmethod
    def _parse_signature(output: str) -> str | None:
        match = _FOUND_RE.search(output)
        if match:
            return match.group(1).strip()
        for line in output.splitlines():
            if " FOUND" in line:
                _, _, tail = line.partition(":")
                signature = tail.replace("FOUND", "").strip()
                if signature:
                    return signature
        return None
