# Study 002 — Mass Flow

Phase 2 scale-and-motion capability study. The first probe tests a deterministic
4,000-agent analytic flow in Houdini while keeping checkpoint and review data
bounded. Each agent also samples a deterministic window of nearby stable IDs and
uses a deterministic stable-ID cohort filtered by 3D distance for same-group
alignment, cohesion, and spacing while separating from other phases. Low deterministic
wander adds individual variation. It is an engineering and composition probe, not yet
a publication specimen.

The flow is volumetric: agents occupy a four-unit depth domain, follow an animated Z
component and phase-specific depth lanes, and perform cross-phase avoidance in 3D.

The visible sequence begins after a hidden 30-frame preroll, and motion-review trails
retain 25 checkpoints of history rather than the original five.

The Karma look renders all 4,000 simulated agents without population subsampling and
places a small phase-material sphere at each agent's latest cached position.
