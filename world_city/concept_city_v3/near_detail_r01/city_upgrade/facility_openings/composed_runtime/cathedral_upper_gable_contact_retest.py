"""Retest only the frozen 1,906 upper-gable and 808 aisle contact witnesses.

No compilation, new render, whole-roof loading, or global edge audit. Preparation
reconstructs exact witness pixels from the frozen r04 proof and baseline signed
sections. Final testing streams the priority composition and seeks the correctly
oriented local panel faces around those same points. All coordinates are integer
half-grid units (0.025m). Run --prepare, then --interfaces FINAL_CATALOG.
"""
from bisect import bisect_left, bisect_right
from collections import defaultdict
from pathlib import Path
import argparse
import gc
import hashlib
import json
import resource
import time
import cathedral_interface_audit as old
import stream_compose_priority as priority
import stream_render as sr

HERE=Path(__file__).resolve().parent
OUT=Path(__file__).with_suffix('.json')
FROZEN=HERE/'cathedral_interface_audit.json'
FROZEN_SHA='b16b46a7f9a92e678e70c1bd9b442a90d9d41fa358028eb1791aca30577a93a4'
FROZEN_HELPER_SHA='c8d9a3abcaf9cba91be6f164c9d6e3f4ec490574f4c4767fb042227c8808c2c7'


def digest(value):return hashlib.sha256(sr._canonical(value)).hexdigest()


def save(report):
    text=json.dumps(report,separators=(',',':'))+'\n'
    assert len(text.encode())+Path(__file__).stat().st_size<100000
    OUT.write_text(text)


def frozen():
    assert sr._file_sha(FROZEN)==FROZEN_SHA
    assert sr._file_sha(old.__file__)==FROZEN_HELPER_SHA
    return json.loads(FROZEN.read_text())


def prepare():
    started=time.monotonic();r=frozen();features=[];records=[];upper_count=0
    for g in r['gable_outward_exposure_audit']['gables']:
        fi=len(features);axis=g['outward_axis'];u=2 if axis==0 else 0
        shape=old.shape_record('masonry',g['original_operation'])
        features.append({'id':g['source_operation'],'source_operation':g['source_operation'],
                         'class':'upper_gable','axis':axis,'outward_sign':g['outward_sign'],
                         'local_band_m':g['local_test_band_m'],'witness_count':g['distinct_projected_loss_cells']})
        for region in g['continuous_pixel_regions']:
            box=region['world_aabb_m'];fixed=region['example_m'][axis];n=0
            for ui in range(round(box['min'][u]*20),round(box['max'][u]*20)):
                for yi in range(round(box['min'][1]*20),round(box['max'][1]*20)):
                    p=[0.,(yi+.5)*.05,0.];p[axis]=fixed;p[u]=(ui+.5)*.05
                    _,body=old.analytic_intervals([shape],p[0],p[2])
                    if any(lo<=p[1]<=hi for lo,hi in body):
                        records.append([fi]+[round(x*40) for x in p]);n+=1
            # The frozen loss is a subset of source-filled pixels in this box.
            # Equal cardinality therefore reconstructs that exact subset.
            assert n==region['cells'],(g['source_operation'],n,region['cells'])
            upper_count+=n
    assert upper_count==1906
    measurement=json.loads(old.MEASUREMENT.read_text())
    source=old.ROOT/measurement['source_master_path'];assert sr._file_sha(source)==measurement['source_master_sha256']
    raw=json.loads(source.read_text())
    shapes=[old.shape_record(c['id'],o) for c in raw['components'] for o in c['operations']]
    all_sections=old.make_sections(measurement,shapes)
    wanted=[row['id'] for row in r['runs']['baseline']['sections']
            if row['id'].startswith('aisle_') and row.get('new_missing_masonry_cells')]
    assert len(wanted)==4
    sections=[s for s in all_sections if s['id'] in wanted]
    coarse,_=old.stream_sections(lambda:sr.iter_quads(old.ROOT/measurement['source_render_path']),sections,collect_axial=False)
    comp=old.audit_composition(priority.base,old.CATALOG,None)
    baseline_inputs_sha=digest(comp.inputs);windows=comp.windows
    masks,diag=old.stream_sections(comp.factory,sections,collect_axial=False)
    assert diag['quad_count']==r['runs']['baseline']['virtual_quad_count']
    del comp;gc.collect()
    refs=old.references(sections,shapes,windows);aisle_count=0
    baseline_rows={row['id']:row for row in r['runs']['baseline']['sections']}
    for si,s in enumerate(sections):
        fi=len(features);axis=s['fixed_axis'];u=s['horizontal_axis'];n=0;h=s['y1']-s['y0']
        for col in range(s['u1']-s['u0']):
            for row in range(h):
                at=col*h+row
                if refs[1][si][at] and coarse[si][at] and not masks[si][at] and not refs[2][si][at]:
                    p=[0.,(s['y0']+row+.5)*.05,0.];p[axis]=s['fixed_m'];p[u]=(s['u0']+col+.5)*.05
                    records.append([fi]+[round(x*40) for x in p]);n+=1
        assert n==baseline_rows[s['id']]['new_missing_masonry_cells']==202
        features.append({'id':s['id'],'source_operation':s['source_feature'],'class':'aisle_gable',
                         'axis':axis,'outward_sign':-1 if 'rear' in s['id'] else 1,
                         'local_band_m':s['local_axial_interval_m'],'witness_count':n})
        aisle_count+=n
    assert aisle_count==808 and len(records)==2714
    records.sort();assert len({tuple(x) for x in records})==2714
    report={'schema':'riverstone.cathedral.frozen_contact_retest.v1',
            'frozen_r04_report_path':str(FROZEN.relative_to(old.ROOT)),'frozen_r04_report_sha256':FROZEN_SHA,
            'frozen_helper_sha256':FROZEN_HELPER_SHA,'preparation_helper_sha256':sr._file_sha(__file__),
            'features':features,'witness_half_grid_records':records,'witness_records_sha256':digest(records),
            'coordinate_contract':'Each [feature_index,x,y,z] uses .025m integer units and original test pixel centers.',
            'upper_gable_witnesses':upper_count,'aisle_witnesses':aisle_count,
            'baseline_composition_quad_count':diag['quad_count'],'baseline_source_inputs_sha256':baseline_inputs_sha,
            'preparation_seconds':round(time.monotonic()-started,3),
            'preparation_max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'method':'Upper witness sets reconstructed from source-filled pixels in every frozen connected-region AABB, with per-region equal-cardinality verification. The exact four original aisle baseline sections reproduce 202 losses each with original analytic masonry and original coarse FULL-union occupancy.'}
    save(report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('features','witness_half_grid_records','method')}),flush=True)


def face_witnesses(factory,features,records):
    lookups=[];by_axis=defaultdict(list)
    for fi,feature in enumerate(features):
        axis=feature['axis'];u=2 if axis==0 else 0
        rows=sorted((r[1+u],r[2],i) for i,r in enumerate(records) if r[0]==fi)
        lookups.append(([r[0] for r in rows],rows));by_axis[axis].append(fi)
    hits=bytearray(len(records));counts=[0]*len(records);quads=0
    for material,q in factory():
        quads+=1
        if all(v[1]==q[0][1] for v in q):continue
        axis,t,plane,sign,rect=priority.a.quad_info(q)
        if axis not in by_axis:continue
        u=2 if axis==0 else 0
        u0=round(min(v[u] for v in q)*40);u1=round(max(v[u] for v in q)*40)
        y0=round(min(v[1] for v in q)*40);y1=round(max(v[1] for v in q)*40);plane2=round(plane*40)
        for fi in by_axis[axis]:
            feature=features[fi];lo,hi=feature['local_band_m']
            if not lo-1e-8<=plane<=hi+1e-8:continue
            us,rows=lookups[fi];direction=feature['outward_sign']
            for pu,py,index in rows[bisect_right(us,u0):bisect_left(us,u1)]:
                if not y0<py<y1:continue
                point2=records[index][1+axis];counts[index]+=1
                if sign==direction and plane2*direction>point2*direction:hits[index]|=1
                if sign==-direction and plane2*direction<point2*direction:hits[index]|=2
    return hits,counts,quads


def selftest():
    front=priority.a.rect_quad([0,0,1,1],2,[0,1],1,1)
    back=priority.a.rect_quad([0,0,1,1],2,[0,1],0,-1)
    features=[{'axis':2,'outward_sign':1,'local_band_m':[-.1,1.1]}]
    records=[[0,20,20,20],[0,60,20,20]]
    hits,counts,n=face_witnesses(lambda:iter([('a',front),('b',back)]),features,records)
    assert list(hits)==[3,0] and counts==[2,0] and n==2
    return {'oriented_local_pair_and_outside_point':True,**priority.selftests()}


def retest(interface_path):
    started=time.monotonic();frozen();report=json.loads(OUT.read_text())
    records=report['witness_half_grid_records'];assert digest(records)==report['witness_records_sha256']
    tests=selftest();print(json.dumps({'stage':'constructing_priority_composition','witnesses':len(records)}),flush=True)
    comp=priority.Composition(old.CATALOG,interface_path)
    inputs_sha=digest(comp.inputs);priority_edits=comp.interface_priority_edits
    hits,counts,quads=face_witnesses(comp.factory,report['features'],records)
    results=[];missing=[]
    for fi,feature in enumerate(report['features']):
        indices=[i for i,r in enumerate(records) if r[0]==fi]
        results.append({'id':feature['id'],'witnesses':len(indices),
                        'correct_outward_face':sum(bool(hits[i]&1) for i in indices),
                        'correct_inward_face':sum(bool(hits[i]&2) for i in indices),
                        'both_oriented_local_faces':sum(hits[i]==3 for i in indices),
                        'no_local_face':sum(counts[i]==0 for i in indices)})
        for i in indices:
            if not hits[i]&1:missing.append({'feature_id':feature['id'],'point_m':[v*.025 for v in records[i][1:]],'face_bits':hits[i],'local_face_count':counts[i]})
    result={'interface_catalog_path':str(interface_path),'interface_catalog_sha256':sr._file_sha(interface_path),
            'priority_compositor_sha256':sr._file_sha(priority.__file__),'base_compositor_sha256':sr._file_sha(priority.base.__file__),
            'retest_helper_sha256':sr._file_sha(__file__),'source_inputs_sha256':inputs_sha,
            'virtual_quad_count':quads,'interface_count':len(comp.interface_outputs),
            'priority_edited_input_count':len(priority_edits),'priority_edits_sha256':digest(priority_edits),
            'witness_records_sha256':report['witness_records_sha256'],'selftests':tests,
            'features':results,'all_2714_outward_faces_restored':not missing,
            'missing_outward_face_count':len(missing),'missing_outward_samples':missing[:24],
            'both_oriented_local_faces':sum(x==3 for x in hits),'face_bits_hex':hits.hex(),
            'proof_scope':'Only the same 1906 upper and 808 aisle source-filled witness pixels. Correctly oriented local outward and inward faces are tested separately. This is not a new whole-building leak, edge, or manifold audit.',
            'elapsed_seconds':round(time.monotonic()-started,3),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'hard_address_space_mib':192}
    print(json.dumps({k:v for k,v in result.items() if k!='face_bits_hex'}),flush=True)
    report['final_retest']=result;save(report)


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--prepare',action='store_true');parser.add_argument('--interfaces',type=Path)
    args=parser.parse_args();resource.setrlimit(resource.RLIMIT_AS,(192*1024*1024,192*1024*1024))
    if args.prepare:prepare()
    else:
        assert args.interfaces,'--prepare or --interfaces is required'
        retest(args.interfaces)


if __name__=='__main__':main()
