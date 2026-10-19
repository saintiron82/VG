"""Independent part layers from one common master, plus a separate transform clip.

Authored operations are partitioned before sampling; moving parts retain hidden
faces and occupancy even when the closed-pose static composite would hide them.
No asset-name dispatch. The track values/time never enter geometry generation.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from core import compile_master, digest, transform, compose, apply, require, number, vector
from render_data import make_render_data


def bindings_from(master, clip):
    require(clip.get('schema') == 'riverstone.voxel.transform_animation.v1', 'unsupported animation schema')
    require(clip.get('source_id') == master['id'], 'clip source_id mismatch')
    require(clip.get('master_hash') == digest(master), 'clip must bind the exact original master')
    require(isinstance(clip.get('tracks'), list) and bool(clip['tracks']), 'tracks required')
    components={c['id']:c for c in master['components']}
    instances={i['id']:i for i in master['instances']}
    world={}
    def world_transform(key):
        if key not in world:
            instance=instances[key]
            value=transform(instance.get('transform'))
            if instance.get('parent') is not None:value=compose(world_transform(instance['parent']),value)
            world[key]=value
        return world[key]
    result=[];used=set()
    for track in clip['tracks']:
        selector=track.get('selector')
        require(isinstance(selector,dict) and set(selector)=={'instance','part'},'explicit instance+part selector required')
        key=tuple(selector[k] for k in ('instance','part'))
        require(key not in used,'duplicate target track');used.add(key)
        require(key[0] in instances,'unknown target instance')
        component=components[instances[key[0]]['component']]
        parts={p['id']:p for p in component['parts']}
        require(key[1] in parts,'unknown target part')
        placement=world_transform(key[0])
        result.append({'selector':copy.deepcopy(selector),'pivot_world':apply(placement,parts[key[1]]['pivot']),
                       'source_world_basis':placement['basis'],'part_metadata':copy.deepcopy(parts[key[1]].get('metadata',{}))})
    return result


def isolate(master, selectors, moving):
    """Keep each instance hierarchy, select paints, preserve all cuts and metadata.

    Cut operations still act on their declared selectors. Components are cloned
    per instance so editing one instance's binding never changes another copy.
    Constraints on the full asset are not misrepresented as subset checks.
    """
    result=copy.deepcopy(master)
    components={c['id']:c for c in master['components']}
    clones={key:[] for key in components}
    for index,instance in enumerate(master['instances']):
        clones[instance['component']].append(f'isolated_component_{index}')
    def remap_component_selector(operation):
        selector=operation.get('selector',{})
        if 'component' in selector:
            original=selector['component']
            source_ids=original if isinstance(original,list) else [original]
            # Unreferenced/unknown IDs remain nonmatching, even if their text
            # happens to equal a generated clone ID.
            selector['component']=[clone for key in source_ids for clone in clones.get(key,[])]
    result['components']=[]
    for index,instance in enumerate(result['instances']):
        source=components[instance['component']]
        component=copy.deepcopy(source)
        component['id']=f'isolated_component_{index}'
        component['operations']=[op for op in component['operations'] if op['action']=='cut' or (((instance['id'],op['part']) in selectors)==moving)]
        for operation in component['operations']:remap_component_selector(operation)
        result['components'].append(component)
        instance['component']=component['id']
    for operation in result.get('assembly_cuts',[]):remap_component_selector(operation)
    result['constraints']=[]
    return result


def make_animated_render(master, clip, pitch, max_candidates=5_000_000):
    bindings=bindings_from(master,clip)
    selectors={tuple(b['selector'][k] for k in ('instance','part')) for b in bindings}
    layers=[]
    for selector in [None,*bindings]:
        selected=selectors if selector is None else {tuple(selector['selector'][k] for k in ('instance','part'))}
        layer_master=isolate(master,selected,selector is not None)
        compiled=compile_master(layer_master,{'pitch':pitch},max_candidate_cells=max_candidates)
        if selector is not None:require(bool(compiled['cells']),'animated part vanished at requested pitch')
        render=make_render_data(compiled) if compiled['cells'] else None
        layers.append({'binding':selector,'render':render,'provenance':{'derived_master_hash':compiled['master_hash'],
            'payload_hash':compiled['payload_hash'],'compiler_source_hash':compiled['compiler_source_hash'],
            'cell_count':len(compiled['cells']),'candidate_cells':compiled['candidate_cells']}})
    visible=[layer['render'] for layer in layers if layer['render'] is not None]
    require(bool(visible),'empty render')
    bounds={'min':[min(r['bounds']['min'][i] for r in visible) for i in range(3)],
            'max':[max(r['bounds']['max'][i] for r in visible) for i in range(3)]}
    parts=[{**layer['binding'],'groups':layer['render']['groups'],'bounds':layer['render']['bounds'],
            'cell_count':layer['render']['cell_count'],'payload_hash':layer['render']['payload_hash']} for layer in layers[1:]]
    return {'schema':'riverstone.voxel.render.v1','unit':'m','source_id':master['id'],'source_revision':master['revision'],
            'master_hash':digest(master),'payload_hash':digest([l['provenance']['payload_hash'] for l in layers]),
            'pitch':pitch,'grid_origin':master.get('grid_origin',[0,0,0]),'materials':copy.deepcopy(master['materials']),
            'bounds':bounds,'cell_count':sum(l['provenance']['cell_count'] for l in layers),
            'groups':layers[0]['render']['groups'] if layers[0]['render'] else [],'rigid_parts':parts,
            'quad_count':sum(r['quad_count'] for r in visible),
            'geometry':'Independent static and animated-selector layers directly sampled from one master. World-space quads; runtime rotates immutable rest geometry about the master part pivot. No occupancy animation.',
            'provenance':{'original_master_hash':digest(master),'binding_hash':digest([b['selector'] for b in bindings]),
                'builder_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                'layers':[{'selector':l['binding']['selector'] if l['binding'] else None,**l['provenance']} for l in layers]}}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('master',type=Path)
    parser.add_argument('--clip',required=True,type=Path)
    parser.add_argument('--pitch',type=float,required=True)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--max-candidates',type=int,default=5_000_000)
    args=parser.parse_args();start=time.perf_counter()
    master=json.loads(args.master.read_text());clip=json.loads(args.clip.read_text())
    result=make_animated_render(master,clip,args.pitch,args.max_candidates)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as stream:json.dump(result,stream,sort_keys=True,separators=(',',':'));stream.write('\n')
    print(json.dumps({'output':str(args.output),'seconds':time.perf_counter()-start,'pitch':args.pitch,
        'master_hash':result['master_hash'],'payload_hash':result['payload_hash'],'cell_count':result['cell_count'],
        'quad_count':result['quad_count'],'parts':[{k:p[k] for k in ('selector','pivot_world','cell_count')} for p in result['rigid_parts']]}))

if __name__=='__main__':main()
