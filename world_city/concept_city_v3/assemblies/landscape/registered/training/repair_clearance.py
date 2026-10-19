"""Conservative half-metre sampling envelopes; native assets and poses unchanged."""
import json,math,copy
from . import author as t
from world_city.concept_city_v3.assemblies.property.registered import author as a

def run():
 path=t.OUT/'source_pack.json';p=json.loads(path.read_text());oldhash=a.file_sha(path);ledger=[]
 for ins in p['placements']:
  if ins.get('entrances'):continue
  b=ins['local_bounds'];lo=[math.floor(x/.5)*.5 for x in b['min']];hi=[math.ceil(x/.5)*.5 for x in b['max']];center=a.xform([(lo[0]+hi[0])/2,(lo[2]+hi[2])/2],[ins['position_m'][0],ins['position_m'][2]],ins['yaw_rad']);foot=a.rect(center,hi[0]-lo[0],hi[2]-lo[2],ins['yaw_rad'])
  if a.sha(foot)!=a.sha(ins['footprint_xz_m']):ledger.append(dict(id=ins['id'],old_footprint_xz_m=ins['footprint_xz_m'],new_footprint_xz_m=foot,reason='Conservative .5 m source grid rounding covers the actual center-sampled native cells. Pose, master and cache unchanged.'))
  ins['footprint_xz_m']=foot
  assert a.contained(foot,p['source_space']['polygon_xz_m']) and not a.overlap(foot,t.CORE)
  assert not any(a.overlap(foot,q) for r in p['internal_routes'] for q in r['ribbon_polygons_xz_m'])
 (t.HERE/'source_before_sampled_clearance.json').write_bytes(path.read_bytes());t.write(path,p);t.write(t.HERE/'sampling_clearance_ledger.json',dict(prior_source_sha256=oldhash,new_source_sha256=a.file_sha(path),changes=ledger,geometry_changed=False,native_poses_changed=False));print('Clearance records repaired:',len(ledger))
if __name__=='__main__':run()
