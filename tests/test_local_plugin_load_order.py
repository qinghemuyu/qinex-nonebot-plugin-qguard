import os
import shutil
import subprocess
import sys
from pathlib import Path


def test_local_plugins_can_load_before_ai_core(tmp_path: Path) -> None:
    plugin_root = tmp_path / "src" / "qinex" / "plugins"
    plugin_root.mkdir(parents=True)
    for package in (
        "nonebot_plugin_ai_core",
        "nonebot_plugin_log_doctor",
        "nonebot_plugin_group_wiki",
        "nonebot_plugin_support_bot",
    ):
        shutil.copytree(
            Path.cwd() / package,
            plugin_root / package,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    for package_dir in (tmp_path / "src", tmp_path / "src" / "qinex", plugin_root):
        (package_dir / "__init__.py").write_text("", encoding="utf-8")

    script = """
import nonebot
from nonebot.adapters.onebot.v11 import Adapter

nonebot.init(driver="~none")
driver = nonebot.get_driver()
driver.register_adapter(Adapter)

for name in (
    "src.qinex.plugins.nonebot_plugin_support_bot",
    "src.qinex.plugins.nonebot_plugin_group_wiki",
    "src.qinex.plugins.nonebot_plugin_log_doctor",
    "src.qinex.plugins.nonebot_plugin_ai_core",
):
    plugin = nonebot.load_plugin(name)
    print(name, plugin is not None)

from nonebot_plugin_group_wiki.services.rag_service import _get_ai_core
from nonebot_plugin_log_doctor.services.ai_diagnose_service import AIDiagnoseService

print(_get_ai_core().__class__.__name__)
print(AIDiagnoseService().ai_core is None)
"""
    env = os.environ.copy()
    env["PYTHONPATH"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "nonebot_plugin_support_bot True" in result.stdout
    assert "nonebot_plugin_group_wiki True" in result.stdout
    assert "nonebot_plugin_log_doctor True" in result.stdout
    assert "nonebot_plugin_ai_core True" in result.stdout
    assert "AICoreService" in result.stdout
