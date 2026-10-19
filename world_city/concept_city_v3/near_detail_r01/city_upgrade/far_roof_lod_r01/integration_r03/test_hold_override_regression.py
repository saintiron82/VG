"""Exercise actual catalog builder through tiny synthetic held/reissued fixtures."""
from pathlib import Path
import contextlib,copy,hashlib,importlib.util,io,json,sys
V=Path(__file__).resolve().parent;U=V.parents[1];R=next(p for p in V.parents if(p/'voxel_character/common/core.py').is_file());sys.path.insert(0,str(R));KEY='held_fixture_house';FAR={'far_visual_contract_path':'same.contract.json','far_visual_contract_sha256':'contract-sha','far_visual_render_path':'same.render.gz','far_visual_render_sha256':'far-sha','far_union_provenance_path':'same.proof.json'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2)+'\n');return p
def module(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
rows=[]
for revision,src in [('before',V/'build_near_catalog.before.py'),('after',U/'build_near_catalog.py')]:
 for mode in ['unchanged_override','changed_near','changed_source','hold_without_override']:
  root=V/'regression_fixtures'/revision/mode;here=root/'U';city=root/'C';compiled=here/'house_rules/compiled'
  master={'components':[{'id':'structure','operations':[{'id':'roof_plane_0','action':'paint','part':'roof','shape':{'kind':'extrusion','polygon':[[-1,1],[1,1],[1,2],[-1,2]],'z_min':-1,'z_max':1}},{'id':'closed_door_leaf','action':'paint','part':'door','shape':{'kind':'box','min':[-.5,0,0],'max':[.5,1,.2]}}]}],'instances':[{'id':'structure','component':'structure'}]}
  mp=write(root/'master.json',master);rp=write(root/'render.json',{'quad_count':1});ip=write(city/'playable_r01/generated/tile_r01/index.json',{'common_assets':{KEY:{'master_path':'master.json','master_sha256':sha(mp)}}})
  previous={'render_path':'render.json','sha256':sha(rp),'source_master_sha256':sha(mp),**FAR}
  if mode=='changed_near':previous['sha256']='stale-near'
  if mode=='changed_source':previous['source_master_sha256']='stale-source'
  cp=write(city/'playable_detail_r01/near_catalog.json',{'source_city_index_sha256':sha(ip),'assets':{KEY:previous}})
  sp=write(compiled/'reissue.stats.json',{'asset_key':KEY,'status':'pass','constraints':[{'pass':True}],'files':{'.render.json':{'path':'render.json','sha256':sha(rp)}}});qp=write(compiled/'reissue.qa.json',{'all_pass':True});write(compiled/'provenance_holds.json',{'assets':{KEY:{'status':'PENDING_NATIVE_REISSUE'}}})
  if mode!='hold_without_override':write(compiled/'selection_overrides.json',{'assets':{KEY:{'stats_path':str(sp.relative_to(root)),'stats_sha256':sha(sp),'qa_path':str(qp.relative_to(root)),'qa_sha256':sha(qp)}}})
  mod=module(src,'test_'+revision+'_'+mode);mod.ROOT=root;mod.HERE=here;mod.CITY=city
  with contextlib.redirect_stdout(io.StringIO()):mod.main()
  result=json.loads(cp.read_text())['assets'];kept=all(result.get(KEY,{}).get(k)==v for k,v in FAR.items());expected=mode=='unchanged_override'and revision=='after';okay=kept==expected
  if mode=='hold_without_override':okay=okay and KEY not in result
  rows.append({'revision':revision,'mode':mode,'far_fields_preserved':kept,'expected_preservation':expected,'held_asset_excluded_without_override':KEY not in result if mode=='hold_without_override'else None,'pass':okay})
report={'all_pass':all(x['pass']for x in rows),'cases':rows,'before_reproduces_bug':next(x for x in rows if x['revision']=='before'and x['mode']=='unchanged_override')['far_fields_preserved']is False,'after_fixes_unchanged_override_only':next(x for x in rows if x['revision']=='after'and x['mode']=='unchanged_override')['far_fields_preserved'],'builder_before_sha256':sha(V/'build_near_catalog.before.py'),'builder_after_sha256':sha(U/'build_near_catalog.py')};write(V/'hold_override_regression.json',report);print(json.dumps(report,indent=2));raise SystemExit(0 if report['all_pass']else 2)
