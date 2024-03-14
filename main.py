import os
import json
import sys
import traceback
import time
import importlib.util
import pathlib
import inspect
import subprocess
import torch

import folder_paths # type: ignore

from fastapi import Request
from typing import Dict, Any, Literal, List

from backend import variable
from backend.app import app
from backend.utils import SafeJSONResponse

# TODO: auto install plugins and their requirements
# TODO: execute_prestartup_script

# THE FOLLOWING CODE ARE TAKEN AND MODIFIED FROM COMFY-UI

from nodes.ComfyUIManager._nodes import NODE_CLASS_MAPPINGS as _NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS as _NODE_DISPLAY_NAME_MAPPINGS, EXTENSION_WEB_DIRS as _EXTENSION_WEB_DIRS

EXTENSION_WEB_DIRS = _EXTENSION_WEB_DIRS # Well, we can't do anything with js injection
NODE_CLASS_MAPPINGS: Dict[str, type] = _NODE_CLASS_MAPPINGS # Similar to node_loader.external_nodes
NODE_DISPLAY_NAME_MAPPINGS: Dict[str, str] = _NODE_DISPLAY_NAME_MAPPINGS


def load_custom_node(module_path, ignore=set()):
    module_name = os.path.basename(module_path)
    if os.path.isfile(module_path):
        sp = os.path.splitext(module_path)
        module_name = sp[0]
    try:
        if os.path.isfile(module_path):
            module_spec = importlib.util.spec_from_file_location(module_name, location=module_path)
            module_dir = os.path.split(module_path)[0]
        else:
            module_spec = importlib.util.spec_from_file_location(module_name, location=os.path.join(module_path, "__init__.py"))
            module_dir = module_path

        assert module_spec is not None
        assert module_spec.loader is not None
        module = importlib.util.module_from_spec(module_spec)
        sys.modules[module_name] = module
        module_spec.loader.exec_module(module)

        if hasattr(module, "WEB_DIRECTORY") and getattr(module, "WEB_DIRECTORY") is not None:
            web_dir = os.path.abspath(os.path.join(module_dir, getattr(module, "WEB_DIRECTORY")))
            if os.path.isdir(web_dir):
                EXTENSION_WEB_DIRS[module_name] = web_dir

        if hasattr(module, "NODE_CLASS_MAPPINGS") and getattr(module, "NODE_CLASS_MAPPINGS") is not None:
            for name in module.NODE_CLASS_MAPPINGS:
                if name not in ignore:
                    NODE_CLASS_MAPPINGS[name] = module.NODE_CLASS_MAPPINGS[name]
            if hasattr(module, "NODE_DISPLAY_NAME_MAPPINGS") and getattr(module, "NODE_DISPLAY_NAME_MAPPINGS") is not None:
                NODE_DISPLAY_NAME_MAPPINGS.update(module.NODE_DISPLAY_NAME_MAPPINGS)
            return True
        else:
            print(f"Skip {module_path} module for custom nodes due to the lack of NODE_CLASS_MAPPINGS.")
            return False
    except Exception as e:
        print(traceback.format_exc())
        print(f"Cannot import {module_path} module for custom nodes:", e)
        return False


def load_custom_nodes():
    base_node_names = set(NODE_CLASS_MAPPINGS.keys())
    node_paths = folder_paths.get_folder_paths("custom_nodes")
    node_import_times = []
    for custom_node_path in node_paths:
        possible_modules = os.listdir(os.path.realpath(custom_node_path))
        if "__pycache__" in possible_modules:
            possible_modules.remove("__pycache__")

        for possible_module in possible_modules:
            module_path = os.path.join(custom_node_path, possible_module)
            if os.path.isfile(module_path) and os.path.splitext(module_path)[1] != ".py":
                continue
            if module_path.endswith(".disabled"):
                continue
            time_before = time.perf_counter()
            success = load_custom_node(module_path, base_node_names)
            node_import_times.append((time.perf_counter() - time_before, module_path, success))

    if len(node_import_times) > 0:
        print("\nImport times for custom nodes:")
        for n in sorted(node_import_times):
            if n[2]:
                import_message = ""
            else:
                import_message = " (IMPORT FAILED)"
            print("{:6.1f} seconds{}:".format(n[0], import_message), n[1])
        print()


def init_custom_nodes():
    extras_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "comfy_extras")
    extras_files = [
        "nodes_latent.py",
        "nodes_hypernetwork.py",
        "nodes_upscale_model.py",
        "nodes_post_processing.py",
        "nodes_mask.py",
        "nodes_compositing.py",
        "nodes_rebatch.py",
        "nodes_model_merging.py",
        "nodes_tomesd.py",
        "nodes_clip_sdxl.py",
        "nodes_canny.py",
        "nodes_freelunch.py",
        "nodes_custom_sampler.py",
        "nodes_hypertile.py",
        "nodes_model_advanced.py",
        "nodes_model_downscale.py",
        "nodes_images.py",
        "nodes_video_model.py",
        "nodes_sag.py",
        "nodes_perpneg.py",
        "nodes_stable3d.py",
        "nodes_sdupscale.py",
        "nodes_photomaker.py",
        "nodes_cond.py",
        "nodes_morphology.py",
        "nodes_stable_cascade.py",
        "nodes_differential_diffusion.py",
    ]

    import_failed = []
    for node_file in extras_files:
        if not load_custom_node(os.path.join(extras_dir, node_file)):
            import_failed.append(node_file)

    load_custom_nodes()

    if len(import_failed) > 0:
        print("WARNING: some comfy_extras/ nodes did not import correctly. This may be because they are missing some dependencies.\n")
        for node in import_failed:
            print("IMPORT FAILED: {}".format(node))
        print("\nThis issue might be caused by missing dependencies.")
        print("Please do a: pip install -r requirements.txt")
        print()


init_custom_nodes() # This function sets EXTENSION_WEB_DIRS, NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

# These are the default folders that checkpoints, clip and vae models will be saved to when using CheckpointSave, etc.. nodes
folder_paths.add_model_folder_path("checkpoints", os.path.join(folder_paths.get_output_directory(), "checkpoints"))
folder_paths.add_model_folder_path("clip", os.path.join(folder_paths.get_output_directory(), "clip"))
folder_paths.add_model_folder_path("vae", os.path.join(folder_paths.get_output_directory(), "vae"))


def node_info(node_class):
    obj_class = NODE_CLASS_MAPPINGS[node_class]
    info = {}
    info['input'] = obj_class.INPUT_TYPES()
    info['output'] = obj_class.RETURN_TYPES
    info['output_is_list'] = obj_class.OUTPUT_IS_LIST if hasattr(obj_class, 'OUTPUT_IS_LIST') else [False] * len(obj_class.RETURN_TYPES)
    info['output_name'] = obj_class.RETURN_NAMES if hasattr(obj_class, 'RETURN_NAMES') else info['output']
    info['name'] = node_class
    info['display_name'] = NODE_DISPLAY_NAME_MAPPINGS[node_class] if node_class in NODE_DISPLAY_NAME_MAPPINGS.keys() else node_class
    info['description'] = obj_class.DESCRIPTION if hasattr(obj_class, 'DESCRIPTION') else ''
    info['category'] = 'sd'
    if hasattr(obj_class, 'OUTPUT_NODE') and obj_class.OUTPUT_NODE == True:
        info['output_node'] = True
    else:
        info['output_node'] = False

    if hasattr(obj_class, 'CATEGORY'):
        info['category'] = obj_class.CATEGORY
    return info


def convert_type(type_original: Any):
    if type(type_original) == str:
        return type_original
    if type(type_original) == list:
        # if all elements are string, then it is a literal
        if all(isinstance(x, str) for x in type_original):
            _type_original = [f"'{x}'" for x in type_original]
            return f"typing.Literal[{', '.join(_type_original)}]"
    raise ValueError(f"Type {type_original} is not supported. Please report this issue to https://github.com/KokeCacao/KatUI/issues")


def node_info_to_node_dict(node_str_types: str, node_info: Dict[str, Any], t: type):
    # constructing input_port_id_to_type
    required_input_port_id = []
    required_input_type = []
    if 'input' in node_info and 'required' in node_info['input']:
        required_input_port_id = list(node_info['input']['required'].keys())
        required_input_type = [convert_type(x[0]) for x in node_info['input']['required'].values()]

    optional_input_port_id = []
    optional_input_type = []
    if 'input' in node_info and 'optional' in node_info['input']:
        optional_input_port_id = list(node_info['input']['optional'].keys())
        optional_input_type = [convert_type(x[0]) for x in node_info['input']['optional'].values()]

    input_port_id = required_input_port_id + optional_input_port_id
    input_type = required_input_type + optional_input_type

    input_port_id_to_type = dict(zip(input_port_id, input_type))

    # constructing output_port_id_to_type
    output_type = [a if not b else "<class 'list'>" for a, b in zip(node_info['output'], node_info['output_is_list'])]
    output_port_id_to_type = dict(zip(node_info['output_name'], output_type))
    if len(output_port_id_to_type) == 0:
        # if there is no output, then it is a None type
        output_port_id_to_type = {"output": "None"}

    # constructing input_port_id_to_default
    execute_fn = getattr(t, t.FUNCTION)
    sig = inspect.signature(execute_fn)
    input_port_id_to_default = {k: v.default for k, v in sig.parameters.items() if v.default is not inspect.Parameter.empty}

    # input_port_id_to_default = {key: None for key in optional_input_port_id}

    return {
        "node_type": node_str_types,
        "class_name": node_info['name'], # Not used since they don't have custom UI
        "display_name": node_info['display_name'],
        "input_port_id_to_type": input_port_id_to_type,
        "output_port_id_to_type": output_port_id_to_type,
        "input_port_id_to_default": input_port_id_to_default,
        "signal_to_default_data": {},
        "data": {
            "hidden": False,
            "singleton": False,
            "persistent": False,
            "inoperable": False,
        },
        "inner_types": {}, # I don't need inner types because I assume no args and kwargs
        "python_path": None, # I am not using it
        "metadata": {
            "author": None,
            "author_url": None,
            "node_description": node_info['description'],
            "input_description": {},
            "output_description": {},
        },
        "plugin_name": node_info['category'].replace('/', '.'),
        "plugin_url": None,
    }


node_str_types = [t.CATEGORY.replace('/', '.') + "." + name for name, t in NODE_CLASS_MAPPINGS.items()]
node_python_types = list(NODE_CLASS_MAPPINGS.values())
main_pys = [] # TODO: where is the prestart file?
repo_name = "ComfyUIManager"
plugin = None
dicts = {t.CATEGORY.replace('/', '.') + '.' + name: node_info_to_node_dict(t.CATEGORY.replace('/', '.') + '.' + name, node_info(name), t) for name, t in NODE_CLASS_MAPPINGS.items()}

installed_plugins_cache_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), "installed_plugins_cache.json")


def monkey_patch_comfy_nodes(t):
    original_fn = getattr(t, '__init__')
    execute_fn = getattr(t, t.FUNCTION)

    # Modify __init__() function of the class so that we can call
    # (_node_id=node_id, _sio=sio, _loop=loop, _sid=sid, _uuid=variable.sid2uuid[sid])
    # Although ComfyUI plugin will never use them

    def modified_init(self, *_args, _node_id=None, _sio=None, _loop=None, _sid=None, _uuid=None, **_kwargs) -> None:
        self._node_id = _node_id
        self._sio = _sio
        self._loop = _loop
        self._sid = _sid
        self._uuid = _uuid
        original_fn(self, *_args, **_kwargs)

    setattr(t, '__init__', modified_init)

    def dummy_function(*args, **kwargs) -> None:
        return None

    setattr(t, 'on_state_change', dummy_function)

    def execute(self, *args, **kwargs) -> Dict[str, Any]:
        ret = execute_fn(self, *args, **kwargs)
        if type(ret) == tuple:
            assert len(ret) >= len(self.RETURN_TYPES), f"Return type length {len(ret)} is not equal to or greater than the length of RETURN_TYPES {len(self.RETURN_TYPES)}."
            ret_names = self.RETURN_NAMES if hasattr(self, 'RETURN_NAMES') else self.RETURN_TYPES
            ret = {name: ret[i] for i, name in enumerate(ret_names)}
            # The rest of ret are UI elements
            return ret
        elif type(ret) == dict:
            # That means only UI element is returned
            return {'output': None}
        else:
            raise ValueError(f"Return type {type(ret)} cannot be correctly parsed. Please report this issue to https://github.com/KokeCacao/KatUI/issues")

    def _execute(self, *args, **kwargs) -> Dict[str, Any]:
        with torch.no_grad():
            # TODO: give user option whether to use torch.no_grad() or not
            return execute(self, *args, **kwargs)

    setattr(t, 'execute', execute)
    setattr(t, '_execute', _execute)


for t in node_python_types:
    monkey_patch_comfy_nodes(t)

node_loader = variable.node_loader
assert node_loader is not None

node_loader.add_plugin(
    node_str_types=node_str_types,
    node_python_types=node_python_types,
    main_pys=main_pys,
    repo_name=pathlib.Path(repo_name),
    plugin=plugin,
    dicts=dicts,
)

from fastapi import Request
from backend import variable
from backend.app import app
from backend.utils import SafeJSONResponse

from nodes.ComfyUIManager._external_functions import *


# not using ComfyUIManager's gitclone_install because I don't want to add git to the dependencies
def gitclone_install(files):
    print(f"install: {files}")
    for url in files:
        if not is_valid_url(url):
            print(f"Invalid git url: '{url}'")
            return False

        if url.endswith("/"):
            url = url[:-1]
        try:
            print(f"Download: git clone '{url}'")
            repo_name = os.path.splitext(os.path.basename(url))[0]
            repo_path = os.path.join(custom_nodes_path, repo_name)

            # Clone the repository from the remote URL
            # if platform.system() == 'Windows':
            #     res = run_script([sys.executable, git_script_path, "--clone", custom_nodes_path, url])
            #     if res != 0:
            #         return False
            # else:
            #     repo = git.Repo.clone_from(url, repo_path, recursive=True, progress=GitProgress())
            #     repo.git.clear_cache()
            #     repo.close()

            # clone github repository to custom_nodes_path
            try:
                if not url.endswith(".git"):
                    url += ".git"
                # TODO: check if the plugin is already installed
                print(f"Installing plugin from {url}")
                out = subprocess.check_output(['git', 'clone', url], cwd=custom_nodes_path, text=True).strip()
                print(f"Executed \"git clone {url}\" -> {out}")
            except subprocess.CalledProcessError as e:
                raise Exception(f"Failed to install plugin from {url} due to {e}")

            if not execute_install_script(url, repo_path):
                return False

        except Exception as e:
            print(f"Install(git-clone) error: {url} / {e}", file=sys.stderr)
            return False

    print("Installation was successful.")
    return True


@app.get('/ComfyUIManager/plugins')
async def comfyui_manager_plugin(request: Request):
    """Client request to get installed ComfyUI plugins
    """
    if variable.node_loader is None:
        return SafeJSONResponse(status_code=500, content={"error": "Server failed to load nodes."})

    installed_plugins_cache = {}
    if os.path.exists(installed_plugins_cache_file):
        with open(installed_plugins_cache_file, 'r') as f:
            installed_plugins_cache = json.load(f)

    for name, plugin in installed_plugins_cache.items():
        plugin['path'] = f"installed somewhere in {custom_nodes_path}"

    return SafeJSONResponse(status_code=200, content=installed_plugins_cache)


@app.post('/ComfyUIManager/plugins/install')
async def comfyui_manager_install_plugin(request: Request, payload: Dict[Any, Any]):
    """Client request to install ComfyUI plugin

    Args:
        payload (Dict[Any, Any]): data of the plugin
            e.g. {
                    "name": "BrevImage",
                    "author": "underclockeddev",
                    "is_single_file": true,
                    "url": "https://github.com/bkunbargi/BrevImage",
                    "description": "Nodes:BrevImage. ComfyUI Load Image From URL",
                    "files": [
                        "https://github.com/bkunbargi/BrevImage/raw/main/BrevLoadImage.py"
                    ],
                    "install_type": "copy"
                }
    """
    if variable.node_loader is None:
        return SafeJSONResponse(status_code=500, content={"error": "Server failed to load nodes."})

    files: List[str] = payload['files']
    install_type: Literal['git-clone', 'copy', 'unzip'] = payload['install_type']

    if install_type == 'git-clone':
        gitclone_install(files)
    elif install_type == 'copy':
        copy_install(files)
    elif install_type == 'unzip':
        unzip_install(files)
    else:
        raise ValueError(f"Invalid install type {install_type}")

    installed_plugins_cache = {}
    if os.path.exists(installed_plugins_cache_file):
        with open(installed_plugins_cache_file, 'r') as f:
            installed_plugins_cache = json.load(f)
    installed_plugins_cache[payload['name']] = payload
    with open(installed_plugins_cache_file, 'w') as f:
        json.dump(installed_plugins_cache, f)

    # reload plugins
    variable.node_loader.__init__(external_node_path=variable.node_loader.external_node_path)
    variable.node_loader.execute_mainpy_files(variable_module=variable)

    return SafeJSONResponse(status_code=200, content={})


@app.post('/ComfyUIManager/plugins/remove')
async def comfyui_manager_remove_plugin(request: Request, payload: Dict[Any, Any]):
    """Client request to remove ComfyUI plugin

    Args:
        payload (Dict[Any, Any]): data of the plugin
    """
    if variable.node_loader is None:
        return SafeJSONResponse(status_code=500, content={"error": "Server failed to load nodes."})

    files: List[str] = payload['files']
    install_type: Literal['git-clone', 'copy', 'unzip'] = payload['install_type']

    if install_type == 'git-clone':
        gitclone_uninstall(files)
    elif install_type == 'copy':
        copy_uninstall(files)
    elif install_type == 'unzip':
        return SafeJSONResponse(status_code=500, content={"error": "Since ComfyUIManager in ComfyUI doesn't support uninstall anything that was installed using unzip method, please remove the files manually."})
    else:
        raise ValueError(f"Invalid install type {install_type}")

    if os.path.exists(installed_plugins_cache_file):
        with open(installed_plugins_cache_file, 'r') as f:
            installed_plugins_cache = json.load(f)
        installed_plugins_cache.pop(payload['name'], None)
        with open(installed_plugins_cache_file, 'w') as f:
            json.dump(installed_plugins_cache, f)

    # reload plugins
    variable.node_loader.__init__(external_node_path=variable.node_loader.external_node_path)
    variable.node_loader.execute_mainpy_files(variable_module=variable)

    return SafeJSONResponse(status_code=200, content={})
