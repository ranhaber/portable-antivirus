from pathlib import Path

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
