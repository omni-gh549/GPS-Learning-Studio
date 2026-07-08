from __future__ import annotations

import json
import hashlib
import subprocess
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from gps_sim.updater import create_update_script, download_update, find_update


NEW_EXECUTABLE = b"MZ-test-updated-executable"
NEW_EXECUTABLE_SHA256 = hashlib.sha256(NEW_EXECUTABLE).hexdigest()


class UpdateServer(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/releases/latest":
            body = json.dumps(
                {
                    "tag_name": "v1.1.0",
                    "html_url": f"http://127.0.0.1:{self.server.server_port}/release",
                    "body": "Integration test release",
                    "assets": [
                        {
                            "name": "GPS-Learning-Studio.exe",
                            "browser_download_url": (
                                f"http://127.0.0.1:{self.server.server_port}/"
                                "GPS-Learning-Studio.exe"
                            ),
                        },
                        {
                            "name": "GPS-Learning-Studio.exe.sha256",
                            "browser_download_url": (
                                f"http://127.0.0.1:{self.server.server_port}/"
                                "GPS-Learning-Studio.exe.sha256"
                            ),
                        }
                    ],
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
        elif self.path == "/releases/no-checksum":
            body = json.dumps(
                {
                    "tag_name": "v1.1.0",
                    "html_url": f"http://127.0.0.1:{self.server.server_port}/release",
                    "body": "Release without a checksum",
                    "assets": [
                        {
                            "name": "GPS-Learning-Studio.exe",
                            "browser_download_url": (
                                f"http://127.0.0.1:{self.server.server_port}/"
                                "GPS-Learning-Studio.exe"
                            ),
                        }
                    ],
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
        elif self.path == "/GPS-Learning-Studio.exe":
            body = NEW_EXECUTABLE
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
        elif self.path == "/GPS-Learning-Studio.exe.sha256":
            body = f"{NEW_EXECUTABLE_SHA256}  GPS-Learning-Studio.exe\n".encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
        elif self.path == "/bad-checksum.sha256":
            body = ("0" * 64 + "  GPS-Learning-Studio.exe\n").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
        else:
            body = b'{"message":"Not Found"}'
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format: str, *_args) -> None:
        pass


class UpdaterIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), UpdateServer)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()

    def test_missing_latest_release_means_no_update(self) -> None:
        self.assertIsNone(
            find_update(api_url=f"{self.base_url}/missing", current_version="1.0.0")
        )

    def test_release_without_checksum_is_not_installable(self) -> None:
        self.assertIsNone(
            find_update(
                api_url=f"{self.base_url}/releases/no-checksum",
                current_version="1.0.0",
            )
        )

    def test_download_and_replace_executable(self) -> None:
        release = find_update(
            api_url=f"{self.base_url}/releases/latest",
            current_version="1.0.0",
        )
        self.assertIsNotNone(release)
        self.assertEqual("Integration test release", release.notes.summary)

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            current = root / "GPS-Learning-Studio.exe"
            current.write_bytes(b"MZ-test-old-executable")
            downloaded = download_update(release, root / "update.download.exe")
            script = create_update_script(
                downloaded,
                current,
                root / "apply-update.cmd",
                restart=False,
            )
            subprocess.run(
                ["cmd.exe", "/c", str(script)],
                check=True,
                timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            self.assertEqual(current.read_bytes(), NEW_EXECUTABLE)
            self.assertFalse(downloaded.exists())

    def test_checksum_mismatch_rejects_download(self) -> None:
        release = find_update(
            api_url=f"{self.base_url}/releases/latest",
            current_version="1.0.0",
        )
        self.assertIsNotNone(release)
        release = release.__class__(
            version=release.version,
            download_url=release.download_url,
            checksum_url=f"{self.base_url}/bad-checksum.sha256",
            page_url=release.page_url,
            notes=release.notes,
        )

        with tempfile.TemporaryDirectory() as directory:
            download_path = Path(directory) / "update.download.exe"
            with self.assertRaisesRegex(ValueError, "SHA-256 verification"):
                download_update(release, download_path)
            self.assertFalse(download_path.exists())


if __name__ == "__main__":
    unittest.main()
