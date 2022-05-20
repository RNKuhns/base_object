# -*- coding: utf-8 -*-
# copyright: base_object developers, BSD-3-Clause License (see LICENSE file)
"""Base classes for objects with scikit-learn and sktime like design principles."""
from __future__ import annotations

import collections
import copy
import inspect
import re
import warnings
from typing import (
    Any,
    ClassVar,
    DefaultDict,
    Dict,
    Iterable,
    List,
    Optional,
    Tuple,
    TypeVar,
    Union,
    overload,
)

from base_object import __version__
from base_object.config import get_config  # type: ignore
from base_object.exceptions import NoTagsError
from base_object.utils._object_html_repr import _object_html_repr

__all__: List[str] = ["BaseObject"]
__author__: List[str] = ["RNKuhns"]

T = TypeVar("T", bound="BaseObject")


class BaseObject:
    """Base class for parametric objects following scikit-learn and sktime design.

    BaseObject incorporates design principles from scikit-learn's BaseEstimator [1]_
    and sktime's tag interface [2]_. In some cases, the included code follows
    the implementation in these packages very closely. However, it also leverages
    the combined design pattern to provide additional functionality.

    In particular, Scikit-learn's parameter getting and setting interface is updated.
    The update allows getting and setting parameters that include "named" instances
    inheriting from ``BaseObject`` to be handled via tags in within BaseObject (rather
    than a base compositer subclass, like in scikit-learn or sktime).

    By decoupling these design principles from scikit-learn and sktime, they can more
    easily be incorporated into a wider range of Python projects that would
    not otherwise need to rely on scikit-learn or sktime as a dependency.

    Notes
    -----
    When using ``BaseObject`` you should follow the following conventions that
    build on common Python, scikit-learn or sktime design patterns:

    - Specify all parameters in the classes ``__init__`` as explicit keyword arguments.
      No ``args`` or ``kwargs`` should be used to set class parameters.
    - Keyword arguments should be stored in the class as attributes with the same name.
      These should be documented in the parameters section of the docstring, and
      are not documented in the attributes section of the docstring.
    - All instance attributes should be created in ``__init__``. If the attribute is
      not assigned a value until later, initialize it as None.
    - Attributes that depend on the state of the instance's parameters should end in
      an underscore to easily communicate that they are "state" dependent.
    - Start non-public attributes and methods with an underscore (per standard
      Python conventions).
    - Document all attributes that are not parameters in the class docstring's
      attributes section.

    References
    ----------
    .. [1] scikit-learn <https://scikit-learn.org/>`_
    .. [2] `sktime <https://www.sktime.org/>`_

    Examples
    --------
    >>> from base_object.base import BaseObject
    >>> class YourClass(BaseObject):
    ...     def __init__(self, some_parameter: int = None):
    ...         self.some_parameter = some_parameter
    ...         self.some_attribute_that_gets_a_value_later = None
    ...         self.stateful_attribute_assigned_later_ = None

    >>> your_class = YourClass(some_parameter=7)
    >>> params = your_class.get_params()
    >>> params == {'some_parameter': 7}
    True

    # Get the tag used in BaseObject to illustrate the incorporation of
    # sktime's tag interface
    >>> tag = your_class.get_class_tag("named_object_parameters")
    >>> tag is None
    True

    # No dynamic tag overrides were made on the instance using set_tags
    # so get_tag returns the same value as get_class_tag
    >>> tag = your_class.get_tag("named_object_parameters")
    >>> tag is None
    True

    # Instances that inherit from BaseObject print a nice representation
    # just like scikit-learn estimators
    >>> print(your_class)
    YourClass(some_parameter=7)
    """

    _tags: ClassVar[Dict[str, Any]] = {"named_object_parameters": None}

    def __init__(self):
        self._tags_dynamic: Dict[str, Any] = {}
        super().__init__()

    @overload
    def _check_iterable_named_objects(
        self,
        iterable_to_check: Iterable[Tuple[str, BaseObject]],
        raise_error: bool = True,
        allow_dict: bool = False,
        iterable_name: Optional[str] = None,
    ) -> Optional[bool]:
        ...

    @overload
    def _check_iterable_named_objects(
        self,
        iterable_to_check: Iterable[Tuple[str, BaseObject]] | Dict[str, BaseObject],
        raise_error: bool = True,
        allow_dict: bool = True,
        iterable_name: Optional[str] = None,
    ) -> Optional[bool]:
        ...

    def _check_iterable_named_objects(
        self,
        iterable_to_check: Iterable[Tuple[str, BaseObject]] | Dict[str, BaseObject],
        raise_error: bool = True,
        allow_dict: bool = True,
        iterable_name: Optional[str] = None,
    ) -> Optional[bool]:
        """Check if input is an iterable of named BaseObject instances.

        This can be an interable of (str, BaseObject instance) tuples or
        a dictionary with string names as keys and BaseObject instances as valeus
        (if ``allow_dict=True``).

        Parameters
        ----------
        iterable_to_check : Iterable((str, BaseObject)) or {str: BaseObjec}
            The iterable to check for conformance with the named object interface.
            Conforming iterables are:

            - Iterable that contains (str, BaseObject instance tuples)
            - Dictionary with string names as keys and BaseObject instances as values
              if ``allow_dict=True``

        raise_error : bool, default=True
            Whether an error should be raised for non-conforming input. If True,
            an error is raised. If False, then True is returned when
            `iterable_to_check` conforms to expected format and False is returned
            when it is non-confomring.
        allow_dict : bool, default=True
            Whether a dictionary with string names as keys and BaseObject instances
            is an allowed format for providing a iterable of named objects.
            If False, then only iterables that contain (str, BaseObject instance)
            tuples are considered conforming with the named object parameter API.
        iterable_name : str, default=None
            Optional name used to refer to the input `iterable_to_check` when
            raising any errors. Ignored ``raise_error=False``.

        Returns
        -------
        is_named_object_input : bool
            If True, then `iterable_to_check` follows the expected named object
            parameter API.

        Raises
        ------
        ValueError
            If `iterable_to_check` is not an iterable or it does not conform
            to the named object API (e.g., it has non-unique name elements or
            does not follow required formatting conventions).
            Input is not iterable.
        """
        name_str = f"Input {iterable_name}" if iterable_name is not None else "Input"
        # Want to end quickly if the input isn't iterable
        if not isinstance(iterable_to_check, collections.Iterable):
            if raise_error:
                raise ValueError(f"{name_str} is not iterable.")
            else:
                return False

        names: List[str]
        all_unique_names: bool
        if allow_dict and isinstance(iterable_to_check, dict):
            is_expected_format = [
                isinstance(name, str) and isinstance(obj, BaseObject)
                for name, obj in iterable_to_check.items()
            ]
            names = [*iterable_to_check.keys()]
            all_unique_names = True
        else:
            if isinstance(iterable_to_check, dict):
                raise ValueError()
            else:
                is_expected_format = [
                    isinstance(it, tuple)
                    and len(it) == 2
                    and (isinstance(it[0], str) and isinstance(it[1], BaseObject))
                    for it in iterable_to_check
                ]
                names = [it[0] for it in iterable_to_check]
                all_unique_names = len(set(names)) == len(names)

        all_expected_format: bool = all(is_expected_format)
        not_expected_format = [
            item
            for item, is_type in zip(iterable_to_check, is_expected_format)
            if not is_type
        ]
        non_unique_names: List[str] = []
        if not all_unique_names:
            name_count = collections.Counter(iterable_to_check)
            non_unique_names = [c for c in name_count if name_count[c] > 1]

        if raise_error:
            if all_unique_names:
                non_unique_str = ""
            else:
                non_unique_str = (
                    f"{name_str} has non unique name elements: " f"{non_unique_names}."
                )
            if all_expected_format:
                not_exp_format_str = ""
            else:
                not_exp_format_str = (
                    f"{name_str} has items that are not expected format: "
                    f"{not_expected_format}."
                )
            if not all_expected_format or not all_unique_names:
                raise ValueError(
                    f"{name_str} does not conform to the expected "
                    "named base object API.\n"
                    f"{not_exp_format_str}\n{non_unique_str}"
                )

        return all_expected_format and all_unique_names

    @classmethod
    def _get_param_names(cls) -> List[str]:
        """Get parameter names.

        Returns
        -------
        param_names : list of str
            Sorted list of parameter names.
        """
        # Left the fetching of the constructor from the original constructor before
        # scikit-learn style deprecation wrapping (if any). In case this is
        # used with project that also uses this deprecation style
        init = getattr(cls.__init__, "deprecated_original", cls.__init__)
        if init is object.__init__:
            # No explicit constructor to introspect
            return []

        # inspect the constructor arguments for model parameters to represent
        init_signature = inspect.signature(init)
        # Consider the constructor parameters excluding 'self' or non VAR keywords
        parameters = [
            p
            for p in init_signature.parameters.values()
            if p.name != "self" and p.kind != p.VAR_KEYWORD
        ]
        for p in parameters:
            if p.kind == p.VAR_POSITIONAL:
                raise RuntimeError(
                    "Classes inheriting from BaseObject should follow its "
                    "scikit-learn style design conventions. This includes "
                    "specifying parameters in the signature of the class __init__ "
                    "(no args or kwargs).\n"
                    f"{cls} with constructor {init_signature} doesn't "
                    "follow this convention."
                )
        # Return sorted params so we always get same result
        param_names = sorted([p.name for p in parameters])
        return param_names

    def get_params(self, deep: bool = True) -> Dict[str, Any]:
        """Get class parameters.

        Parameters
        ----------
        deep : bool, default=True
            If True, will return the parameters for this class instance and
            contained subobjects that inherit from base_object's BaseObject
            or another class that implements a conforming `get_params` method
            (e.g. e.g., classes inheritting from scikit-learn's BaseEstimator).

        Returns
        -------
        params : dict
            Parameter names mapped to their values.

        Notes
        -----
        This implementation incorporates amended parameter getting logic from
        scikit-learn's BaseEstimator. It amends the logic for handling the
        case when parameter values contained named objects
        (e.g. (name, object instance) tuples as incorporated in
        scikit-learn's _BaseComposition, or a dictionary with string keys (names)).
        """
        # Check if any parameters contain named objects
        named_object_params = self.get_tag("named_object_parameters")
        if named_object_params is None:
            named_object_params = []
        elif isinstance(named_object_params, str):
            named_object_params = [named_object_params]
        params = {}
        for param_name in self._get_param_names():
            value = getattr(self, param_name)
            params[param_name] = value
            if deep:
                if hasattr(value, "get_params"):
                    deep_items = value.get_params().items()
                    params.update((param_name + "__" + k, val) for k, val in deep_items)
                elif param_name in named_object_params:
                    objs = getattr(self, param_name)
                    # Verify that named objects follow expected design pattern
                    self._check_iterable_named_objects(objs, iterable_name=param_name)
                    # Now look to add references to params of named objects to params
                    # If objs is a dictionary we want to iterate over the items
                    # but otherwise we iterate over the iterable of named object tuples
                    objs = objs.items() if isinstance(objs, dict) else objs
                    for name, obj in objs:
                        if hasattr(obj, "get_params"):
                            obj_params = obj.get_params(deep=True)
                            for key, value in obj_params.items():
                                params[f"{name}__{key}"] = value
        return params

    def _get_composite_params(self) -> Dict[str, Any]:
        """Get parameters whose values are BaseObjects or iterable named BaseObejcts.

        Returns
        -------
        composite_params : dict
            Composite parameter names mapped to their values.
        """
        named_object_parameters = self.get_tag("named_object_parameters")
        if isinstance(named_object_parameters, str):
            named_object_parameters = [named_object_parameters]
        elif named_object_parameters is None:
            named_object_parameters = []

        composite_params = {
            k: v
            for k, v in self.get_params(deep=False).items()
            if hasattr(v, "get_params") or k in named_object_parameters
        }
        return composite_params

    def _set_params(self, **params: Any) -> BaseObject:
        """Logic used internally to set the class instance's parameters.

        The method works on simple BaseObjects and on nested objects
        (such as :class:`sklearn.pipeline.Pipeline`). The latter have
        parameters of the form ``<component>__<parameter>`` so that it's
        possible to update each component of a nested object.

        Parameters
        ----------
        **params : dict
            BaseObject parameters.

        Returns
        -------
        self : instance of BaseObject
            BaseObject instance.
        """
        if not params:
            # Simple optimization to gain speed (inspect is slow)
            return self
        valid_params = self.get_params(deep=True)

        nested_params: DefaultDict[str, Any] = collections.defaultdict(dict)
        for key, value in params.items():
            key, delim, sub_key = key.partition("__")
            if key not in valid_params:
                raise ValueError(
                    f"Invalid parameter {key} for BaseObject {self}. "
                    "Check the list of available parameters "
                    "with `BaseObject.get_params().keys()`."
                )

            if delim:
                nested_params[key][sub_key] = value
            else:
                setattr(self, key, value)
                valid_params[key] = value

        for key, sub_params in nested_params.items():
            valid_params[key].set_params(**sub_params)

        return self

    def _replace_object(self, attr: str, name: str, new_val: Any) -> None:
        """Replace a BaseObject in parameter with named BaseObject values.

        Parameters
        ----------
        attr : str
            Name of parameter (and attribute) that includes named objects.
        name : str
            Name of parameter to set.
        new_val : Any
            The new value to set for the BaseObject corresponding to `name`.
        """
        new_objects = list(getattr(self, attr))
        for i, (object_name, _) in enumerate(new_objects):
            if object_name == name:
                new_objects[i] = (name, new_val)
                break
            setattr(self, attr, new_objects)

    def _replace_object_param(
        self, attr: str, obj_name: str, obj_param_name: str, new_val: Any
    ) -> None:
        """Replace a BaseObject's parameter in parameter with named BaseObject values.

        Parameters
        ----------
        attr : str
            Name of parameter (and attribute) that includes named objects.
        obj_name : str
            Name of object in the named object parameter that will have its
            parameter updated.
        obj_param_name : str
            The name of the parameter to have its value set for `obj_name`.
        new_val : Any
            The new value to set for the object parameter corresponding
            to `obj_param_name`.
        """
        new_objects = list(getattr(self, attr))
        for i, (object_name, obj) in enumerate(new_objects):
            if object_name == obj_name:
                new_objects[i] = (obj_name, obj.set_params(**{obj_param_name: new_val}))
                break
            setattr(self, attr, new_objects)

    def set_params(self, **params: Any) -> BaseObject:
        """Set the class instance's parameters.

        The method works on simple BaseObjects as well as on nested objects
        (e.g. items following a design patter like
        :class:`sklearn.pipeline.Pipeline`). These nested objects have
        parameters of the form ``<component>__<parameter>`` so that it's
        possible to update each component of a nested object.

        Parameters
        ----------
        **params : dict
            BaseObject parameters.

        Returns
        -------
        self : instance of BaseObject
            BaseObject instance.
        """
        # Step 1: Get any parameters that have named objects
        attrs = self.get_tag("named_object_parameters")
        if isinstance(attrs, str):
            attrs = [attrs]
        elif attrs is None:
            attrs = []

        # Step 2: If any parameters contain named objects and that attribute
        # is being set in params, replace the object
        # Initial loop to make sure the values being set adhere to the expected format
        for attr in attrs:
            if attr in params:
                self._check_iterable_named_objects(params[attr], iterable_name=attr)
        # Now loop to do the actual replacement
        for attr in attrs:
            if attr in params:
                setattr(self, attr, params.pop(attr))
            # Start of replacement
            items = getattr(self, attr)
            names: List[str] = []
            if items:
                names, _ = zip(*items)
            for name in list(params.keys()):
                # Replace a whole named object
                if "__" not in name and name in names:
                    self._replace_object(attr, name, params.pop(name))
                # Replacing parameter value in named object
                elif "__" in name:
                    obj_name, delim, obj_param_name = name.partition("__")
                    if obj_name in names:
                        self._replace_object_param(
                            attr, obj_name, obj_param_name, params.pop(name)
                        )

        # Step 3: set other params
        self._set_params(**params)

        return self

    def is_composite(self):
        """Check if the instance is a composite of BaseObjects.

        Composite objects have parameters with values set to instances other BaseObjects
        or parameter(s) that contain iterables of named BaseObject instances.

        Returns
        -------
        composite: bool
            Whether the instance contains any parameters that are instances of
            BaseObject  or parameters that are iterables of named BaseObject instances.
        """
        composite_params = self._get_composite_params()
        composite = True if composite_params else False

        return composite

    @classmethod
    def _check_has_class_tags(
        cls,
        allow_empty: bool = True,
        raise_error: bool = True,
    ) -> Any:
        """Verify whether the `_tags` class attribute exists.

        Parameters
        ----------
        allow_empty : bool, default=True
            Whether to consider an empty `_tags` attribute as having tags.
        raise_error : bool, default=True
            Whether to raise an error if `_tags` is not present.
            If False, no errors are raised and a boolean indicating the presence of
            the tag attribute being checked is returned.

        Returns
        -------
        has_tags : bool
            Whether the class has the "_tags" class attribute.

        Raises
        ------
        NoTagsError :
            If ``raise_error=True``  "_tags" class attribute does not exist.
        """
        has_tags = hasattr(cls, "_tags")
        if has_tags and len(cls._tags) == 0 and not allow_empty:
            has_tags = False

        if raise_error:
            if not has_tags:
                raise NoTagsError(
                    f"{cls.__class__.__name__} is unable to inspect tags, no "
                    "`_tags` attribute found."
                )
        else:
            return has_tags

    def _check_has_tags(
        self,
        dynamic: bool = False,
        allow_empty: bool = True,
        raise_error: bool = True,
    ) -> Any:
        """Verify whether the `_tags` or `_tags_dynamic` attribute exists.

        Parameters
        ----------
        dynamic : bool, default=False
            Whether to check for existance of class tags or dynamic tags attribute.
        allow_empty : bool, default=True
            Whether to consider an empty `_tags` attribute as having tags.
        raise_error : bool, default=True
            Whether to raise an error if `_tags` or `_tags_dynamic` is not present.
            If False, no errors are reaised and a boolean indicating the presence of
            the tag attribute being checked is returned.

        Returns
        -------
        has_tags : bool
            Whether the object as the "_tags" attribute (``dynamic=False``) or
            "_tags_dynamic" attribute (``dynamic=True``).

        Raises
        ------
        NoTagsError :
            If ``raise_error=True`` and the selected tag attribute does not exist
            ("_tags_dynamic" if ``dynamic=True`` otherwise "_tags" attribute).
        """
        tag_to_check = "_tags_dynamic" if dynamic else "_tags"
        has_tags = hasattr(self, tag_to_check)
        if has_tags and len(getattr(self, tag_to_check)) == 0 and not allow_empty:
            has_tags = False

        if raise_error:
            if not has_tags:
                raise NoTagsError(
                    f"{self.__class__.__name__} is unable to inspect tags, no "
                    f"`{tag_to_check}` attribute found."
                )
        else:
            return has_tags

    @classmethod
    def get_class_tags(cls) -> Dict[str, Any]:
        """Get class tags from class and all its parent classes.

        Returns
        -------
        collected_tags : dict
            Dictionary of tag name : tag value pairs. Collected from _tags
            class attribute via nested inheritance. This returns tags that
            are not overridden by dynamic tags set by set_tags.

        Raises
        ------
        ValueError
            If ``raise_error=True`` and `tag_name` does not exist in tags.
        """
        cls._check_has_class_tags()
        collected_tags = {}

        # We exclude the last parent classes: the basic Python object.
        for parent_class in reversed(inspect.getmro(cls)[:-1]):
            if hasattr(parent_class, "_tags"):
                more_tags = parent_class._tags.copy()  # type: ignore
                collected_tags.update(more_tags)

        return copy.deepcopy(collected_tags)

    @classmethod
    def get_class_tag(
        cls,
        tag_name: str,
        default_value: Optional[Any] = None,
        raise_error: bool = False,
    ) -> Any:
        """Get tag value from class (only class tags).

        Does not return any dynamic tags.

        Parameters
        ----------
        tag_name : str
            Name of tag value.
        default_value : any type
            Default value to return if `tag_name` is not found in class tags.
        raise_error : bool, default=False
            Whether to raise an error if `tag_name` not in class tags.

        Returns
        -------
        tag_value :
            Value of the `tag_name` tag in self. If not found, returns
            `tag_value_default`.
        """
        collected_tags = cls.get_class_tags()
        if raise_error and tag_name not in collected_tags:
            raise ValueError(f"`{tag_name}` not in class tags.")
        tag_value = collected_tags.get(tag_name, default_value)
        return tag_value

    def get_tags(self) -> Dict[str, Any]:
        """Get tags from class and any dynamic tag overrides.

        Returns
        -------
        collected_tags : dict
            Dictionary of tag name : tag value pairs. Collected from _tags
            class attribute via nested inheritance and then any overrides
            and new tags from _tags_dynamic object attribute.
        """
        collected_tags = self.get_class_tags()
        if self._check_has_tags(dynamic=True, allow_empty=True, raise_error=False):
            collected_tags.update(self._tags_dynamic)
        return copy.deepcopy(collected_tags)

    def get_tag(
        self,
        tag_name: str,
        default_value: Optional[Any] = None,
        raise_error: bool = True,
    ) -> Any:
        """Get tag value from the class and dynamic tag overrides.

        Parameters
        ----------
        tag_name : str
            Name of tag to be retrieved
        default_value : any type, optional; default=None
            Default value to return if `tag_name` is not found in tags.
        raise_error : bool
            whether a ValueError is raised when `tag_name` is not found in tags.

        Returns
        -------
        tag_value :
            Value of the `tag_name` tag in self. If not found, returns `default_value`.

        Raises
        ------
        ValueError
            If ``raise_error=True`` and `tag_name` does not exist in tags.
        """
        collected_tags = self.get_tags()
        if raise_error and tag_name not in collected_tags:
            raise ValueError(f"Tag with name `{tag_name}` could not be found.")
        tag_value = collected_tags.get(tag_name, default_value)
        return tag_value

    def set_tags(self, **tag_dict) -> BaseObject:
        """Set dynamic tags to given values.

        Parameters
        ----------
        tag_dict : dict
            Dictionary of tag name : tag value pairs.

        Returns
        -------
        Self :
            Reference to self.

        Raises
        ------
        NoTagsError
            If ``raise_error=True`` and "_tags_dynamic" attribute does not exist.

        Notes
        -----
        Changes object state by settting tag values in tag_dict as dynamic tags
        in the "_tags_dynamic attribute of the instance.
        """
        self._check_has_tags(dynamic=True, allow_empty=True, raise_error=True)
        self._tags_dynamic.update(copy.deepcopy(tag_dict))
        return self

    def clone_tags(
        self,
        obj: BaseObject,
        tag_names: Optional[Union[str, List[str]]] = None,
    ) -> BaseObject:
        """clone/mirror tags from another class as dynamic override.

        Parameters
        ----------
        obj : class inheriting from :class:`BaseObject`
            The object with tags to be cloned and set on the current object.
        tag_names : str or list of str, default = None
            Names of tags to clone. If None, then all tags in the BaseObject
            whose tags are being cloned are used as `tag_names`.

        Returns
        -------
        Self :
            Reference to self.

        Raises
        ------
        NoTagsError
            If ``raise_error=True`` and "_tags_dynamic" attribute does not exist.

        Notes
        -----
        Changes object state by setting dynamic tag values to the values
        in the passed class.
        """
        tags_est = copy.deepcopy(obj.get_tags())

        # if tag_set is not passed, default is all tags in class
        if tag_names is None:
            tag_names = [*tags_est.keys()]
        # if tag_set is passed, intersect keys with tags in class
        if isinstance(tag_names, str):
            tag_names = [tag_names]

        update_dict = {
            key: tags_est[key] for key in tag_names if key in tags_est.keys()
        }

        self.set_tags(**update_dict)

        return self

    def __repr__(self, n_char_max: int = 700):
        """Represent class as string.

        Parameters
        ----------
        n_char_max : int
            Maximum (approximate) number of non-blank characters to render. This
            can be useful in testing.
        """
        from base_object.utils._pprint import _BaseObjectPrettyPrinter

        n_max_elements_to_show = 30  # number of elements to show in sequences

        # use ellipsis for sequences with a lot of elements
        pp = _BaseObjectPrettyPrinter(
            compact=True,
            indent=1,
            indent_at_name=True,
            n_max_elements_to_show=n_max_elements_to_show,
        )

        repr_ = pp.pformat(self)

        # Use bruteforce ellipsis when there are a lot of non-blank characters
        n_nonblank = len("".join(repr_.split()))
        if n_nonblank > n_char_max:
            lim = n_char_max // 2  # apprx number of chars to keep on both ends
            regex = r"^(\s*\S){%d}" % lim
            # The regex '^(\s*\S){%d}' matches from the start of the string
            # until the nth non-blank character:
            # - ^ matches the start of string
            # - (pattern){n} matches n repetitions of pattern
            # - \s*\S matches a non-blank char following zero or more blanks
            left_match = re.match(regex, repr_)
            right_match = re.match(regex, repr_[::-1])
            left_lim = left_match.end() if left_match is not None else 0
            right_lim = right_match.end() if right_match is not None else 0

            if "\n" in repr_[left_lim:-right_lim]:
                # The left side and right side aren't on the same line.
                # To avoid weird cuts, e.g.:
                # categoric...ore',
                # we need to start the right side with an appropriate newline
                # character so that it renders properly as:
                # categoric...
                # handle_unknown='ignore',
                # so we add [^\n]*\n which matches until the next \n
                regex += r"[^\n]*\n"
                right_match = re.match(regex, repr_[::-1])
                right_lim = right_match.end() if right_match is not None else 0

            ellipsis = "..."
            if left_lim + len(ellipsis) < len(repr_) - right_lim:
                # Only add ellipsis if it results in a shorter repr
                repr_ = repr_[:left_lim] + "..." + repr_[-right_lim:]

        return repr_

    def __getstate__(self):
        """Get state of class for use in pickling."""
        try:
            state = super().__getstate__()
        except AttributeError:
            state = self.__dict__.copy()

        # Included for now for compatability with scikit-learn
        if type(self).__module__.startswith("sklearn."):
            return dict(state.items(), _sklearn_version=__version__)
        else:
            return state

    def __setstate__(self, state):
        """Set the state of the class."""
        # Included for now for compatability with scikit-learn
        if type(self).__module__.startswith("sklearn."):
            pickle_version = state.pop("_sklearn_version", "pre-0.18")
            if pickle_version != __version__:
                warnings.warn(
                    "Trying to unpickle scikit-learn estimator {0} from version {1} "
                    "when using version {2}. This might lead to breaking code or "
                    "invalid results. Use at your own risk. "
                    "For more info please refer to:\n"
                    "https://scikit-learn.org/stable/modules/model_persistence"
                    ".html#security-maintainability-limitations".format(
                        self.__class__.__name__, pickle_version, __version__
                    ),
                    UserWarning,
                )
        try:
            super().__setstate__(state)
        except AttributeError:
            self.__dict__.update(state)

    @property
    def _repr_html_(self):
        """HTML representation of BaseObject.

        This is redundant with the logic of `_repr_mimebundle_`. The latter
        should be favorted in the long term, `_repr_html_` is only
        implemented for consumers who do not interpret `_repr_mimbundle_`.
        """
        if get_config()["display"] != "diagram":
            raise AttributeError(
                "_repr_html_ is only defined when the "
                "`display` configuration option is set to 'diagram'."
            )
        return self._repr_html_inner

    def _repr_html_inner(self):
        """Return HTML representation of class.

        This function is returned by the @property `_repr_html_` to make
        `hasattr(BaseObject, "_repr_html_") return `True` or `False` depending
        on `get_config()["display"]`.
        """
        return _object_html_repr(self)

    def _repr_mimebundle_(self, **kwargs):
        """Mime bundle used by jupyter kernels to display instances of BaseObject."""
        output = {"text/plain": repr(self)}
        if get_config()["display"] == "diagram":
            output["text/html"] = _object_html_repr(self)
        return output
