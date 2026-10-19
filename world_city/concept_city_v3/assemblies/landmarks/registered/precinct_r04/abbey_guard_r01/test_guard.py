"""Source/cache replay and explicit finite interface assertions."""
from build_guard import *
p=load(HERE/'resolved_placements.json');asset=p['assets'][0];source=load(ROOT/asset['source']['path']);cache=load(ROOT/asset['cache']['path']);compiled=coordinate_planes.compile_master(source,{'pitch':.1},max_candidate_cells=5000,max_output_cells=5000)
assert compiled['valid'];assert render_data.make_render_data(compiled)==cache
assert ref(ROOT/asset['source']['path'])==asset['source'];assert ref(ROOT/asset['cache']['path'])==asset['cache'];assert core.digest(source)==asset['master_hash']
assert p['test_results']['travel_ribbon_hits']==0
assert p['test_results']['connected_cells']==p['test_results']['total_cells']==720
assert p['test_results']['minimum_native_guard_to_traffic_edge_m']>1
assert p['test_results']['minimum_post_embed_m']>.2
q=p['placements'][0];assert q['scale']==[1,1,1] and q['yaw_rad']==0
lo=cache['bounds']['min'];hi=cache['bounds']['max'];assert abs(hi[1]+q['position_m'][1]-8.9)<1e-8
assert lo[2]+q['position_m'][2]<222.167089675 and hi[2]+q['position_m'][2]>226.969529341
assert lo[0]+q['position_m'][0]>-149.6
print('12 native guard checks passed; independent terrain/controller/view acceptance remains pending.')
