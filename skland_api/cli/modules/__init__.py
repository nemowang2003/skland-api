import importlib
import logging
import pkgutil

default_modules = [
    "title",
    "sign",
    "online",
    "stamina",
    "affair",
    "mission",
    "recruit",
    "base",
]

_registry: dict = {}


def _load_registry() -> dict:
    if _registry:
        return _registry
    for _, name, ispkg in pkgutil.iter_modules(__path__):
        try:
            module = importlib.import_module(f"{__name__}.{name}")
            if hasattr(module, "main"):
                _registry[name] = module.main
            else:
                logging.warning(f"module {name!r} has no entrypoint 'main'")
        except ImportError:
            logging.exception(f"failed to import module {name!r}")
        except Exception:
            logging.exception(f"internal error in module {name!r}")
    return _registry


def __getattr__(name: str):
    if name == "registry":
        return _load_registry()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "default_modules",
    "registry",
]
