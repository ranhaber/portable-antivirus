from pathlib import Path
from unittest.mock import patch

from portable_av.engine.clamav_adapter import ClamAvAdapter
from portable_av.engine.file_enumerator import FileEnumerator, should_scan_file
from portable_av.common.models import ScanMode


def test_quick_scan_extension_filter(tmp_path: Path) -> None:
    exe = tmp_path / "sample.exe"
    txt = tmp_path / "notes.txt"
    exe.write_bytes(b"MZ")
    txt.write_text("hello", encoding="utf-8")
    assert should_scan_file(exe, ScanMode.QUICK) is True
    assert should_scan_file(txt, ScanMode.QUICK) is False
    assert should_scan_file(txt, ScanMode.FULL) is True


def test_enumerator_quick_scan_skips_plain_text(tmp_path: Path) -> None:
    (tmp_path / "clean.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "payload.exe").write_bytes(b"MZ")
    files = list(FileEnumerator().enumerate(tmp_path, ScanMode.QUICK))
    names = {item.relative_path for item in files}
    assert names == {"payload.exe"}


def test_clamav_parse_signature() -> None:
    output = r"C:\malware\eicar.com: Eicar-Signature FOUND"
    assert ClamAvAdapter._parse_signature(output) == "Eicar-Signature"


def test_clamd_mode_requires_clamdscan(tmp_path: Path) -> None:
    sample = tmp_path / "sample.exe"
    sample.write_bytes(b"MZ")
    with patch("portable_av.engine.clamav_adapter.which") as mock_which:
        mock_which.side_effect = lambda name: "/usr/bin/clamscan" if name == "clamscan" else None
        command = ClamAvAdapter(mode="clamd")._build_command(sample)

    assert command is None
    mock_which.assert_called_once_with("clamdscan")


def test_clamd_mode_uses_fdpass(tmp_path: Path) -> None:
    sample = tmp_path / "sample.exe"
    sample.write_bytes(b"MZ")
    with patch("portable_av.engine.clamav_adapter.which", return_value="/usr/bin/clamdscan"):
        command = ClamAvAdapter(mode="clamd")._build_command(sample)

    assert command == ["/usr/bin/clamdscan", "--no-summary", "--fdpass", str(sample)]


def test_clamscan_mode_uses_standalone_scanner(tmp_path: Path) -> None:
    sample = tmp_path / "sample.exe"
    sample.write_bytes(b"MZ")
    with patch("portable_av.engine.clamav_adapter.which", return_value="/usr/bin/clamscan"):
        command = ClamAvAdapter(mode="clamscan")._build_command(sample)

    assert command == ["/usr/bin/clamscan", "--no-summary", str(sample)]
