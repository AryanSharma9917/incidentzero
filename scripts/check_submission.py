"""Offline package integrity; release readiness is a separate explicit, evidence-gated check."""
import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_GATES = {"public_demo", "repository_public", "container_runtime", "live_nebius", "conditional_tavily",
                  "five_live_oom_runs", "final_live_video", "public_video_url", "devto_published", "team_confirmation", "devpost_submitted"}


def validate_package(root: Path = ROOT) -> list[str]:
    errors = []
    required = ["LICENSE", "README.md", "docs/architecture.md", "docs/safety.md", "docs/demo.md", "docs/development.md",
                "docs/assets/architecture.svg", "docs/assets/architecture.png", "docs/assets/rehearsal.webm",
                "docs/assets/capture-manifest.json", "docs/submission/article.md", "docs/submission/devpost.md",
                "docs/submission/readiness.json", "docs/submission/golden-path-results.json"]
    for name in required:
        if not (root / name).is_file():
            errors.append("Missing package file: " + name)
    if errors:
        return errors
    manifest = json.loads((root / "docs/assets/capture-manifest.json").read_text())
    if any(manifest.get(key) != "mocked" for key in ("reasoning", "research", "infrastructure")):
        errors.append("Rehearsal provenance must explicitly mark all external boundaries mocked")
    screenshots = manifest.get("screenshots", [])
    if not 6 <= len(screenshots) <= 8 or len({item["file"] for item in screenshots}) != len(screenshots):
        errors.append("Expected six to eight unique screenshots")
    for entry in screenshots:
        image = root / "docs/assets" / entry["file"]
        if not image.is_file():
            errors.append("Missing screenshot: " + entry["file"])
            continue
        data = image.read_bytes()
        if data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24:
            errors.append("Invalid PNG: " + entry["file"])
            continue
        width, height = struct.unpack(">II", data[16:24])
        if (width, height) != (entry["width"], entry["height"]) or width * 2 != height * 3:
            errors.append("Screenshot dimensions/provenance mismatch: " + entry["file"])
        if entry.get("provenance") != "mocked-ui-rehearsal":
            errors.append("Screenshot is missing rehearsal provenance: " + entry["file"])
    video = root / "docs/assets" / manifest["video"]
    if not 0 < manifest.get("video_duration_seconds", 0) < 180:
        errors.append("Verified rehearsal duration is missing or is not below three minutes")
    if hashlib.sha256(video.read_bytes()).hexdigest() != manifest.get("video_sha256"):
        errors.append("Video hash does not match inspected duration/provenance manifest")
    evidence = json.loads((root / "docs/submission/golden-path-results.json").read_text())
    if evidence.get("status") == "pending" and evidence.get("accepted_live_runs"):
        errors.append("Pending live acceptance cannot contain invented accepted runs")
    # Offline local Markdown targets only. External links and publication are separate gates.
    documents = [root / "README.md", *sorted((root / "docs").glob("*.md")), *sorted((root / "docs/submission").glob("*.md"))]
    for document in documents:
        for match in re.finditer(r"\]\(([^)]+)\)", document.read_text()):
            target = match.group(1).split("#", 1)[0]
            if not target or re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", target):
                continue
            if not (document.parent / target).exists():
                errors.append(f"Broken local link in {document.relative_to(root)}: {target}")
    return errors


def release_blockers(root: Path = ROOT) -> list[str]:
    readiness = json.loads((root / "docs/submission/readiness.json").read_text())
    gates = {item["id"]: item for item in readiness.get("gates", [])}
    blockers = ["Missing release gate: " + name for name in sorted(REQUIRED_GATES - gates.keys())]
    for name in sorted(REQUIRED_GATES & gates.keys()):
        gate = gates[name]
        if gate.get("status") != "passed" or not gate.get("evidence"):
            blockers.append("Unverified release gate: " + name)
    evidence = json.loads((root / "docs/submission/golden-path-results.json").read_text())
    runs = evidence.get("accepted_live_runs", [])
    if len(runs) != 5 or len({run.get("run_id") for run in runs}) != 5 or not all(
        run.get("passed") is True and run.get("mode") == "kubernetes" and run.get("status") == "verified" for run in runs
    ):
        blockers.append("Five distinct accepted live Kubernetes golden-path runs are not recorded")
    return blockers


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-ready", action="store_true")
    parser.add_argument("--inspect-video", metavar="FFMPEG", help="Inspect actual video and update only its duration/hash metadata")
    args = parser.parse_args()
    if args.inspect_video:
        path = ROOT / "docs/assets/capture-manifest.json"
        manifest = json.loads(path.read_text())
        video = ROOT / "docs/assets" / manifest["video"]
        result = subprocess.run([args.inspect_video, "-hide_banner", "-i", str(video)], capture_output=True, text=True, timeout=15)
        match = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
        if not match:
            parser.error("Could not inspect actual video duration")
        hours, minutes, seconds = map(float, match.groups())
        manifest["video_duration_seconds"] = round(hours * 3600 + minutes * 60 + seconds, 3)
        manifest["video_sha256"] = hashlib.sha256(video.read_bytes()).hexdigest()
        path.write_text(json.dumps(manifest, indent=2) + "\n")
    errors = validate_package()
    if args.release_ready:
        errors += release_blockers()
    if errors:
        print("\n".join("BLOCKED: " + message for message in errors))
        raise SystemExit(1)
    print("PASS: local package integrity" + (" and declared release evidence" if args.release_ready else "; live acceptance/publication gates are separate and remain pending"))


if __name__ == "__main__":
    main()
