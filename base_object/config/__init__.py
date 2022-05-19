# -*- coding: utf-8 -*-
"""Functionality for configuring the the ``base_object`` package."""
# Includes functionality like get_config, set_config, and config_context
# that is similar to scikit-learn. However,the code was altered to make
# define the configuration as a class importable as a module similar to Tensorly
# Modifications were also made to make things more easily extensible, by
# driving the configuration settings based on a registry of configurations
import os
import sys
import threading
import types
import warnings
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional, Tuple, TypedDict

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal  # type: ignore

__author__: List[str] = ["RNKuhns"]


class ConfigParamSettingInfo(TypedDict):
    """Define types of the setting information for a given config parameter."""

    env_name: str
    values: Tuple[Any, ...]
    default: Any


_CONFIG_REGISTRY: Dict[str, ConfigParamSettingInfo] = {
    "print_changed_only": {
        "env_name": "BASE_OBJECT_PRINT_CHANGED_ONLY",
        "values": (True, False),
        "default": True,
    },
    "display": {
        "env_name": "BASE_OBJECT_DISPLAY",
        "values": ("text", "diagram"),
        "default": "text",
    },
}

_GLOBAL_CONFIG: Dict[str, Any] = {
    config_name: os.environ.get(config_info["env_name"], config_info["default"])
    for config_name, config_info in _CONFIG_REGISTRY.items()
}

_THREAD_LOCAL_DATA = threading.local()


class ConfigManager(types.ModuleType):
    """Configure the package."""

    _default_config = _GLOBAL_CONFIG.copy()
    _threadlocal = _THREAD_LOCAL_DATA

    @classmethod
    def _get_threadlocal_config(cls) -> Dict[str, Any]:
        """Get a threadlocal **mutable** configuration.

        If the configuration does not exist, copy the default global configuration.

        Returns
        -------
        threadlocal_global_config : dict
            Threadlocal global config or copy of default global configuration.
        """
        if not hasattr(cls._threadlocal, "global_config"):
            cls._threadlocal.global_config = cls._default_config.copy()
        threadlocal_global_config = cls._threadlocal.global_config
        return threadlocal_global_config

    @classmethod
    def get_config_os_env_names(cls) -> List[str]:
        """Retrieve the os environment names for configurable settings.

        Returns
        -------
        env_names : list
            The os environment names that can be used to set configurable settings.

        See Also
        --------
        config_context :
            Configuration context manager.
        get_config :
            Retrieve current global configuration values.
        get_default_config :
            Return default global configuration values.
        set_config :
            Set global configuration.
        set_default_config :
            Reset configuration to default.

        Examples
        --------
        >>> from base_object.config import get_config_os_env_names
        >>> get_config_os_env_names()
        ['BASE_OBJECT_PRINT_CHANGED_ONLY', 'BASE_OBJECT_DISPLAY']
        """
        return [config_info["env_name"] for config_info in _CONFIG_REGISTRY.values()]

    @classmethod
    def get_default_config(cls) -> Dict[str, Any]:
        """Retrive the default global configuration.

        Returns
        -------
        config : dict
            The default configurable settings (keys) and their default values (values).

        See Also
        --------
        config_context :
            Configuration context manager.
        get_config :
            Retrieve current global configuration values.
        get_config_os_env_names :
            Retrieve os environment names that can be used to set configuration.
        set_config :
            Set global configuration.
        set_default_config :
            Reset configuration to default.

        Examples
        --------
        >>> from base_object.config import get_default_config
        >>> get_default_config()
        {'print_changed_only': True, 'display': 'text'}
        """
        return _GLOBAL_CONFIG.copy()

    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Retrieve current values for configuration set by :meth:`set_config`.

        Returns
        -------
        config : dict
            The configurable settings (keys) and their default values (values).

        See Also
        --------
        config_context :
            Configuration context manager.
        get_config_os_env_names :
            Retrieve os environment names that can be used to set configuration.
        get_default_config :
            Return default global configuration values.
        set_config :
            Set global configuration.
        set_default_config :
            Reset configuration to default.

        Examples
        --------
        >>> from base_object.config import get_config
        >>> get_config()
        {'print_changed_only': True, 'display': 'text'}
        """
        return cls._get_threadlocal_config().copy()

    @classmethod
    def set_config(
        cls,
        print_changed_only: Optional[bool] = None,
        display: Literal["text", "diagram"] = None,
        local_threadsafe: bool = False,
    ) -> None:
        """Set global configuration.

        Parameters
        ----------
        print_changed_only : bool, default=None
            If True, only the parameters that were set to non-default
            values will be printed when printing a BaseObject instance. For example,
            ``print(SVC())`` while True will only print 'SVC()', but would print
            'SVC(C=1.0, cache_size=200, ...)' with all the non-changed parameters
            when False. If None, the existing value won't change.
        display : {'text', 'diagram'}, default=None
            If 'diagram', instances inheritting from BaseOBject will be displayed
            as a diagram in a Jupyter lab or notebook context. If 'text', instances
            inheritting from BaseObject will be displayed as text. If None, the
            existing value won't change.
        local_threadsafe : bool, default=False
            If False, set the backend as default for all threads.

        Returns
        -------
        None : None
            No output returned.

        See Also
        --------
        config_context :
            Configuration context manager.
        get_config :
            Retrieve current global configuration values.
        get_config_os_env_names :
            Retrieve os environment names that can be used to set configuration.
        get_default_config :
            Return default global configuration values.
        set_default_config :
            Reset configuration to default.

        Examples
        --------
        >>> from base_object.config import get_config, set_config
        >>> get_config()
        {'print_changed_only': True, 'display': 'text'}
        >>> set_config(display='diagram')
        >>> get_config()
        {'print_changed_only': True, 'display': 'diagram'}
        """
        local_config = cls._get_threadlocal_config()

        if print_changed_only is not None:
            local_config["print_changed_only"] = print_changed_only
        if display is not None:
            local_config["display"] = display

        if not local_threadsafe:
            cls._default_config = local_config

    @classmethod
    def set_default_config(cls) -> None:
        """Reset the configuration to the default.

        Returns
        -------
        None : None
            No output returned.

        See Also
        --------
        config_context :
            Configuration context manager.
        get_config :
            Retrieve current global configuration values.
        get_config_os_env_names :
            Retrieve os environment names that can be used to set configuration.
        get_default_config :
            Return default global configuration values.
        set_config :
            Set global configuration.

        Examples
        --------
        >>> from base_object.config import get_config, get_default_config, \
            set_config, set_default_config
        >>> get_default_config()
        {'print_changed_only': True, 'display': 'text'}
        >>> set_config(display='diagram')
        >>> get_config()
        {'print_changed_only': True, 'display': 'diagram'}
        >>> set_default_config()
        >>> get_config()
        {'print_changed_only': True, 'display': 'text'}
        """
        default_config = cls.get_default_config()
        cls.set_config(**default_config)

    @classmethod
    @contextmanager
    def config_context(
        cls,
        print_changed_only: Optional[bool] = None,
        display: Literal["text", "diagram"] = None,
        local_threadsafe: bool = False,
    ) -> Iterator[None]:
        """Context manager for global configuration.

        Parameters
        ----------
        print_changed_only : bool, default=None
            If True, only the parameters that were set to non-default
            values will be printed when printing a BaseObject instance. For example,
            ``print(SVC())`` while True will only print 'SVC()', but would print
            'SVC(C=1.0, cache_size=200, ...)' with all the non-changed parameters
            when False. If None, the existing value won't change.
        display : {'text', 'diagram'}, default=None
            If 'diagram', instances inheritting from BaseOBject will be displayed
            as a diagram in a Jupyter lab or notebook context. If 'text', instances
            inheritting from BaseObject will be displayed as text. If None, the
            existing value won't change.
        local_threadsafe : bool, default=False
            If False, set the backend as default for all threads.

        Yields
        ------
        None

        See Also
        --------
        set_config :
            Set global configuration.
        get_config :
            Retrieve current values of the global configuration.
        get_config_os_env_names :
            Retrieve os environment names that can be used to set configuration.
        get_default_config :
            Return default global configuration values.
        set_default_config :
            Reset configuration to default.

        Notes
        -----
        All settings, not just those presently modified, will be returned to
        their previous values when the context manager is exited.

        Examples
        --------
        >>> from base_object.config import config_context
        >>> with config_context(display='diagram'):
        ...     pass
        """
        old_config = cls.get_config()
        cls.set_config(
            print_changed_only=print_changed_only,
            display=display,
            local_threadsafe=local_threadsafe,
        )

        try:
            yield
        finally:
            cls.set_config(**old_config)

    @classmethod
    def initialize_config(cls) -> None:
        """Initialize the package configuration.

        The package configuration is initialized according to the following
        hierarchy:

        - Any configurations set in the os environment variables are retrieved
        - Configurable settings not set in os environment have their default values
          retrieved
        - Set config is used to initialize the configuration.

        Returns
        -------
        None : None
            No output returned.

        See Also
        --------
        config_context :
            Configuration context manager.
        get_config :
            Retrieve current values of the global configuration.
        get_config_os_env_names :
            Retrieve os environment names that can be used to set configuration.
        get_default_config :
            Return default global configuration values.
        set_config :
            Set global configuration.
        set_default_config :
            Reset configuration to default.
        """
        config_setting: Any
        config_settings: Dict[str, Any] = {}
        for config_name in _CONFIG_REGISTRY:
            config_setting = os.environ.get(
                _CONFIG_REGISTRY[config_name]["env_name"],
                cls._default_config[config_name],
            )
            if config_setting == "True":
                config_setting = True
            if config_setting == "False":
                config_setting = False
            if config_setting not in _CONFIG_REGISTRY[config_name]["values"]:
                msg = f"{_CONFIG_REGISTRY[config_name]['env_name']} should be one of "
                msg += (
                    f"{', '.join(map(repr, _CONFIG_REGISTRY[config_name]['values']))}."
                )
                msg += "Using default value for this configuration as a result."
                warnings.warn(msg, UserWarning)
                config_setting = cls._default_config[config_name]
            config_settings[config_name] = config_setting

        cls._default_config = config_settings
        cls.set_config(**config_settings)

    def __dir__(self) -> List[str]:
        """Indicate items in the scope."""
        return [
            "config_context",
            "get_config",
            "get_config_os_env_names",
            "get_default_config",
            "set_config",
            "set_default_config",
            "ConfigManager",
        ]


# Initialise the backend to the default one
ConfigManager.initialize_config()

sys.modules[__name__].__class__ = ConfigManager
