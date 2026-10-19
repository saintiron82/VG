"""Source-only normalized shared-range budget; reuse existing rear-range caches."""
import copy,json,math,hashlib
from .grammar import HERE,ROOT,ref,write,xform
from voxel_character.common import core
from world_city.concept_city_v3.assemblies.ordinary.registered.r1.compile_rows import count_master
CAP=240000;OUTPUT=70000

def canonical(entries):
 entries=sorted(entries,key=lambda q:(q['translation'][0],q['translation'][2],q['asset_key']));anchor=entries[0]['translation'];normal=[dict(asset_key=q['asset_key'],translation=[float(round(q['translation'][k]-anchor[k],7)) for k in range(3)],yaw_rad=float(round(q.get('yaw_rad',0),7))) for q in entries];signature=hashlib.sha256(json.dumps(normal,sort_keys=True).encode()).hexdigest();return signature,normal,anchor

def make_master(entries,key,assets,source):
 master=dict(schema='riverstone.voxel.master.v1',id=key,revision=1,axes=dict(up='+Y',front='+Z',right='+X'),grid_origin=[0,0,0],materials=None,components=[],instances=[],constraints=[dict(id='nonempty',kind='nonempty',selector={})],provenance=dict(eligibility=source,policy='Rigid unchanged native common modules, normalized at a shared local anchor. No scaling, cell edits or new mesher.',native_sources=[]),metadata=dict(assembly_class='merchant_attached_range_r02',native_modules=entries,floor_local_y_m=.5,reusable=True));foundation=[]
 for j,e in enumerate(entries):
  a=assets[e['asset_key']];path=ROOT/a['master_path'];assert ref(path)['sha256']==a['master_sha256'];src=json.loads(path.read_text());prefix=f'N{j:02}_';master['provenance']['native_sources'].append(ref(path));cmap={c['id']:prefix+c['id'] for c in src['components']};sis={i['id']:i for i in src['instances']};poses={}
  if master['materials'] is None:master['materials']=src['materials']
  assert master['materials']==src['materials']
  for c in src['components']:q=copy.deepcopy(c);q['id']=cmap[c['id']];master['components'].append(q)
  def local(k):
   if k not in poses:
    i=sis[k];t=core.transform(i.get('transform'));poses[k]=core.compose(local(i['parent']),t) if i.get('parent') else t
   return poses[k]
  y=e.get('yaw_rad',0);unit=dict(basis=[[math.cos(y),0,math.sin(y)],[0,1,0],[-math.sin(y),0,math.cos(y)]],translation=e['translation'])
  for i in src['instances']:
   item=dict(id=prefix+i['id'],component=cmap[i['component']],transform=core.compose(unit,local(i['id'])));master['instances'].append(item)
   if 'foundation' in i['component']:foundation.append(item['id'])
  assert not src.get('assembly_cuts')
  for c in src['constraints']:
   q=copy.deepcopy(c);q['id']=prefix+q['id'];sel=q.get('selector',{})
   for field,mapping in [('instance',{k:prefix+k for k in sis}),('component',cmap)]:
    if field in sel:sel[field]=[mapping[v] for v in sel[field]] if isinstance(sel[field],list) else mapping[sel[field]]
   if 'shape' in q:q['transform']=core.compose(unit,core.transform(q.get('transform')))
   master['constraints'].append(q)
 master['constraints'].append(dict(id='joined_native_foundations',kind='connected',selector=dict(instance=foundation)));core.validate_master(master,.5);return master

def run():
 source=ref(HERE/'eligibility.json');s=json.loads((HERE/'eligibility.json').read_text());oldbase=HERE.parent/'merchant_block011';oldbudget=json.loads((oldbase/'compile_budget.json').read_text());oldreport=json.loads((oldbase/'compile_report.json').read_text());known={};assets={};variants={};placements=[];(HERE/'masters').mkdir(exist_ok=True)
 for key,v in oldbudget['variants'].items():
  signature,_,anchor=canonical(v['entries']);known[signature]=dict(asset_key=key,anchor=anchor,asset=oldreport['assets'][key])
 for prop in s['properties']:
  members={p['id']:p for p in prop['placements']}
  for group in prop['groups']:
   ms=[members[k] for k in group['member_ids']];entries=[dict(asset_key=p['asset_key'],translation=[p['local_center_xz_m'][0],0,p['local_center_xz_m'][1]],yaw_rad=p['local_yaw_rad']) for p in ms]
   signature,normal,anchor=canonical(entries)
   if len(ms)==1:
    key=ms[0]['asset_key'];assets[key]=prop['assets'][key];position=ms[0]['position_m'];yaw=ms[0]['yaw_rad'];kind='existing_native_single'
   elif signature in known:
    old=known[signature];key=old['asset_key'];assets[key]=old['asset'];delta=[anchor[k]-old['anchor'][k] for k in range(3)];center=xform([delta[0],delta[2]],prop['origin_xz_m'],prop['yaw_rad']);position=[center[0],prop['floor_y_m']-.5,center[1]];yaw=prop['yaw_rad'];kind='existing_native_union'
   else:
    key='merchant_fabric_union_'+signature[:14]
    if key not in variants:
     master=make_master(normal,key,prop['assets'],source);path=HERE/'masters'/f'{key}.json';write(path,master);count=count_master(master);assert count<=CAP,(key,count);variants[key]=dict(master=ref(path),signature=signature,canonical_entries=normal,predicted_candidate_cells=count,resource=dict(pitch=.5),candidate_cap=CAP,output_cell_cap=OUTPUT)
    center=xform([anchor[0],anchor[2]],prop['origin_xz_m'],prop['yaw_rad']);position=[center[0],prop['floor_y_m']-.5,center[1]];yaw=prop['yaw_rad'];kind='new_shared_native_union_source'
   placements.append(dict(id=group['id'],asset_key=key,position_m=position,yaw_rad=yaw,scale=[1,1,1],property_id=prop['id'],block_id=prop['block_id'],source_member_ids=group['member_ids'],kind=kind,palette_id=ms[0]['roof_palette'],finished_floor_y_m=prop['floor_y_m'],canonical_signature=signature))
 for a in assets.values():
  for k in ('master','render'):assert ref(ROOT/a[k+'_path'])['sha256']==a[k+'_sha256']
 assert len(variants)<=8
 out=dict(schema='riverstone.merchant_fabric_r02_cache_budget.v1',eligibility=source,grammar=ref(HERE/'grammar.py'),author=ref(HERE/'prepare_cache.py'),status='source_only_no_new_compilation',variants=variants,reused_assets=assets,placements=placements,summary=dict(runtime_groups=len(placements),new_shared_native_sources=len(variants),reused_native_assets=len(assets),new_union_instances=sum(p['kind']=='new_shared_native_union_source' for p in placements),existing_union_instances=sum(p['kind']=='existing_native_union' for p in placements),existing_single_instances=sum(p['kind']=='existing_native_single' for p in placements),predicted_total_candidate_cells=sum(v['predicted_candidate_cells'] for v in variants.values()),largest_predicted_candidate_cells=max(v['predicted_candidate_cells'] for v in variants.values()),candidate_cap_each=CAP,output_cap_each=OUTPUT,new_compile_count=0),limits=['Building-range source budget only; no ground/retaining/cache compilation or scene placement.','Native door and union occupancy proofs must be rerun on the new common cache after compilation.']);write(HERE/'compile_budget.json',out);print(json.dumps(out['summary'],indent=2));return out
if __name__=='__main__':run()
