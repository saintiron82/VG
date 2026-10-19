"""Append a sealed producer handoff to a staging binding, by exact source ref."""
import json,pathlib,hashlib,sys
ROOT=next(p for p in pathlib.Path(__file__).resolve().parents if(p/'voxel_character').is_dir())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(ref):
 p=ROOT/ref['path'];assert sha(p)==ref['sha256'],ref['path'];return json.loads(p.read_bytes())
def main(binding_path,handoff_path,output_path):
 p=ROOT/binding_path;h=ROOT/handoff_path;out=ROOT/output_path;assert not out.exists();b=json.loads(p.read_bytes());j=json.loads(h.read_bytes())
 for row in j['producer_replacements']:
  old=row['source'];new=row['replacement'];matches=[i for i,r in enumerate(b['patches'])if r==old];assert len(matches)==1,old;load(new);b['patches'][matches[0]]=new
 b['evidence'].append(dict(path=str(h.relative_to(ROOT)),sha256=sha(h)));freeze=h.parent/'freeze_manifest.json'
 if freeze.exists():b['evidence'].append(dict(path=str(freeze.relative_to(ROOT)),sha256=sha(freeze)))
 b['source_stage']='Final exterior staging with exact source-preserving local corrections; combined visual and runtime acceptance remains pending.'
 out.write_text(json.dumps(b,indent=2)+'\n');print(json.dumps(dict(path=str(out.relative_to(ROOT)),sha256=sha(out),patches=len(b['patches']),packs=len(b['packs']))))
if __name__=='__main__':main(*sys.argv[1:])
