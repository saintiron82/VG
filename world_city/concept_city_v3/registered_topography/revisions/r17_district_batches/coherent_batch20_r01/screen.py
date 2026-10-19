"""Immutable output writer for the twenty-holding continuation."""
import json
from pathlib import Path
from .. import author as a
HERE = Path(__file__).resolve().parent

def write(name, data):
    path = HERE / name
    if path.exists():
        raise ValueError('Preserve existing candidate: ' + str(path))
    path.write_text(json.dumps(data, separators=(',', ':'), allow_nan=False) + '\n')
