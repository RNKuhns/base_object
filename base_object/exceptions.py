# -*- coding: utf-8 -*-
# copyright: base_object developers, BSD-3-Clause License (see LICENSE file)
"""Custom exceptions used in base_object."""
__all__ = ["NotFittedError", "NoTagsError", "NoTagsDynamicError"]
__author__ = ["RNKuhns"]


class NotFittedError(ValueError, AttributeError):
    """Exception class to raise if an instance of BaseEstimator is used before fitting.

    References
    ----------
    [1] Based on scikit-learn's NotFittedError
    """


class NoTagsError(ValueError, AttributeError):
    """Exception class raised if an object does not have expected tag attribute.

    Notes
    -----
    Follows convention used in scikit-learn when creating custom errors.
    """


class NoTagsDynamicError(ValueError, AttributeError):
    """Exception class raised if an object does not have expected dynamic tag attribute.

    Notes
    -----
    Follows convention used in scikit-learn when creating custom errors.
    """
