"""Bounded 1 m shared surface modules. JSON rules -> common master -> common mesh.

Never compile a city volume at fine pitch. Every variant is independently compiled,
validated, exported and released before the next. Only this directory is writable.
"""
from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import math
import re
import resource
import sys
import time
from functools import lru_cache
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
sys.path.insert(0, str(ROOT / 'voxel_character' / 'common'))
from core import compile_master, digest
from render_data import make_render_data

EPS = 1e-8
AXES = {'up': '+Y', 'front': '+Z', 'right': '+X'}
KINDS = ('ashlar', 'rubble', 'planks', 'paving')
SLOTS = {
    'ashlar': ('masonry.base', 'masonry.light', 'masonry.dark'),
    'rubble': ('masonry.base', 'masonry.light', 'masonry.dark'),
    'paving': ('paving.warm', 'paving.cool', 'paving.light', 'paving.dark'),
    'planks': ('wood.base', 'wood.warm', 'wood.light'),
}

def require(ok, message):
    if not ok:
        raise ValueError(message)


def finite(n):
    return type(n) in (int, float) and math.isfinite(n)


def aligned(n, pitch, origin=0):
    return finite(n) and abs((n-origin)/pitch-round((n-origin)/pitch)) < EPS


def r(n):
    return round(n, 9)


def stable(*parts):
    return int(hashlib.sha256('|'.join(map(str, parts)).encode()).hexdigest()[:16], 16)


def bounds_rect(spec):
    t = spec['trim']
    return [0.0, 0.0, t['width_m'], t['height_m']]


def rect_overlap(a, b):
    return min(a[2], b[2])-max(a[0], b[0]) > EPS and min(a[3], b[3])-max(a[1], b[1]) > EPS


def course_partitions(widths, pitch):
    """Periodic one-metre bond; fixed wrapped edge stone, seeded interior."""
    units = tuple(sorted(set(round(x/pitch) for x in widths)))
    first = round(widths[0]/pitch)
    @lru_cache(None)
    def tails(remaining):
        if remaining == 0:
            return ((),)
        return tuple((n,)+tail for n in units if n <= remaining for tail in tails(remaining-n))
    return [tuple(r(n*pitch) for n in (first,)+tail) for tail in tails(round(1/pitch)-first)]


def validate_rules(spec):
    require(spec.get('schema') == 'riverstone.shared_surface.rules.v1', 'unsupported rules schema')
    require(type(spec.get('revision')) is int and spec['revision'] > 0, 'positive integer revision required')
    require('variant_family' not in spec or isinstance(spec['variant_family'],str) and re.fullmatch('[a-z][a-z0-9_]{0,40}',spec['variant_family']), 'variant family must be a short safe identifier')
    p = spec['pitch_m']
    require(p == 0.0125, 'this revision requires 0.0125 m pitch; regenerate with a reviewed revision for any other pitch')
    require(spec['module_size_m'] == [1, 1], 'shared source tile must remain exactly 1 x 1 m')
    trim = spec['trim']
    require(isinstance(trim, dict) and set(trim) == {'width_m', 'height_m', 'offset_m'}, 'trim requires width_m, height_m and offset_m')
    require(isinstance(trim['offset_m'], list) and len(trim['offset_m']) == 2, 'trim offset requires XY')
    for size, offset in zip((trim['width_m'], trim['height_m']), trim['offset_m']):
        require(finite(size) and p <= size <= 1 and aligned(size, p), 'trim dimensions must be positive, <=1 m and grid aligned')
        require(finite(offset) and offset >= 0 and offset+size <= 1+EPS and aligned(offset, p), 'trim offset must be nonnegative, grid aligned and stay inside the source tile')
    require(isinstance(spec['holes'], list), 'holes must be a list of local XY rectangles')
    outer = bounds_rect(spec)
    for i, hole in enumerate(spec['holes']):
        require(isinstance(hole, dict) and set(hole) == {'rect'}, 'holes support only explicit axis-aligned rect, not unchecked polygons')
        q = hole['rect']
        require(isinstance(q, list) and len(q) == 4 and all(finite(v) and aligned(v, p) for v in q), 'hole boundaries must be finite and grid aligned')
        require(0 <= q[0] < q[2] <= outer[2] and 0 <= q[1] < q[3] <= outer[3], 'hole must have positive area and stay in trimmed local XY bounds')
        require(not any(rect_overlap(q, h['rect']) for h in spec['holes'][:i]), 'hole interiors must not overlap')
    require(allowed_rectangles(spec), 'holes leave no occupied footprint')
    require(isinstance(spec['seeds'], list) and 1 <= len(spec['seeds']) <= 4 and all(type(s) is int for s in spec['seeds']), 'one to four integer seeds required')
    require(len(set(spec['seeds'])) == len(spec['seeds']), 'seed variants must be unique')
    require(isinstance(spec['kinds'], list) and spec['kinds'] and set(spec['kinds']) <= set(KINDS) and len(set(spec['kinds'])) == len(spec['kinds']), 'unique supported kinds required')
    required_slots = set(sum((list(SLOTS[k]) for k in KINDS), [])) | {'masonry.joint', 'paving.joint', 'wood.joint', 'metal.iron'}
    require(required_slots <= set(spec['materials']) and all(isinstance(v, str) and re.fullmatch('[0-9a-fA-F]{6}', v) for v in spec['materials'].values()), 'semantic palette slots require six-digit RGB values')
    g = spec['geometry']
    require(g['joint_width_m'] == .025 and g['mortar_top_z_m'] == -.025 and g['back_z_m'] == -.0375, 'shallow joints and back-plane heights are fixed in this revision')
    require(g['bevel_inset_m'] == p, 'one-pitch geometric bevel required')
    for k in ('ashlar', 'rubble', 'paving'):
        v = g[k]
        require(finite(v['course_height_m']) and .15 <= v['course_height_m'] <= .5 and aligned(v['course_height_m'], p) and aligned(1, v['course_height_m']), 'course height must divide 1 m exactly')
        require(isinstance(v['stone_widths_m'], list) and v['stone_widths_m'] and all(finite(x) and .15 <= x <= .5 and aligned(x, p) for x in v['stone_widths_m']), 'stone widths must resolve within the bounded tile')
        require(len(v['stone_widths_m']) <= 8 and course_partitions(v['stone_widths_m'],p), 'stone width choices must form an exact 1 m periodic course')
        require(finite(v['corner_clip_m']) and p <= v['corner_clip_m'] <= .025 and aligned(v['corner_clip_m'], p), 'corner clip must be 0.0125..0.025 m')
        require(isinstance(v['face_z_choices_m'], list) and v['face_z_choices_m'] and all(finite(x) and 0 <= x <= .025 and aligned(x, p) for x in v['face_z_choices_m']), 'stone projection must be grid aligned and no more than 0.025 m')
    require(g['paving']['face_z_choices_m'] == [0], 'paving tops must remain exactly Z=0')
    v = g['planks']
    require(finite(v['plank_width_m']) and .15 <= v['plank_width_m'] <= .5 and aligned(1, v['plank_width_m']), 'plank width must divide 1 m')
    require(v['face_z_m'] == 0 and type(v['nails']) is bool, 'plank top is Z=0 and nails is boolean')
    require(v['nail_width_m'] == .025 and v['nail_projection_m'] == .0125, 'nails must stay small and shallow')
    caps = {'max_candidate_cells_per_module': 150000, 'max_output_cells_per_module': 50000, 'max_artifact_bytes': 20000000, 'max_rss_mib': 600}
    require(all(type(spec['budgets'].get(k)) is int and 0 < spec['budgets'][k] <= cap for k, cap in caps.items()), 'budgets must be positive and cannot expand the approved envelope')
    return spec


def allowed_rectangles(spec):
    """A small exact grid footprint partition, not an alternate volume sampler."""
    p = spec['pitch_m']; w, h = spec['trim']['width_m'], spec['trim']['height_m']
    nx, ny = round(w/p), round(h/p)
    active, result = {}, []
    for y in range(ny):
        row = [x for x in range(nx) if not any(rect_overlap([x*p, y*p, (x+1)*p, (y+1)*p], q['rect']) for q in spec['holes'])]
        runs = []
        for x in row:
            if runs and runs[-1][1] == x:
                runs[-1][1] = x+1
            else:
                runs.append([x, x+1])
        fresh = {}
        for a, b in runs:
            key = (a, b)
            q = active.pop(key, [a, y, b, y])
            q[3] = y+1
            fresh[key] = q
        result.extend(active.values()); active = fresh
    result.extend(active.values())
    return [[r(v*p) for v in q] for q in sorted(result)]


def clip_polygon(points, rect):
    # Same Sutherland-Hodgman authoring operation as the approved lane author.
    result = points
    for axis, edge, sign in ((0, rect[0], 1), (0, rect[2], -1), (1, rect[1], 1), (1, rect[3], -1)):
        old, result = result, []
        if not old:
            break
        for a, b in zip(old[-1:]+old[:-1], old):
            inside_a, inside_b = sign*(a[axis]-edge) >= -EPS, sign*(b[axis]-edge) >= -EPS
            if inside_a != inside_b:
                t = (edge-a[axis])/(b[axis]-a[axis]); c = [a[k]+t*(b[k]-a[k]) for k in range(2)]; c[axis] = edge; result.append(c)
            if inside_b:
                result.append(b)
    return [[r(x), r(y)] for x, y in result]


def area(points):
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points, points[1:]+points[:1])))/2 if len(points) >= 3 else 0


def octagon(rect, inset, corner):
    a,b,c,d = rect; a+=inset; b+=inset; c-=inset; d-=inset
    if c-a <= EPS or d-b <= EPS:
        return []
    q = min(corner, (c-a)/4, (d-b)/4)
    return [[r(x),r(y)] for x,y in ((a+q,b),(c-q,b),(c,b+q),(c,d-q),(c-q,d),(a+q,d),(a,d-q),(a,b+q))]


def box(oid, lo, hi, material, part='joint', action='paint'):
    op = {'id': oid, 'part': part, 'action': action, 'shape': {'kind':'box','min':[r(v) for v in lo],'max':[r(v) for v in hi]}}
    if action == 'paint':
        op['material'] = material
    return op


def author(spec, kind, seed):
    """Return ordinary common-master data and a separate placement contract."""
    validate_rules(spec)
    require(kind in spec['kinds'] and seed in spec['seeds'], 'kind/seed must be declared in rules')
    p = spec['pitch_m']; g = spec['geometry']; width,height = spec['trim']['width_m'],spec['trim']['height_m']; ox,oy = spec['trim']['offset_m']
    trim_source = [ox,oy,ox+width,oy+height]
    joint = 'wood.joint' if kind == 'planks' else 'paving.joint' if kind == 'paving' else 'masonry.joint'
    used = set(SLOTS[kind]) | {joint} | ({'metal.iron'} if kind == 'planks' and g['planks']['nails'] else set())
    ops = [box('joint_bed',[0,0,g['back_z_m']],[width,height,g['mortar_top_z_m']],joint)]
    layout = []
    def add_polygon(oid, polygon, z0, z1, material, part):
        polygon = clip_polygon(polygon, trim_source)
        if area(polygon) > EPS:
            ops.append({'id':oid,'action':'paint','part':part,'material':material,'shape':{'kind':'extrusion','polygon':[[r(x-ox),r(y-oy)] for x,y in polygon],'z_min':r(z0),'z_max':r(z1)}})
    half = g['joint_width_m']/2
    if kind != 'planks':
        v = g[kind]; course = v['course_height_m']
        partitions = course_partitions(v['stone_widths_m'],p)
        for row in range(round(1/course)):
            lengths = partitions[stable(seed,kind,row,'partition')%len(partitions)]
            # The source repeats every metre. Its wrapped boundary stone uses a
            # seed-independent tone and relief so different variants match too.
            x = -lengths[0]/2 if row%2 else 0.0
            periodic = lengths+(lengths[0],) if row%2 else lengths
            for col,length in enumerate(periodic):
                token = stable(seed,kind,row,col)
                if row%2 and col in (0,len(periodic)-1):
                    token = stable('shared_boundary',kind,row)
                rect = [x+half, row*course+half, x+length-half, (row+1)*course-half]
                material = SLOTS[kind][(token//7)%len(SLOTS[kind])]
                top = v['face_z_choices_m'][(token//17)%len(v['face_z_choices_m'])]
                oid = f'stone_r{row:02}_c{col:02}'
                add_polygon(oid+'_shoulder',octagon(rect,0,v['corner_clip_m']),g['back_z_m'],top-p,material,'stone')
                add_polygon(oid+'_cap',octagon(rect,g['bevel_inset_m'],v['corner_clip_m']),top-p,top,material,'stone')
                layout.append({'id':oid,'source_rect':[r(n) for n in rect],'material':material,'face_z_m':top})
                x += length
    else:
        v = g[kind]
        for col in range(round(1/v['plank_width_m'])):
            x = col*v['plank_width_m']; rect = [x+half,half,x+v['plank_width_m']-half,1-half]
            tone = SLOTS[kind][stable(seed,kind,col)%len(SLOTS[kind])]
            oid = f'plank_{col:02}'
            add_polygon(oid,[[rect[0],rect[1]],[rect[2],rect[1]],[rect[2],rect[3]],[rect[0],rect[3]]],g['back_z_m'],0,tone,'wood')
            layout.append({'id':oid,'source_rect':[r(n) for n in rect],'material':tone,'face_z_m':0})
            if v['nails']:
                for end,y in enumerate((.075,.925)):
                    cx = x+v['plank_width_m']/2; radius = v['nail_width_m']/2
                    add_polygon(f'{oid}_nail_{end}',[[cx-radius,y-radius],[cx+radius,y-radius],[cx+radius,y+radius],[cx-radius,y+radius]],0,v['nail_projection_m'],'metal.iron','iron')
    max_z = .0125 if kind == 'planks' and g['planks']['nails'] else max(g[kind].get('face_z_choices_m',[0]))
    constraints = [{'id':'nonempty','kind':'nonempty','selector':{}}]
    for i,hole in enumerate(spec['holes']):
        a,b,c,d = hole['rect']; shape = {'kind':'box','min':[a,b,g['back_z_m']],'max':[c,d,max_z+p]}
        ops.append({'id':f'hole_{i:02}','part':'joint','action':'cut','shape':shape})
        constraints.append({'id':f'hole_{i:02}_empty','kind':'empty_region','selector':{},'shape':copy.deepcopy(shape)})
    family = spec.get('variant_family')
    ident = f'surface_{family+"_" if family else ""}{kind}_s{seed}'
    if spec['trim'] != {'width_m':1,'height_m':1,'offset_m':[0,0]} or spec['holes']:
        ident += '_trim_'+digest({'trim':spec['trim'],'holes':spec['holes']})[:10]
    master = {'schema':'riverstone.voxel.master.v1','id':ident,'revision':spec['revision'],'axes':AXES,'grid_origin':[0,0,0],
              'materials':{k:spec['materials'][k] for k in sorted(used)},
              'components':[{'id':'surface','parts':[{'id':x,'pivot':[0,0,0]} for x in ('joint','stone','wood','iron')], 'operations':ops}],
              'instances':[{'id':'surface','component':'surface'}],'assembly_cuts':[],'constraints':constraints,
              'extensions':{'shared_surface':{'kind':kind,'seed':seed,'rules_hash':digest(spec),'required_pitch_m':p,'local_surface_plane':'XY','outward_normal':[0,0,1],'layout':layout,'trim':copy.deepcopy(spec['trim']),'holes':copy.deepcopy(spec['holes'])}},
              'provenance':{'author':'author_surfaces.py','input':'JSON rules object identified by extensions.shared_surface.rules_hash','geometry':'Ordinary common occupancy, shared small surface only; no custom mesher or city-wide fine volume.'}}
    footprint = allowed_rectangles(spec)
    collision = {'mode':'reference_envelope_only','generate_from_render_mesh':False,'create_module_colliders_automatically':False,
                 'nominal_plane_z_m':0.0,'reference_prisms':[{'min':[q[0],q[1],-.1],'max':[q[2],q[3],0.0]} for q in footprint],
                 'integration':'Merge footprint with owner collision in its coordinate frame; preserve owner doors/holes. Existing continuous collision remains authoritative.'}
    contract = {'schema':'riverstone.shared_surface.placement.v1','module_id':ident,'kind':kind,'seed':seed,'render_file':f'{ident}.render.json',
                'local_frame':{'plane':'XY','right':[1,0,0],'up':[0,1,0],'normal':[0,0,1],'nominal_face_z_m':0,'grid_origin':[0,0,0]},
                'trim':copy.deepcopy(spec['trim']),'holes':copy.deepcopy(spec['holes']),
                'visual_max_bounds':{'min':[0,0,g['back_z_m']],'max':[width,height,max_z]},
                'front_height_contract':{'paving_top_z_m':0 if kind == 'paving' else None,'joint_top_z_m':-.025,'maximum_wall_projection_m':.025},
                'collision':collision,
                'placement_preconditions':{'basis':'proper orthonormal rotation, determinant +1; no reflection, shear or scale',
                    'translation':'finite XYZ; negative coordinates allowed; grid-merge requires inverse-basis translation aligned to pitch relative to owner grid_origin',
                    'standalone_mesh_instances':'any finite translation and proper rotation; no second voxel sampling',
                    'boundary':'trim dimensions, offsets and rectangular holes must align to local pitch; holes may touch outer edge but not overlap interiors',
                    'support_front_max_local_z_m':g['back_z_m'],'preserve_owner_collision':True},
                'floor_basis_rows':[[1,0,0],[0,0,1],[0,-1,0]],
                'floor_mapping':'local (x,y,z) -> world (x,z,-y); +Z normal becomes world +Y; translate in world Z to cover desired interval',
                'whole_city_application':False}
    return master, contract


def validate_placement(translation, basis, *, pitch=.0125, grid_origin=(0,0,0), grid_merge=False):
    require(finite(pitch) and pitch > 0, 'positive finite placement pitch required')
    require(isinstance(translation,(list,tuple)) and len(translation)==3 and all(finite(x) for x in translation),'finite XYZ translation required')
    require(isinstance(basis,list) and len(basis)==3 and all(isinstance(row,list) and len(row)==3 and all(finite(x) for x in row) for row in basis),'finite 3x3 basis required')
    require(all(abs(sum(a*b for a,b in zip(basis[i],basis[j]))-(i==j))<EPS for i in range(3) for j in range(3)),'basis must be orthonormal; no scaling or shear')
    a=basis
    det=a[0][0]*(a[1][1]*a[2][2]-a[1][2]*a[2][1])-a[0][1]*(a[1][0]*a[2][2]-a[1][2]*a[2][0])+a[0][2]*(a[1][0]*a[2][1]-a[1][1]*a[2][0])
    require(abs(det-1)<EPS,'reflection changes winding; proper rotation required')
    if grid_merge:
        require(len(grid_origin)==3 and all(finite(x) for x in grid_origin),'finite owner grid_origin required')
        require(all(abs(v-round(v))<EPS for row in basis for v in row),'grid merge only supports signed-axis permutations; instance rotated meshes instead')
        local=[sum(basis[j][i]*(translation[j]-grid_origin[j]) for j in range(3)) for i in range(3)]
        require(all(aligned(n,pitch) for n in local),'nonaligned placement requires an independent mesh instance, not common-grid merge')
    return True


def validate_geometry(spec, compiled, render, contract):
    require(compiled['valid'],'common semantic constraints failed')
    p=compiled['pitch']; origin=compiled['grid_origin']; cells={tuple(row[:3]) for row in compiled['cells']}; allowed=contract['visual_max_bounds']
    lo,hi=render['bounds']['min'],render['bounds']['max']
    require(all(lo[i]>=allowed['min'][i]-EPS and hi[i]<=allowed['max'][i]+EPS for i in range(3)),'render bounds exceed placement envelope')
    require(any(row[4]=='joint' for row in compiled['cells']),'trim must retain visible joint/support cells')
    require(contract['collision']['generate_from_render_mesh'] is False,'fine mesh collision forbidden')
    for row in compiled['cells']:
        rect=[origin[0]+row[0]*p,origin[1]+row[1]*p,origin[0]+(row[0]+1)*p,origin[1]+(row[1]+1)*p]
        require(not any(rect_overlap(rect,h['rect']) for h in spec['holes']),'occupied cell overlaps a hole')
    counts={'+X':0,'-X':0,'+Y':0,'-Y':0,'+Z':0,'-Z':0}
    def occupied(point):
        return tuple(math.floor((point[i]-origin[i])/p+1e-7) for i in range(3)) in cells
    for group in render['groups']:
        for q in group['quads']:
            a=[q[1][i]-q[0][i] for i in range(3)]; b=[q[2][i]-q[0][i] for i in range(3)]
            n=[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]
            axes=[i for i in range(3) if abs(n[i])>EPS]
            require(len(axes)==1,'degenerate or non-axis-aligned common quad')
            axis=axes[0]; sign=1 if n[axis]>0 else -1
            center=[sum(v[i] for v in q)/4 for i in range(3)]; inside=center.copy(); outside=center.copy(); inside[axis]-=sign*p*.1; outside[axis]+=sign*p*.1
            require(occupied(inside) and not occupied(outside),'quad winding/normal is not outward from occupancy')
            counts[('+' if sign>0 else '-')+'XYZ'[axis]]+=1
            require(all(allowed['min'][i]-EPS <= v[i] <= allowed['max'][i]+EPS for v in q for i in range(3)),'quad vertex leaves allowed bounds')
    require(counts['+Z']>0 and counts['-Z']>0,'both front and backing surfaces required')
    if contract['kind']=='paving':
        require(abs(hi[2])<EPS,'paving must have exact top Z=0')
    joint_top=max(origin[2]+(row[2]+1)*p for row in compiled['cells'] if row[4]=='joint')
    require(abs(joint_top+.025)<EPS,'joint top must remain exactly -0.025')
    return {'bounds':render['bounds'],'hole_overlap_cells':0,'joint_top_z_m':r(joint_top),'normal_quad_counts':counts,'all_quad_normals_outward':True,'collision_footprint_rectangles':len(contract['collision']['reference_prisms'])}


def payload(value):
    return (json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False)+'\n').encode()


def write_exact(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        require(path.read_bytes()==data,f'existing changed artifact preserved: {path}; choose a new output directory')
    else:
        path.write_bytes(data)


def build(spec, output, *, render_only=False):
    validate_rules(spec); started=time.perf_counter(); output=Path(output)
    require(output.resolve().is_relative_to(HERE.resolve()),'outputs must stay inside owned surface_modules directory')
    source_paths=[ROOT/'voxel_character/common/core.py',ROOT/'voxel_character/common/render_data.py',ROOT/'voxel_character/tools/mesh.py',HERE.parents[1]/'source/detail_rules.r04.json',HERE.parents[1]/'lane/inputs/lane_rules.json']
    source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
    records=[]; total=0
    for kind in spec['kinds']:
        for seed in spec['seeds']:
            master,contract=author(spec,kind,seed)
            c=compile_master(master,{'pitch':spec['pitch_m']},max_candidate_cells=spec['budgets']['max_candidate_cells_per_module'],max_output_cells=spec['budgets']['max_output_cells_per_module'])
            mesh=make_render_data(c); checks=validate_geometry(spec,c,mesh,contract)
            ident=master['id']
            data={f'{ident}.master.json':payload(master),f'{ident}.render.json':payload(mesh),f'{ident}.placement.json':payload(contract),f'{ident}.compiled.json.gz':gzip.compress(payload(c),compresslevel=6,mtime=0)}
            if render_only:
                data={f'{ident}.render.json':data[f'{ident}.render.json']}
            total+=sum(len(b) for b in data.values());require(total<=spec['budgets']['max_artifact_bytes'],'generated artifact budget exceeded')
            files={}
            for filename,content in data.items():
                write_exact(output/filename,content);files[filename]={'bytes':len(content),'sha256':hashlib.sha256(content).hexdigest()}
            record={'id':ident,'kind':kind,'seed':seed,'cells':len(c['cells']),'candidate_cells':c['candidate_cells'],'quads':mesh['quad_count'],'master_hash':c['master_hash'],'payload_hash':c['payload_hash'],'render_hash':digest(mesh),'files':files,'checks':checks}
            if render_only:
                record['placement_contract']=contract
            records.append(record)
            print(json.dumps({'id':ident,'cells':record['cells'],'quads':record['quads']}),flush=True)
            del c,mesh,data,master,contract
    current={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in source_paths}
    require(current==source_hashes,'source dependencies changed during build')
    rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    require(rss<spec['budgets']['max_rss_mib']*1024,'offline peak RSS exceeds 600 MiB')
    manifest={'schema':'riverstone.shared_surface.manifest.v1','rules_hash':digest(spec),'pipeline':['author_surfaces.author','common.core.compile_master','common.render_data.make_render_data'],
              'source_hashes':source_hashes,'module_count':len(records),'artifact_bytes':total,'modules':records,'whole_city_application':False}
    if render_only:
        manifest['artifact_mode']='render_only_with_embedded_placement_contracts'
    write_exact(output/'manifest.json',payload(manifest))
    report={'status':'PASS','module_count':len(records),'artifact_bytes':total+(output/'manifest.json').stat().st_size,'offline_peak_rss_kib':rss,'elapsed_seconds':round(time.perf_counter()-started,3),'source_dependencies_unchanged':True,
            'scope':'Offline shared module generation and geometry QA only. No GUI, runtime integration, city mapping, FPS or GPU memory result.'}
    # Run timing is intentionally not a reproducible geometry artifact.
    (output/'latest_build_report.json').write_bytes(payload(report));print(json.dumps(report),flush=True)
    return manifest,report


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--rules',type=Path,default=HERE/'inputs/surface_rules.v1.json');ap.add_argument('--output',type=Path,default=HERE/'generated');ap.add_argument('--render-only',action='store_true');args=ap.parse_args()
    build(json.loads(args.rules.read_text()),args.output,render_only=args.render_only)

if __name__=='__main__':
    main()
