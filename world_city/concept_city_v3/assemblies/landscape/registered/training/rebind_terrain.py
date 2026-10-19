"""Rebind a changed terrain module only when all training-owned heights stay exact."""
import json,copy
from . import author as t
from world_city.concept_city_v3.assemblies.property.registered import author as a

def run():
 path=t.OUT/'source_pack.json';p=json.loads(path.read_text());data=t.source_inputs();changed=[k for k in p['sources'] if p['sources'][k]!=data['sources'][k]];assert changed==['active_terrain_author'],changed
 oldhash=a.file_sha(path);gate,surface=t.make_gate(data['plan'],p['source_space']['polygon_xz_m']);assert a.sha(gate)==a.sha(p['gate']);assert a.sha(surface)==a.sha(p['external_surface']),'Changed gate/profile requires a real new design revision'
 checks=[]
 for row in p['native_support_samples']:
  for old in row['samples']:
   actual=t.terrain.land_height_at(*old['point_xz_m']);delta=abs(actual-old['terrain_y_m']);checks.append(dict(placement_id=row['placement_id'],point_xz_m=old['point_xz_m'],height_delta_m=delta));assert delta<1e-9
 before=t.HERE/('source_before_terrain_'+p['sources']['active_terrain_author']['sha256'][:12]+'.json');before.write_bytes(path.read_bytes());oldsource=copy.deepcopy(p['sources']['active_terrain_author']);p['sources']=data['sources'];t.write(path,p)
 report=dict(schema='riverstone.training.terrain_rebind.v1',prior_source_sha256=oldhash,new_source_sha256=a.file_sha(path),prior_terrain=oldsource,new_terrain=p['sources']['active_terrain_author'],actual_support_checks=checks,gate_identical=True,all_external_triangle_and_support_records_identical=True,geometry_changed=False);t.write(t.HERE/'terrain_rebind_report.json',report);print(json.dumps(dict(status='metadata_rebound_with_exact_geometry_and_support_proof',source_sha256=a.file_sha(path),terrain_sha256=p['sources']['active_terrain_author']['sha256'])),flush=True)
if __name__=='__main__':run()
