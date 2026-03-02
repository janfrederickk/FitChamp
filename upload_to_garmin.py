import argparse
import os
import sys
from pathlib import Path

from garminconnect import Garmin


def _resolve_fit_path(cli_value: str | None) -> Path:
    env_value = os.getenv("FIT_FILE_PATH")
    if cli_value:
        candidate = Path(cli_value)
        if candidate.is_file():
            return candidate
        raise FileNotFoundError(f"FIT file not found at: {candidate}")

    if env_value:
        candidate = Path(env_value)
        if candidate.is_file():
            return candidate
        raise FileNotFoundError(f"FIT file not found at FIT_FILE_PATH={candidate}")

    # Common filenames used by this repo
    for name in ("Ringen_Training.fit", "mma_training_activity.fit"):
        candidate = Path(name)
        if candidate.is_file():
            return candidate

    # Fallback: find the newest .fit file in the repo (avoid build dirs)
    ignore_dirs = {"bin", "obj", ".git"}
    fit_files: list[Path] = []
    for p in Path(".").rglob("*.fit"):
        if any(part in ignore_dirs for part in p.parts):
            continue
        if p.is_file():
            fit_files.append(p)

    if fit_files:
        return max(fit_files, key=lambda p: p.stat().st_mtime)

    raise FileNotFoundError(
        "No .fit file found. Provide one as an argument, or set FIT_FILE_PATH, "
        "or run the generator step first."
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Upload a .fit activity to Garmin Connect.")
    parser.add_argument(
        "fit_file",
        nargs="?",
        help="Path to a .fit file (optional). If omitted, uses FIT_FILE_PATH or auto-detects.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve the FIT path and print it without uploading.",
    )
    args = parser.parse_args()

    fit_path = _resolve_fit_path(args.fit_file)
    if args.dry_run:
        print(str(fit_path))
        return 0

    email = os.getenv("GARMIN_USER")
    password = os.getenv("GARMIN_PASS")
    if not email or not password:
        raise ValueError("GARMIN_USER and GARMIN_PASS must be set")

    client = Garmin(email, password)
    client.login()

    client.upload_activity(str(fit_path))

    print(f"✅ Activity uploaded: {fit_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
