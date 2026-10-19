"""Prepare shared native merchant source unions and finite compile caps. Never compile."""
import copy,json,math,hashlib
from .grammar import HERE,ROOT,ref,write
from voxel_character.common import core
from world_city.concept_city_v3.assemblies.ordinary.registered.r1.compile_rows import count_master,pose,inverse
CANDIDATE_CAP=240000;OUTPUT_CAP=70000

def run():
 p=json.loads((HERE/'proposal.json').read_text());variants={};instances=[];(HERE/'masters').mkdir(exist_ok=True)
 for prop in p['properties']:
  members={m['id']:m for m in prop['placements']}
  for group in prop['groups']:
   ms=[members[k] for k in group['member_ids']]
   if len(ms)==1:instances.append(dict(group_id=group['id'],existing_asset_key=ms[0]['asset_key'],source_member_ids=group['member_ids']));continue
   entries=[dict(asset_key=m['asset_key'],translation=[m['local_center_xz_m'][0],0,m['local_center_xz_m'][1]],yaw_rad=m.get('local_yaw_rad',0)) for m in ms];entries.sort(key=lambda x:(x['translation'],x['asset_key']));key='merchant_native_union_'+hashlib.sha256(json.dumps(entries,sort_keys=True).encode()).hexdigest()[:14]
   if key not in variants:
    master=dict(schema='riverstone.voxel.master.v1',id=key,revision=1,axes=dict(up='+Y',front='+Z',right='+X'),grid_origin=[0,0,0],materials=None,components=[],instances=[],constraints=[dict(id='nonempty',kind='nonempty',selector={})],provenance=dict(proposal=ref(HERE/'proposal.json'),grammar=ref(HERE/'grammar.py'),policy='Compose unchanged native common sources with rigid transforms; no whole-house scaling, generated-cell edits or new mesher.',native_sources=[]),metadata=dict(assembly_class='merchant_attached_front_or_rear_range',native_modules=entries,floor_local_y_m=.5,reusable=True))
    foundation=[]
    for j,e in enumerate(entries):
     a=p['assets'][e['asset_key']];src=json.loads((ROOT/a['master_path']).read_text());prefix=f'M{j:02}_';master['provenance']['native_sources'].append(ref(ROOT/a['master_path']));cmap={c['id']:prefix+c['id'] for c in src['components']};sis={i['id']:i for i in src['instances']};poses={}
     if master['materials'] is None:master['materials']=src['materials']
     assert master['materials']==src['materials']
     for c in src['components']:q=copy.deepcopy(c);q['id']=cmap[c['id']];master['components'].append(q)
     def local(k):
      if k not in poses:
       q=sis[k];tr=core.transform(q.get('transform'));poses[k]=core.compose(local(q['parent']),tr) if q.get('parent') else tr
      return poses[k]
     y=e['yaw_rad'];unit=dict(basis=[[math.cos(y),0,math.sin(y)],[0,1,0],[-math.sin(y),0,math.cos(y)]],translation=e['translation'])
     for inst in src['instances']:
      item=dict(id=prefix+inst['id'],component=cmap[inst['component']],transform=core.compose(unit,local(inst['id'])));master['instances'].append(item)
      if 'foundation' in inst['component']:foundation.append(item['id'])
     assert not src.get('assembly_cuts')
     for constraint in src['constraints']:
      q=copy.deepcopy(constraint);q['id']=prefix+q['id'];sel=q.get('selector',{})
      for field,mapping in [('instance',{k:prefix+k for k in sis}),('component',cmap)]:
       if field in sel:sel[field]=[mapping[v] for v in sel[field]] if isinstance(sel[field],list) else mapping[sel[field]]
      if 'shape' in q:q['transform']=core.compose(unit,core.transform(q.get('transform')))
      master['constraints'].append(q)
    master['constraints'].append(dict(id='joined_native_foundations',kind='connected',selector=dict(instance=foundation)));core.validate_master(master,.5);count=count_master(master);assert count<=CANDIDATE_CAP
    path=HERE/'masters'/f'{key}.json';write(path,master);variants[key]=dict(master=ref(path),predicted_candidate_cells=count,native_module_count=len(entries),entries=entries,resource=dict(pitch=.5),candidate_cap=CANDIDATE_CAP,output_cell_cap=OUTPUT_CAP)
   instances.append(dict(group_id=group['id'],variant_key=key,source_member_ids=group['member_ids'],position_m=[prop['origin_xz_m'][0],prop['floor_y_m']-.5,prop['origin_xz_m'][1]],yaw_rad=prop['yaw_rad'],scale=[1,1,1]))
 result=dict(schema='riverstone.merchant_shared_union_budget.v1',proposal=ref(HERE/'proposal.json'),grammar=ref(HERE/'grammar.py'),status='source_only_no_compilation',variants=variants,placements=instances,unique_new_union_sources=len(variants),new_union_instances=sum('variant_key' in x for x in instances),existing_single_instances=sum('existing_asset_key' in x for x in instances),predicted_total_candidate_cells=sum(v['predicted_candidate_cells'] for v in variants.values()),largest_predicted_candidate_cells=max(v['predicted_candidate_cells'] for v in variants.values()),candidate_cap=CANDIDATE_CAP,output_cell_cap=OUTPUT_CAP,compile_count=0,platforms_and_retaining='Not included; exact finite terrain ownership proposal must be reviewed separately.',compiler=ref(ROOT/'voxel_character/common/core.py'),mesher=ref(ROOT/'voxel_character/tools/mesh.py'))
 write(HERE/'compile_budget.json',result);print(json.dumps({k:result[k] for k in ('unique_new_union_sources','new_union_instances','existing_single_instances','predicted_total_candidate_cells','largest_predicted_candidate_cells','candidate_cap','output_cell_cap','compile_count')},indent=2));return result
if __name__=='__main__':run()
