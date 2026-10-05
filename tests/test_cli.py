import shutil
from pathlib import Path

from deckoction import cli

DEMO_DIR = Path(__file__).resolve().parent.parent / "examples" / "demo"


def _copy_demo(tmp_path):
    deck = tmp_path / "deck"
    shutil.copytree(DEMO_DIR, deck)
    return deck / "slides.md"


def test_slides_md_builds_next_to_input_and_serves(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(cli.subprocess, "run", lambda cmd, **kw: calls.append((cmd, kw)))
    slides = _copy_demo(tmp_path)

    assert cli.serve_main([str(slides)]) == 0
    out = slides.parent / "build"
    assert (out / "index.html").exists()
    (cmd, kw), = calls
    assert cmd[1:] == ["-m", "http.server", "8000"]
    assert kw["cwd"] == out


def test_slides_md_rebuild_requires_force(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli.subprocess, "run", lambda cmd, **kw: None)
    slides = _copy_demo(tmp_path)

    assert cli.serve_main([str(slides)]) == 0
    assert cli.serve_main([str(slides)]) == 1
    assert "--force" in capsys.readouterr().err
    assert cli.serve_main([str(slides), "--force", "--port", "9001"]) == 0
