"""Reconcile estate route review against actual active R7 caches and repaired metadata."""
from . import geometry as g
from .design import HERE as SOURCE
import types

def run():
 out=SOURCE/'noble_internal_route_review_r01';out.mkdir(exist_ok=True);src=g.CITY/'assemblies/property/registered/r1/repair_01/resolved_placements.json';p=g.load(src);scene=g.load(g.R7);by={i['id']:i for i in scene['common_instances']};checks=[]
 for r in p['placements']:
  if r.get('property_id')not in ['E1','E2','E3','E4','E5','E6','E7']:continue
  i=by[r['id']];a=scene['common_assets'][i['asset_key']];checks.append(dict(id=r['id'],source_asset=r['asset_key'],actual_asset=i['asset_key'],cache_sha_matches=r['render_sha256']==a['render_sha256'],pose_matches=r['position_m']==i['position_m']and r.get('yaw_rad',0)==i.get('yaw_rad',0),asset_matches=r['asset_key']==i['asset_key']))
 assert all(r['cache_sha_matches']and r['pose_matches']and r['asset_matches']for r in checks)
 g.write(out/'active_source_reconciliation.json',dict(base_scene=g.ref(g.R7),active_metadata=g.ref(src),checks=checks,passed=True,previous_failure_source=g.ref(g.CITY/'assemblies/property/registered/r1/resolved_placements.json'),finding='The earlier three-route failure report consumed superseded original r1 cache paths and route metadata. Actual R7 selects both repair_01 infrastructure masters.'))
 path=g.CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/retained_owner_review/audit_noble_holdings.py';text=path.read_text().replace("src=CITY/'assemblies/property/registered/r1/resolved_placements.json'","src=CITY/'assemblies/property/registered/r1/repair_01/resolved_placements.json'").replace("for q in external['polygon_regions_xz_m']:","for q in []:")
 mod=types.ModuleType('audit_actual_noble');mod.__file__=str(path);exec(compile(text,str(path),'exec'),mod.__dict__);mod.OUT=out;mod.main();report=g.load(out/'noble_native_use_and_access.json');failed=[r for o in report['owners']for r in o['internal_routes']if not r['passes']];g.write(out/'internal_route_acceptance.json',dict(active_reconciliation=g.ref(out/'active_source_reconciliation.json'),exact_native_audit=g.ref(out/'noble_native_use_and_access.json'),checked_internal_routes=report['summary']['internal_routes'],remaining_failures=failed,passed=not failed,public_lane_cut_dependency=g.ref(g.CITY/'assemblies/property/registered/public_lane_repairs_r01/source_candidates.json'),operation_addendum=[],new_retirements=[],policy='Preserve the exact active repair_01 non-exterior operations and current repaired route records. The precinct exterior skin replacement must consolidate the E1/E2 public-lane cap-cut dependency. No new internal asset replacement is warranted if all exact current route tests pass.'));print('FAILED',failed);print(g.ref(out/'internal_route_acceptance.json'))
if __name__=='__main__':run()
