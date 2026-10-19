"""Source-feature rectangular pane witnesses for the frozen emitted-ray verifier.

Uses exact common point predicates along finite lines. No volume compilation or
source edits. Existing opaque doors retain their state rather than being called
open passages. Source components/instances and protected door operations bind
unchanged around the explicit roof substitution and pane trims.
"""
import copy,importlib.util,itertools,json,resource,sys,time
from collections import Counter
from pathlib import Path
HERE=Path(__file__).resolve().parent;B=HERE.parent;ROOT=B.parents[5]
sys.path[:0]=[str(B.parent),str(B/'sampler_v2'),str(B.parent.parent/'house_rules')]
import author as a
import reserved_io_r04 as rio
from output_reservations_v3 import ReservationBook
p=B/'polygon_sources/emitted_qa/verify_polygon_windows.py';spec=importlib.util.spec_from_file_location('frozen_rect_ray_verifier',p);v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)

def prepare(row,catalog,rules_path,writer):
 start=time.monotonic();key=row['asset_key'];rules=a.load(rules_path);contract=a.load(ROOT/row['replacement_contract_path']);source=a.load(ROOT/row['source_master_path']);master=a.load(ROOT/row['emitted_master_path']);proof=a.load(ROOT/row['composition_proof_path'])
 for field,sha in [('source_master_path','source_sha256'),('emitted_master_path','emitted_master_sha256'),('replacement_contract_path','replacement_contract_sha256'),('composition_proof_path','composition_proof_sha256')]:assert a.sha(ROOT/row[field])==row[sha]
 assert contract['adapter_schema']=='riverstone.existing_aperture.adapter.v1' and contract['authored_master_sha256']==row['emitted_master_sha256']
 assert source['instances']==master['instances'] and source.get('constraints',[])==master.get('constraints',[])
 old={c['id']:c for c in source['components']};new={c['id']:c for c in master['components']};selected=set(proof['source_roof_components']);assert list(old)==list(new) and all(new[k]==old[k] for k in old if k not in selected)
 original_cuts=source.get('assembly_cuts',[]);assert master.get('assembly_cuts',[])[:len(original_cuts)]==original_cuts;added=master['assembly_cuts'][len(original_cuts):];assert len(added)==2*row['window_count'];cutmap={c['id']:c for c in added};assert len(cutmap)==len(added)
 before=v.Scene(source,.05,a);after=v.Scene(master,.05,a);lookup={(c,i,o['id']):(o,t) for c,i,o,t,_ in a.source_inventory(source)};rays=[];windows=[];sampled=0;failures=[];depth=rules['glass_recess_m'];thickness=rules['glass_thickness_m']
 for patch in contract['patches']:
  bind=patch['source_glass'];pane,t=lookup[bind['component'],bind['instance'],bind['operation']];assert a.core.digest(pane)==bind['operation_sha256'] and pane['shape']==patch['source_glass_shape_local'];assert t==patch['local_to_master'];shape=pane['shape'];assert shape['kind']=='box';back,front=patch['retained_glass_local_z_interval_m'];assert abs(back+depth+thickness)<1e-9 and abs(front+depth)<1e-9
  selector={'component':bind['component'],'instance':bind['instance'],'part':pane['part'],'material':pane['material'],'feature':pane['id']};rear,forward=copy.deepcopy(shape),copy.deepcopy(shape);rear['max'][2]=back;forward['min'][2]=front;expected=[{'id':patch['id']+'_glass_'+name,'selector':selector,'shape':s,'transform':t} for name,s in [('rear_trim',rear),('front_recess',forward)]];assert [cutmap[x] for x in patch['authored_cut_ids']]==expected
  features=[lookup[f['component'],f['instance'],f['operation']][0] for f in patch['source_features']];assert all(a.core.digest(o)==f['operation_sha256'] for o,f in zip(features,patch['source_features']))
  ids=[]
  for n,(fx,fy) in enumerate(itertools.product((.25,.75),(.3,.5,.7))):
   xy=[shape['min'][j]+f*(shape['max'][j]-shape['min'][j]) for j,f in enumerate((fx,fy))];axis,sign,point,local=v.snapped_witness(t,xy,.05,contract['grid_origin'],a.core)
   # Skip only source frame/mullion/shutter intersections, explicitly recording
   # them below; whole-assembly structural occlusion is retained and tested.
   intersects=[o['id'] for o in features if a.core.contains(a.core.prepare_shape(o['shape'],.05),[local[0],local[1],0])]
   if intersects:continue
   ray={'id':patch['id']+'__'+str(n),'patch_id':patch['id'],'kind':'pane','axis':axis,'outward_sign':sign,'frame_axis_origin_m':t['translation'][axis],'sample_master_m':point,'requested_local_xy_m':xy,'snapped_local_xy_m':local[:2],'minimum_depth_m':min(shape['min'][2]-.05,-.6),'pane_front_depth_m':v.snapped_depth(t,front,.05,contract['grid_origin'],a.core),'pane_back_depth_m':v.snapped_depth(t,back,.05,contract['grid_origin'],a.core),'pane_material':pane['material'],'pane_feature':pane['id']}
   hits,count=after.surfaces(ray);sampled+=count;oldhits,count=before.surfaces(ray);sampled+=count;classification,blocker=v.classify(ray,hits,oldhits,bind);ray.update(exposure=classification,expected_hits=hits,original_source_hits=oldhits,preexisting_occluder=blocker if classification.startswith('preexisting') else None)
   if classification=='exposed':
    expected=[{'depth_m':ray['pane_front_depth_m'],'normal_outward':1,'material':pane['material']},{'depth_m':ray['pane_back_depth_m'],'normal_outward':-1,'material':pane['material']}]
    if len(hits)<2 or not v.compare_hits(hits[:2],expected):failures.append({'id':ray['id'],'reason':'pane thickness or front/rear air failed'})
   elif classification=='unexplained_canonical_pane_failure':failures.append({'id':ray['id'],'reason':classification})
   rays.append(ray);ids.append(ray['id'])
  assert len(ids)>=2,'No two independent clear pane probes for '+patch['id'];windows.append({'patch_id':patch['id'],'source_glass':bind,'source_features':patch['source_features'],'ray_ids':ids})
 counts=Counter(r['exposure'] for r in rays);references={name:v.ref(path) for name,path in [('source_master',ROOT/row['source_master_path']),('canonical_master',ROOT/row['emitted_master_path']),('replacement_contract',ROOT/row['replacement_contract_path']),('source_composition_proof',ROOT/row['composition_proof_path']),('catalog',catalog),('rules',rules_path),('source_witness_driver',Path(__file__)),('frozen_author',Path(a.__file__)),('frozen_predicates',Path(a.core.__file__)),('stream_reader',v.STREAM),('witness_verifier',p)]};report={'schema':'riverstone.rectangular_windows.source_witnesses.v1','asset_key':key,'source_witnesses_pass':not failures,'all_pass':None,'actual_render_tested':False,'status':'source_witnesses_ready_actual_render_not_tested' if not failures else 'source_witness_failure','window_count':len(windows),'pitch_m':.05,'grid_origin':contract['grid_origin'],'source_references':references,'source_exposure_counts':dict(counts),'windows':windows,'rays':rays,'entry_preservation':{'original_components_except_exact_roof_selection_identical':True,'original_instances_constraints_identical':True,'original_assembly_cuts_exact_prefix':True,'original_closed_door_operations_identical':True,'open_passage_claimed':False},'source_line_point_evaluations':sampled,'failures':failures,'compile_calls':0,'geometry_edits':0,'runtime_edits':0,'limitation_scope':v.LIMITS,'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_seconds':time.monotonic()-start};writer.write(p.parent/(key+'.source_witnesses.json'),report);assert not failures,failures;return {k:report[k] for k in ['asset_key','window_count','source_exposure_counts','source_witnesses_pass','elapsed_seconds','max_rss_kib']}
def main(directory):
 resource.setrlimit(resource.RLIMIT_AS,(256*1024**2,256*1024**2));d=directory.resolve();catalog=d/'canonical/generated/catalog.json';rules=d/'rules.v1.json';rows=a.load(catalog)['assets'];identity={'catalog':v.ref(catalog),'rules':v.ref(rules),'driver':v.ref(__file__),'verifier':v.ref(p)};cfg=a.load(B.parent.parent/'house_rules/shared_output_budget.v2.json');book=ReservationBook(ROOT/cfg['book_path'],ROOT,[ROOT/x for x in cfg['retained_roots']],cfg['limit_bytes'],min_free_disk_bytes=cfg['min_free_disk_bytes']);key='facility_rect_source_rays:'+d.name;scopes=[{'directory':str(p.parent.relative_to(ROOT)),'prefix':r['asset_key']+'.source_witnesses'} for r in rows]+[{'directory':str(HERE.relative_to(ROOT)),'prefix':'prepare_rectangular_witnesses.py'},{'directory':str((d/'source_ray_validation').relative_to(ROOT)),'prefix':''}];book.reserve(key,scopes,500000,identity);book.acquire_writer(key);w=rio.ReservedWriter(book,key,B,scopes,ROOT)
 try:
  result=[prepare(row,catalog,rules,w) for row in rows];w.write(d/'source_ray_validation/report.json',{'all_pass':True,'assets':result,'identity':identity,'compile_calls':0});book.release(key,identity,'Original pane, feature, exact trim and whole-source finite ray checks passed; emitted mesh pending.');print(json.dumps(result),flush=True)
 finally:w.close()
if __name__=='__main__':main(Path(sys.argv[1]))
