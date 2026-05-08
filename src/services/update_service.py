from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from src.version import APP_VERSION, GITHUB_LATEST_RELEASE_API, GITHUB_RELEASES_URL


@dataclass(frozen=True)
class UpdateCheckResult:
    update_available: bool
    current_version: str
    latest_version: str | None
    release_url: str | None
    download_url: str | None
    error: str | None = None


def _clean_version(version: str) -> str:
    value = version.strip()
    if value.lower().startswith("v"):
        value = value[1:]
    return value


def _version_parts(version: str) -> tuple[int, ...] | None:
    clean = _clean_version(version)
    clean = clean.split("+", 1)[0].split("-", 1)[0]
    if not clean:
        return None

    parts: list[int] = []
    for raw_part in clean.split("."):
        if not raw_part.isdigit():
            return None
        parts.append(int(raw_part))
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def is_newer_version(latest_version: str, current_version: str = APP_VERSION) -> bool:
    latest_parts = _version_parts(latest_version)
    current_parts = _version_parts(current_version)
    if latest_parts is None or current_parts is None:
        return False
    return latest_parts > current_parts


def _asset_score(asset_name: str) -> int:
    name = asset_name.lower()
    score = 0
    if "windows" in name:
        score += 40
    if "win" in name:
        score += 25
    if name.endswith(".exe") or ".exe" in name:
        score += 20
    if name.endswith(".zip") or ".zip" in name:
        score += 15
    return score


def _select_download_url(assets: Any) -> str | None:
    if not isinstance(assets, list):
        return None

    candidates: list[tuple[int, str]] = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        name = str(asset.get("name", ""))
        url = asset.get("browser_download_url")
        if not isinstance(url, str) or not url:
            continue
        score = _asset_score(name)
        if score > 0:
            candidates.append((score, url))

    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def check_for_update(timeout_seconds: float = 4.0) -> UpdateCheckResult:
    current_version = APP_VERSION
    request = urllib.request.Request(
        GITHUB_LATEST_RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "TetrisUpdateChecker",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw_payload = response.read(256 * 1024)
    except (OSError, urllib.error.URLError, TimeoutError) as exc:
        return UpdateCheckResult(False, current_version, None, None, None, exc.__class__.__name__)

    try:
        payload = json.loads(raw_payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        return UpdateCheckResult(False, current_version, None, None, None, exc.__class__.__name__)

    if not isinstance(payload, dict):
        return UpdateCheckResult(False, current_version, None, None, None, "InvalidReleaseResponse")

    latest_tag = payload.get("tag_name")
    if not isinstance(latest_tag, str) or not latest_tag.strip():
        return UpdateCheckResult(False, current_version, None, None, None, "MissingReleaseTag")

    latest_version = _clean_version(latest_tag)
    if _version_parts(latest_version) is None:
        return UpdateCheckResult(False, current_version, latest_version, GITHUB_RELEASES_URL, None, "MalformedReleaseTag")

    release_url = payload.get("html_url")
    if not isinstance(release_url, str) or not release_url:
        release_url = GITHUB_RELEASES_URL

    download_url = _select_download_url(payload.get("assets")) or release_url
    return UpdateCheckResult(
        update_available=is_newer_version(latest_version, current_version),
        current_version=current_version,
        latest_version=latest_version,
        release_url=release_url,
        download_url=download_url,
    )


class BackgroundUpdateChecker:
    def __init__(self, timeout_seconds: float = 4.0) -> None:
        self.timeout_seconds = timeout_seconds
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._result: UpdateCheckResult | None = None
        self._checking = False

    def start(self, *, force: bool = False) -> bool:
        with self._lock:
            if self._checking:
                return False
            if self._result is not None and not force:
                return False
            if force:
                self._result = None
            self._checking = True
            self._thread = threading.Thread(target=self._run, name="tetris-update-check", daemon=True)
            self._thread.start()
            return True

    def _run(self) -> None:
        result = check_for_update(self.timeout_seconds)
        if result.error:
            print(f"Update check failed: {result.error}")
        with self._lock:
            self._result = result
            self._checking = False

    def is_checking(self) -> bool:
        with self._lock:
            return self._checking

    def result(self) -> UpdateCheckResult | None:
        with self._lock:
            return self._result

    def consume_result(self) -> UpdateCheckResult | None:
        with self._lock:
            result = self._result
            self._result = None
            return result
