"""Measure every retained roof vertex with bounded JSON reads, without cells."""
import json
import math
from pathlib import Path
import layered_qa as qa


def analyze(path):
    bounds={'min':[math.inf]*3,'max':[-math.inf]*3};count=0;metadata={}
    def quad(value):
        nonlocal count
        if not isinstance(value,list) or len(value)!=4 or any(not isinstance(p,list) or len(p)!=3 for p in value):
            raise ValueError('Malformed quad vertices')
        for point in value:
            for axis,v in enumerate(point):
                if type(v) not in (int,float) or not math.isfinite(v):raise ValueError('Nonfinite or invalid vertex')
                bounds['min'][axis]=min(bounds['min'][axis],v);bounds['max'][axis]=max(bounds['max'][axis],v)
        count+=1
    with qa._text_file(Path(path)) as stream:
        reader=qa._JSONStream(stream);reader.expect('{');root_keys=set();first=True
        while reader.peek()!='}':
            if not first:reader.expect(',')
            key=reader.value();reader.expect(':')
            if key in root_keys:raise ValueError('Duplicate render field')
            root_keys.add(key)
            if key!='groups':metadata[key]=reader.value()
            else:
                reader.expect('[');first_group=True
                while reader.peek()!=']':
                    if not first_group:reader.expect(',')
                    reader.expect('{');first_field=True;keys=set()
                    while reader.peek()!='}':
                        if not first_field:reader.expect(',')
                        group_key=reader.value();reader.expect(':')
                        if group_key in keys:raise ValueError('Duplicate group field')
                        keys.add(group_key)
                        if group_key!='quads':reader.value()
                        else:
                            reader.expect('[');first_quad=True
                            while reader.peek()!=']':
                                if not first_quad:reader.expect(',')
                                quad(reader.value());first_quad=False
                            reader.expect(']')
                        first_field=False
                    reader.expect('}')
                    if 'quads' not in keys:raise ValueError('Missing group quads')
                    first_group=False
                reader.expect(']')
            first=False
        reader.expect('}')
        if reader.peek():raise ValueError('Trailing render data')
    if 'groups' not in root_keys or count==0:raise ValueError('Empty or missing roof geometry')
    checks={'declared_quads_match':metadata.get('quad_count')==count,
            'declared_bounds_match_all_vertices':metadata.get('bounds')==bounds}
    return {'schema':'riverstone.facility_roof.render_bounds.v1','pass':all(checks.values()),'checks':checks,
            'actual_fine_render_bounds':bounds,'rendered_quad_count':count,'render_file':qa._file_info(path),
            'scope':'All retained render vertices, incrementally decoded; this is a bounds check, not an original solid membership proof.',
            'whole_mesh_loaded':False,'voxel_sampling_performed':False}


def publish(key,output,root):
    import compile_batch as batch
    output=Path(output);manifest_path=output/'handoff_manifest.json';manifest=json.loads(manifest_path.read_text())
    record=next(r for r in manifest['assets'] if r['asset_key']==key);render=record['files']['.render.json'];path=Path(root)/render['path']
    report_path=output/(key+'.layered.bounds.json')
    report=analyze(path)
    if not report['pass'] or report['render_file']['sha256']!=render['sha256']:raise ValueError('Full render bounds verification failed')
    if report_path.exists():
        if json.loads(report_path.read_text())!=report:raise ValueError('Prior bounds evidence differs; preserve it')
    else:batch.atomic_json(report_path,report)
    record.update(actual_fine_render_bounds=report['actual_fine_render_bounds'],rendered_quad_count=report['rendered_quad_count'],
                  bounds_evidence={'path':str(report_path.relative_to(root)),'sha256':qa._file_info(report_path)['sha256'],'pass':True})
    batch.atomic_json(manifest_path,manifest)
    return report
