from pathlib import Path


def test_pipeline_modules_do_not_use_shell_or_process_orchestration():
    forbidden = (
        "subprocess.run",
        "subprocess.Popen",
        "os.system",
    )
    for path in Path("src/hal_runtime").glob("pipeline_*.py"):
        source = path.read_text(encoding="utf-8")
        assert not [item for item in forbidden if item in source]
