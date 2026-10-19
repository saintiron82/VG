"""Compile reusable rigid native row unions through unchanged common machinery."""
from __future__ import annotations
import json,math,copy,hashlib,itertools,time,resource,argparse
from pathlib import Path
from voxel_character.common import core,coordinate_planes,render_data
from .author_density import HERE,ROOT,ref,write
PITCH=.5;CAP=65000;OUTCAP=60000

def inverse(t):
 b=core.transpose(t['basis']);return {'basis':b,'translation':[-sum(b[i][j]*t['translation'][j] for j in range(3)) for i in range(3)]}
def pose(p):
 y=p['yaw_rad'];return {'translation':p['position_m'],'basis':[[math.cos(y),0,math.sin(y)],[0,1,0],[-math.sin(y),0,math.cos(y)]]}
def count_master(m):
 count=0;comps={c['id']:c for c in m['components']}
 for inst in m['instances']:
  t=core.transform(inst.get('transform'))
  for o in comps[inst['component']]['operations']:
   s=core.prepare_shape(o['shape'],PITCH);a,b=core.shape_bounds(s);tr=core.compose(t,core.transform(o.get('transform')));corners=[core.apply(tr,q) for q in itertools.product(*zip(a,b))];lo=[min(q[k] for q in corners) for k in range(3)];hi=[max(q[k] for q in corners) for k in range(3)];count+=math.prod(math.ceil(b/PITCH-core.EPS)-math.floor(a/PITCH+core.EPS) for a,b in zip(lo,hi))
 return count

def prepare():
 d=json.loads((HERE/'candidate.json').read_text());review=json.loads((HERE/'geometry_review.json').read_text());assert review['candidate']==ref(HERE/'candidate.json') and review['valid_horizontal_source'];members={p['id']:p for p in d['placements']};(HERE/'masters').mkdir(exist_ok=True);variants={};instances=[]
 for g in d['groups']:
  ps=[members[k] for k in g['member_ids']]
  if len(ps)==1:instances.append({'group_id':g['id'],'kind':'existing_single_cache','source_member_ids':g['member_ids'],'placement':ps[0]});continue
  yaw=ps[0]['yaw_rad'];basis=pose(ps[0])['basis'];raw={'basis':basis,'translation':[0,0,0]};invraw=inverse(raw);local=[core.apply(invraw,p['position_m']) for p in ps];left=min(q[0]+p['actual_body_bounds_local_m']['min'][0] for p,q in zip(ps,local));right=max(q[0]+p['actual_body_bounds_local_m']['max'][0] for p,q in zip(ps,local));front=sum(q[2]+p['all_cached_lod_outer_bounds_local_m']['max'][2] for p,q in zip(ps,local))/len(ps);anchor=core.apply(raw,[(left+right)/2,ps[0]['position_m'][1],front]);frame={'basis':basis,'translation':anchor};inv=inverse(frame)
  entries=[{'asset_key':p['asset_key'],'translation':[round(v,7) for v in core.apply(inv,p['position_m'])]} for p in ps];entries.sort(key=lambda q:q['translation'][0]);key='attached_native_row_'+hashlib.sha256(json.dumps(entries,sort_keys=True).encode()).hexdigest()[:14]
  if key not in variants:
   m={'schema':'riverstone.voxel.master.v1','id':key,'revision':1,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':None,'components':[],'instances':[],'constraints':[{'id':'union_present','kind':'nonempty','selector':{}}],'provenance':{'candidate':ref(HERE/'candidate.json'),'source_policy':'Rigid native masters only; one common occupancy union removes internal party/eave faces. No output-cell edits, object scaling or compiler changes.','native_sources':[]},'metadata':{'assembly_class':'attached_native_poor_row_group','native_modules':entries,'floor_local_y_m':.5,'body_side_join':'Native body side planes coincide; eaves are deliberately unioned.','reusable':True,'source_unit_count':len(entries)}}
   foundation_instances=[]
   for j,e in enumerate(entries):
    asset=d['assets'][e['asset_key']];source=json.loads((ROOT/asset['master_path']).read_text());m['provenance']['native_sources'].append(ref(ROOT/asset['master_path']));prefix=f'H{j:02}_';cmap={c['id']:prefix+c['id'] for c in source['components']}
    if m['materials'] is None:m['materials']=source['materials']
    assert m['materials']==source['materials'],'Material dictionaries differ; explicit semantic remapping needed'
    for c in source['components']:cc=copy.deepcopy(c);cc['id']=cmap[c['id']];m['components'].append(cc)
    srcis={i['id']:i for i in source['instances']};poses={}
    def local_pose(k):
     if k not in poses:
      i=srcis[k];tr=core.transform(i.get('transform'));poses[k]=core.compose(local_pose(i['parent']),tr) if i.get('parent') else tr
     return poses[k]
    unit={'translation':e['translation'],'basis':core.IDENTITY}
    for inst in source['instances']:
     new={'id':prefix+inst['id'],'component':cmap[inst['component']],'transform':core.compose(unit,local_pose(inst['id']))};m['instances'].append(new)
     if 'foundation' in inst['component']:foundation_instances.append(new['id'])
    assert not source.get('assembly_cuts'),'Unexpected cross-component cuts need explicit selector remapping'
    for constraint in source['constraints']:
     c=copy.deepcopy(constraint);c['id']=prefix+c['id'];sel=c.get('selector',{})
     for field,mapping in [('instance',{k:prefix+k for k in srcis}),('component',cmap)]:
      if field in sel:sel[field]=[mapping[v] for v in sel[field]] if isinstance(sel[field],list) else mapping[sel[field]]
     if 'shape' in c:c['transform']=core.compose(unit,core.transform(c.get('transform')))
     m['constraints'].append(c)
   m['constraints'].append({'id':'joined_foundations_connected','kind':'connected','selector':{'instance':foundation_instances}});core.validate_master(m,PITCH);path=HERE/'masters'/f'{key}.json';write(path,m);count=count_master(m);assert count<=CAP;(variants.setdefault(key,{})).update(master=ref(path),predicted_candidate_cells=count,native_unit_count=len(entries),member_spec=entries)
  instances.append({'group_id':g['id'],'variant_key':key,'kind':'native_common_union','transform':frame,'position_m':anchor,'yaw_rad':yaw,'source_member_ids':g['member_ids'],'scale':[1,1,1]})
 preflight={'schema':'riverstone.native_row_preflight.v1','candidate':ref(HERE/'candidate.json'),'review':ref(HERE/'geometry_review.json'),'pitch_m':PITCH,'per_asset_candidate_cap':CAP,'per_asset_output_cap':OUTCAP,'variants':variants,'placements':instances,'unique_new_union_assets':len(variants),'existing_single_instances':sum(p['kind']=='existing_single_cache' for p in instances),'total_predicted_candidate_cells':sum(v['predicted_candidate_cells'] for v in variants.values()),'largest_predicted_candidate_cells':max(v['predicted_candidate_cells'] for v in variants.values()),'compiler':ref(ROOT/'voxel_character/common/core.py'),'mesher':ref(ROOT/'voxel_character/tools/mesh.py'),'estimated_peak_memory_mib_range':[60,300],'sequential_compile':True};write(HERE/'compile_preflight.json',preflight);print(json.dumps({k:preflight[k] for k in ['unique_new_union_assets','existing_single_instances','total_predicted_candidate_cells','largest_predicted_candidate_cells','estimated_peak_memory_mib_range']},indent=2));return preflight

def compile_all(preflight):
 (HERE/'cache').mkdir(exist_ok=True);assets={};reports=[];started=time.monotonic()
 for key,spec in preflight['variants'].items():
  before=time.monotonic();master=json.loads((ROOT/spec['master']['path']).read_text());c=coordinate_planes.compile_master(master,{'pitch':PITCH},max_candidate_cells=CAP,max_output_cells=OUTCAP);assert c['candidate_cells']==spec['predicted_candidate_cells'];assert c['valid'],c['constraints'];r=render_data.make_render_data(c);cp=HERE/'cache'/f'{key}.compiled.json';rp=HERE/'cache'/f'{key}.render.json';write(cp,c);write(rp,r);asset={'key':key,'master_path':spec['master']['path'],'master_sha256':spec['master']['sha256'],'render_path':str(rp.relative_to(ROOT)),'render_sha256':ref(rp)['sha256'],'compiled_path':str(cp.relative_to(ROOT)),'compiled_sha256':ref(cp)['sha256'],'bounds':r['bounds'],'cell_count':r['cell_count'],'quad_count':r['quad_count'],'constraints':c['constraints'],'pitch_m':PITCH,'author_metadata':master['metadata']};assets[key]=asset;reports.append({'key':key,'candidate_cells':c['candidate_cells'],'cell_count':r['cell_count'],'quad_count':r['quad_count'],'seconds':time.monotonic()-before,'valid':c['valid']});print(json.dumps(reports[-1]),flush=True)
 report={'schema':'riverstone.native_row_compile_result.v1','preflight':ref(HERE/'compile_preflight.json'),'assets':assets,'variants':reports,'total_seconds':time.monotonic()-started,'peak_rss_mib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024,'total_unique_quads':sum(a['quad_count'] for a in assets.values()),'new_union_assets':len(assets),'cell_edit_count':0,'whole_house_scaling_count':0};write(HERE/'compile_report.json',report);print(json.dumps({k:report[k] for k in ['new_union_assets','total_seconds','peak_rss_mib','total_unique_quads']},indent=2));return report
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--compile',action='store_true');args=ap.parse_args();p=prepare()
 if args.compile:compile_all(p)
