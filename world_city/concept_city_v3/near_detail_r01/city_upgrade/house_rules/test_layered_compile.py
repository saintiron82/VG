import copy
import math
from pathlib import Path
import sys
import unittest
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import layered_compile as l


def toy():
    return {'schema':l.a.core.SCHEMA,'id':'layer_contract_toy','revision':1,
        'axes':{'up':'+Y','front':'+Z','right':'+X'},'grid_origin':[0,0,0],
        'materials':{'stone':{'color':'888888'},'glass':{'color':'335577'}},
        'components':[{'id':'body','parts':[{'id':'solid','pivot':[0,0,0]}],
            'operations':[l.a.box('body',[0,0,0],[.4,.4,.4],'stone')]}],
        'instances':[{'id':'body','component':'body','transform':{'translation':[0,0,0]}}],
        'constraints':[],'assembly_cuts':[]}


def compiled(master,pitch=.05):
    return l.a.core.compile_master(master,{'pitch':pitch},max_candidate_cells=20000,max_output_cells=10000)


class LayerCompilerContracts(unittest.TestCase):
    def setUp(self):self.rules=l.a.load(HERE/'layer_rules.v1.json')

    def test_hidden_uniform_core_is_lossless_and_surface_is_fine(self):
        master=toy();fine=compiled(master);coarse=compiled(master,.1)
        own,near,core,cells=l.split_cells(fine,coarse,[0,0,0],[8,8,8],self.rules)
        self.assertEqual(len(core),8)
        reconstructed={tuple(row[:3]):row[3:] for row in near}
        for row in core:
            for dx,dy,dz in l.itertools.product((0,1),repeat=3):
                key=(2*row[0]+dx,2*row[1]+dy,2*row[2]+dz)
                self.assertNotIn(key,reconstructed);reconstructed[key]=row[3:]
        self.assertEqual(reconstructed,{tuple(r[:3]):r[3:] for r in own})
        self.assertTrue(all(tuple(row[:3]) in {tuple(r[:3]) for r in near} for row in own if any(q not in cells for q in l.a.core.neighbors(tuple(row[:3])))))

    def test_all_original_cuts_and_later_paints_survive_roi(self):
        master=toy();ops=master['components'][0]['operations']
        ops.append(l.a.box('aperture',[.1,.1,-.1],[.3,.3,.5],action='cut'))
        ops.append(l.a.box('recessed_glass',[.1,.1,.03],[.3,.3,.08],'glass'))
        full=compiled(master)
        source=l.SpatialSource(master,.05)
        crop=compiled(source.crop([.05,.05,0],[.35,.35,.2]))
        expect=[row for row in full['cells'] if l.owned(row[:3],[1,1,0],[7,7,4])]
        self.assertEqual(crop['cells'],expect)

    def test_translated_rotated_extrusion_crop_matches_global_grid(self):
        master=toy();master['components'][0]['operations']=[l.a.prism('slope',[[0,0],[.4,.2],[.4,.4],[0,.2]],0,.4,'stone')]
        master['instances'][0]['transform']={'translation':[.033,.017,.011],'basis':[[0,0,1],[0,1,0],[-1,0,0]]}
        full=compiled(master);source=l.SpatialSource(master,.05)
        crop=compiled(source.crop([.1,.05,-.3],[.35,.35,0]))
        expect=[row for row in full['cells'] if l.owned(row[:3],[2,1,-6],[7,7,0])]
        self.assertEqual(crop['cells'],expect)

    def test_minimum_cells_is_resolved_before_crop(self):
        master=toy();master['components'][0]['operations'][0]['shape']={'kind':'box','min':[.03,.03,.03],'max':[.04,.04,.04],'minimum_cells':[2,2,2]}
        full=compiled(master);crop=compiled(l.SpatialSource(master,.05).crop([0,0,0],[.05,.05,.05]))
        self.assertEqual(crop['cells'],[r for r in full['cells'] if l.owned(r[:3],[0,0,0],[1,1,1])])

    def test_protected_detail_is_never_aggregated(self):
        master=toy();master['components'][0]['operations'][0]['id']='body__near_tile'
        own,near,core,_=l.split_cells(compiled(master),compiled(master,.1),[0,0,0],[8,8,8],self.rules)
        self.assertEqual(core,[]);self.assertEqual(own,near)

    def test_chunk_mesh_has_no_internal_or_duplicate_faces(self):
        full=compiled(toy());render=l.make_render_data(full);cells={tuple(r[:3]):r for r in full['cells']}
        combined=set()
        for lo,hi in [([0,0,0],[4,8,8]),([4,0,0],[8,8,8])]:
            quads,faces=l.owned_quads(render,lo,hi,self.rules)
            expected=l.expected_faces([r for r in full['cells'] if l.owned(r[:3],lo,hi)],cells)
            self.assertEqual(faces,expected);self.assertFalse(combined.intersection(faces));combined.update(faces)
        self.assertEqual(combined,l.expected_faces(full['cells'],cells))
        self.assertFalse(any(f[0]==0 and f[2]==4 for f in combined))

    def test_unsupported_transform_and_shared_component_are_pending(self):
        master=toy();c=math.sqrt(.5)
        master['instances'][0]['transform']['basis']=[[c,0,c],[0,1,0],[-c,0,c]]
        with self.assertRaises(l.a.UnsupportedSurface):l.SpatialSource(master,.05)
        master=toy();master['instances'].append({'id':'copy','component':'body','transform':{'translation':[1,0,0]}})
        with self.assertRaises(l.a.UnsupportedSurface):l.SpatialSource(master,.05)


if __name__=='__main__':unittest.main(verbosity=2)
