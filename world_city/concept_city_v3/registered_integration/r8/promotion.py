"""Small scene-promotion guards. Reuse the existing common placement/terrain tools.

This file does not compile geometry. Triangle rebinding alone is not a spatial
compatibility proof: producers must additionally verify exact owner/route masks.
"""
import copy
from collections import defaultdict
from ..r6 import apply_packs as a
from ...registered_topography.revisions.r15_merchant_local_patch.frozen import canonical_sha

SEMANTIC_ROOFS={'clay_red','wood_brown','slate_gray'}

def explicit_retirements(pack):
    """Read both supported, explicit producer retirement contracts.

    A producer's replacement ledger is operational input, not merely prose.
    If both schemas are populated they must agree; never guess which wins.
    Unknown runtime IDs remain an error in the existing common pack applier.
    """
    def ids(value, name):
        if not isinstance(value,list) or any(not isinstance(v,str) or not v for v in value):
            raise ValueError('Invalid retirement ID list: '+name)
        if len(value)!=len(set(value)):raise ValueError('Duplicate retirement ID: '+name)
        return set(value)
    canonical=ids(pack.get('replaced_placement_ids',[]),'replaced_placement_ids')
    ledger=pack.get('replacement_ledger',{})
    if not isinstance(ledger,dict):raise ValueError('Invalid replacement ledger')
    declared=ids(ledger.get('existing_native_placements_removed',[]),'replacement_ledger.existing_native_placements_removed')
    if canonical and declared and canonical!=declared:
        raise ValueError('Conflicting explicit retirement contracts')
    return sorted(canonical|declared)

def palette_catalog(scene):
    result={}
    for p in scene['common_instances']:
        key=p.get('palette_id');value=p.get('palette_override')
        if key not in SEMANTIC_ROOFS or not value:continue
        if key in result and result[key]!=value:raise ValueError('Ambiguous existing semantic palette '+key)
        result[key]=copy.deepcopy(value)
    if SEMANTIC_ROOFS-set(result):raise ValueError('Missing established roof palette')
    return result


def resolve_palettes(pack,catalog):
    """Prevent a named clay/wood/slate instance silently showing native teal."""
    out=copy.deepcopy(pack);records=[]
    for p in out['placements']:
        key=p.get('palette_id')
        if key not in SEMANTIC_ROOFS:continue
        expected=catalog[key];old=p.get('palette_override')
        if old and old!=expected:raise ValueError('Semantic palette changes approved mapping: '+p['id'])
        p['palette_override']=copy.deepcopy(expected)
        records.append(dict(id=p['id'],palette_id=key,mapping_sha256=a.digest(expected),was_explicit=bool(old)))
    return out,records


def triangle_key(tri):return tuple(tuple(v) for v in tri)


def rebind_unchanged_triangles(patch,old_scene,new_scene,old_sha,new_sha):
    """Translate source indices only when full ordered triangles remain identical.

    No coordinate tolerance, projection, nearest match, winding reversal or
    replacement geometry change is permitted. Duplicate matching triangles are
    ambiguous and rejected. Source hashes must first validate against old scene.
    """
    if patch['base_scene_sha256']!=old_sha:raise ValueError('Wrong old scene binding')
    by_material=defaultdict(list)
    for row in patch['surface_edits']:by_material[row['material']].append(row)
    out=copy.deepcopy(patch);new_rows=[];ledger=[]
    for material,rows in by_material.items():
        old=old_scene['surfaces'][material];new=new_scene['surfaces'][material]
        if canonical_sha(old)!=patch['source_surface_hashes'][material]:raise ValueError('Wrong old surface hash')
        identical_surface = old == new
        required={};seen=set()
        for row in rows:
            index=row['triangle_index']
            if not isinstance(index,int) or index<0 or index>=len(old)//3:raise ValueError('Invalid old index')
            if index in seen:raise ValueError('Duplicate old edit')
            seen.add(index);tri=old[index*3:index*3+3]
            if canonical_sha(tri)!=row['source_triangle_sha256']:raise ValueError('Wrong old triangle hash')
            required[triangle_key(tri)]=[]
        for index in range(len(new)//3):
            key=triangle_key(new[index*3:index*3+3])
            if key in required:required[key].append(index)
        for row in rows:
            tri=old[row['triangle_index']*3:row['triangle_index']*3+3]
            # Full ordered-array identity proves index identity even when the
            # original contains equal triangles. Never choose among duplicates
            # after any array change.
            matches=[row['triangle_index']] if identical_surface else required[triangle_key(tri)]
            if len(matches)!=1:raise ValueError('Changed or ambiguous exact source triangle: '+str((material,row['triangle_index'],matches)))
            q=copy.deepcopy(row);q['triangle_index']=matches[0];new_rows.append(q)
            ledger.append(dict(material=material,old_index=row['triangle_index'],new_index=matches[0],source_triangle_sha256=row['source_triangle_sha256']))
    out['surface_edits']=new_rows
    out['source_surface_hashes']={m:canonical_sha(new_scene['surfaces'][m]) for m in by_material}
    out['base_scene_sha256']=new_sha
    out['rebind_provenance']=dict(old_scene_sha256=old_sha,new_scene_sha256=new_sha,ordered_xyz_unchanged=True,index_ledger=ledger,spatial_compatibility='Must be independently verified from producer ownership and route masks.')
    return out
