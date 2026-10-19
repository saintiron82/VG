"""Independent negative fixtures for r2 provenance, compiled geometry and doors."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location('revision2_under_test', Path(__file__).with_name('revision2.py'))
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)


def box_render(bounds):
    a, b = bounds['min'], bounds['max']
    return {'bounds': copy.deepcopy(bounds), 'groups': [{'material': 'stone', 'quads': [
        [[a[0], a[1], a[2]], [b[0], a[1], a[2]], [b[0], b[1], a[2]], [a[0], b[1], a[2]]],
        [[a[0], a[1], b[2]], [b[0], a[1], b[2]], [b[0], b[1], b[2]], [a[0], b[1], b[2]]]]}]}


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bounds = {'min': [-1, 0, -1], 'max': [1, 3, 1]}
        doors = [[-0.5, 0, 1], [0.5, 0, 1]]
        meta = {'assembly_class': 'poor_row', 'row_units': 2, 'entrance': {'all_positions': doors, 'position': doors[0], 'front': '+Z'}}
        asset = self.resource('row', self.bounds, meta)
        footprint = [[-2, -2], [2, -2], [2, 2], [-2, 2]]
        source = {'id': 'B1', 'district_id': 'D01', 'functional_role': 'house', 'implementation_tier': 'exterior_only',
                  'footprint_xz_m': footprint, 'road_access': {'road_id': 'R1', 'connection_xz_m': [0, 4]}}
        self.plan = {'building_plans': [source], 'road_nodes': [{'id': 'N1', 'position_m': [-10, None, 4]}, {'id': 'N2', 'position_m': [10, None, 4]}],
                     'roads': [{'id': 'R1', 'from_node': 'N1', 'to_node': 'N2', 'width_m': 2, 'kind': 'cart_street'}],
                     'plots': [{'id': 'P1', 'courtyard_xz_m': [[10, 0], [12, 0], [12, 2], [10, 2]]}]}
        instance = {'id': 'B1', 'source_footprint_id': 'B1', 'district_id': 'D01', 'asset_key': 'row', 'position_m': [0, 0, 0], 'yaw_rad': 0,
                    'source_footprint_xz_m': copy.deepcopy(footprint), 'local_bounds': copy.deepcopy(self.bounds),
                    'implementation_tier': 'exterior_only', 'preserved_record': False, 'assembly_class': 'poor_row',
                    'all_entrances_local_m': copy.deepcopy(doors),
                    'entrance': {'local_position_m': doors[0], 'position_m': doors[0], 'facade_inset_m': 0,
                                 'road_id': 'R1', 'road_connection_m': [0, 0, 4]}}
        self.scene = {'assets': {'row': {'coarse': asset}}, 'instances': [instance],
                      'roads': copy.deepcopy(self.plan['roads']), 'road_nodes': copy.deepcopy(self.plan['road_nodes'])}
        self.fabric = {'assets': {}, 'placements': [], 'properties': [], 'building_override_specs': [],
                       'source_building_supersessions': [], 'access_reservations': [], 'repurposed_courtyard_plot_ids': []}

    def tearDown(self):
        self.temp.cleanup()

    def resource(self, name, bounds, meta=None):
        render_path = name + '.render.json'
        (self.root / render_path).write_text(json.dumps(box_render(bounds)))
        resource = {'render_path': render_path, 'bounds': copy.deepcopy(bounds)}
        if meta is not None:
            resource['master_path'] = name + '.master.json'
            (self.root / resource['master_path']).write_text(json.dumps({'metadata': meta}))
            resource['author_metadata'] = copy.deepcopy(meta)
        return resource

    def audit(self):
        return r.audit_revision2(self.scene, self.fabric, self.plan, self.root)

    def names(self, result):
        return {x['check'] for x in result['failures']}

    def add_fabric(self, fid='F1', position=None, bounds=None, category='property_boundary', blocking=True):
        position = position or [10, 0, 10]
        bounds = bounds or {'min': [-0.5, 0, -0.5], 'max': [0.5, 2, 0.5]}
        self.fabric['assets'][fid] = self.resource(fid, bounds)
        guard = {'min': [bounds['min'][0] - 0.18, 0, bounds['min'][2] - 0.18],
                 'max': [bounds['max'][0] + 0.18, 1, bounds['max'][2] + 0.18]}
        placement = {'id': fid, 'asset_key': fid, 'local_bounds': copy.deepcopy(bounds), 'position_m': position, 'yaw_rad': 0,
                     'category': category, 'collision_enabled': blocking,
                     'conservative_sample_envelope_xz_m': r.g.transformed_aabb_xz_m(guard, position, 0)}
        self.fabric['placements'].append(placement)
        return placement

    def add_repurpose(self, public=True):
        self.fabric['repurposed_courtyard_plot_ids'] = ['P1']
        self.fabric['properties'].append({'id': 'PROP1', 'source_plot_ids': ['P1'], 'land_use': {'working_court_m2': 4}})
        self.fabric['access_reservations'].append({'id': 'LINK1', 'owner_id': 'PROP1', 'kind': 'court_to_public_road',
                                                 'polyline_xz_m': [[11, 1], [9, 4 if public else 8]], 'width_m': 1.4})

    def test_bent_access_lane_includes_outside_turn_clearance(self):
        polygons = r._ribbons([[0, 0], [2, 0], [2, 2]], 1)
        obstacle = [[2.28, -0.32], [2.32, -0.32], [2.32, -0.28], [2.28, -0.28]]
        self.assertEqual(len(polygons), 3)
        self.assertFalse(any(r._overlap(p, obstacle) for p in polygons[:2]))
        self.assertTrue(r._overlap(polygons[2], obstacle))

    def test_valid_every_door_is_audited(self):
        result = self.audit()
        self.assertTrue(result['passed'], result['failures'])
        self.assertEqual(result['counts']['authored_poor_row_doors'], 2)
        self.assertEqual(result['counts']['rows_with_clear_all_door_route'], 1)

    def test_retained_footprint_cannot_silently_change(self):
        self.scene['instances'][0]['source_footprint_xz_m'][0][0] -= 0.1
        self.assertIn('retained_original_source_footprint', self.names(self.audit()))

    def test_missing_source_is_not_complete(self):
        self.scene['instances'] = []
        self.assertIn('all_original_ids_accounted_for', self.names(self.audit()))

    def test_authorized_replacement_keeps_original_and_new_provenance(self):
        source = self.plan['building_plans'][0]
        new = [[-3, -3], [3, -3], [3, 3], [-3, 3]]
        self.scene['instances'][0].update(source_footprint_xz_m=new, original_v2_footprint_xz_m=source['footprint_xz_m'], property_id='PROP')
        self.fabric['building_override_specs'] = [{'id': 'B1', 'property_id': 'PROP', 'source_building_ids': ['B1'],
            'provenance': {'source_footprint_xz_m': source['footprint_xz_m']}, 'footprint_xz_m': new, 'position_m': [0, 0, 0], 'yaw_rad': 0}]
        self.fabric['source_building_supersessions'] = [{'source_building_id': 'B1', 'replacement_id': 'B1', 'property_id': 'PROP', 'source_footprint_xz_m': source['footprint_xz_m']}]
        self.fabric['properties'] = [{'id': 'PROP', 'source_building_ids': ['B1'], 'land_use': {'roofed_m2': 4},
                                      'footprint_xz_m': [[-4, -4], [4, -4], [4, 4], [-4, 4]]}]
        result = self.audit()
        self.assertTrue(result['passed'], result['failures'])
        self.assertEqual(result['counts']['explicit_replacements'], 1)
        self.scene['instances'][0]['original_v2_footprint_xz_m'] = new
        self.assertIn('replacement_original_provenance', self.names(self.audit()))

    def test_repurposed_court_needs_explicit_landuse_and_access(self):
        self.fabric['repurposed_courtyard_plot_ids'] = ['P1']
        result = self.audit()
        self.assertIn('repurposed_court_has_landuse_and_public_access', self.names(result))
        self.assertEqual(result['counts']['remaining_reserved_courtyards'], 1)

    def test_repurposed_court_route_must_reach_real_public_road(self):
        self.add_repurpose(public=False)
        self.assertIn('repurposed_court_has_landuse_and_public_access', self.names(self.audit()))

    def test_documented_repurpose_does_not_trigger_old_void_rule(self):
        self.add_repurpose()
        result = self.audit()
        self.assertTrue(result['passed'], result['failures'])
        self.assertEqual(result['counts']['remaining_reserved_courtyards'], 0)

    def test_internal_court_crossing_cannot_pass_through_building_envelope(self):
        self.fabric['access_reservations'].append({'id': 'COURT_CROSS', 'kind': 'cross_courtyard', 'owner_id': 'PROP',
                                                 'polyline_xz_m': [[-1, 1.1], [1, 1.1]], 'width_m': 1.4})
        result = self.audit()
        self.assertIn('reserved_court_access_routes_clear_of_buildings', self.names(result))
        self.assertEqual(result['counts']['reserved_court_access_building_conflicts'], 1)

    def test_clear_but_disconnected_court_crossing_is_not_public_access(self):
        self.add_repurpose()
        self.fabric['access_reservations'].append({'id': 'ISOLATED_CROSS', 'kind': 'cross_courtyard', 'owner_id': 'PROP1',
                                                 'polyline_xz_m': [[20, 20], [22, 20]], 'width_m': 1.4})
        result = self.audit()
        self.assertIn('internal_court_reservation_connected_to_public_link', self.names(result))

    def test_compiled_vertices_override_false_catalog_bounds(self):
        self.scene['assets']['row']['coarse']['bounds']['max'][0] = 0.5
        self.assertIn('compiled_vertex_bounds_match_catalog', self.names(self.audit()))

    def test_compiled_vertices_override_false_render_bounds(self):
        path = self.root / 'row.render.json'
        render = json.loads(path.read_text())
        render['bounds']['max'][0] = 0.5
        path.write_text(json.dumps(render))
        self.assertIn('compiled_vertex_bounds_match_render', self.names(self.audit()))

    def test_missing_compiled_geometry_fails(self):
        (self.root / 'row.render.json').unlink()
        self.assertIn('compiled_render_readable', self.names(self.audit()))

    def test_missing_secondary_door_metadata_fails(self):
        self.scene['instances'][0]['all_entrances_local_m'].pop()
        self.assertIn('poor_row_all_doors_retained_in_instance', self.names(self.audit()))

    def test_center_door_is_not_substituted_for_authored_primary(self):
        self.scene['instances'][0]['entrance'].update(local_position_m=[0, 0, 1], position_m=[0, 0, 1])
        self.assertIn('poor_row_primary_entrance_matches_authored', self.names(self.audit()))

    def test_fabric_blocking_only_second_door_fails_whole_row(self):
        self.add_fabric(position=[0.5, 0, 1.2], bounds={'min': [-0.05, 0, -0.05], 'max': [0.05, 1, 0.05]})
        result = self.audit()
        self.assertIn('all_poor_row_doors_reach_clear_shared_frontage_and_street', self.names(result))
        self.assertEqual(result['counts']['rows_with_blocked_route'], 1)

    def test_named_street_connection_cannot_be_invented(self):
        self.scene['instances'][0]['entrance']['road_connection_m'] = [0, 0, 9]
        self.assertIn('poor_row_named_public_street_target', self.names(self.audit()))

    def test_actual_fabric_bounds_cannot_intrude_road(self):
        self.add_fabric(position=[0, 0, 4])
        self.assertIn('fabric_respects_reserved_clearance', self.names(self.audit()))

    def test_actual_fabric_bounds_cannot_intrude_reserved_court(self):
        self.add_fabric(position=[11, 0, 1])
        self.assertIn('fabric_respects_reserved_clearance', self.names(self.audit()))

    def test_sampled_outset_is_recorded_when_guard_really_contains_it(self):
        placement = self.add_fabric(bounds={'min': [-0.75, 0, -1.25], 'max': [0.5, 1.25, 1.25]})
        placement['local_bounds'] = {'min': [-0.625, -0.5, -1.25], 'max': [0.625, 1.25, 1.25]}
        result = self.audit()
        self.assertTrue(result['passed'], result['failures'])
        self.assertEqual(result['counts']['explicit_sample_guard_outsets'], 1)

    def test_sample_guard_does_not_silently_ignore_meaningful_outset(self):
        placement = self.add_fabric(bounds={'min': [-0.75, 0, -1.25], 'max': [0.5, 1.25, 1.25]})
        placement['conservative_sample_envelope_xz_m'] = [[9.5, 8.75], [10.5, 8.75], [10.5, 11.25], [9.5, 11.25]]
        self.assertIn('fabric_sample_guard_encloses_compiled', self.names(self.audit()))

    def test_nonblocking_flag_cannot_hide_a_wall(self):
        self.add_fabric(blocking=False)
        self.assertIn('nonblocking_fabric_is_declared_flush_surface', self.names(self.audit()))

    def test_verified_flush_surface_underlay_is_reported_separately(self):
        self.add_fabric('WALL')
        self.add_fabric('FLOOR', bounds={'min': [-1, -0.5, -1], 'max': [1, 0.25, 1]}, category='flush_work_surface', blocking=False)
        result = self.audit()
        self.assertTrue(result['passed'], result['failures'])
        self.assertEqual(result['counts']['nonblocking_surface_underlays'], 1)

    def test_single_unit_row_still_checks_its_one_real_door(self):
        meta = {'assembly_class': 'poor_row', 'row_units': 1, 'entrance': {'all_positions': [[0, 0, 1]], 'position': [0, 0, 1]}}
        self.scene['assets']['row']['coarse'] = self.resource('row', self.bounds, meta)
        self.scene['instances'][0]['all_entrances_local_m'] = [[0, 0, 1]]
        self.scene['instances'][0]['entrance'].update(local_position_m=[0, 0, 1], position_m=[0, 0, 1])
        result = self.audit()
        self.assertTrue(result['passed'], result['failures'])
        self.assertEqual(result['counts']['authored_poor_row_doors'], 1)


if __name__ == '__main__':
    unittest.main()
