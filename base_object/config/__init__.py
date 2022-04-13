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

__author__ = ["RNKuhns"]

_CONFIG_REGISTRY = {
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
_GLOBAL_CONFIG = {
    config_name: os.environ.get(config_info["env_name"], config_info["default"])
    for config_name, config_info in _CONFIG_REGISTRY.items()
}
_THREAD_LOCAL_DATA = threading.local()


class ConfigManager(types.ModuleType):
    """Configure the base_object package."""

    _default_config = _GLOBAL_CONFIG
    _threadlocal = _THREAD_LOCAL_DATA
    _environment_default_var = [
        "BASE_OBJECT_PRINT_CHANGED_ONLY",
        "BASE_OBJECT_DISPLAY",
    ]

    @classmethod
    def _get_threadlocal_config(cls):
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
    def get_config(cls):
        """Retrieve current values for configuration set by :meth:`set_config`.

        Returns
        -------
        config : dict
            Keys are parameter names that can be passed to :meth:`set_config`.

        See Also
        --------
        config_context :
            Context manager for global configuration.
        set_config :
            Set global configuration.

        Examples
        --------
        >>> from base_object.config import get_config
        >>> get_config()
        {'print_changed_only': True, 'display': 'text'}
        """
        return cls._get_threadlocal_config().copy()

    @classmethod
    def set_config(cls, print_changed_only=None, display=None, local_threadsafe=False):
        """Set global configuration.

        Parameters
        ----------
        print_changed_only : bool, default=None
            If True, only the parameters that were set to non-default
            values will be printed when printing an estimator. For example,
            ``print(SVC())`` while True will only print 'SVC()' while the default
            behaviour would be to print 'SVC(C=1.0, cache_size=200, ...)' with
            all the non-changed parameters.
        display : {'text', 'diagram'}, default=None
            If 'diagram', estimators will be displayed as a diagram in a Jupyter
            lab or notebook context. If 'text', estimators will be displayed as
            text. Default is 'text'.
        local_threadsafe : bool, default=False
            If False, set the backend as default for all threads.

        See Also
        --------
        config_context :
            Context manager for global scikit-learn configuration.
        get_config :
            Retrieve current values of the global configuration.

        Examples
        --------
        >>> from base_object.config import set_config
        >>> set_config(display='diagram')
        """
        local_config = cls._get_threadlocal_config()

        if print_changed_only is not None:
            local_config["print_changed_only"] = print_changed_only
        if display is not None:
            local_config["display"] = display

        if not local_threadsafe:
            cls._default_config = local_config

    @classmethod
    @contextmanager
    def config_context(
        cls, print_changed_only=None, display=None, local_threadsafe=False
    ):
        """Context manager for global configuration.

        Parameters
        ----------
        print_changed_only : bool, default=None
            If True, only the parameters that were set to non-default
            values will be printed when printing an estimator. For example,
            ``print(SVC())`` while True will only print 'SVC()', but would print
            'SVC(C=1.0, cache_size=200, ...)' with all the non-changed parameters
            when False. If None, the existing value won't change.
            The default value is None.
        display : {'text', 'diagram'}, default=None
            If 'diagram', estimators will be displayed as a diagram in a Jupyter
            lab or notebook context. If 'text', estimators will be displayed as
            text. If None, the existing value won't change.
            The default value is None.
        local_threadsafe : bool, default=False
            If False, set the backend as default for all threads.

        Yields
        ------
        None

        See Also
        --------
        set_config :
            et global scikit-learn configuration.
        get_config :
            Retrieve current values of the global configuration.

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
    def initialize_config(cls):
        """Initialize the package configuration.

        1) retrieve the default backend name from the `TENSORLY_BACKEND` environment
            variable if not found, use _DEFAULT_BACKEND
        2) sets the backend to the retrieved backend name
        """
        config_settings = {}
        for config_name in _CONFIG_REGISTRY:
            config_setting = os.environ.get(
                _CONFIG_REGISTRY[config_name]["env_name"],
                cls._default_config[config_name],
            )
            if config_setting not in _CONFIG_REGISTRY[config_name]["values"]:
                msg = f"{_CONFIG_REGISTRY[config_name]['env_name']} should be one of "
                msg += (
                    f"{', '.join(map(repr, _CONFIG_REGISTRY[config_name]['values']))}."
                )
                warnings.warn(msg, UserWarning)
                config_setting = cls._default_config[config_name]
            config_settings[config_name] = config_setting

        cls._default_config = config_settings
        cls.set_config(**config_settings)

    def __dir__(cls):
        """Indiate items in the scope."""
        return ["config_context", "get_config", "set_config", "ConfigManager"]


# Initialise the backend to the default one
ConfigManager.initialize_config()

sys.modules[__name__].__class__ = ConfigManager
