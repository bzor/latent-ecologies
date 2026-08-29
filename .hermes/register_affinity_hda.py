from datetime import datetime, timezone
from pathlib import Path
from houdini_ai.studio_schema import validate_record
from houdini_ai.studio_store import StudioStore

root=Path(r'E:/Projects/houdini-ai')
store=StudioStore(root)
study_id='study-003-nonlocal-affinity-dance'
study=store.read('studies',study_id)
extensions=dict(study.get('extensions',{}))
extensions.update({
    'studio/behavior-hda': 'work/studio/handoffs/study-003-affinity-shallow3d-parallel-hda-v1/nonlocal-affinity-parallel.hda',
    'studio/behavior-hda-type': 'bzor::nonlocal_affinity_parallel::1.0',
    'studio/behavior-hda-receipt': 'work/studio/handoffs/study-003-affinity-shallow3d-parallel-hda-v1/handoff-receipt.json',
})
updated={
    **study,
    'recommended_next_action': 'Explore HDA variations against the frozen canonical defaults; promote any useful mutation as a new Behavior branch or continue to the Look Direction Workshop.',
    'updated_at': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z'),
    'extensions': extensions,
}
errors=validate_record('study',updated)
if errors:
    raise RuntimeError('; '.join(errors))
store.update('studies',study_id,updated)
print(updated['extensions']['studio/behavior-hda'])
