# core/workspace.py
import os
import pathlib
from typing import List

def read_text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")

def ensure_in_workspace(rel_path: str, workspace_path: pathlib.Path) -> pathlib.Path:
    """
    Ensure a relative path resolves under workspace and cannot escape via '..'.
    """
    p = (workspace_path / rel_path).resolve()
    if not str(p).startswith(str(workspace_path) + os.sep):
        raise RuntimeError(f"Path escapes workspace: {rel_path}")
    return p

def repo_summary(workspace_path: pathlib.Path, max_files: int = 200) -> str:
    files = []
    for p in workspace_path.rglob("*"):
        if p.is_file() and p.suffix in (".py", ".md", ".txt", ".json", ".yaml", ".yml", ".tex"):
            files.append(str(p.relative_to(workspace_path)))
            if len(files) >= max_files:
                break
    return "\n".join(files)

def ensure_package_structure(project_root: str, workspace_path: pathlib.Path):
    """Ensure all package directories have __init__.py files"""
    project_path = workspace_path / project_root
    if project_path.exists():
        # Create root package __init__.py
        init_file = project_path / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# Package init file\n", encoding="utf-8")
            print(f"Created missing {project_root}/__init__.py")
        
        # Create subpackage __init__.py files
        for subdir in project_path.iterdir():
            if subdir.is_dir() and not subdir.name.startswith('.'):
                sub_init = subdir / "__init__.py"
                if not sub_init.exists():
                    sub_init.write_text("# Package init file\n", encoding="utf-8")
                    print(f"Created missing {project_root}/{subdir.name}/__init__.py")
