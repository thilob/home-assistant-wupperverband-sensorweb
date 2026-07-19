"""Load API modules without requiring a full Home Assistant installation."""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

ROOT = Path(__file__).parents[1]
PACKAGE_NAME = "custom_components.wupperverband_sensorweb"
PACKAGE_PATH = ROOT / "custom_components" / "wupperverband_sensorweb"


class FakeStore:
    """Small Home Assistant Store replacement for cache unit tests."""

    saved: dict = {}

    def __class_getitem__(cls, item):
        return cls

    def __init__(self, hass, version, key) -> None:
        self.key = key

    async def async_load(self):
        return self.saved.get(self.key)

    async def async_save(self, data) -> None:
        self.saved[self.key] = data


homeassistant = types.ModuleType("homeassistant")
homeassistant_core = types.ModuleType("homeassistant.core")
homeassistant_helpers = types.ModuleType("homeassistant.helpers")
homeassistant_storage = types.ModuleType("homeassistant.helpers.storage")
homeassistant_core.HomeAssistant = object
homeassistant_storage.Store = FakeStore
sys.modules.setdefault("homeassistant", homeassistant)
sys.modules.setdefault("homeassistant.core", homeassistant_core)
sys.modules.setdefault("homeassistant.helpers", homeassistant_helpers)
sys.modules.setdefault("homeassistant.helpers.storage", homeassistant_storage)

custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components)

package = types.ModuleType(PACKAGE_NAME)
package.__path__ = [str(PACKAGE_PATH)]
sys.modules.setdefault(PACKAGE_NAME, package)

for module_name in ("models", "api"):
    full_name = f"{PACKAGE_NAME}.{module_name}"
    spec = importlib.util.spec_from_file_location(
        full_name, PACKAGE_PATH / f"{module_name}.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
