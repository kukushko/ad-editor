from __future__ import annotations

from pathlib import Path

from .process import ProcResult, run_command


class BuildService:
    def __init__(self, repo_root: Path, adtool_path: Path, output_dir: Path, specs_dir: Path) -> None:
        self.repo_root = repo_root
        self.adtool_path = adtool_path
        self.output_dir = output_dir
        self.specs_dir = specs_dir

    def get_output_path(self, architecture_id: str) -> Path:
        return self.output_dir / f"AD_{architecture_id}.md"

    def build(self, architecture_id: str) -> ProcResult:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        spec_path = self.specs_dir if architecture_id == "_root" else (self.specs_dir / architecture_id)
        output_file = self.get_output_path(architecture_id)

        cmd = [
            "python",
            str(self.adtool_path),
            "build",
            str(spec_path),
            "--out",
            str(output_file),
        ]
        return run_command(cmd, cwd=self.repo_root)
