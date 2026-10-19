"""Shared data-driven appearance variants, never new per-person generators.
Preset -> derived common master + compatible rig/clips. No runtime sampling.
"""
from pathlib import Path
import copy,json,re,sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'common'))
from core import digest
CONTRACT_PATH=ROOT/'data'/'appearance_contract.json'

def validate_preset(preset,contract=None):
 contract=contract or json.loads(CONTRACT_PATH.read_text())
 if not isinstance(preset,dict):raise ValueError('preset must be an object')
 for k in contract['required_fields']:
  if k not in preset:raise ValueError('missing field '+k)
 if preset['schema']!=contract['preset_schema'] or preset['family']!=contract['family']:raise ValueError('unsupported appearance family/schema')
 if not re.fullmatch('[a-z][a-z0-9_]{0,63}',str(preset['id'])):raise ValueError('safe lower-case preset ID required')
 for key,choices in [('body_frame',contract['body_frames']),('face',contract['faces']),('hair_style',contract['hair_styles']),('outfit',contract['outfits'])]:
  if preset[key] not in choices:raise ValueError('unsupported '+key+': '+str(preset[key]))
 if not isinstance(preset['palette'],dict):raise ValueError('palette map required')
 for k,v in preset['palette'].items():
  if k not in contract['palette_slots'] or not isinstance(v,str) or not re.fullmatch('#?[0-9A-Fa-f]{6}',v):raise ValueError('invalid palette override: '+k)
 if not isinstance(preset['accessories'],dict):raise ValueError('accessories map required')
 for k,v in preset['accessories'].items():
  if k not in contract['accessory_keys'] or type(v) is not bool:raise ValueError('invalid accessory '+k)
 return True

def load_sources():
 names=['master','rig','bind','idle','walk','blink','expression_neutral','expression_happy','expression_focused']
 return {n+'.json':json.loads((ROOT/'data'/(n+'.json')).read_text()) for n in names}

def derive_sources(preset,source=None):
 validate_preset(preset)
 sources=copy.deepcopy(source if source is not None else load_sources())
 master=sources['master.json'];base_hash=digest(master);rig=sources['rig.json'];contract=json.loads(CONTRACT_PATH.read_text())
 # The named Lily preset is exactly the canonical source. Other presets bind
 # to a new source hash, even when only palette values differ.
 is_canonical=preset==json.loads((ROOT/'data'/'lily.preset.json').read_text())
 if is_canonical:return sources
 master['id']='city_person_'+preset['id']
 master['materials'].update({k:v.lstrip('#').lower() for k,v in preset['palette'].items()})
 component=master['components'][0]
 removed=set()
 if preset['hair_style']!='braided':removed.add('braid')
 for key in contract['accessory_keys']:
  if not preset['accessories'].get(key,True):removed.add(key)
 if preset['face']=='angular':
  face=next(o for o in component['operations'] if o['id']=='face_shape')
  face['shape']['polygon']=[[-.075,1.44],[.075,1.44],[.13,1.48],[.16,1.55],[.16,1.64],[.125,1.69],[.08,1.72],[-.08,1.72],[-.125,1.69],[-.16,1.64],[-.16,1.55],[-.13,1.48]]
 for op in component['operations']:
  shape=op['shape'];feature=op['id']
  if preset['hair_style']=='cropped':
   if feature=='hair_rear_mass':
    if shape['kind']=='box':shape['min'][1]=1.55
    else:
     for p in shape['polygon']:p[1]=max(p[1],1.55)
   if feature.startswith('rear_silver_strand_') or feature.startswith('temple_lock_') or feature.startswith('side_layer_'):
    if shape['kind']=='box':shape['min'][1]=1.57
    else:
     for p in shape['polygon']:p[1]=max(p[1],1.57)
   if feature in ['fringe_lock_0','fringe_lock_6']:
    shape['polygon'][0][1]=1.63;shape['polygon'][1][1]=1.61
  elif preset['hair_style']=='loose':
   if feature=='hair_rear_mass':
    if shape['kind']=='box':shape['min'][1]=1.21
    else:
     for p in shape['polygon']:p[1]=1.21+(p[1]-1.43)*(1.70-1.21)/(1.70-1.43)
   if feature.startswith('rear_silver_strand_'):
    if shape['kind']=='box':shape['min'][1]=1.23
    else:
     for p in shape['polygon']:p[1]=1.23+(p[1]-1.43)*(1.72-1.23)/(1.72-1.43)
  if preset['outfit']!='traveller_tunic' and op['part'].startswith('skirt_'):
   # Short work hem or straight guard tabard; interpolate the same garment slot.
   low=.78 if preset['outfit']=='work_tunic' else .70
   if shape['kind']=='extrusion':
    for p in shape['polygon']:
     if p[1]<.99:p[1]=low+(p[1]-.62)*(.99-low)/(.99-.62)
   elif shape['kind']=='box':
    for bound in ['min','max']:
     if shape[bound][1]<.99:shape[bound][1]=low+(shape[bound][1]-.62)*(.99-low)/(.99-.62)
 component['parts']=[p for p in component['parts'] if p['id'] not in removed]
 component['operations']=[o for o in component['operations'] if o['part'] not in removed]
 rig['parts']=[p for p in rig['parts'] if p['id'] not in removed]
 for channel in rig['motion_channels']:
  rig['motion_channels'][channel]=[p for p in rig['motion_channels'][channel] if p not in removed]
 scale=contract['body_frames'][preset['body_frame']]
 def xyz(v):return [round(v[i]*scale[i],8) for i in range(3)]
 for p in component['parts']:p['pivot']=xyz(p['pivot'])
 for p in rig['parts']:p['pivot_m']=xyz(p['pivot_m'])
 for op in component['operations']:
  shape=op['shape']
  if shape['kind']=='box':shape['min']=xyz(shape['min']);shape['max']=xyz(shape['max'])
  elif shape['kind']=='extrusion':
   shape['polygon']=[[round(x*scale[0],8),round(y*scale[1],8)] for x,y in shape['polygon']]
   shape['z_min']*=scale[2];shape['z_max']*=scale[2]
  else:raise ValueError('unsupported shape transformation, do not silently drop')
 for s in rig['sockets'].values():s['offset_m']=xyz(s['offset_m'])
 rig['capsule']['radius_m']*=max(scale[0],scale[2]);rig['capsule']['height_m']*=scale[1];rig['capsule']['center_m']=xyz(rig['capsule']['center_m'])
 master['extensions']['appearance']={'family':preset['family'],'preset':copy.deepcopy(preset),'base_master_hash':base_hash}
 master['extensions']['dimensions']['standing_height_m']*=scale[1]
 master['extensions']['style']={'kind':'shared appearance variant','preset_id':preset['id']}
 h=digest(master)
 for name,data in sources.items():
  if name=='master.json':continue
  data['source_id']=master['id'];data['master_hash']=h
  if 'tracks' in data:
   data['tracks']=[t for t in data['tracks'] if t['selector']['part'] not in removed]
   for t in data['tracks']:
    for k in t['keys']:k['translation']=xyz(k['translation'])
 return sources
