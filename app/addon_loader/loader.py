import importlib


def load_addons(app, addon_paths):
    for path in addon_paths:
        module_path, func_name = path.split(":", 1)
        module = importlib.import_module(module_path)
        register = getattr(module, func_name)
        register(app)