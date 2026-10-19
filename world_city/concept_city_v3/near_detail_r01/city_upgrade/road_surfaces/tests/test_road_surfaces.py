import copy
import hashlib
import json
import math
from pathlib import Path
import sys
import unittest
import numpy as np

HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE))
import road_surface_index as r


def face(vertices,index=0):
    geometry,error=r.geometry_check(vertices)
    if error:raise ValueError(error)
    return {'tile_id':'fixture','face_index':index,'vertices_xyz_m':vertices,**geometry}


def rectangle(x0,z0,x1,z1,plane=(0,0,0)):
    a,b,c=plane
    p=[[x,a*x+b*z+c,z] for x,z in [(x0,z0),(x1,z0),(x1,z1),(x0,z1)]]
    return [face([p[0],p[2],p[1]]),face([p[0],p[3],p[2]],1)]


class RoadSurfaces(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index=r.read(HERE/'generated/source_index.json');cls.report=r.read(HERE/'generated/selection_report.json')
        cls.source=r.read(r.checked_ref(cls.index['source_tile_index']))

    def test_full_source_tile_hashes_counts_and_rle(self):
        self.assertEqual(len(self.index['tiles']),360)
        total=0
        for tid,record in self.index['tiles'].items():
            source=self.source['tiles'][tid]
            self.assertEqual(r.sha(r.ROOT/source['terrain_path']),record['source_binary_sha256'])
            self.assertEqual(r.sha(r.ROOT/source['instances_path']),record['source_companion_sha256'])
            last=-1;count=0
            blob=(r.ROOT/source['terrain_path']).read_bytes()
            self.assertEqual(len(blob),record['face_count']*88)
            for start,end,owners in record['eligible_face_runs']:
                self.assertGreaterEqual(start,last);self.assertLess(start,end);self.assertLessEqual(end,record['face_count']);last=end;count+=end-start
                self.assertTrue(owners)
                self.assertTrue(all(0<=owner<len(self.index['owners']) for owner in owners))
                for at in (start,end-1):
                    _,provenance=r.decode_face(blob,at)
                    self.assertIn(self.source['material_ids'][provenance[1]],['road','space_civic'])
            self.assertEqual(count,record['eligible_face_count']);total+=count
        self.assertEqual(total,50771)
        self.assertEqual(self.report['all_source_faces_read'],1397505)

    def test_selection_is_conservative_and_not_whole_city_claim(self):
        self.assertEqual(self.report['counts']['source/stair'],0)
        self.assertEqual(self.report['counts']['selected/road'],42746)
        self.assertEqual(self.report['counts']['selected/space_civic'],8025)
        self.assertNotIn('selected/alley',self.report['counts'])
        self.assertNotIn('selected/ground_stone',self.report['counts'])
        self.assertFalse(self.index['whole_city_coverage_pass'])
        self.assertTrue(self.report['native_stair_candidates'])
        self.assertTrue(all(v['status'].startswith('NOT_SELECTED') for v in self.report['native_stair_candidates']))

    def test_actual_selected_faces_match_public_source_owner(self):
        header=r.scene_header(r.checked_ref(self.index['source_scene']));owners,domains=r.make_domains(header);di=r.DomainIndex(domains)
        self.assertEqual(owners,self.index['owners'])
        for tid,record in self.index['tiles'].items():
            source=self.source['tiles'][tid];blob=(r.ROOT/source['terrain_path']).read_bytes()
            for start,end,owners in record['eligible_face_runs'][::max(1,len(record['eligible_face_runs'])//3)]:
                vertices,provenance=r.decode_face(blob,start);g,error=r.geometry_check(vertices);self.assertIsNone(error)
                material=self.source['material_ids'][provenance[1]]
                self.assertTrue(r.domain_owners([[v[0],v[2]] for v in vertices],material,di))

    def test_bounded_actual_queries_including_negative_coordinates(self):
        for observer in ([90,4.9,20],[-240,12.5,-85],[140,2,600]):
            q=r.query_sources(self.index,observer,8,4096)
            self.assertTrue(q['faces']);self.assertFalse(q['truncated'])
            self.assertTrue(all(f['grade']<=.25 for f in q['faces']))
        q=r.query_sources(self.index,[90,4.9,20],8,1);self.assertTrue(q['truncated']);self.assertEqual(len(q['faces']),1)
        with self.assertRaises(ValueError):r.query_sources(self.index,[0,0,0],13)

    def test_rigid_slope_frame_preserves_plane_and_normal(self):
        frame,origin=r.rigid_frame([.1,.05,4])
        self.assertTrue(np.allclose(frame.T@frame,np.eye(3)));self.assertAlmostEqual(np.linalg.det(frame),1)
        for u,v in [(0,0),(1,0),(1,1),(0,1)]:
            p=frame@np.asarray([u,v,0])+origin;self.assertAlmostEqual(p[1],.1*p[0]+.05*p[2]+4)
        self.assertTrue(np.allclose(r.rigid_frame([0,0,0])[0],[[1,0,0],[0,0,1],[0,-1,0]]))

    def test_exact_footprint_cannot_bridge_gap_or_step(self):
        corners=[[0,0,0],[1,0,0],[1,0,1],[0,0,1]]
        self.assertTrue(r.footprint_supported(corners,rectangle(0,0,1,1)))
        self.assertFalse(r.footprint_supported(corners,rectangle(0,0,.49,1)+rectangle(.51,0,1,1)))
        self.assertFalse(r.footprint_supported(corners,rectangle(0,0,.5,1)+rectangle(.5,0,1,1,(0,0,.1))))
        self.assertFalse(r.footprint_supported(corners,rectangle(0,0,1,1)[:1]))
        self.assertFalse(r.footprint_supported(corners,rectangle(0,0,1,1,(.1,0,0))))

    def test_degenerate_downward_and_riser_faces_rejected(self):
        self.assertIsNotNone(r.geometry_check([[0,0,0],[1,0,0],[0,0,1]])[1])
        self.assertIsNotNone(r.geometry_check([[0,0,0],[0,1,0],[1,0,0]])[1])
        self.assertIsNotNone(r.geometry_check([[0,0,0],[0,0,0],[0,0,0]])[1])
        self.assertIsNotNone(r.geometry_check([[0,0,0],[1,2,1],[1,2,0]])[1])

    def test_reference_planner_is_bounded_trimmed_and_collision_free(self):
        faces=rectangle(-3,-3,3,3,(.1,0,0))
        planned=r.plan_local_modules(faces,[0,.9,0],radius_m=2,max_modules=12)
        self.assertTrue(planned['modules']);self.assertLessEqual(len(planned['modules']),12)
        for module in planned['modules']:
            self.assertFalse(module['collision_change']);self.assertEqual(module['maximum_visual_collision_difference_m'],.0375)
            frame=np.asarray(module['transform']['basis']);position=np.asarray(module['transform']['translation'])
            self.assertAlmostEqual(np.linalg.det(frame),1)
            size=module['width_m'];self.assertTrue(all(o+size<=1+1e-8 for o in module['trim_offset_m']))
            corners=[frame@np.asarray([u,v,-.0375])+position for u,v in [(0,0),(size,0),(size,size),(0,size)]]
            self.assertTrue(r.footprint_supported(corners,faces))
            self.assertLessEqual(max(math.hypot(q[0],q[2]) for q in corners),2+1e-8)

    def test_union_owner_policy_rejects_ambiguous_material(self):
        domains=[{'owner':0,'material':'road','polygon_xz_m':[[0,0],[1,0],[1,1],[0,1]],'bounds':[0,0,1,1]}]
        di=r.DomainIndex(domains);poly=[[.1,.1],[.8,.1],[.1,.8]]
        self.assertEqual(r.domain_owners(poly,'road',di),[0])
        self.assertEqual(r.domain_owners(poly,'alley',di),[])
        self.assertEqual(r.domain_owners([[0,0],[2,0],[0,2]],'road',di),[])

    def test_small_artifact_budget(self):
        self.assertLess(sum(p.stat().st_size for p in HERE.rglob('*') if p.is_file()),8000000)
        self.assertFalse(any(p.suffix=='.bin' for p in HERE.rglob('*')))

if __name__=='__main__':unittest.main(verbosity=2)
