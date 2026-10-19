"""Read-only appearance-family regression checks, reusing common validators.
No mesh compilation, runtime actors, source edits or scheduler imports.
"""
from __future__ import annotations
import copy, json, math, sys
from pathlib import Path
from presets import HERE,LILY,read,digest,appearance_module
sys.path.insert(0,str(HERE.parent/'common'/'animation'))
from build_render import bindings_from
from core import validate_master

def validate_derived(preset,sources,canonical_sources=None):
    contract=read(LILY/'data/appearance_contract.json')
    canonical_sources=canonical_sources or appearance_module().load_sources()
    master=sources['master.json'];rig=sources['rig.json'];component=master['components'][0]
    validate_master(master,.02)
    if master['extensions']['appearance']['base_master_hash']!=digest(canonical_sources['master.json']): raise ValueError('canonical base source binding mismatch')
    if master['extensions']['appearance']['preset']!=preset: raise ValueError('preset provenance mismatch')
    ids={p['id'] for p in component['parts']};rigids={p['id'] for p in rig['parts']}
    if ids!=rigids or len(ids)!=len(rig['parts']): raise ValueError('master/rig part mismatch')
    if not set(contract['required_parts'])<=ids: raise ValueError('missing required rig part')
    expected_optional={'braid'} if preset['hair_style']=='braided' else set()
    expected_optional|={k for k in ['cape','satchel'] if preset['accessories'].get(k,True)}
    if ids&set(contract['optional_parts'])!=expected_optional: raise ValueError('optional geometry mismatch')
    seen=set()
    for part in rig['parts']:
        if part['parent'] is not None and part['parent'] not in seen: raise ValueError('non-topological or cyclic rig')
        if part['id'] in seen: raise ValueError('duplicate rig part')
        seen.add(part['id'])
        pivot=next(p['pivot'] for p in component['parts'] if p['id']==part['id'])
        if part['pivot_m']!=pivot: raise ValueError('pivot mismatch')
    scale=contract['body_frames'][preset['body_frame']]
    canonical_rig=canonical_sources['rig.json']
    if set(rig['sockets'])!=set(contract['sockets']): raise ValueError('socket set mismatch')
    for name,socket in rig['sockets'].items():
        if socket['part'] not in ids: raise ValueError('orphan socket')
        expected=[round(v*scale[i],8) for i,v in enumerate(canonical_rig['sockets'][name]['offset_m'])]
        if socket['offset_m']!=expected: raise ValueError('socket body scaling mismatch')
    channel_ids=[p for parts in rig['motion_channels'].values() for p in parts]
    if len(channel_ids)!=len(set(channel_ids)) or set(channel_ids)!=ids: raise ValueError('motion channel partition mismatch')
    source_hash=digest(master);clips={}
    for name,data in sources.items():
        if name=='master.json': continue
        if data['master_hash']!=source_hash or data['source_id']!=master['id']: raise ValueError('stale sidecar source binding')
        if 'tracks' not in data: continue
        bindings=bindings_from(master,data)
        for track in data['tracks']:
            times=[k['time'] for k in track['keys']]
            if times!=sorted(times) or len(times)!=len(set(times)): raise ValueError('invalid animation key times')
            if times[0]<0 or times[-1]>data['duration']+1e-9: raise ValueError('animation outside duration')
            for key in track['keys']:
                if not all(math.isfinite(v) for v in key['translation']+[key['rotation_degrees']]): raise ValueError('nonfinite animation')
            if data['loop']:
                first,last=track['keys'][0],track['keys'][-1]
                if first['translation']!=last['translation'] or first['rotation_degrees']!=last['rotation_degrees']: raise ValueError('open animation loop')
        clips[name]={'tracks':len(bindings),'duration':data['duration'],'sha256':digest(data)}
    required_clips={name+'.json' for name in contract['supported_animations']}
    if not required_clips<=set(clips): raise ValueError('missing supported animation')
    walk_parts={t['selector']['part'] for t in sources['walk.json']['tracks']}
    if not set(rig['motion_channels']['locomotion'])<=walk_parts: raise ValueError('walk missing live locomotion part')
    if master['materials']!={**canonical_sources['master.json']['materials'],**{k:v.lstrip('#').lower() for k,v in preset['palette'].items()}}: raise ValueError('palette mapping mismatch')
    return {'preset_id':preset['id'],'body_frame':preset['body_frame'],'face':preset['face'],'hair_style':preset['hair_style'],'outfit':preset['outfit'],
      'accessories':preset['accessories'],'parts':len(ids),'source_master_sha256':source_hash,'rig_sha256':digest(rig),'sockets':sorted(rig['sockets']),
      'clips':clips,'status':'pass','geometry_compiled':False,'visual_reviewed':False}
