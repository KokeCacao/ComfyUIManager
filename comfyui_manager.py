import os
from backend.loader.decorator import KatzukiNode
from backend.nodes.builtin import BaseNode
from typing import Any

# Dynamically load comfy as a module
import sys
import importlib.util


def load_module(module_name, module_path):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is not None and spec.loader is not None:
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module
    else:
        raise ImportError(f"Could not load module {module_name} from {module_path}")


def load_package(package_name, package_path):
    spec = importlib.util.spec_from_file_location(package_name, package_path + '/__init__.py')
    if spec is not None and spec.loader is not None:
        package = importlib.util.module_from_spec(spec)
        sys.modules[package_name] = package
        spec.loader.exec_module(package)
        return package
    else:
        raise ImportError(f"Could not load package {package_name} from {package_path}")


# Add _folder_paths to sys.modules as folder_paths module
load_module('folder_paths', os.path.join(os.path.dirname(os.path.realpath(__file__)), "_folder_paths.py"))

# Add comfy to sys.modules as comfy package
load_package('comfy', os.path.join(os.path.dirname(os.path.realpath(__file__)), "comfy"))


class ComfyUIManager(BaseNode):
    """A node to manage ComfyUI-native nodes"""

    @KatzukiNode(singleton=True, persistent=True, inoperable=True)
    def __init__(self) -> None:
        pass

    def execute(self, input: Any) -> Any:
        return input
