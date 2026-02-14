from __future__ import annotations

from pathlib import Path
from typing import List

from .process import ProcResult, run_command


class GitService:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def branches(self) -> ProcResult:
        return run_command(["git", "branch", "--format=%(refname:short)"], cwd=self.repo_root)

    def checkout(self, branch: str) -> ProcResult:
        return run_command(["git", "checkout", branch], cwd=self.repo_root)

    def create_branch(self, branch: str, start_point: str | None = None) -> ProcResult:
        cmd: List[str] = ["git", "checkout", "-b", branch]
        if start_point:
            cmd.append(start_point)
        return run_command(cmd, cwd=self.repo_root)

    def delete_branch(self, branch: str) -> ProcResult:
        return run_command(["git", "branch", "-D", branch], cwd=self.repo_root)

    def commit(self, message: str, add_all: bool = True) -> ProcResult:
        if add_all:
            add_res = run_command(["git", "add", "-A"], cwd=self.repo_root)
            if not add_res.ok:
                return add_res
        return run_command(["git", "commit", "-m", message], cwd=self.repo_root)

    def push(self, remote: str = "origin", branch: str | None = None) -> ProcResult:
        cmd = ["git", "push", remote]
        if branch:
            cmd.append(branch)
        return run_command(cmd, cwd=self.repo_root)
