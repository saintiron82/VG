"""Local output identity for the next atomic eighteen-holding batch."""
import json
from pathlib import Path
from .. import author as a
HERE=Path(__file__).resolve().parent
def write(name,data):
 p=HERE/name
 if p.exists():raise ValueError("Preserve "+str(p))
 p.write_text(json.dumps(data,separators=(",",":"))+"\n")
