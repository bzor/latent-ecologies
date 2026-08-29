import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from houdini_ai.doctor import discover_tools

ROOT = Path(__file__).resolve().parents[1]


class LookSceneVerifierHoudiniTests(unittest.TestCase):
    def test_accepts_declared_dag_inputs_and_only_requires_final_output_flag(self) -> None:
        hython = next((tool.path for tool in discover_tools() if tool.name == "hython"), None)
        if hython is None:
            self.skipTest("Houdini is unavailable")
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            hip_path = work / "dag-look.hiplc"
            plan_path = work / "00_design" / "IMPLEMENTATION_PLAN.json"
            plan_path.parent.mkdir()
            audit_path = work / "audit.json"
            builder = work / "build_fixture.py"
            builder.write_text(
                "\n".join([
                    "import hashlib, json, sys",
                    "from pathlib import Path",
                    "import hou",
                    "hip, plan = map(Path, sys.argv[1:3])",
                    "hou.hipFile.clear(suppress_save_prompt=True)",
                    "cache_dir = hip.parent / 'cache'; cache_dir.mkdir()",
                    "cache_geo = hou.node('/obj').createNode('geo', 'CACHE_BUILD'); [c.destroy() for c in cache_geo.children()]",
                    "cache_box = cache_geo.createNode('box'); cache_box.parm('tx').setExpression('$F*0.1')",
                    "[(hou.setFrame(f), cache_box.geometry().saveToFile(str(cache_dir / f'simulation.{f:04d}.bgeo.sc'))) for f in range(1,9)]",
                    "cache_geo.destroy()",
                    "geo = hou.node('/obj').createNode('geo', 'LOOK'); [c.destroy() for c in geo.children()]",
                    "source = geo.createNode('file', 'SOURCE_FROZEN_CACHE'); source.parm('file').set(str(cache_dir / 'simulation.$F4.bgeo.sc')); source.setPosition(hou.Vector2(2, 8))",
                    "substitute = geo.createNode('box', 'SUBSTITUTE_GEOMETRY'); substitute.setPosition(hou.Vector2(6, 8))",
                    "source_switch = geo.createNode('switch', 'SOURCE_SWITCH'); source_switch.setInput(0, source); source_switch.setInput(1, substitute); source_switch.parm('input').set(0); source_switch.setPosition(hou.Vector2(2, 5))",
                    "mid = geo.createNode('null', 'OUT_SOURCE'); mid.setInput(0, source_switch); mid.setPosition(hou.Vector2(2, 2))",
                    "process = geo.createNode('attribwrangle', 'PROCESS'); process.setInput(0, mid); process.parm('class').set('point'); process.parm('snippet').set('f@verified = 1;'); process.setPosition(hou.Vector2(2, -1))",
                    "out = geo.createNode('null', 'OUT_LOOK'); out.setInput(0, process); out.setPosition(hou.Vector2(2, -4)); out.setDisplayFlag(True); out.setRenderFlag(True)",
                    "stage = hou.node('/stage')",
                    "for child in stage.children(): child.destroy()",
                    "imp = stage.createNode('sopimport','IMPORT_LOOK'); imp.parm('soppath').set(out.path()); imp.parm('primpath').set('/World/Look'); imp.parm('pathprefix').set('/World/Look')",
                    "lib = stage.createNode('materiallibrary','MATERIALS_LOOK'); lib.setInput(0,imp)",
                    "shader = lib.createNode('mtlxstandard_surface','LOOK_SHADER'); surface = lib.createNode('mtlxsurfacematerial','LOOK_MATERIAL'); surface.setInput(0,shader)",
                    "assign = stage.createNode('assignmaterial','ASSIGN_LOOK_MATERIALS'); assign.setInput(0,lib); assign.parm('nummaterials').set(1); assign.parm('primpattern1').set('/World/Look/**'); assign.parm('matspecpath1').set('/materials/LOOK_MATERIAL')",
                    "neutral = stage.createNode('camera','CAM_NEUTRAL'); neutral.setInput(0,assign); neutral.parm('primpath').set('/World/Cameras/Neutral'); neutral.parm('tz').set(8); neutral.parm('focalLength').set(50)",
                    "hero = stage.createNode('camera','CAM_HERO'); hero.setInput(0,neutral); hero.parm('primpath').set('/World/Cameras/Hero'); hero.parm('tz').set(5)",
                    "dome = stage.createNode('domelight::3.0','LIGHT_NEUTRAL_DOME'); dome.setInput(0,hero); dome.parm('primpath').set('/World/Lights/NeutralDome'); dome.parm('xn__inputsintensity_i0a').set(1); dome.parm('xn__inputscolor_ztar').set(1); dome.parm('xn__inputscolor_ztag').set(1); dome.parm('xn__inputscolor_ztab').set(1)",
                    "key = stage.createNode('distantlight::2.0','KEY'); key.setInput(0,dome)",
                    "fill = stage.createNode('distantlight::2.0','FILL'); fill.setInput(0,key)",
                    "rim = stage.createNode('distantlight::2.0','RIM'); rim.setInput(0,fill)",
                    "selector = stage.createNode('switch','SELECT_LIGHTING_MODE'); selector.setInput(0,dome); selector.setInput(1,rim)",
                    "settings = stage.createNode('karmarendersettings','RENDER_KARMA_SETTINGS'); settings.setInput(0,selector); settings.parm('camera').set('/World/Cameras/Hero'); settings.parm('picture').set(str(hip.with_name('test.$F4.exr'))); settings.parm('resolutionx').set(640); settings.parm('samplesperpixel').set(4); settings.parm('pathtracedsamples').set(16); settings.parm('enabledof').set(0); settings.parm('enablemblur').set(0); settings.parm('res_mode').set('manual')",
                    "render = stage.createNode('usdrender_rop','OUT_KARMA'); render.setInput(0,settings); render.parm('renderer').set('BRAY_HdKarma')",
                    "hou.hipFile.save(str(hip))",
                    "def spec(node, role, inputs): return {'path': node.path(), 'type': node.type().name(), 'role': role, 'inputs': [item.path() for item in inputs]}",
                    "receipt=[{'path':f'cache/simulation.{f:04d}.bgeo.sc','bytes':(cache_dir/f'simulation.{f:04d}.bgeo.sc').stat().st_size,'sha256':hashlib.sha256((cache_dir/f'simulation.{f:04d}.bgeo.sc').read_bytes()).hexdigest()} for f in range(1,9)]",
                    "value = {'direction_id':'look-direction-dag-test','project_root':str(hip.parent),'source_behavior_content_hash':'sha256:" + "a" * 64 + "','source_cache_receipt':receipt,'stages':[",
                    " {'id':'source-stage','network_section':'SOURCE','nodes':[spec(source,'frozen cache',[]),spec(substitute,'substitute probe',[]),spec(source_switch,'source selector',[source,substitute]),spec(mid,'source output',[source_switch])],'output_node':mid.path(),'artist_controls':[]},",
                    " {'id':'look-stage','network_section':'LOOK','nodes':[spec(process,'process',[mid]),spec(out,'final output',[process])],'output_node':out.path(),'artist_controls':[]}",
                    "], 'render_setup': {'renderer':'karma','color_pipeline':'ACEScg-OCIO','neutral_rig_id':'bzor-neutral-lookdev-v1','resolution':[640,360],'samples_per_pixel':4,'path_traced_samples':16,'neutral_camera_parameters':{'tx':0.0,'ty':0.0,'tz':8.0,'rx':0.0,'ry':0.0,'rz':0.0,'focalLength':50.0},'neutral_dome_parameters':{'xn__inputsintensity_i0a':1.0,'xn__inputscolor_ztar':1.0,'xn__inputscolor_ztag':1.0,'xn__inputscolor_ztab':1.0},'neutral_render_parameters':{'enabledof':0,'enablemblur':0,'res_mode':'manual'},'neutral_frames':{'early':1,'middle':4,'late':8},'motion_frames':[1,2,3,4,5,6,7,8],'nodes':{",
                    "'look_import':imp.path(),'material_library':lib.path(),'material_assignment':assign.path(),'neutral_camera':neutral.path(),'hero_camera':hero.path(),'neutral_dome':dome.path(),'hero_key':key.path(),'hero_fill':fill.path(),'hero_rim':rim.path(),'lighting_selector':selector.path(),'render_settings':settings.path(),'render_output':render.path()}}}",
                    "plan.write_text(json.dumps(value, indent=2))",
                    "",
                ]),
                encoding="utf-8",
            )
            environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
            built = subprocess.run(
                [str(hython), str(builder), str(hip_path), str(plan_path)],
                capture_output=True, text=True, timeout=120, check=False, env=environment,
            )
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            preseed = work / "04_evidence" / "parent-renders" / "neutral-early.0001.png"
            preseed.parent.mkdir(parents=True)
            preseed.write_bytes(b"worker-authored-not-a-render")
            verified = subprocess.run(
                [str(hython), str(ROOT / "houdini/verify_look_scene.py"), str(hip_path), str(plan_path), str(audit_path)],
                capture_output=True, text=True, timeout=300, check=False, env=environment,
            )
            self.assertEqual(verified.returncode, 0, verified.stdout + verified.stderr)
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            self.assertTrue(audit["passed"], json.dumps(audit, indent=2))
            self.assertFalse(audit["stages"][0]["output_flag_required"])
            self.assertTrue(audit["stages"][1]["output_flag_required"])
            self.assertEqual(audit["node_errors"], [])
            self.assertTrue(audit["render_setup"]["passed"])
            self.assertNotEqual(preseed.read_bytes(), b"worker-authored-not-a-render")

            inactive_mutator = work / "activate_substitute_geometry.py"
            inactive_mutator.write_text(
                "import hou, sys\n"
                "hou.hipFile.load(sys.argv[1], suppress_save_prompt=True)\n"
                "hou.node('/obj/LOOK/SOURCE_SWITCH').parm('input').set(1)\n"
                "hou.hipFile.save(sys.argv[1])\n",
                encoding="utf-8",
            )
            inactive_mutated = subprocess.run(
                [str(hython), str(inactive_mutator), str(hip_path)],
                capture_output=True, text=True, timeout=120, check=False, env=environment,
            )
            self.assertEqual(inactive_mutated.returncode, 0, inactive_mutated.stdout + inactive_mutated.stderr)
            inactive_rejected = subprocess.run(
                [str(hython), str(ROOT / "houdini/verify_look_scene.py"), str(hip_path), str(plan_path), str(audit_path)],
                capture_output=True, text=True, timeout=120, check=False, env=environment,
            )
            inactive_audit = json.loads(audit_path.read_text(encoding="utf-8"))
            self.assertNotEqual(inactive_rejected.returncode, 0)
            self.assertIn("no actively cooked File SOP", " ".join(inactive_audit["node_errors"]))

            frame_mutator = work / "break_frame_bindings.py"
            frame_mutator.write_text(
                "import hou, sys\n"
                "hou.hipFile.load(sys.argv[1], suppress_save_prompt=True)\n"
                "hou.node('/obj/LOOK/SOURCE_SWITCH').parm('input').set(0)\n"
                "hou.node('/stage/IMPORT_LOOK').parm('soppath').setExpression('\"/obj/LOOK/OUT_LOOK\" if hou.frame() == 8 else \"/obj/LOOK/OUT_SOURCE\"', hou.exprLanguage.Python)\n"
                "hou.node('/stage/ASSIGN_LOOK_MATERIALS').parm('primpattern1').setExpression('\"/World/Look/**\" if hou.frame() == 8 else \"/World/NoMatch\"', hou.exprLanguage.Python)\n"
                "hou.hipFile.save(sys.argv[1])\n",
                encoding="utf-8",
            )
            frame_mutated = subprocess.run(
                [str(hython), str(frame_mutator), str(hip_path)],
                capture_output=True, text=True, timeout=120, check=False, env=environment,
            )
            self.assertEqual(frame_mutated.returncode, 0, frame_mutated.stdout + frame_mutated.stderr)
            frame_rejected = subprocess.run(
                [str(hython), str(ROOT / "houdini/verify_look_scene.py"), str(hip_path), str(plan_path), str(audit_path)],
                capture_output=True, text=True, timeout=120, check=False, env=environment,
            )
            frame_audit = json.loads(audit_path.read_text(encoding="utf-8"))
            self.assertNotEqual(frame_rejected.returncode, 0)
            self.assertIn("final SOP output at frame 1", " ".join(frame_audit["node_errors"]))
            self.assertIn("no primitives at frame 1", " ".join(frame_audit["node_errors"]))

            mutator = work / "break_material_binding.py"
            mutator.write_text(
                "import hou, sys\n"
                "hou.hipFile.load(sys.argv[1], suppress_save_prompt=True)\n"
                "hou.node('/stage/IMPORT_LOOK').parm('soppath').deleteAllKeyframes(); hou.node('/stage/IMPORT_LOOK').parm('soppath').set('/obj/LOOK/OUT_LOOK')\n"
                "hou.node('/stage/ASSIGN_LOOK_MATERIALS').parm('primpattern1').deleteAllKeyframes(); hou.node('/stage/ASSIGN_LOOK_MATERIALS').parm('primpattern1').set('/World/Look/**')\n"
                "hou.node('/stage/MATERIALS_LOOK/LOOK_MATERIAL').setInput(0, None)\n"
                "hou.node('/stage/ASSIGN_LOOK_MATERIALS').parm('matspecpath1').set('/materials/DOES_NOT_EXIST')\n"
                "hou.hipFile.save(sys.argv[1])\n",
                encoding="utf-8",
            )
            mutated = subprocess.run(
                [str(hython), str(mutator), str(hip_path)],
                capture_output=True, text=True, timeout=120, check=False, env=environment,
            )
            self.assertEqual(mutated.returncode, 0, mutated.stdout + mutated.stderr)
            rejected = subprocess.run(
                [str(hython), str(ROOT / "houdini/verify_look_scene.py"), str(hip_path), str(plan_path), str(audit_path)],
                capture_output=True, text=True, timeout=120, check=False, env=environment,
            )
            rejected_audit = json.loads(audit_path.read_text(encoding="utf-8"))
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("MaterialX shader is not directly connected", " ".join(rejected_audit["node_errors"]))
            self.assertIn("does not resolve to the authored MaterialX material", " ".join(rejected_audit["node_errors"]))


if __name__ == "__main__":
    unittest.main()
