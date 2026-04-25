import importlib
import pkgutil
from typing import Any

import dash

import src.dashboard.components as _components_pkg
from src.logging_config import get_logger

logger = get_logger(__name__)


def discover_components(app: dash.Dash) -> list[tuple[dict, Any]]:
    """Walk src/dashboard/components/, import each module, register callbacks, return sorted (spec, layout) pairs."""
    results: list[tuple[dict, Any]] = []
    pkg_path = _components_pkg.__path__
    pkg_name = _components_pkg.__name__

    for _finder, mod_name, _ispkg in pkgutil.iter_modules(pkg_path):
        full_name = f"{pkg_name}.{mod_name}"
        try:
            mod = importlib.import_module(full_name)
        except Exception as exc:
            logger.error("Failed to import component module %s: %s", full_name, exc)
            continue

        for attr in ("CARD_SPEC", "layout", "register_callbacks"):
            if not hasattr(mod, attr):
                logger.warning("Component %s missing %s — skipping", full_name, attr)
                break
        else:
            try:
                mod.register_callbacks(app)
                results.append((mod.CARD_SPEC, mod.layout()))
                logger.info("Registered component: %s", mod_name)
            except Exception as exc:
                logger.error("Error registering component %s: %s", full_name, exc)

    results.sort(key=lambda x: x[0].get("order", 999))
    return results
