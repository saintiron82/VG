"""Small deterministic source/CSG checks; no full-city compile or physics claim."""
import copy
import hashlib
import json
import math
import random
import unittest
from pathlib import Path

from world_city.runtime_city.topography import author as a
from voxel_character.common import coordinate_planes,core


def cells(result): return {tuple(row[:3]) for row in result["cells"]}


class GradeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.brief=json.loads(a.BRIEF.read_text());cls.scene=json.loads(a.SCENE.read_text());cls.history=json.loads(a.HISTORY.read_text())
        cls.field=a.field_from_brief(cls.brief)
        cls.plan=a.build_grade_plan(cls.brief,cls.scene,cls.history)

    def test_determinism_and_input_immutability(self):
        before=a._hash([self.brief,self.scene,self.history])
        result=a.build_grade_plan(self.brief,self.scene,self.history)
        self.assertEqual(a._hash(result),a._hash(self.plan))
        self.assertEqual(before,a._hash([self.brief,self.scene,self.history]))

    def test_source_footprints_roads_courts_preserved(self):
        source={b["id"]:b for b in self.scene["instances"]}
        self.assertEqual(len(self.plan["buildings"]),1308)
        self.assertEqual(len(self.plan["roads"]),870)
        self.assertEqual(self.plan["preserved_reservations"]["courtyards"],1003)
        for b in self.plan["buildings"]:
            i=source[b["id"]]
            self.assertEqual(b["source_footprint_xz_m"],i["source_footprint_xz_m"])
            self.assertEqual(b["position_m"][::2],i["position_m"][::2])
            self.assertEqual(b["yaw_rad"],i["yaw_rad"])
            self.assertEqual(b["entrance_position_m"][::2],i["entrance"]["position_m"][::2])

    def test_plateau_courts_and_lower_city(self):
        for r in self.field.regions:
            for p in r["plateau_polygon_xz_m"]:
                self.assertAlmostEqual(self.field.height(*p),r["height_m"],places=9)
        for p in [(0,0),(-20,330),(200,660),(0,-390),(-300,20),(250,-10)]:
            self.assertEqual(self.field.height(*p),0.)

    def test_global_grade_proof_and_random_pairs(self):
        for r in self.field.regions:
            for p in r["planes"]: self.assertLessEqual(math.hypot(*p[:2]),.12+1e-12)
        rng=random.Random(145002)
        for _ in range(2000):
            p=[rng.uniform(-800,800),rng.uniform(-700,760)]
            q=[p[0]+rng.uniform(-25,25),p[1]+rng.uniform(-25,25)]
            self.assertLessEqual(abs(self.field.height(*p)-self.field.height(*q)),.12*math.dist(p,q)+1e-9)

    def test_exact_profile_interpolation(self):
        rng=random.Random(17)
        for _ in range(60):
            p=[rng.uniform(-800,800),rng.uniform(-700,100)]
            q=[rng.uniform(-800,800),rng.uniform(-700,100)]
            profile=self.field.profile(p,q)
            for v,w in zip(profile["points_m"],profile["points_m"][1:]):
                for t in (.13,.5,.87):
                    x,z=v[0]+(w[0]-v[0])*t,v[2]+(w[2]-v[2])*t
                    y=v[1]+(w[1]-v[1])*t
                    self.assertAlmostEqual(y,self.field.height(x,z),places=8)
            self.assertLessEqual(profile["max_grade"],a.GRADE_LIMIT)

    def test_all_active_roads_and_entrances_within_bound(self):
        for r in self.plan["roads"]:
            if r["projection"] is not None: self.assertLessEqual(r["projection"]["max_grade"],a.GRADE_LIMIT)
        for b in self.plan["buildings"]:
            self.assertLessEqual(b["approach"]["max_grade"],a.GRADE_LIMIT)
            self.assertEqual(b["approach"]["points_m"][-1],b["entrance_position_m"])
            self.assertAlmostEqual(b["position_m"][1]+b["entrance_local_y_m"],b["entrance_position_m"][1])
            self.assertLessEqual(b["foundation"]["bottom_y_m"],b["foundation"]["terrain_min_y_m"]-2.5+1e-8)

    def test_road_junctions_share_identical_height(self):
        used={}
        for r in self.plan["roads"]:
            if r["projection"] is None: continue
            for node,p in zip(r["source_node_ids"],[r["projection"]["points_m"][0],r["projection"]["points_m"][-1]]):
                if node in used: self.assertLess(math.dist(used[node],p),1e-8)
                used[node]=p

    def test_landmark_ingress_and_flat_castle_court(self):
        for r in self.plan["ingress"].values(): self.assertTrue(r["centerline_continuous"])
        self.assertEqual(self.plan["ingress"]["RT_CASTLE_CLIMB"]["end_m"][1],24.)
        self.assertEqual(self.plan["ingress"]["RT_CATHEDRAL_APPROACH"]["end_m"][1],14.)
        self.assertEqual(self.plan["ingress"]["RT_CASTLE_COURT"]["max_grade"],0.)

    def test_gate_ground_stays_flat_but_not_collision_certified(self):
        gates=[b for b in self.plan["buildings"] if b["passage_status"].startswith("needs")]
        self.assertEqual(len(gates),4)
        for b in gates:
            self.assertEqual(b["foundation"]["terrain_max_y_m"],0.)
            self.assertEqual(b["foundation"]["terrain_min_y_m"],0.)

    def test_facet_domains_cover_area_and_match_field(self):
        for bounds in [[-576,-256,-544,-224],[224,-256,256,-224],[-32,-32,0,0],[-736,-384,-704,-352]]:
            facets=self.field.facets(a._rect(bounds))
            self.assertAlmostEqual(sum(abs(a._area(f["polygon_xz_m"])) for f in facets),1024.,places=6)
            for f in facets:
                p=[sum(v[i] for v in f["polygon_xz_m"])/len(f["polygon_xz_m"]) for i in (0,1)]
                self.assertAlmostEqual(a._eval(f["plane"],*p),self.field.height(*p),places=8)

    def test_authoring_rejects_invalid_input(self):
        with self.assertRaises(ValueError):a.height_at(math.nan,0)
        with self.assertRaises(ValueError):a.make_terrain_master([0,0,64,32])
        with self.assertRaises(ValueError):a.make_surface_master([0,0,9,8])
        with self.assertRaises(ValueError):a.GradeField([{"id":"bad","height_m":20,"grade":.5,"plateau_polygon_xz_m":[[0,0],[4,0],[4,4],[0,4]]}])
        with self.assertRaises(ValueError):a.GradeField([self.field.regions[0],self.field.regions[0]])


class CommonGeometryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.field=a.default_field()

    def test_macro_compiles_via_unchanged_common(self):
        master=a.make_terrain_master([-512,-224,-504,-216],self.field)
        compiled,render=a.compile_sample(master,2.)
        self.assertTrue(compiled["valid"]);self.assertGreater(render["quad_count"],0)
        self.assertEqual(compiled["grid_origin"],[0,0,0])
        self.assertFalse(master["metadata"]["walk_collision_allowed"])

    def test_fine_surface_matches_analytic_slab_and_rise_limit(self):
        master=a.make_surface_master([-512,-224,-510,-222],field=self.field)
        compiled,render=a.compile_sample(master,.1)
        tops={}
        for x,y,z,*_ in compiled["cells"]:
            h=self.field.height((x+.5)*.1,(z+.5)*.1)
            self.assertLessEqual(h-a.SURFACE_DEPTH,(y+.5)*.1+1e-8)
            self.assertLessEqual((y+.5)*.1,h+1e-8)
            tops[(x,z)]=max(tops.get((x,z),-10000),(y+1)*.1)
        self.assertEqual(len(tops),400)
        self.assertGreater(render["quad_count"],0)
        for (x,z),h in tops.items():
            for key in [(x+1,z),(x,z+1)]:
                if key in tops:self.assertLessEqual(abs(h-tops[key]),.1+1e-8)
        with self.assertRaises(ValueError):a.compile_sample(master,2.)

    def test_adjacent_macro_chunks_equal_single_compile(self):
        left=a.make_terrain_master([-576,-256,-544,-224],self.field)
        # Smaller two test patches around the shared x=-544 plane, not city fill.
        left=a.make_terrain_master([-548,-232,-544,-224],self.field)
        right=a.make_terrain_master([-544,-232,-540,-224],self.field)
        full=a.make_terrain_master([-548,-232,-540,-224],self.field)
        lc,_=a.compile_sample(left,2.);rc,_=a.compile_sample(right,2.);fc,_=a.compile_sample(full,2.)
        self.assertFalse(cells(lc)&cells(rc))
        self.assertEqual(cells(lc)|cells(rc),cells(fc))
        lp={p["id"]:p for p in left["coordinate_planes"]};rp={p["id"]:p for p in right["coordinate_planes"]}
        key="boundary_0_"+float(-544).hex()
        self.assertEqual(lp[key],rp[key])
        for i in range(81):
            z=-232+i*.1
            self.assertAlmostEqual(self.field.height(-544-1e-7,z),self.field.height(-544+1e-7,z),places=6)

    def test_adjacent_fine_patches_equal_single_compile(self):
        left=a.make_surface_master([-512,-224,-511,-223],field=self.field)
        right=a.make_surface_master([-511,-224,-510,-223],field=self.field)
        full=a.make_surface_master([-512,-224,-510,-223],field=self.field)
        lc,_=a.compile_sample(left,.1);rc,_=a.compile_sample(right,.1);fc,_=a.compile_sample(full,.1)
        self.assertFalse(cells(lc)&cells(rc))
        self.assertEqual(cells(lc)|cells(rc),cells(fc))

    def test_recess_keeps_macro_below_visible_fine_top(self):
        macro=a.make_terrain_master([-512,-224,-504,-216],self.field,surface_recess=True)
        compiled,_=a.compile_sample(macro,2.)
        for x,y,z,*_ in compiled["cells"]:
            # Include horizontal slope variation across a complete macro cell.
            h=min(self.field.height(xx,zz) for xx in [x*2,(x+1)*2] for zz in [z*2,(z+1)*2])
            self.assertLess((y+1)*2,h-.5)
        self.assertEqual(macro["metadata"]["surface_recess_m"],2.)

    def test_source_surface_exclusion_is_real_geometry(self):
        bounds=[0,0,2,2];excluded=[[[.5,.5],[1.5,.5],[1.5,1.5],[.5,1.5]]]
        master=a.make_surface_master(bounds,exclude_polygons=excluded)
        compiled,_=a.compile_sample(master,.1)
        for x,y,z,*_ in compiled["cells"]:
            self.assertFalse(.5<(x+.5)*.1<1.5 and .5<(z+.5)*.1<1.5)

    def test_foundation_bounded_source_volume_and_excavation(self):
        scene=json.loads(a.SCENE.read_text());i=next(i for i in scene["instances"] if i["id"]=="D02-B018")
        p=a.project_instance(i,scene["asset_specs"][i["asset_key"]],self.field)
        x,z=p["position_m"][0],p["position_m"][2];bounds=[x-2,z-2,x+2,z+2]
        master=a.make_foundation_master(p,bounds)
        compiled,_=a.compile_sample(master,.5)
        self.assertGreater(len(compiled["cells"]),0)
        self.assertLessEqual(compiled["candidate_cells"],2000000)
        for _,y,_,*_ in compiled["cells"]:self.assertLess((y+.5)*.5,p["foundation"]["top_y_m"]+1e-8)
        terrain=a.make_terrain_master(bounds,self.field,surface_recess=True,foundation_projections=[p])
        tc,_=a.compile_sample(terrain,2.)
        ceiling=p["foundation"]["cut_top_y_m"]
        self.assertEqual(terrain["metadata"]["foundation_excavation_ceiling_y_m"],ceiling)
        for _,y,_,*_ in tc["cells"]:self.assertLess((y+1)*2,ceiling+1.000001)
        with self.assertRaises(ValueError):a.make_terrain_master(bounds,foundation_projections=[p])

    def test_large_foundation_requires_bounded_chunk(self):
        scene=json.loads(a.SCENE.read_text());i=next(i for i in scene["instances"] if i["id"]=="D01-B001")
        p=a.project_instance(i,scene["asset_specs"][i["asset_key"]],self.field)
        with self.assertRaises(ValueError):a.make_foundation_master(p)
        master=a.make_foundation_master(p,[-448,-352,-432,-336])
        compiled,_=a.compile_sample(master,.5)
        self.assertGreater(len(compiled["cells"]),0)

    def test_river_cut_is_preserved(self):
        master=a.make_terrain_master([-16,528,16,560])
        compiled,_=a.compile_sample(master,2.)
        self.assertEqual(compiled["cells"],[])
        self.assertEqual(master["metadata"]["river_surface_y_m"],-2.)

    def test_multifacet_macro_has_no_internal_cracks(self):
        field=a.GradeField([{"id":"fixture","height_m":1.,"grade":.1,
                             "plateau_polygon_xz_m":[[-1,-1],[1,-1],[1,1],[-1,1]]}])
        master=a.make_terrain_master([-4,-4,4,4],field,river_polygons=[])
        compiled,_=a.compile_sample(master,.5)
        expected=set()
        for x in range(-8,8):
            for z in range(-8,8):
                for y in range(-8,2):
                    if (y+.5)*.5<field.height((x+.5)*.5,(z+.5)*.5)-1e-9:
                        expected.add((x,y,z))
        self.assertEqual(cells(compiled),expected)

    def test_buried_support_fills_deep_excavation(self):
        master=a.make_interface_support_master([-512,-224,-508,-220],10.,self.field)
        compiled,_=a.compile_sample(master,.5)
        self.assertFalse(master["metadata"]["walk_collision_allowed"])
        tops={}
        for x,y,z,*_ in compiled["cells"]:
            h=self.field.height((x+.5)*.5,(z+.5)*.5)
            self.assertLessEqual((y+.5)*.5,h+a.BURIED_TOP_OFFSET+1e-8)
            tops[(x,z)]=max(tops.get((x,z),-1000),(y+1)*.5)
        for (x,z),top in tops.items():
            self.assertGreater(top,self.field.height((x+.5)*.5,(z+.5)*.5)-1.5)

    def test_sparse_recess_does_not_replace_unwalked_field(self):
        master=a.make_terrain_master([0,0,8,8],surface_recess=True,
                    recess_polygons=[[[2,2],[6,2],[6,6],[2,6]]])
        compiled,_=a.compile_sample(master,2.)
        tops={}
        for x,y,z,*_ in compiled["cells"]:tops[x,z]=max(tops.get((x,z),-100),(y+1)*2)
        for (x,z),top in tops.items():
            self.assertEqual(top,-2. if 2<(x+.5)*2<6 and 2<(z+.5)*2<6 else 0.)

    def test_road_and_owned_shoulder_have_no_sampled_cliff(self):
        bounds=[-512,-224,-510,-222]
        road=[[-512,-224],[-511,-224],[-511,-222],[-512,-222]]
        full=a.make_surface_master(bounds)
        road_master=a.make_surface_master(bounds,[road])
        shoulder=a.make_surface_master(bounds,material="earth",exclude_polygons=[road])
        fc,_=a.compile_sample(full,.1);rc,_=a.compile_sample(road_master,.1);sc,_=a.compile_sample(shoulder,.1)
        self.assertFalse(cells(rc)&cells(sc));self.assertEqual(cells(rc)|cells(sc),cells(fc))
        tops={}
        for x,y,z,*_ in fc["cells"]:tops[x,z]=max(tops.get((x,z),-1000),(y+1)*.1)
        for z in range(-2240,-2220):self.assertLessEqual(abs(tops[-5111,z]-tops[-5110,z]),.1+1e-8)

    def test_thin_cap_buffer_and_coarse_support_overlap_below_top(self):
        bounds=[-512,-224,-510,-222]
        fine,_=a.compile_sample(a.make_surface_master(bounds),.1)
        buffer,_=a.compile_sample(a.make_walk_buffer_master(bounds),.2)
        buried,_=a.compile_sample(a.make_interface_support_master(bounds,18.),.5)
        def spans(c,pitch):
            d={}
            for x,y,z,*_ in c["cells"]:
                low,high=d.get((x,z),(math.inf,-math.inf))
                d[x,z]=(min(low,y*pitch),max(high,(y+1)*pitch))
            return d
        fs,bs,cs=spans(fine,.1),spans(buffer,.2),spans(buried,.5)
        for (x,z),(low,high) in fs.items():
            xx,zz=(x+.5)*.1,(z+.5)*.1
            blo,bhi=bs[math.floor(xx/.2),math.floor(zz/.2)]
            clo,chi=cs[math.floor(xx/.5),math.floor(zz/.5)]
            self.assertGreaterEqual(bhi,low-1e-8)
            self.assertLess(bhi,high-1e-8)
            self.assertGreaterEqual(chi,blo-1e-8)

    def test_budget_is_not_silently_relaxed(self):
        master=a.make_surface_master([-512,-224,-510,-222])
        with self.assertRaises(core.BudgetExceeded):a.compile_sample(master,.1,max_candidate_cells=10)


if __name__=="__main__": unittest.main()
