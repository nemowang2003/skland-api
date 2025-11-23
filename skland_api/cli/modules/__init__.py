import pkgutil
import importlib
import logging

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

registry = dict()


def __getattr__(name: str):
    if name == "registry":
        for _, name, ispkg in pkgutil.iter_modules(__path__):
            try:
                module = importlib.import_module(f"{__name__}.{name}")
                if hasattr(module, "main"):
                    registry[name] = module.main
                else:
                    logging.warning(f"module {name!r} has no entrypoint 'main'")
            except ImportError:
                logging.exception(f"failed to import module {name!r}")
            except Exception:
                logging.exception(f"internal error in module {name!r}")


__all__ = [
    "default_modules",
    "registry",
]
