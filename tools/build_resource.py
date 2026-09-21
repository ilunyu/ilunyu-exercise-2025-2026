#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, tempfile, zipfile
from pathlib import Path
from typing import Any
ROOT = Path(__file__).resolve().parents[1]
def validate_exercise(path: Path, item: dict[str, Any]) -> list[str]:
    required = ("id", "title", "year", "source", "type", "grade", "number", "score", "month", "question", "answer")
    return [f"{path.name}: missing {key}" for key in required if key not in item]
def read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"));
    if not isinstance(value, dict): raise ValueError(f"{path}: root must be an object")
    return value
def write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")
def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""): h.update(block)
    return h.hexdigest()
def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--output", type=Path, default=ROOT / "dist" / "resource.ilunyupack"); parser.add_argument("--release-output", type=Path); args = parser.parse_args(); config = read(ROOT / "resource.json"); exercises = []
    for path in sorted(ROOT.glob("*.json")):
        if path.name == "resource.json": continue
        item = read(path); errors = validate_exercise(path, item)
        if errors: raise ValueError("\n".join(errors))
        exercises.append(item)
    if not exercises: raise ValueError("no exercise JSON files found")
    with tempfile.TemporaryDirectory(prefix="ilunyu-package-") as directory:
        build, content = Path(directory), Path(directory) / "content"; summary = lambda item: {key: item[key] for key in ("id", "title", "year", "source", "type", "grade", "number", "score", "month") if key in item}
        write(content / "index.json", {"formatVersion": 2, "exercises": [summary(item) for item in exercises]}); write(content / "search.json", {"formatVersion": 2, "exercises": [{**summary(item), "question": item.get("question", [])} for item in exercises]})
        for item in exercises: write(content / "items" / f"{item['id']}.json", item)
        files = {path.relative_to(build).as_posix(): f"sha256:{digest(path)}" for path in sorted(content.rglob("*.json"))}; manifest = {"packageFormat": 1, "contentSchema": 1, "packageId": config["packageId"], "kind": config["kind"], "name": config["name"], "versionName": config["versionName"], "versionCode": config["versionCode"], "minAppVersionCode": config["minAppVersionCode"], "sourceRepository": config.get("sourceRepository", ""), "license": config.get("license", ""), "files": files}; write(build / "manifest.json", manifest); args.output.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for path in sorted(build.rglob("*")):
                if path.is_file(): archive.write(path, path.relative_to(build).as_posix())
    result = {"packageId": manifest["packageId"], "kind": manifest["kind"], "name": manifest["name"], "versionName": manifest["versionName"], "versionCode": manifest["versionCode"], "minAppVersionCode": manifest["minAppVersionCode"], "size": args.output.stat().st_size, "sha256": digest(args.output), "sourceRepository": manifest["sourceRepository"]}; write(args.release_output or args.output.parent / "release.json", result); print(f"Built {args.output}: {result['size']} bytes, sha256 {result['sha256']}")
if __name__ == "__main__": main()
