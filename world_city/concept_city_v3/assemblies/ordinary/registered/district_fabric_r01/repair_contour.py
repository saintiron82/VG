"""Reuse already-proven native doorway paths after a pure vertical terrace move."""
from . import geometry as g
from .design import HERE as SOURCE
from .coherent_bulk import config
import types
blocks={b['block_id']:b for b in g.load(g.CITY/'registered_integration/r8/coverage_plan/baseline_blocks.json')['blocks']}
for out in sorted((SOURCE/'contour_revision_r01').glob('BLOCK_*')):
 a=g.load(out/'access_handoff.json');l=g.load(out/'selected_layout.json');old=g.load(SOURCE/'coherent_regrade_r01'/out.name/'access_handoff.json');by={r['door_id']:r for r in old['routes']};hs={h['id']:h for h in l['holdings']};restored=[]
 for fail in a['unresolved_doors']:
  r=g.copy.deepcopy(by[fail['door_id']]);floor=hs[r['holding_id']]['floor_y_m'];r['floor_y_m']=floor;r['polyline_xyz_m']=[[q[0],floor,q[1]]for q in r['polyline_xz_m']];r['source_native_planar_proof']=g.ref(SOURCE/'coherent_regrade_r01'/out.name/'access_handoff.json');r['status']='Exact unchanged native XZ door route reused at the proposed terrace datum. Terrain profile remains pending.';a['routes'].append(r);restored.append(r['door_id'])
 a.update(layout=g.ref(out/'selected_layout.json'),unresolved_doors=[]);a['summary'].update(finite_full_width_door_links=len(a['routes']),unresolved_doors=0);g.write(out/'access_handoff.json',a)
 if restored:
  config(blocks[out.name]);g.HERE=out;src=(SOURCE/'furnish.py').read_text().replace("holes=b['native_foundation_polygons_xz_m']+", "holes=[q for bp in layout['placements']if bp['holding_id']==h['id']for q in bp['native_foundation_polygons_xz_m']]+");m=types.ModuleType(__package__+'.repair_furnish');m.__package__=__package__;exec(compile(src,str(SOURCE/'furnish.py'),'exec'),m.__dict__);m.run();print(out.name,restored)
 proposal=g.load(out/'ground_proposal.json');proposal.update(access=g.ref(out/'access_handoff.json'),court_equipment=g.ref(out/'court_equipment.json'));g.write(out/'ground_proposal.json',proposal)
