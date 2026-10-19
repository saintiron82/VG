"""Bounded independent axial sections for cathedral body/roof contacts.

No meshing, voxel compilation, render output, or whole-roof JSON loading.
0.05m pixel centers are independently classified from original analytic box /
extruded-polygon CSG, original coarse render, and a streamed virtual composition.
Signed horizontal-face crossings reconstruct occupied vertical intervals. This
detects sampled missing masonry rather than using global edge parity as a seal
certificate. Finite sections cannot prove absence of all three-dimensional leaks.

Run from any cwd: --phase baseline, or --phase interfaces --interfaces CATALOG.
The JSON report keeps both phases. Only this helper and its report are written.
"""
from array import array
from bisect import bisect_left
from collections import deque
from pathlib import Path
import argparse
import hashlib
import gc
import gzip
import json
import math
import resource
import time
import stream_render as sr

HERE=Path(__file__).resolve().parent
F=HERE.parent
ROOT=next(p for p in HERE.parents if (p/'VG_PROJECT_INDEX.json').exists())
PITCH=.05
MEASUREMENT=F/'composed/cathedral_contact_gap_measurement.json'
CATALOG=F/'compiled_active_r02/registered_cathedral_nave_aisles_transept.catalog.json'
IDENTITY=[[1,0,0],[0,1,0],[0,0,1]]


def transform(op,p):
    t=op.get('transform',{});b=t.get('basis',IDENTITY);off=t.get('translation',[0,0,0])
    return [sum(b[i][j]*p[j] for j in range(3))+off[i] for i in range(3)]


def shape_record(component,op):
    s=op['shape'];axis=None;poly=None
    if s['kind']=='box':
        points=[transform(op,[x,y,z]) for x in (s['min'][0],s['max'][0])
                for y in (s['min'][1],s['max'][1]) for z in (s['min'][2],s['max'][2])]
        basis=op.get('transform',{}).get('basis',IDENTITY)
        assert all(sum(abs(x)>1e-9 for x in row)==1 for row in basis)
    else:
        assert s['kind']=='extrusion',s['kind']
        basis=op.get('transform',{}).get('basis',IDENTITY)
        assert basis[1]==[0,1,0]
        axis=next(a for a in (0,2) if abs(basis[a][2])==1)
        points=[transform(op,[x,y,z]) for x,y in s['polygon'] for z in (s['z_min'],s['z_max'])]
        cross=2 if axis==0 else 0
        poly=[(p[cross],p[1]) for p in [transform(op,[x,y,s['z_min']]) for x,y in s['polygon']]]
    return {'id':op['id'],'component':component,'action':op['action'],
            'min':[min(p[a] for p in points) for a in range(3)],
            'max':[max(p[a] for p in points) for a in range(3)],'axis':axis,'poly':poly}


def vertical_interval(poly,u):
    ys=[]
    for i,p in enumerate(poly):
        q=poly[(i+1)%len(poly)]
        if min(p[0],q[0])-1e-10<=u<=max(p[0],q[0])+1e-10:
            if abs(q[0]-p[0])<1e-10:ys.extend((p[1],q[1]))
            else:ys.append(p[1]+(u-p[0])*(q[1]-p[1])/(q[0]-p[0]))
    return (min(ys),max(ys)) if ys else None


def merge(intervals):
    result=[]
    for lo,hi in sorted(intervals,key=lambda iv:(iv[0],iv[1])):
        if result and lo<=result[-1][1]+1e-10:result[-1][1]=max(result[-1][1],hi)
        else:result.append([lo,hi])
    return result


def subtract(intervals,cut):
    result=[]
    for lo,hi in intervals:
        if hi<=cut[0] or lo>=cut[1]:result.append([lo,hi])
        else:
            if lo<cut[0]:result.append([lo,cut[0]])
            if hi>cut[1]:result.append([cut[1],hi])
    return result


def analytic_intervals(shapes,x,z):
    components={}
    for s in shapes:
        if not(s['min'][0]<=x<=s['max'][0] and s['min'][2]<=z<=s['max'][2]):continue
        interval=(s['min'][1],s['max'][1]) if s['axis'] is None else vertical_interval(s['poly'],z if s['axis']==0 else x)
        if not interval:continue
        old=components.get(s['component'],[])
        if s['action']=='paint':components[s['component']]=merge(old+[interval])
        elif s['action']=='cut':components[s['component']]=subtract(old,interval)
        else:raise ValueError('unsupported original CSG action')
    return merge([iv for intervals in components.values() for iv in intervals]),components.get('masonry',[])


def center(v):
    return (round(v/PITCH-.5)+.5)*PITCH


def make_sections(measurement,shapes):
    by_id={s['id']:s for s in shapes};result=[]
    def add(name,kind,fixed_axis,fixed,u0,u1,y0,y1,extra):
        uaxis=2 if fixed_axis==0 else 0
        result.append({'id':name,'kind':kind,'fixed_axis':fixed_axis,'fixed_m':round(center(fixed),8),
                       'horizontal_axis':uaxis,'u0':math.floor((u0+1e-8)/PITCH),'u1':math.ceil((u1-1e-8)/PITCH),
                       'y0':math.floor((y0+1e-8)/PITCH),'y1':math.ceil((y1-1e-8)/PITCH),**extra})
    for row in measurement['eave_strips']:
        sid=row['eave_strip_id'];axis=0 if row['cross_axis']=='x' else 2
        lo,hi=row['wall_cross_interval_m'];outer_low=sid.endswith(('west','rear'))
        values=[('outer_025',lo+.025 if outer_low else hi-.025),
                ('outer_125',lo+.125 if outer_low else hi-.125),
                ('inner_025',hi-.025 if outer_low else lo+.025)]
        for label,v in values:
            add(sid+'/'+label,'eave',axis,v,*row['full_wall_longitudinal_interval_m'],
                row['wall_top_y_m']-.65,max(row['roof_underside_y_at_cross_minmax_m'])+.45,
                {'source_feature':sid,'known_gap_intervals_m':row['continuous_gap_intervals_m'],
                 'feature_depth_interval_m':[lo,hi],'local_axial_interval_m':[lo-.1,hi+.1],
                 'wall_top_y_m':row['wall_top_y_m'],
                 'original_roof_underside_y_m':row['roof_underside_y_at_cross_minmax_m'][0]+row['roof_slope_dy_du']*(center(v)-lo)})
    for row in measurement['gable_panel_joints_separate_from_eaves']:
        shape=by_id[row['gable_operation']];axis=0 if row['depth_axis']=='x' else 2;uaxis=2 if axis==0 else 0
        lo,hi=row['gable_panel_depth_interval_m']
        extra={'source_feature':row['gable_operation'],'original_depth_separation_m':round(row['depth_separation_m'],8),
               'feature_depth_interval_m':[lo,hi],'local_axial_interval_m':[lo-.1,hi+.1],
               'depth_joint_classification':row['classification']}
        for label,v in (('panel_min',lo+.025),('panel_max',hi-.025)):
            add(row['gable_operation']+'/'+label,'gable_panel',axis,v,shape['min'][uaxis],shape['max'][uaxis],
                shape['min'][1]-.1,shape['max'][1]+.7,extra)
        if row['depth_separation_m']>1e-8:
            wall=row['lower_wall_depth_interval_m'];v=(wall[1]+lo)/2 if wall[1]<lo else (hi+wall[0])/2
            add(row['gable_operation']+'/known_depth_gap','known_gable_depth_gap',axis,v,
                shape['min'][uaxis],shape['max'][uaxis],row['gable_base_y_m'],row['lower_wall_top_y_m'],extra)
    assert len(result)==45
    return result


def stream_sections(factory,sections,ray_probes=(),collect_axial=True):
    """Exact mesh-ray winding at selected 0.05m cell-center rays, not voxel CSG."""
    events=[];starts=[];totals=[];lookup={0:[],2:[]};axial_masks=[]
    for i,s in enumerate(sections):
        width=s['u1']-s['u0'];height=s['y1']-s['y0']
        events.append(array('h',[0])*(width*height));starts.append(array('h',[0])*width);totals.append(array('h',[0])*width)
        axial_masks.append(bytearray(width*height))
        lookup[s['fixed_axis']].append((s['fixed_m'],i))
    for a in lookup:lookup[a].sort()
    fixeds={a:[p for p,i in lookup[a]] for a in lookup};quads=horizontal=0
    ray_hits=[[] for p in ray_probes]
    for material,q in factory():
        quads+=1
        for axis in ((0,2) if collect_axial else ()):
            plane=q[0][axis]
            if not all(v[axis]==plane for v in q):continue
            uaxis=2 if axis==0 else 0
            q_u0=round(min(v[uaxis] for v in q)/PITCH);q_u1=round(max(v[uaxis] for v in q)/PITCH)
            q_y0=round(min(v[1] for v in q)/PITCH);q_y1=round(max(v[1] for v in q)/PITCH)
            for _,si in lookup[axis]:
                s=sections[si];interval=s.get('local_axial_interval_m')
                if interval is None or not interval[0]-1e-8<=plane<=interval[1]+1e-8:continue
                u0=max(s['u0'],q_u0);u1=min(s['u1'],q_u1);y0=max(s['y0'],q_y0);y1=min(s['y1'],q_y1)
                if y1<=y0 or u1<=u0:continue
                height=s['y1']-s['y0'];fill=b'\1'*(y1-y0)
                for col in range(u0-s['u0'],u1-s['u0']):
                    start=col*height+y0-s['y0'];axial_masks[si][start:start+len(fill)]=fill
        for ri,probe in enumerate(ray_probes):
            axis=probe['axis'];plane=q[0][axis]
            if not probe['local_interval_m'][0]<=plane<=probe['local_interval_m'][1]:continue
            if not all(v[axis]==plane for v in q):continue
            tangent=[a for a in range(3) if a!=axis];point=probe['point_m']
            if all(min(v[a] for v in q)<=point[a]<max(v[a] for v in q) for a in tangent):
                if len(ray_hits[ri])>=128:raise sr.BudgetExceeded('axial probe hit cap exceeded')
                ray_hits[ri].append({'plane_m':plane,'material':material})
        if not all(v[1]==q[0][1] for v in q):continue
        horizontal+=1;y=round(q[0][1]/PITCH)
        e=[q[1][a]-q[0][a] for a in range(3)];f=[q[2][a]-q[1][a] for a in range(3)]
        normal=e[2]*f[0]-e[0]*f[2];assert normal
        delta=-1 if normal>0 else 1
        lo=[min(v[a] for v in q) for a in range(3)];hi=[max(v[a] for v in q) for a in range(3)]
        for a in (0,2):
            start=bisect_left(fixeds[a],lo[a]);end=bisect_left(fixeds[a],hi[a])
            for _,si in lookup[a][start:end]:
                s=sections[si];u=s['horizontal_axis'];h=s['y1']-s['y0']
                u0=max(s['u0'],round(lo[u]/PITCH));u1=min(s['u1'],round(hi[u]/PITCH))
                for col in range(u0-s['u0'],u1-s['u0']):
                    totals[si][col]+=delta
                    if y<=s['y0']:starts[si][col]+=delta
                    elif y<s['y1']:events[si][col*h+y-s['y0']]+=delta
    masks=[];diagnostics=[]
    for si,s in enumerate(sections):
        width=s['u1']-s['u0'];height=s['y1']-s['y0'];mask=bytearray(width*height);negative=0
        for col in range(width):
            winding=starts[si][col]
            for row in range(height):
                index=col*height+row;winding+=events[si][index]
                mask[index]=winding>0;negative+=winding<0
        masks.append(mask);diagnostics.append({'unbalanced_vertical_rays':sum(v!=0 for v in totals[si]),'negative_winding_cells':negative})
        events[si]=None;starts[si]=None;totals[si]=None
    return masks,{'quad_count':quads,'horizontal_quads':horizontal,'sections':diagnostics,'ray_hits':ray_hits,'_axial_masks':axial_masks}


def axial_loss_regions(sections,refs,coarse,coarse_diag,target,target_diag,roof):
    """Local through-band ray absence; independent of vertical winding state."""
    rows=[]
    for si,s in enumerate(sections):
        if s['kind']=='known_gable_depth_gap':continue
        wall=refs[1][si];exclude=refs[2][si]
        old=coarse_diag['_axial_masks'][si];new=target_diag['_axial_masks'][si]
        lost=bytearray(bool(w and occupied and a and not b and not x) for w,occupied,a,b,x in zip(wall,coarse[si],old,new,exclude))
        raw_count=sum(lost)
        buried=sum(bool(a and b) for a,b in zip(lost,roof[si]))
        for i,inside in enumerate(roof[si]):
            if inside:lost[i]=0
        count=sum(lost)
        if not raw_count:continue
        height=s['y1']-s['y0'];width=s['u1']-s['u0'];regions=[]
        for seed in range(len(lost)):
            if not lost[seed]:continue
            lost[seed]=0;queue=deque([seed]);umin=umax=seed//height;ymin=ymax=seed%height;n=0;empty=0;example=None
            while queue:
                at=queue.popleft();col,row=divmod(at,height);n+=1;empty+=not target[si][at]
                if example is None:
                    example=[0.,(s['y0']+row+.5)*PITCH,0.];example[s['fixed_axis']]=s['fixed_m'];example[s['horizontal_axis']]=(s['u0']+col+.5)*PITCH
                umin=min(umin,col);umax=max(umax,col);ymin=min(ymin,row);ymax=max(ymax,row)
                neighbors=[]
                if col:neighbors.append(at-height)
                if col+1<width:neighbors.append(at+height)
                if row:neighbors.append(at-1)
                if row+1<height:neighbors.append(at+1)
                for other in neighbors:
                    if lost[other]:lost[other]=0;queue.append(other)
            lo=[0.,(s['y0']+ymin)*PITCH,0.];hi=[0.,(s['y0']+ymax+1)*PITCH,0.]
            lo[s['fixed_axis']],hi[s['fixed_axis']]=s['feature_depth_interval_m']
            lo[s['horizontal_axis']]=(s['u0']+umin)*PITCH;hi[s['horizontal_axis']]=(s['u0']+umax+1)*PITCH
            regions.append({'cells':n,'target_vertical_empty_cells':empty,'example_m':[round(x,8) for x in example],'world_aabb_m':{'min':[round(x,8) for x in lo],'max':[round(x,8) for x in hi]}})
        rows.append({'section_id':s['id'],'source_feature':s['source_feature'],'new_local_axial_face_loss_cells':raw_count,'buried_in_independent_closed_roof_cells':buried,'remaining_outside_roof_cells':count,
                     'local_ray_interval_m':s['local_axial_interval_m'],'connected_regions':regions})
    return rows


def fill_intervals(mask,col,height,y0,intervals):
    for lo,hi in intervals:
        first=max(0,math.ceil(lo/PITCH-.5-y0-1e-8));last=min(height,math.floor(hi/PITCH-.5-y0+1e-8)+1)
        if last>first:mask[col*height+first:col*height+last]=b'\1'*(last-first)


def references(sections,shapes,windows):
    solids=[];masonry=[];excluded=[];known=[]
    for s in sections:
        width=s['u1']-s['u0'];height=s['y1']-s['y0'];solid=bytearray(width*height);wall=bytearray(width*height)
        exclude=bytearray(width*height);gap=bytearray(width*height)
        for col in range(width):
            u=(s['u0']+col+.5)*PITCH;x,z=(s['fixed_m'],u) if s['fixed_axis']==0 else (u,s['fixed_m'])
            whole,body=analytic_intervals(shapes,x,z)
            fill_intervals(solid,col,height,s['y0'],whole);fill_intervals(wall,col,height,s['y0'],body)
            for roi in windows:
                if roi['min'][0]<=x<=roi['max'][0] and roi['min'][2]<=z<=roi['max'][2]:
                    fill_intervals(exclude,col,height,s['y0'],[(roi['min'][1],roi['max'][1])])
            if s['kind']=='eave' and any(lo<=u<=hi for lo,hi in s['known_gap_intervals_m']):
                fill_intervals(gap,col,height,s['y0'],[(s['wall_top_y_m'],s['original_roof_underside_y_m'])])
            elif s['kind']=='known_gable_depth_gap':
                fill_intervals(gap,col,height,s['y0'],[(s['y0']*PITCH,s['y1']*PITCH)])
        solids.append(solid);masonry.append(wall);excluded.append(exclude);known.append(gap)
    return solids,masonry,excluded,known


def summarize(sections,target,coarse,refs,diagnostics):
    result=[]
    for si,s in enumerate(sections):
        analytic,wall,exclude,known=(r[si] for r in refs);t=target[si];old=coarse[si]
        fields=['new_missing_masonry_cells','inherited_cache_missing_masonry_cells','missing_analytic_roof_or_other_cells',
                'known_original_gap_empty_cells','solid_added_in_original_empty_cells','excluded_window_cells']
        counts={k:0 for k in fields};examples=[];max_run=0;longest=None;h=s['y1']-s['y0']
        for col in range(s['u1']-s['u0']):
            run=0
            for row in range(h):
                idx=col*h+row
                if exclude[idx]:counts['excluded_window_cells']+=1;run=0;continue
                new=bool(wall[idx] and old[idx] and not t[idx])
                counts['new_missing_masonry_cells']+=new
                counts['inherited_cache_missing_masonry_cells']+=bool(wall[idx] and not old[idx] and not t[idx])
                counts['missing_analytic_roof_or_other_cells']+=bool(analytic[idx] and not wall[idx] and not t[idx])
                counts['known_original_gap_empty_cells']+=bool(known[idx] and not analytic[idx] and not t[idx])
                counts['solid_added_in_original_empty_cells']+=bool(t[idx] and not analytic[idx])
                run=run+1 if new else 0
                if run>max_run:
                    max_run=run;u=(s['u0']+col+.5)*PITCH;y=(s['y0']+row+.5)*PITCH
                    longest={'horizontal_m':round(u,8),'y_interval_m':[round(y-(run-.5)*PITCH,8),round(y+.5*PITCH,8)]}
                if new and len(examples)<3:
                    p=[0.,(s['y0']+row+.5)*PITCH,0.];p[s['fixed_axis']]=s['fixed_m'];p[s['horizontal_axis']]=(s['u0']+col+.5)*PITCH
                    examples.append([round(x,8) for x in p])
        result.append({'id':s['id'],'kind':s['kind'],'fixed_axis':s['fixed_axis'],'fixed_m':s['fixed_m'],
                       'horizontal_axis':s['horizontal_axis'],'horizontal_interval_m':[s['u0']*PITCH,s['u1']*PITCH],
                       'vertical_interval_m':[s['y0']*PITCH,s['y1']*PITCH],**counts,
                       'maximum_new_missing_vertical_run_m':round(max_run*PITCH,8),'longest_new_missing_run':longest,
                       'new_missing_masonry_examples_m':examples,**diagnostics['sections'][si]})
    return result


def selftest():
    # A signed closed box; horizontal faces alone must classify its section.
    down=[[0,0,0],[1,0,0],[1,0,1],[0,0,1]]
    up=[[0,1,0],[0,1,1],[1,1,1],[1,1,0]]
    section={'id':'cube','fixed_axis':2,'fixed_m':.025,'horizontal_axis':0,'u0':-1,'u1':21,'y0':-1,'y1':21}
    masks,d=stream_sections(lambda:iter([('a',down),('a',up)]),[section])
    assert sum(masks[0])==400 and d['sections'][0]=={'unbalanced_vertical_rays':0,'negative_winding_cells':0}
    shape={'id':'x','component':'masonry','action':'paint','min':[0,0,0],'max':[1,1,1],'axis':None,'poly':None}
    cut={**shape,'action':'cut','min':[0,.4,0],'max':[1,.6,1]}
    assert analytic_intervals([shape,cut],.25,.25)==([[0,.4],[.6,1]],[[0,.4],[.6,1]])
    assert analytic_intervals([shape,shape,cut],.25,.25)==([[0,.4],[.6,1]],[[0,.4],[.6,1]])
    assert vertical_interval([(0,0),(2,0),(1,2)],.5)==(0.,1.)
    return {'signed_vertical_crossings_closed_box':True,'ordered_component_csg_cut':True,'extruded_triangle_section':True}


class PackedQuad:
    """Audit-only binary64 storage, retaining exact numerical coordinates/order."""
    __slots__=('data',)
    def __init__(self,q):self.data=array('d',(v for p in q for v in p))
    def __len__(self):return 4
    def __getitem__(self,i):
        if isinstance(i,slice):return [self[j] for j in range(4)[i]]
        if i<0:i+=4
        if i<0 or i>=4:raise IndexError(i)
        return self.data[3*i:3*i+3]
    def __iter__(self):
        for i in range(4):yield self[i]


def audit_composition(sc,catalog,interfaces):
    class BoundedComposition(sc.Composition):
        def bind(self,path,role,expected=None,load=True):
            if role=='authored interface fine geometry and seam' and load:
                super().bind(path,role,expected,load=False)
                p=Path(path);p=p if p.is_absolute() else ROOT/p
                return {'groups':({'material':m,'quads':(PackedQuad(q),)} for m,q in sr.iter_quads(p))}
            return super().bind(path,role,expected,load)
    return BoundedComposition(catalog,interfaces)


def save_report(report,output):
    baseline={r['id']:r for r in report.get('runs',{}).get('baseline',{}).get('sections',[])}
    for name,run in report.get('runs',{}).items():
        for row in run.get('sections',[]):
            for key in list(row):
                if (key.endswith('_cells') or key.endswith('_rays') or key=='maximum_new_missing_vertical_run_m') and row[key]==0:row.pop(key)
            if name!='baseline' and row['id'] in baseline:
                for key in ('kind','fixed_axis','fixed_m','horizontal_axis','horizontal_interval_m','vertical_interval_m'):row.pop(key,None)
    report['compact_section_contract']='Omitted section counters equal zero; section domain coordinates are inherited by matching id from baseline.sections.'
    encoded=json.dumps(report,separators=(',',':'))+'\n'
    assert len(encoded.encode())+Path(__file__).stat().st_size<300000,'deliverable size cap exceeded'
    output.write_text(encoded)


def point_parities(factory,queries):
    columns={};states=bytearray(len(queries))
    for i,(x,y,z) in enumerate(queries):columns.setdefault(x,[]).append((z,y,i))
    xs=sorted(columns)
    for x in xs:columns[x].sort()
    zs={x:[p[0] for p in columns[x]] for x in xs};n=0
    for material,q in factory():
        n+=1;y=q[0][1]
        if not all(v[1]==y for v in q):continue
        x0=min(v[0] for v in q);x1=max(v[0] for v in q);z0=min(v[2] for v in q);z1=max(v[2] for v in q)
        for x in xs[bisect_left(xs,x0):bisect_left(xs,x1)]:
            for z,py,index in columns[x][bisect_left(zs[x],z0):bisect_left(zs[x],z1)]:
                if y<=py:states[index]^=1
    return states,n


def edge_roof_audit(path,output):
    """Four transverse off-edge samples using closed-roof Y-ray parity."""
    start=time.monotonic();report=json.loads(output.read_text());doc=json.load(gzip.open(path,'rt'))
    segments=doc['remaining_segments'];points=[]
    for d,a,b,lo,hi in segments:
        fixed=[j for j in range(3) if j!=d]
        for k in range(lo,hi):
            p=[0.,0.,0.];p[d]=(k+.5)*PITCH;p[fixed[0]]=a*PITCH;p[fixed[1]]=b*PITCH
            points.append((d,p))
    queries=[]
    for i,(d,p) in enumerate(points):
        fixed=[j for j in range(3) if j!=d]
        for du,dv in ((-1,-1),(-1,1),(1,-1),(1,1)):
            q=p[:];q[fixed[0]]+=du*1e-5;q[fixed[1]]+=dv*1e-5;queries.append(q)
    roof_path=ROOT/report['runs']['interfaces']['roof_render_path']
    assert len(points)==doc['remaining_unit_edges']
    assert hashlib.sha256(sr._canonical(doc['source_inputs'])).hexdigest()==report['runs']['interfaces']['source_inputs_sha256']
    cube=[('a',[[0,0,0],[1,0,0],[1,0,1],[0,0,1]]),('a',[[0,1,0],[0,1,1],[1,1,1],[1,1,0]])]
    answer,_=point_parities(lambda:iter(cube),[(.5,.5,.5),(.5,-.1,.5),(.5,1.1,.5),(-.01,.5,.5),(1.01,.5,.5),(.5,.5,1.01)])
    assert list(answer)==[1,0,0,0,0,0]
    assert [list(v) for v in PackedQuad(cube[0][1])]==cube[0][1]
    states,n=point_parities(lambda:sr.iter_quads(roof_path),queries)
    masks=bytearray();hidden=0;unknown=[];by_axis=[0,0,0]
    for i,(d,p) in enumerate(points):
        mask=sum(states[4*i+j]<<j for j in range(4));masks.append(mask);hidden+=mask==15
        if mask!=15:
            by_axis[d]+=1
            if len(unknown)<48:unknown.append({'direction':d,'point_m':[round(v,8) for v in p],'roof_quadrant_mask':mask})
    result={'input_edge_face_report_path':str(path),'input_edge_face_report_sha256':sr._file_sha(path),
            'input_remaining_segments':len(segments),'input_remaining_unit_edges':len(points),
            'input_all_odd_unit_edges':doc['input_unpaired_unit_edges'],'already_face_interior_covered_unit_edges':doc['face_interior_covered_unit_edges'],
            'selftests':{'closed_cube_inside_outside_6_probes':True,'packed_coordinate_winding_invariance':True},
            'frozen_roof_sha256':sr._file_sha(roof_path),'frozen_roof_quads':n,
            'strict_frozen_roof_interior_unit_edges':hidden,'not_proven_roof_hidden_unit_edges':len(points)-hidden,
            'not_proven_hidden_by_direction':by_axis,'unresolved_samples':unknown,
            'quadrant_masks_hex':masks.hex(),'quadrant_mask_contract':'One byte per unit edge in input segment order, then lo..hi-1; low four bits correspond to transverse offsets (--),(-+),(+-),(++). 15 means all four sampled neighborhoods are inside the independently closed frozen roof.',
            'proof_scope':'Strict roof-neighborhood coverage only. A non-15 mask is unresolved, not automatically a new exterior gap. Existing source gaps remain separate.',
            'elapsed_seconds':round(time.monotonic()-start,3),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'helper_sha256':sr._file_sha(__file__)}
    print(json.dumps({k:v for k,v in result.items() if k not in ('quadrant_masks_hex','unresolved_samples')}),flush=True)
    report['edge_roof_neighborhood_audit']=result
    report['capacity_failure_history']=[{'hard_address_space_mib':128,'stage':'First all-ray extension allocated coarse section masks while the full composition remained resident','exception':'MemoryError','resolution':'Compute original coarse masks before composition; release composition before analytic masks.'},{'hard_address_space_mib':128,'stage':'Final 10-ROI unmodified Composition interface gzip JSON expansion','exception':'MemoryError: Insufficient memory for buffer allocation','resolution':'Audit-local streaming packed binary64 interface adapter; same 128 MiB limit.'}]
    report['current_helper_sha256']=sr._file_sha(__file__);save_report(report,output)


def gable_outward_audit(manifest_path,output):
    """Only the four already-tested nave/transept gable domains."""
    start=time.monotonic();report=json.loads(output.read_text());manifest=json.loads(manifest_path.read_text())
    phase=report['runs']['interfaces']
    expected=json.load(gzip.open(report['edge_roof_neighborhood_audit']['input_edge_face_report_path'],'rt'))['source_inputs']
    assert hashlib.sha256(sr._canonical(expected)).hexdigest()==phase['source_inputs_sha256']
    actual={item['path']:item for item in manifest['source_inputs']}
    assert all(actual.get(item['path'])==item for item in expected)
    render=ROOT/manifest['render_path'];assert sr._file_sha(render)==manifest['render_sha256']
    count=0;front_blockers=[];front_blocker_count=0
    for material,q in sr.iter_quads(render):
        count+=1;plane=q[0][2]
        if plane<27.7 or not all(v[2]==plane for v in q):continue
        if max(v[1] for v in q)<=29.5 or min(v[1] for v in q)>=39.35:continue
        if max(v[0] for v in q)<=-7.05 or min(v[0] for v in q)>=7.05:continue
        front_blocker_count+=1
        if len(front_blockers)<8:front_blockers.append({'material':material,'quad':q})
    assert count==phase['virtual_quad_count']==manifest['output_quad_count']
    source=ROOT/json.loads(MEASUREMENT.read_text())['source_master_path'];raw=json.loads(source.read_text())
    operations={o['id']:o for c in raw['components'] if c['id']=='masonry' for o in c['operations']}
    features=('nave_gable_rear','nave_gable_front','transept_gable_rear','transept_gable_front');rows=[]
    for feature in features:
        matches=[x for x in phase['new_local_axial_face_loss_sections'] if x['source_feature']==feature]
        chosen=max(matches,key=lambda x:x['remaining_outside_roof_cells']);regions=chosen['connected_regions']
        axis=2 if feature.startswith('nave') else 0
        direction=-1 if feature in ('nave_gable_rear','transept_gable_front') else 1
        bound=manifest['bounds']['min' if direction<0 else 'max'][axis]
        local=chosen['local_ray_interval_m'];covers_bound=local[0]<=bound if direction<0 else local[1]>=bound
        verified=covers_bound or (feature=='nave_gable_front' and front_blocker_count==0)
        lo=[min(g['world_aabb_m']['min'][i] for g in regions) for i in range(3)]
        hi=[max(g['world_aabb_m']['max'][i] for g in regions) for i in range(3)]
        halo_lo=lo[:];halo_hi=hi[:]
        for i in range(3):
            if i!=axis:halo_lo[i]=round(lo[i]-PITCH,8);halo_hi[i]=round(hi[i]+PITCH,8)
        halo_lo[1]=lo[1] # Preserve the shared y boundary of the existing eave ROI.
        # Existing native panel depth is never enlarged toward a known .1m gap.
        rows.append({'source_operation':feature,'source_component':'masonry',
                     'original_operation_sha256':hashlib.sha256(sr._canonical(operations[feature])).hexdigest(),
                     'original_operation':operations[feature],
                     'outward_axis':axis,'outward_sign':direction,'final_global_outward_bound_m':bound,
                     'local_test_band_m':local,'all_outward_rays_unoccluded':verified,
                     'distinct_projected_loss_cells':chosen['remaining_outside_roof_cells'],
                     'projected_loss_area_m2':round(chosen['remaining_outside_roof_cells']*PITCH*PITCH,8),
                     'sampled_loss_aabb_m':{'min':lo,'max':hi},
                     'source_native_one_cell_halo_roi_proposal_m':{'min':halo_lo,'max':halo_hi},
                     'continuous_pixel_regions':regions})
    result={'candidate_render_path':str(render.relative_to(ROOT)),'candidate_render_sha256':manifest['render_sha256'],
            'candidate_manifest_sha256':sr._file_sha(manifest_path),'verified_quad_count':count,
            'front_outward_band_extension_m':[27.7,manifest['bounds']['max'][2]],
            'front_extension_blocking_faces_in_existing_gable_domain':front_blocker_count,'front_extension_blocker_samples':front_blockers,
            'new_exposed_gable_projected_cells':sum(r['distinct_projected_loss_cells'] for r in rows),
            'new_exposed_gable_projected_area_m2':round(sum(r['projected_loss_area_m2'] for r in rows),8),
            'all_four_outward_domains_verified':all(r['all_outward_rays_unoccluded'] for r in rows),'gables':rows,
            'evidence':'Every counted projected cell is original analytic masonry and original coarse FULL-union occupied, had an original local depth face, has no final local depth face, and lies outside the independently closed frozen roof. Rear nave and both transept bands reach beyond the final outward AABB; front nave additionally has zero faces in the remaining outward band. Half-grid transverse samples cannot coincide with grid-aligned parallel faces. This proves a missing outward gable boundary on the tested pixel domains, even where nonclosed vertical winding is nonzero.',
            'roi_scope':'Proposals only, no geometry written. Preserve each exact native source operation and its original panel depth. The .05m tangential halo is clipped at the existing eave ROI upper boundary (y=29.5 nave, y=22 transept) to avoid positive-volume overlap; do not box-fill the triangular exterior, fill the five existing .1m depth joints, or extend roof geometry.',
            'elapsed_seconds':round(time.monotonic()-start,3),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            'helper_sha256':sr._file_sha(__file__)}
    print(json.dumps({k:v for k,v in result.items() if k not in ('gables','evidence','roi_scope')}),flush=True)
    report['gable_outward_exposure_audit']=result;report['current_helper_sha256']=sr._file_sha(__file__);save_report(report,output)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--phase',choices=['baseline','interfaces'],default='baseline')
    ap.add_argument('--interfaces',type=Path);ap.add_argument('--edge-roof',type=Path);ap.add_argument('--gable-outward-manifest',type=Path);args=ap.parse_args();start=time.monotonic()
    resource.setrlimit(resource.RLIMIT_AS,(128*1024*1024,128*1024*1024))
    output=Path(__file__).with_suffix('.json')
    if args.edge_roof:
        edge_roof_audit(args.edge_roof,output);return
    if args.gable_outward_manifest:
        gable_outward_audit(args.gable_outward_manifest,output);return
    report=json.loads(output.read_text()) if output.exists() else {}
    measurement=json.loads(MEASUREMENT.read_text());source=ROOT/measurement['source_master_path'];raw=json.loads(source.read_text())
    assert sr._file_sha(source)==measurement['source_master_sha256'];assert not raw['assembly_cuts']
    assert all(set(i)<= {'id','component'} for i in raw['instances']);assert all(not c.get('transform') for c in raw['components'])
    shapes=[shape_record(c['id'],o) for c in raw['components'] for o in c['operations']]
    sections=make_sections(measurement,shapes);tests=selftest()
    import stream_compose as sc
    assert (HERE/'registered_cathedral_nave_aisles_transept.roof_handoff_snapshot.json').exists()
    print(json.dumps({'stage':'building_virtual_composition','phase':args.phase,'section_count':len(sections)}),flush=True)
    rays=[]
    if args.phase=='interfaces' and 'baseline' in report.get('runs',{}):
        by_id={s['id']:s for s in shapes}
        for row in report['runs']['baseline']['sections']:
            if not row.get('new_missing_masonry_cells',0):continue
            if row['kind']!='gable_panel' and not row['id'].endswith('/outer_025'):continue
            run=row['longest_new_missing_run'];point=[0.,sum(run['y_interval_m'])/2,0.]
            point[row['fixed_axis']]=row['fixed_m'];point[row['horizontal_axis']]=run['horizontal_m']
            feature=by_id[row['id'].split('/')[0]];axis=row['fixed_axis']
            rays.append({'section_id':row['id'],'axis':axis,'point_m':point,
                         'local_interval_m':[feature['min'][axis]-.1,feature['max'][axis]+.1]})
    coarse,coarse_d=stream_sections(lambda:sr.iter_quads(ROOT/measurement['source_render_path']),sections,rays)
    print(json.dumps({'stage':'original_sections_ready','sample_cells':sum(len(m) for m in coarse),'rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}),flush=True)
    comp=audit_composition(sc,CATALOG,args.interfaces)
    windows=comp.windows;roof_path=comp.roof_path;inputs_hash=hashlib.sha256(sr._canonical(comp.inputs)).hexdigest()
    target,diag=stream_sections(comp.factory,sections,rays)
    del comp;gc.collect()
    print(json.dumps({'stage':'composition_sections_ready','rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}),flush=True)
    roof,roof_diag=stream_sections(lambda:sr.iter_quads(roof_path),sections,collect_axial=False)
    assert not any(d['unbalanced_vertical_rays'] or d['negative_winding_cells'] for d in roof_diag['sections'])
    refs=references(sections,shapes,windows)
    rows=summarize(sections,target,coarse,refs,diag)
    axial=axial_loss_regions(sections,refs,coarse,coarse_d,target,diag,roof)
    phase={'input_compositor_sha256':sr._file_sha(sc.__file__),'helper_sha256':sr._file_sha(__file__),
           'source_inputs_sha256':inputs_hash,
           'source_catalog_path':str(CATALOG.relative_to(ROOT)),'source_catalog_sha256':sr._file_sha(CATALOG),
           'roof_render_path':str(roof_path.relative_to(ROOT)),'roof_render_sha256':sr._file_sha(roof_path),
           'virtual_quad_count':diag['quad_count'],'section_count':len(rows),'sections':rows,
           'new_missing_masonry_cells':sum(x['new_missing_masonry_cells'] for x in rows),
           'sections_with_new_missing_masonry':sum(x['new_missing_masonry_cells']>0 for x in rows),
           'unbalanced_vertical_rays':sum(x['unbalanced_vertical_rays'] for x in rows),
           'negative_winding_cells':sum(x['negative_winding_cells'] for x in rows),
           'original_coarse_unbalanced_vertical_rays':sum(x['unbalanced_vertical_rays'] for x in coarse_d['sections']),
           'original_coarse_negative_winding_cells':sum(x['negative_winding_cells'] for x in coarse_d['sections']),
           'orthogonal_local_ray_probes':[{**p,'original_coarse_hits':coarse_d['ray_hits'][i],'target_hits':diag['ray_hits'][i]} for i,p in enumerate(rays)],
           'new_local_axial_face_loss_sections':axial,
           'new_local_axial_face_loss_section_cells':sum(x['new_local_axial_face_loss_cells'] for x in axial),
           'buried_in_independent_closed_roof_section_cells':sum(x['buried_in_independent_closed_roof_cells'] for x in axial),
           'remaining_axial_face_loss_outside_roof_section_cells':sum(x['remaining_outside_roof_cells'] for x in axial),
           'independent_closed_roof_section_quad_count':roof_diag['quad_count'],
           'interface_input_storage':'Streaming SHA-validated interface input; packed binary64 quads, original numeric coordinates and winding unchanged.',
           'preserved_capacity_failure':{'hard_address_space_mib':128,'stage':'unmodified Composition interface gzip full JSON expansion','exception':'MemoryError: Insufficient memory for buffer allocation','response':'Audit-local streaming packed interface adapter; cap unchanged.'},
           'elapsed_seconds':round(time.monotonic()-start,3),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
           'interface_catalog_path':str(args.interfaces) if args.interfaces else None,
           'interface_catalog_sha256':sr._file_sha(args.interfaces) if args.interfaces else None}
    report.update(schema='riverstone.cathedral.interface_axial_audit.v1',helper_sha256=sr._file_sha(__file__),
                  pitch_m=PITCH,selftests=tests,measurement_sha256=sr._file_sha(MEASUREMENT),
                  original_source_master_sha256=measurement['source_master_sha256'],
                  original_source_render_sha256=measurement['source_render_sha256'],
                  method='Signed horizontal render-face crossings on 45 bounded vertical sections, compared with independent original analytic component CSG and original coarse-render masks.',
                  classification={'new_missing_masonry_cells':'Original analytic masonry AND original coarse render occupied; target composition empty. Excludes authorized window ROIs. A candidate new coarse/fine seam loss.',
                                  'inherited_cache_missing_masonry_cells':'Original analytic masonry occupied but both original coarse render and target empty; inherited coarse sampling deficit.',
                                  'known_original_gap_empty_cells':'Analytically empty original source in measured eave gap envelopes or the five 0.1m gable-depth joints; not a new leak.',
                                  'missing_analytic_roof_or_other_cells':'Source roof/other occupancy differs from target; may reflect intentional fine roof geometry and is not automatically called a leak.'},
                  limitations=['Finite axial sections are not an exhaustive 3D leak/visibility certificate.','Cell-center section sampling cannot resolve sub-0.05m slits.','Original continuous-source gaps and intentional gable/attic interiors are not filled or classified as new missing masonry.','Window replacement ROIs are excluded from masonry-loss classification.','No voxel compiler or output render is created; only bounded 2D arrays are held.'])
    report['local_axial_proof_scope']='A counted cell lies in original analytic masonry AND occupied original coarse full union, had an original coarse face along the local wall/panel depth ray, and has no final face of any material anywhere in that local depth band. Connected AABBs bound sampled losses; they are not authorization to fill boxes. Counts from distinct depth sections can overlap. Candidates inside the independently closed frozen roof are counted separately and removed from connected remaining regions. Target vertical emptiness is reported per remaining region; inconsistent winding is still not a global visibility proof. A remote component outside the tested local band may still occlude a world-space view.'
    for previous in report.get('runs',{}).values():
        if 'source_inputs' in previous:
            previous['source_inputs_sha256']=hashlib.sha256(sr._canonical(previous.pop('source_inputs'))).hexdigest()
            previous['source_catalog_path']=str(CATALOG.relative_to(ROOT));previous['source_catalog_sha256']=sr._file_sha(CATALOG)
    previous=report.setdefault('runs',{}).get(args.phase)
    if previous and previous.get('interface_catalog_sha256')!=phase['interface_catalog_sha256']:
        keep=('interface_catalog_path','interface_catalog_sha256','virtual_quad_count','new_missing_masonry_cells','new_local_axial_face_loss_section_cells','orthogonal_local_ray_probes','elapsed_seconds','max_rss_kib','helper_sha256')
        report.setdefault('superseded_run_summaries',[]).append({**{k:previous[k] for k in keep if k in previous},'full_phase_sha256':hashlib.sha256(sr._canonical(previous)).hexdigest()})
    report['runs'][args.phase]=phase
    # Keep detailed loss intervals/probes; drop repeated empty examples and
    # secondary roof-style diagnostics from the human-readable bounded report.
    for run in report['runs'].values():
        for row in run['sections']:
            for key in ('missing_analytic_roof_or_other_cells','solid_added_in_original_empty_cells','new_missing_masonry_examples_m'):
                row.pop(key,None)
            if row.get('longest_new_missing_run') is None:row.pop('longest_new_missing_run',None)
    print(json.dumps({k:v for k,v in phase.items() if k not in ('sections','source_inputs')}),flush=True)
    save_report(report,output)


if __name__=='__main__':main()
