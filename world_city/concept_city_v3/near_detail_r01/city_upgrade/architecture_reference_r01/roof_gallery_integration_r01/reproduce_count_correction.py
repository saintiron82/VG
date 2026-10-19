"""Reproduce metadata-only halo count correction without rewriting geometry JSON."""
from pathlib import Path
import json,gzip,hashlib,re
P=Path(__file__).resolve().parent
record=json.loads((P/'count_correction.json').read_text())
src=(P/'gallery_repaired.render.json.gz').read_bytes()
assert hashlib.sha256(src).hexdigest()==record['original_candidate_sha256']
raw=gzip.decompress(src)
old=str(record['before_incorrect_count']).encode();new=str(record['corrected_virtual_native_count']).encode()
raw,n=re.subn(rb'("cell_count"\s*:\s*)'+old,lambda m:m.group(1)+new,raw,count=1);assert n==1
metadata={k:v for k,v in record.items() if k not in ['corrected_render_sha256','corrected_render_path','render_bytes']}
raw=raw.rstrip();assert raw.endswith(b'}')
raw=raw[:-1]+b',"count_metadata_correction":'+json.dumps(metadata,separators=(',',':')).encode()+b'}'
encoded=gzip.compress(raw,compresslevel=9,mtime=0)
expected=record['corrected_render_sha256']
actual=hashlib.sha256(encoded).hexdigest()
assert actual==expected,(actual,expected)
output=P/'gallery_repaired_count_corrected.render.json.gz'
if output.exists():assert output.read_bytes()==encoded
else:output.write_bytes(encoded)
print('exact metadata correction verified',actual)
