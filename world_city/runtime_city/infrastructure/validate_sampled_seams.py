"""Read-only seam audit using existing common compiled occupancy, not metadata claims.

Writes only its evidence report. It never changes master or placement source.
"""
from __future__ import annotations
import json
import math
import hashlib
import sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from world_city.runtime_city.infrastructure.author import make_master,_point_inside,_lerp,_sub,_cross,_segment_convex_interval
from voxel_character.common import coordinate_planes

HERE=Path(__file__).resolve().parent
DATA=HERE/'generated/infrastructure.json'


def _merge(intervals,tolerance=1e-7):
    result=[]
    for a,b in sorted(intervals):
        if b<a:continue
        if result and a<=result[-1][1]+tolerance:result[-1][1]=max(result[-1][1],b)
        else:result.append([a,b])
    return result


def _missing(targets,covers):
    out=[]
    for a,b in targets:
        at=a
        for c,d in covers:
            if d<=at:continue
            if c>=b:break
            if c>at:out.append([at,min(c,b)])
            at=max(at,d)
            if at>=b:break
        if at<b:out.append([at,b])
    return [[a,b] for a,b in out if b-a>1e-7]


def _inside_intervals(a,b,poly):
    v=_sub(b,a);ts=[0,1]
    for c,d in zip(poly,poly[1:]+poly[:1]):
        u=_sub(d,c);den=_cross(v,u)
        if abs(den)<1e-10:continue
        w=_sub(c,a);t=_cross(w,u)/den;s=_cross(w,v)/den
        if 0<=t<=1 and 0<=s<=1:ts.append(t)
    ts=sorted(set(round(t,12) for t in ts))
    return [[lo,hi] for lo,hi in zip(ts,ts[1:]) if _point_inside(_lerp(a,b,(lo+hi)/2),poly)]


def validate(data=None):
    if data is None:data=json.loads(DATA.read_text())
    placements=data['placements'];cache={}
    def compile_one(p):
        key=(p['master_key'],p['requested_pitch_m'])
        if key not in cache:
            cache[key]=coordinate_planes.compile_master(make_master(p['spec']),{'pitch':p['requested_pitch_m']})
        return cache[key]
    def columns(p):return {(c[0],c[2]) for c in compile_one(p)['cells']} if p else set()
    by_position=defaultdict(dict)
    for p in placements:
        if p['category'] in ('terrain','water'):by_position[tuple(p['position_m'])][p['category']]=p
    shore=[];empty=[]
    for pos,group in sorted(by_position.items()):
        if 'water' not in group:continue
        water=group['water'];terrain=group.get('terrain')
        spec={'kind':'terrain_tile','width_m':water['spec']['width_m'],'length_m':water['spec']['length_m']}
        full=coordinate_planes.compile_master(make_master(spec),{'pitch':2})
        expected={(c[0],c[2]) for c in full['cells']}
        land_cols=columns(terrain);water_cols=columns(water)
        for p in (terrain,water):
            if p and not compile_one(p)['cells']:empty.append(p['id'])
        missing=expected-(land_cols|water_cols);extra=(land_cols|water_cols)-expected;overlap=land_cols&water_cols
        # XZ are horizontal columns. Y layers intentionally differ by two metres.
        shore.append({'position_m':list(pos),'terrain_id':terrain['id'] if terrain else None,'water_id':water['id'],
                      'expected_columns':len(expected),'terrain_columns':len(land_cols),'water_columns':len(water_cols),
                      'missing_columns':[list(c) for c in sorted(missing)],'extra_columns':[list(c) for c in sorted(extra)],
                      'overlap_columns':[list(c) for c in sorted(overlap)],'passed':not(missing or extra or overlap)})
    bridge_placements=[p for p in placements if p['category']=='bridge']
    polygons={};piece_reports=[]
    for p in bridge_placements:
        c=compile_one(p);pitch=c['pitch'];origin=c['grid_origin'];cells=c['cells']
        lo=[origin[i]+min(row[i] for row in cells)*pitch for i in range(3)]
        hi=[origin[i]+(max(row[i] for row in cells)+1)*pitch for i in range(3)]
        basis=p['transform']['basis'];pos=p['position_m']
        def world(x,z):return [basis[0][0]*x+basis[0][2]*z+pos[0],basis[2][0]*x+basis[2][2]*z+pos[2]]
        polygons[p['id']]=[world(lo[0],lo[2]),world(hi[0],lo[2]),world(hi[0],hi[2]),world(lo[0],hi[2])]
        a,b=p['source_segment_xz_m'];source_length=math.dist(a,b)
        sample_interval=_segment_convex_interval(a,b,polygons[p['id']])
        center=[(a[0]+b[0])/2,(a[1]+b[1])/2]
        alignment_error=math.dist(center,[pos[0],pos[2]])
        piece_reports.append({'id':p['id'],'source_road_id':p['source_road_id'],'source_length_m':source_length,
                              'sampled_length_m':hi[2]-lo[2],'length_deficit_m':source_length-(hi[2]-lo[2]),
                              'sampled_local_bounds':{'min':lo,'max':hi},'sampled_polygon_xz_m':polygons[p['id']],
                              'source_center_alignment_error_m':alignment_error,'sampled_source_interval':sample_interval})
    # Directly compare sampled end planes, not only union coverage: contiguous
    # modules of each source segment must neither overlap nor leave a gap.
    deck_groups=defaultdict(list)
    for p in placements:
        if p['category'] in ('bridge','dock','dock_connector'):
            deck_groups[p['id'].rsplit(':',1)[0]].append(p)
    internal_seams=[]
    for group_id,pieces in sorted(deck_groups.items()):
        pieces=sorted(pieces,key=lambda p:p['id'])
        for previous,current in zip(pieces,pieces[1:]):
            endpoints=[]
            for p,is_end in ((previous,True),(current,False)):
                c=compile_one(p);pitch=c['pitch'];origin=c['grid_origin']
                z=origin[2]+((max(row[2] for row in c['cells'])+1) if is_end else min(row[2] for row in c['cells']))*pitch
                basis=p['transform']['basis'];position=p['position_m']
                endpoints.append([position[0]+basis[0][2]*z,position[2]+basis[2][2]*z])
            gap=math.dist(*endpoints)
            internal_seams.append({'source_segment_id':group_id,'previous_id':previous['id'],'next_id':current['id'],
                                   'previous_sampled_end_xz_m':endpoints[0],'next_sampled_start_xz_m':endpoints[1],
                                   'shared_end_plane_error_m':gap,'passed':gap<1e-7})
    route_reports=[]
    for route in data['bridges']:
        a,b=route['centerline_xz_m'];length=math.dist(a,b)
        cover=_merge([interval for poly in polygons.values() if (interval:=_segment_convex_interval(a,b,poly)) is not None])
        gaps=_missing([[0,1]],cover)
        water=_inside_intervals(a,b,data['river']['outline_xz_m'])
        water_gaps=_missing(water,cover)
        route_reports.append({'road_id':route['id'],'source_length_m':length,'sampled_deck_coverage_intervals':cover,
                              'source_river_intervals':water,'uncovered_source_intervals':gaps,
                              'uncovered_source_lengths_m':[(hi-lo)*length for lo,hi in gaps],
                              'uncovered_water_intervals':water_gaps,
                              'uncovered_water_lengths_m':[(hi-lo)*length for lo,hi in water_gaps],
                              'passed':not gaps and not water_gaps})
    shoreline_pass=all(r['passed'] for r in shore)
    bridge_pass=all(r['passed'] for r in route_reports) and all(s['passed'] for s in internal_seams)
    return {'schema':'riverstone.city.sampled_seams.v1','passed':shoreline_pass and bridge_pass,
            'source_data':str(DATA.relative_to(ROOT)),
            'provenance':{'source_data_sha256':hashlib.sha256(DATA.read_bytes()).hexdigest(),
                          'author_sha256':hashlib.sha256((HERE/'author.py').read_bytes()).hexdigest(),
                          'common_core_sha256':hashlib.sha256((ROOT/'voxel_character/common/core.py').read_bytes()).hexdigest(),
                          'coordinate_planes_sha256':hashlib.sha256((ROOT/'voxel_character/common/coordinate_planes.py').read_bytes()).hexdigest()},
            'method':'Existing common coordinate-plane compiler occupancy. XZ column partition for each river-intersected tile; actual sampled bridge local bounds transformed to world polygons and intersected with exact source centerlines.',
            'shoreline':{'passed':shoreline_pass,'tiles_checked':len(shore),'expected_columns':sum(r['expected_columns'] for r in shore),
                         'terrain_columns':sum(r['terrain_columns'] for r in shore),'water_columns':sum(r['water_columns'] for r in shore),
                         'missing_column_count':sum(len(r['missing_columns']) for r in shore),
                         'overlap_column_count':sum(len(r['overlap_columns']) for r in shore),
                         'empty_sampled_placements':empty,'tiles':shore},
            'bridge':{'passed':bridge_pass,'piece_count':len(piece_reports),'source_road_count':len(route_reports),
                      'pieces':piece_reports,'routes':route_reports,'internal_deck_seams':internal_seams,
                      'internal_deck_seam_count':len(internal_seams),
                      'max_internal_shared_plane_error_m':max((s['shared_end_plane_error_m'] for s in internal_seams),default=0),
                      'scope':'Geometric sampled deck continuity and source-river centerline coverage; no runtime physics, swept cart clearance, or navigation simulation.'}}


def main():
    output=Path(sys.argv[1]) if len(sys.argv)>1 else HERE/'generated/sampled_seams.json'
    result=validate();output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':result['passed'],'shoreline':{k:v for k,v in result['shoreline'].items() if k!='tiles'},
                      'bridge':{k:v for k,v in result['bridge'].items() if k not in ('pieces','routes','internal_deck_seams')},
                      'bridge_gaps':[{k:v for k,v in r.items() if k in ('road_id','uncovered_source_lengths_m','uncovered_water_lengths_m')} for r in result['bridge']['routes']]},indent=2))
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
