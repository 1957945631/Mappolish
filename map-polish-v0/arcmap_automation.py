import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


ARCMAP_PYTHON = r"C:\Python27\ArcGIS10.8\python.exe"
MAX_MXD_BYTES = 100 * 1024 * 1024
WORKER_SCRIPT = Path(__file__).resolve().parent / "scripts" / "arcmap_worker.py"


@dataclass(frozen=True)
class MxdValidation:
    extension: str
    size_bytes: int


@dataclass(frozen=True)
class MxdInspection:
    layers: list[str]
    layout_elements: list[dict]
    warnings: list[str]


@dataclass(frozen=True)
class PolishResult:
    output_mxd: str
    output_png: str
    changes: list[str]
    warnings: list[str]
    errors: list[str]


def validate_mxd_upload(filename: str, mxd_bytes: bytes) -> MxdValidation:
    extension = Path(filename).suffix.lower().lstrip(".")
    if extension != "mxd":
        raise ValueError("Only MXD files are supported for ArcMap automation.")
    if len(mxd_bytes) > MAX_MXD_BYTES:
        raise ValueError("MXD file size must be 100MB or smaller.")
    return MxdValidation(extension=extension, size_bytes=len(mxd_bytes))


def build_arcmap_command(mode: str, mxd_path: str, output_dir: str, config_path: str) -> list[str]:
    return [ARCMAP_PYTHON, str(WORKER_SCRIPT), mode, mxd_path, output_dir, config_path]


def write_polish_config(
    config_path: str,
    layer_mapping: dict[str, str],
    layout_options: dict,
    rules: dict,
    auto_actions: list[dict] | None = None,
) -> None:
    payload = {
        "layer_mapping": layer_mapping,
        "layout_options": layout_options,
        "rules": rules,
        "auto_actions": auto_actions or [],
    }
    with open(config_path, "w", encoding="utf-8") as file_obj:
        json.dump(payload, file_obj, ensure_ascii=False, indent=2)


def inspect_mxd(mxd_path: str) -> MxdInspection:
    work_dir = tempfile.mkdtemp(prefix="mappolish_inspect_")
    config_path = os.path.join(work_dir, "config.json")
    write_polish_config(config_path, {}, {}, {})

    result = _run_worker("inspect", mxd_path, work_dir, config_path)
    return MxdInspection(
        layers=result.get("layers", []),
        layout_elements=result.get("layout_elements", []),
        warnings=result.get("warnings", []),
    )


def run_arcmap_polish(
    mxd_path: str,
    layer_mapping: dict[str, str],
    layout_options: dict,
    rules: dict,
    auto_actions: list[dict] | None = None,
) -> PolishResult:
    work_dir = tempfile.mkdtemp(prefix="mappolish_arcmap_")
    config_path = os.path.join(work_dir, "config.json")
    write_polish_config(config_path, layer_mapping, layout_options, rules, auto_actions)

    result = _run_worker("polish", mxd_path, work_dir, config_path)
    return PolishResult(
        output_mxd=result.get("output_mxd", ""),
        output_png=result.get("output_png", ""),
        changes=result.get("changes", []),
        warnings=result.get("warnings", []),
        errors=result.get("errors", []),
    )


def parse_polish_result(return_code: int, result_path: str, stdout: str, stderr: str) -> dict:
    if return_code != 0:
        detail = stderr.strip() or stdout.strip() or "No ArcPy error output was captured."
        raise RuntimeError(f"ArcPy execution failed: {detail}")
    if not os.path.exists(result_path):
        raise RuntimeError("ArcPy execution failed: result JSON was not created.")
    with open(result_path, "r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def save_uploaded_mxd(filename: str, mxd_bytes: bytes) -> str:
    validate_mxd_upload(filename, mxd_bytes)
    work_dir = tempfile.mkdtemp(prefix="mappolish_upload_")
    safe_name = Path(filename).name
    mxd_path = os.path.join(work_dir, safe_name)
    with open(mxd_path, "wb") as file_obj:
        file_obj.write(mxd_bytes)
    return mxd_path


def _run_worker(mode: str, mxd_path: str, output_dir: str, config_path: str) -> dict:
    result_path = os.path.join(output_dir, "result.json")
    command = build_arcmap_command(mode, mxd_path, output_dir, config_path)
    completed = subprocess.run(command, capture_output=True, text=True)
    return parse_polish_result(completed.returncode, result_path, completed.stdout, completed.stderr)
