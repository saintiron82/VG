"""Deploy the canonical player into the standalone preview's Godot resource root."""
from pathlib import Path
import argparse,hashlib
SOURCE=Path(__file__).resolve().parent/'TransformTracks.gd'
TARGET=SOURCE.parent.parent/'preview/AnimationTracks.gd'
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    if args.check:
        if not TARGET.exists() or SOURCE.read_bytes()!=TARGET.read_bytes():raise SystemExit('Runtime drift: run animation/sync_runtime.py')
    else:TARGET.write_bytes(SOURCE.read_bytes())
    print('Canonical/runtime SHA256',hashlib.sha256(SOURCE.read_bytes()).hexdigest())
