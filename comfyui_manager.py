import os
from backend.loader.decorator import KatzukiNode
from backend.nodes.builtin import BaseNode
from typing import Any

current_dir = os.path.abspath(os.path.dirname(__file__))
target_dir = os.path.abspath(os.path.join(current_dir, "../../"))
target_folder_paths_path = os.path.join(target_dir, "folder_paths.py")
target_gitignore_path = os.path.join(target_dir, ".gitignore")
installed_plugins_cache_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "installed_plugins_cache.json")

# Create proper gitignore
ignores = [".gitignore", "folder_paths.py"]
current_ignore = []
if os.path.exists(target_gitignore_path):
    with open(target_gitignore_path, "r") as f:
        current_ignore = [line.strip() for line in f.readlines()]

with open(target_gitignore_path, "a") as f:
    for ignore in ignores:
        # if gitignore don't already contain ignore, write it to gitignore
        if ignore not in current_ignore:
            f.write(f"{ignore}\n")

# Create a file at "./src/folder_paths.py" if not exist
# KatUI will load this file first before main.py and before any other file in subdirectories
try:
    import folder_paths # type: ignore
except ImportError:
    # if there is no file at "../../folder_paths.py", create it
    print(f"Creating folder_paths.py at {target_folder_paths_path}, since it does not exist.")

    with open(target_folder_paths_path, "w") as f:
        f.write("from nodes.ComfyUIManager._folder_paths import *")
    import folder_paths # type: ignore

# Dynamically load comfy as a module
import sys
import importlib.util


def load_package(package_name, package_path):
    spec = importlib.util.spec_from_file_location(package_name, package_path + '/__init__.py')
    if spec is not None and spec.loader is not None:
        package = importlib.util.module_from_spec(spec)
        sys.modules[package_name] = package
        spec.loader.exec_module(package)
        return package
    else:
        raise ImportError(f"Could not load package {package_name} from {package_path}")


# Example usage
package_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "_comfy")
package = load_package('comfy', package_path)


class ComfyUIManager(BaseNode):
    """A node to manage ComfyUI-native nodes"""

    @KatzukiNode(singleton=True, persistent=True, inoperable=True)
    def __init__(self) -> None:
        pass

    def execute(self, input: Any) -> Any:
        return input
