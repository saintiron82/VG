"""Resolve existing semantic palette IDs without changing native geometry."""
import copy,json
from ..r6 import apply_packs as a

SOURCE=a.CITY/'evidence/visual_registered_common_r7/scene.json'
SOURCE_SHA='07af0d0f1913fe6b6749475c877dbd6d1e6f4bd590a5576d1d0628b37084d363'
PACK=a.CITY/'assemblies/ordinary/registered/working_ranges_r01/resolved_placements.json'

def resolve(scene):
    ids={p['id'] for p in a.load(PACK,'57577354dd51455f49b836e5e65e628ec9d0988888647d3f5f42e034dd9aba07')['placements']}
    palettes={};sources={}
    for p in scene['common_instances']:
        if p['id'] in ids or not p.get('palette_override'):continue
        name=p['palette_id'];value=p['palette_override']
        if name not in ('clay_red','wood_brown','slate_gray'):continue
        if name in palettes and palettes[name]!=value:raise ValueError('Ambiguous existing palette '+name)
        palettes[name]=value;sources.setdefault(name,p['id'])
    out=dict(scene);out['common_instances']=list(scene['common_instances']);records=[]
    for i,p in enumerate(scene['common_instances']):
        if p['id'] not in ids:continue
        if p.get('palette_override'):raise ValueError('Do not overwrite an existing palette binding')
        q=dict(p);q['palette_override']=copy.deepcopy(palettes[p['palette_id']]);out['common_instances'][i]=q
        records.append(dict(id=p['id'],palette_id=p['palette_id'],existing_reference_id=sources[p['palette_id']],palette_override=q['palette_override']))
        assert {k:v for k,v in q.items() if k!='palette_override'}=={k:v for k,v in p.items() if k!='palette_override'}
    assert len(records)==4
    assert all(out[k]==scene[k] for k in scene if k!='common_instances')
    a.validate_instances(out)
    return out,records

def main():
    scene=a.load(SOURCE,SOURCE_SHA);out,records=resolve(scene)
    dest=a.CITY/'evidence/visual_registered_common_r7_palette_r01';dest.mkdir(exist_ok=True)
    path=dest/'scene.json';assert not path.exists();path.write_text(json.dumps(out,separators=(',',':'),allow_nan=False)+'\n')
    report=dict(source_scene_sha256=SOURCE_SHA,scene_sha256=a.sha(path),
        source_bug='Semantic palette IDs were present, but explicit runtime overrides were omitted. Renderer requires both.',
        changed_instances=records,all_non_palette_instance_fields_identical=True,all_other_scene_fields_identical=True,
        native_asset_bytes_unchanged=True,terrain_and_collision_and_doors_unchanged=True,
        route_result_scope='Same geometry as sealed 36/36 R7 replay; only four existing material mappings are now explicit.',
        source_and_failed_visual_preserved=True,actual_capture='pending')
    (dest/'palette_binding_review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
