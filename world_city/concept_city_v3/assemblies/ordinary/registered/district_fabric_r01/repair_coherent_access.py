"""Increase source route clearance, never collision tolerance or door width."""
from . import geometry as g
from .design import HERE as SOURCE
from .coherent_bulk import config
import types

def run():
 plan=g.CITY/'registered_integration/r8/coverage_plan';blocks={b['block_id']:b for b in g.load(plan/'baseline_blocks.json')['blocks']}
 for out in sorted((SOURCE/'coherent_regrade_r01').glob('BLOCK_*')):
  p=out/'access_handoff.json'
  if not p.exists()or not g.load(p)['unresolved_doors']:continue
  config(blocks[out.name]);g.HERE=out
  for name in['access','furnish']:
   src=(SOURCE/(name+'.py')).read_text()
   if name=='access':src=src.replace('>=w/2+.2','>=w/2+.4')
   else:src=src.replace("holes=b['native_foundation_polygons_xz_m']+", "holes=[q for bp in layout['placements']if bp['holding_id']==h['id']for q in bp['native_foundation_polygons_xz_m']]+")
   mod=types.ModuleType(__package__+'.repair_'+name);mod.__package__=__package__;exec(compile(src,str(SOURCE/(name+'.py')),'exec'),mod.__dict__);mod.run()
  proposal=g.load(out/'ground_proposal.json');proposal.update(access=g.ref(out/'access_handoff.json'),court_equipment=g.ref(out/'court_equipment.json'));g.write(out/'ground_proposal.json',proposal);print(out.name,g.load(p)['summary'])
if __name__=='__main__':run()
