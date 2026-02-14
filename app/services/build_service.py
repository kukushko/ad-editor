from __future__ import annotations

from pathlib import Path

from .process import ProcResult, run_command


class BuildService:
    def __init__(self, repo_root: Path, adtool_path: Path, output_dir: Path, specs_dir: Path) -> None:
        self.repo_root = repo_root
        self.adtool_path = adtool_path
        self.output_dir = output_dir
        self.specs_dir = specs_dir

    def build(self, architecture_id: str, output_format: str = "md") -> ProcResult:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        if architecture_id == "_root":
            spec_path = self.specs_dir
        else:
            spec_path = self.specs_dir / architecture_id

        extension = "md" if output_format.lower() == "md" else "html"
        output_file = self.output_dir / f"AD_{architecture_id}.{extension}"

        cmd = [
            "python3",
            str(self.adtool_path),
            "build",
            str(spec_path),
            "--out",
            str(output_file),
        ]
        return run_command(cmd, cwd=self.repo_root)
