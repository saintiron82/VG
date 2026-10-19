"""Data-only modules -> one common master, bind rig and transform sidecars.
No runtime engine or per-person geometry generator. All sampling stays in common.
"""
from pathlib import Path
import argparse,copy,hashlib,json,math,re,sys
from author import HERE,LILY,COMMON,dump
sys.path.insert(0,str(COMMON));from core import digest
BASE_PARTS=json.loads((LILY/'data/rig.json').read_text())['parts']
FRAMES={'adult_slender':{'scale':[.84,1,.92],'age':'adult_female'},'adult_average':{'scale':[.92,1,1],'age':'adult_male'},'adult_broad':{'scale':[1.04,1,1.06],'age':'adult_male'},'adult_female':{'scale':[.84,1,.92],'age':'adult_female'},'adult_male':{'scale':[.94,1,1],'age':'adult_male'},'child':{'scale':[.68,.70,.76],'age':'child','y_knots':[[0,0],[.12,.09],[.52,.32],[.94,.59],[1.405,.94],[1.82,1.27]]}}
PALETTE_OVERRIDES={'skin':'efcbbd','skin_shadow':'d8ac9e','skin_light':'f5d6c6','silver':'c2bdd6','silver_light':'e5dfed','silver_shadow':'9793b1','eye_white':'f7eadf','iris':'3b989e','iris_light':'8dd3bd','pupil':'213642','lash':'554752','lip':'a96d71','lip_light':'cd9093'}

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def ymap(y,frame):
 if 'y_knots' not in frame:return y*frame['scale'][1]
 k=frame['y_knots']
 for i in range(len(k)-1):
  if y<=k[i+1][0]:
   a,b=k[i],k[i+1];return a[1]+(y-a[0])*(b[1]-a[1])/(b[0]-a[0])
 a,b=k[-2:];return b[1]+(y-b[0])*(b[1]-a[1])/(b[0]-a[0])
def point(v,frame):return [round(v[0]*frame['scale'][0],8),round(ymap(v[1],frame),8),round(v[2]*frame['scale'][2],8)]
def relative(v,pivot,frame):return [round(a-b,8) for a,b in zip(point([pivot[i]+v[i] for i in range(3)],frame),point(pivot,frame))]
def load_module(id):
 if not re.fullmatch('[a-z][a-z0-9_]{0,63}',str(id)):raise ValueError('Unsafe module ID')
 a=HERE/'data/modules'/(id+'.json');b=HERE/'clothing_library/modules'/(id+'.json')
 path=a if a.exists() else b
 if not path.exists():raise ValueError('Unknown module '+id)
 m=json.loads(path.read_text());m['_path']=str(path.relative_to(HERE));m['_sha256']=sha(path)
 if 'operations' not in m:m['operations']=m['ops']
 if 'layer' not in m:m['layer']='costume'
 if 'parts' not in m:m['parts']=m.get('attachment_parts',[])
 return m

def validate_preset(p):
 if p.get('schema')!='riverstone.character.assembly.v1':raise ValueError('Unsupported preset schema')
 if not re.fullmatch('[a-z][a-z0-9_]{0,63}',str(p.get('id',''))):raise ValueError('Unsafe preset ID')
 if p.get('body') not in FRAMES:raise ValueError('Unknown body frame')
 if p.get('role')!='lily' and (p.get('hair')=='lily_long' or 'lily_teal_gold' in p.get('ornaments',[])):raise ValueError('Lily signature hair/ornament reserved for Lily identity')
 if p.get('role')=='lily' and (p['id']!='lily_original' or p['body']!='adult_slender'):raise ValueError('Lily canonical identity/frame is fixed')
 for k,v in p.get('palette',{}).items():
  if not re.fullmatch('[a-fA-F0-9]{6}',str(v)):raise ValueError('Invalid palette '+k)
 if p.get('district','any') not in ['any','market','craft','residential','civic','harbor','garden']:raise ValueError('Unknown district')
 if p.get('role') not in ['lily','merchant','artisan','resident','guard','child','porter','scholar']:raise ValueError('Unknown occupation/presentation')
 if (p['body']=='child') != (p.get('role')=='child'):raise ValueError('Child frame/role must agree; no child occupational assignment')
 if p.get('role')!='lily' and (HERE/'data/combination_rules.json').exists():
  rules=json.loads((HERE/'data/combination_rules.json').read_text());role=p['role'];district=p.get('district','any')
  if district!='any' and role not in rules['district_roles'].get(district,[]):raise ValueError('Occupation/district combination not allowed')
  if p.get('outfit_id') and p['outfit_id'] not in rules['occupation_outfits'].get(role,[]):raise ValueError('Occupation/outfit combination not allowed')
 return True

def fit_apron_modules(modules):
 """Fit separate apron leaves to a selected flared skirt; preserve source module data."""
 path=HERE/'clothing_library/validation_rules.json'
 if not path.exists():return []
 rules=json.loads(path.read_text());fit=rules.get('optional_apron_layer_fit',{});profiles=rules.get('stride_depth_profiles',{})
 skirt=next((m['id'] for m in modules if m['id'] in ['female_dress','female_skirt']),None)
 if not skirt or skirt not in profiles:return []
 profile=profiles[skirt];records=[]
 def depth(y):
  if y<=profile[0][0]:return profile[0][1]
  for a,b in zip(profile,profile[1:]):
   if y<=b[0]:return a[1]+(y-a[0])/(b[0]-a[0])*(b[1]-a[1])
  return profile[-1][1]
 def clip(poly,y,above):
  out=[]
  for a,b in zip(poly,poly[1:]+poly[:1]):
   ia=(a[1]>=y) if above else (a[1]<=y);ib=(b[1]>=y) if above else (b[1]<=y)
   if ia:out.append(a)
   if ia!=ib:
    t=(y-a[1])/(b[1]-a[1]);out.append([a[0]+t*(b[0]-a[0]),y])
  return out
 for m in modules:
  if m['id'] not in fit.get('allowed_apron_modules',[]):continue
  out=[];changed=[]
  for op in m['operations']:
   kind='leaf' if fit['apron_leaf_id_contains'] in op['id'] else 'pocket' if fit['apron_pocket_id_contains'] in op['id'] else None
   if not kind:out.append(op);continue
   shape=op['shape'];poly=shape.get('polygon')
   lo=min(v[1] for v in poly) if poly else shape['min'][1];hi=max(v[1] for v in poly) if poly else shape['max'][1]
   n=math.ceil((hi-lo)/fit['band_max_height_m']);offset=fit[kind+'_offsets_from_selected_skirt_depth_m']
   for i in range(n):
    a=lo+(hi-lo)*i/n;b=lo+(hi-lo)*(i+1)/n;d=max(depth(a),depth(b));new=copy.deepcopy(op);new['id']+='__fitted_band_%02d'%i;sh=new['shape']
    if poly:sh['polygon']=clip(clip(poly,a,True),b,False);sh['z_min']=round(d+offset[0],8);sh['z_max']=round(d+offset[1],8)
    else:sh['min'][1]=a;sh['max'][1]=b;sh['min'][2]=round(d+offset[0],8);sh['max'][2]=round(d+offset[1],8)
    out.append(new)
   changed.append(op['id'])
  m['operations']=out
  if changed:records.append({'module':m['id'],'selected_skirt':skirt,'source_operations':changed,'rule_source':'clothing_library/validation_rules.json','rule_sha256':sha(path),'fit':copy.deepcopy(fit),'profile':copy.deepcopy(profile)})
 return records

def assemble(p):
 validate_preset(p);frame=FRAMES[p['body']]
 selected=['adult_base',p['face'],p['hair']]
 cost=p['costume'];selected+=([cost] if isinstance(cost,str) else cost)
 selected+=p.get('ornaments',[])
 modules=[load_module(s) for s in selected]
 if isinstance(cost,list):
  sys.path.insert(0,str(HERE/'clothing_library'))
  from validate_clothing import validate_outfit
  problems=validate_outfit(cost,frame['age'])
  if problems:raise ValueError('; '.join(problems))
  rules=json.loads((HERE/'data/combination_rules.json').read_text())
  outfits=json.loads((HERE/'clothing_library/outfit_examples.json').read_text())['outfits']
  def core(ids):return {mid for mid in ids if set(load_module(mid).get('slots',[])) & {'top','bottom','outer'}}
  chosen=core(cost)
  allowed=[o for o in outfits if o['id'] in rules['occupation_outfits'].get(p['role'],[])]
  if not any(chosen==core(o['modules']) for o in allowed):raise ValueError('Occupation/core garment combination not allowed')
  if p.get('outfit_id') and not any(o['id']==p['outfit_id'] and chosen==core(o['modules']) for o in allowed):raise ValueError('Declared outfit and core garment selection disagree')
 for m in modules:
  allowed=m.get('allowed_age_frames')
  if allowed and frame['age'] not in allowed:raise ValueError('Garment/frame combination not allowed: '+m['id'])
 fit_records=fit_apron_modules(modules)
 rig=copy.deepcopy(json.loads((LILY/'data/rig.json').read_text()))
 parts=copy.deepcopy(BASE_PARTS)
 # New identity face anchors are explicit rest-pivot replacements, not hidden scaling.
 for q in parts:
  if q['id']=='braid':q['pivot_m']=[.160,1.660,.060]
  if q['id'].startswith(('eyelid_','brow_')):
   q['pivot_m']=[(-1 if q['id'].endswith('left') else 1)*.074,1.675,.140]
  if q['id'].startswith('mouth_corner_'):q['pivot_m']=[(-1 if q['id'].endswith('left') else 1)*.028,1.523,.115]
  if q['id']=='mouth':q['pivot_m']=[0,1.523,.115]
 ops=[];costume_parts={};baseby={q['id']:q for q in parts}
 semantic_layers=[]
 for m in modules:
  own=[]
  for part in m['parts']:
   part=copy.deepcopy(part)
   if 'pivot_m' not in part:part['pivot_m']=part.pop('pivot')
   existing=next((q for q in parts if q['id']==part['id']),None)
   if existing is None:parts.append(part)
   elif existing['parent']!=part['parent'] or existing['pivot_m']!=part['pivot_m']:raise ValueError('Conflicting module attachment '+part['id'])
  for op in m['operations']:
   op=copy.deepcopy(op);original=op['part'];op['id']=m['id']+'__'+op['id']
   if m['layer']=='costume' and original not in ['cape','satchel','skirt_left','skirt_right']:
    pid='costume_'+original
    if pid not in costume_parts:
     if original not in baseby:raise ValueError('Unknown costume socket '+original)
     costume_parts[pid]={'id':pid,'parent':original,'pivot_m':copy.deepcopy(baseby[original]['pivot_m']),'role':'costume'}
    op['part']=pid
   ops.append(op);own.append(op['id'])
  semantic_layers.append({'module':m['id'],'layer':m['layer'],'source_path':m['_path'],'sha256':m['_sha256'],'operation_ids':own})
 parts+=list(costume_parts.values())
 used={o['part'] for o in ops};parts=[q for q in parts if q['id'] in used]
 # Unused optional nodes are pruned; ancestors must remain present rather than empty geometry.
 for q in parts:
  if q['parent'] is not None and q['parent'] not in used:raise ValueError('Missing parent '+q['parent'])
 # Sort the union after module attachment, then transform authored world coordinates.
 ordered=[];remaining=parts[:];seen=set()
 while remaining:
  ready=[q for q in remaining if q['parent'] is None or q['parent'] in seen]
  if not ready:raise ValueError('Parent cycle')
  for q in ready:ordered.append(q);seen.add(q['id']);remaining.remove(q)
 unscaled={q['id']:copy.deepcopy(q['pivot_m']) for q in ordered}
 for q in ordered:q['pivot_m']=point(q['pivot_m'],frame)
 for op in ops:
  s=op['shape']
  if s['kind']=='box':s['min']=point(s['min'],frame);s['max']=point(s['max'],frame)
  elif s['kind']=='extrusion':s['polygon']=[[point([x,y,0],frame)[i] for i in [0,1]] for x,y in s['polygon']];s['z_min']*=frame['scale'][2];s['z_max']*=frame['scale'][2]
  else:raise ValueError('Unsupported primitive')
 palette=copy.deepcopy(json.loads((LILY/'data/master.json').read_text())['materials']);palette.update(PALETTE_OVERRIDES)
 if any(k not in palette for k in p.get('palette',{})):raise ValueError('Unknown palette slot')
 palette.update(p.get('palette',{}))
 master={'schema':'riverstone.voxel.master.v1','id':'lily_original_r01__'+p['id'],'revision':1,'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],'materials':palette,'components':[{'id':'lily','parts':[{'id':q['id'],'pivot':q['pivot_m'],'metadata':{'parent_part':q['parent'],'role':q['role']}} for q in ordered],'operations':ops}],'instances':[{'id':'lily','component':'lily'}],'constraints':[],'extensions':{'provenance':json.loads((HERE/'data/reference.json').read_text()),'assembly':{'preset':copy.deepcopy(p),'layers':semantic_layers,'frame':frame,'rest_retarget':{'from':'r5 canonical world pivots','source_world_basis':'identity','frame_transform':'baked into world geometry, pivots, relative clip translations and socket offsets','anchor_overrides':{k:unscaled[k] for k in unscaled if k=='braid' or k.startswith(('eyelid_','brow_','mouth'))},'capsule_change':'none for Lily/adults; child explicit 1.27m visual-preview capsule'}}}}
 if fit_records:master['extensions']['assembly']['costume_fit']=fit_records
 h=digest(master);rig['source_id']=master['id'];rig['master_hash']=h;rig['parts']=ordered
 rig['limits']={'maximum_parts':72,'maximum_candidate_cells_per_layer':1000000,'reference_max_cells':350000,'reference_max_quads':25000,'max_materials':32}
 if p['body']=='child':rig['capsule']={'radius_m':.18,'height_m':1.27,'center_m':[0,.635,0]}
 # Capsule of all adult presets remains exactly the compatible gameplay dimensions.
 for s in rig['sockets'].values():s['offset_m']=relative(s['offset_m'],unscaled[s['part']],frame)
 rig['sockets']['hair_ornament']={'part':'head','offset_m':relative([.16,.26,.08],unscaled['head'],frame)}
 rig['sockets']['costume_attachments']={'part':'torso','offset_m':[0,0,0]}
 rig['motion_channels']={k:[x for x in v if x in used] for k,v in rig['motion_channels'].items()}
 tailids=[q['id'] for q in ordered if q['role']=='hair_secondary']
 rig['motion_channels']['locomotion']+=tailids
 sources={'master.json':master,'rig.json':rig}
 for name in ['bind','idle','walk','blink','expression_neutral','expression_happy','expression_focused']:
  clip=copy.deepcopy(json.loads((LILY/'data'/(name+'.json')).read_text()));clip['source_id']=master['id'];clip['master_hash']=h
  clip['tracks']=[t for t in clip['tracks'] if t['selector']['part'] in used]
  for t in clip['tracks']:
   pid=t['selector']['part']
   for k in t['keys']:
    if name=='blink' and k['translation'][1]<0:k['translation'][1]=-.0725
    if name.startswith('expression_'):
     k['rotation_degrees']*=.4;k['translation']=[v*.4 for v in k['translation']]
    if pid=='braid':k['rotation_degrees']*=.22
    k['translation']=relative(k['translation'],unscaled[pid],frame)
  def track(pid,duration,angles):return {'id':pid,'type':'rigid_transform','selector':{'instance':'lily','part':pid},'axis':[1,0,0],'space':'part','interpolation':'smoothstep','keys':[{'time':duration*i/(len(angles)-1),'rotation_degrees':angle,'translation':[0,0,0]} for i,angle in enumerate(angles)]}
  if name=='bind':
   existing={t['selector']['part'] for t in clip['tracks']}
   clip['tracks'] += [track(pid,1,[0,0]) for pid in used-existing]
   clip['tracks'].sort(key=lambda t:[q['id'] for q in ordered].index(t['selector']['part']))
  elif name in ['idle','walk']:
   for i,pid in enumerate(tailids):clip['tracks'].append(track(pid,clip['duration'],[0,.8,0,-.8,0] if name=='idle' else [-1.2,1.2,-1.2,1.2,-1.2]))
  sources[name+'.json']=clip
 return sources

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--preset',type=Path,default=HERE/'data/presets/lily_original.json');ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
 if a.output.exists():raise FileExistsError('New source output required')
 sources=assemble(json.loads(a.preset.read_text()))
 for n,v in sources.items():dump(a.output/n,v)
 print(json.dumps({'source':str(a.output),'parts':len(sources['rig.json']['parts']),'operations':len(sources['master.json']['components'][0]['operations']),'master_hash':digest(sources['master.json'])}))
if __name__=='__main__':main()
