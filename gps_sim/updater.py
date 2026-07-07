"""GitHub Releases based updater for the packaged Windows application."""

from __future__ import annotations

import json
import os
import hashlib
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


CURRENT_VERSION = "1.0.0"
REPOSITORY = "omni-gh549/GPS-Learning-Studio"
EXECUTABLE_ASSET = "GPS-Learning-Studio.exe"
CHECKSUM_ASSET = f"{EXECUTABLE_ASSET}.sha256"
RELEASES_API_URL = (
    f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
)


@dataclass(frozen=True)
class Release:
    version: str
    download_url: str
    checksum_url: str
    page_url: str
    notes: str


def is_packaged() -> bool:
    return bool(getattr(sys, "frozen", False))


def _version_parts(version: str) -> tuple[int, ...]:
    clean = version.strip().lower().removeprefix("v").split("-", 1)[0]
    return tuple(int(part) for part in clean.split("."))


def _asset_named(payload: dict, name: str) -> dict | None:
    return next(
        (item for item in payload.get("assets", []) if item.get("name") == name),
        None,
    )


def parse_sha256_checksum(content: str) -> str:
    first_line = next(
        (line.strip() for line in content.splitlines() if line.strip()),
        "",
    )
    checksum = first_line.split()[0] if first_line else ""
    if len(checksum) != 64 or any(character not in "0123456789abcdefABCDEF" for character in checksum):
        raise ValueError("Release checksum is not a valid SHA-256 digest.")
    return checksum.lower()


def calculate_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def verify_download_checksum(downloaded_executable: Path, expected_sha256: str) -> None:
    actual_sha256 = calculate_sha256(downloaded_executable)
    if actual_sha256 != expected_sha256.lower():
        raise ValueError(
            "Downloaded update failed SHA-256 verification; the executable was not replaced."
        )


def find_update(
    timeout: float = 8.0,
    api_url: str = RELEASES_API_URL,
    current_version: str = CURRENT_VERSION,
) -> Release | None:
    request = urllib.request.Request(
        api_url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"GPS-Learning-Studio/{current_version}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise

    asset = _asset_named(payload, EXECUTABLE_ASSET)
    checksum_asset = _asset_named(payload, CHECKSUM_ASSET)
    if not asset or not checksum_asset:
        return None

    version = str(payload.get("tag_name", "")).removeprefix("v")
    if not version or _version_parts(version) <= _version_parts(current_version):
        return None
    return Release(
        version=version,
        download_url=asset["browser_download_url"],
        checksum_url=checksum_asset["browser_download_url"],
        page_url=payload.get("html_url", ""),
        notes=payload.get("body", ""),
    )


def download_update(
    release: Release,
    destination: Path | None = None,
    timeout: float = 60,
) -> Path:
    download_path = destination or Path(tempfile.gettempdir()) / (
        f"GPS-Learning-Studio-{release.version}.download.exe"
    )
    request = urllib.request.Request(
        release.download_url,
        headers={"User-Agent": f"GPS-Learning-Studio/{CURRENT_VERSION}"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        with download_path.open("wb") as destination:
            while chunk := response.read(1024 * 1024):
                destination.write(chunk)
    checksum_request = urllib.request.Request(
        release.checksum_url,
        headers={"User-Agent": f"GPS-Learning-Studio/{CURRENT_VERSION}"},
    )
    try:
        with urllib.request.urlopen(checksum_request, timeout=timeout) as response:
            expected_sha256 = parse_sha256_checksum(response.read().decode("utf-8"))
        verify_download_checksum(download_path, expected_sha256)
    except Exception:
        download_path.unlink(missing_ok=True)
        raise
    return download_path


def create_update_script(
    downloaded_executable: Path,
    current_executable: Path,
    script_path: Path | None = None,
    restart: bool = True,
) -> Path:
    updater_script = script_path or (
        Path(tempfile.gettempdir()) / "gps-learning-studio-update.cmd"
    )
    restart_command = f'start "" "{current_executable}"\n' if restart else ""

    updater_script.write_text(
        "@echo off\n"
        "setlocal\n"
        "timeout /t 2 /nobreak >nul\n"
        f':replace\nmove /y "{downloaded_executable}" "{current_executable}" >nul 2>&1\n'
        "if errorlevel 1 (\n"
        "  timeout /t 1 /nobreak >nul\n"
        "  goto replace\n"
        ")\n"
        f"{restart_command}"
        'start "" /b cmd.exe /c "timeout /t 1 /nobreak >nul & del /q \\"%~f0\\""\n'
        "exit /b 0\n",
        encoding="ascii",
    )
    return updater_script


def download_and_install(release: Release) -> None:
    if not is_packaged():
        raise RuntimeError("Automatic installation is available only in the packaged app.")

    current_executable = Path(sys.executable).resolve()
    download_path = download_update(release)
    updater_script = create_update_script(download_path, current_executable)
    subprocess.Popen(
        ["cmd.exe", "/c", str(updater_script)],
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        close_fds=True,
    )
    os._exit(0)
