"""Immutable source transform traversal copied verbatim from the source binder."""
from voxel_character.common import core
ORIGIN_SHA256='2efeecdb665fc41db04e17af173240b3160ea5864ed2084af90a7ae4105fa072'
def source_parts(source):
    components={c['id']:c for c in source['components']};instances={i['id']:i for i in source['instances']};transforms={}
    def tr(key):
        if key not in transforms:
            i=instances[key];value=core.transform(i.get('transform'))
            transforms[key]=core.compose(tr(i['parent']),value) if i.get('parent') else value
        return transforms[key]
    for i in source['instances']:
        for op in components[i['component']]['operations']:
            yield i,op,core.compose(tr(i['id']),core.transform(op.get('transform')))
