"""Build and verify the artist-editable Refractory Route Ecology SOP HDA.

Promotes the Study 001 Memory Field browser selects into the VEX-authoritative
Behavior HDA required by the artist-led Look handoff. The five select presets
carry embedded browser-exact initial states; changed identity parameters fall
back to a deterministic procedural regeneration of the same RNG contract.

Run under hython:

    hython houdini/build_refractory_route_hda.py \
        studies/001-memory-field/01_behavior/02_selects \
        studies/001-memory-field/01_behavior/03_promoted/receipts \
        studies/001-memory-field/01_behavior/03_promoted
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import hou

from houdini_ai.overlay_parameter_manifest import validate_overlay_parameter_manifest

TYPE_NAME = "bzor::refractory_route::1.0"
OPDEF_PREFIX = "opdef:/bzor::Sop/refractory_route::1.0"
ASSET_FILE = "refractory-route.hda"
DEMO_FILE = "refractory-route-demo.hiplc"

# Identity parameters: changing any of these creates a new deterministic
# identity (they feed the mulberry32 consumption order or initial velocities).
IDENTITY_PARMS = (
    "seed", "agent_count", "grid_width", "grid_height",
    "domain_width", "domain_height", "speed",
)
# birth_threshold exists in the prototype presets but only feeds browser event
# counters; it has no causal effect on state, so it is intentionally absent.
AGENT_STAGE_CHANNELS = (
    "domain_width", "domain_height", "rest_energy", "scar_threshold",
    "follow_threshold", "resource_attraction", "trace_follow", "scar_avoid",
    "scar_deflect", "crowd_radius", "crowd_avoid", "exploration",
    "boundary_steer", "turn_rate", "speed", "inertia", "consume_rate",
    "energy_gain", "energy_cost", "trace_deposit",
)
FIELD_STAGE_CHANNELS = (
    "trace_decay", "scar_trigger", "scar_growth", "idle_healing",
    "scar_decay", "heal_threshold", "resource_recovery",
)


def native(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def add_channel_parm(node: hou.Node, name: str, value: float, levels_up: int) -> None:
    group = node.parmTemplateGroup()
    group.append(hou.FloatParmTemplate(name, name.replace("_", " ").title(), 1, default_value=(float(value),)))
    node.setParmTemplateGroup(group)
    node.parm(name).setExpression("ch(\"" + "../" * levels_up + name + "\")", hou.exprLanguage.Hscript)


def overlay_parm(
    template: hou.ParmTemplate,
    key: str,
    units: str,
    comparison_range: tuple[float, float] | None = None,
) -> hou.ParmTemplate:
    tags = dict(template.tags())
    tags.update({"bzor_overlay_key": key, "bzor_overlay_units": units})
    if comparison_range is not None:
        tags["bzor_overlay_min"] = str(comparison_range[0])
        tags["bzor_overlay_max"] = str(comparison_range[1])
    template.setTags(tags)
    return template


def load_selects(selects_dir: Path, receipts_dir: Path) -> list[dict[str, Any]]:
    """Pair each select preset with its Node-exported receipt, ordered by filename."""
    selects: list[dict[str, Any]] = []
    for preset_path in sorted(selects_dir.glob("*.preset.json")):
        receipt_path = receipts_dir / (preset_path.name.replace(".preset.json", "") + ".receipt.json")
        if not receipt_path.exists():
            raise FileNotFoundError(f"missing Node receipt for {preset_path.name}: {receipt_path}")
        preset = json.loads(preset_path.read_text(encoding="utf-8"))
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt["seed"] != preset["seed"] or receipt["parameters"] != preset["parameters"]:
            raise ValueError(f"receipt does not match preset for {preset_path.name}")
        selects.append({
            "token": str(len(selects) + 1),
            "file": preset_path.name,
            "preset": preset,
            "receipt": receipt,
        })
    if len(selects) != 5:
        raise ValueError(f"expected exactly 5 selects, found {len(selects)}")
    return selects


def identity_of(select: dict[str, Any]) -> dict[str, float]:
    parameters = select["preset"]["parameters"]
    return {
        "seed": int(select["preset"]["seed"]),
        "agent_count": int(parameters["agent_count"]),
        "grid_width": int(parameters["grid_width"]),
        "grid_height": int(parameters["grid_height"]),
        "domain_width": float(parameters["domain_width"]),
        "domain_height": float(parameters["domain_height"]),
        "speed": float(parameters["speed"]),
    }


def build_initial_geometry(select: dict[str, Any], path: Path) -> None:
    """Freeze the browser-exact initial state (field + agents) as bgeo."""
    receipt = select["receipt"]["identity_receipt"]
    grid_width, grid_height = receipt["grid"]
    domain_width, domain_height = receipt["domain"]
    field_count = grid_width * grid_height
    resource = receipt["initial_field"]["resource"]
    agents = receipt["initial_agents"]
    if len(resource) != field_count:
        raise ValueError("initial field length does not match grid")

    geometry = hou.Geometry()
    positions: list[hou.Vector3] = []
    for gy in range(grid_height):
        y = ((gy + 0.5) / grid_height - 0.5) * domain_height
        for gx in range(grid_width):
            x = ((gx + 0.5) / grid_width - 0.5) * domain_width
            positions.append(hou.Vector3(x, y, 0.0))
    for agent in agents:
        positions.append(hou.Vector3(agent["position"][0], agent["position"][1], 0.0))
    geometry.createPoints(positions)

    for name, default in (
        ("resource", 0.0), ("resource_target", 0.0), ("fresh", 0.0), ("scar", 0.0),
        ("fresh_deposit", 0.0), ("consumption", 0.0),
        ("energy", 0.0), ("speed_profile", 0.0), ("turn_profile", 0.0),
        ("phase", 0.0), ("chirality", 0.0),
        ("deposit_fresh", 0.0), ("deposit_intake", 0.0),
    ):
        geometry.addAttrib(hou.attribType.Point, name, default)
    for name in ("v", "trace_dir", "dir_deposit", "deposit_dir"):
        geometry.addAttrib(hou.attribType.Point, name, hou.Vector3())
    for name, default in (
        ("idle_age", 0), ("healed", 0), ("occupancy", 0), ("occupancy_accum", 0),
        ("mode", 0), ("last_cell", -1), ("deposit_cell", 0),
    ):
        geometry.addAttrib(hou.attribType.Point, name, default)

    zeros_field = [0.0] * field_count
    geometry.setPointFloatAttribValues("resource", resource + [0.0] * len(agents))
    geometry.setPointFloatAttribValues("resource_target", resource + [0.0] * len(agents))
    geometry.setPointFloatAttribValues("energy", zeros_field + [agent["energy"] for agent in agents])
    geometry.setPointFloatAttribValues("speed_profile", zeros_field + [agent["speed_profile"] for agent in agents])
    geometry.setPointFloatAttribValues("turn_profile", zeros_field + [agent["turn_profile"] for agent in agents])
    geometry.setPointFloatAttribValues("phase", zeros_field + [agent["phase"] for agent in agents])
    geometry.setPointFloatAttribValues("chirality", zeros_field + [agent["chirality"] for agent in agents])
    velocities = [0.0] * (field_count * 3)
    for agent in agents:
        velocities.extend((agent["velocity"][0], agent["velocity"][1], 0.0))
    geometry.setPointFloatAttribValues("v", velocities)
    geometry.setPointIntAttribValues("last_cell", [-1] * (field_count + len(agents)))

    field_group = geometry.createPointGroup("field")
    agent_group = geometry.createPointGroup("agents")
    points = geometry.points()
    for point in points[:field_count]:
        field_group.add(point)
    for point in points[field_count:]:
        agent_group.add(point)

    for name, value in (
        ("simstep", 0),
        ("grid_width", grid_width), ("grid_height", grid_height),
        ("field_count", field_count), ("agent_count", len(agents)),
    ):
        geometry.addAttrib(hou.attribType.Global, name, 0)
        geometry.setGlobalAttribValue(name, value)
    geometry.addAttrib(hou.attribType.Global, "identity_source", "promoted-embedded-receipt")
    geometry.setGlobalAttribValue("identity_source", "promoted-embedded-receipt")

    path.parent.mkdir(parents=True, exist_ok=True)
    geometry.saveToFile(native(path))


AGENT_SNIPPET = r'''
function vector rr_gradient(string attrib; int cell; int gw; int gh) {
    int cx = cell % gw;
    int cy = cell / gw;
    float leftv = point(0, attrib, cy * gw + max(0, cx - 1));
    float rightv = point(0, attrib, cy * gw + min(gw - 1, cx + 1));
    float downv = point(0, attrib, max(0, cy - 1) * gw + cx);
    float upv = point(0, attrib, min(gh - 1, cy + 1) * gw + cx);
    return set(rightv - leftv, upv - downv, 0.0);
}

function vector rr_normalize(vector value; vector fallback) {
    float len = length(value);
    if (len > 1e-9) return value / len;
    return fallback;
}

function int rr_cell(float x; float y; float dw; float dh; int gw; int gh) {
    float nx = clamp(x / dw + 0.5, 0.0, 0.999999);
    float ny = clamp(y / dh + 0.5, 0.0, 0.999999);
    return int(floor(ny * gh)) * gw + int(floor(nx * gw));
}

int gw = detail(0, "grid_width");
int gh = detail(0, "grid_height");
int simstep = detail(0, "simstep");
float dw = chf("domain_width");
float dh = chf("domain_height");

float x = @P.x;
float y = @P.y;
vector vel = v@v;
int cell = rr_cell(x, y, dw, dh, gw, gh);
float fresh = point(0, "fresh", cell);
float scar = point(0, "scar", cell);

// Mode selection uses the previous step's state, exactly as the browser kernel.
int mode = 0;
if (f@energy < chf("rest_energy")) mode = 3;
else if (scar > chf("scar_threshold")) mode = 2;
// >= (not >): the browser kernel stores fresh as float32 but compares against
// the float64 parameter, so a deposit landing exactly at follow_threshold
// (e.g. trace_deposit == follow_threshold in the Drifting Foragers select)
// counts as above-threshold. VEX float32 comparison needs >= to reproduce it.
else if (fresh >= chf("follow_threshold")) mode = 1;
i@mode = mode;

if (cell != i@last_cell && point(0, "healed", cell) > 0) {
    setpointattrib(0, "healed", cell, 0, "set");
}
i@last_cell = cell;

vector rgrad = rr_gradient("resource", cell, gw, gh);
vector sgrad = rr_gradient("scar", cell, gw, gh);
vector steer = rgrad * chf("resource_attraction");
if (mode == 1) {
    vector tdir = point(0, "trace_dir", cell);
    steer += tdir * chf("trace_follow");
}
if (mode == 2) {
    float chirality = f@chirality;
    steer.x += -sgrad.x * chf("scar_avoid") - sgrad.y * chirality * chf("scar_deflect");
    steer.y += -sgrad.y * chf("scar_avoid") + sgrad.x * chirality * chf("scar_deflect");
}

float crowd_radius = max(chf("crowd_radius"), 1e-6);
vector crowd = 0;
int neighbors[] = nearpoints(0, "agents", @P, crowd_radius);
foreach (int other; neighbors) {
    if (other == @ptnum) continue;
    vector op = point(0, "P", other);
    float dx = x - op.x;
    float dy = y - op.y;
    float d2 = dx * dx + dy * dy;
    if (d2 > 1e-8 && d2 < crowd_radius * crowd_radius) {
        float weight = 1.0 - sqrt(d2) / crowd_radius;
        crowd.x += dx / d2 * weight;
        crowd.y += dy / d2 * weight;
    }
}
steer += crowd * chf("crowd_avoid");

float wander = f@phase + simstep * (0.021 + 0.006 * f@turn_profile);
steer.x += cos(wander) * chf("exploration");
steer.y += sin(wander) * chf("exploration");

float margin_x = dw * 0.08;
float margin_y = dh * 0.06;
float half_w = dw * 0.5;
float half_h = dh * 0.5;
float boundary = chf("boundary_steer");
if (x > half_w - margin_x) steer.x -= (x - (half_w - margin_x)) / margin_x * boundary;
if (x < -half_w + margin_x) steer.x += ((-half_w + margin_x) - x) / margin_x * boundary;
if (y > half_h - margin_y) steer.y -= (y - (half_h - margin_y)) / margin_y * boundary;
if (y < -half_h + margin_y) steer.y += ((-half_h + margin_y) - y) / margin_y * boundary;

vector current_dir = rr_normalize(vel, {1, 0, 0});
vector desired = rr_normalize(steer, current_dir);
float turn = clamp(chf("turn_rate") * f@turn_profile, 0.0, 1.0);
vector blended = rr_normalize(current_dir * (1.0 - turn) + desired * turn, current_dir);
float mode_scale = mode == 3 ? 0.28 : (mode == 2 ? 1.08 : 1.0);
float target_speed = chf("speed") * f@speed_profile * mode_scale;
float inertia = chf("inertia");
vector next_vel = vel * inertia + blended * target_speed * (1.0 - inertia);
float next_x = x + next_vel.x;
float next_y = y + next_vel.y;
if (next_x < -half_w || next_x > half_w) {
    next_x = clamp(next_x, -half_w, half_w);
    next_vel.x *= -0.85;
}
if (next_y < -half_h || next_y > half_h) {
    next_y = clamp(next_y, -half_h, half_h);
    next_vel.y *= -0.85;
}
@P = set(next_x, next_y, 0.0);
v@v = next_vel;

int next_cell = rr_cell(next_x, next_y, dw, dh, gw, gh);
float intake = min(point(0, "resource", next_cell), chf("consume_rate") * (mode == 3 ? 1.3 : 1.0));
f@energy = clamp(f@energy + intake * chf("energy_gain") - chf("energy_cost") * mode_scale, 0.0, 1.0);
float deposit_scale = mode == 3 ? 0.18 : (mode == 2 ? 0.45 : 1.0);
float deposit = chf("trace_deposit") * deposit_scale;
i@deposit_cell = next_cell;
f@deposit_fresh = deposit;
f@deposit_intake = intake;
v@deposit_dir = rr_normalize(next_vel, {1, 0, 0}) * deposit;
'''.strip() + "\n"


ACCUMULATE_SNIPPET = r'''
// Serial deposit accumulation: the only cross-agent write stage.
int agents[] = expandpointgroup(0, "agents");
foreach (int agent; agents) {
    int cell = point(0, "deposit_cell", agent);
    float fresh_dep = point(0, "deposit_fresh", agent);
    vector dir_dep = point(0, "deposit_dir", agent);
    float intake = point(0, "deposit_intake", agent);
    setpointattrib(0, "fresh_deposit", cell, fresh_dep, "add");
    setpointattrib(0, "dir_deposit", cell, dir_dep, "add");
    setpointattrib(0, "consumption", cell, intake, "add");
    setpointattrib(0, "occupancy_accum", cell, 1, "add");
}
setdetailattrib(0, "simstep", 1, "add");
'''.strip() + "\n"


FIELD_SNIPPET = r'''
float old_fresh = f@fresh;
float old_scar = f@scar;
int used = i@occupancy_accum > 0;
i@idle_age = used ? 0 : min(65535, i@idle_age + 1);
float trace_decay = chf("trace_decay");
float next_fresh = clamp(old_fresh * (1.0 - trace_decay) + f@fresh_deposit, 0.0, 1.0);
float scar_input = max(0.0, next_fresh - chf("scar_trigger")) * chf("scar_growth");
float age_boost = 1.0 + min(4.0, i@idle_age * chf("idle_healing"));
float next_scar = clamp(old_scar + scar_input - chf("scar_decay") * age_boost, 0.0, 1.0);
if (old_scar >= chf("heal_threshold") && next_scar < chf("heal_threshold") && i@idle_age > 8) {
    i@healed = 1;
}
float old_weight = old_fresh * (1.0 - trace_decay);
if (old_weight + f@fresh_deposit > 1e-8) {
    vector combined = v@trace_dir * old_weight + v@dir_deposit;
    float len = length(combined);
    v@trace_dir = len > 1e-9 ? combined / len : vector(0.0);
} else {
    v@trace_dir = 0;
}
f@fresh = next_fresh;
f@scar = next_scar;
float recovery = chf("resource_recovery") * (1.0 + max(0.0, old_scar - next_scar) * 2.0);
f@resource = clamp(f@resource - f@consumption + recovery * (f@resource_target - f@resource), 0.0, 1.0);
i@occupancy = i@occupancy_accum;
i@occupancy_accum = 0;
f@fresh_deposit = 0;
v@dir_deposit = 0;
f@consumption = 0;
'''.strip() + "\n"


DISPLAY_SNIPPET = r'''
// Viewport preview only: pscale/lift/colour are display conveniences, not Look
// decisions. Raw behavior attributes stay untouched for Look Development.
if (inpointgroup(0, "agents", @ptnum)) {
    if (chi("show_agents") == 0) {
        removepoint(0, @ptnum);
    }
    f@pscale = chf("agent_point_size");
    @P.z = chf("agent_lift");
    v@v *= chf("steps_per_frame") * chf("fps");
    if (chi("preview_color")) {
        vector colors[] = array(
            set(0.82, 0.9, 0.86), set(0.35, 1.0, 0.62),
            set(1.0, 0.48, 0.12), set(0.36, 0.5, 0.62));
        v@Cd = colors[i@mode];
    }
} else {
    f@pscale = chf("field_point_size");
    if (chi("preview_color")) {
        float freshv = clamp(f@fresh * 2.8, 0.0, 1.0);
        float scarv = clamp(f@scar * 4.0, 0.0, 1.0);
        v@Cd = clamp(set(
            0.015 + f@resource * 0.04 + scarv * 0.9,
            0.025 + f@resource * 0.25 + freshv * 0.68 + scarv * 0.2,
            0.04 + f@resource * 0.42 + freshv * 0.22), 0.0, 1.0);
    }
}
'''.strip() + "\n"


def procedural_generator_code(preset_identities: dict[str, dict[str, Any]]) -> str:
    template = r'''
import math

import hou

node = hou.pwd()
asset = node.parent()
geo = node.geometry()
source = node.inputs()[0].geometry()

PRESET_IDENTITIES = __PRESET_IDENTITIES__

token = asset.parm("preset").evalAsString()
current = {
    "seed": int(asset.evalParm("seed")) & 0xFFFFFFFF,
    "agent_count": int(asset.evalParm("agent_count")),
    "grid_width": int(asset.evalParm("grid_width")),
    "grid_height": int(asset.evalParm("grid_height")),
    "domain_width": float(asset.evalParm("domain_width")),
    "domain_height": float(asset.evalParm("domain_height")),
    "speed": float(asset.evalParm("speed")),
}
if current["agent_count"] < 2 or current["agent_count"] > 4096:
    raise hou.NodeError("Agent count must be between 2 and 4,096")
if not (8 <= current["grid_width"] <= 512 and 8 <= current["grid_height"] <= 512):
    raise hou.NodeError("Grid dimensions must be between 8 and 512")

canonical = PRESET_IDENTITIES.get(token)
matches = canonical is not None and all(
    (abs(current[key] - canonical[key]) <= 1e-12 if isinstance(canonical[key], float) else current[key] == canonical[key])
    for key in current
)

geo.clear()
if matches:
    geo.merge(source)
    geo.setGlobalAttribValue("identity_source", "promoted-embedded-receipt")
else:
    class Mulberry32:
        def __init__(self, value):
            self.state = value & 0xFFFFFFFF

        @staticmethod
        def imul(left, right):
            return ((left & 0xFFFFFFFF) * (right & 0xFFFFFFFF)) & 0xFFFFFFFF

        def random(self):
            self.state = (self.state + 0x6D2B79F5) & 0xFFFFFFFF
            value = self.state
            value = self.imul(value ^ (value >> 15), value | 1)
            value ^= (value + self.imul(value ^ (value >> 7), value | 61)) & 0xFFFFFFFF
            value &= 0xFFFFFFFF
            return ((value ^ (value >> 14)) & 0xFFFFFFFF) / 4294967296.0

    # RNG consumption order matches the browser kernel: five patches
    # (x, y, amplitude, radius), then each agent (x, y, heading,
    # speed profile, turn profile, phase, chirality).
    rng = Mulberry32(current["seed"])
    dw, dh = current["domain_width"], current["domain_height"]
    gw, gh = current["grid_width"], current["grid_height"]
    count = current["agent_count"]
    field_count = gw * gh
    patches = []
    for _ in range(5):
        patches.append({
            "x": (rng.random() - 0.5) * dw * 0.76,
            "y": (rng.random() - 0.5) * dh * 0.76,
            "amplitude": 0.48 + rng.random() * 0.42,
            "radius": 0.12 + rng.random() * 0.16,
        })
    resource = []
    positions = []
    for gy in range(gh):
        y = ((gy + 0.5) / gh - 0.5) * dh
        for gx in range(gw):
            x = ((gx + 0.5) / gw - 0.5) * dw
            value = 0.12
            for patch in patches:
                dx = x - patch["x"]
                dy = y - patch["y"]
                value += patch["amplitude"] * math.exp(-(dx * dx + dy * dy) / (2 * patch["radius"] * patch["radius"]))
            resource.append(min(1.0, max(0.0, value)))
            positions.append(hou.Vector3(x, y, 0.0))
    agents = []
    for _ in range(count):
        x = (rng.random() - 0.5) * dw * 0.88
        y = (rng.random() - 0.5) * dh * 0.88
        heading = rng.random() * math.pi * 2.0
        speed_profile = 0.82 + rng.random() * 0.34
        turn_profile = 0.78 + rng.random() * 0.44
        phase = rng.random() * math.pi * 2.0
        chirality = -1.0 if rng.random() < 0.5 else 1.0
        agents.append({
            "x": x, "y": y,
            "vx": math.cos(heading) * current["speed"] * speed_profile,
            "vy": math.sin(heading) * current["speed"] * speed_profile,
            "energy": 0.45 + 0.35 * math.sin(phase) ** 2,
            "speed_profile": speed_profile, "turn_profile": turn_profile,
            "phase": phase, "chirality": chirality,
        })
        positions.append(hou.Vector3(x, y, 0.0))
    geo.createPoints(positions)
    for name, default in (
        ("resource", 0.0), ("resource_target", 0.0), ("fresh", 0.0), ("scar", 0.0),
        ("fresh_deposit", 0.0), ("consumption", 0.0),
        ("energy", 0.0), ("speed_profile", 0.0), ("turn_profile", 0.0),
        ("phase", 0.0), ("chirality", 0.0),
        ("deposit_fresh", 0.0), ("deposit_intake", 0.0),
    ):
        geo.addAttrib(hou.attribType.Point, name, default)
    for name in ("v", "trace_dir", "dir_deposit", "deposit_dir"):
        geo.addAttrib(hou.attribType.Point, name, hou.Vector3())
    for name, default in (
        ("idle_age", 0), ("healed", 0), ("occupancy", 0), ("occupancy_accum", 0),
        ("mode", 0), ("last_cell", -1), ("deposit_cell", 0),
    ):
        geo.addAttrib(hou.attribType.Point, name, default)
    zeros_field = [0.0] * field_count
    geo.setPointFloatAttribValues("resource", resource + [0.0] * count)
    geo.setPointFloatAttribValues("resource_target", resource + [0.0] * count)
    geo.setPointFloatAttribValues("energy", zeros_field + [agent["energy"] for agent in agents])
    geo.setPointFloatAttribValues("speed_profile", zeros_field + [agent["speed_profile"] for agent in agents])
    geo.setPointFloatAttribValues("turn_profile", zeros_field + [agent["turn_profile"] for agent in agents])
    geo.setPointFloatAttribValues("phase", zeros_field + [agent["phase"] for agent in agents])
    geo.setPointFloatAttribValues("chirality", zeros_field + [agent["chirality"] for agent in agents])
    velocities = [0.0] * (field_count * 3)
    for agent in agents:
        velocities.extend((agent["vx"], agent["vy"], 0.0))
    geo.setPointFloatAttribValues("v", velocities)
    geo.setPointIntAttribValues("last_cell", [-1] * (field_count + count))
    field_group = geo.createPointGroup("field")
    agent_group = geo.createPointGroup("agents")
    points = geo.points()
    for point in points[:field_count]:
        field_group.add(point)
    for point in points[field_count:]:
        agent_group.add(point)
    for name, value in (
        ("simstep", 0),
        ("grid_width", gw), ("grid_height", gh),
        ("field_count", field_count), ("agent_count", count),
    ):
        geo.addAttrib(hou.attribType.Global, name, 0)
        geo.setGlobalAttribValue(name, value)
    geo.addAttrib(hou.attribType.Global, "identity_source", "")
    geo.setGlobalAttribValue("identity_source", "procedural-canvas-receipt")
'''
    return template.replace("__PRESET_IDENTITIES__", repr(preset_identities)).strip() + "\n"


def hda_python_module_source(selects: list[dict[str, Any]]) -> str:
    presets = {
        select["token"]: {
            "title": select["preset"]["title"],
            "seed": int(select["preset"]["seed"]),
            "parameters": select["preset"]["parameters"],
        }
        for select in selects
    }
    module = r'''
import hashlib
import json
import re
from pathlib import Path

import hou

PRESETS = __PRESETS__


def _reset(node):
    solver = node.node("solver/d")
    if solver is not None:
        solver.parm("resimulate").pressButton()


def apply_preset(node):
    token = node.parm("preset").evalAsString()
    preset = PRESETS.get(token)
    if preset is None:
        raise hou.NodeError("Unknown preset token: " + token)
    node.parm("seed").set(int(preset["seed"]))
    for name, value in preset["parameters"].items():
        parm = node.parm(name)
        if parm is not None:
            parm.set(value)
    _reset(node)


def _slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "untitled"


def _value(parm):
    type_name = str(parm.parmTemplate().type()).lower()
    if "toggle" in type_name:
        return bool(parm.eval())
    if "int" in type_name:
        return int(parm.eval())
    if "float" in type_name:
        return float(parm.eval())
    return parm.evalAsString()


def _value_type(parm):
    type_name = str(parm.parmTemplate().type()).lower()
    if "toggle" in type_name:
        return "toggle"
    if "int" in type_name:
        return "integer"
    if "float" in type_name:
        return "float"
    return "string"


def export_overlay_manifest(node):
    number = int(node.evalParm("overlay_variation_number"))
    title = node.evalParm("overlay_variation_title").strip()
    if number < 1 or number > 999:
        raise hou.NodeError("Overlay variation number must be between 1 and 999")
    if not title:
        raise hou.NodeError("Overlay variation title is required")

    parameters = []
    for parm in node.parms():
        tags = parm.parmTemplate().tags()
        key = tags.get("bzor_overlay_key")
        if not key:
            continue
        record = {
            "key": key,
            "label": parm.parmTemplate().label(),
            "parameter": parm.name(),
            "type": _value_type(parm),
            "value": _value(parm),
            "units": tags.get("bzor_overlay_units", "scalar"),
            "animated": bool(parm.isTimeDependent()),
        }
        if "bzor_overlay_min" in tags and "bzor_overlay_max" in tags:
            record["comparison_range"] = [float(tags["bzor_overlay_min"]), float(tags["bzor_overlay_max"])]
        parameters.append(record)

    hip_path = hou.hipFile.path()
    dirty = bool(hou.hipFile.hasUnsavedChanges())
    hip_sha256 = None
    hip_file = Path(hip_path)
    if hip_file.is_file() and not dirty:
        hip_sha256 = "sha256:" + hashlib.sha256(hip_file.read_bytes()).hexdigest()
    manifest = {
        "schema_version": 1,
        "variation": {
            "number": number,
            "title": title,
            "file_stem": "var_{:03d}_{}".format(number, _slug(title)),
        },
        "source": {
            "hip_path": hip_path,
            "hip_sha256": hip_sha256,
            "hip_dirty": dirty,
            "node_path": node.path(),
            "asset_type": node.type().name(),
            "frame": float(hou.frame()),
        },
        "parameters": parameters,
    }
    output = Path(node.parm("overlay_manifest_path").evalAsString())
    if output.suffix.lower() != ".json":
        raise hou.NodeError("Overlay manifest path must end in .json")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    node.setUserData("bzor_overlay_manifest", str(output))
    return manifest
'''
    return module.replace("__PRESETS__", repr(presets)).strip() + "\n"


def artist_parameter_group(selects: list[dict[str, Any]]) -> hou.ParmTemplateGroup:
    first = selects[0]["preset"]["parameters"]
    first_seed = int(selects[0]["preset"]["seed"])

    def dyn(name: str, minimum: float, maximum: float, key: str, units: str) -> hou.ParmTemplate:
        return overlay_parm(
            hou.FloatParmTemplate(name, name.replace("_", " ").title(), 1,
                                  default_value=(float(first[name]),), min=minimum, max=maximum),
            key, units, (minimum, maximum),
        )

    group = hou.ParmTemplateGroup()
    group.append(hou.LabelParmTemplate(
        "identity_notice", "Identity",
        column_labels=(
            "Selects embed browser-exact initial states. Changing seed, agent count, grid, "
            "domain, or speed regenerates a deterministic procedural identity; press Reset "
            "Simulation after identity changes.",
        ),
    ))

    identity = hou.FolderParmTemplate("identity", "Preset & Identity", folder_type=hou.folderType.Simple)
    preset = hou.StringParmTemplate(
        "preset", "Select Preset", 1, default_value=("1",),
        menu_items=tuple(select["token"] for select in selects),
        menu_labels=tuple(select["preset"]["title"] for select in selects),
        script_callback="kwargs['node'].hdaModule().apply_preset(kwargs['node'])",
        script_callback_language=hou.scriptLanguage.Python,
    )
    preset.setHelp("Applies the promoted select's full parameter set and resets the simulation.")
    identity.addParmTemplate(overlay_parm(preset, "behavior.preset", "token"))
    identity.addParmTemplate(overlay_parm(
        hou.IntParmTemplate("seed", "Deterministic Seed", 1, default_value=(first_seed,),
                            min=0, max=2147483647, min_is_strict=True, max_is_strict=True),
        "behavior.seed", "integer",
    ))
    identity.addParmTemplate(hou.ButtonParmTemplate(
        "new_seed", "New Seed",
        script_callback="import random; node = kwargs['node']; node.parm('seed').set(random.SystemRandom().randrange(0, 2147483648)); solver = node.node('solver/d'); solver.parm('resimulate').pressButton() if solver is not None else None",
        script_callback_language=hou.scriptLanguage.Python,
    ))
    identity.addParmTemplate(overlay_parm(
        hou.IntParmTemplate("agent_count", "Agent Count", 1, default_value=(int(first["agent_count"]),),
                            min=2, max=4096, min_is_strict=True, max_is_strict=True),
        "behavior.agent_count", "agents", (2, 4096),
    ))
    identity.addParmTemplate(hou.IntParmTemplate(
        "grid_width", "Grid Width", 1, default_value=(int(first["grid_width"]),),
        min=8, max=512, min_is_strict=True, max_is_strict=True))
    identity.addParmTemplate(hou.IntParmTemplate(
        "grid_height", "Grid Height", 1, default_value=(int(first["grid_height"]),),
        min=8, max=512, min_is_strict=True, max_is_strict=True))
    identity.addParmTemplate(hou.FloatParmTemplate(
        "domain_width", "Domain Width", 1, default_value=(float(first["domain_width"]),), min=0.6, max=4.0))
    identity.addParmTemplate(hou.FloatParmTemplate(
        "domain_height", "Domain Height", 1, default_value=(float(first["domain_height"]),), min=0.6, max=4.0))
    group.append(identity)

    movement = hou.FolderParmTemplate("movement", "Movement", folder_type=hou.folderType.Simple)
    movement.addParmTemplate(dyn("speed", 0.002, 0.03, "behavior.speed", "domain-units/step"))
    movement.addParmTemplate(dyn("inertia", 0.0, 0.99, "behavior.inertia", "coefficient"))
    movement.addParmTemplate(dyn("turn_rate", 0.01, 0.8, "behavior.turn_rate", "coefficient"))
    movement.addParmTemplate(dyn("exploration", 0.0, 1.0, "behavior.exploration", "coefficient"))
    movement.addParmTemplate(dyn("boundary_steer", 0.0, 8.0, "behavior.boundary_steer", "coefficient"))
    group.append(movement)

    sensing = hou.FolderParmTemplate("sensing", "Sensing & Steering", folder_type=hou.folderType.Simple)
    sensing.addParmTemplate(dyn("resource_attraction", 0.0, 8.0, "behavior.resource_attraction", "coefficient"))
    sensing.addParmTemplate(dyn("trace_follow", 0.0, 6.0, "behavior.trace_follow", "coefficient"))
    sensing.addParmTemplate(dyn("scar_avoid", 0.0, 8.0, "behavior.scar_avoid", "coefficient"))
    sensing.addParmTemplate(dyn("scar_deflect", 0.0, 6.0, "behavior.scar_deflect", "coefficient"))
    sensing.addParmTemplate(dyn("crowd_radius", 0.01, 0.15, "behavior.crowd_radius", "domain-units"))
    sensing.addParmTemplate(dyn("crowd_avoid", 0.0, 0.004, "behavior.crowd_avoid", "coefficient"))
    group.append(sensing)

    memory = hou.FolderParmTemplate("route_memory", "Route Memory", folder_type=hou.folderType.Simple)
    memory.addParmTemplate(dyn("trace_deposit", 0.001, 0.15, "behavior.trace_deposit", "per-step"))
    memory.addParmTemplate(dyn("trace_decay", 0.001, 0.2, "behavior.trace_decay", "per-step"))
    memory.addParmTemplate(dyn("follow_threshold", 0.01, 0.5, "behavior.follow_threshold", "field-value"))
    group.append(memory)

    scarring = hou.FolderParmTemplate("scarring", "Scar & Healing", folder_type=hou.folderType.Simple)
    scarring.addParmTemplate(dyn("scar_trigger", 0.0, 0.5, "behavior.scar_trigger", "field-value"))
    scarring.addParmTemplate(dyn("scar_growth", 0.0, 0.1, "behavior.scar_growth", "per-step"))
    scarring.addParmTemplate(dyn("scar_threshold", 0.01, 1.0, "behavior.scar_threshold", "field-value"))
    scarring.addParmTemplate(dyn("heal_threshold", 0.0, 0.5, "behavior.heal_threshold", "field-value"))
    scarring.addParmTemplate(dyn("scar_decay", 0.0001, 0.02, "behavior.scar_decay", "per-step"))
    scarring.addParmTemplate(dyn("idle_healing", 0.0, 0.1, "behavior.idle_healing", "per-step"))
    group.append(scarring)

    energy = hou.FolderParmTemplate("resource_energy", "Resource & Energy", folder_type=hou.folderType.Simple)
    energy.addParmTemplate(dyn("resource_recovery", 0.0, 0.02, "behavior.resource_recovery", "per-step"))
    energy.addParmTemplate(dyn("consume_rate", 0.0, 0.02, "behavior.consume_rate", "per-step"))
    energy.addParmTemplate(dyn("energy_gain", 0.0, 3.0, "behavior.energy_gain", "coefficient"))
    energy.addParmTemplate(dyn("energy_cost", 0.0, 0.03, "behavior.energy_cost", "per-step"))
    energy.addParmTemplate(dyn("rest_energy", 0.0, 0.95, "behavior.rest_energy", "energy"))
    group.append(energy)

    playback = hou.FolderParmTemplate("playback", "Playback", folder_type=hou.folderType.Simple)
    playback.addParmTemplate(overlay_parm(
        hou.IntParmTemplate("steps_per_frame", "Steps / Display Frame", 1, default_value=(2,),
                            min=1, max=12, min_is_strict=True, max_is_strict=True),
        "playback.steps_per_frame", "steps", (1, 12),
    ))
    playback.addParmTemplate(overlay_parm(
        hou.IntParmTemplate("start_frame", "Start Frame", 1, default_value=(1,),
                            min=1, max=100000, min_is_strict=True),
        "playback.start_frame", "frame",
    ))
    playback.addParmTemplate(hou.ButtonParmTemplate(
        "reset_simulation", "Reset Simulation",
        script_callback="node = kwargs['node']; solver = node.node('solver/d'); solver.parm('resimulate').pressButton() if solver is not None else None",
        script_callback_language=hou.scriptLanguage.Python,
    ))
    group.append(playback)

    display = hou.FolderParmTemplate("display", "Display", folder_type=hou.folderType.Simple)
    display.addParmTemplate(overlay_parm(
        hou.FloatParmTemplate("field_point_size", "Field Point Size", 1, default_value=(0.0085,),
                              min=0.0005, max=0.08, min_is_strict=True),
        "look.field_point_size", "houdini-units", (0.0005, 0.08),
    ))
    display.addParmTemplate(overlay_parm(
        hou.FloatParmTemplate("agent_point_size", "Agent Point Size", 1, default_value=(0.018,),
                              min=0.0005, max=0.1, min_is_strict=True),
        "look.agent_point_size", "houdini-units", (0.0005, 0.1),
    ))
    display.addParmTemplate(hou.FloatParmTemplate(
        "agent_lift", "Agent Z Lift", 1, default_value=(0.025,), min=0.0, max=0.2))
    display.addParmTemplate(hou.ToggleParmTemplate("show_agents", "Show Agents", default_value=True))
    preview = hou.ToggleParmTemplate("preview_color", "Preview Color", default_value=True)
    preview.setHelp("Diagnostic composite colour from the browser explorer. Disable for Look work.")
    display.addParmTemplate(preview)
    group.append(display)

    overlay = hou.FolderParmTemplate("overlay_detail", "Overlay Detail", folder_type=hou.folderType.Simple)
    overlay.addParmTemplate(hou.LabelParmTemplate(
        "overlay_notice", "Parameter Manifest",
        column_labels=("Exports curated Behavior and Look controls for the detail generator. Save the HIP first when a checksum-bound snapshot is required.",),
    ))
    overlay.addParmTemplate(hou.IntParmTemplate(
        "overlay_variation_number", "Variation Number", 1, default_value=(1,),
        min=1, max=999, min_is_strict=True, max_is_strict=True))
    overlay.addParmTemplate(hou.StringParmTemplate(
        "overlay_variation_title", "Variation Title", 1, default_value=("Primary Treatment",)))
    overlay.addParmTemplate(hou.StringParmTemplate(
        "overlay_manifest_path", "Manifest Path", 1,
        default_value=("$HIP/$HIPNAME.overlay-parameters.json",),
        string_type=hou.stringParmType.FileReference,
        file_type=hou.fileType.Any,
    ))
    overlay.addParmTemplate(hou.ButtonParmTemplate(
        "export_overlay_manifest", "Export Overlay Parameter Manifest",
        script_callback="kwargs['node'].hdaModule().export_overlay_manifest(kwargs['node'])",
        script_callback_language=hou.scriptLanguage.Python,
    ))
    group.append(overlay)
    return group


def build_network(parent: hou.Node, selects: list[dict[str, Any]], state_dir: Path) -> hou.Node:
    subnet = parent.createNode("subnet", "REFRACTORY_ROUTE")
    subnet.setParmTemplateGroup(artist_parameter_group(selects))

    source = subnet.createNode("file", "EMBEDDED_PROMOTED_INITIAL_STATE")
    source.parm("file").set(native(state_dir / "initial-state-1.bgeo.sc"))

    preset_identities = {select["token"]: identity_of(select) for select in selects}
    generator = subnet.createNode("python", "PREPARE_IDENTITY_RECEIPT")
    generator.setInput(0, source)
    generator.parm("python").set(procedural_generator_code(preset_identities))
    generator.parm("maintainstate").set(False)

    solver = subnet.createNode("solver", "solver")
    solver.allowEditingOfContents(propagate=True)
    solver.setInput(0, generator)
    solver.parm("startframe").setExpression('ch("../start_frame") + 1', hou.exprLanguage.Hscript)
    solver.parm("substep").set(1)
    sopsolver = solver.node("d/s")
    if sopsolver is None:
        raise RuntimeError("Solver SOP has no internal SOP Solver")
    previous = sopsolver.node("Prev_Frame")
    output = sopsolver.node("OUT")
    if previous is None or output is None:
        raise RuntimeError("Solver SOP feedback nodes are unavailable")

    agents = sopsolver.createNode("attribwrangle", "AGENT_SENSE_MOVE_DEPOSIT")
    agents.setInput(0, previous)
    agents.parm("class").set("point")
    agents.parm("group").set("agents")
    agents.parm("grouptype").set("points")
    agents.parm("snippet").set(AGENT_SNIPPET)
    first = selects[0]["preset"]["parameters"]
    for name in AGENT_STAGE_CHANNELS:
        add_channel_parm(agents, name, float(first[name]), 4)

    accumulate = sopsolver.createNode("attribwrangle", "ACCUMULATE_DEPOSITS_SERIAL")
    accumulate.setInput(0, agents)
    accumulate.parm("class").set("detail")
    accumulate.parm("snippet").set(ACCUMULATE_SNIPPET)

    field = sopsolver.createNode("attribwrangle", "FIELD_AGE_SCAR_HEAL")
    field.setInput(0, accumulate)
    field.parm("class").set("point")
    field.parm("group").set("field")
    field.parm("grouptype").set("points")
    field.parm("snippet").set(FIELD_SNIPPET)
    for name in FIELD_STAGE_CHANNELS:
        add_channel_parm(field, name, float(first[name]), 4)
    output.setInput(0, field)

    cadence = subnet.createNode("timeshift", "STEPS_PER_DISPLAY_FRAME")
    cadence.setInput(0, solver)
    cadence.parm("frame").setExpression(
        'ch("../start_frame") + ($F - ch("../start_frame")) * ch("../steps_per_frame")',
        hou.exprLanguage.Hscript,
    )
    switch = subnet.createNode("switch", "OUTPUT_INITIAL_OR_SIMULATION")
    switch.setInput(0, generator)
    switch.setInput(1, cadence)
    switch.parm("input").setExpression('$F >= ch("../start_frame") + 1', hou.exprLanguage.Hscript)

    display = subnet.createNode("attribwrangle", "DISPLAY_PREVIEW_CONTROLS")
    display.setInput(0, switch)
    display.parm("class").set("point")
    display.parm("snippet").set(DISPLAY_SNIPPET)
    for name, value in (
        ("agent_point_size", 0.018), ("field_point_size", 0.0085), ("agent_lift", 0.025),
    ):
        add_channel_parm(display, name, value, 1)
    group = display.parmTemplateGroup()
    for name, default in (("show_agents", 1), ("preview_color", 1), ("steps_per_frame", 2)):
        group.append(hou.IntParmTemplate(name, name.replace("_", " ").title(), 1, default_value=(default,)))
    group.append(hou.FloatParmTemplate("fps", "Fps", 1, default_value=(24.0,)))
    display.setParmTemplateGroup(group)
    for name in ("show_agents", "preview_color", "steps_per_frame"):
        display.parm(name).setExpression(f'ch("../{name}")', hou.exprLanguage.Hscript)
    display.parm("fps").setExpression("$FPS", hou.exprLanguage.Hscript)

    final = subnet.createNode("null", "OUTPUT_BEHAVIOR_POINTS")
    final.setInput(0, display)
    final.setDisplayFlag(True)
    final.setRenderFlag(True)

    for index, node in enumerate((source, generator, solver, cadence, switch, display, final)):
        node.setPosition(hou.Vector2(0, -1.5 * index))
    subnet.setColor(hou.Color((0.42, 0.26, 0.55)))
    return subnet


def node_errors(node: hou.Node) -> list[str]:
    errors: list[str] = []
    for child in (node, *node.allSubChildren()):
        errors.extend(f"{child.path()}: {error}" for error in child.errors())
    return errors


def agent_state(geometry: hou.Geometry, field_count: int) -> dict[str, list[float]]:
    positions = list(geometry.pointFloatAttribValues("P"))
    energies = list(geometry.pointFloatAttribValues("energy"))
    modes = list(geometry.pointIntAttribValues("mode"))
    agents_xy: list[float] = []
    for index in range(field_count, len(energies)):
        agents_xy.extend(positions[index * 3:index * 3 + 2])
    return {
        "positions": agents_xy,
        "energies": energies[field_count:],
        "modes": [float(value) for value in modes[field_count:]],
    }


def field_stats(geometry: hou.Geometry, field_count: int) -> dict[str, float]:
    fresh = geometry.pointFloatAttribValues("fresh")[:field_count]
    scar = geometry.pointFloatAttribValues("scar")[:field_count]
    resource = geometry.pointFloatAttribValues("resource")[:field_count]
    return {
        "freshMax": max(fresh), "scarMax": max(scar),
        "resourceMin": min(resource), "resourceMax": max(resource),
    }


def max_abs_delta(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError(f"length mismatch: {len(left)} vs {len(right)}")
    return max((abs(a - b) for a, b in zip(left, right)), default=0.0)


def audit_preset(node: hou.Node, select: dict[str, Any]) -> dict[str, Any]:
    receipt = select["receipt"]
    identity = receipt["identity_receipt"]
    field_count = identity["grid"][0] * identity["grid"][1]
    node.parm("preset").set(select["token"])
    node.hdaModule().apply_preset(node)
    node.parm("steps_per_frame").set(1)
    node.parm("reset_simulation").pressButton()

    hou.setFrame(1)
    node.cook(force=True)
    geometry = node.geometry()
    if geometry is None:
        raise RuntimeError(f"preset {select['token']} produced no initial geometry")
    if geometry.attribValue("identity_source") != "promoted-embedded-receipt":
        raise RuntimeError(f"preset {select['token']} did not load the embedded receipt: {geometry.attribValue('identity_source')}")
    initial = agent_state(geometry, field_count)
    expected_positions = [component for agent in identity["initial_agents"] for component in agent["position"]]
    expected_energies = [agent["energy"] for agent in identity["initial_agents"]]
    initial_position_delta = max_abs_delta(initial["positions"], expected_positions)
    initial_energy_delta = max_abs_delta(initial["energies"], expected_energies)
    resource_delta = max_abs_delta(
        list(geometry.pointFloatAttribValues("resource")[:field_count]),
        identity["initial_field"]["resource"],
    )
    if initial_position_delta > 1e-6 or initial_energy_delta > 1e-6 or resource_delta > 1e-6:
        raise RuntimeError(
            f"preset {select['token']} embedded initial state mismatch: "
            f"P {initial_position_delta}, energy {initial_energy_delta}, resource {resource_delta}"
        )

    parity_report = []
    for snapshot in receipt["parity_trace"]["snapshots"]:
        hou.setFrame(snapshot["step"] + 1)
        node.cook(force=True)
        geometry = node.geometry()
        state = agent_state(geometry, field_count)
        mode_matches = sum(
            1 for ours, theirs in zip(state["modes"], snapshot["modes"]) if int(ours) == int(theirs)
        )
        parity_report.append({
            "step": snapshot["step"],
            "max_position_delta": max_abs_delta(state["positions"], snapshot["positions"]),
            "max_energy_delta": max_abs_delta(state["energies"], snapshot["energies"]),
            "mode_agreement": mode_matches / len(snapshot["modes"]),
            "field": field_stats(geometry, field_count),
            "field_reference": snapshot["field"],
        })
    step_one = next(entry for entry in parity_report if entry["step"] == 1)
    step_six = next(entry for entry in parity_report if entry["step"] == 6)
    if step_one["max_position_delta"] > 1e-4 or step_six["max_position_delta"] > 5e-3:
        raise RuntimeError(f"preset {select['token']} diverges from the browser reference too early: {parity_report}")

    horizon = receipt["structural_horizon"]
    hou.setFrame(horizon["steps"] + 1)
    node.cook(force=True)
    geometry = node.geometry()
    stats = field_stats(geometry, field_count)
    state = agent_state(geometry, field_count)
    # Positions clamp to exactly +/- half-domain; allow float32 rounding of the bound.
    domain_half_w = float(identity["domain"][0]) * 0.5 + 1e-6
    domain_half_h = float(identity["domain"][1]) * 0.5 + 1e-6
    xs = state["positions"][0::2]
    ys = state["positions"][1::2]
    finite = all(math.isfinite(value) for value in state["positions"])
    in_bounds = all(-domain_half_w <= x <= domain_half_w for x in xs) and all(-domain_half_h <= y <= domain_half_h for y in ys)
    reference = horizon["field"]
    structural = {
        "steps": horizon["steps"],
        "field": stats,
        "field_reference": {key: reference[key] for key in ("freshMax", "scarMax", "resourceMin", "resourceMax")},
        "positions_finite": finite,
        "positions_in_bounds": in_bounds,
        "mode_histogram": {str(mode): state["modes"].count(float(mode)) for mode in range(4)},
        "reference_mode_counts": horizon["mode_counts"],
    }
    ratio_ok = (
        0.5 <= stats["freshMax"] / max(reference["freshMax"], 1e-6) <= 2.0
        and 0.5 <= stats["scarMax"] / max(reference["scarMax"], 1e-6) <= 2.0
    )
    if not (finite and in_bounds and ratio_ok):
        raise RuntimeError(f"preset {select['token']} failed structural checks: {structural}")

    return {
        "token": select["token"],
        "title": select["preset"]["title"],
        "source_preset": select["file"],
        "initial_state": {
            "max_position_delta": initial_position_delta,
            "max_energy_delta": initial_energy_delta,
            "max_resource_delta": resource_delta,
        },
        "parity": parity_report,
        "structural": structural,
    }


def run(selects_dir: Path, receipts_dir: Path, output: Path) -> dict[str, Any]:
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    selects = load_selects(selects_dir, receipts_dir)

    state_dir = output / "initial-states"
    for select in selects:
        build_initial_geometry(select, state_dir / f"initial-state-{select['token']}.bgeo.sc")

    hda_path = output / ASSET_FILE
    hip_path = output / DEMO_FILE
    if hda_path.exists():
        hda_path.unlink()

    hou.hipFile.clear(suppress_save_prompt=True)
    container = hou.node("/obj").createNode("geo", "REFRACTORY_ROUTE_PLAYGROUND")
    for child in container.children():
        child.destroy()
    subnet = build_network(container, selects, state_dir)
    asset = subnet.createDigitalAsset(
        name=TYPE_NAME,
        hda_file_name=native(hda_path),
        description="Bzor Refractory Route Ecology",
        min_num_inputs=0,
        max_num_inputs=0,
        save_as_embedded=False,
    )
    definition = asset.type().definition()
    if definition is None:
        raise RuntimeError("HDA definition was not created")
    for select in selects:
        state_path = state_dir / f"initial-state-{select['token']}.bgeo.sc"
        definition.addSection(f"InitialState_{select['token']}.bgeo.sc", state_path.read_bytes())
    asset.allowEditingOfContents()
    embedded_source = asset.node("EMBEDDED_PROMOTED_INITIAL_STATE")
    if embedded_source is None:
        raise RuntimeError("embedded initial-state node is unavailable")
    embedded_source.parm("file").set(f"{OPDEF_PREFIX}?InitialState_`chs(\"../preset\")`.bgeo.sc")
    definition.updateFromNode(asset)
    definition.setParmTemplateGroup(artist_parameter_group(selects))
    definition.addSection("PythonModule", hda_python_module_source(selects))
    asset.matchCurrentDefinition()
    hou.setFrame(1)
    asset.cook(force=True)
    hou.hipFile.save(native(hip_path))

    # Fresh-session audit: the HDA must reopen, cook, and match the promoted
    # browser behavior from nothing but the installed asset file.
    hou.hipFile.clear(suppress_save_prompt=True)
    hou.hda.installFile(native(hda_path))
    audit_container = hou.node("/obj").createNode("geo", "HDA_FRESH_SESSION_AUDIT")
    for child in audit_container.children():
        child.destroy()
    audit_node = audit_container.createNode(TYPE_NAME, "REFRACTORY_ROUTE")
    preset_audits = [audit_preset(audit_node, select) for select in selects]
    audit_errors = node_errors(audit_node)
    if audit_errors:
        raise RuntimeError(f"fresh-session audit reported node errors: {audit_errors}")

    # Procedural identity probe: a changed seed must produce a distinct,
    # finite, regenerated identity.
    audit_node.parm("preset").set("1")
    audit_node.hdaModule().apply_preset(audit_node)
    audit_node.parm("seed").set((int(selects[0]["preset"]["seed"]) + 1) & 0x7FFFFFFF)
    audit_node.parm("agent_count").set(24)
    audit_node.parm("reset_simulation").pressButton()
    hou.setFrame(1)
    audit_node.cook(force=True)
    procedural_geometry = audit_node.geometry()
    procedural_source = procedural_geometry.attribValue("identity_source")
    procedural_agents = procedural_geometry.attribValue("agent_count")
    hou.setFrame(4)
    audit_node.cook(force=True)
    stepped = audit_node.geometry()
    procedural_probe = {
        "identity_source": procedural_source,
        "agent_count": procedural_agents,
        "simstep_at_frame_4": int(stepped.attribValue("simstep")),
        "positions_finite": all(math.isfinite(value) for value in stepped.pointFloatAttribValues("P")),
        "node_errors": node_errors(audit_node),
    }
    if (
        procedural_source != "procedural-canvas-receipt"
        or procedural_agents != 24
        or procedural_probe["simstep_at_frame_4"] != 3
        or not procedural_probe["positions_finite"]
        or procedural_probe["node_errors"]
    ):
        raise RuntimeError(f"procedural identity probe failed: {procedural_probe}")

    manifest_path = output / "audit-overlay-parameter-manifest.json"
    audit_node.parm("preset").set("1")
    audit_node.hdaModule().apply_preset(audit_node)
    audit_node.parm("overlay_variation_number").set(1)
    audit_node.parm("overlay_variation_title").set("Braided Deflection")
    audit_node.parm("overlay_manifest_path").set(native(manifest_path))
    audit_node.parm("export_overlay_manifest").pressButton()
    exported_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_errors = validate_overlay_parameter_manifest(exported_manifest)
    if manifest_errors:
        raise RuntimeError("HDA overlay parameter manifest failed validation: " + "; ".join(manifest_errors))

    audit = {
        "schema_version": 1,
        "asset_type": TYPE_NAME,
        "asset_file": ASSET_FILE,
        "demo_hip": DEMO_FILE,
        "state_authority": "vex-geometry",
        "mechanism": "refractory-route-ecology-v1",
        "study_id": "study-001-memory-field",
        "handoff_contract": "live-hda",
        "identity_parameters": list(IDENTITY_PARMS),
        "presets": preset_audits,
        "procedural_identity_probe": procedural_probe,
        "overlay_parameter_manifest_probe": {
            "variation": exported_manifest["variation"],
            "parameter_keys": [parameter["key"] for parameter in exported_manifest["parameters"]],
            "path": native(manifest_path),
        },
        "interactive_semantics": (
            "frame 1 is the embedded initial state; with Steps / Display Frame = S, "
            "frame N+1 contains N x S synchronous steps"
        ),
        "parity_semantics": (
            "browser kernel computes in float64 and stores float32; VEX computes in float32. "
            "Initial states are browser-exact; trajectories are audited against the browser "
            "reference at steps 1/6/12/24 and structurally at step 120. birth_threshold is "
            "event-diagnostic only in the prototype and is intentionally absent from the HDA."
        ),
        "ordered_events": "parallel agent stage, serial deposit accumulation, parallel field stage",
        "node_errors": audit_errors,
    }
    (output / "audit.json").write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(audit, sort_keys=True))
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("selects", type=Path)
    parser.add_argument("receipts", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    run(args.selects.resolve(), args.receipts.resolve(), args.output)


if __name__ == "__main__":
    main()
