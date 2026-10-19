"""Derived r02 material-cache identity correction; frozen r01 bytes remain untouched."""
import copy,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
def load(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def canonical(d):return json.dumps(d,sort_keys=True,separators=(',',':'))
def build():
 src=HERE/'pack.json';old=load(src);frozen=load(HERE/'handoff.json')['pack_sha256'];assert sha(src)==frozen
 new=copy.deepcopy(old);changes=[]
 for p in new['add_instances']:
  overrides=p.get('palette_override',{});suffix=hashlib.sha256(canonical(overrides).encode()).hexdigest()[:12]
  if overrides:
   before=p['palette_id'];p['palette_id']=before+'_'+suffix
   changes.append(dict(id=p['id'],old_palette_id=before,new_palette_id=p['palette_id'],palette_override=overrides))
 seen={}
 for p in new['add_instances']:
  key=(p['asset_key'],p['palette_id']);value=canonical(p.get('palette_override',{}));assert key not in seen or seen[key]==value;seen[key]=value
 for a,b in zip(old['add_instances'],new['add_instances']):
  test=copy.deepcopy(b);test['palette_id']=a['palette_id'];assert test==a
 for key in old:
  if key!='add_instances':assert old[key]==new[key]
 out=HERE/'pack_r02.json';out.write_text(json.dumps(new,indent=2)+'\n')
 report=dict(schema='riverstone.port_market.palette_identity_repair.v1',status='PASS',source_pack=dict(path=str(src.relative_to(ROOT)),sha256=frozen),corrected_pack=dict(path=str(out.relative_to(ROOT)),sha256=sha(out)),changed_palette_ids=changes,geometry_and_poses_unchanged=True,palette_override_colors_unchanged=True,all_nonpalette_fields_identical=True,unique_asset_palette_pairs=len(seen),material_cache_collisions=0,original_pack_unchanged=sha(src)==frozen)
 (HERE/'palette_identity_r02.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':build()
