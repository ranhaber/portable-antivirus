from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from portable_av.history.repository import HistoryRepository


@dataclass(frozen=True)
class ReportPaths:
    txt_path: Path
    html_path: Path


class ReportWriter:
    def __init__(self, templates_dir: Path) -> None:
        self._env = Environment(
            loader=FileSystemLoader(templates_dir),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def write_reports(
        self,
        *,
        scan_id: str,
        output_dir: Path,
        scan_record: dict,
        detections: list[dict],
    ) -> ReportPaths:
        output_dir.mkdir(parents=True, exist_ok=True)
        context = {
            "scan_id": scan_id,
            "scan": scan_record,
            "detections": detections,
            "threat_count": scan_record.get("threat_count", 0),
            "status": scan_record.get("status", "unknown"),
        }
        txt_path = output_dir / "report.txt"
        html_path = output_dir / "report.html"
        txt_path.write_text(
            self._env.get_template("report.txt.j2").render(**context),
            encoding="utf-8",
        )
        html_path.write_text(
            self._env.get_template("report.html.j2").render(**context),
            encoding="utf-8",
        )
        return ReportPaths(txt_path=txt_path, html_path=html_path)
