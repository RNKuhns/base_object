# -*- coding: utf-8 -*-
"""Lookup package metadata."""
import importlib
import inspect
import pkgutil
import sys
from pathlib import Path
from types import FunctionType, ModuleType
from typing import Any, Dict, List, Optional, Tuple, Type, Union

from base_object.base import BaseObject

# Conditionally import TypedDict based on Python version
if sys.version_info >= (3, 9):
    from typing import TypedDict
else:
    from typing_extensions import TypedDict

__all__: List[str] = ["package_metadata", "all_objects"]
__author__: List[str] = ["RNKuhns"]

# TOP_LEVEL_PACKAGE_NAME: str = "base_object"
SOURCE_ROOT: str = str(Path(__file__).parent.parent)
# MODULES_TO_IGNORE: Tuple[str, ...] = ("tests", "examples")
# BASE_CLASSES: Tuple[Type[BaseObject], ...] = (BaseObject,)


class ClassInfo(TypedDict):
    """Type definitions for information on a module's classes."""

    klass: Type
    name: str
    description: str
    is_concrete_implementation: bool
    is_base_class: bool
    is_base_object: bool
    authors: Optional[Union[List[str], str]]
    module_name: str


class FunctionInfo(TypedDict):
    """Type definitions for information on a module's functions."""

    func: FunctionType
    name: str
    description: str
    module_name: str


class ModuleInfo(TypedDict):
    """Module information type definitions."""

    path: str
    name: str
    classes: Dict[str, ClassInfo]
    functions: Dict[str, FunctionInfo]
    __all__: List[str]
    authors: str
    is_package: bool
    contains_concrete_class_implementations: bool
    contains_base_classes: bool
    contains_base_objects: bool


def _is_non_public_module(module_name: str) -> bool:
    """Determine if a module is non-public or not.

    Parameters
    ----------
    module_name : str
        Name of the module.

    Returns
    -------
    is_non_public : bool
        Whether the module is non-public or not.
    """
    is_non_public: bool = "._" in module_name
    return is_non_public


def _is_ignored_module(
    module_name: str, modules_to_ignore: Union[List[str], Tuple[str]] = None
) -> bool:
    """Determine if module is one of the ignored modules.

    Paramters
    ---------
    module_name : str
        Name of the module.
    modules_to_ignore : list[str] or tuple[str]
        The modules that should be ignored when walking the package.

    Returns
    -------
    is_ignored : bool
        Whether the module is an ignrored module or not.
    """
    is_ignored: bool
    if modules_to_ignore is not None:
        is_ignored = any(part in modules_to_ignore for part in module_name.split("."))
    else:
        is_ignored = False
    return is_ignored


def package_metadata(
    path: str = SOURCE_ROOT,
    top_level_package_name: Optional[str] = None,
    recursive: bool = True,
    prefix: str = "",
    exclude_nonpublic_modules: bool = True,
    modules_to_ignore: Union[List[str], Tuple[str]] = ("tests",),
    package_base_classes: Tuple[Union[type, Tuple[Any, ...]]] = (BaseObject,),
) -> Dict[str, ModuleInfo]:
    """Return a dictionary mapping all package modules to their metadata.

    Parameters
    ----------
    path : str, default=None
        String path that should be used as root to find any modules or submodules.
    recursive : bool, default=True
        Whether to recursively walk through submodules.

        - If True, then submoudles of submodules and so on are found.
        - If False, then only first-level submoundes of `package` are found.
    prefix : str, default=""
        The prefix to use when returning module names on the `path`.
    exclude_non_public_modules : bool, default=True
        Whether to exclude nonpublic modules (modules where names start with
        a leading underscore).
    modules_to_ignore : list[str] or tuple[str], default=()
        The modules that should be ignored when walking the package.

    Returns
    -------
    module_info: dict
        Dictionary mapping string submodule name (key) to a dictionary of the
        submodules metadata.
    """
    if not isinstance(path, str):
        raise ValueError("Provide parameter `path` as a string .")

    module_info: Dict[str, ModuleInfo] = {}
    for _loader, name, is_pkg in pkgutil.walk_packages(path=[path], prefix=prefix):
        # Used to skip-over ignored modules and non-public modules
        if _is_ignored_module(name, modules_to_ignore=modules_to_ignore) or (
            exclude_nonpublic_modules and _is_non_public_module(name)
        ):
            continue

        if isinstance(top_level_package_name, str):
            full_name: str = top_level_package_name + "." + name
        else:
            full_name = name

        try:
            module: ModuleType = importlib.import_module(full_name)
            designed_imports: List[str] = getattr(module, "__all__", [])
            authors: Union[str, List[str]] = getattr(module, "__author__", [])
            if isinstance(authors, (list, tuple)):
                authors = ", ".join(authors)
            # Compile information on classes in the module
            module_classes: Dict[str, ClassInfo] = {}
            for name, klass in inspect.getmembers(module, inspect.isclass):
                klass_authors = getattr(klass, "__author__", authors)
                if isinstance(klass_authors, (list, tuple)):
                    klass_authors = ", ".join(klass_authors)
                if klass.__module__ == module.__name__ or name in designed_imports:
                    module_classes[name] = {
                        "klass": klass,
                        "name": klass.__name__,
                        "description": klass.__doc__.split("\n")[0],
                        "is_concrete_implementation": (
                            issubclass(klass, package_base_classes)
                            and klass not in package_base_classes
                        ),
                        "is_base_class": klass in package_base_classes,
                        "is_base_object": issubclass(klass, BaseObject),
                        "authors": klass_authors,
                        "module_name": module.__name__,
                    }

            module_functions: Dict[str, FunctionInfo] = {}
            for name, func in inspect.getmembers(module, inspect.isfunction):
                if func.__module__ == module.__name__ or name in designed_imports:
                    module_functions[name] = {
                        "func": func,
                        "name": func.__name__,
                        "description": func.__doc__.split("\n")[0],
                        "module_name": module.__name__,
                    }

            # Combine all the information on the module together
            module_info[full_name] = {
                "path": getattr(_loader, "path", ""),
                "name": module.__name__,
                "classes": module_classes,
                "functions": module_functions,
                "__all__": designed_imports,
                "authors": authors,
                "is_package": is_pkg,
                "contains_concrete_class_implementations": False,
                "contains_base_classes": any(
                    v["is_base_class"] for v in module_classes.values()
                ),
                "contains_base_objects": any(
                    v["is_base_object"] for v in module_classes.values()
                ),
            }

        except ImportError:
            continue

        if recursive and is_pkg:
            name_ending: str = name.split(".")[1] if "." in name else name
            updated_path: str = "\\".join([path, name_ending])
            module_info.update(package_metadata(path=updated_path, prefix=name + "."))

    return module_info


def all_objects(
    path: Optional[str] = None, prefix: str = "", filter_class: object = None
) -> List[ClassInfo]:
    """Find all classes inheritting from BaseObject.

    Returns
    -------
    base_objects : dict
    """
    if path is not None and not isinstance(path, str):
        raise ValueError("Provide parameter `path` as a string .")
    if not isinstance(prefix, str):
        raise ValueError("Provide parameter `prefix` as a string.")

    registry: Dict[str, ModuleInfo] = package_metadata(path=path, prefix=prefix)

    # Filter registry to only include classes that contain BaseObjects
    source_mods = {
        k: v for k, v in registry.items() if v["contains_base_objects"] is True
    }

    # Now filter the classes in the filter modules to just retain those
    # classes inheritting from BaseObject
    base_objects: List[ClassInfo] = []
    for mod_info in source_mods.values():
        for class_info in mod_info["classes"].values():
            issubclass(class_info["klass"], BaseObject)
            if class_info["is_base_object"]:
                if filter_class is not None and (
                    issubclass(class_info["klass"], filter_class)
                ):
                    base_objects.append(class_info)

    return base_objects
