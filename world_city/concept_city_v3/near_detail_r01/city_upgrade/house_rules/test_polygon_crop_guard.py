"""Preserve an actual hip trim exact-edge failure as a regression fixture."""
import unittest
import layered_compile as l


class PolygonCropPredicateContracts(unittest.TestCase):
    def test_real_hip_trim_exact_edge_keeps_original_polygon(self):
        f=l.a.load(l.HERE/'fixtures/hip_trim_float_boundary.json')
        shape=l.a.core.prepare_shape(f['operation']['shape'],.05)
        t=l.a.core.compose(l.a.core.transform(f['instance']['transform']),l.a.core.transform(f['operation']['transform']))
        original=l.crop_prepared_shape(shape,t,f['world_lo'],f['world_hi'])
        stats={'operations_checked':0,'grid_samples_checked':0,'original_polygons_retained':0,'examples':[]}
        safe=l.crop_prepared_shape(shape,t,f['world_lo'],f['world_hi'],{'origin':f['grid_origin'],'pitch':.05},stats)
        point=[f['grid_origin'][j]+(f['failing_cell'][j]+.5)*.05 for j in range(3)]
        local=l.a.core.inverse(t,point)
        self.assertTrue(l.a.core.contains(shape,local))
        self.assertFalse(l.a.core.contains(original,local))
        self.assertTrue(l.a.core.contains(safe,local))
        self.assertEqual(safe['polygon'],shape['polygon'])
        self.assertEqual(stats['original_polygons_retained'],1)
        self.assertGreater(stats['grid_samples_checked'],0)

    def test_no_change_when_polygon_predicate_matches(self):
        shape={'kind':'extrusion','polygon':[[0,0],[1,0],[1,1],[0,1]],'z_min':0,'z_max':1}
        stats={'operations_checked':0,'grid_samples_checked':0,'original_polygons_retained':0,'examples':[]}
        result=l.crop_prepared_shape(shape,l.a.core.transform(),[.2,.2,.2],[.8,.8,.8],{'origin':[0,0,0],'pitch':.05},stats)
        self.assertEqual(stats['original_polygons_retained'],0)
        self.assertEqual(result['z_min'],.2);self.assertEqual(result['z_max'],.8)


if __name__=='__main__':unittest.main()
