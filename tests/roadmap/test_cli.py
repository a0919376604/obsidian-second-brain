import json
import subprocess
import sys
from pathlib import Path


def _make_minimal_project(root: Path):
    arch = root / "Architecture"
    arch.mkdir(parents=True)
    (arch / "future.md").write_text(
        "## 落差分析\n\n- README 提到 streaming API 但 api-surface 沒對應 endpoint\n"
        "## 期望中的想法\n\n- 把 AI 引擎抽象成 pluggable adapter\n"
    )
    (arch / "decisions.md").write_text(
        "## 建議升級為 ADR\n\n1. **為什麼 Redis Cluster** — TBD\n"
    )
    (arch / "roadmap.md").write_text("## 給未來 Claude\n empty roadmap\n")


def test_cli_dry_run_emits_candidates(tmp_path: Path):
    proj = tmp_path / "Projects" / "p"
    _make_minimal_project(proj)
    out_dir = tmp_path / "out"
    result = subprocess.run(
        [sys.executable, "scripts/roadmap_synth.py",
         "--project-root", str(proj),
         "--vault-root", str(tmp_path),
         "--out", str(out_dir),
         "--dry-run"],
        capture_output=True, text=True, cwd=Path(__file__).resolve().parents[2],
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    candidates_file = out_dir / "candidates.json"
    assert candidates_file.exists()
    data = json.loads(candidates_file.read_text())
    assert len(data) >= 3
    kinds = {c["kind"] for c in data}
    assert "gap" in kinds
    assert "aspiration" in kinds
    assert "promote-to-adr" in kinds


def test_cli_emits_keyword_prompt(tmp_path: Path):
    proj = tmp_path / "Projects" / "p"
    _make_minimal_project(proj)
    out_dir = tmp_path / "out"
    result = subprocess.run(
        [sys.executable, "scripts/roadmap_synth.py",
         "--project-root", str(proj),
         "--vault-root", str(tmp_path),
         "--out", str(out_dir),
         "--dry-run"],
        capture_output=True, text=True, cwd=Path(__file__).resolve().parents[2],
    )
    assert result.returncode == 0
    kp = out_dir / "keyword_extraction_prompt.txt"
    assert kp.exists()
    text = kp.read_text()
    assert "streaming" in text or "AI 引擎" in text or "Redis" in text


def test_cli_aborts_when_no_architecture_dir(tmp_path: Path):
    proj = tmp_path / "Projects" / "p"
    proj.mkdir(parents=True)  # no Architecture subfolder
    result = subprocess.run(
        [sys.executable, "scripts/roadmap_synth.py",
         "--project-root", str(proj),
         "--vault-root", str(tmp_path),
         "--out", str(tmp_path / "out"),
         "--dry-run"],
        capture_output=True, text=True, cwd=Path(__file__).resolve().parents[2],
    )
    assert result.returncode != 0
    assert "Architecture" in result.stderr or "Architecture" in result.stdout
