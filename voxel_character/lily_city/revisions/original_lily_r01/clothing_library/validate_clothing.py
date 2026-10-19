#!/usr/bin/env python3
"""Validate and compose clothing source operations, never compile or alter a body."""
from __future__ import annotations
from copy import deepcopy
import json
import math
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent

class ClothingValidationError(ValueError):
    pass

def read_json(name):
    return json.loads((ROOT/name).read_text(encoding='utf-8'))

def load_module(module_id):
    catalog=read_json('catalog.json')
    records={entry['id']:entry for entry in catalog['modules']}
    if module_id not in records:
        raise ClothingValidationError(f'Unknown clothing module: {module_id}')
    return read_json(records[module_id]['path'])

def signed_area(poly):
    return sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1]))/2

def validate_module(module):
    rules=read_json('validation_rules.json')
    errors=[]
    for key in rules['required_module_fields']:
        if key not in module: errors.append(f'Missing required field: {key}')
    if errors: return errors
    ident=module['id']
    if not module['allowed_age_frames'] or not set(module['allowed_age_frames']) <= set(rules['allowed_age_frames']):
        errors.append(f'{ident}: invalid age frames')
    if not module['ops'] and not module.get('optional_empty'):
        errors.append(f'{ident}: no geometry without explicit optional_empty')
    ids=set()
    for op in module['ops']:
        name=op.get('id','<missing>')
        if name in ids: errors.append(f'{ident}: duplicate operation ID {name}')
        ids.add(name)
        if op.get('part') not in rules['allowed_parts']: errors.append(f'{name}: unknown or body-only part')
        if op.get('material') not in rules['allowed_materials']: errors.append(f'{name}: noncanonical material')
        if op.get('action')!='paint': errors.append(f'{name}: unsupported operation')
        s=op.get('shape',{}); kind=s.get('kind')
        try:
            if kind=='box':
                lo,hi=s['min'],s['max']; nums=lo+hi
                if len(lo)!=3 or len(hi)!=3 or not all(a<b for a,b in zip(lo,hi)): errors.append(f'{name}: invalid box bounds')
                if s.get('minimum_cells') != [1,1,1]: errors.append(f'{name}: invalid box minimum_cells')
                xs=[lo[0],hi[0]]; zs=[lo[2],hi[2]]
            elif kind=='extrusion':
                poly=s['polygon']; nums=[v for p in poly for v in p]+[s['z_min'],s['z_max']]
                if len(poly)<3 or any(len(p)!=2 for p in poly) or abs(signed_area(poly))<1e-8: errors.append(f'{name}: degenerate polygon')
                if s['z_min']>=s['z_max']: errors.append(f'{name}: invalid extrusion depth')
                if s.get('minimum_cells')!=1: errors.append(f'{name}: invalid extrusion minimum_cells')
                xs=[p[0] for p in poly];zs=[s['z_min'],s['z_max']]
            else:
                errors.append(f'{name}: unsupported shape {kind}');continue
            if not all(isinstance(v,(int,float)) and math.isfinite(v) for v in nums): errors.append(f'{name}: nonfinite coordinate')
            if op['part'] in ['skirt_left','skirt_right']:
                # Either a thin front/rear leaf or a side return outside the leg envelope.
                # Any center-spanning solid prism at lower-body level is rejected.
                if op['part']=='skirt_left' and max(xs)>0: errors.append(f'{name}: left cloth crosses center')
                if op['part']=='skirt_right' and min(xs)<0: errors.append(f'{name}: right cloth crosses center')
                if max(zs)-min(zs)>rules['maximum_shell_depth_m']:
                    if min(abs(x) for x in xs)<.15: errors.append(f'{name}: solid lower cloth blocks the leg interior')
                elif min(abs(z) for z in zs)<rules['minimum_front_rear_skirt_shell_inner_z_m']:
                    errors.append(f'{name}: front/rear cloth is too close to leg interior')
        except (KeyError,TypeError,IndexError): errors.append(f'{name}: malformed shape')
    coverage=rules.get('pelvis_coverage',{})
    if ident in coverage.get('required_for',[]):
        for face in ['front','rear','left','right']:
            matches=[op for op in module['ops'] if '_pelvis_'+face in op['id'] and op['part']=='pelvis']
            if not matches: errors.append(f'{ident}: missing opaque pelvis coverage {face}')
            for op in matches:
                s=op['shape']
                if s.get('kind')!='box' or s['min'][1]>.825 or s['max'][1]<1.05:
                    errors.append(f'{ident}: incomplete pelvis coverage {face}')
    return errors

def validate_outfit(module_ids: Iterable[str], age_frame: str):
    rules=read_json('validation_rules.json');errors=[];slots={};modules=[]
    if age_frame not in rules['allowed_age_frames']: errors.append('Unknown age frame: '+age_frame)
    module_ids=list(module_ids)
    if len(module_ids)!=len(set(module_ids)): errors.append('Duplicate module selected')
    for mid in module_ids:
        try: m=load_module(mid)
        except ClothingValidationError as e: errors.append(str(e));continue
        modules.append(m);errors.extend(validate_module(m))
        if age_frame not in m['allowed_age_frames']: errors.append(f'{mid} does not allow {age_frame}')
        for slot in m['slots']:
            if slot in slots: errors.append(f'Slot {slot} is occupied by both {slots[slot]} and {mid}')
            slots[slot]=mid
    for slot in rules['required_outfit_slots']:
        if slot not in slots: errors.append(f'Missing required slot: {slot}')
    for a,b in rules['clashing_pairs']:
        if a in module_ids and b in module_ids: errors.append(f'Clashing modules: {a}, {b}')
    for m in modules:
        for slot in m.get('requires_slots',[]):
            if slot not in slots: errors.append(f'{m["id"]} requires slot {slot}')
        allowed=m.get('requires_sleeve_options')
        if allowed and slots.get('sleeves') not in allowed: errors.append(f'{m["id"]} requires one of {allowed}')
    return errors

def compose_outfit(module_ids: Iterable[str], age_frame: str):
    """Return untouched canonical ops. Caller owns body-specific transforms/remapping.

    No module is recolored, no skeleton is changed, and no file is written.
    Multi-slot modules are applied once, in a stable order.
    """
    module_ids=list(module_ids);errors=validate_outfit(module_ids,age_frame)
    if errors: raise ClothingValidationError('\n'.join(errors))
    order=read_json('catalog.json')['assembly_order'];rank={s:i for i,s in enumerate(order)}
    modules=sorted([load_module(mid) for mid in module_ids],key=lambda m:(min(rank[s] for s in m['slots']),m['id']))
    ops=[];attachments={}
    for m in modules:
        ops.extend(deepcopy(m['ops']))
        for p in m['attachment_parts']:
            if p['id'] in attachments and p != attachments[p['id']]:
                raise ClothingValidationError('Conflicting attachment part: '+p['id'])
            attachments[p['id']]=deepcopy(p)
    return {'schema':'riverstone.clothing.composition.v1','age_frame':age_frame,
        'coordinate_space':'original_adult_bind_m','frame_transform_required':True,
        'module_ids':[m['id'] for m in modules], 'ops':ops,'attachment_parts':list(attachments.values())}

def validate_library():
    catalog=read_json('catalog.json'); errors=[];all_op_ids=set()
    for entry in catalog['modules']:
        m=load_module(entry['id']);errors.extend(validate_module(m))
        if entry['operation_count']!=len(m['ops']): errors.append('Stale catalog operation count: '+m['id'])
        if entry['allowed_age_frames']!=m['allowed_age_frames']: errors.append('Stale catalog age frames: '+m['id'])
        for op in m['ops']:
            if op['id'] in all_op_ids: errors.append('Cross-module duplicate ID: '+op['id'])
            all_op_ids.add(op['id'])
    for outfit in read_json('outfit_examples.json')['outfits']:
        errors.extend(outfit['id']+': '+e for e in validate_outfit(outfit['modules'],outfit['age_frame']))
    return errors

if __name__=='__main__':
    errors=validate_library()
    if errors:
        for error in errors: print('ERROR:',error)
        raise SystemExit(1)
    c=read_json('catalog.json')
    print(f'PASS: {len(c["modules"])} modules, {len(c["example_outfits"])} complete silhouette combinations, all required slot selections.')
