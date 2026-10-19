"""Bounded T-junction/hidden-contact classification, without regenerating cells."""
from collections import Counter,defaultdict
import gc,json,resource,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import compose as c
a=c.a;HERE=c.HERE;KEY='registered_port_long_loading_shed';P=.05

def odd_segments(groups):
    result=[]
    for d in range(3):
        lines=defaultdict(list);fixed=[j for j in range(3) if j!=d]
        for g in groups:
            for q in g['quads']:
                vs=[[round(x/P) for x in v] for v in q]
                for p,r in zip(vs,vs[1:]+vs[:1]):
                    if p[d]==r[d] or any(p[j]!=r[j] for j in fixed):continue
                    lo,hi=sorted((p[d],r[d]));lines[p[fixed[0]],p[fixed[1]]].extend(((lo,1),(hi,-1)))
        for key,events in lines.items():
            changes=Counter()
            for at,delta in events:changes[at]+=delta
            previous=None;active=0
            for at,delta in sorted(changes.items()):
                if previous is not None and active%2:
                    for k in range(previous,at):
                        center=[0,0,0];center[d]=k+.5
                        for j,x in zip(fixed,key):center[j]=x
                        result.append((d,center))
                active+=delta;previous=at
    return result

def face_index(groups):
    result=defaultdict(list)
    for g in groups:
        for q in g['quads']:
            axis,t,plane,sign,rect=a.quad_info(q)
            result[axis,round(plane/P)].append((g['material'],[x/P for x in rect]))
    return result

def face_cover(index,d,point):
    matches=[]
    for axis in range(3):
        if axis==d:continue
        t=[j for j in range(3) if j!=axis];other=next(j for j in t if j!=d)
        for material,r in index.get((axis,round(point[axis])),[]):
            if all(r[i]+1e-6<point[t[i]]<r[i+2]-1e-6 for i in range(2)):
                matches.append((material,axis))
    return matches

def main():
    start=time.monotonic();manifest=a.load(HERE/f'{KEY}.r02.manifest.json');source=a.load(a.ROOT/manifest['collision_reference_path']);baseodd=odd_segments(source['groups']);render=a.load(a.ROOT/manifest['render_path']);bad=odd_segments(render['groups']);index=face_index(render['groups']);covered=Counter();uncovered=[];samples=[]
    for d,p in bad:
        hits=face_cover(index,d,p)
        if hits:
            covered[','.join(sorted({m for m,axis in hits}))]+=1
            if len(samples)<12:samples.append({'direction':d,'point_m':[round(x*P,5) for x in p],'covering_face_materials':hits})
        else:uncovered.append((d,p))
    del render,index;gc.collect()
    roof_input=next(x for x in manifest['source_inputs'] if x['role']=='complete fine roof render');roof=a.load(a.ROOT/roof_input['path'])
    # Ray events sampled at each residual edge midpoint plus tiny off-edge offsets.
    # Exact original fine roof quads are retained; no mesh or primitive cropping.
    faces=[]
    for g in roof['groups']:
        for q in g['quads']:
            axis,t,plane,sign,r=a.quad_info(q)
            if axis==2:faces.append((plane,sign,r))
    def inside(point):
        x,y,z=point;events=[]
        for plane,sign,r in faces:
            if r[0]<=x<r[2] and r[1]<=y<r[3]:events.append((plane,sign))
        events.sort();count=sum(plane<=z for plane,sign in events)
        return bool(count%2)
    roof_hidden=[];unknown=[]
    for d,p in uncovered:
        pt=[x*P for x in p];fixed=[j for j in range(3) if j!=d]
        # Strict interior at all four transverse quadrants proves the entire
        # edge neighborhood is hidden inside the existing roof solid.
        answers=[]
        for du,dv in [(-1,-1),(-1,1),(1,-1),(1,1)]:
            q=pt[:];q[fixed[0]]+=du*1e-5;q[fixed[1]]+=dv*1e-5;answers.append(inside(q))
        (roof_hidden if all(answers) else unknown).append({'direction':d,'point_m':[round(x,5) for x in pt],'roof_solid_quadrants':answers})
    report={'schema':'riverstone.facility.composition.edge_visibility.v1','asset_key':KEY,'input_render_sha256':manifest['render_sha256'],'source_render_sha256':manifest['source_render_sha256'],'source_coarse_unpaired_unit_edges':len(baseodd),'composed_unpaired_unit_edges':len(bad),'strict_existing_face_interior_covered':sum(covered.values()),'covering_material_counts':dict(covered),'strict_fine_roof_solid_interior_covered':len(roof_hidden),'unresolved_unit_edges':len(unknown),'unresolved_samples':unknown[:32],'covered_face_samples':samples,'covered_roof_samples':roof_hidden[:12],'all_unpaired_edges_proven_hidden':not unknown,'method':'Every odd edge is subdivided to 0.05m. A strict interior point of an existing face covers T-junction edges; remaining edges require all four transverse neighborhoods inside the unchanged closed fine-roof mesh by exact ray parity.','max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_seconds':time.monotonic()-start}
    a.write(HERE/f'{KEY}.r02.edge_visibility.json',report);print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':main()
