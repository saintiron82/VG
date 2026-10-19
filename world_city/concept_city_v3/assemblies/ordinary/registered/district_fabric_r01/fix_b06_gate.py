from . import geometry as g
from .design import HERE as SOURCE
from .coherent_bulk import config
import types

def run():
 out=SOURCE/'contour_revision_r01/BLOCK_006';g.HERE=out;config(next(b for b in g.load(g.CITY/'registered_integration/r8/coverage_plan/baseline_blocks.json')['blocks']if b['block_id']==out.name));l=g.load(out/'selected_layout.json');h=next(h for h in l['holdings']if h['id']=='BLOCK_006:R8_C002');base=g.load(SOURCE/'coherent_regrade_r01/BLOCK_006/selected_layout.json');old=next(p for p in base['placements']if p['holding_id']==h['id']);center=[old['position_m'][0],old['position_m'][2]];yaw=old['yaw_rad'];gate=g.xform([14,1.5],center,yaw);outside=g.xform([18,1.5],center,yaw);h.update(gate_position_xz_m=gate,external_route=[gate,outside,h['public_target_xz_m']]);h['external_route_polygons_xz_m']=g.ribbons(h['external_route'],h['external_width_m']);g.write(out/'selected_layout.json',l)
 for name in['access','furnish']:
  s=(SOURCE/(name+'.py')).read_text()
  if name=='access':s=s.replace("allowed=raster([h['holding_polygon_xz_m']]+", "allowed=raster(h.get('ground_owner_polygons_xz_m',[h['holding_polygon_xz_m']])+")
  else:s=s.replace("holes=b['native_foundation_polygons_xz_m']+", "holes=[q for bp in layout['placements']if bp['holding_id']==h['id']for q in bp['native_foundation_polygons_xz_m']]+")
  m=types.ModuleType(__package__+'.b06gate_'+name);m.__package__=__package__;exec(compile(s,str(SOURCE/(name+'.py')),'exec'),m.__dict__);m.run()
if __name__=='__main__':run()
