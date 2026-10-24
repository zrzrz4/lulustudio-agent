import json
from pathlib import Path

from lulustudio.tools.comfyui import ComfyUITool, _replace_templates


def test_flux_lulu_workflow_template_resolves_runtime_parameters() -> None:
    path = Path("workflows/flux_lulu_t2i_api.json")
    workflow = json.loads(path.read_text(encoding="utf-8"))
    resolved = _replace_templates(
        workflow,
        {
            "PROMPT": "one lulu",
            "SEED": 42,
            "WIDTH": 768,
            "HEIGHT": 1152,
            "LORA_STRENGTH": 0.8,
            "GUIDANCE": 3.5,
            "STEPS": 25,
            "FILENAME_PREFIX": "LuluStudio/test",
        },
    )

    assert resolved["3"]["inputs"]["text"] == "one lulu"
    assert resolved["6"]["inputs"]["noise_seed"] == 42
    assert resolved["2"]["inputs"]["strength_model"] == 0.8
    assert resolved["12"]["inputs"]["filename_prefix"] == "LuluStudio/test"


def test_comfyui_history_preserves_subfolder_and_surfaces_execution_error() -> None:
    history = {
        "outputs": {
            "12": {
                "images": [
                    {
                        "filename": "flux_lulu_00001_.png",
                        "subfolder": "LuluStudio",
                        "type": "output",
                    }
                ]
            }
        },
        "status": {"status_str": "success", "completed": True, "messages": []},
    }
    assert ComfyUITool._collect_artifacts(history) == {
        "12.images.0": "LuluStudio/flux_lulu_00001_.png"
    }
    assert ComfyUITool._execution_error(history) is None

    failed = {
        "status": {
            "status_str": "error",
            "completed": False,
            "messages": [
                [
                    "execution_error",
                    {
                        "node_id": "2",
                        "node_type": "LoraLoaderModelOnly",
                        "exception_message": "incompatible LoRA",
                    },
                ]
            ],
        }
    }
    assert ComfyUITool._execution_error(failed) == (
        "ComfyUI execution failed at node 2 (LoraLoaderModelOnly): incompatible LoRA"
    )
