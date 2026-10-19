"""Bounded memoization of the unchanged common semantic selector predicate.

Coordinates are never keys because core.selector_matches receives only the five
semantic fields below in the layered engine. Each distinct complete semantic
cell is evaluated by the original predicate. No geometry or threshold changes.
"""
import copy

FIELDS=('instance','component','part','material','feature')

class SemanticSelectorCache:
    def __init__(self,constraints,instance_to_component,selector_matches,*,max_cached_keys=65536):
        if type(max_cached_keys) is not int or max_cached_keys<0:raise ValueError('Invalid semantic-cache bound')
        self._constraints=copy.deepcopy(constraints);self._instances=dict(instance_to_component)
        if len({c['id'] for c in constraints})!=len(constraints):raise ValueError('Duplicate constraint IDs')
        if any(c['kind'] not in ('nonempty','connected') for c in constraints):raise ValueError('Unsupported global constraint')
        self._predicate=selector_matches;self._cache={};self._limit=max_cached_keys
        self.calls=0;self.hits=0;self.misses=0;self.uncached=0
    def match(self,row):
        key=(row[3],self._instances[row[3]],row[4],row[5],row[6])
        cacheable=all(isinstance(value,(str,type(None))) for value in key)
        if cacheable and key in self._cache:
            self.hits+=1;return self._cache[key]
        self.misses+=1;cell=dict(zip(FIELDS,key));matches=[]
        for constraint in self._constraints:
            self.calls+=1
            if self._predicate(constraint.get('selector',{}),cell):matches.append((constraint['id'],constraint['kind']))
        result=tuple(matches)
        if cacheable and len(self._cache)<self._limit:self._cache[key]=result
        else:self.uncached+=1
        return result
    def assert_source(self,constraints,instance_to_component):
        if constraints!=self._constraints or instance_to_component!=self._instances:raise ValueError('Selector source changed')
    def metrics(self):
        return {'cached_semantic_keys':len(self._cache),'max_cached_keys':self._limit,'hits':self.hits,'misses':self.misses,'reference_predicate_calls':self.calls,'uncached_reference_cells':self.uncached}
