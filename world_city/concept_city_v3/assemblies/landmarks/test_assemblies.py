"""Source, cache and assembly integration contract checks; no GUI/full city build."""
from __future__ import annotations
import copy,itertools,json,unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[4];sys.path.insert(0,str(ROOT))
from voxel_character.common import core,coordinate_planes
from world_city.concept_city_v3.assemblies.landmarks.author import HERE,ref,placement,write,CANDIDATE_CAP,OUTPUT_CAP,source_bounds
from world_city.concept_city_v3.assemblies.landmarks.resolve_placements import resolve


def read(path):return json.loads(path.read_text())


class AssemblyTests(unittest.TestCase):
    def test_standard_source_and_rigid_only(self):
        manifest=read(HERE/'assemblies.json')
        self.assertEqual(len(manifest['source_masters']),5)
        self.assertEqual(len(manifest['assemblies']),7)
        for name,r in manifest['source_masters'].items():
            self.assertEqual(ref(r['path'])['sha256'],r['sha256'])
            source=read(ROOT/r['path']);resolved,_=coordinate_planes.resolve_master(source,{'pitch':.5})
            core.validate_master(resolved,.5)
            self.assertFalse(source['provenance']['new_engine'])
            self.assertFalse(source['provenance']['new_mesher'])
            for inst in source['instances']:core.transform(inst.get('transform'))
            self.assertEqual(source_bounds(source),source['extensions']['local_bounds_m'])

    def test_all_final_cache_hashes_and_caps(self):
        report=read(HERE/'evidence/compile_report.json')
        self.assertEqual(report['status'],'pass')
        self.assertEqual(len(report['requests']),9)
        self.assertEqual(ref(report['author']['path'])['sha256'],report['author']['sha256'])
        for row in report['requests']:
            self.assertTrue(row['valid'])
            self.assertLessEqual(row['candidate_cells'],CANDIDATE_CAP)
            self.assertLessEqual(row['output_cells'],OUTPUT_CAP)
            self.assertEqual(ref(row['render']['path'])['sha256'],row['render']['sha256'])
            source=read(HERE/'masters'/f"{row['id']}.json")
            self.assertEqual(core.digest(source),row['master_hash'])
            self.assertEqual(read(ROOT/row['render']['path'])['payload_hash'],row['payload_hash'])
            self.assertTrue(all(c['pass'] for c in row['constraints']))

    def test_reservations_and_main_square(self):
        manifest=read(HERE/'assemblies.json')
        for a in manifest['assemblies']:
            source=read(HERE/'masters'/f"{a['assembly_source']}.json");ext=source['extensions']
            b=ext['local_bounds_m'];p=a['world_translation_m'];r=ext['reservation_world_xz_m']
            # Port module has three rigid repeats; its source reservation is local in X.
            shift=p[0] if a['assembly_source']=='port_cluster' else 0
            for x in (b['min'][0],b['max'][0]):
                self.assertGreaterEqual(x+p[0],r[0]+shift-1e-7);self.assertLessEqual(x+p[0],r[2]+shift+1e-7)
            for z in (b['min'][2],b['max'][2]):
                self.assertGreaterEqual(z+p[2],r[1]-1e-7);self.assertLessEqual(z+p[2],r[3]+1e-7)
        civic=read(HERE/'masters/civic_grain.json')['extensions']
        self.assertLessEqual(civic['local_bounds_m']['max'][2]+40,-10)
        port=read(HERE/'masters/port_cluster.json')['extensions']['local_bounds_m']
        for center in (-180,0,180):self.assertFalse(center+port['min'][0] < 120 < center+port['max'][0])

    def test_fine_source_floor_ownership_and_access(self):
        manifest=read(HERE/'assemblies.json');compiled={}
        for kind in manifest['fine_cache_kinds']:
            source=read(HERE/'masters'/f'fine_{kind}.json')
            compiled[kind]=coordinate_planes.compile_master(source,{'pitch':.2},max_candidate_cells=120000,max_output_cells=40000)
            self.assertTrue(compiled[kind]['valid'])
        cloister=read(HERE/'masters/fine_pointed_arch_cloister_bay.json')
        self.assertNotIn('paving',[c['id'] for c in cloister['components']])
        crane=read(HERE/'masters/fine_timber_harbor_crane.json')
        self.assertFalse(any(op['id']=='stone_pad' for c in crane['components'] for op in c['operations']))
        for name in manifest['source_masters']:
            ext=read(HERE/'masters'/f'{name}.json')['extensions']
            for detail in ext['fine_details']:
                if detail['datum']=='river_water':continue  # resolved separately at water datum
                compiled_detail=compiled[detail['cache_key']];t=placement(detail['position_local_m'],detail['yaw_degrees'])
                for row in compiled_detail['cells']:
                    p=core.apply(t,[(row[j]+.5)*.2 for j in range(3)])
                    for c in ext['access_reservations']:
                        b=c['clearance_box_local_m']
                        self.assertFalse(all(b['min'][j] < p[j] < b['max'][j] for j in range(3)),(name,detail['id'],c['id'],p))

    def test_flying_buttress_host_contact_geometry(self):
        ext=read(HERE/'masters/cathedral.json')['extensions']
        flies=[s for s in ext['source_assemblies'] if s['key'].startswith('fly_')]
        self.assertEqual(len(flies),4)
        for fly in flies:
            p=core.apply(fly['placement'],[-6,20.4,0])
            self.assertAlmostEqual(abs(p[0]),32*.235)
            self.assertLess(p[1],58*.47)
            self.assertGreater(p[1],58*.32)
            self.assertEqual(fly['placed_bounds_m']['min'][1],0)

    def test_terrain_and_bed_support_water_datums(self):
        result=resolve();self.assertTrue(result['support_pass'])
        self.assertEqual(len(result['dock_pile_bed_checks']),12)
        self.assertEqual(len(result['quay_footing_bed_checks']),9)
        self.assertEqual(len(result['boat_waterline_checks']),3)
        self.assertEqual([round(x['waterline_y_m'],3) for x in result['boat_waterline_checks']],[.672,-.048,-.768])
        for b in result['boat_waterline_checks']:
            self.assertEqual(b['quay_y_m'],2.2)
            self.assertNotEqual(b['waterline_y_m'],b['quay_y_m'])
        write(HERE/'resolved_placements.json',result)

    def test_final_proxy_replacement_ids(self):
        manifest=read(HERE/'assemblies.json');plan=read(ROOT/'world_city/concept_city_v3/source/plan.json')
        ids={b['id'] for b in plan['buildings']}
        replaced=[]
        for a in manifest['assemblies']:
            for key in a['replaces_source_building_ids']:self.assertIn(key,ids);replaced.append(key)
        self.assertEqual(set(replaced),{'B_CASTLE_KEEP','B_CATHEDRAL','B_MONASTERY','B_TOWN_HALL','B_GRAIN_HALL'})
        self.assertEqual(len(replaced),5)

    def test_small_independent_repeat(self):
        source=read(HERE/'masters/fine_timber_harbor_crane.json')
        a=coordinate_planes.compile_master(copy.deepcopy(source),{'pitch':.2})
        b=coordinate_planes.compile_master(copy.deepcopy(source),{'pitch':.2})
        self.assertTrue(a['valid'] and b['valid']);self.assertEqual(a['payload_hash'],b['payload_hash'])
        write(HERE/'evidence/fine_repeat.json',{'source_master_hash':core.digest(source),
               'first_payload_hash':a['payload_hash'],'second_payload_hash':b['payload_hash'],
               'same':True,'independent_direct_compile':True,'copied_output':False})


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AssemblyTests))
    write(HERE/'evidence/test_report.json',{'status':'pass' if result.wasSuccessful() else 'fail','tests_run':result.testsRun,
          'failures':len(result.failures),'errors':len(result.errors),
          'test_source':ref('world_city/concept_city_v3/assemblies/landmarks/test_assemblies.py'),
          'scope':'Source/cache integrity, reserved footprints, static/fine access, source support/head datums and small deterministic repeat. No GUI or full city compile.',
          'visual_review':'not_run','runtime_motion':'not_run','whole_city_integration':'not_applied'})
    sys.exit(0 if result.wasSuccessful() else 1)
