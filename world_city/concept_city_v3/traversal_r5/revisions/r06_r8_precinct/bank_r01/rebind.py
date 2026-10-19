import pathlib,json,hashlib,sys,importlib.util,copy
sys.dont_write_bytecode=True
H=pathlib.Path(__file__).resolve().parent;OLD=H.parent;ROOT=next(p for p in H.parents if (p/'voxel_character').is_dir());CITY=ROOT/'world_city/concept_city_v3';BASE=CITY/'traversal_r5'
spec=importlib.util.spec_from_file_location('b',BASE/'prepare.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
def main():
 p=CITY/'evidence/r8_precinct_bank_r01/scene.json';expected='4113a70f323b5481a118eb4c70f0511ace0741e14cb9fbfb1b3031843b303769';assert b.sha(p)==expected;scene=b.read(p);data=b.read(OLD/'prepared.json');oldscene=b.read(pathlib.Path(data['sources']['actual_r8_candidate']['path']))
 metadata_changes={k for k in scene.keys()|oldscene.keys()if k!='surfaces' and scene.get(k)!=oldscene.get(k)};assert metadata_changes=={'r8_provenance','counts','local_terrain_patch','limits'}
 assert {k:v for k,v in scene.items()if k not in metadata_changes|{'surfaces'}}=={k:v for k,v in oldscene.items()if k not in metadata_changes|{'surfaces'}}
 assert {k:v for k,v in scene['surfaces'].items()if k!='bank'}=={k:v for k,v in oldscene['surfaces'].items()if k!='bank'}
 old_geometry={}
 for group in ['estate','guest']:
  key='SCENE:R8:'+group;old_geometry[group]=copy.deepcopy(data['assets'][key]);bounds=next(r['collision_bounds_xz_m']for r in data['routes']if r['group']==group);tris=[];faces=[]
  for material,vs in scene['surfaces'].items():
   if material=='water':continue
   for i in range(0,len(vs),3):
    t=vs[i:i+3]
    if b.overlaps(b.bounds(t),bounds):tris.append([t[0],t[2],t[1]]);faces.append([material,i//3])
  dest=H/'geometry'/(group+'.json');b.write(dest,{'scene_sha256':expected,'source_face_indices':faces,'triangles':tris,'selection_bounds_xz_m':bounds,'whole_triangles_only':True,'height_resampling':False});data['assets'][key]={'render_path':str(dest.relative_to(ROOT)),'render_sha256':b.sha(dest),'collision_format':'actual_scene_triangles'}
 for n in ['Traversal.gd','RenderData.gd','Traversal.tscn','PauseTraversal.gd','PauseTraversal.tscn','project.godot','run.sh','run_capture.py']:assert b.sha(H/n)==b.sha(OLD/n)
 data['sources']['actual_r8_candidate']=b.ref(p);data['sources']['retained_failed_prepared']=b.ref(OLD/'prepared.json')
 for n in ['stair_bank_patch_r01.json','stair_bank_review_r01.json','precinct_bank_binding_r01.json']:data['sources'][n]=b.ref(CITY/'registered_integration/r8'/n)
 data['implementation_hashes'].update({str(q.relative_to(ROOT)):b.sha(q)for q in H.iterdir()if q.is_file()})
 data['coverage']['replay']='Exact unchanged 16 routes after parent bank-only patch; original step/controller settings retained.'
 b.write(H/'prepared.json',data);b.write(H/'evidence/rebind.json',{'scene':b.ref(p),'prepared':b.ref(H/'prepared.json'),'original':b.ref(OLD/'prepared.json'),'routes_verbatim':data['routes']==b.read(OLD/'prepared.json')['routes'],'non_bank_geometry_fields_verbatim':True,'changed_metadata_fields':sorted(metadata_changes),'old_geometry':old_geometry});print('REBOUND',b.sha(H/'prepared.json'))
if __name__=='__main__':main()
