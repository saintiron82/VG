import hashlib,importlib.util,json,math,pathlib,sys
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;ROOT=next(p for p in H.parents if(p/'voxel_character').is_dir());sys.path.insert(0,str(ROOT));CITY=ROOT/'world_city/concept_city_v3'
from world_city.runtime_city.checks import placement as geo
sp=importlib.util.spec_from_file_location('cap',CITY/'assemblies/property/registered/public_lane_repairs_r01/inspect_contacts.py');g=importlib.util.module_from_spec(sp);sp.loader.exec_module(g)
sp=importlib.util.spec_from_file_location('r5p',CITY/'traversal_r5/prepare.py');b=importlib.util.module_from_spec(sp);sp.loader.exec_module(b)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def ref(p):return {'path':str(p.relative_to(ROOT)),'sha256':sha(p)}
p=H/'fixed_interfaces_complete.json';d=json.loads(p.read_bytes());sour=next(q for q in d['sources']if q['path'].endswith('visual_registered_common_r7_palette_r01/scene.json'));s=json.loads((ROOT/sour['path']).read_bytes());row=next(r for r in d['retained_corridor_review']['checks']if set(r['roads'])=={'BLOCK_006:ALLEY','WEST_MONASTERY_EDGE'});masks=row['uncovered_polygons_xz_m'];pinst=next(p for p in s['common_instances']if p['id']=='REGISTERED_LANDSCAPE:SITE_COMMON');a=s['common_assets'][pinst['asset_key']];rp=ROOT/a['render_path'];assert sha(rp)==a['render_sha256'];render=json.loads(rp.read_bytes());hits=[]
for gi,group in enumerate(render['groups']):
 for qi,quad in enumerate(group['quads']):
  p0,p1,p2=quad[:3];ny=(p1[2]-p0[2])*(p2[0]-p0[0])-(p1[0]-p0[0])*(p2[2]-p0[2])
  if ny<=1e-10:continue
  world=[b.transform(v,pinst)for v in quad];poly=[[v[0],v[2]]for v in world];clips=g.disjoint_intersections(poly,masks)
  if clips:hits.append({'group_index':gi,'quad_index':qi,'material':group['material'],'native_quad_world_xyz_m':world,'native_top_y_m':world[0][1],'source_gap_overlap_polygons_xz_m':clips,'covered_area_m2':sum(geo.polygon_area(q)for q in clips)})
out={'scene':sour,'fixed_input':ref(p),'native_instance':pinst['id'],'native_render':ref(rp),'terrain_top_missing_area_m2':row['uncovered_area_m2'],'native_upward_face_overlap_area_m2':sum(h['covered_area_m2']for h in hits),'native_top_levels_m':sorted({h['native_top_y_m']for h in hits}),'faces':hits,'scope':'Missing terrain projection is accounted by actual native upward-face projection only; quantized levels/steps and old park public interface still require separate seam/controller review. No support is synthesized.'}
with(H/'native_gap_diagnosis.json').open('x')as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in out.items()if k not in ['faces']}))
