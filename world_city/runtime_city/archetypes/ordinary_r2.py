"""R2 livelihood-specific continuous building masters; r1 remains immutable.

All geometry is standard riverstone.voxel.master.v1 data. No renderer, sampler,
mesh scaling, texture noise or per-pitch source variants are introduced here.
"""
from __future__ import annotations
from collections.abc import Mapping
from copy import deepcopy
import hashlib
import math
from pathlib import Path

from .ordinary import (_Assembly, _box, _extrusion, _source, _window, _door,
                       _wall, ROTATIONS, STYLES, SCHEMA)

ASSEMBLY_CLASSES = ("regular_house", "older_stone_manor", "merchant_palazzo",
                    "timber_courtyard_house", "stable", "servant_lodge", "poor_row")
ROOF_FORMS = ("gable", "steep_gable", "hip", "shed", "flat", "twin_gable_z", "twin_gable_x")
ERA_MAP = {"early":"early", "rebuilt":"rebuilt", "late":"late",
           "crossing_fort":"early", "religious_precinct":"early", "chartered_market":"early",
           "river_trade":"rebuilt", "market_rebuilding":"rebuilt", "outer_infill":"late"}


def _number(spec, key, default):
    value = spec.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value):
        raise ValueError(f"{key} must be a finite number")
    return float(value)


def describe_spec(spec: Mapping) -> dict:
    """Resolve dimensions without authoring geometry; height is never a pitch cap."""
    if not isinstance(spec, Mapping):
        raise TypeError("spec must be a mapping")
    kind = spec.get("assembly_class", "regular_house")
    if kind not in ASSEMBLY_CLASSES:
        raise ValueError(f"assembly_class must be one of {ASSEMBLY_CLASSES}")
    w,d = _number(spec,"width_m",None),_number(spec,"depth_m",None)
    if not 3 <= w <= 100 or not 3.5 <= d <= 100:
        raise ValueError("width must be 3–100 m and depth 3.5–100 m")
    floors = spec.get("floors",1)
    if type(floors) is not int or not 1 <= floors <= 8:
        raise ValueError("floors must be an integer from 1 to 8")
    if kind == "stable" and floors != 1:
        raise ValueError("stable is explicitly a one-storey livestock building")
    default_fh = {"older_stone_manor":3.5,"merchant_palazzo":3.6,"stable":2.65,
                  "servant_lodge":2.7,"poor_row":2.5}.get(kind,3.0)
    fh = _number(spec,"floor_height_m",default_fh)
    if not 2.25 <= fh <= 6:
        raise ValueError("floor_height_m must be 2.25–6 m")
    roof = spec.get("roof_form", "hip" if kind in ("older_stone_manor","merchant_palazzo") else "gable")
    roof = {"hipped":"hip","pitched":"gable"}.get(roof,roof)
    if roof not in ROOF_FORMS:
        raise ValueError(f"roof_form must be one of {ROOF_FORMS}")
    pitch = _number(spec,"roof_pitch_degrees",0 if roof == "flat" else 42)
    if roof == "flat":
        if pitch != 0: raise ValueError("flat roof requires explicit zero-degree pitch")
    elif not 15 <= pitch <= 60:
        raise ValueError("pitched roof angle must be 15–60 degrees")
    era = spec.get("construction_era","rebuilt")
    if era not in ERA_MAP:
        raise ValueError(f"unsupported construction_era {era}")
    # Total roof depth leaves .30 m for the front threshold edge.
    roof_d = d-.30
    units = spec.get("attached_units", max(1,int(w/3.4))) if kind == "poor_row" else 1
    if type(units) is not int or not 1 <= units <= 8 or w/units < 2:
        raise ValueError("attached_units must be 1–8 with at least 2 m roof frontage per unit")
    if kind == "poor_row" and roof in ("gable","steep_gable"):
        half_span = w/units/2
    elif roof == "twin_gable_z": half_span = w/4
    elif roof == "twin_gable_x": half_span = roof_d/4
    elif roof == "hip": half_span = min(w,roof_d)/2
    elif roof == "shed": half_span = w  # one full run, not a gable half-run
    elif roof == "flat": half_span = 0
    else: half_span = w/2
    rise = half_span*math.tan(math.radians(pitch)) if roof != "flat" else .50
    eave = .50+floors*fh
    roof_peak = eave+rise
    total = roof_peak+.50
    supplied = spec.get("height_m")
    if supplied is not None and not math.isclose(_number(spec,"height_m",None),total,abs_tol=.01):
        raise ValueError(f"height_m conflicts with explicit storeys/pitch: required {total:.6f} m; omit height_m to derive")
    return {"assembly_class":kind,"width_m":w,"depth_m":d,"floors":floors,
            "floor_height_m":fh,"roof_form":roof,"roof_pitch_degrees":pitch,
            "roof_run_m":half_span,"roof_rise_m":rise,"eave_height_m":eave,
            "roof_peak_height_m":roof_peak,"height_m":total,
            "construction_era":era,"geometry_era":ERA_MAP[era],"row_units":units}


def _paint(a,c,name,shape,mat,part="solid",basis=None):
    a.paint(c,name,shape,mat,part)
    if basis is not None: c["operations"][-1]["transform"]={"basis":deepcopy(basis)}


def _stone_window(a,c,name,x,y,width,height):
    before = len(c["operations"])
    _window(a,c,name,x,y,width,height)
    for op in c["operations"][before:]:
        if op["action"] == "cut": op["shape"]["min"][2] = -1.0
        if op.get("material") in ("timber","timber_light"):
            op["material"]="stone_light"


def _new_facade(a,name,span,fh,kind,floor,front,era,units=1):
    c = a.component(name,"livelihood_wall_assembly")
    half = span/2
    panel = {"older_stone_manor":"stone", "merchant_palazzo":"plaster_light",
             "timber_courtyard_house":"plaster", "stable":"timber_light",
             "servant_lodge":"plaster", "poor_row":"plaster_dark"}[kind]
    wall_t = .75 if kind == "older_stone_manor" else .50
    a.paint(c,"wall_panel",_box((-half,0,-wall_t),(half,fh,0)),panel)
    base_h = ({"early":.75,"rebuilt":.65,"late":.45}[era] if kind != "merchant_palazzo" else {"early":1.25,"rebuilt":1.05,"late":.85}[era])
    if floor == 0:
        a.paint(c,"masonry_base",_box((-half,0,-wall_t),(half,base_h,.04)),"stone_dark" if kind == "older_stone_manor" else "stone")
    timber = kind in ("timber_courtyard_house","stable","servant_lodge","poor_row")
    if timber:
        for k,y in enumerate((.18,fh-.20)):
            a.paint(c,f"horizontal_belt_{k}",_box((-half,y-.18,-wall_t),(half,y+.18,.12)),"timber_dark")
        bays = max(1,round(span/(2.55 if kind=="timber_courtyard_house" else 3.4)))
        for i in range(bays+1):
            x = max(-half+.2,min(half-.2,-half+span*i/bays))
            a.paint(c,f"timber_post_{i}",_box((x-.19,0,-wall_t),(x+.19,fh,.14)),"timber")
        if kind == "timber_courtyard_house" and floor>0:
            for i in range(bays):
                x0,x1=-half+span*i/bays+.30,-half+span*(i+1)/bays-.30
                if x1>x0+.45:
                    a.paint(c,f"court_cross_brace_{i}",_extrusion([(x0,.4),(x0+.22,.4),(x1,fh-.4),(x1-.22,fh-.4)],-.5,.16),"timber_dark")
    else:
        # Mineral corners/belts distinguish these halls from half-timber houses.
        for side,x0 in (("left",-half),("right",half-.48)):
            a.paint(c,"stone_corner_"+side,_box((x0,0,-wall_t),(x0+.48,fh,.13)),"stone_light")
        a.paint(c,"stone_cornice",_box((-half,fh-.30,-wall_t),(half,fh,.13)),"stone_light")
        if kind == "merchant_palazzo":
            a.paint(c,"regular_sill_course",_box((-half,.72,-wall_t),(half,1.00,.12)),"stone")
    if front and floor == 0:
        if kind == "stable":
            n=max(1,int(span/4.5))
            for i in range(n):
                x=(i-(n-1)/2)*span/n
                # _door emits IDs; keep repeated stable bays unique.
                tmp=a.component(name+f"_door_{i}","stable_closed_double_door")
                _door(a,tmp,x,0,min(2.75,span/n*.72),min(2.35,fh-.35),True)
                # Put its aperture cut into the structural wall; insert the leaves later.
                a.cut(c,f"stable_door_aperture_{i}",deepcopy(tmp["operations"][0]["shape"]))
                for op in tmp["operations"]:
                    op["id"]=f"stable_{i}_"+op["id"]
                # Return inserts through metadata; authoring removes this staging field.
                c.setdefault("_inserts",[]).append(tmp)
        elif kind == "poor_row":
            n=max(1,units)
            for i in range(n):
                x=(i-(n-1)/2)*span/n
                tmp=a.component(name+f"_door_{i}","row_closed_entrance")
                _door(a,tmp,x,0,min(1.15,span/n*.42),min(2.05,fh-.35))
                a.cut(c,f"row_door_aperture_{i}",deepcopy(tmp["operations"][0]["shape"]))
                for op in tmp["operations"]:op["id"]=f"row_{i}_"+op["id"]
                c.setdefault("_inserts",[]).append(tmp)
        else:
            door_w=1.9 if kind in ("older_stone_manor","merchant_palazzo") else 1.3
            _door(a,c,0,0,min(door_w,span*.4),min(2.6,fh-.45),kind=="older_stone_manor")
            if kind=="older_stone_manor":
                next(op for op in c["operations"] if op["id"]=="door_aperture")["shape"]["min"][2]=-1.0
    if kind=="stable":
        centers=[] if front else [0]
        wy,wh,ww=max(.70,fh-1.55),1.0,min(1.20,span*.35)
    elif kind=="poor_row":
        n=max(1,units if front else int(span/3.8))
        centers=[(i-(n-1)/2)*span/n for i in range(n)] if not(front and floor==0) else []
        wy,wh,ww=.85,min(1.0,fh-1.25),min(1.15,span/max(1,n)*.40)
    else:
        spacing=3.8 if kind=="older_stone_manor" else 2.7 if kind=="merchant_palazzo" else 3.1
        count=max(1,min(7,int(span/spacing)))
        centers=[(i-(count-1)/2)*span/(count+.6) for i in range(count)]
        if front and floor==0:centers=[x for x in centers if abs(x)>1.8]
        wy=.95 if kind=="older_stone_manor" else .95 if floor==0 else .75
        wh=min(1.65 if kind=="older_stone_manor" else 2.05,fh-wy-.45)
        ww=min(1.25 if kind=="older_stone_manor" else 1.65,span*.33)
    for i,x in enumerate(centers):
        if kind in ("older_stone_manor","merchant_palazzo"):
            _stone_window(a,c,f"window_{i}",x,wy,ww,wh)
        else:_window(a,c,f"window_{i}",x,wy,ww,wh,kind=="servant_lodge" and abs(x)+ww/2+.7<half)
    return c


def _roof_gable(a,name,w,z0,z1,eave,pitch,position=(0,0,0),side="front",shed=False):
    run=w if shed else w/2
    peak=eave+run*math.tan(math.radians(pitch))
    c=a.component(name,"uniform_material_pitched_roof")
    sections=[(-w/2,eave,w/2,peak)] if shed else [(-w/2,eave,0,peak),(0,peak,w/2,eave)]
    for i,(x0,y0,x1,y1) in enumerate(sections):
        a.paint(c,f"roof_plane_{i}",_extrusion([(x0,y0-.55),(x1,y1-.55),(x1,y1),(x0,y0)],z0,z1),"slate")
    if not shed:a.paint(c,"subtle_ridge",_box((-.22,peak-.35,z0),(.22,peak,z1)),"slate_dark")
    a.instance(c,position=position,side=side)
    return peak


def _roof_hip(a,name,w,d,eave,pitch,position=(0,0,0),side="front"):
    """Four true sloping skins trimmed by matching orthogonal hip planes."""
    if w>d:
        return _roof_hip(a,name,d,w,eave,pitch,position,"right" if side=="front" else "front")
    half,run=w/2,w/2
    z0,z1=-d/2,d/2
    peak=eave+run*math.tan(math.radians(pitch))
    side_c=a.component(name+"_long_planes","hip_roof_planes")
    for i,(x0,y0,x1,y1) in enumerate(((-half,eave,0,peak),(0,peak,half,eave))):
        a.paint(side_c,f"slope_{i}",_extrusion([(x0,y0-.55),(x1,y1-.55),(x1,y1),(x0,y0)],z0,z1),"slate")
    for tag,poly in (
        ("back",[(z0,eave),(z0+run,peak),(z0+run,peak+1),(z0,peak+1)]),
        ("front",[(z1-run,peak),(z1,eave),(z1,peak+1),(z1-run,peak+1)])):
        a.cut(side_c,"trim_"+tag,_extrusion(poly,-half-.1,half+.1))
        side_c["operations"][-1]["transform"]={"basis":deepcopy(ROTATIONS["left"])}
    a.instance(side_c,position=position,side=side)
    end_c=a.component(name+"_end_planes","hip_roof_planes")
    for tag,x0,y0,x1,y1 in (("back",z0,eave,z0+run,peak),("front",z1-run,peak,z1,eave)):
        _paint(a,end_c,"slope_"+tag,_extrusion([(x0,y0-.55),(x1,y1-.55),(x1,y1),(x0,y0)],-half,half),"slate",basis=ROTATIONS["left"])
    for tag,poly in (
        ("left",[(-half,eave),(0,peak),(0,peak+1),(-half,peak+1)]),
        ("right",[(0,peak),(half,eave),(half,peak+1),(0,peak+1)])):
        a.cut(end_c,"trim_"+tag,_extrusion(poly,z0-.1,z1+.1))
    a.instance(end_c,position=position,side=side)
    return peak


def _roofs(a,info):
    w,d,eave=info["width_m"],info["depth_m"]-.3,info["eave_height_m"]
    pitch,form=info["roof_pitch_degrees"],info["roof_form"]
    z0,z1=-info["depth_m"]/2,info["depth_m"]/2-.3
    if form=="hip":
        _roof_hip(a,"roof",w,d,eave,pitch,(0,0,-.15))
    elif form=="twin_gable_z" or info["assembly_class"]=="poor_row" and form in ("gable","steep_gable"):
        count=2 if form=="twin_gable_z" else info["row_units"]
        for i in range(count):
            _roof_gable(a,f"roof_{i}",w/count,z0,z1,eave,pitch,((i-(count-1)/2)*w/count,0,0))
    elif form=="twin_gable_x":
        for i,z in enumerate((z0+d/4,z0+3*d/4)):
            _roof_gable(a,f"roof_{i}",d/2,-w/2,w/2,eave,pitch,(0,0,z),"right")
    elif form=="flat":
        c=a.component("roof","flat_roof_deck")
        a.paint(c,"deck",_box((-w/2,eave,z0),(w/2,eave+.5,z1)),"slate")
        a.instance(c)
    else:_roof_gable(a,"roof",w,z0,z1,eave,pitch,shed=form=="shed")


def _gable_supports(a,c,info,bx,back,front):
    form=info["roof_form"];eave=info["eave_height_m"];peak=info["roof_peak_height_m"]
    if form in ("hip","flat"):return
    w=info["width_m"];d=info["depth_m"]-.3
    if form=="twin_gable_x":
        for i,(z0,z1,cz) in enumerate(((back,-.15,-info["depth_m"]/2+d/4),(-.15,front,-info["depth_m"]/2+3*d/4))):
            poly=[(-z1,eave-.1),(-z0,eave-.1),(-cz,peak-.55)]
            for tag,x0,x1 in (("left",-bx,-bx+.5),("right",bx-.5,bx)):
                _paint(a,c,f"cross_gable_{i}_{tag}",_extrusion(poly,x0,x1),"stone" if info["assembly_class"]=="older_stone_manor" else "plaster",basis=ROTATIONS["right"])
        return
    count=2 if form=="twin_gable_z" else info["row_units"] if info["assembly_class"]=="poor_row" else 1
    for i in range(count):
        x0=max(-bx,-w/2+i*w/count);x1=min(bx,-w/2+(i+1)*w/count);cx=-w/2+(i+.5)*w/count
        poly=[(x0,eave-.1),(x1,eave-.1),(x1,peak-.55)] if form=="shed" else [(x0,eave-.1),(x1,eave-.1),(cx,peak-.55)]
        for tag,z0,z1 in (("front",front-.5,front),("back",back,back+.5)):
            a.paint(c,f"gable_{i}_{tag}",_extrusion(poly,z0,z1),"stone" if info["assembly_class"]=="older_stone_manor" else "plaster")


def make_master(spec: Mapping) -> dict:
    """Author one fresh continuous master, with height derived from real roof run."""
    info=describe_spec(spec)
    asset_id=spec.get("asset_id")
    if not isinstance(asset_id,str) or not asset_id:raise ValueError("asset_id required")
    style=spec.get("style","old_timber")
    if style not in STYLES:raise ValueError(f"style must be one of {STYLES}")
    source,source_hash=_source()
    a=_Assembly();kind=info["assembly_class"];era=info["geometry_era"]
    w,d=info["width_m"],info["depth_m"];fh=info["floor_height_m"];floors=info["floors"]
    eave,peak,height=info["eave_height_m"],info["roof_peak_height_m"],info["height_m"]
    gallery=kind in ("merchant_palazzo","timber_courtyard_house") and d>=6 and w>=7
    reserve=min(1.80 if gallery else 1.4 if kind=="regular_house" and style in ("merchant","artisan") else 1.0,d*.27)
    bx=w/2-.5;back=-d/2+.5;front=d/2-reserve
    overhang=.30 if floors>1 and (kind=="timber_courtyard_house" or kind=="regular_house" and style=="old_timber") else 0
    foundation=a.component("foundation","continuous_stone_plinth")
    a.paint(foundation,"plinth",_box((-bx,0,back),(bx,.5,front)),"stone_dark")
    threshold_w=min(2.7 if kind in ("older_stone_manor","stable") else 2.1,w-1)
    entry_x=-(2*bx-2*overhang)*.28 if kind=="regular_house" and style in ("merchant","artisan") and 2*bx-2*overhang>=4.2 else 0
    a.paint(foundation,"threshold",_box((entry_x-threshold_w/2,0,front-.1),(entry_x+threshold_w/2,.5,d/2)),"stone_light")
    a.instance(foundation)
    front_entries=[]
    for floor in range(floors):
        y=.5+floor*fh;inset=overhang if floor==0 else 0
        x=bx-inset;z0=back+inset;z1=front-inset
        slab=a.component(f"floor_{floor}","structural_floor")
        a.paint(slab,"floor_slab",_box((-x,y-.05,z0),(x,y+.40,z1)),"timber_dark")
        if kind=="poor_row":
            for i in range(1,info["row_units"]):
                px=-bx+2*bx*i/info["row_units"]
                a.paint(slab,f"party_wall_{i}",_box((px-.25,y,z0),(px+.25,y+fh,z1)),"stone_dark")
        a.instance(slab)
        for side,span,pos in (("front",2*x,(0,y,z1)),("back",2*x,(0,y,z0)),("right",z1-z0,(x,y,(z0+z1)/2)),("left",z1-z0,(-x,y,(z0+z1)/2))):
            name=f"wall_{floor}_{side}"
            facade=_wall(a,name,span,fh,style,floor,side=="front",era) if kind=="regular_house" else _new_facade(a,name,span,fh,kind,floor,side=="front",era,info["row_units"])
            inserts=facade.pop("_inserts",[])
            a.instance(facade,position=pos,side=side)
            for insert in inserts:a.instance(insert,position=pos,side=side)
        if floor==0:
            n=max(1,int(2*x/4.5)) if kind=="stable" else info["row_units"] if kind=="poor_row" else 1
            front_entries=[[(i-(n-1)/2)*2*x/n if n>1 else entry_x,.5,z1] for i in range(n)]
    if kind in ("poor_row","stable"):
        for i,(ex,ey,ez) in enumerate(front_entries):
            sw=min(threshold_w,w/max(1,len(front_entries)))
            a.paint(foundation,f"service_threshold_{i}",_box((ex-sw/2,0,front-.1),(ex+sw/2,.5,d/2)),"stone_light")
        entry_x=front_entries[0][0]
    attic=a.component("attic_support","roof_support")
    a.paint(attic,"ceiling",_box((-bx,eave-.30,back),(bx,eave,front)),"timber_dark")
    _gable_supports(a,attic,info,bx,back,front);a.instance(attic)
    _roofs(a,info)
    if gallery:
        c=a.component("front_gallery","stone_loggia" if kind=="merchant_palazzo" else "timber_covered_gallery")
        mat="stone_light" if kind=="merchant_palazzo" else "timber"
        gy=.5+min(fh-.30,2.8)
        a.paint(c,"gallery_walk",_box((-bx,.25,front),(bx,.5,d/2-.1)),"stone")
        a.paint(c,"gallery_roof",_box((-bx,gy,front),(bx,gy+.40,d/2-.2)),"slate")
        n=max(2,round(2*bx/3))
        for i in range(n+1):
            x=max(-bx+.25,min(bx-.25,-bx+2*bx*i/n))
            if abs(x-entry_x)<.95:continue
            a.paint(c,f"gallery_column_{i}",_box((x-.22,.5,d/2-.65),(x+.22,gy,d/2-.2)),mat)
        a.instance(c)
    elif kind=="regular_house" and style in ("merchant","artisan") and 2*bx>=4.2:
        c=a.component("shop_canopy","shopfront_canopy")
        left,right=max(-bx+.25,entry_x+.9),bx-.25
        if right-left>.6:
            cy=.5+min(2.40,fh-.35)
            _paint(a,c,"awning",_extrusion([(front,cy),(d/2-.1,cy-.25),(d/2-.1,cy+.1),(front,cy+.35)],-right,-left),"slate",basis=ROTATIONS["left"])
            a.instance(c)
    if kind=="older_stone_manor":
        portal=a.component("stone_portal","projecting_stone_portal")
        dw=min(1.9,2*bx*.4);dh=min(2.6,fh-.45)
        outer=[(-dw/2-.4,.5),(dw/2+.4,.5),(dw/2+.4,.5+dh+.15),(0,.5+dh+.65),(-dw/2-.4,.5+dh+.15)]
        a.paint(portal,"portal_arch",_extrusion(outer,front,front+.38),"stone_light")
        a.cut(portal,"portal_clearance",_box((-dw/2,.5,front-.05),(dw/2,.5+dh,front+.45)))
        a.instance(portal)
    chimney=a.component("chimney","masonry_flue")
    cx=min(bx-.5,.45);cz=max(back+.7,min(front-.5,-.15))
    if info["roof_form"]=="twin_gable_z":cx=-w/4
    elif kind=="poor_row" and info["roof_form"] in ("gable","steep_gable"):
        cx=-(info["row_units"]-1)*w/info["row_units"]/2
    elif info["roof_form"]=="twin_gable_x":cz=-d/2+(d-.3)/4
    cw=.90 if style=="artisan" or kind=="older_stone_manor" else .65
    # Stable gets a small service-end vent rather than a ground-floor hearth.
    a.paint(chimney,"shaft",_box((cx-cw/2,eave-.4,cz-cw/2),(cx+cw/2,height-.25,cz+cw/2)),"stone")
    a.paint(chimney,"cap",_box((cx-cw/2-.1,height-.35,cz-cw/2-.1),(cx+cw/2+.1,height,cz+cw/2+.1)),"stone_dark")
    a.instance(chimney)
    rail=deepcopy(next(c for c in source["components"] if c["id"]=="eave_rail"));a.components.append(rail)
    a.instance(rail,"entry_source_eave_rail",(entry_x-.75,.5+min(2.15,fh-.45)+.42,front+.12))
    roof_instances=[i["id"] for i in a.instances if i["id"].startswith("roof")]
    return {"schema":SCHEMA,"id":asset_id,"revision":2,"axes":{"up":"+Y","front":"+Z","right":"+X"},"grid_origin":[0,0,0],
        "materials":deepcopy(source["materials"]),"components":a.components,"instances":a.instances,"assembly_cuts":[],
        "constraints":[{"id":"foundation_present","kind":"nonempty","selector":{"instance":"foundation"}},
            {"id":"roof_present","kind":"nonempty","selector":{"instance":roof_instances}},
            {"id":"closed_door_present","kind":"nonempty","selector":{"part":"door"}},
            {"id":"structural_floor_present","kind":"nonempty","selector":{"instance":"floor_0"}}],
        "metadata":{**info,"style":style,"envelope":{"min":[-w/2,0,-d/2],"max":[w/2,height,d/2]},
            "body_bounds":{"min":[-bx,.5,back],"max":[bx,eave,front]},
            "entrance":{"front":"+Z","closed":True,"position":front_entries[0],"all_positions":front_entries,
                "threshold_bounds":{"min":[entry_x-threshold_w/2,.5,front+.4],"max":[entry_x+threshold_w/2,2.2,d/2]}},
            "roof_geometry":"Exact roof run multiplied by tan(explicit pitch); no height-driven flattening.",
            "palette_policy":"Uniform slate semantic slots; per-property red clay/brown wood/gray slate runtime mapping is external.",
            "lod":"One continuous source; independently sample at each pitch.",
            "authoring":"Dimension-authored modular livelihood assembly; no whole-building scaling.",
            "compound_scope":"Main residence building; enclosing property walls, gardens and service buildings are separate measured land-use assemblies."},
        "provenance":{"source_files":[{"path":"voxel_character/common/assets/house/master.json","sha256":source_hash},
            {"path":"world_city/runtime_city/archetypes/ordinary.py","sha256":hashlib.sha256(Path(__file__).with_name("ordinary.py").read_bytes()).hexdigest()}],
            "reused_exact_components":["eave_rail"],"grammar":"Existing common master boxes/extrusions/cuts and rigid transforms only.",
            "r1_policy":"Protected seven use unchanged r1 author/compiler path; this module is never an automatic protected-house upgrade.",
            "not_visual_approval":True}}
