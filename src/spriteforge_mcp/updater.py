"""Read official release metadata. Package installation is deliberately not enabled yet."""

import platform

import httpx
from packaging.version import InvalidVersion, Version
from pydantic import BaseModel

from spriteforge_mcp import __version__

REPOSITORY = "https://github.com/katsushoe/SpriteForge"
RELEASES_API = "https://api.github.com/repos/katsushoe/SpriteForge/releases"
METADATA_LIMIT = 2_000_000


class ReleaseInfo(BaseModel):
    version: str
    name: str
    published_at: str | None
    prerelease: bool
    notes: str
    notes_url: str
    classification: str
    newer: bool
    package_name: str | None = None
    message: str
    download_available: bool = False
    apply_available: bool = False


def classify_release(release: dict, current: str = __version__) -> ReleaseInfo:
    tag = release["tag_name"]
    version = Version(tag.removeprefix("v"))
    name = f"SpriteForge-{tag.removeprefix('v')}-windows-x64.zip"
    assets = release.get("assets", [])

    def official_asset(asset: dict) -> bool:
        url = asset.get("browser_download_url", "")
        prefix = f"{REPOSITORY}/releases/download/{tag}/"
        return url.startswith(prefix) and url == prefix + asset.get("name", "")

    compatible = platform.system() == "Windows" and platform.machine().lower() in (
        "amd64",
        "x86_64",
    )
    package = next((a for a in assets if a.get("name") == name and official_asset(a)), None)
    manifest = next(
        (a for a in assets if a.get("name") == "SHA256SUMS.txt" and official_asset(a)), None
    )
    if not package or not compatible:
        classification = "metadata_only"
        message = (
            f"Release {tag} is available as release information, "
            "but it does not contain an installable package."
        )
    elif not manifest:
        classification = "unverified_package"
        message = "An update package exists, but its SHA-256 manifest is missing."
    else:
        classification = "package_available"
        message = (
            "Package metadata is available; secure staging/application is not implemented yet."
        )
    return ReleaseInfo(
        version=tag,
        name=release.get("name") or tag,
        published_at=release.get("published_at"),
        prerelease=bool(release.get("prerelease")),
        notes=release.get("body") or "",
        notes_url=f"{REPOSITORY}/releases",
        classification=classification,
        newer=version > Version(current),
        package_name=name if package and compatible else None,
        message=message,
    )


def check_updates(*, prereleases: bool = False) -> dict:
    with httpx.Client(timeout=10, follow_redirects=False) as client:
        with client.stream(
            "GET",
            RELEASES_API,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "SpriteForge-MCP",
            },
            params={"per_page": 100},
        ) as response:
            response.raise_for_status()
            data = bytearray()
            for chunk in response.iter_bytes():
                data.extend(chunk)
                if len(data) > METADATA_LIMIT:
                    raise ValueError("Release metadata exceeds the size limit")
    import json

    releases = json.loads(data)
    candidates = []
    for release in releases:
        if release.get("draft") or (release.get("prerelease") and not prereleases):
            continue
        try:
            version = Version(release["tag_name"].removeprefix("v"))
        except (InvalidVersion, KeyError):
            continue
        if version.is_prerelease and not prereleases:
            continue
        candidates.append((version, release))
    if not candidates:
        return {"state": "no_release", "message": "No matching published release found"}
    release = max(candidates, key=lambda item: item[0])[1]
    return {"state": "checked", **classify_release(release).model_dump()}
