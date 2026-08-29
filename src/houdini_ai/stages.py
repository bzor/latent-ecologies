from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StageGraph:
    graph_id: str
    stages: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.graph_id:
            raise ValueError("graph_id must not be empty")
        if not self.stages:
            raise ValueError("stage graph must not be empty")
        if any(not stage for stage in self.stages):
            raise ValueError("stage IDs must not be empty")
        if len(set(self.stages)) != len(self.stages):
            raise ValueError("stage IDs must be unique")


LEGACY_GRAPH = StageGraph(
    "legacy",
    ("validate", "build", "simulate", "probe", "render", "composite", "encode", "package"),
)
BEHAVIOR_GRAPH = StageGraph("behavior", ("validate", "build", "simulate", "instrument", "package"))
LOOK_GRAPH = StageGraph("look", ("validate", "build", "look", "package"))
CAMERA_GRAPH = StageGraph("camera", ("validate", "build", "camera", "package"))
