"""Independent bounded render-surface audit. No occupancy compiler is imported.

Streams JSON quads, checks end-wall axial apertures, and flood-tests exact .05m
YZ surface barriers. The upper-section test starts at y=5.5, above intentional
entries/windows; this is an audit-domain boundary, never output geometry.
"""
import argparse
from collections import Counter, defaultdict, deque
import gzip
import hashlib
import json
from pathlib import Path
import resource
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
KEY = 'registered_port_long_loading_shed'
SOURCE = ROOT / 'world_city/concept_city_v3/assemblies/landmarks/registered/port_r01/cache' / (KEY + '.pitch_0.5.render.json')
JOINT_XS = [(-939+20*i)/40 for i in range(95)]
XS = sorted(set(JOINT_XS + [-23.225,23.225]))
FULL_XS = XS


def quads(path):
    """Decode only one quad at a time, with a bounded text buffer."""
    op = gzip.open if path.suffix == '.gz' else open
    decoder = json.JSONDecoder()
    buf = ''
    with op(path, 'rt') as stream:
        while True:
            while '"quads":' not in buf:
                chunk = stream.read(65536)
                if not chunk:
                    return
                buf = buf[-30:] + chunk
            buf = buf[buf.index('"quads":') + 8:].lstrip()
            if not buf:
                buf = stream.read(65536)
            assert buf[0] == '['
            buf = buf[1:]
            while True:
                buf = buf.lstrip(' \n\r\t,')
                if not buf:
                    buf = stream.read(65536)
                if buf.startswith(']'):
                    buf = buf[1:]
                    break
                try:
                    quad, end = decoder.raw_decode(buf)
                except json.JSONDecodeError:
                    chunk = stream.read(65536)
                    if not chunk:
                        raise
                    buf += chunk
                    continue
                buf = buf[end:]
                yield quad


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            digest.update(chunk)
    return digest.hexdigest()


def components(cells):
    todo = set(cells)
    result = []
    while todo:
        first = todo.pop()
        stack, part = [first], [first]
        while stack:
            y, z = stack.pop()
            for neighbor in ((y-1,z), (y+1,z), (y,z-1), (y,z+1)):
                if neighbor in todo:
                    todo.remove(neighbor)
                    stack.append(neighbor)
                    part.append(neighbor)
        result.append({'unit_face_cells': len(part),
                       'yz_min_m': [min(p[j] for p in part) / 20 for j in (0,1)],
                       'yz_max_m': [(max(p[j] for p in part)+1) / 20 for j in (0,1)]})
    return sorted(result, key=lambda p: (-p['unit_face_cells'], p['yz_min_m']))


def apertures(mask):
    """Only holes between lower facade and upper roof, not roof silhouette cuts."""
    gaps = set()
    for z in range(-120,120):
        ys = [y for y in range(110,200) if (y,z) in mask]
        if ys:
            gaps.update((y,z) for y in range(min(ys),max(ys)+1) if (y,z) not in mask)
    return gaps


def section_flood(segments, lower_y, virtual_caps=False):
    y0, z0, ymax, nz = lower_y, -140, 220, 280
    ny = ymax-y0
    by, bz = bytearray((ny+1)*nz), bytearray(ny*(nz+1))
    if virtual_caps:
        segments = segments + [(1,120,-120,-119), (1,120,119,120)]
    for axis, plane, lo, hi in segments:
        if axis == 1:
            iy = plane-y0
            if 0 <= iy <= ny:
                for z in range(max(lo,z0), min(hi,z0+nz)):
                    by[iy*nz+z-z0] = 1
        else:
            iz = plane-z0
            if 0 <= iz <= nz:
                for y in range(max(lo,y0), min(hi,ymax)):
                    bz[(y-y0)*(nz+1)+iz] = 1
    visited = bytearray(ny*nz)
    queue = deque([0])
    visited[0] = 1
    while queue:
        n = queue.popleft()
        iy, iz = divmod(n,nz)
        neighbors = []
        if iy and not by[iy*nz+iz]:
            neighbors.append(n-nz)
        if iy+1 < ny and not by[(iy+1)*nz+iz]:
            neighbors.append(n+nz)
        if iz and not bz[iy*(nz+1)+iz]:
            neighbors.append(n-1)
        if iz+1 < nz and not bz[iy*(nz+1)+iz+1]:
            neighbors.append(n+1)
        for m in neighbors:
            if not visited[m]:
                visited[m] = 1
                queue.append(m)
    return bool(visited[(140-y0)*nz-z0])  # y=7.025,z=.025 cell center


def inspect(path):
    masks = {'all_x':set(), 'west_1m':set(), 'east_1m':set()}
    sections = {x:[] for x in XS}
    endpoints = set()
    count = 0
    for quad in quads(path):
        count += 1
        v = [tuple(round(c*20) for c in p) for p in quad]
        assert all(abs(c*20-round(c*20)) < 1e-5 for p in quad for c in p)
        lo = [min(p[j] for p in v) for j in range(3)]
        hi = [max(p[j] for p in v) for j in range(3)]
        axis = next(j for j in range(3) if lo[j] == hi[j])
        for a,b in zip(v,v[1:]+v[:1]):
            direction = next(j for j in range(3) if a[j] != b[j])
            fixed = [j for j in range(3) if j != direction]
            for p in (a,b):
                event = (direction,p[fixed[0]],p[fixed[1]],p[direction])
                if event in endpoints:
                    endpoints.remove(event)
                else:
                    endpoints.add(event)
        if axis == 0:
            targets = [masks['all_x']]
            if -480 <= lo[0] <= -460:
                targets.append(masks['west_1m'])
            if 460 <= lo[0] <= 480:
                targets.append(masks['east_1m'])
            for y in range(max(110,lo[1]), min(200,hi[1])):
                for z in range(max(-120,lo[2]), min(120,hi[2])):
                    for mask in targets:
                        mask.add((y,z))
        else:
            for x in XS:
                if lo[0] < x*20 < hi[0]:
                    sections[x].append((axis,lo[axis],lo[3-axis],hi[3-axis]))
    lines = defaultdict(list)
    for d,a,b,t in endpoints:
        lines[d,a,b].append(t)
    odd = 0
    for ts in lines.values():
        ts.sort()
        assert len(ts) % 2 == 0
        odd += sum(b-a for a,b in zip(ts[::2],ts[1::2]))
    holes = {}
    for key, mask in masks.items():
        gap = apertures(mask)
        holes[key] = {'aperture_unit_cells':len(gap), 'aperture_area_m2':len(gap)/400,
                      'component_count':len(components(gap))}
        if key == 'all_x':
            holes[key]['components'] = components(gap)
    upper = {'x_positions_m':XS, 'exterior_reaches_upper_interior':[section_flood(sections[x],110) for x in XS]}
    full = {'x_positions_m':FULL_XS, 'exterior_reaches_upper_interior':[section_flood(sections[x],-40) for x in FULL_XS]}
    result = {'path':str(path.relative_to(ROOT)), 'sha256':sha(path), 'quad_count':count,
              'raw_unpaired_unit_edges':odd, 'gable_axial_projection':holes,
              'upper_section_domain_y_min_m':5.5, 'upper_section_tests':upper,
              'full_height_section_tests_including_entries':full}
    if '.r02.' in path.name:
        result['earlier_virtual_cap_experiment_not_written_to_geometry'] = [
            {'x_m':x, 'exterior_reaches_upper_interior':section_flood(sections[x],-40,True)}
            for x in [-23.475,-23.225,-22.975]]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=HERE/'independent_interface_qa.json')
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_AS, (128*1024**2,128*1024**2))
    start = time.monotonic()
    paths = [('original_coarse',SOURCE)] + [(rev,HERE/(KEY+'.'+rev+'.composed.render.json.gz')) for rev in ('r01','r02','r03')]
    missing = [str(p) for _,p in paths if not p.is_file()]
    if missing:
        raise SystemExit('Inputs not complete: '+', '.join(missing))
    results = {}
    for label,path in paths:
        results[label] = inspect(path)
        r = results[label]
        print(json.dumps({'revision':label, 'gable_through_cells':r['gable_axial_projection']['all_x']['aperture_unit_cells'],
                          'upper_section_leaks':sum(r['upper_section_tests']['exterior_reaches_upper_interior']),
                          'raw_unpaired_unit_edges':r['raw_unpaired_unit_edges']}), flush=True)
    source, current = results['original_coarse'], results['r03']
    checks = {
        'original_coarse_gable_baseline_zero':source['gable_axial_projection']['all_x']['aperture_unit_cells']==0,
        'known_r01_r02_gable_failures_reproduced':all(results[r]['gable_axial_projection']['all_x']['aperture_unit_cells']==294 for r in ('r01','r02')),
        'r03_gable_axial_apertures_zero':all(v['aperture_unit_cells']==0 for v in current['gable_axial_projection'].values()),
        'original_upper_section_baseline_zero':not any(source['upper_section_tests']['exterior_reaches_upper_interior']),
        'r03_upper_section_leaks_zero':not any(current['upper_section_tests']['exterior_reaches_upper_interior']),
        'intentional_entry_and_full_section_baselines_preserved':source['full_height_section_tests_including_entries']==current['full_height_section_tests_including_entries'],
    }
    report = {'schema':'riverstone.independent_interface_surface_qa.v1','checks':checks,'bounded_tests_pass':all(checks.values()),
              'method':'Streaming render faces only. Exact .05m axial projection plus .05m surface-barrier section flood. No voxel compilation, no source-shape modification.',
              'interpretation':'Upper-domain flood isolates roof/wall seams above entries. All 95 half-metre fascia joints and two normal fascia controls are checked. Full-height sections at existing entries/loading bays are compared to original reachability rather than required to be closed.',
              'limitations':['These are bounded roof/wall external-leak tests, not a certificate that every possible global surface or view is watertight.',
                             'Raw edge parity includes hidden intersections and T-junctions; it is reported separately and does not decide visible leakage.',
                             'No claim of source-shape, collider, or all outside-ROI geometry equality is made by this independent script.'],
              'results':results,'audit_script_sha256':sha(Path(__file__)),'max_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
              'elapsed_seconds':round(time.monotonic()-start,3)}
    data = json.dumps(report,sort_keys=True,separators=(',',':'))+'\n'
    assert len(data.encode()) < 30000
    args.output.write_text(data)
    print(json.dumps({'checks':checks,'bounded_tests_pass':report['bounded_tests_pass'],'max_rss_kib':report['max_rss_kib'],'output_bytes':len(data.encode())}),flush=True)


if __name__ == '__main__':
    main()
