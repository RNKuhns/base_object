# -*- coding: utf-8 -*-
# copyright: base_object developers, BSD-3-Clause License (see LICENSE file)
"""Utility functions to perform input checks."""
from __future__ import annotations

import math
import numbers
from typing import Any

__all__ = ["is_scalar_nan"]
__author__ = ["RNKuhns"]


def is_scalar_nan(x: Any) -> bool:
    """Test if x is NaN.

    This function is meant to overcome the issue that np.isnan does not allow
    non-numerical types as input, and that np.nan is not float('nan').

    Parameters
    ----------
    x : any type
        The item to be checked to determine if it is a scalar nan value.

    Returns
    -------
    scalar_nan : bool
        True if `x` is a scalar nan value

    Notes
    -----
    This code follows scikit-learn's implementation.

    Examples
    --------
    >>> import numpy as np
    >>> from base_object.utils import is_scalar_nan
    >>> is_scalar_nan(np.nan)
    True
    >>> is_scalar_nan(float("nan"))
    True
    >>> is_scalar_nan(None)
    False
    >>> is_scalar_nan("")
    False
    >>> is_scalar_nan([np.nan])
    False
    """
    return isinstance(x, numbers.Real) and math.isnan(x)
