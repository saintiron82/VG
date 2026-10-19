"""Explicit registration-bound revision; preserves the preparation-only v1."""
from author_measured_v1 import build_source as build_preparation_source
from registration_gate_v1 import validate_registration_binding
from parts_v1 import ROOT


def build_source(recipe,measurement,repo_root=ROOT):
    registration=validate_registration_binding(measurement,repo_root)
    master,bom,proof,axes=build_preparation_source(recipe,measurement,repo_root)
    master['provenance']['actual_image_registration']=registration
    proof['image_registration']=registration
    return master,bom,proof,axes
