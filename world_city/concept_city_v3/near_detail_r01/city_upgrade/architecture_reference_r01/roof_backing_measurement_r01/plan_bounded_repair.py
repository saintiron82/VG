#!/usr/bin/env python3
"""Read-only operation AABB arithmetic for a proposed isolated-instance repair."""
import os
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import resource
resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,)*2);resource.setrlimit(resource.RLIMIT_CPU,(30,)*2)
import json,gzip,math,itertools,hashlib,sys,collections
from pathlib import Path
O=Path(__file__).resolve().parent;A=O.parent;ROOT=next(p for p in A.parents if (p/'voxel_character/common/core.py').exists());sys.path.insert(0,str(ROOT));from voxel_character.common import core
P=.03125
def read(p):
 with gzip.open(p,'rt') if str(p).endswith('.gz') else p.open() as f:return json.load(f)
def ranges(lo,hi):return [(math.floor(a/P+core.EPS),math.ceil(b/P-core.EPS)) for a,b in zip(lo,hi)]
def count(rs,lo=None,hi=None):
 r=list(rs)
 if lo is not None:r[2]=(max(r[2][0],lo),min(r[2][1],hi))
 return math.prod(max(0,b-a) for a,b in r)
def main():
 a=read(O/'audit.json');cv=read(O/'candidate_separator_validation.json');cand=read(O/'candidate_intervals.json');coef=a['conditional_mapping'];records=[];old_ranges=[];slope=None
 for rev in ['roof_repair_r02','roof_repair_r03']:
  pl=read(A/rev/'plan.json');ma=read(A/rev/'roof_patch.master.json.gz');ids={l['operation'] for l in pl['tile_source_links']}
  if rev.endswith('02'):slope=ma['metadata']['measured_gable_slope']
  for comp in ma['components']:
   for op in comp['operations']:
    if op['id'] not in ids and op.get('selector',{}).get('feature') not in ids:continue
    sh=core.prepare_shape(op['shape'],P);t=core.transform(op.get('transform'));lo,hi=core.shape_bounds(sh);cs=[core.apply(t,p) for p in itertools.product(*zip(lo,hi))];rs=ranges([min(p[k] for p in cs) for k in range(3)],[max(p[k] for p in cs) for k in range(3)]);old_ranges.append(rs)
 statuses={q['id']:q for q in cv['candidate_results']};c=1/math.sqrt(1+slope*slope);nx=slope*c
 for q in cand['candidate_intervals']:
  st=statuses[q['id']]
  if not st['both_V_endpoints_observed']:continue
  u0,v0,u1,v1=q['bbox_px'];full_u=[859,870] if q['local_profile_ref']=='chimney_left_margin' else [903,913] if q['local_profile_ref']=='chimney_right_margin' else [913,919]
  x0=coef['sx']*(full_u[0]+.5)+coef['tx'];x1=coef['sx']*(full_u[1]-(0 if full_u[1]==919 else .5))+coef['tx'];z0=coef['sz']*(v0+.5)+coef['tz'];z1=coef['sz']*(v1-.5)+coef['tz'];base=13.875-slope*x0-.0625;along0=-.125;along1=(x1-x0)/c+.125
  # Bounding support only: no polygon, source master or occupied cells are constructed.
  lo=[x0-.0625*nx+along0*c,base-.0625*c-along1*nx,z0];hi=[x0+.0625*nx+along1*c,base+.0625*c-along0*nx,z1]
  vis0=coef['sx']*(u0+(.5 if u0 in [859,913] else 0))+coef['tx'];vis1=coef['sx']*(u1-(.5 if u1==913 else 0))+coef['tx'];wl=[x-P for x in lo];wh=[x+P for x in hi];rs=[ranges(lo,hi),ranges(wl,[vis0,wh[1],wh[2]]),ranges([vis1,wl[1],wl[2]],wh)]
  conflict=st['current_top_pixel_center_correspondence_counts'].get('current_chimney',0)>0
  records.append({'candidate_id':q['id'],'proposal_status':'DEFER_CURRENT_CHIMNEY_CONFLICT' if conflict else 'OBSERVED_V_CLEAR_AT_PIXEL_CENTERS_FULL_COLLISION_CHECK_STILL_REQUIRED','source_profile_phase':'Keep original observed V interval and two trough endpoints; U clipping only.','parent_U_support_px':full_u,'visible_fragment_bbox_px':q['bbox_px'],'candidate_evaluation_bound_from_proposed_operation_AABBs':sum(count(r) for r in rs),'per_operation_AABB_integer_ranges':rs})
 zchunks=[(z,min(z+16,164)) for z in range(-164,164,16)]
 report={'schema':'riverstone.roof.bounded_repair_plan.r1','status':'PLAN_ONLY_NO_GEOMETRY_NO_COMPILATION','ordering_repair':'Put each unchanged tile paint and its two feature cuts into its own component/instance; preserve its source ID, profile, transforms, crop bounds, material and grid. Common cuts are instance-local; merge finalized layers. Do not merely move all cuts to the end of one shared instance.','source_phase_rule':'24 candidates have two actual V troughs. Preserve that full measured V interval/profile phase, clip visible U only. The other 4 candidates have partial V endpoints and are deferred; never treat their clipped V bbox as a fresh full barrel profile.','geometry_priority':'First independently repair existing 354-feature operation ordering; then separately assess new observed fragments. Do not fill the 1781 losses from new image pixels.','holdout_rule':'Retain original TOP holdout. Do not move it onto the finite chimney or fill its 4220 exposed lattice columns. Registration disagreement remains unresolved.','candidate_collision_rule':'Defer all 3 candidate rectangles with 171 source pixels mapping to current chimney (252 total source pixels in those 3 rectangles). Remaining 21 candidates cover 1381 source pixels. Before any geometry, test complete proposed 3D tile/crop footprint against actual finite chimney and protected source ownership, not only pixel centers.','separator_rule':'1px is an appearance prior, not a physical gap/depth measurement. Preserve it pending explicit art review; separately note R2 uniformly inset partial endpoints by .5px despite R1 declaring zero separator there.','old_354_isolated_tile_operation_count':len(old_ranges),'old_354_total_AABB_candidate_evaluations_unchanged_by_instance_isolation':sum(count(r) for r in old_ranges),'old_354_max_AABB_candidates_in_existing_16Z_chunk':max(sum(count(r,lo,hi) for r in old_ranges) for lo,hi in zchunks),'proposed_24_fragment_candidate_evaluations_upper_bound':sum(q['candidate_evaluation_bound_from_proposed_operation_AABBs'] for q in records),'proposed_21_nonconflicting_pixel_center_fragment_candidate_evaluations_upper_bound':sum(q['candidate_evaluation_bound_from_proposed_operation_AABBs'] for q in records if not q['proposal_status'].startswith('DEFER')),'fragment_bounds_caveat':'AABB candidate counts for stated existing-profile-prior proposal, not occupied-cell or memory guarantees. Bounds include both feature-cut boxes. Revised source/collision masks require recomputation.','recommended_execution_limits':{'AS_MiB':256,'CPU_seconds_per_process':45,'candidate_cells_per_chunk':350000,'output_cells_per_chunk':100000,'no_whole_house_resample':True,'audit_before_render':True},'required_future_checks':['Exact no-overwrite witness restoration with isolated instances','Complete original 354 source/profile/crop identity preservation','Full candidate collision and zero existing-feature/source-holdout overlap','No change to original finite chimney, ridge, lower house or source raster','Actual TOP/RIGHT/oblique comparison before art acceptance'],'candidate_bounds':records,'compiler_calls':0,'sampler_calls':0,'master_or_geometry_written':False}
 (O/'bounded_repair_plan.json').write_text(json.dumps(report,indent=2)+'\n');assert sum(p.stat().st_size for p in O.iterdir() if p.is_file())<2*1024**2;print(json.dumps({k:v for k,v in report.items() if k!='candidate_bounds'},indent=2))
if __name__=='__main__':main()
