"""Four-tile R13 fixture for exporter cache equivalence, never a city scene."""
from world_city.concept_city_v3.registered_topography.revisions.r13_precinct_interfaces.materials import *
from world_city.concept_city_v3.registered_topography.revisions.r13_precinct_interfaces import materials as original

def build_contract():
 c=original.build_contract();c['review_bounds_xz_m']=[320,304,336,320];return c
