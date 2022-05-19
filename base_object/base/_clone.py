# -*- coding: utf-8 -*-
# copyright: base_object developers, BSD-3-Clause License (see LICENSE file)
"""Create a copied instance of a class inheritting from BaseObject."""
import copy
from typing import Dict, FrozenSet, List, Set, Tuple, TypeVar, Union

from base_object.base._base import BaseObject

__all__: List[str] = ["clone"]
__author__: List[str] = ["RNKuhns"]


T = TypeVar("T", bound="BaseObject")


def clone(
    base_object: Union[T, Dict, FrozenSet, List, Set, Tuple], safe: bool = True
) -> Union[T, Dict, FrozenSet, List, Set, Tuple]:
    """Construct a new instance of a BaseObject instance with the same parameters.

    Clone does a deep copy. It returns a new BaseObject with the same parameters
    that has not yet set any state dependent parameters.

    Parameters
    ----------
    base_object : {list, tuple, set, frozenset, dict} of BaseObject instances \
            or a single BaseObject instance
        The BaseObject instance or group of BaseObject instances to be cloned.
    safe : bool, default=True
        If safe is False, clone will fall back to a deep copy on objects
        that are not instances of BaseObject.

    Returns
    -------
    BaseObject : base_object.base.BaseObject
        The deep copy of the input. Returns a cloned BaseObject instance if the
        input was a BaseObject.

    Notes
    -----
    When cloning object's that have a `random_state` parameter, if the
    parameter value is an integer, an *exact clone* is
    returned: the clone and the original object will give the exact same
    results. If the `random_state` parameter has a non-integer value, a
    *statistical clone* is returned: the clone might return different results
    from the original object. See scikit-learn's discussion on randomness
    for more information.
    """
    object_type: type = type(base_object)
    if isinstance(base_object, (list, tuple, set, frozenset)):
        return object_type([clone(bo, safe=safe) for bo in base_object])
    elif isinstance(base_object, dict):
        return {
            clone(key, safe=False): clone(value, safe=safe)
            for key, value in base_object.items()
        }
    elif not hasattr(base_object, "get_params") or isinstance(base_object, type):
        if not safe:
            return copy.deepcopy(base_object)
        else:
            if isinstance(base_object, type):
                raise TypeError(
                    "Cannot clone object. You should provide an instance of "
                    "``BaseObject`` instead of a class."
                )
            else:
                raise TypeError(
                    f"Cannot clone object {repr(base_object)} of type "
                    f"{type(base_object)}. It does not seem to inherit from "
                    "BaseObject, or a scikit-learn or sktime compliant class "
                    "that implements a `get_params` method."
                )
    new_object_params = base_object.get_params(deep=False)
    for name, param in new_object_params.items():
        new_object_params[name] = clone(param, safe=False)
    new_object = base_object.__class__(**new_object_params)  # type: ignore
    params_set = new_object.get_params(deep=False)

    # quick sanity check of the parameters of the clone
    unequal_params = []
    for name in new_object_params:
        param1 = new_object_params[name]
        param2 = params_set[name]
        if param1 is not param2:
            unequal_params.append(name)
    if len(unequal_params) > 0:
        raise RuntimeError(
            f"Cannot clone object {base_object}. The constructor either does not "
            f"set or modifies parameter {', '.join(unequal_params)}."
        )
    return new_object
