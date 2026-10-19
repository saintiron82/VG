"""Small source-geometry tests; no GUI or whole-city fine-grid compilation."""
import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from world_city.runtime_city.infrastructure.author import (
    BRIEF, build_infrastructure, make_master, _dot, _sub, _unit, _ribbon,
    _segment_convex_interval, _signed_area, _point_inside, _lerp,
)
from voxel_character.common import coordinate_planes, render_data


class InfrastructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=json.loads(BRIEF.read_text())
        cls.data=build_infrastructure(cls.plan)

    def test_six_openings_cover_all_ten_source_crossings(self):
        d=self.data
        self.assertTrue(d['checks']['source_wall_report_matches'])
        self.assertEqual(d['checks']['designated_openings'],6)
        self.assertEqual(d['checks']['wall_crossings'],10)
        self.assertEqual(d['walls']['unexplained_gaps'],[])
        openings={o['id']:o for o in d['walls']['openings']}
        for c in d['walls']['crossings']:
            lo,hi=openings[c['opening_id']]['interval_m']
            a,b=c['required_clearance_interval_m']
            self.assertLessEqual(lo,a+1e-6)
            self.assertGreaterEqual(hi,b-1e-6)

    def test_wall_exact_partition_no_extra_gaps(self):
        wall=self.plan['wall_outline_xz_m']
        for wi,(a,b) in enumerate(zip(wall,wall[1:]+wall[:1])):
            intervals=[(s['interval_m'],'solid') for s in self.data['walls']['segments'] if s['wall_edge']==wi]
            intervals += [(o['interval_m'],'opening') for o in self.data['walls']['openings'] if o['wall_edge']==wi]
            cursor=0
            for (lo,hi),kind in sorted(intervals):
                self.assertAlmostEqual(lo,cursor,places=7)
                self.assertGreater(hi,lo)
                cursor=hi
            self.assertAlmostEqual(cursor,math.dist(a,b),places=7)

    def test_road_true_ribbons_clear_solid_wall_full_thickness(self):
        """Test all three longitudinal lines through the actual 3 m wall slab."""
        roadmap={r['id']:r for r in self.data['routes']}
        for crossing in self.data['walls']['crossings']:
            road=roadmap[crossing['road_id']]
            for solid in self.data['walls']['segments']:
                if solid['wall_edge']!=crossing['wall_edge']:continue
                a,b=solid['a_xz_m'],solid['b_xz_m']
                unit,_=_unit(a,b)
                for offset in (-1.5,0,1.5):
                    shift=[-unit[1]*offset,unit[0]*offset]
                    aa=[a[0]+shift[0],a[1]+shift[1]]
                    bb=[b[0]+shift[0],b[1]+shift[1]]
                    self.assertIsNone(_segment_convex_interval(aa,bb,road['ribbon_polygon_xz_m']))

    def test_exact_roads_and_draw_only_pads(self):
        roads={r['id']:r for r in self.plan['roads']}
        nodes={n['id']:[n['position_m'][0],n['position_m'][2]] for n in self.plan['road_nodes']}
        for r in self.data['routes']:
            src=roads[r['id']]
            self.assertEqual(r['reserved_width_m'],src['width_m'])
            self.assertEqual(r['centerline_xz_m'],[nodes[src['from_node']],nodes[src['to_node']]])
            self.assertEqual(r['walk_surface_y_m'],0)
        self.assertEqual(len(self.data['routes']),855)
        for p in self.data['placements']:
            if p['category']=='road_join_draw_only':
                self.assertFalse(p['collision_enabled'])
                self.assertFalse(p['reservation_geometry'])
                self.assertTrue(p['draw_only_overlap_join'])
            if p['category']=='terrain':self.assertEqual(p['requested_pitch_m'],2)

    def test_flat_stage_and_river_are_honestly_declared(self):
        self.assertFalse(self.data['terrain']['candidate_52m_elevation_realized'])
        self.assertFalse(self.data['terrain']['whole_city_fine_fill'])
        self.assertEqual(self.data['river']['water_surface_y_m'],-2)
        poly=self.data['river']['outline_xz_m']
        for r in self.data['routes']:
            if r['kind']!='bridge':
                self.assertFalse(any(_point_inside(_lerp(*r['centerline_xz_m'],t),poly) for t in (0,.25,.5,.75,1)))
        self.assertEqual(len(self.data['docks']),3)
        self.assertTrue(all(d['quay_connection_xz_m'] for d in self.data['docks']))

    def test_paved_source_footprints_and_muted_city_ground(self):
        self.assertEqual({p['id'] for p in self.data['plazas']},
                         {'F_MARKET_OPEN','F_CASTLE_CLOSE','F_CATHEDRAL_CLOSE'})
        for p in self.data['placements']:
            if p['category']=='terrain':
                inside=_point_inside([p['position_m'][0],p['position_m'][2]],self.plan['wall_outline_xz_m'])
                self.assertEqual(p['spec']['material'],'earth' if inside else 'grass')
            if p['category']=='plaza':
                self.assertLessEqual(p['spec']['width_m'],32)
                self.assertLessEqual(p['spec']['length_m'],32)
                self.assertEqual(p['requested_pitch_m'],.25)
            if p['category']=='road':self.assertEqual(p['render_offset_y_m'],.025)

    def test_common_compiler_and_render_adapter_small_modules(self):
        for spec,pitch in [({'kind':'terrain_tile'},2),
                           ({'kind':'water_tile','width_m':8,'length_m':8},2),
                           ({'kind':'road_paver','width_m':3.5,'length_m':4},.25),
                           ({'kind':'curb','length_m':2},.25),
                           ({'kind':'surface_patch','width_m':4,'length_m':4},.25),
                           ({'kind':'wall_panel','width_m':4,'height_m':5},.5),
                           ({'kind':'battlement'},.25),
                           ({'kind':'bridge_deck','width_m':7,'length_m':4},.25),
                           ({'kind':'bridge_pier'},.5),
                           ({'kind':'dock','width_m':7,'length_m':4},.25)]:
            compiled=coordinate_planes.compile_master(make_master(spec),{'pitch':pitch},max_candidate_cells=100000,max_output_cells=50000)
            self.assertTrue(compiled['valid'])
            self.assertTrue(compiled['cells'])
            render=render_data.make_render_data(compiled)
            self.assertGreater(render['quad_count'],0)
            if spec['kind']=='terrain_tile':
                self.assertEqual(render['bounds']['min'],[-16,-2,-16])
                self.assertEqual(render['bounds']['max'],[16,0,16])
                self.assertEqual(render['cell_count'],256)
            if spec['kind']=='water_tile':self.assertEqual(render['bounds']['max'][1],-2)
            if spec['kind'] in ('road_paver','bridge_deck','dock'):self.assertEqual(render['bounds']['max'][1],0)

    def test_west_external_approach_full_width_clearance(self):
        from world_city.runtime_city.infrastructure.validate_gate_approach import validate
        report=validate(self.data)
        self.assertTrue(report['passed'])
        self.assertEqual(report['wall_panels_checked'],238)
        approach=self.data['external_gate_approaches'][0]
        self.assertEqual(approach['gate_instance_id'],'D09-B004')
        self.assertEqual(approach['route_id'],'RT_WEST_MARKET')
        self.assertEqual(approach['evidence'],'design_inference')
        self.assertEqual(approach['width_m'],6.5)
        self.assertEqual(len(self.data['routes']),855)
        self.assertAlmostEqual(report['approaches'][0]['minimum_main_opening_lateral_clearance_m'],1.75)

    def test_dock_access_uses_quay_projection_without_backtracking(self):
        docks={d['id']:d for d in self.data['docks']}
        sources={f['id']:f for f in self.plan['site_features'] if f['kind']=='loading_pier'}
        for dock in docks.values():
            self.assertEqual(dock['source_footprint_xz_m'],sources[dock['id']]['footprint_xz_m'])
            points=dock['accessible_polyline_xz_m']
            self.assertEqual(points[0],dock['quay_connection_xz_m'])
            self.assertEqual(points[-1],dock['authored_sampled_outward_edge_xz_m'])
            self.assertTrue(all(b[1]>=a[1]-1e-8 for a,b in zip(points,points[1:])))
        self.assertEqual(docks['F_PIER_0']['connection_adjustment']['trimmed_landward_length_m'],0)
        self.assertAlmostEqual(docks['F_PIER_1']['authored_centerline_xz_m'][0][1],457.70556589526177)
        self.assertAlmostEqual(docks['F_PIER_2']['authored_centerline_xz_m'][0][1],464.2063213399848)
        self.assertNotIn([-120,457],docks['F_PIER_2']['accessible_polyline_xz_m'])

    def test_dock_access_clears_all_runtime_building_envelopes(self):
        from world_city.runtime_city.infrastructure.validate_dock_access import validate
        report=validate(self.data)
        self.assertTrue(report['passed'])
        self.assertEqual(report['building_envelopes_checked'],1308)
        for dock in report['docks']:
            self.assertEqual(dock['outward_edge_metadata_error_m'],0)
            self.assertTrue(all(s['capsule_clearance_m']>0 for s in dock['segments']))
        pier2=next(d for d in report['docks'] if d['id']=='F_PIER_2')
        self.assertEqual(pier2['before_fix_nearest_envelope']['building_id'],'D05-B013')
        self.assertEqual(pier2['before_fix_nearest_envelope']['centerline_distance_m'],0)

    def test_all_sampled_shoreline_tiles_and_deck_shared_planes(self):
        from world_city.runtime_city.infrastructure.validate_sampled_seams import validate
        report=validate(self.data)
        self.assertTrue(report['passed'])
        self.assertEqual(report['shoreline']['tiles_checked'],218)
        self.assertEqual(report['shoreline']['missing_column_count'],0)
        self.assertEqual(report['shoreline']['overlap_column_count'],0)
        self.assertEqual(report['bridge']['piece_count'],9)
        self.assertEqual(report['bridge']['internal_deck_seam_count'],9)
        self.assertLess(report['bridge']['max_internal_shared_plane_error_m'],1e-7)

    def test_coarse_shoreline_masks_sample_without_overlap(self):
        # One representative shore chunk, including both source clip variants.
        shores=[p for p in self.data['placements'] if p['category']=='terrain' and p['spec'].get('river_polygons_xz_m')]
        p=shores[len(shores)//2]
        land=coordinate_planes.compile_master(make_master(p['spec']),{'pitch':2})
        water_spec={**p['spec'],'kind':'water_tile'}
        water=coordinate_planes.compile_master(make_master(water_spec),{'pitch':2})
        land_xz={(c[0],c[2]) for c in land['cells']}
        water_xz={(c[0],c[2]) for c in water['cells']}
        self.assertFalse(land_xz & water_xz)
        self.assertEqual(len(land_xz | water_xz),256)


if __name__=='__main__':unittest.main()
