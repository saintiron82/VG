"""Author landmark data; sampling and meshing belong to existing common modules.

All dimensions describe the TOTAL continuous envelope, not the nave/body alone.
There is one continuous source per specification and no resolution dispatch.
The geometry is an original, fictional medieval-inspired design inference.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

SUPPORTED_KINDS = (
    "castle_keep", "cathedral", "town_hall", "gatehouse", "wall_tower",
    "monastery", "church", "warehouse",
)

# These roles intentionally match common/assets/house/master.json.
PALETTE = {
    "stone": "9e9b88", "stone_light": "b7b19b", "stone_dark": "7e8075",
    "mortar": "666c63", "slate": "45676a", "slate_dark": "355157",
    "timber": "654631", "timber_dark": "493729", "glass": "314d55",
    "glass_light": "54716e", "iron": "394648", "door": "946b45",
}


def _box(lo, hi):
    return {"kind": "box", "min": list(lo), "max": list(hi)}


def _extrusion(poly, z0, z1):
    return {"kind": "extrusion", "polygon": [list(p) for p in poly],
            "z_min": z0, "z_max": z1}


class _Author:
    """Small source-data writer, deliberately not a compiler or mesher."""

    def __init__(self, spec):
        self.spec = spec
        self.w, self.d, self.h = (float(spec[k]) for k in
                                ("width_m", "depth_m", "height_m"))
        self.components = {}
        self.features = []
        self.portals = []
        self.empty_regions = []
        self.assembly_cuts = []

    def op(self, category, label, shape, material="stone", action="paint", transform=None):
        component = self.components.setdefault(category, {
            "id": category,
            "parts": [{"id": "solid", "pivot": [0, 0, 0],
                       "metadata": {"source_category": category, "dynamic": False}}],
            "operations": [],
        })
        operation = {"id": label, "part": "solid", "action": action, "shape": shape}
        if action == "paint":
            operation["material"] = material
        if transform is not None:
            operation["transform"] = transform
        component["operations"].append(operation)

    def box(self, category, label, lo, hi, material="stone"):
        if any(b - a <= 1e-8 for a, b in zip(lo, hi)):
            raise ValueError(f"degenerate authored box: {label}: {lo}, {hi}")
        self.op(category, label, _box(lo, hi), material)

    def shell(self, name, x0, x1, z0, z1, y0, y1, t=None, entrance=None):
        """Four thin walls, never a dense solid with an interior-volume cut."""
        t = min(t or .7, (x1-x0)*.23, (z1-z0)*.23)
        self.box("masonry", name+"_west", [x0,y0,z0], [x0+t,y1,z1])
        self.box("masonry", name+"_east", [x1-t,y0,z0], [x1,y1,z1])
        self.box("masonry", name+"_rear", [x0+t,y0,z0], [x1-t,y1,z0+t])
        self.box("masonry", name+"_front", [x0+t,y0,z1-t], [x1-t,y1,z1])
        if entrance:
            cx, width, clear_h = entrance
            # Cut only the wall thickness, not the whole building volume.
            self.op("masonry", name+"_door_opening",
                    _box([cx-width/2,y0,z1-t-.01], [cx+width/2,y0+clear_h,z1+.01]),
                    action="cut")
        return t

    def belt(self, name, x0, x1, z0, z1, y0, y1, t=.5):
        t = min(t, (x1-x0)*.23, (z1-z0)*.23)
        self.box("dressings", name+"_west", [x0,y0,z0], [x0+t,y1,z1], "stone_light")
        self.box("dressings", name+"_east", [x1-t,y0,z0], [x1,y1,z1], "stone_light")
        self.box("dressings", name+"_rear", [x0+t,y0,z0], [x1-t,y1,z0+t], "stone_light")
        self.box("dressings", name+"_front", [x0+t,y0,z1-t], [x1-t,y1,z1], "stone_light")

    def roof(self, name, x0, x1, z0, z1, eave, ridge, *, across_x=False):
        """Hollow gable roof using bounded slope strips and two thin gables.

        Strips are geometry partitions of one exact continuous roof, independent
        of requested voxel pitch. Their small boxes avoid huge empty candidates.
        """
        if across_x:
            # Author in a temporary local XY profile, then rotate its operations.
            local = _Author(self.spec)
            local.roof(name, z0, z1, -x1, -x0, eave, ridge)
            rotation = {"basis": [[0,0,-1],[0,1,0],[1,0,0]], "translation": [0,0,0]}
            for category, comp in local.components.items():
                for op in comp["operations"]:
                    self.op(category, op["id"], op["shape"], op.get("material", "stone"),
                            op["action"], rotation)
            return
        mid = (x0+x1)/2
        thickness = min(.6, (ridge-eave)*.25)
        for side, a, b in (("left", x0, mid), ("right", mid, x1)):
            count = max(1, math.ceil((b-a)/2))
            for i in range(count):
                xa, xb = a+(b-a)*i/count, a+(b-a)*(i+1)/count
                ya = ridge-(ridge-eave)*abs(xa-mid)/((x1-x0)/2)
                yb = ridge-(ridge-eave)*abs(xb-mid)/((x1-x0)/2)
                self.op("roof", f"{name}_{side}_{i}",
                        _extrusion([[xa,ya],[xb,yb],[xb,yb-thickness],[xa,ya-thickness]],z0,z1),
                        "slate")
        for end, za, zb in (("rear", z0, z0+.5), ("front", z1-.5, z1)):
            self.op("masonry", name+"_gable_"+end,
                    _extrusion([[x0,eave-thickness],[x1,eave-thickness],[mid,ridge-thickness]],za,zb),
                    "stone_dark")
        self.box("roof", name+"_ridge", [mid-.18,ridge-thickness,z0],
                 [mid+.18,ridge,z1], "slate_dark")

    def spire(self, name, cx, cz, radius, base, top):
        t = min(.55, radius*.25)
        shape = {"kind": "lathe", "profile": [[radius,base],[0,top],
                 [0,top-t],[max(0,radius-t),base]]}
        self.op("roof", name, shape, "slate_dark",
                transform={"translation": [cx,0,cz]})

    def battlements(self, name, x0, x1, z0, z1, top):
        rh = min(1.1, self.h*.06)
        t = min(.75, (x1-x0)*.16, (z1-z0)*.16)
        parapet = top-rh
        self.belt(name+"_parapet",x0,x1,z0,z1,parapet-rh*.7,parapet,t)
        for side,z in (("front", z1-t),("rear",z0)):
            count = max(2, round((x1-x0)/2))
            step = (x1-x0)/count
            for i in range(count):
                self.box("battlements",f"{name}_{side}_{i}",
                         [x0+i*step,parapet,z],[x0+i*step+step*.58,top,z+t],"stone_light")
        for side,x in (("west",x0),("east",x1-t)):
            count = max(2, round((z1-z0)/2))
            step = (z1-z0)/count
            for i in range(count):
                self.box("battlements",f"{name}_{side}_{i}",
                         [x,parapet,z0+i*step],[x+t,top,z0+i*step+step*.58],"stone_light")

    def tower(self, name, x0, x1, z0, z1, top, *, spire=False):
        body_top = top*.75 if spire else top-min(1.1,self.h*.06)
        self.shell(name,x0,x1,z0,z1,0,body_top)
        self.belt(name+"_base",x0,x1,z0,z1,0,min(.6,body_top*.1))
        self.belt(name+"_cornice",x0,x1,z0,z1,body_top-.6,body_top)
        self.box("masonry",name+"_top_deck",[x0,body_top-.65,z0],[x1,body_top-.15,z1],"stone_dark")
        if spire:
            self.spire(name+"_spire",(x0+x1)/2,(z0+z1)/2,
                       min(x1-x0,z1-z0)*.5,body_top,top)
        else:
            self.battlements(name,x0,x1,z0,z1,top)
        slit_w = min(.65,(x1-x0)*.18)
        slit_h = min(2.4,body_top*.18)
        self.window(name+"_slit",(x0+x1)/2,body_top*.56,z1,
                    slit_w,slit_h,"front",pointed=True)

    def window(self, name, horizontal, base, surface, width, height, side="front", pointed=True):
        """Dark inset pointed panels with restrained dressed-stone margins."""
        r = width/2
        shoulder = height*.72 if pointed else height
        poly = [[-r,base],[r,base],[r,base+shoulder]]
        if pointed:
            poly.append([0,base+height])
        poly.append([-r,base+shoulder])
        # The outer face stays within the supplied envelope; all depth is inward.
        if side == "front":
            tr = {"translation":[horizontal,0,surface]}
        elif side == "rear":
            tr = {"basis":[[-1,0,0],[0,1,0],[0,0,-1]],"translation":[horizontal,0,surface]}
        elif side == "east":
            tr = {"basis":[[0,0,1],[0,1,0],[-1,0,0]],"translation":[surface,0,horizontal]}
        else:
            tr = {"basis":[[0,0,-1],[0,1,0],[1,0,0]],"translation":[surface,0,horizontal]}
        self.op("windows",name+"_surround",_extrusion(poly,-.65,0),"stone_light",transform=tr)
        margin = min(.25,width*.18,height*.12)
        inner = [[x*(1-2*margin/width), y+margin if y==base else y-margin] for x,y in poly]
        self.op("windows",name+"_pane",_extrusion(inner,-.5,-.01),"glass",transform=tr)
        # A vertical mullion changes the reading from a dark arrow to tracery.
        if width >= 1.5:
            self.op("windows",name+"_mullion",_box([-.10,base+margin,-.50],
                    [.10,base+height-margin,-.01]),"stone_light",transform=tr)

    def portal(self, name, width, clear_h, z, *, depth=.9, through=False):
        self.portals.append({"id":name,"threshold_local_m":[0,0,z],
            "forward_into_asset":[0,0,-1],"clear_width_m":width,"clear_height_m":clear_h,
            "through_passage":through,"interior_status":"not_authored"})
        z0 = -self.d/2 if through else z-depth
        z1 = self.d/2 if through else z
        self.empty_regions.append({"id":name+"_clearance","kind":"empty_region",
            "selector":{},"shape":_box([-width/2,0,z0],[width/2,clear_h,z1])})

    def secondary_openings(self):
        for i, opening in enumerate(self.spec.get("secondary_openings", [])):
            name = f"secondary_opening_{i}"
            # All layers must be cut, including base dressings and window panels.
            # This is authored route-interface geometry, not a postcompile repair.
            self.assembly_cuts.append({"id":name,"selector":{},
                                     "shape":_box(opening["min"],opening["max"])})
            self.empty_regions.append({"id":name+"_clearance","kind":"empty_region",
                                       "selector":{},"shape":_box(opening["min"],opening["max"])})
        if self.spec.get("secondary_openings"):
            self.features.append("explicit_secondary_route_openings")

    def finish(self):
        root = Path(__file__).resolve().parents[3]
        sources = ["world_city/data/city_brief.v2.json",
                   "voxel_character/common/assets/house/master.json"]
        source_files = [{"path":p,"sha256":hashlib.sha256((root/p).read_bytes()).hexdigest()}
                        for p in sources]
        constraints = [{"id":"landmark_present","kind":"nonempty","selector":{}}]
        constraints.extend({"id":category+"_present","kind":"nonempty",
                            "selector":{"component":category}} for category in self.components)
        constraints.extend(self.empty_regions)
        return {
            "schema":"riverstone.voxel.master.v1", "id":self.spec["asset_id"], "revision":1,
            "axes":{"up":"+Y","front":"+Z","right":"+X"},"grid_origin":[0,0,0],
            "materials":dict(PALETTE),"components":list(self.components.values()),
            "instances":[{"id":name,"component":name} for name in self.components],
            "assembly_cuts":self.assembly_cuts,"constraints":constraints,
            "provenance":{"source_files":source_files,
                "author":"world_city/runtime_city/landmarks/author.py",
                "author_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                "evidence":"design_inference_not_historical_reconstruction",
                "observed_source":"Layout roles, total planning dimensions and common house material grammar.",
                "inferred":"All architectural silhouettes, bays, shell thicknesses, roofs, towers, openings and decorative proportions.",
                "source_of_geometry":"This continuous standard common master; compile independently at each requested pitch.",
                "new_engine":False},
            "extensions":{
                "landmark_kind":self.spec["kind"],
                "total_envelope_m":{"min":[-self.w/2,0,-self.d/2],"max":[self.w/2,self.h,self.d/2]},
                "dimensions_m":{"width":self.w,"depth":self.d,"height":self.h},
                "exterior_features":self.features,"entrances":self.portals,
                "secondary_openings":[{"min":list(o["min"]),"max":list(o["max"])}
                                      for o in self.spec.get("secondary_openings",[])],
                "secondary_opening_support":{
                    "rear_half_ground_shell_retained":(
                        self.spec["kind"] == "wall_tower" and
                        bool(self.spec.get("secondary_openings")) and
                        all(o["min"][2] >= 0 for o in self.spec.get("secondary_openings",[]))),
                    "status":"geometric_ground_support_only_not_structural_engineering",
                    "clearance_is_game_design_inference":True,
                },
                "scope":{"exterior":"authored","interior":"not_authored","physics":"not_authored",
                         "visual_review":"not_run","historical_reconstruction":False},
                "construction":"Thin shell walls, bounded roof slope strips, supported cornices; no dense building fill.",
                "sampling_policy":"Unmodified common coordinate_planes/core and render_data; no alternate LOD master or output-cell repair.",
            },
        }


def _castle(a):
    w,d,h=a.w,a.d,a.h
    tw=min(w*.18,d*.28)
    curtain=h*.42
    # Main curtain fronts enclose an OPEN central court; rear keep stays behind it.
    a.shell("curtain",-w/2,w/2,-d/2,d/2,0,curtain,t=.95,
            entrance=(0,min(8,w*.20),min(6,h*.23)))
    a.battlements("curtain",-w/2,w/2,-d/2,d/2,curtain+min(1.1,h*.05))
    for sx in (-1,1):
        for sz in (-1,1):
            x0=-w/2 if sx<0 else w/2-tw
            z0=-d/2 if sz<0 else d/2-tw
            a.tower(f"corner_{sx}_{sz}",x0,x0+tw,z0,z0+tw,h if sz<0 else h*.84)
    a.shell("rear_keep",-w*.29,w*.29,-d*.45,-d*.06,0,h*.70,t=.95,
            entrance=(0,min(4,w*.12),min(5,h*.20)))
    a.roof("keep",-w*.30,w*.30,-d*.46,-d*.05,h*.70,h*.89,across_x=True)
    for i in range(5):
        x=-w*.23+i*w*.115
        a.window(f"keep_upper_{i}",x,h*.49,-d*.06,min(1.7,w*.035),h*.12)
    width,clear=min(8,w*.20),min(6,h*.23)
    a.portal("castle_entry",width,clear,d/2)
    a.features += ["open_courtyard","four_projecting_crenellated_towers","rear_keep_great_hall",
                   "battlement_curtain","large_front_entrance"]


def _cathedral(a, small=False):
    w,d,h=a.w,a.d,a.h
    nave_top=h*(.50 if small else .47)
    a.shell("nave",-w*.235,w*.235,-d/2,d*.45,0,nave_top,
            entrance=(0,min(5,w*.26),min(6,h*.24)))
    a.roof("nave",-w*.25,w*.25,-d/2,d*.46,nave_top,h*.67)
    for side in (-1,1):
        x0,x1=(-w*.43,-w*.235) if side<0 else (w*.235,w*.43)
        a.shell(f"aisle_{side}",x0,x1,-d*.43,d*.28,0,h*.24,t=.6)
        a.roof(f"aisle_{side}",x0,x1,-d*.44,d*.29,h*.24,h*.32)
    # Transept tips touch the total width; it remains below the nave ridge.
    a.shell("transept",-w/2,w/2,-d*.20,-d*.02,0,h*.34,t=.7)
    a.roof("transept",-w/2,w/2,-d*.21,-d*.01,h*.34,h*.47,across_x=True)
    bays=max(3,min(9,round(d/8)))
    for i in range(bays):
        z=-d*.37+i*(d*.57/(bays-1))
        for side in (-1,1):
            x0,x1=(-w/2,-w*.40) if side<0 else (w*.40,w/2)
            # Stepped buttresses visibly rise from the ground to aisle shoulder.
            a.box("buttresses",f"buttress_{side}_{i}_lower",[x0,0,z-.45],[x1,h*.25,z+.45],"stone_light")
            xa,xb=(-w*.46,-w*.40) if side<0 else (w*.40,w*.46)
            a.box("buttresses",f"buttress_{side}_{i}_upper",[xa,h*.25,z-.35],[xb,h*.34,z+.35],"stone_light")
            a.window(f"clerestory_{side}_{i}",z,h*.32,side*w*.235,
                     min(2,d*.035),h*.12,"east" if side>0 else "west")
            a.window(f"aisle_window_{side}_{i}",z,h*.075,side*w*.43,
                     min(2,d*.035),h*.14,"east" if side>0 else "west")
    if small:
        a.tower("bell_tower",-w*.17,w*.17,d*.23,d*.50,h,spire=True)
        # Functional game clearance, not a reconstructed historical dimension.
        # Keep the silhouette while cutting the low chapel variants sufficiently
        # high for a future 1.8 m character capsule and a modest headroom margin.
        entry_h=min(h*.5,max(2.2,min(3,h*.20)))
        entry_w=min(w*.30,max(1.4,w*.24))
        a.op("masonry","church_tower_entry",_box([-entry_w/2,0,d*.23-.01],
             [entry_w/2,entry_h,d*.50+.01]),action="cut")
        a.op("dressings","church_tower_base_entry",_box([-entry_w/2,0,d*.23-.01],
             [entry_w/2,entry_h,d*.50+.01]),action="cut")
        a.portal("church_entry",entry_w,entry_h,d/2)
        a.portals[-1]["clearance_basis"]="functional_game_design_inference_not_historical_value"
    else:
        for side in (-1,1):
            x0,x1=(-w*.46,-w*.24) if side<0 else (w*.24,w*.46)
            a.tower(f"front_tower_{side}",x0,x1,d*.27,d/2,h,spire=True)
            a.window(f"tower_lancet_{side}",(x0+x1)/2,h*.46,d/2,(x1-x0)*.40,h*.16)
        a.window("west_great_window",0,h*.25,d*.45,w*.26,h*.18)
        a.portal("cathedral_entry",min(5,w*.26),min(6,h*.24),d*.45)
    a.features += ["long_nave","lower_side_aisles","cross_transept","stepped_buttress_bays",
                   "pointed_clerestory_windows","single_bell_spire" if small else "paired_front_spires"]


def _town_hall(a):
    w,d,h=a.w,a.d,a.h
    arcade_h=h*.22
    a.shell("hall",-w/2,w/2,-d*.48,d*.32,0,h*.49,
            entrance=(0,min(3,w*.15),min(3,h*.23)))
    a.roof("great_roof",-w/2,w/2,-d/2,d/2,h*.49,h*.79,across_x=True)
    bays=max(3,min(9,round(w/5)))
    if bays % 2 == 0:
        bays += 1  # The central arcade bay, rather than a pier, faces the portal.
    step=w/bays
    for i in range(bays+1):
        cx=-w/2+i*step
        xa,xb=max(-w/2,cx-.35),min(w/2,cx+.35)
        a.box("arcade",f"pier_{i}",[xa,0,d*.32],[xb,arcade_h,d/2],"stone_light")
    for i in range(bays):
        x0=-w/2+i*step; x1=x0+step; mid=(x0+x1)/2
        # Polygon spandrels make actual peaked openings, not painted arch icons.
        a.op("arcade",f"spandrel_{i}",_extrusion([
            [x0,arcade_h*.65],[mid,arcade_h],[x1,arcade_h*.65],
            [x1,h*.49],[x0,h*.49]],d*.43,d/2),"stone")
        a.window(f"civic_window_{i}",mid,h*.30,d/2,min(1.65,step*.45),h*.12,pointed=False)
    a.tower("civic_tower",-w*.085,w*.085,-d*.15,d*.13,h,spire=True)
    # Civic tower sits away from the street-facing threshold and arcade.
    a.portal("town_hall_entry",min(3,w*.15),min(3,h*.23),d*.32)
    a.features += ["open_street_arcade","stone_piers_and_peaked_spandrels","broad_steep_cross_roof",
                   "civic_tower","regular_upper_civic_windows"]


def _gatehouse(a):
    w,d,h=a.w,a.d,a.h
    half=5.0
    spring=max(5.5,h*.32)
    for side in (-1,1):
        x0,x1=(-w/2,-half) if side<0 else (half,w/2)
        a.tower(f"gate_tower_{side}",x0,x1,-d/2,d/2,h)
    # All center geometry starts above the guaranteed rectangular clearance.
    a.shell("guard_gallery",-half,half,-d*.38,d*.38,spring,h*.72,t=.65)
    a.box("masonry","gallery_floor",[-half,spring,-d*.38],[half,spring+.55,d*.38],"stone_dark")
    a.box("masonry","gallery_roof",[-half,h*.70,-d*.38],[half,h*.75,d*.38],"stone_dark")
    a.battlements("gallery",-half,half,-d*.38,d*.38,h*.81)
    for i,x in enumerate((-3,0,3)):
        a.window(f"gallery_lancet_{i}",x,spring+.9,d*.38,.75,max(.8,h*.10))
    a.portal("gate_through_passage",10.0,5.0,d/2,through=True)
    a.features += ["paired_projecting_towers","unobstructed_10m_by_5m_through_passage",
                   "raised_guard_gallery","crenellated_gallery_and_towers"]


def _wall_tower(a):
    a.tower("wall_tower",-a.w/2,a.w/2,-a.d/2,a.d/2,a.h)
    for side in (-1,1):
        a.window(f"side_arrow_slit_{side}",0,a.h*.43,side*a.w/2,
                 min(.65,a.d*.12),a.h*.18,"east" if side>0 else "west")
    front_arch = next((o for o in a.spec.get("secondary_openings",[])
                       if o["min"][0] <= 0 < o["max"][0] and o["min"][1] == 0
                       and math.isclose(o["max"][2],a.d/2)),None)
    if front_arch:
        width=2*min(-front_arch["min"][0],front_arch["max"][0])
        height=front_arch["max"][1]
        a.portal("wall_tower_open_arch",width,height,a.d/2,
                 depth=a.d/2-front_arch["min"][2])
        a.portals[-1].update({"geometry_state":"open_exterior_arch","door_state":"no_leaf",
            "interior_transition_available":False,"wallwalk_access":"pending_vertical_connection",
            "clearance_status":"authored_exterior_road_clearance_not_interior_access"})
        a.features.append("open_ground_arch_for_reserved_lane")
    else:
        width=min(2.2,a.w*.35); height=min(3.0,a.h*.30)
        # An exterior closed leaf is visible at .5 m without moving outside the
        # envelope. It is not a cut, portal traversal, hinge rig or interior.
        a.box("doors","closed_ground_door",[-width/2,0,a.d/2-.6],
              [width/2,height,a.d/2],"door")
        a.portals.append({"id":"wall_tower_closed_door","threshold_local_m":[0,0,a.d/2],
            "forward_into_asset":[0,0,-1],"door_width_m":width,"door_height_m":height,
            "clear_width_m":width,"clear_height_m":height,
            "through_passage":False,"geometry_state":"closed_exterior_door","door_state":"closed",
            "clearance_status":"door_aperture_dimensions_only_blocked_by_closed_leaf",
            "interior_status":"not_authored","interior_transition_available":False,
            "wallwalk_access":"pending_vertical_connection"})
        a.features.append("visible_closed_ground_door")
    a.features += ["projecting_stone_tower","crenellated_parapet","arrow_slit_facades"]


def _monastery(a):
    w,d,h=a.w,a.d,a.h
    wing=min(w*.20,d*.22)
    for name,x0,x1,z0,z1 in (
        ("west_wing",-w/2,-w/2+wing,-d/2,d/2),
        ("east_wing",w/2-wing,w/2,-d/2,d/2),
        ("rear_wing",-w/2+wing,w/2-wing,-d/2,-d/2+wing),
    ):
        a.shell(name,x0,x1,z0,z1,0,h*.58,t=.65)
        a.roof(name,x0,x1,z0,z1,h*.58,h*.82,across_x=name=="rear_wing")
    a.shell("chapel",-w*.19,w*.19,-d*.38,-d*.02,0,h*.64,t=.7,
            entrance=(0,min(2.5,w*.17),min(3,h*.25)))
    a.roof("chapel",-w*.19,w*.19,-d*.38,-d*.02,h*.64,h)
    a.portal("cloister_entry",min(5,w*.26),min(4,h*.4),d/2,depth=wing)
    a.features += ["open_front_cloister_court","three_roofed_wings","tall_rear_chapel"]


def _warehouse(a):
    w,d,h=a.w,a.d,a.h
    door_w=min(4,w*.30); door_h=min(4,h*.37)
    a.shell("warehouse",-w/2,w/2,-d/2,d/2,0,h*.65,t=.6,
            entrance=(0,door_w,door_h))
    a.roof("warehouse",-w/2,w/2,-d/2,d/2,h*.65,h)
    for side in (-1,1):
        for i in range(4):
            z=-d*.35+i*d*.23
            a.window(f"store_window_{side}_{i}",z,h*.42,side*w/2,
                     min(1.5,d*.09),h*.12,"east" if side>0 else "west",pointed=False)
    for x in (-w*.35,w*.35):
        post=_box([x-.13,0,d/2-.35],[x+.13,h*.65,d/2])
        # Existing generic preservation rule retains off-grid narrow posts.
        # The depth is anchored to the facade, so preservation grows inward.
        post["minimum_cells"]=[1,0,1]
        post["anchors"]=["center","min","max"]
        a.op("timber",f"front_post_{x:g}",post,"timber")
    a.portal("loading_entry",door_w,door_h,d/2)
    a.features += ["large_loading_portal","tall_gable_store_roof","small_high_store_windows"]


def make_master(spec):
    """Return JSON-serializable common master for a total metric envelope.

    Required: asset_id, kind, width_m, depth_m, height_m. Building placement,
    frontage rotation, ground elevation, chunking and sampling remain callers'
    responsibilities. Gatehouse's 10 m by 5 m corridor cannot be scaled down.
    Optional gatehouse/wall_tower secondary_openings are [{"min":[x,y,z],"max":[x,y,z]}]
    inside the total envelope. They cut every layer and have empty constraints.
    """
    if not isinstance(spec, dict):
        raise ValueError("landmark spec must be a dictionary")
    if not isinstance(spec.get("asset_id"), str) or not spec["asset_id"].strip():
        raise ValueError("asset_id must be nonempty")
    if spec.get("kind") not in SUPPORTED_KINDS:
        raise ValueError(f"unsupported landmark kind: {spec.get('kind')!r}")
    for key in ("width_m","depth_m","height_m"):
        if type(spec.get(key)) not in (int,float) or not math.isfinite(spec[key]) or spec[key] < 4:
            raise ValueError(f"{key} must be a finite number >= 4 m")
    if spec["kind"] == "gatehouse" and (spec["width_m"] < 14 or spec["height_m"] < 10):
        raise ValueError("gatehouse requires width >= 14 m and height >= 10 m for a 10 m x 5 m passage")
    secondary = spec.get("secondary_openings", [])
    if not isinstance(secondary,list) or (secondary and spec["kind"] not in ("gatehouse","wall_tower")):
        raise ValueError("secondary_openings must be a list and are supported for gatehouse or wall_tower only")
    envelope_lo = [-spec["width_m"]/2,0,-spec["depth_m"]/2]
    envelope_hi = [spec["width_m"]/2,spec["height_m"],spec["depth_m"]/2]
    for opening in secondary:
        if not isinstance(opening,dict) or set(opening) != {"min","max"}:
            raise ValueError("secondary opening requires only min and max XYZ bounds")
        if any(not isinstance(opening[k],list) or len(opening[k]) != 3 or
               any(type(v) not in (int,float) or not math.isfinite(v) for v in opening[k])
               for k in ("min","max")):
            raise ValueError("secondary opening bounds must be finite XYZ lists")
        if any(not a <= lo < hi <= b for a,lo,hi,b in
               zip(envelope_lo,opening["min"],opening["max"],envelope_hi)):
            raise ValueError("secondary opening must be increasing and inside the total envelope")
    author = _Author(spec)
    {"castle_keep":_castle,"cathedral":_cathedral,"town_hall":_town_hall,
     "gatehouse":_gatehouse,"wall_tower":_wall_tower,"monastery":_monastery,
     "church":lambda a:_cathedral(a,small=True),"warehouse":_warehouse}[spec["kind"]](author)
    author.secondary_openings()
    return author.finish()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("spec",type=Path,help="JSON object with required make_master fields")
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    master=make_master(json.loads(args.spec.read_text()))
    with args.output.open("x",encoding="utf-8") as stream:
        json.dump(master,stream,ensure_ascii=False,sort_keys=True,separators=(",",":"))
        stream.write("\n")
    print(json.dumps({"id":master["id"],"kind":master["extensions"]["landmark_kind"],
                      "components":len(master["components"]),"output":str(args.output)}))


if __name__ == "__main__":
    main()
