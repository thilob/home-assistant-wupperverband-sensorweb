"""Load integration modules without requiring a full Home Assistant installation."""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
PACKAGE_NAME = "custom_components.wupperverband_sensorweb"
PACKAGE_PATH = ROOT / "custom_components" / "wupperverband_sensorweb"

custom_components = types.ModuleType("custom_components")
custom_components.__path__ = [str(ROOT / "custom_components")]
sys.modules.setdefault("custom_components", custom_components)

package = types.ModuleType(PACKAGE_NAME)
package.__path__ = [str(PACKAGE_PATH)]
sys.modules.setdefault(PACKAGE_NAME, package)

homeassistant = types.ModuleType("homeassistant")
homeassistant.__path__ = []
sys.modules.setdefault("homeassistant", homeassistant)

core = types.ModuleType("homeassistant.core")


class HomeAssistant:
    """Minimal Home Assistant stub for cache tests."""

    def __init__(self) -> None:
        self.data: dict[str, Any] = {}


core.HomeAssistant = HomeAssistant
sys.modules.setdefault("homeassistant.core", core)

helpers = types.ModuleType("homeassistant.helpers")
helpers.__path__ = []
sys.modules.setdefault("homeassistant.helpers", helpers)

storage = types.ModuleType("homeassistant.helpers.storage")


class FakeStore:
    """Tiny in-memory replacement for Home Assistant's Store."""

    saved: dict[str, Any] = {}

    def __init__(self, hass: HomeAssistant, version: int, key: str) -> None:
        self._storage_key = f"{version}:{key}"

    async def async_load(self) -> dict[str, Any] | None:
        data = self.saved.get(self._storage_key)
        return None if data is None else dict(data)

    async def async_save(self, data: dict[str, Any]) -> None:
        self.saved[self._storage_key] = dict(data)


storage.Store = FakeStore
sys.modules.setdefault("homeassistant.helpers.storage", storage)

for module_name in ("const", "models", "api", "metadata_cache"):
    full_name = f"{PACKAGE_NAME}.{module_name}"
    spec = importlib.util.spec_from_file_location(full_name, PACKAGE_PATH / f"{module_name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
