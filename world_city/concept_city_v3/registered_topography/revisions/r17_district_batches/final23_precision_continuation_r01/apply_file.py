"""Write one derived runtime scene and exact final-scene row ledger."""
import argparse,json,hashlib
from pathlib import Path
from .runtime_winding import bind_scene,apply_runtime

def run():
 p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('output');p.add_argument('ledger');args=p.parse_args();source=Path(args.source);out=Path(args.output);ledger=Path(args.ledger)
 if out.exists()or ledger.exists():raise ValueError('Refusing to overwrite scene or ledger')
 raw=source.read_bytes();scene=json.loads(raw);binding=bind_scene(scene,dict(path=str(source),sha256=hashlib.sha256(raw).hexdigest()));derived=apply_runtime(scene,binding);data=(json.dumps(derived,separators=(',',':'),allow_nan=False)+'\n').encode();binding['derived_scene']=dict(path=str(out),sha256=hashlib.sha256(data).hexdigest());binding['changed_surface_rows']=len(binding['rows']);binding['unchanged_non_surface_fields']=all(scene[k]==derived[k]for k in scene if k!='surfaces');out.parent.mkdir(parents=True,exist_ok=True);ledger.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(data);ledger.write_text(json.dumps(binding,separators=(',',':'),allow_nan=False)+'\n');print(binding['derived_scene'],flush=True)
if __name__=='__main__':run()
