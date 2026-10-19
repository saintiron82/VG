"""Full-width private dogleg to the actual sealed +15.6 water junction."""
import json,time
from pathlib import Path
from .. import author as a
from ..public_owner_completion_r05.solve import solve
from ..incident_risers_r01.solve import write
HERE=Path(__file__).resolve().parent
SOURCE=a.CITY/'assemblies/ordinary/registered/district_fabric_r01/b05_native_junction_entry_r04/source_candidates.json'
PUBLIC=a.CITY/'registered_topography/revisions/public_corridors_r18/north_junction_transition_r01/c006_public_planes.json'
def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def run():
 c=json.loads(SOURCE.read_bytes())['candidates'][0];pub=json.loads(PUBLIC.read_bytes());public=pub['public_overlap_records'];h=next(x for x in json.loads((a.HERE/'coherent_batch20_r01/effective_source_layout_r03.json').read_bytes())['holdings']if x['id']==c['holding_id']);flat=[dict(id=h['id']+':COURT_DATUM',polygon_xz_m=h['holding_polygon_xz_m'],plane_y_xz_m=[0,0,h['floor_y_m']])];union=a.common.disjoint_union(c['polygons_xz_m']);domains=a.common.subtract(union,[r['polygon_xz_m']for r in public]);start=time.monotonic();result=solve(domains,flat+public,lambda p:c['floor_y_m'],pitch=.5,limit=.12,seam_points=[p for r in flat+public for p in r['polygon_xz_m']]);d=dict(holding_id=c['holding_id'],candidate_index=0,candidate=c,source=ref(SOURCE),public_authority=ref(PUBLIC),private_domain_polygons_xz_m=domains,public_fixed_regions=public,court_fixed_regions=flat,result=result,elapsed_s=time.monotonic()-start,grade_limit=.12,activation=False,route_policy='The full 2 m dogleg replaces the obsolete long loop. Only its true private length supplies rise; existing water planes remain fixed.');p=HERE/'BLOCK_005_R8_C006.json';write(p,d);print(ref(p),result['status'],result.get('maximum_gradient'),flush=True)
if __name__=='__main__':run()
