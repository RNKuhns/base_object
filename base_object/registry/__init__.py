# -*- coding: utf-8 -*-
""":mod:`base_object.registry` provides a registry of package functionality."""
from typing import List

from base_object.registry._lookup import all_objects, package_metadata

__all__: List[str] = ["package_metadata", "all_objects"]
__author__: List[str] = ["RNKuhns"]
