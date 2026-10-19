"""Read-only verification of the published file inventory."""
from pathlib import Path
import hashlib, json, sys
root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / "snapshot/file_manifest.json").read_text())
errors = []
for item in manifest["files"]:
    path = root / item["path"]
    if not path.is_file():
        errors.append(item["path"] + ": missing")
        continue
    data = path.read_bytes()
    if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
        errors.append(item["path"] + ": changed")
print(json.dumps({"files_checked": len(manifest["files"]), "errors": errors}, indent=2))
sys.exit(bool(errors))
