"""Rebuild the CleanCity file manifest after changing minecraft/ contents."""
import hashlib
import json
import re
import shutil
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / "games" / "cleancity"
SOURCE = GAME / "minecraft"
RAW_ROOT = "https://raw.githubusercontent.com/lumoung-mc/launcher-releases/main"


def main():
    details_path = ROOT / "details.json"
    details = json.loads(details_path.read_text(encoding="utf-8-sig"))
    game = next(game for game in details["games"] if game["id"] == "cleancity")
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){2}", game["version"]):
        raise ValueError("Invalid release version")
    files = []
    for source in sorted(SOURCE.rglob("*")):
        if not source.is_file():
            continue
        relative = source.relative_to(SOURCE).as_posix()
        # A personal Minecraft installation is never a distributable game pack.
        if relative != "options.txt" and not relative.startswith(("mods/", "config/", "resourcepacks/")):
            raise ValueError(f"Review this file before distributing it: {relative}")
        with source.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        # Published payloads never change at a given URL, even after a new release.
        immutable = GAME / "files" / digest / source.name
        if immutable.exists():
            with immutable.open("rb") as stream:
                if hashlib.file_digest(stream, "sha256").hexdigest() != digest:
                    raise ValueError(f"Immutable payload changed: {immutable}")
        else:
            immutable.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, immutable)
        files.append({
            "path": relative,
            "url": f"{RAW_ROOT}/{quote(immutable.relative_to(ROOT).as_posix(), safe='/')}",
            "size": source.stat().st_size,
            "sha256": digest,
            "mode": "install_if_missing" if relative == "options.txt" or relative.startswith("config/") else "managed",
        })
    if not files:
        raise ValueError("minecraft/ contains no game files")
    manifest = {
        "schema_version": 1,
        "game_id": game["id"],
        "version": game["version"],
        "minecraft_version": "26.2",
        "java_major_version": 25,
        "loader": {"type": "fabric", "version": "0.19.5"},
        "files": files,
    }
    text = json.dumps(manifest, ensure_ascii=False, indent=4) + "\n"
    versioned = GAME / "versions" / game["version"] / "manifest.json"
    if versioned.exists() and versioned.read_text(encoding="utf-8") != text:
        raise ValueError("This version already contains different files. Increment the game version.")
    versioned.parent.mkdir(parents=True, exist_ok=True)
    versioned.write_text(text, encoding="utf-8")
    # Compatibility for launchers still holding the former catalog URL.
    (GAME / "manifest.json").write_text(text, encoding="utf-8")
    game["manifest_url"] = f"{RAW_ROOT}/games/cleancity/versions/{game['version']}/manifest.json"
    details_path.write_text(json.dumps(details, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")
    print(f"Generated manifest: {len(files)} files, {sum(file['size'] for file in files):,} bytes")


if __name__ == "__main__":
    main()
