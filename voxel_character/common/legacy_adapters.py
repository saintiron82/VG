"""Explicit legacy-operation lowering; no legacy sampler runs here.

These are migration front ends, not object dispatch in the common compiler.
Unsupported source operations fail rather than silently dropping geometry.
"""
import math


def lower_prism_operation(source, operation_id, part):
    kind = source["kind"]
    if kind == "box":
        shape = {"kind": "box", "min": source["a"], "max": source["b"]}
        if source["material"] != "__erase__":
            shape["minimum_cells"] = [1, 1, 1]
    elif kind == "polygon_xy":
        shape = {"kind": "extrusion", "polygon": source["vertices"], "z_min": source["z0"], "z_max": source["z1"]}
    elif kind == "slope":
        x0, x1 = source["x0"], source["x1"]
        top0, top1 = [source["intercept"]+source["gradient"]*x for x in (x0, x1)]
        shape = {"kind": "extrusion", "polygon": [[x0, top0-source["thickness"]], [x1, top1-source["thickness"]], [x1, top1], [x0, top0]], "z_min": source["z0"], "z_max": source["z1"]}
    elif kind == "beam_xy":
        a, b = source["a"], source["b"]
        dx, dy = b[0]-a[0], b[1]-a[1]
        length = math.hypot(dx, dy)
        if length <= 0 or a[2] != b[2]:
            raise ValueError("beam_xy requires a nonzero planar segment")
        nx, ny = -dy/length*source["width"]/2, dx/length*source["width"]/2
        shape = {"kind": "extrusion", "polygon": [[a[0]+nx, a[1]+ny], [b[0]+nx, b[1]+ny], [b[0]-nx, b[1]-ny], [a[0]-nx, a[1]-ny]], "z_min": a[2]-source["depth"]/2, "z_max": a[2]+source["depth"]/2}
    else:
        raise ValueError(f"unmigrated prism operation: {kind}")
    operation = {"id": operation_id, "part": part, "action": "cut" if source["material"] == "__erase__" else "paint", "shape": shape}
    if operation["action"] == "paint":
        operation["material"] = source["material"]
    return operation


def lower_rotational_operation(source):
    kind = source["kind"]
    base = {"id": source["id"], "part": source["part"], "action": "paint", "material": source["role"]}
    if kind == "lathe_y":
        return [{**base, "shape": {"kind": "lathe", "profile": source["profile"]}}]
    if kind == "water_disk":
        return [{**base, "shape": {"kind": "annulus", "inner_radius": source["inner_radius"], "outer_radius": source["radius"], "y_min": source["surface"]-source["depth"], "y_max": source["surface"], "minimum_cells_y": source.get("minimum_visible_cells", 0), "anchor_y": "max"}}]
    if kind == "radial_bezier_tubes":
        operations = []
        controls = source["curve_radius_y"]
        # Fixed source approximation; not changed for each output resolution.
        for index in range(source["count"]):
            angle = math.radians(source["phase_degrees"])+math.tau*index/source["count"]
            points = []
            for n in range(65):
                t, u = n/64, 1-n/64
                weights = [u**3, 3*u*u*t, 3*u*t*t, t**3]
                r, y = [sum(w*p[axis] for w, p in zip(weights, controls)) for axis in range(2)]
                points.append([r*math.cos(angle), y, r*math.sin(angle)])
            operations.append({**base, "id": f"{source['id']}_{index}", "shape": {"kind": "tube", "points": points, "radius": source["radius"], "minimum_radius_cells": .75*source.get("minimum_visible_cells", 0)}})
        return operations
    raise ValueError(f"unmigrated rotational operation: {kind}; no silent fallback")
