"""Source integrity and real common-occupancy checks for the r2 terrain adapter."""
import json
import math
import unittest
from world_city.runtime_city.topography import author as a, integrate as i


class SourceIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.plan=i.build_source_plan()

    def test_only_affected_ground_and_source_owners_replaced(self):
        source=json.loads(i.R1_INFRA.read_text());by_id={p["id"]:p for p in source["placements"]}
        replacements=self.plan["replace_r1_placement_ids"]
        self.assertEqual(len(replacements),len(set(replacements)))
        self.assertTrue(all(by_id[x]["category"] in {"terrain","road","plaza","road_join_draw_only"} for x in replacements))
        field=a.GradeField(self.plan["regions"])
        for chunk in self.plan["chunks"]:
            self.assertTrue(i.affected(a._rect(chunk["bounds_xz_m"]),field) or chunk["boundary_transition_only"])
            self.assertLessEqual(chunk["bounds_xz_m"][2]-chunk["bounds_xz_m"][0],32.)
        self.assertTrue(all(o["material"] in infrastructure_materials() for o in self.plan["owners"]))

    def test_all_removed_source_owners_have_complete_replacement(self):
        for owner in self.plan["owners"]:
            area=abs(a._area(owner["polygon_xz_m"]))
            covered=sum(abs(a._area(q)) for c in self.plan["chunks"] if c["medium_surface"] and (q:=i.clipped(owner["polygon_xz_m"],c["bounds_xz_m"])))
            self.assertAlmostEqual(area,covered,places=6)

    def test_active_fine_budget_and_empty_building_sample(self):
        budget=self.plan["budgets"]
        self.assertEqual(budget["fine_active_area_m2"],1024.)
        self.assertEqual(budget["fine_patch_count"],64)
        self.assertFalse(budget["whole_city_fine_fill"])
        self.assertEqual(sum(c["fine_sample"] for c in self.plan["chunks"]),1)
        for p in self.plan["building_footing_contracts"]:
            self.assertFalse(i.clipped(p["body_footprint_xz_m"],i.FINE_BOUNDS))

    def test_entrance_floor_and_foundation_contract(self):
        for p in self.plan["building_footing_contracts"]:
            self.assertAlmostEqual(p["position_m"][1]+p["entrance_local_y_m"],p["entrance_position_m"][1])
            self.assertLessEqual(p["foundation"]["bottom_y_m"],p["foundation"]["cut_top_y_m"]-1.)
            self.assertTrue(p["integration_exceptions"])
            self.assertFalse(p["retaining_treatment"]["scope"].startswith("outside"))


class CompiledIntegrationTests(unittest.TestCase):
    def test_single_composite_road_shoulder_and_source_bounds(self):
        field=a.default_field();bounds=[-560.,-240.,-558.,-238.]
        owner=i._owner("test_road","road",[[-560,-240],[-559,-240],[-559,-238],[-560,-238]])
        master=i.make_ground_master(bounds,[owner],field,pitch=.1,depth=.4)
        compiled,render=a.compile_sample(master,.1)
        validation=i.validate_compiled_layer(compiled,master,field)
        self.assertTrue(validation["source_height_upper_bound_pass"])
        self.assertEqual(compiled["candidate_cells"],i.candidate_budget(master,.1))
        tops={};materials={}
        for x,y,z,_,_,material,_ in compiled["cells"]:
            if (x,z) not in tops or y>tops[x,z]:tops[x,z]=y;materials[x,z]=material
        self.assertEqual(len(tops),400)
        for (x,z),y in tops.items():
            self.assertEqual(materials[x,z],"stone" if (x+.5)*.1<-559 else "grass")
            for key in [(x+1,z),(x,z+1)]:
                if key in tops:self.assertLessEqual(abs(y-tops[key]),1)
        self.assertGreater(render["quad_count"],0)

    def test_adjacent_fine_exports_are_same_as_single_source(self):
        field=a.default_field();allbounds=[-560,-240,-556,-238]
        def compile_(bounds):
            m=i.make_ground_master(bounds,[],field,pitch=.1,depth=.4)
            c,_=a.compile_sample(m,.1)
            return {tuple(row[:3]) for row in c["cells"]}
        left=compile_([-560,-240,-558,-238]);right=compile_([-558,-240,-556,-238])
        self.assertFalse(left&right)
        self.assertEqual(left|right,compile_(allbounds))

    def test_foundation_cut_is_source_geometry(self):
        field=a.default_field();bounds=[-560.,-240.,-556.,-236.]
        body=a._rect([-559.,-239.,-557.,-237.])
        p={"id":"fixture","body_footprint_xz_m":body,"foundation":{"cut_top_y_m":15.}}
        master=i.make_ground_master(bounds,[],field,foundations=[p],bottom=13.)
        compiled,_=a.compile_sample(master,.5)
        for x,y,z,*_ in compiled["cells"]:
            if -559<(x+.5)*.5<-557 and -239<(z+.5)*.5<-237:self.assertLess((y+.5)*.5,15.)


    def test_all_retaining_door_apertures_are_actual_source_cuts(self):
        field=a.default_field();bounds=[-560.,-240.,-556.,-236.]
        floor=field.height(-559,-236);base=floor-.5
        doors=[{"position_m":[x,floor,-236],"yaw_rad":0.} for x in [-559.,-557.]]
        projection={"id":"two_doors","body_footprint_xz_m":a._rect(bounds),
                    "position_m":[-558,base,-238],"entrance_position_m":doors[0]["position_m"],
                    "yaw_rad":0.,"all_entrance_contracts":doors}
        master=i.make_retaining_master(projection,bounds,field)
        self.assertIsNotNone(master);self.assertEqual(len(master["assembly_cuts"]),2)
        compiled,_=a.compile_sample(master,.5)
        for x,y,z,*_ in compiled["cells"]:
            xx,yy,zz=(x+.5)*.5,(y+.5)*.5,(z+.5)*.5
            for entry in doors:
                self.assertFalse(abs(xx-entry["position_m"][0])<.9 and abs(zz+236)<1.5 and floor-.1<yy<floor+2.5)


class FinalResourceTests(unittest.TestCase):
    def test_final_manifest_integrity_when_available(self):
        path=i.DEFAULT_OUT/"layer_manifest.json"
        if not path.exists():self.skipTest("full resources are not compiled")
        m=json.loads(path.read_text())
        if m["status"]!="compiled_structural_only":self.skipTest("full resources are not compiled")
        self.assertEqual(i.sha(i.ROOT/m["source_plan_path"]),m["source_plan_sha256"])
        for asset in m["assets"].values():
            self.assertTrue(asset["validation"]["common_valid"])
            self.assertTrue(asset["validation"]["nonempty"])
            self.assertTrue(asset["validation"]["bounded_source_columns"])
            self.assertTrue(asset["validation"]["source_height_upper_bound_pass"])
            self.assertLessEqual(asset["candidate_cells"],2000000)
            self.assertEqual(i.sha(i.ROOT/asset["render_path"]),asset["render_sha256"])
        for p in m["placements"]:
            self.assertEqual(p["position_m"],[0,0,0]);self.assertEqual(p["render_offset_y_m"],0)
            self.assertEqual(p["collision_enabled"],p["category"]=="fine_walk_surface")
        for projection in m["building_footing_contracts"]:
            self.assertTrue(projection["foundation_source_cut_applied"])
            self.assertTrue(projection["compiled_resources"]["foundation_asset_keys"])
            for key in projection["compiled_resources"]["retaining_asset_keys"]:
                master=json.loads((i.ROOT/m["assets"][key]["master_path"]).read_text())
                self.assertEqual(len(master["assembly_cuts"]),len(projection["all_entrance_contracts"]))
        self.assertEqual(m["tested_fine_region"]["validation"]["status"],"passed")


def infrastructure_materials():
    from world_city.runtime_city.infrastructure.author import PALETTE
    return PALETTE

if __name__=="__main__":unittest.main()
