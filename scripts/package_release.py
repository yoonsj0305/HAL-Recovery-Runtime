"""Build the HAL Recovery Runtime v1.0.0 public PoC source release archive."""

from __future__ import annotations

from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RELEASE_VERSION = "1.0.0"
ARCHIVE_ROOT = "hal-recovery-runtime"
DEFAULT_OUTPUT = PROJECT_ROOT / "dist" / f"hal-recovery-runtime-v{RELEASE_VERSION}.zip"
INCLUDED_ROOT_FILES = (
    ".gitignore",
    "CHANGELOG.md",
    "CITATION.cff",
    "CONTRIBUTING.md",
    "LICENSE",
    "PUBLIC_POC_MANIFEST.json",
    "README.md",
    "SECURITY.md",
    "pyproject.toml",
)
INCLUDED_DIRECTORIES = ("docs", "examples", "samples", "src", "tests", "scripts")
EXCLUDED_PARTS = {"__pycache__", ".pytest_cache", ".venv", "dist", "build"}


def _is_excluded(relative_path: Path) -> bool:
    return any(
        part in EXCLUDED_PARTS or part.endswith(".egg-info")
        for part in relative_path.parts
    )


def _release_files() -> list[Path]:
    files = [PROJECT_ROOT / name for name in INCLUDED_ROOT_FILES]
    for directory in INCLUDED_DIRECTORIES:
        files.extend(path for path in (PROJECT_ROOT / directory).rglob("*") if path.is_file())
    return sorted(
        (path for path in files if not _is_excluded(path.relative_to(PROJECT_ROOT))),
        key=lambda path: path.relative_to(PROJECT_ROOT).as_posix(),
    )


def build_release_zip(output_path: str | Path = DEFAULT_OUTPUT) -> Path:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for source in _release_files():
            relative = source.relative_to(PROJECT_ROOT)
            archive_name = str(PurePosixPath(ARCHIVE_ROOT, relative.as_posix()))
            archive.write(source, archive_name)
    return output


def main() -> int:
    output = build_release_zip()
    print(f"Release archive written: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
