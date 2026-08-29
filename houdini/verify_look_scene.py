from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import traceback
from pathlib import Path
from typing import Any

import hou
from pxr import UsdShade

_CACHE_FRAME = re.compile(r"\.(\d+)\.bgeo(?:\.sc)?$")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _node_type(node: hou.Node) -> str:
    return node.type().name()


def _stage_audit(
    stage: dict[str, Any],
    planned_paths: set[str],
    *,
    require_output_flag: bool,
) -> dict[str, Any]:
    stage_id = stage["id"]
    specs = stage["nodes"]
    nodes: list[hou.Node] = []
    errors: list[str] = []
    actual: list[dict[str, str]] = []
    for index, spec in enumerate(specs):
        node = hou.node(spec["path"])
        if node is None:
            errors.append(f"{stage_id}: missing node {spec['path']}")
            continue
        nodes.append(node)
        actual_type = _node_type(node)
        declared_inputs = spec.get("inputs")
        if declared_inputs is None:
            declared_inputs = [] if index == 0 else [specs[index - 1]["path"]]
        actual.append({
            "path": node.path(),
            "type": actual_type,
            "role": spec["role"],
            "inputs": list(declared_inputs),
        })
        if actual_type != spec["type"]:
            errors.append(
                f"{stage_id}: node {node.path()} has type {actual_type}, expected {spec['type']}"
            )

        actual_inputs = [
            source.path()
            for source in node.inputs()
            if source is not None and source.path() in planned_paths
        ]
        if actual_inputs != list(declared_inputs):
            errors.append(
                f"{stage_id}: declared inputs do not match the reopened graph for {node.path()}: "
                f"expected {list(declared_inputs)}, measured {actual_inputs}"
            )

    output = hou.node(stage["output_node"])
    if output is None:
        errors.append(f"{stage_id}: missing output node {stage['output_node']}")
    elif specs[-1]["path"] != output.path():
        errors.append(f"{stage_id}: output_node must be the final planned node")
    else:
        try:
            output.cook(force=True)
        except hou.Error as error:
            errors.append(f"{stage_id}: output cook failed: {error}")
        errors.extend(f"{stage_id}: {message}" for message in output.errors())

    for control in stage["artist_controls"]:
        node = hou.node(control["node_path"])
        if node is None or node.parm(control["parm"]) is None:
            errors.append(
                f"{stage_id}: missing artist control {control['node_path']}/{control['parm']}"
            )

    display_flag = False
    render_flag = False
    if output is not None:
        try:
            display_flag = bool(output.isDisplayFlagSet())
        except (hou.OperationFailed, AttributeError):
            pass
        try:
            render_flag = bool(output.isRenderFlagSet())
        except (hou.OperationFailed, AttributeError):
            pass
    if require_output_flag and output is not None and not (display_flag or render_flag):
        errors.append(f"{stage_id}: output node has neither display nor render flag")

    return {
        "stage_id": stage_id,
        "network_section": stage["network_section"],
        "nodes": actual,
        "output_node": stage["output_node"],
        "display_flag": display_flag,
        "render_flag": render_flag,
        "output_flag_required": require_output_flag,
        "errors": errors,
    }


_RENDER_TYPES = {
    "look_import": "sopimport",
    "material_library": "materiallibrary",
    "material_assignment": "assignmaterial",
    "neutral_camera": "camera",
    "hero_camera": "camera",
    "neutral_dome": "domelight",
    "hero_key": "distantlight",
    "hero_fill": "distantlight",
    "hero_rim": "distantlight",
    "lighting_selector": "switch",
    "render_settings": "karmarendersettings",
    "render_output": "usdrender_rop",
}


def _upstream_nodes(node: hou.Node) -> set[hou.Node]:
    found: set[hou.Node] = set()
    pending = [source for source in node.inputs() if source is not None]
    while pending:
        source = pending.pop()
        if source in found:
            continue
        found.add(source)
        pending.extend(item for item in source.inputs() if item is not None)
    return found


def _source_cache_audit(plan: dict[str, Any], plan_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    records: list[dict[str, Any]] = []
    receipt = plan.get("source_cache_receipt")
    if not isinstance(receipt, list) or not receipt:
        return {"passed": False, "records": [], "errors": ["source cache receipt is missing"]}
    by_frame = {
        int(match.group(1)): record
        for record in receipt
        if isinstance(record, dict)
        and (match := _CACHE_FRAME.search(str(record.get("path", "")))) is not None
    }
    render_setup = plan.get("render_setup", {})
    review_frames = sorted(set([
        *render_setup.get("neutral_frames", {}).values(),
        *render_setup.get("motion_frames", []),
    ]))
    if any(frame not in by_frame for frame in review_frames):
        errors.append("source cache receipt does not cover every rendered review frame")
    try:
        project_root = Path(str(plan["project_root"])).resolve(strict=True)
        plan_path.resolve().relative_to(project_root)
    except (KeyError, OSError, ValueError) as error:
        errors.append(f"source cache project root is invalid: {error}")
        project_root = None
    if project_root is not None and not all(
        (project_root / str(record["path"])).is_file() for record in receipt
    ):
        errors.append("source cache files are not present beneath the canonical project root")
        project_root = None

    planned_file_nodes: list[hou.Node] = []
    for stage in plan.get("stages", []):
        for node_spec in stage.get("nodes", []):
            if str(node_spec.get("type", "")).split("::", 1)[0] == "file":
                node = hou.node(str(node_spec.get("path", "")))
                if node is not None:
                    planned_file_nodes.append(node)
    stages = plan.get("stages", [])
    final_output = hou.node(stages[-1]["output_node"]) if stages else None
    upstream = _upstream_nodes(final_output) if final_output is not None else set()
    topological_cache_nodes = [node for node in planned_file_nodes if node in upstream]
    if not topological_cache_nodes:
        errors.append("rendered Look output has no planned upstream frozen-cache File SOP")
    import_path = render_setup.get("nodes", {}).get("look_import")
    look_import = hou.node(import_path) if isinstance(import_path, str) else None
    sop_parm = look_import.parm("soppath") if look_import is not None else None

    if project_root is not None:
        for frame in review_frames:
            record = by_frame.get(frame)
            if record is None:
                continue
            expected_path = (project_root / str(record["path"])).resolve()
            if expected_path.stat().st_size != record.get("bytes") or _sha256(expected_path) != record.get("sha256"):
                errors.append(f"frozen source cache metadata mismatch at frame {frame}")
                continue
            hou.setFrame(frame)
            try:
                final_output.cook(force=True)
                active_upstream = set(final_output.inputAncestors(
                    include_ref_inputs=False,
                    follow_subnets=True,
                    only_used_inputs=True,
                ))
            except hou.Error as error:
                errors.append(f"final Look SOP active-input cook failed at frame {frame}: {error}")
                active_upstream = set()
            cache_nodes = [node for node in topological_cache_nodes if node in active_upstream]
            evaluated_import = sop_parm.evalAsString() if sop_parm is not None else ""
            import_bound = final_output is not None and hou.node(evaluated_import) == final_output
            if not import_bound:
                errors.append(
                    f"Solaris Look import is not bound to the verified final SOP output at frame {frame}"
                )
            matched_nodes = []
            for node in cache_nodes:
                file_parm = node.parm("file")
                if file_parm is not None and Path(file_parm.evalAsString()).resolve() == expected_path:
                    matched_nodes.append(node.path())
            if not matched_nodes:
                errors.append(f"no actively cooked File SOP resolves to the frozen cache at frame {frame}")
            records.append({
                "frame": frame,
                "path": str(expected_path),
                "bytes": expected_path.stat().st_size,
                "sha256": _sha256(expected_path),
                "file_nodes": matched_nodes,
                "active_cook_only": True,
                "sop_import_path": evaluated_import,
                "sop_import_bound": import_bound,
            })

    return {"passed": not errors, "records": records, "errors": errors}


def _render_setup_audit(
    setup: dict[str, Any], plan_path: Path, *, render_proofs: bool = True
) -> dict[str, Any]:
    paths = setup.get("nodes")
    errors: list[str] = []
    records: list[dict[str, Any]] = []
    if not isinstance(paths, dict) or set(paths) != set(_RENDER_TYPES):
        return {
            "passed": False,
            "renderer": setup.get("renderer"),
            "color_pipeline": setup.get("color_pipeline"),
            "neutral_rig_id": setup.get("neutral_rig_id"),
            "nodes": [],
            "errors": ["render setup role coverage mismatch"],
        }
    output = hou.node(paths["render_output"])
    upstream = _upstream_nodes(output) if output is not None else set()
    for role, expected_type in _RENDER_TYPES.items():
        path = paths[role]
        node = hou.node(path)
        actual_type = _node_type(node) if node is not None else ""
        connected = node is not None and (role == "render_output" or node in upstream)
        records.append({
            "role": role,
            "path": path,
            "type": actual_type,
            "connected_to_render_output": connected,
        })
        if node is None:
            errors.append(f"render setup: missing {role} node {path}")
        elif actual_type.split("::", 1)[0] != expected_type:
            errors.append(f"render setup: {role} has type {actual_type}, expected {expected_type}")
        if not connected:
            errors.append(f"render setup: {role} is not connected to render output")

    library = hou.node(paths["material_library"])
    materials: list[hou.Node] = []
    if library is not None and not library.children():
        errors.append("render setup: material library contains no editable shader nodes")
    elif library is not None:
        children = list(library.children())
        shader_types = {child.type().name().split("::", 1)[0] for child in children}
        if not {"mtlxstandard_surface", "mtlxsurfacematerial"}.issubset(shader_types):
            errors.append("render setup: material library lacks an editable MaterialX surface")
        else:
            shaders = [child for child in children if child.type().name().split("::", 1)[0] == "mtlxstandard_surface"]
            materials = [child for child in children if child.type().name().split("::", 1)[0] == "mtlxsurfacematerial"]
            if len(shaders) != 1 or len(materials) != 1 or materials[0].input(0) != shaders[0]:
                errors.append("render setup: MaterialX shader is not directly connected to the surface material")
    assignment = hou.node(paths["material_assignment"])
    count_parm = assignment.parm("nummaterials") if assignment is not None else None
    if count_parm is not None and count_parm.evalAsInt() < 1:
        errors.append("render setup: material assignment contains no assignments")
    if assignment is not None:
        prim_parm = assignment.parm("primpattern1")
        material_parm = assignment.parm("matspecpath1")
        if prim_parm is None or not prim_parm.evalAsString().strip():
            errors.append("render setup: material assignment has no target primitives")
        if material_parm is None or not material_parm.evalAsString().strip():
            errors.append("render setup: material assignment has no material path")
        elif library is not None and len(materials) == 1:
            prefix_parm = library.parm("matpathprefix")
            expected_material = f"{prefix_parm.evalAsString() if prefix_parm else '/materials/'}{materials[0].name()}"
            assigned_material = material_parm.evalAsString().strip()
            if assigned_material != expected_material:
                errors.append("render setup: assignment does not resolve to the authored MaterialX material")
            try:
                stage = assignment.stage()
                material_prim = stage.GetPrimAtPath(assigned_material)
                if not material_prim.IsValid() or not UsdShade.Material(material_prim):
                    errors.append("render setup: assigned MaterialX USD material does not exist")
                rule = hou.LopSelectionRule()
                rule.setPathPattern(prim_parm.evalAsString().strip())
                target_paths = list(rule.expandedPaths(assignment))
                if not target_paths:
                    errors.append("render setup: material assignment pattern resolves to no primitives")
                for target_path in target_paths:
                    target = stage.GetPrimAtPath(target_path)
                    bound_material, _ = UsdShade.MaterialBindingAPI(target).ComputeBoundMaterial()
                    if not bound_material or bound_material.GetPrim().GetPath().pathString != assigned_material:
                        errors.append(f"render setup: target {target_path} is not bound to the authored material")
                        break
            except (hou.Error, RuntimeError) as error:
                errors.append(f"render setup: MaterialX USD binding audit failed: {error}")

    def material_binding_at_frame(frame: int) -> tuple[dict[str, Any], list[str]]:
        frame_errors: list[str] = []
        prim_parm = assignment.parm("primpattern1") if assignment is not None else None
        material_parm = assignment.parm("matspecpath1") if assignment is not None else None
        pattern = prim_parm.evalAsString().strip() if prim_parm is not None else ""
        assigned_material = material_parm.evalAsString().strip() if material_parm is not None else ""
        prefix_parm = library.parm("matpathprefix") if library is not None else None
        expected_material = (
            f"{prefix_parm.evalAsString() if prefix_parm else '/materials/'}{materials[0].name()}"
            if len(materials) == 1 else ""
        )
        target_paths: list[str] = []
        if assigned_material != expected_material or not assigned_material:
            frame_errors.append(f"material assignment path mismatch at frame {frame}")
        try:
            stage = assignment.stage() if assignment is not None else None
            material_prim = stage.GetPrimAtPath(assigned_material) if stage is not None else None
            if material_prim is None or not material_prim.IsValid() or not UsdShade.Material(material_prim):
                frame_errors.append(f"assigned MaterialX USD material is invalid at frame {frame}")
            rule = hou.LopSelectionRule()
            rule.setPathPattern(pattern)
            target_paths = (
                [str(path) for path in rule.expandedPaths(assignment)]
                if assignment is not None else []
            )
            if not target_paths:
                frame_errors.append(f"material assignment resolves to no primitives at frame {frame}")
            for target_path in target_paths:
                target = stage.GetPrimAtPath(target_path)
                bound_material, _ = UsdShade.MaterialBindingAPI(target).ComputeBoundMaterial()
                if not bound_material or bound_material.GetPrim().GetPath().pathString != assigned_material:
                    frame_errors.append(f"target {target_path} has no authored MaterialX binding at frame {frame}")
                    break
        except (hou.Error, RuntimeError) as error:
            frame_errors.append(f"MaterialX USD binding audit failed at frame {frame}: {error}")
        return {
            "frame": frame,
            "prim_pattern": pattern,
            "material_path": assigned_material,
            "target_paths": target_paths,
            "passed": not frame_errors,
        }, frame_errors

    camera_prims: dict[str, str] = {}
    for role in ("neutral_camera", "hero_camera"):
        camera = hou.node(paths[role])
        prim_parm = camera.parm("primpath") if camera is not None else None
        prim_path = prim_parm.evalAsString().strip() if prim_parm is not None else ""
        camera_prims[role] = prim_path
        if not prim_path:
            errors.append(f"render setup: {role} has no authored USD camera path")
    if camera_prims["neutral_camera"] == camera_prims["hero_camera"]:
        errors.append("render setup: neutral and hero cameras must author distinct USD paths")
    settings = hou.node(paths["render_settings"])
    if settings is not None:
        try:
            settings.cook(force=True)
        except hou.Error as error:
            errors.append(f"render setup: Karma settings cook failed: {error}")
        errors.extend(f"render setup: {message}" for message in settings.errors())
        camera_parm = settings.parm("camera")
        picture_parm = settings.parm("picture")
        resolution_parm = settings.parm("resolutionx")
        if camera_parm is None or not camera_parm.evalAsString().strip():
            errors.append("render setup: Karma settings have no authored camera")
        elif camera_parm.evalAsString().strip() != camera_prims["hero_camera"]:
            errors.append("render setup: Karma settings are not bound to the hero camera")
        if picture_parm is None or not picture_parm.evalAsString().strip():
            errors.append("render setup: Karma settings have no authored output path")
        if resolution_parm is None or resolution_parm.evalAsInt() < 320:
            errors.append("render setup: Karma settings resolution is below review minimum")
    render = hou.node(paths["render_output"])
    renderer_parm = render.parm("renderer") if render is not None else None
    if renderer_parm is None or "karma" not in renderer_parm.evalAsString().lower():
        errors.append("render setup: USD render output is not configured for Karma")
    ocio_config = hou.getenv("OCIO")
    if not ocio_config or not Path(ocio_config).is_file() or "aces" not in Path(ocio_config).name.lower():
        errors.append("render setup: no readable ACES OCIO configuration is active")
    resolution = setup.get("resolution")
    if (
        not isinstance(resolution, list)
        or len(resolution) != 2
        or any(not isinstance(value, int) or value < 180 for value in resolution)
    ):
        errors.append("render setup: invalid locked review resolution")
        resolution = [640, 360]
    samples = setup.get("samples_per_pixel")
    path_samples = setup.get("path_traced_samples")
    if not isinstance(samples, int) or samples < 1 or not isinstance(path_samples, int) or path_samples < 1:
        errors.append("render setup: invalid locked Karma sampling")
        samples, path_samples = 4, 16

    def require_parm_value(node: hou.Node | None, name: str, expected: object) -> None:
        parm = node.parm(name) if node is not None else None
        if parm is None:
            errors.append(f"render setup: missing required parameter {node.path() if node else '<missing>'}/{name}")
        elif parm.eval() != expected:
            errors.append(
                f"render setup: {node.path()}/{name} is {parm.eval()!r}, expected locked value {expected!r}"
            )

    require_parm_value(settings, "resolutionx", resolution[0])
    require_parm_value(settings, "resolutiony", resolution[1])
    require_parm_value(settings, "samplesperpixel", samples)
    require_parm_value(settings, "pathtracedsamples", path_samples)

    locked_camera = setup.get("neutral_camera_parameters")
    locked_dome = setup.get("neutral_dome_parameters")
    locked_render = setup.get("neutral_render_parameters")
    if not all(isinstance(values, dict) and values for values in (locked_camera, locked_dome, locked_render)):
        errors.append("render setup: locked neutral parameter contract is missing")
        locked_camera, locked_dome, locked_render = {}, {}, {}
    camera_node = hou.node(paths["neutral_camera"])
    dome_node = hou.node(paths["neutral_dome"])
    evidence_frames = sorted(set([
        *setup.get("neutral_frames", {}).values(),
        *setup.get("motion_frames", []),
    ]))
    for frame in evidence_frames:
        hou.setFrame(frame)
        for name, value in locked_camera.items():
            require_parm_value(camera_node, name, value)
        for name, value in locked_dome.items():
            require_parm_value(dome_node, name, value)
        for name, value in locked_render.items():
            require_parm_value(settings, name, value)

    parent_renders: list[dict[str, Any]] = []
    frames = setup.get("neutral_frames")
    proof_dir = plan_path.parent.parent / "04_evidence" / "parent-renders"
    if proof_dir.is_symlink():
        errors.append("render setup: parent render proof directory must not be a symlink")
    else:
        proof_dir.mkdir(parents=True, exist_ok=True)
    deliveries: list[tuple[str, int, str, int]] = []
    if isinstance(frames, dict) and set(frames) == {"early", "middle", "late"}:
        deliveries.extend(
            (
                f"neutral-{role}",
                int(frames[role]),
                camera_prims["neutral_camera"],
                0,
            )
            for role in ("early", "middle", "late")
        )
        deliveries.append(("hero", int(frames["middle"]), camera_prims["hero_camera"], 1))
    else:
        errors.append("render setup: neutral frame contract is invalid")
        frames = {"early": 1, "middle": 2, "late": 3}
    motion_frames = setup.get("motion_frames")
    if (
        not isinstance(motion_frames, list)
        or len(motion_frames) != 8
        or any(not isinstance(frame, int) for frame in motion_frames)
        or any(right != left + 1 for left, right in zip(motion_frames, motion_frames[1:]))
    ):
        errors.append("render setup: parent motion proof requires eight contiguous source frames")
        motion_frames = []
    else:
        deliveries.extend(
            (f"motion-{index:03d}", frame, camera_prims["neutral_camera"], 0)
            for index, frame in enumerate(motion_frames)
        )

    selector = hou.node(paths["lighting_selector"])
    selector_parm = selector.parm("input") if selector is not None else None
    if selector_parm is None:
        errors.append("render setup: lighting selector has no input parameter")
    material_binding_records: list[dict[str, Any]] = []
    if settings is not None and render is not None and not errors:
        def set_runtime_parm(name: str, value: object) -> None:
            parm = settings.parm(name)
            if parm is None:
                raise hou.OperationFailed(f"missing runtime render parameter {name}")
            parm.set(value, follow_parm_reference=False)

        for role, frame, camera_path, lighting_mode in deliveries:
            hou.setFrame(frame)
            binding_record, binding_errors = material_binding_at_frame(frame)
            material_binding_records.append({"role": role, **binding_record})
            if binding_errors:
                errors.extend(f"render setup: {message}" for message in binding_errors)
                break
            if not render_proofs:
                continue
            output_path = proof_dir / f"{role}.{frame:04d}.png"
            output_path.unlink(missing_ok=True)
            render_started_ns = time.time_ns()
            selector_parm.set(lighting_mode)
            set_runtime_parm("camera", camera_path)
            set_runtime_parm("picture", str(output_path.resolve()))
            try:
                render.render(frame_range=(frame, frame, 1), ignore_inputs=False)
            except hou.Error as error:
                errors.append(f"parent render proof failed for {role}: {error}")
                break
            render_errors = list(render.errors())
            if render_errors:
                errors.extend(f"parent render proof {role}: {message}" for message in render_errors)
                break
            if not output_path.is_file():
                errors.append(f"parent render proof produced no image for {role}")
                break
            if output_path.stat().st_mtime_ns < render_started_ns:
                errors.append(f"parent render proof was not freshly authored for {role}")
                break
            parent_renders.append({
                "role": role,
                "frame": frame,
                "camera": camera_path,
                "lighting_mode": lighting_mode,
                "path": str(output_path.resolve()),
                "bytes": output_path.stat().st_size,
                "sha256": _sha256(output_path),
            })

    camera = hou.node(paths["neutral_camera"])
    dome = hou.node(paths["neutral_dome"])
    def measured(node: hou.Node | None, excluded: tuple[str, ...] = ()) -> dict[str, Any]:
        values: dict[str, Any] = {}
        if node is None:
            return values
        for parm in node.parms():
            if parm.name() in excluded:
                continue
            try:
                value = parm.eval()
            except hou.Error:
                continue
            if isinstance(value, (str, int, float, bool)) or (
                isinstance(value, tuple)
                and all(isinstance(item, (str, int, float, bool)) for item in value)
            ):
                values[parm.name()] = value
        return values
    signature_samples = []
    for frame in sorted(set([*frames.values(), *motion_frames])):
        hou.setFrame(frame)
        signature_samples.append({
            "frame": frame,
            "camera": measured(camera),
            "dome": measured(dome),
            "render_settings": measured(settings, ("picture", "dcmfilename", "productName")),
        })
    neutral_signature = {
        "samples": signature_samples,
        "camera": signature_samples[0]["camera"] if signature_samples else {},
        "dome": signature_samples[0]["dome"] if signature_samples else {},
        "render_settings": signature_samples[0]["render_settings"] if signature_samples else {},
        "resolution": resolution,
        "samples_per_pixel": samples,
        "path_traced_samples": path_samples,
        "neutral_selector_input": 0,
        "locked_contract": {
            "camera": locked_camera,
            "dome": locked_dome,
            "render_settings": locked_render,
        },
        "ocio_sha256": _sha256(Path(ocio_config)) if ocio_config and Path(ocio_config).is_file() else None,
    }
    return {
        "passed": not errors,
        "renderer": setup.get("renderer"),
        "color_pipeline": setup.get("color_pipeline"),
        "neutral_rig_id": setup.get("neutral_rig_id"),
        "camera_prims": camera_prims,
        "ocio_config": ocio_config,
        "neutral_signature": neutral_signature,
        "parent_renders": parent_renders,
        "material_bindings": material_binding_records,
        "nodes": records,
        "errors": errors,
    }


def verify(hip_path: Path, plan_path: Path) -> dict[str, Any]:
    hou.hipFile.load(str(hip_path.resolve()), suppress_save_prompt=True, ignore_load_warnings=False)
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    planned_nodes = {
        node["path"]
        for stage in plan["stages"]
        for node in stage["nodes"]
    }
    stages = plan["stages"]
    stage_audits = [
        _stage_audit(stage, planned_nodes, require_output_flag=index == len(stages) - 1)
        for index, stage in enumerate(stages)
    ]
    source_cache = _source_cache_audit(plan, plan_path)
    render_setup = _render_setup_audit(plan.get("render_setup", {}), plan_path, render_proofs=False)
    node_objects = [hou.node(path) for path in sorted(planned_nodes)]
    existing_nodes = [node for node in node_objects if node is not None]

    duplicate_positions: list[list[str]] = []
    by_position: dict[tuple[str, float, float], list[str]] = {}
    for node in existing_nodes:
        position = node.position()
        key = (node.parent().path(), round(float(position.x()), 4), round(float(position.y()), 4))
        by_position.setdefault(key, []).append(node.path())
    for paths in by_position.values():
        if len(paths) > 1:
            duplicate_positions.append(sorted(paths))

    upward_edges: list[list[str]] = []
    planned_set = set(existing_nodes)
    for destination in existing_nodes:
        for source in destination.inputs():
            if source in planned_set and source.parent() == destination.parent():
                if float(destination.position().y()) >= float(source.position().y()):
                    upward_edges.append([source.path(), destination.path()])

    node_errors = [
        *[error for stage in stage_audits for error in stage["errors"]],
        *source_cache["errors"],
        *render_setup["errors"],
    ]
    if not node_errors and not duplicate_positions and not upward_edges:
        render_setup = _render_setup_audit(plan.get("render_setup", {}), plan_path, render_proofs=True)
        node_errors.extend(render_setup["errors"])
    scaffold_identities: dict[str, dict[str, str]] = {}
    for network_path in ("/obj", "/stage"):
        network = hou.node(network_path)
        if network is None:
            continue
        for node in network.allSubChildren():
            scaffold_id = node.userData("parent_scaffold_id")
            if scaffold_id:
                scaffold_identities[node.path()] = {
                    "type": node.type().name(),
                    "scaffold_id": scaffold_id,
                }
    return {
        "schema_version": 1,
        "verification_engine": "fresh-hython-reopen",
        "hip_path": str(hip_path.resolve()),
        "hip_sha256": _sha256(hip_path),
        "plan_sha256": _sha256(plan_path),
        "passed": not node_errors and not duplicate_positions and not upward_edges,
        "node_count": len(existing_nodes),
        "network_sections": [stage["network_section"] for stage in plan["stages"]],
        "stages": stage_audits,
        "upward_edges": upward_edges,
        "duplicate_node_positions": duplicate_positions,
        "node_errors": node_errors,
        "source_cache": source_cache,
        "render_setup": render_setup,
        "scaffold_identities": scaffold_identities,
    }


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit("usage: hython verify_look_scene.py HIP PLAN AUDIT")
    hip_path, plan_path, audit_path = map(Path, sys.argv[1:])
    try:
        audit = verify(hip_path, plan_path)
    except Exception as error:
        audit = {
            "schema_version": 1,
            "verification_engine": "fresh-hython-reopen",
            "hip_path": str(hip_path.resolve()),
            "passed": False,
            "node_errors": [f"{type(error).__name__}: {error}", traceback.format_exc()],
        }
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0 if audit.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
