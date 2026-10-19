from author_plan import *
import shutil

def main():
 plan=load(HERE/'design_plan.json');spec=plan['sources'][1];path=ROOT/spec['source']['path'];source=load(path);before=ref(path);rejected=HERE/'rejected_02';rejected.mkdir(exist_ok=True)
 for path0 in[HERE/'resolved_placements.json',HERE/'native_geometry.json',HERE/'native_tests.json',HERE/'design_plan.json',path,HERE/'cache/registered_phase02_estate_boundary.pitch_0.25.render.json']:
  shutil.copy2(path0,rejected/path0.name)
 target=rect(-69,-134.3,-68.5,-134);pose=spec['position_m'];removed=[]
 for comp in source['components']:
  kept=[]
  for op in comp.get('operations',[]):
   sh=op['shape'];p=rect(sh['min'][0]+pose[0],sh['min'][2]+pose[2],sh['max'][0]+pose[0],sh['max'][2]+pose[2])
   if geo.positive_area_overlap(p,target,0):removed.append({'operation':op,'polygon_xz_m':p})
   else:kept.append(op)
  comp['operations']=kept
 assert len(removed)==1,removed
 cut=removed[0]['polygon_xz_m'];source['extensions']['terrain_aligned_native_support']=[r for r in source['extensions']['terrain_aligned_native_support']if not geo.positive_area_overlap(r['polygon_xz_m'],cut,0)];source['extensions']['collar_gate_full_span_omission_xz_m']=[cut];source['provenance']['collar_boundary_repair']={'before_source':before,'author':ref(Path(__file__)),'reason':'Whole terminal wall span omitted for finite collar opening; preserves continuous remaining bands, no cell whittling.'};write(path,source);spec['source']=ref(path);spec['estimate']=estimate_candidates(source,spec['pitch_m']);plan['holdings'][0]['native_boundary_source_regions']=[r for r in plan['holdings'][0]['native_boundary_source_regions']if not geo.positive_area_overlap(r['polygon_xz_m'],cut,0)];plan['summary']['candidate_visits_total']=sum(r['estimate']['candidate_cells_exact_aabb_visits']for r in plan['sources']);write(HERE/'design_plan.json',plan);write(HERE/'collar_boundary_repair.json',{'before_source':before,'after_source':spec['source'],'removed_complete_operations':removed,'omitted_native_ground_area_m2':geo.polygon_area(cut),'initial_positive_collar_overlap_m2':.03981165245548883,'reason':'Deliberate slightly wider gate terminal. Common recompilation required.'});print(removed,spec['estimate']['candidate_cells_exact_aabb_visits'])
if __name__=='__main__':main()
