#!/usr/bin/env python3
"""Streaming render audit: never expands the whole JSON or whole fine house."""
from validate_exterior import *
from candidate_oracle import CandidateOracle
import gc

class JsonStream:
    def __init__(self,stream):self.stream=stream;self.buffer='';self.position=0;self.eof=False;self.decoder=json.JSONDecoder()
    def fill(self):
        if self.position:
            self.buffer=self.buffer[self.position:];self.position=0
        chunk=self.stream.read(65536)
        if not chunk:self.eof=True
        self.buffer+=chunk
    def space(self):
        while True:
            while self.position<len(self.buffer) and self.buffer[self.position].isspace():self.position+=1
            if self.position<len(self.buffer) or self.eof:return
            self.fill()
    def peek(self):self.space();return self.buffer[self.position] if self.position<len(self.buffer) else ''
    def eat(self,c):
        assert self.peek()==c,('Expected JSON token',c,self.peek());self.position+=1
    def value(self):
        self.space()
        while True:
            try:
                result,end=self.decoder.raw_decode(self.buffer,self.position)
                if end==len(self.buffer) and not self.eof:self.fill();continue
                self.position=end;return result
            except json.JSONDecodeError:
                if self.eof:raise
                self.fill()

def stream_render(path):
    holder={'schema':'riverstone.voxel.render.v1','unit':'m','quad_count':None}
    def groups():
        with gzip.open(path,'rt') if str(path).endswith('.gz') else open(path) as f:
            p=JsonStream(f);p.eat('{');top_seen=set();actual_quads=0
            while p.peek()!='}':
                key=p.value();assert key not in top_seen,'Duplicate render key';top_seen.add(key);p.eat(':')
                if key=='groups':
                    p.eat('[')
                    while p.peek()!=']':
                        p.eat('{');material=None;group_seen=set()
                        while p.peek()!='}':
                            field=p.value();assert field not in group_seen;group_seen.add(field);p.eat(':')
                            if field=='material':material=p.value()
                            elif field=='quads':
                                assert isinstance(material,str),'Material must precede streamed quads'
                                p.eat('[')
                                while p.peek()!=']':
                                    q=p.value();actual_quads+=1;yield {'material':material,'quads':[q]}
                                    if p.peek()==',':p.eat(',')
                                    else:break
                                p.eat(']')
                            else:raise AssertionError('Unknown render group field')
                            if p.peek()==',':p.eat(',')
                            else:break
                        p.eat('}');assert group_seen=={'material','quads'}
                        if p.peek()==',':p.eat(',')
                        else:break
                    p.eat(']')
                else:holder[key]=p.value()
                if p.peek()==',':p.eat(',')
                else:break
            p.eat('}');assert p.peek()=='' and holder['schema']=='riverstone.voxel.render.v1' and holder['unit']=='m'
            assert actual_quads==holder['quad_count'],'Streamed quad count mismatch'
    holder['groups']=groups();return holder

def prove_lower(path):
    def extract(path):
        lower=[];data=stream_render(path)
        for g in data['groups']:
            q=g['quads'][0];n=cross(sub(q[1],q[0]),sub(q[2],q[0]));ys=[p[1] for p in q]
            below=(ys[0]<9.5 or (ys[0]==9.5 and n[1]>0)) if min(ys)==max(ys) else max(ys)<=9.5
            if below:lower.append((g['material'],tuple(tuple(p) for p in q)))
        return sorted(lower)
    old=extract(ARCH/'foundation_repair_r01/foundation_repaired.render.json.gz');new=extract(path)
    assert old==new,'Lower original quads changed'
    return len(old)

def run():
    started=time.monotonic();path=R/'roof_repaired.render.json.gz';composition=read(R/'composition.json');before=sha(path)
    assert all(composition['render'][k]==v for k,v in ref(path).items())
    assert sha(ARCH/'roof_repair_r02/roof_repaired.render.json.gz')=='d71a5987debe5e3e22a3663f8ee4b604bd7d880a0fa7d8188e4d9247c26edb17'
    original_lower=prove_lower(path);gc.collect()
    oracle=CandidateOracle(ARCH/'foundation_repair_r01/foundation_arrays.npz',R/'upper_union_arrays.npz');adapter,order=adapter_order()
    render=stream_render(path);report=audit_render(render,oracle,{n:i for i,n in enumerate(oracle.names)},order,interface_y=304,extra_interfaces={(2,z) for z in composition['mesher_chunk_edges_z']})
    expected_materials=dict(read(ARCH/'foundation_repair_r01/foundation_revised.master.json.gz')['materials']);expected_materials.update(read(R/'roof_patch.master.json.gz')['materials'])
    assert render['materials']==expected_materials,'Render palette differs from preserved source and source-derived roof palette'
    assert list(expected_materials)==oracle.names,'Union material IDs differ from source material order'
    assert render['grid_origin']==[0,0,0] and render['pitch']==PITCH
    report['render_palette_matches_exact_source_colors']=True
    report.update(schema='riverstone.roof_repair_r03.independent_render_proof.v1',status='TECHNICAL_PASS' if report['outward_CCW_matches_actual_solid_exterior'] else 'TECHNICAL_FAIL',original_lower_quads_exact=original_lower,candidate_render=ref(path),validator=ref(Path(__file__)),face_validator=ref(HERE/'validate_exterior.py'),godot_adapter=ref(adapter),source_unchanged=sha(path)==before,visual_acceptance='REQUIRES_PARENT_ACTUAL_SEVEN_VIEW_REVIEW',sampling_calls=0,mesher_calls=0,full_house_fine_volume_allocated=False,full_render_JSON_expanded=False,address_space_limit_mib=256,peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,elapsed_seconds=time.monotonic()-started)
    save(HERE/'render_validation.json',report);print(json.dumps(report,sort_keys=True))
    assert report['outward_CCW_matches_actual_solid_exterior'] and report['source_unchanged']
if __name__=='__main__':run()
