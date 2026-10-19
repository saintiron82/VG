"""Optional exact-input memoization; no installation or original module writes."""
import hashlib, types
from pathlib import Path
from functools import lru_cache
SOURCE_SHA256='70fa004d44b1df7cea713cfe1d384dd516ecd5f60388c871d41e8774364a8805'
class ExcludedMemo:
 def __init__(self,source):
  if hashlib.sha256(Path(source.__file__).read_bytes()).hexdigest()!=SOURCE_SHA256:raise ValueError('Exclusion source binding changed')
  code=compile(Path(source.__file__).read_text(),source.__file__,'exec')
  expected=next(c for c in code.co_consts if isinstance(c,types.CodeType) and c.co_name=='is_excluded')
  original=source.is_excluded
  if not isinstance(original,types.FunctionType) or original.__code__!=expected or original.__globals__ is not source.__dict__:raise ValueError('Exclusion callable binding changed')
  self.original=original
  @lru_cache(maxsize=262144)
  def cached(source_id,owner_id,door_id,excluded):
   return original(dict(source_mass_id=source_id,owner_id=owner_id,door_id=door_id),excluded)
  self.cached=cached
 def is_excluded(self,record,excluded_source_ids):
  # Limit memoization to plain types whose values fully determine the original.
  if type(record) is not dict or type(excluded_source_ids) not in (tuple,list):return self.original(record,excluded_source_ids)
  source_id=record.get('source_mass_id');owner_id=record.get('owner_id','');door_id=record.get('door_id','')
  if (source_id is not None and type(source_id) is not str) or type(owner_id) is not str or type(door_id) is not str or any(type(v) is not str for v in excluded_source_ids):return self.original(record,excluded_source_ids)
  return self.cached(source_id,owner_id,door_id,tuple(excluded_source_ids))
