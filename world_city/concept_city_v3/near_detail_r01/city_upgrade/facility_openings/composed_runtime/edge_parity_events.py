"""Single-pass exact unit-edge parity using packed endpoint XOR events.

No geometry is changed. Odd ranges remain diagnostics until visibility checks.
"""
from collections import defaultdict
import argparse,random,resource,time
from pathlib import Path
import stream_render as sr
import stream_compose as sc
a=sc.a

def collect(factory,max_endpoint_events=1500000):
    events=set();peak=0;quads=0
    for material,q in factory():
        *_,v=sr.grid_rectangle(q);quads+=1
        for p,r in zip(v,v[1:]+v[:1]):
            direction=next(j for j in range(3) if p[j]!=r[j])
            for point in (p,r):
                assert all(-32768<=x<32768 for x in point)
                key=(direction<<48)|((point[0]+32768)<<32)|((point[1]+32768)<<16)|(point[2]+32768)
                if key in events:events.remove(key)
                else:events.add(key)
        peak=max(peak,len(events));assert len(events)<=max_endpoint_events,'packed parity endpoint budget exceeded'
    lines=defaultdict(list)
    for key in events:
        direction=key>>48;p=[((key>>shift)&65535)-32768 for shift in (32,16,0)];fixed=[j for j in range(3) if j!=direction];lines[direction,p[fixed[0]],p[fixed[1]]].append(p[direction])
    segments=[]
    for key,ts in sorted(lines.items()):
        ts.sort();assert len(ts)%2==0
        segments.extend([*key,lo,hi] for lo,hi in zip(ts[::2],ts[1::2]))
    return {'quad_count':quads,'unpaired_unit_edges':sum(s[4]-s[3] for s in segments),'odd_segments':segments,'odd_segment_count':len(segments),'peak_endpoint_events':peak,'remaining_endpoint_events':len(events),'coordinate_contract':'Grid integers at pitch .05, origin0. Each [direction,fixed_axis0,fixed_axis1,lo,hi] uses ascending fixed axes and half-open longitudinal unit edges.'}

def selftest():
    rng=random.Random(73)
    for case in range(25):
        quads=[]
        for i in range(18):
            axis=rng.randrange(3);t=[j for j in range(3) if j!=axis];lo=[rng.randrange(-4,5),rng.randrange(-4,5)];r=[*lo,lo[0]+rng.randrange(1,5),lo[1]+rng.randrange(1,5)];q=a.rect_quad(r,axis,t,rng.randrange(-4,5),rng.choice([-1,1]));quads.append(('test',[[x*.05 for x in v] for v in q]))
        expected=sr.edge_audit(lambda:iter(quads));actual=collect(lambda:iter(quads));assert actual['unpaired_unit_edges']==expected['unpaired_unit_edges']
    return {'randomized_3_axis_Tjunction_and_overlap_cases':25,'all_match_interval_audit':True}

def main():
    p=argparse.ArgumentParser();p.add_argument('catalog',type=Path);p.add_argument('interfaces',type=Path);p.add_argument('output',type=Path);q=p.parse_args();start=time.monotonic();tests=selftest();comp=sc.Composition(q.catalog,q.interfaces);result=collect(comp.factory);result.update(schema='riverstone.mesh.odd_edge_domains.v1',selftests=tests,source_inputs=comp.inputs,code_sha256=a.sha(__file__),elapsed_seconds=round(time.monotonic()-start,3),max_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,interpretation='Odd edge parity is a diagnostic. Face-interior T-junction and independent solid coverage classification is required before calling an exterior gap.');a.write(q.output,result);assert result['max_rss_kib']<256*1024;print({k:result[k] for k in ['quad_count','unpaired_unit_edges','odd_segment_count','peak_endpoint_events','max_rss_kib','elapsed_seconds']})

if __name__=='__main__':main()
