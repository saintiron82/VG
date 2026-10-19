#!/usr/bin/env python3
"""Small invariants plus a full generated-pack structural/ownership audit.

For full independent source-coordinate parity also run build_city_tiles.py
--verify --deep. No Godot, GUI, compiler, or source writes are used here.
"""
import collections
import math
import unittest

import numpy as np

import build_city_tiles as b


class TilePolicyTests(unittest.TestCase):
    def test_binary_record_is_88_bytes_lossless(self):
        values=[-188.2950486829768,15.937628494523967,-253.02105735114577]*3
        raw=b.RECORD.pack(*values,1,12,12345,4)
        self.assertEqual(len(raw),88)
        self.assertEqual(b.DTYPE.itemsize,88)
        row=np.frombuffer(raw,dtype=b.DTYPE)[0]
        self.assertEqual(row['vertices'].reshape(-1).tolist(),values)
        self.assertEqual([int(row[k]) for k in b.DTYPE.names[1:]],[1,12,12345,4])

    def test_centroid_single_owner_including_negative(self):
        self.assertEqual(b.owner_of([[-65,1,-1],[-63,1,-1],[-64,1,2]]),'-1_0')

    def test_exact_zero_edge_includes_both_sides(self):
        self.assertEqual(set(b.cells_for_bounds([0,0,0,0])),{'-1_-1','-1_0','0_-1','0_0'})

    def test_exact_positive_and_negative_edges(self):
        self.assertEqual(set(b.cells_for_bounds([-64,64,-64,64])),{'-2_0','-2_1','-1_0','-1_1'})

    def test_whole_triangle_not_centroid_only(self):
        tri=[[-200,3,-200],[200,3,-200],[0,3,200]]
        cells=set(b.cells_for_bounds(b.xz_bounds(tri)))
        self.assertEqual(len(cells),64)
        self.assertIn('-4_-4',cells)
        self.assertIn('3_3',cells)

    def test_native_yaw_and_basis_bounds(self):
        bounds={'min':[-1,0,-3],'max':[1,2,3]}
        p={'position_m':[100,4,100],'yaw_rad':math.pi/2}
        np.testing.assert_allclose(b.instance_bounds(p,bounds),[97,99,103,101],rtol=0,atol=1e-12)
        p['transform']={'basis':[[1,0,0],[0,0,-1],[0,1,0]]}
        np.testing.assert_allclose(b.instance_bounds(p,bounds),[99,100,101,102],rtol=0,atol=1e-12)

    def test_dedup_exact_only_and_preserves_orientation(self):
        t=[[0,0,0],[1,0,0],[0,0,1]]
        self.assertEqual(b.face_key(t),b.face_key(t[::-1]))
        self.assertEqual(b.face_key(t,True),b.face_key(t[1:]+t[:1],True))
        self.assertNotEqual(b.face_key(t,True),b.face_key(t[::-1],True))
        other=[[0,0,0],[1+1e-12,0,0],[0,0,1]]
        self.assertNotEqual(b.face_key(t),b.face_key(other))

    def test_reject_nonfinite_and_degenerate(self):
        for tri in [[[0,0,0],[1,0,0],[2,0,0]],[[0,0,0],[1,float('nan'),0],[0,0,1]]]:
            with self.assertRaises(ValueError):b.checked_triangles([tri],'test')

    def test_reject_wrong_top_winding(self):
        with self.assertRaises(ValueError):b.checked_triangles([[[0,0,0],[1,0,0],[0,0,1]]],'test',require_up=True)

    def test_hash_drift_is_rejected(self):
        with self.assertRaises(ValueError):
            b.resolve({'path':b.relative(b.HERE/'build_city_tiles.py'),'sha256':'0'*64})

    def test_unsupported_contracts_are_rejected(self):
        supported=[{'id':c} for c in b.SUPPORTED_CONTRACTS]
        b.validate_contract_set(supported)
        for contracts in [supported[:-1],supported+[{'id':'UNSUPPORTED_FALLBACK_FLOOR'}],supported+[supported[0]]]:
            with self.assertRaises(ValueError):b.validate_contract_set(contracts)

    def test_output_override_fresh_repository_path(self):
        import uuid
        relative='world_city/concept_city_v3/playable_r01/generated/unit_uncreated_'+uuid.uuid4().hex
        expected=b.ROOT/relative
        self.assertEqual(b.validate_output(relative,fresh=True),expected)
        self.assertEqual(b.validate_output(expected,fresh=True),expected)
        self.assertFalse(expected.exists())

    def test_output_override_rejects_existing_and_outside(self):
        with self.assertRaisesRegex(ValueError,'will be preserved'):
            b.validate_output(b.OUT,fresh=True)
        for path in ['/tmp/tile_pack_output_test', b.ROOT/'..'/'escaped_output_test']:
            with self.assertRaisesRegex(ValueError,'inside the repository'):
                b.validate_output(path,fresh=True)
            with self.assertRaisesRegex(ValueError,'inside the repository'):
                b.validate_output(path,fresh=False)
        self.assertEqual(b.validate_output(b.OUT,fresh=False),b.OUT)

    def test_source_input_identity(self):
        for path,digest in b.INPUTS.values():self.assertEqual(b.sha(b.CITY/path),digest)


class GeneratedPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not (b.OUT/'index.json').exists():raise unittest.SkipTest('Pack not yet completely generated')
        cls.index=b.read(b.OUT/'index.json')

    def test_pack_size_and_public_policy(self):
        self.assertLess(sum(p.stat().st_size for p in b.OUT.rglob('*') if p.is_file()),200_000_000)
        p=self.index['loading_policy']
        self.assertTrue(p['whole_triangles_only'])
        self.assertTrue(p['no_fallback_floor'])
        self.assertFalse(p['water_support'])
        self.assertGreaterEqual(p['safety_margin_m'],p['capsule_max_radius_m']+p['spring_arm_max_length_m'])
        self.assertEqual(self.index['render_materials'],self.index['materials'])

    def test_exact_contract_policy(self):
        contracts=self.index['collision_contracts']
        self.assertEqual({c['id'] for c in contracts},b.SUPPORTED_CONTRACTS)
        disabled={p for c in contracts for p in c.get('disable_native_mesh_collider_ids',[])}
        self.assertEqual(disabled,set(self.index['disabled_native_instance_ids']))
        self.assertIn('PHASE02:real_neighborhood_stair:0',disabled)
        self.assertNotIn('BRIDGE_MAIN_RIVER:DRAWBRIDGE_FIXED',disabled)
        fixed=next(c for c in contracts if c['id']=='FIXED_BRIDGE_STONE_SPANS_CONTINUOUS_WALK_R02')
        self.assertEqual(fixed['source_native_face_retirements'],[])
        self.assertEqual(fixed['triangle_count'],29184)

    def test_every_generated_hash_binary_id_and_face(self):
        native_ids=set();box_ids=set();contract_faces=set();face_ids=set();counts=collections.Counter()
        for ident,record in self.index['tiles'].items():
            binary=b.resolve({'path':record['terrain_path'],'sha256':record['terrain_sha256']})
            tile=b.read(b.resolve({'path':record['instances_path'],'sha256':record['instances_sha256']}))
            a=np.fromfile(binary,dtype=b.DTYPE)
            self.assertEqual(binary.stat().st_size,record['face_count']*88)
            if len(a):
                self.assertTrue(np.isfinite(a['vertices']).all())
                owner=np.floor(a['vertices'].mean(axis=1)[:,[0,2]]/b.TILE_SIZE).astype(int)
                self.assertTrue(np.all(owner==np.array(record['cell_xz'])))
                self.assertTrue(np.all(a['material_index']<len(self.index['material_ids'])))
                self.assertTrue(np.all(a['source_kind']<4))
            for row in a:
                key=tuple(int(row[k]) for k in b.DTYPE.names[1:])
                self.assertNotIn(key,face_ids);face_ids.add(key)
            for key in ['render_skip_indices','collision_skip_indices']:
                self.assertEqual(len(tile[key]),len(set(tile[key])))
                self.assertTrue(all(0<=i<len(a) for i in tile[key]))
            for p in tile['common_instances']:
                self.assertNotIn(p['id'],native_ids);native_ids.add(p['id'])
            for p in tile['boxes']:
                self.assertNotIn(p['id'],box_ids);box_ids.add(p['id'])
            self.assertEqual(len(tile['contract_triangles']),len(tile['contract_face_refs']))
            for key in tile['contract_face_refs']:
                self.assertNotIn(tuple(key),contract_faces);contract_faces.add(tuple(key))
            counts['terrain_faces']+=len(a)
        self.assertEqual(counts['terrain_faces'],self.index['counts']['terrain_faces'])
        self.assertEqual(len(native_ids),self.index['counts']['native_instances'])
        self.assertEqual(len(box_ids),self.index['counts']['boxes'])
        self.assertEqual(len(contract_faces),self.index['counts']['contract_faces'])

    def test_market_boundary_and_spawn_interest_covered(self):
        routes=[[[98.41505784216918,4,48.75638652919374],[97.36957813563573,4,78.20197532570691],[87.00464271333841,4,94.67581530557659]],
                [[-68.574043186,8.1118629655,-132.45476887],[-79.290019247,12,-140.16241813]],
                [[418.061128,4,-.7431916],[435.355625,4,-6.1191]],
                [[-392.254945,21,-227.515824],[-407.961464,21,-236.532766]]]
        self.assertNotEqual(b.owner_of([routes[0][0]]*3),b.owner_of([routes[0][-1]]*3))
        for points in routes:
            for p in points:
                for ident in b.cells_for_bounds([p[0]-112,p[2]-112,p[0]+112,p[2]+112]):
                    self.assertIn(ident,self.index['tiles'])
                    self.assertTrue(self.index['tiles'][ident]['dependency_owner_tiles'])

    def test_bridge_exact_closed_source_poses_and_visual_chains(self):
        bridge=b.read(b.resolve(self.index['bridge_mechanism']))
        expected={p['id']:p for p in b.static_bridge_placements(bridge)}
        actual={}
        for record in self.index['tiles'].values():
            for p in b.read(b.ROOT/record['instances_path'])['common_instances']:
                if p.get('source_bridge_state'):actual[p['id']]=p
        self.assertEqual(actual,expected)
        self.assertEqual(sum(p['collision_enabled'] for p in actual.values()),len(bridge['states']['ROAD_OPEN']['movable_placements']))
        self.assertTrue(any(not p['collision_enabled'] for p in actual.values()))
        self.assertEqual(self.index['bridge_runtime_state'],'ROAD_OPEN')
        self.assertFalse(self.index['bridge_motion_enabled'])


if __name__=='__main__':unittest.main(verbosity=2)
