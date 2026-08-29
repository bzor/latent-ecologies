from __future__ import annotations

import json
from pathlib import Path

from houdini_ai.fieldwriting_ants import DirectionResult, simulate_collision_colony
from houdini_ai.fieldwriting_ants_c2_options import c2_compact_configurations
from houdini_ai.fieldwriting_ants_selection import freeze_fieldwriting_behavior

ROOT = Path(__file__).resolve().parents[1]
ROUND = (
    ROOT
    / "studies"
    / "study_004_three-dimensional-fieldwriting-ants"
    / "01_behavior"
    / "01_work"
    / "11_C2-prewarmed-options"
    / "01_radius-2-control"
)
AUTHORIZATION_MESSAGE_ID = "1541188371026546759"


def build_c2_radius2_selection_result() -> DirectionResult:
    configuration = c2_compact_configurations()["radius-2-control"]
    return simulate_collision_colony(
        "RLRU",
        steps=1_200,
        snapshot_interval=10,
        collision_policy="frame-exchange",
        initial_agents=configuration["initial_agents"],
    )


def main() -> None:
    frozen = freeze_fieldwriting_behavior(
        ROOT,
        selection_id="selection-c2-radius-2",
        branch_id="C2-radius-2",
        result=build_c2_radius2_selection_result(),
        source_media={
            "motion-timelapse.mp4": ROUND / "motion-timelapse.mp4",
            "contact-sheet.png": ROUND / "contact-sheet.png",
            "projection-sheet.png": ROUND / "projection-sheet.png",
        },
        rationale=(
            "KC promoted the exact C2 radius-2 compact control as an additional synchronous "
            "frame-exchange Behavior source for Look Development. Existing promoted selections remain intact."
        ),
        authorization_message_id=AUTHORIZATION_MESSAGE_ID,
    )
    print(
        json.dumps(
            {
                "selection_directory": str(frozen["selection_directory"]),
                "component_id": frozen["component"]["id"],
                "artifact_id": frozen["artifact"]["id"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
