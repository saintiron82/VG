"""Bind source-sealed common collision and finite northern water-road repairs."""
import copy,json
from .build_scene import a,HERE,verify

def ref(p):return dict(path=str(p.relative_to(a.ROOT)),sha256=a.sha(p))
def write_new(p,value):
 if p.exists():raise ValueError('Preserve prior binding '+str(p))
 p.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n');return ref(p)

def main():
 b=a.load(HERE/'district_bound_r03.json')
 w=a.CITY/'assemblies/waterworks/registered_water_completion_r01/approaches_r03'
 c=a.CITY/'assemblies/landmarks/registered/precinct_r06_whole/residual_completion_r01/common_entry_repair_r03/candidate_r02'
 g=c.parents[1]/'retained_garden_access_r02'
 contract=a.load(c/'collision_contract.json','338ad107b2c32b1bdedb9f7e37fcc0eb7d5de8cf1d967c8281beb423477127b2')
 handoff=a.load(c/'integration_handoff.json');pack=verify(handoff['unchanged_native_pack'])
 poses=[p for p in pack['placements']if p['id']==contract['native_placement_id']]
 if len(poses)!=1:raise ValueError('Ambiguous explicit collision source pose')
 pose=poses[0]
 bound=copy.deepcopy(contract)
 bound['replacement_transform']={k:copy.deepcopy(pose[k])for k in ('position_m','yaw_rad','scale')}
 bound['integration_pose_binding']=dict(original_contract=ref(c/'collision_contract.json'),native_pack=handoff['unchanged_native_pack'],source_id=pose['id'],world_collision_geometry_unchanged=True)
 assert bound['add_triangles_world_xyz_m']==contract['add_triangles_world_xyz_m']
 b['collision_contracts'].append(write_new(HERE/'common_r03_pose_bound_contract.json',bound))
 b['patches'] += [ref(w/'surface_patch.json'),ref(g/'cemetery_surface_patch.json')]
 b['evidence'] += [ref(w/'freeze_manifest.json'),ref(c/'SOURCE_SEAL.json'),ref(g/'CEMETERY_READY_SEAL.json')]
 b['limits'].append('Common collision replacement, northern canal interior turn and cemetery access are source-bound candidates awaiting unchanged-controller replay; old SITE_COMMON is explicitly retired.')
 print(write_new(HERE/'district_bound_r04.json',b))
if __name__=='__main__':main()
