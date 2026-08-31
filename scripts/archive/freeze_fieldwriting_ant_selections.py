from __future__ import annotations

import json
from pathlib import Path

from houdini_ai.fieldwriting_ants import simulate_chiral_highway_pair, simulate_collision_colony
from houdini_ai.fieldwriting_ants_selection import freeze_fieldwriting_behavior

ROOT = Path(__file__).resolve().parents[1]
ROBUSTNESS = (
    ROOT
    / "studies"
    / "study_004_three-dimensional-fieldwriting-ants"
    / "01_behavior"
    / "01_work"
    / "06_A3-C2-robustness"
)
AUTHORIZATION_MESSAGE_ID = "1540841497015091301"


def main() -> None:
    a3 = simulate_chiral_highway_pair(
        "RLRUUUL",
        steps=20_000,
        snapshot_interval=500,
        initial_agents=(
            ((-2, 0, 0), (0, 1, 0), (0, 0, 1)),
            ((2, 0, 0), (0, 1, 0), (0, 0, 1)),
        ),
    )
    c2 = simulate_collision_colony(
        "RLRU",
        steps=1_200,
        snapshot_interval=20,
        collision_policy="frame-exchange",
        initial_agents=(
            ((3, 0, 0), (-1, 0, 0), (0, 0, 1)),
            ((-3, 0, 0), (1, 0, 0), (0, 0, 1)),
            ((0, 3, 0), (0, -1, 0), (0, 0, 1)),
            ((0, -3, 0), (0, 1, 0), (0, 0, 1)),
            ((0, 0, 3), (0, 0, -1), (0, 1, 0)),
            ((0, 0, -3), (0, 0, 1), (0, 1, 0)),
        ),
    )
    frozen = [
        freeze_fieldwriting_behavior(
            ROOT,
            selection_id="selection-a3-gap-4",
            branch_id="A3-gap-4",
            result=a3,
            source_media={
                "motion-timelapse.mp4": ROBUSTNESS / "01_A3" / "gap-4" / "motion-timelapse.mp4",
                "contact-sheet.png": ROBUSTNESS / "01_A3" / "gap-4" / "contact-sheet.png",
            },
            rationale="KC approved A3 gap-4 as the canonical mirrored chiral shared-field highway Behavior.",
            authorization_message_id=AUTHORIZATION_MESSAGE_ID,
        ),
        freeze_fieldwriting_behavior(
            ROOT,
            selection_id="selection-c2-radius-3",
            branch_id="C2-radius-3",
            result=c2,
            source_media={
                "motion-timelapse.mp4": ROBUSTNESS / "02_C2" / "radius-3" / "motion-timelapse.mp4",
                "contact-sheet.png": ROBUSTNESS / "02_C2" / "radius-3" / "contact-sheet.png",
            },
            rationale="KC approved C2 radius-3 as the canonical synchronous frame-exchange collision-chemistry Behavior.",
            authorization_message_id=AUTHORIZATION_MESSAGE_ID,
        ),
    ]
    print(
        json.dumps(
            [
                {
                    "selection_directory": str(item["selection_directory"]),
                    "component_id": item["component"]["id"],
                    "artifact_id": item["artifact"]["id"],
                }
                for item in frozen
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
