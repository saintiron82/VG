"""Exact diagnostic: odd edge intervals strictly covered by another face interior."""
from collections import defaultdict
import argparse,resource,time
import stream_compose as sc
import stream_render as sr
a=sc.a

def main():
    p=argparse.ArgumentParser();p.add_argument('edges');p.add_argument('catalog');p.add_argument('interfaces');p.add_argument('output');args=p.parse_args();start=time.monotonic();data=a.load(args.edges);segments=data['odd_segments'];marks=[bytearray(s[4]-s[3]) for s in segments];index=defaultdict(list)
    for i,(d,f0,f1,lo,hi) in enumerate(segments):
        fixed=[j for j in range(3) if j!=d]
        for axis,plane,other in [(fixed[0],f0,f1),(fixed[1],f1,f0)]:index[axis,plane].append((i,d,other,lo,hi))
    comp=sc.Composition(args.catalog,args.interfaces);count=0
    for material,q in comp.factory():
        axis,plane,sign,x0,y0,x1,y1,v=sr.grid_rectangle(q);count+=1;candidates=index.get((axis,plane))
        if not candidates:continue
        lo=[min(p[j] for p in v) for j in range(3)];hi=[max(p[j] for p in v) for j in range(3)]
        for i,d,other,slo,shi in candidates:
            otheraxis=3-axis-d
            if not lo[otheraxis]<other<hi[otheraxis]:continue
            begin=max(slo,lo[d]);end=min(shi,hi[d])
            if begin<end:marks[i][begin-slo:end-slo]=b'\1'*(end-begin)
    remaining=[];covered=0
    for seg,mask in zip(segments,marks):
        covered+=sum(mask);begin=None
        for j,m in enumerate(mask+b'\1'):
            if not m and begin is None:begin=j
            if m and begin is not None:remaining.append([*seg[:3],seg[3]+begin,seg[3]+j]);begin=None
    result={'schema':'riverstone.mesh.edge_face_interior_coverage.v1','input_edge_sha256':a.sha(args.edges),'source_inputs':comp.inputs,'quad_count':count,'input_unpaired_unit_edges':data['unpaired_unit_edges'],'face_interior_covered_unit_edges':covered,'remaining_unit_edges':sum(s[4]-s[3] for s in remaining),'remaining_segments':remaining,'code_sha256':a.sha(__file__),'interpretation':'Exact strict-interior planar coverage explains T-junction parity edges; remaining edges require independent solid coverage or exterior-gap inspection. Not a full manifold certificate.','elapsed_seconds':round(time.monotonic()-start,3),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss};assert covered+result['remaining_unit_edges']==data['unpaired_unit_edges'];a.write(args.output,result);assert result['max_rss_kib']<256*1024;print({k:result[k] for k in ['quad_count','face_interior_covered_unit_edges','remaining_unit_edges','elapsed_seconds','max_rss_kib']})

if __name__=='__main__':main()
