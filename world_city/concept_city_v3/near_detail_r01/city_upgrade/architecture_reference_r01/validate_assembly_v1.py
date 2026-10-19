"""Conservative source envelope/route checks plus explicit support witnesses.

Not a structural engineering certification or full compiled connectivity proof.
Exact empty-region proofs cover rigid axis-aligned boxes and later encompassing
box cuts. Ambiguous polygon overlap refuses to certify the route as clear.
"""
from itertools import product
from parts_v1 import core,need
EPS=1e-8


def world_records(master):
    cs,ins=core.validate_master(master,.05);ts={};visiting=set()
    def trans(key):
        if key not in ts:
            need(key not in visiting,'Instance cycle');visiting.add(key);i=ins[key];t=core.transform(i.get('transform'))
            if i.get('parent'):t=core.compose(trans(i['parent']),t)
            ts[key]=t;visiting.remove(key)
        return ts[key]
    rows=[]
    for i in ins.values():
        for index,op in enumerate(cs[i['component']]['operations']):
            t=core.compose(trans(i['id']),core.transform(op.get('transform')));s=core.prepare_shape(op['shape'],.05);lo,hi=core.shape_bounds(s)
            points=[core.apply(t,p) for p in product(*zip(lo,hi))];bounds={'min':[min(p[j] for p in points) for j in range(3)],'max':[max(p[j] for p in points) for j in range(3)]}
            signed_permutation=all(sum(abs(v)>EPS for v in row)==1 and abs(sum(v*v for v in row)-1)<EPS for row in t['basis'])
            rows.append({'instance':i['id'],'component':i['component'],'index':index,'op':op,'shape':s,'transform':t,'bounds':bounds,'axis_box':op['shape']['kind']=='box' and signed_permutation})
    need(not master.get('assembly_cuts'),'Assembly cuts need a separate route proof; implicit omission forbidden')
    return rows


def intersect(a,b):
    lo=[max(a['min'][j],b['min'][j]) for j in range(3)];hi=[min(a['max'][j],b['max'][j]) for j in range(3)]
    return {'min':lo,'max':hi} if all(hi[j]-lo[j]>EPS for j in range(3)) else None


def encompasses(a,b):return all(a['min'][j]<=b['min'][j]+EPS and a['max'][j]>=b['max'][j]-EPS for j in range(3))


def empty_reservation(rows,box):
    blockers=[]
    for r in rows:
        o=r['op']
        if o['action']!='paint':continue
        overlap=intersect(r['bounds'],box)
        if overlap is None:continue
        label={'instance':r['instance'],'component':r['component'],'part':o['part'],'material':o['material'],'feature':o['id']}
        cleared=any(c['instance']==r['instance'] and c['index']>r['index'] and c['op']['action']=='cut' and c['axis_box'] and core.selector_matches(c['op'].get('selector',{}),label) and encompasses(c['bounds'],overlap) for c in rows)
        if not cleared:blockers.append({'instance':r['instance'],'operation':o['id'],'overlap_bounds':overlap,'proof':'definite_box_overlap' if r['axis_box'] else 'conservative_polygon_bound_requires_additional_proof'})
    return {'clear':not blockers,'blockers':blockers,'proof_scope':'All paint domains disjoint from reservation or each overlap fully removed by a later exact axis-aligned component box cut. Later paints are separately checked.'}


def point_labels(rows,point):
    labels={}
    for r in rows:
        o=r['op'];inst=r['instance']
        if not core.contains(r['shape'],core.inverse(r['transform'],point)):continue
        if o['action']=='cut':
            if inst in labels and core.selector_matches(o.get('selector',{}),labels[inst]):labels.pop(inst)
        else:labels[inst]={'instance':inst,'component':r['component'],'part':o['part'],'material':o['material'],'feature':o['id']}
    return labels


def validate(master,contract):
    rows=world_records(master);envelope=contract['envelope'];outside=[]
    for r in rows:
        if r['op']['action']=='paint' and not encompasses(envelope,r['bounds']):outside.append({'instance':r['instance'],'operation':r['op']['id'],'bounds':r['bounds']})
    reservations=[]
    for r in contract.get('reservations',[]):
        need(r.get('kind') in ('entry_passage','gallery_walk','room_to_gallery','balcony_door'),'Explicit pedestrian reservation kind required')
        proof=empty_reservation(rows,r['bounds']);reservations.append({'id':r['id'],'kind':r['kind'],**proof})
    connections=[]
    for c in contract.get('support_connections',[]):
        need(c.get('a')!=c.get('b'),'A support connection requires two instances');points=c['contact_witnesses'];need(points,'Contact witnesses required')
        matches=[all(inst in point_labels(rows,p) for inst in (c['a'],c['b'])) for p in points]
        connections.append({'id':c['id'],'a':c['a'],'b':c['b'],'witness_count':len(points),'all_points_inside_both_sources':all(matches)})
    doors=master.get('metadata',{}).get('openings',[]);bad_doors=[d['id'] for d in doors if d.get('kind')=='door' and (d.get('state')!='open_passage' or abs(d['bottom_world_y']-d['deck_top_y'])>EPS)]
    return {'schema':'riverstone.architecture.assembly_source_validation.v1','outside_envelope_operations':outside,'reservations':reservations,'support_connections':connections,'bad_balcony_door_ids':bad_doors,'all_pass':not outside and not bad_doors and all(x['clear'] for x in reservations) and all(x['all_points_inside_both_sources'] for x in connections),'proof_scope':'Conservative entire source AABB enclosure, exact box/cut route domains, and explicitly sampled analytic support contacts. Source-only; no complete structure/load, global voxel connectivity or visual quality certification.'}
