# -*- coding: utf-8 -*-
# copyright: base_object developers, BSD-3-Clause License (see LICENSE file)
""":mod:`base_object.base` provides base classes with a scikit-learn style design."""
from typing import List

from base_object.base._base import BaseObject
from base_object.base._clone import clone

__all__: List[str] = ["BaseObject", "clone"]
__author__: List[str] = ["RNKuhns"]
