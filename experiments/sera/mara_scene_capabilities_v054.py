"""Frozen Mara S1 registered capabilities, shared by OFFLINE and delegated lanes.

Capabilities come only from application-owned entry state, never from model
claims, synthetic gold event lists or analyst annotations. Both the pocket
watch and notebook are physical objects. Notebook is OPENABLE + DOCUMENT.
"""
from __future__ import annotations

from experiments.sera.coverage import CoverageError


def registered_mara_facets(world):
    if not isinstance(world,dict) or not isinstance(world.get("entities"),dict):
        raise CoverageError("V054_MARA_ENTRY_WORLD_INVALID")
    roles={"openables":["vane_watch","mara_notebook"],
           "documents":["mara_notebook"]}
    for identifier in set(roles["openables"]+roles["documents"]):
        entity=world["entities"].get(identifier)
        if not isinstance(entity,dict) or entity.get("kind")!="OBJECT" or entity.get("lifecycle")!="ACTIVE":
            raise CoverageError("V052_MARA_REGISTERED_FACET_MISSING")
    if (world["entities"]["vane_watch"]["holder"]!="vane" or
        world["entities"]["mara_notebook"]["holder"]!="mara"):
        raise CoverageError("V052_MARA_FACET_CUSTODY_MISMATCH")
    return roles
