"""Read-only actual scene side-volume audit with the updated shared classifier."""
import pathlib,json,hashlib,sys
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT))
from world_city.concept_city_v3.registered_topography.revisions.r17_district_batches import side_clearance as side
CITY=ROOT/'world_city/concept_city_v3';REPAIR=CITY/'assemblies/waterworks/registered_water_completion_r01/approaches_r03'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return dict(path=str(p.relative_to(ROOT)),sha256=sha(p))
def main():
 d=json.loads((H/'prepared_runtime.json').read_bytes());path=pathlib.Path(d['sources']['scene']['path']);assert sha(path)==d['sources']['scene']['sha256'];scene=json.loads(path.read_bytes());route=json.loads((REPAIR/'route_handoff.json').read_bytes());owners=[dict(id='NORTH_INTERIOR_TUBE_'+str(i),polygon_xz_m=p,plane_y_xz_m=[0.,0.,15.6],headroom_m=1.8)for i,p in enumerate(route['tube_polygons_xz_m'])];ix=side.SideIndex(scene,[r['polygon_xz_m']for r in owners]);audit=ix.audit(owners);fixture=json.loads((REPAIR/'near_vertical_face_fixture.json').read_bytes());triangle=fixture['face']['vertices_xyz_m'];assert side.physical_side(triangle,'road');oldscene=json.loads((CITY/'evidence/r8_district_r02/scene.json').read_bytes());old=side.SideIndex(oldscene,[r['polygon_xz_m']for r in owners]).audit(owners);known=any(c['material']=='road'and c['triangle_index']==1833 for c in old['contacts']);assert known
 out=dict(schema='riverstone.actual_normalized_north_side_audit.r03',scene=ref(path),shared_checker=ref(pathlib.Path(side.__file__)),route=ref(REPAIR/'route_handoff.json'),actual_new_scene=audit,known_old_blocker_detected=known,old_scene=ref(CITY/'evidence/r8_district_r02/scene.json'),old_scene_audit=old,near_vertical_normal_y_ratio_threshold=side.MAX_SIDE_NORMAL_Y,limits=['This audit tests actual scene surface sides in the finite northern interior-turn tube.','Native colliders and complete approach/entry controls are independently exercised by the unchanged controller.'])
 with(H/'evidence/normalized_side_audit.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
 print('NORMALIZED_SIDE_AUDIT',audit['status'],'contacts',len(audit['contacts']),'old blocker detected',known)
if __name__=='__main__':main()
