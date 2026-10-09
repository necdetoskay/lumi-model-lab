"""Versioned seed-bound planner admission; no provider calls or state mutation."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Literal
from pydantic import Field, model_validator
from src.spineforge_relay_v1_contracts import (
    StrictModel, CharacterState, ObjectState, NarrativeObligation, canonical_sha256,
)
from src.spineforge_relay_v1_spatial import SpatialTopologyV1, SpatialStateV1
from src.spineforge_story_design import StoryRequestV1, StoryDesignV1, planner_input, validate_design


class StorySeedV1(StrictModel):
    schema_name: Literal["spineforge.story-seed.v1"] = "spineforge.story-seed.v1"
    story_id: str = Field(min_length=1)
    scenario_id: str = Field(min_length=1)
    characters: dict[str, CharacterState]
    relevant_character_canon: dict[str, dict[str, Any]]
    world: dict[str, Any]
    objects: dict[str, ObjectState]
    topology: SpatialTopologyV1
    prop_authorization_policy: dict[str, Any]
    open_threads: list[str] = Field(min_length=1)
    narrative_obligations: list[NarrativeObligation] = Field(min_length=1)
    assumptions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def check(self):
        if not self.characters or set(self.characters) != set(self.relevant_character_canon):
            raise ValueError("Character state/canon identities differ")
        if set(self.characters) & set(self.objects):
            raise ValueError("Character/object identity collision")
        spatial=SpatialStateV1.model_validate(self.world.get("spatial"))
        if spatial.topology_sha256 != canonical_sha256(self.topology):
            raise ValueError("Seed topology fingerprint differs")
        entities={**self.characters,**self.objects}
        if set(spatial.positions) != set(entities) or set(self.topology.position_state_paths) != set(entities):
            raise ValueError("Seed entities require exact canonical spatial tracking")
        for name,entity in entities.items():
            category="characters" if name in self.characters else "objects"
            token=name.replace("~","~0").replace("/","~1")
            if self.topology.position_state_paths[name] != f"/{category}/{token}/location":
                raise ValueError("Seed position must bind canonical entity location")
            if entity.location not in self.topology.locations or spatial.positions[name] != entity.location:
                raise ValueError("Seed location disagrees with spatial state")
        for edge in self.topology.edges:
            if not set(edge.allowed_entities) <= set(entities):
                raise ValueError("Unknown edge entity")
        if len(set(self.open_threads)) != len(self.open_threads):
            raise ValueError("Duplicate seed threads")
        if len({o.id for o in self.narrative_obligations}) != len(self.narrative_obligations) or any(o.status != "OPEN" for o in self.narrative_obligations):
            raise ValueError("Seed obligations must be unique and OPEN")
        return self

    def initial_state(self, first_beat: str):
        # Spine and intent hashes do not exist until planning; no fake hash is used.
        return json.loads(json.dumps(dict(revision=0,characters={k:v.model_dump(mode="json") for k,v in self.characters.items()},
                    world=self.world,objects={k:v.model_dump(mode="json") for k,v in self.objects.items()},
                    open_threads=self.open_threads,resolved_threads=[],completed_spine_beats=[],
                    next_spine_beat=first_beat,narrative_obligations=[o.model_dump(mode="json") for o in self.narrative_obligations])))


def freeze_seed(seed_path: Path, output: Path):
    seed=StorySeedV1.model_validate_json(seed_path.read_bytes())
    record=dict(schema="spineforge.frozen-story-seed.v1",seed=seed.model_dump(mode="json"),
                seed_sha256=canonical_sha256(seed),seed_file_sha256=hashlib.sha256(seed_path.read_bytes()).hexdigest())
    # New run/seed version requires a new file; the baseline is never rewritten.
    with output.open("xb") as stream:
        stream.write((json.dumps(record,ensure_ascii=False,indent=2)+"\n").encode())
    return record


def verify_frozen_seed(seed_path: Path, freeze_path: Path):
    record=json.loads(freeze_path.read_text(encoding="utf8"))
    seed=StorySeedV1.model_validate_json(seed_path.read_bytes())
    if (record.get("schema") != "spineforge.frozen-story-seed.v1"
        or record.get("seed_sha256") != canonical_sha256(seed)
        or record.get("seed_file_sha256") != hashlib.sha256(seed_path.read_bytes()).hexdigest()
        or record.get("seed") != seed.model_dump(mode="json")):
        raise ValueError("Frozen starting seed changed")
    return seed


def compare_story_states(seed_path: Path, freeze_path: Path, fixture_path: Path, records: Path):
    from scripts.spineforge_relay_story_replay import verify_story
    seed=verify_frozen_seed(seed_path,freeze_path)
    fixture=json.loads(fixture_path.read_text(encoding="utf8"))
    if fixture.get("initial_state") != seed.initial_state(fixture["route"][0]) or fixture.get("story_id") != seed.story_id:
        raise ValueError("Story did not start from frozen seed")
    for key,value in dict(relevant_character_canon=seed.relevant_character_canon,
                          topology=seed.topology.model_dump(mode="json"),
                          prop_authorization_policy=seed.prop_authorization_policy).items():
        if fixture.get(key) != value:
            raise ValueError("Story changed frozen seed field: "+key)
    proof=verify_story(records,fixture_path)
    if proof["recorded_decision"] != "ACCEPT":
        raise ValueError("Complete accepted story required for final-state comparison")
    final=json.loads((records/(fixture["route"][-1]+"-accepted.json")).read_text(encoding="utf8"))["state_after"]
    before=seed.initial_state(fixture["route"][0])
    after={k:final[k] for k in before}
    changes=[]
    def diff(a,b,path):
        if isinstance(a,dict) and isinstance(b,dict):
            for k in sorted(set(a)|set(b)):
                token=k.replace("~","~0").replace("/","~1")
                if k not in a or k not in b:
                    changes.append(dict(path=path+"/"+token,before_present=k in a,after_present=k in b,before=a.get(k),after=b.get(k)))
                else:diff(a[k],b[k],path+"/"+token)
        elif a!=b:changes.append(dict(path=path,before_present=True,after_present=True,before=a,after=b))
    diff(before,after,"")
    return dict(status="VERIFIED_STATE_COMPARISON",seed_sha256=canonical_sha256(seed),
        final_state_sha256=proof["final_state_sha256"],initial_revision=0,final_revision=proof["final_revision"],
        changes=changes,offline_replay="PASS",semantic_quality="REQUIRES_SEPARATE_REVIEW")


class SeededStoryDesignV2(StoryDesignV1):
    schema_name: Literal["spineforge.story-design.v2"] = "spineforge.story-design.v2"
    seed_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def seeded_planner_input(request: StoryRequestV1, seed: StorySeedV1):
    payload=planner_input(request)
    payload.update(schema="spineforge.planner-input.v2",seed=seed.model_dump(mode="json"),
        seed_sha256=canonical_sha256(seed),output_schema=SeededStoryDesignV2.model_json_schema(),
        initial_state_template=seed.initial_state("<first planned beat>"))
    payload["instructions"] += "\n\n"+Path("prompts/spineforge_seeded_design.md").read_text(encoding="utf8")
    payload["sources"].update({name:hashlib.sha256(Path(name).read_bytes().replace(b"\r\n",b"\n")).hexdigest()
        for name in ["src/spineforge_seeded_design.py","prompts/spineforge_seeded_design.md"]})
    return payload


def validate_seeded_design(request,seed,design,fixture_path):
    if design.seed_sha256 != canonical_sha256(seed):
        raise ValueError("Stale seed binding")
    f=design.fixture
    if not f.get("route"):
        raise ValueError("Missing seeded route")
    locked=dict(story_id=seed.story_id,initial_state=seed.initial_state(f["route"][0]),
                relevant_character_canon=seed.relevant_character_canon,
                topology=seed.topology.model_dump(mode="json"),prop_authorization_policy=seed.prop_authorization_policy)
    for key,value in locked.items():
        if f.get(key) != value:
            raise ValueError("Planner changed frozen seed field: "+key)
    proof=validate_design(request,design,fixture_path)
    proof["seed_sha256"]=canonical_sha256(seed)
    proof["seed_preserved"]=True
    return proof


def record_seeded_design(request_path: Path,seed_path: Path,output: Path,proposal_path: Path|None=None,*,freeze_path: Path):
    output.mkdir(parents=True,exist_ok=False)
    def save(name,value):
        (output/name).write_bytes((json.dumps(value,ensure_ascii=False,indent=2)+"\n").encode())
    for name,path in [("request-input.json",request_path),("seed-input.json",seed_path),("frozen-seed.json",freeze_path),("proposal-input.json",proposal_path)]:
        if path is not None:(output/name).write_bytes(path.read_bytes())
    try:
        request=StoryRequestV1.model_validate_json((output/"request-input.json").read_bytes())
        seed=verify_frozen_seed(output/"seed-input.json",output/"frozen-seed.json")
        save("planner-input.json",seeded_planner_input(request,seed))
        if proposal_path is None:
            proof=dict(status="READY_FOR_PLANNER",request_sha256=canonical_sha256(request),seed_sha256=canonical_sha256(seed),
                       provider_calls=0,actual_state_advanced=False,semantic_status="NOT_REVIEWED")
        else:
            design=SeededStoryDesignV2.model_validate_json((output/"proposal-input.json").read_bytes())
            save("candidate-fixture.json",design.fixture)
            proof=validate_seeded_design(request,seed,design,output/"candidate-fixture.json")
    except (ValueError,RuntimeError,KeyError,TypeError) as exc:
        proof=dict(status="REJECTED_DESIGN",failure_type=type(exc).__name__,message=str(exc),provider_calls=0,actual_state_advanced=False)
    save("validation.json",proof)
    save("manifest.json",dict(schema="spineforge.seeded-design-record.v1",files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())},
        paid_authority_created=False,production_write=False))
    return proof


def main():
    p=argparse.ArgumentParser(description="Prepare or validate a state-bound planner input; no inference")
    for name in ("request","seed","freeze","output"):p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--proposal",type=Path)
    a=p.parse_args();r=record_seeded_design(a.request,a.seed,a.output,a.proposal,freeze_path=a.freeze)
    print(json.dumps(r,ensure_ascii=False));return 2 if r["status"]=="REJECTED_DESIGN" else 0


if __name__=="__main__":raise SystemExit(main())
