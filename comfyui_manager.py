import os
from backend.loader.decorator import KatzukiNode
from backend.nodes.builtin import BaseNode
from typing import Any

# Dynamically load comfy as a module
import sys
import importlib.util


def load_module(module_name: str, module_path: str):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is not None and spec.loader is not None:
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    else:
        raise ImportError(f"Could not load module {module_name} from {module_path}")


def load_package(package_name: str, package_path: str):
    spec = importlib.util.spec_from_file_location(package_name, package_path + '/__init__.py')
    if spec is not None and spec.loader is not None:
        package = importlib.util.module_from_spec(spec)
        sys.modules[package_name] = package
        spec.loader.exec_module(package)

        # Then, load all submodules
        # for root, dirs, files in os.walk(package_path):
        #     for file in files:
        #         if file.endswith('.py') and file != '__init__.py':
        #             module_name = file[:-3]
        #             module_path = os.path.join(root, file)
        #             spec = importlib.util.spec_from_file_location(package_name + '.' + module_name, module_path)
        #             if spec is not None and spec.loader is not None:
        #                 module = importlib.util.module_from_spec(spec)
        #                 setattr(package, module_name, module)
        #                 spec.loader.exec_module(module)
        #             else:
        #                 raise ImportError(f"Could not load module {module_name} from {module_path}")

        return package
    else:
        raise ImportError(f"Could not load package {package_name} from {package_path}")


def add_to_sys_path(path: str):
    # since if we want to use `load_package`, we need to load everything recursively
    # which is prone to error, so we just add the path to sys.path
    if path not in sys.path:
        sys.path.append(path)


# Note: the order of executing these matters!
add_to_sys_path(os.path.join(os.path.dirname(os.path.realpath(__file__))))

# Add chainner_models to sys.modules as chainner_models package
# load_package('chainner_models', os.path.join(os.path.dirname(os.path.realpath(__file__)), "comfy_extras", "chainner_models"))

# Add comfy to sys.modules as comfy package
import comfy
# load_package('comfy', os.path.join(os.path.dirname(os.path.realpath(__file__)), "comfy"))

# Add comfy_extras to sys.modules as comfy_extras package
import comfy_extras
# load_package('comfy_extras', os.path.join(os.path.dirname(os.path.realpath(__file__)), "comfy_extras"))

# Add _folder_paths to sys.modules as folder_paths module
load_module('folder_paths', os.path.join(os.path.dirname(os.path.realpath(__file__)), "_folder_paths.py"))

# Add _latent_preview to sys.modules as latent_preview module
load_module('latent_preview', os.path.join(os.path.dirname(os.path.realpath(__file__)), "_latent_preview.py"))

# Add nodes.py to sys.modules as nodes module (a very hacky way to do this)
import nodes # THIS LINE IS ESSENTIAL! IT FORCE THE PROGRAM TO INITIALIZE THE NODES MODULE

setattr(sys.modules['nodes'], 'MAX_RESOLUTION', 8192)


class ComfyUIManager(BaseNode):
    """A node to manage ComfyUI-native nodes"""

    @KatzukiNode(singleton=True, persistent=True, inoperable=True)
    def __init__(self) -> None:
        pass

    def execute(self, input: Any) -> Any:
        return input
