from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import List


@dataclass
class ProcResult:
    command: List[str]
    stdout: str
    stderr: str
    returncode: int

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def run_command(command: List[str], cwd: Path) -> ProcResult:
    proc = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        capture_output=True,
        check=False,
    )
    return ProcResult(
        command=command,
        stdout=proc.stdout,
        stderr=proc.stderr,
        returncode=proc.returncode,
    )
