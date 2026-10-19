"""Package-facing hashes and evidence index; does not rebuild or mutate geometry."""
from pathlib import Path
import json,hashlib,struct,shutil,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'common'))
from core import digest

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')

def finalize():
 r=ROOT;rev='r05';snap=r/'evidence/source_r05';snap.mkdir(exist_ok=True)
 for p in [r/'tools/build.py',r/'tools/verify.py',r/'data/rules.json',r/'data/design.json',r/'runtime/Review.gd',r/'runtime/CheckExport.gd',*sorted((r/'data/presets').glob('*.json'))]:shutil.copy2(p,snap/p.name)
 roundtrip=json.loads((r/'evidence/glb_roundtrip_r05.json').read_text());verify=json.loads((r/'evidence/verification_r05.json').read_text());assert roundtrip['pass'] and verify['pass']
 assets=[];index=[];inputs=[]
 for preset in sorted((r/'data/presets').glob('*.json')):
  aid=json.loads(preset.read_text())['id'];directory=r/f'generated/{aid}_{rev}';m=json.loads((directory/'manifest.json').read_text());master=json.loads((directory/'master.json').read_text());pr=master['extensions']['provenance'];assert digest(master)==m['master_hash']
  for k,p in [('rules_sha256',r/'data/rules.json'),('design_sha256',r/'data/design.json'),('generator_sha256',r/'tools/build.py'),('preset_sha256',preset)]:
   assert sha(p)==pr[k];inputs.append({'asset':aid,'input':str(p.relative_to(r)),'sha256':sha(p)})
  assert sha(r/pr['reference']['file'])==pr['reference']['sha256']==m['reference_sha256']
  f=r/f'exports/{aid}_{rev}.glb';raw=f.read_bytes();magic,version,length=struct.unpack('<4sII',raw[:12]);n,kind=struct.unpack('<I4s',raw[12:20]);gltf=json.loads(raw[20:20+n]);assert magic==b'glTF' and version==2 and length==len(raw) and kind==b'JSON';assert not gltf.get('images') and not gltf.get('textures')
  a={'id':aid,'glb':str(f.relative_to(r)),'glb_sha256':sha(f),'bytes':len(raw),'reference_sha256':m['reference_sha256'],'master_hash':m['master_hash'],'render_sha256':m['render_sha256'],'generated_manifest_sha256':sha(directory/'manifest.json'),'cell_count':m['cell_count'],'triangles':m['quad_count']*2,'semantic_parts':m['parts'],'verified_sockets':5,'gltf_meshes':len(gltf['meshes']),'embedded_image_count':0,'embedded_texture_count':0,'animation_count':len(gltf.get('animations',[])),'capture_files':[]}
  for folder in ['visual_r05','visual_r05_cyan']:
   cdir=r/'evidence'/folder
   captures=json.loads((cdir/'capture_manifest.json').read_text())
   for c in captures['captures']:
    if c['data']['asset']['id']!=aid:continue
    cf=cdir/c['file'];assert cf.exists();assert c['data']['asset']['master_hash']==m['master_hash'];assert c['data']['asset']['render_sha256']==m['render_sha256'];entry={'file':str(cf.relative_to(r)),'sha256':sha(cf),'pixels':c['pixels'],'view':c['data']['view'],'asset':aid};a['capture_files'].append(entry);index.append(entry)
  assert len(a['capture_files'])==4
  rt=next(v for v in roundtrip['assets'] if v['id']==aid);assert rt['triangles']==a['triangles'];a['godot_roundtrip']=rt;assets.append(a)
 write(r/'evidence/visual_r05_index.json',{'schema':'riverstone.reference_character.capture_index.v1','revision':rev,'actual_godot_views':8,'captures':index,'art_acceptance':False})
 write(r/'evidence/input_dependency_validation_r05.json',{'pass':True,'reference_master_input_hashes_match':True,'inputs':inputs})
 write(r/'exports/manifest.json',{'schema':'riverstone.reference_character.export_manifest.v1','revision':rev,'status':'actual_3d_approximation_draft','art_acceptance':False,'assets':assets,'export_method':'Godot 4.6.3 GLTFDocument.append_from_scene + write_to_filesystem; separate append_from_file + generate_scene roundtrip','exporter_sha256':sha(r/'runtime/Review.gd'),'roundtrip_verifier_sha256':sha(r/'runtime/CheckExport.gd'),'common_renderer_sha256':sha(r/'runtime/common/RenderData.gd'),'evidence':{p:sha(r/p) for p in ['evidence/verification_r05.json','evidence/glb_roundtrip_r05.json','evidence/visual_r05_index.json','evidence/input_dependency_validation_r05.json']},'limits':['Static bind pose only; no verified walk, expressions, physics, skinning or animation.','Side/rear and hidden surfaces are newly authored interpretations of a single illustration.','Technical verification is not visual approval or complete reference restoration.']})
 write(r/'evidence/visual_review_r05.json',{'schema':'riverstone.reference_character.visual_review.v1','review_method':'All eight actual Godot comparison PNGs directly inspected alongside source illustrations on 2026-10-19.','technical_render_complete':True,'art_acceptance':False,'status':'3d_approximation_draft','improvements':['Removed the radial dome entirely. Five separately authored 3D cloth sweeps and one recessed rear overlap sheet now create asymmetric raised side petals and a rear train.','The front of the legs is no longer covered by a wide dome. Garment overlap remains around the waist.','Hair endpoints no longer return in closed loop-like paths.','Gold narrow eyes, cyan single eye/fringe, different halo/crown/gloves/bouquet remain identifiable.'],'remaining_three_differences':['The upright torso and separated straight legs differ from the illustrations\' leaning, graceful asymmetric poses.','Hair strands, skull/face planes and expression remain coarser; the cyan open smile is not reproduced.','Cloth turns and blue lining occupy less of the cyan front silhouette than in the reference; hidden rear drape is a new interpretation.'],'render_notes':['Violet face capture is framed higher than cyan face capture; both three-quarter views use the same camera.','Voxel step shading remains visible, particularly on cloth viewed from the rear.'],'metrics_are_not_art_score':True,'back_and_hidden_surface_status':'new design interpretation, not claimed observed reconstruction'})
 write(r/'STATUS.json',{'schema':'riverstone.reference_character.delivery.v1','latest_revision':rev,'status':'3d_approximation_draft','complete_original_restoration':False,'technical_checks':{'common_recompile':True,'renderer_from_common':True,'actual_gui_comparison_views':8,'glb_roundtrip':True,'parts_per_asset':33,'sockets_per_asset':5,'source_input_hashes_match':True},'art_acceptance':False,'entry_points':{'exports':'exports/manifest.json','visual_review':'evidence/visual_review_r05.json','capture_index':'evidence/visual_r05_index.json','readme':'README_KO.md','shared_generator':'tools/build.py','input_rules':'data/rules.json','input_presets':['data/presets/violet_bride.json','data/presets/cyan_bride.json']}})
 print(json.dumps({'revision':rev,'assets':[{k:a[k] for k in ['id','glb_sha256','bytes','triangles']} for a in assets],'actual_views':8,'source_inputs_match':True,'art_acceptance':False},indent=2))
if __name__=='__main__':finalize()
