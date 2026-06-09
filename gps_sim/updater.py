"""GitHub Releases based updater for the packaged Windows application."""

from __future__ import annotations

import json
import os
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
RELEASES_API_URL = (
    f"https://api.github.com/repos/{REPOSITORY}/releases/latest"
)


@dataclass(frozen=True)
class Release:
    version: str
    download_url: str
    page_url: str
    notes: str


def is_packaged() -> bool:
    return bool(getattr(sys, "frozen", False))


def _version_parts(version: str) -> tuple[int, ...]:
    clean = version.strip().lower().removeprefix("v").split("-", 1)[0]
    return tuple(int(part) for part in clean.split("."))


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

    asset = next(
        (item for item in payload.get("assets", []) if item.get("name") == EXECUTABLE_ASSET),
        None,
    )
    if not asset:
        return None

    version = str(payload.get("tag_name", "")).removeprefix("v")
    if not version or _version_parts(version) <= _version_parts(current_version):
        return None
    return Release(
        version=version,
        download_url=asset["browser_download_url"],
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
