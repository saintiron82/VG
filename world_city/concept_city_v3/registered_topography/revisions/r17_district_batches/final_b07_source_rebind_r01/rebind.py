import json
from pathlib import Path
from .. import author as a
from ..incident_risers_r01.solve import write
from ..final_profile_audit_r01.exact_clip import difference
HERE=Path(__file__).resolve().parent
OLD=a.HERE/'final_district_profiles_r05/BLOCK_007_R8_C001.json';SOURCE=a.CITY/'assemblies/ordinary/registered/district_fabric_r01/paired_contour_entry_refit_r05/source_candidates.json'
def minus(ps,masks):
 for m in masks:ps=[v for p in ps for v in difference(p,m)]
 return sum(a.geo.polygon_area(p)for p in ps)
d=json.loads(OLD.read_bytes());c=json.loads(SOURCE.read_bytes())['records'][0];old=d['candidate'];assert c['holding_id']==d['holding_id'];assert c['floor_y_m']==old['floor_y_m'];assert c['fixed_public_regions']==old['fixed_public_regions']
errors=[minus(c['profile_domain_polygons_xz_m'],old['profile_domain_polygons_xz_m']),minus(old['profile_domain_polygons_xz_m'],c['profile_domain_polygons_xz_m'])];assert max(errors)<1e-9
ref=lambda p:dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
out=dict(d,candidate=c,source=ref(SOURCE),source_rebind=dict(old_profile=ref(OLD),profile_domain_directional_difference_m2=errors,exact_public_regions_unchanged=True,triangle_geometry_sha256=a.canonical_sha(d['result']['triangles']),physical_profile_unchanged=True),court_fixed_regions=[dict(id=c['holding_id']+':FLAT_CORE:'+str(i),polygon_xz_m=p,plane_y_xz_m=[0,0,c['floor_y_m']])for i,p in enumerate(c['flat_owner_polygons_xz_m'])]);write(HERE/'BLOCK_007_R8_C001.json',out);print(ref(HERE/'BLOCK_007_R8_C001.json'))
