# -*- coding: utf-8 -*-
""":mod:`base_object.registry` provides a registry of package functionality."""
from collections.abc import Iterable
from typing import Any, Dict, List, TypeVar

try:
    from typing import TypedDict
except ImportError:
    from typing_extensions import TypedDict  # type: ignore

from base_object.base import BaseObject
from base_object.exceptions import InvalidTagError

__all__: List[str] = []
__author__: List[str] = ["RNKuhns"]

T = TypeVar("T", bound="BaseObject")


class TagDetails(TypedDict):
    """Defines types of included in tag registry details."""

    allowed_types: Any
    allowed_values: Any
    can_be_dynamic: bool


ALLOWED_TAGS_BY_CLASS: Dict[T, Dict[str, TagDetails]] = {
    BaseObject: {
        "named_object_parameters": {
            "allowed_types": Any,
            "allowed_values": Any,
            "can_be_dynamic": False,
        },
    }
}


def check_tags_allowed(
    obj: T,
    allowed_tags: Dict[str, TagDetails],
    dynamic: bool = False,
    raise_error: bool = True,
) -> bool:
    """Verify if an object's tags are in the allowed tags.

    The check first verifies that tag names are allowed. Then for allowed tag names,
    it proceeds to check that the assigned tag value is an allowable type. If
    this is true, then it verifies the tag value is in the allowable values.

    Parameters
    ----------
    obj : BaseObject
        Class or instance inheritting from BaseObject.
    allowed_tags : Dict[str, TagDetails]
        Dictionary mapping from a string tag name to a dictionary of tag details
        that indicate the allowed tag types, allowed tag values and whether the
        tag can be a dynamic tag.
    dynamic : bool
        Whether to check the object's tags or dynamic tags.

        - If True, check the object's dynamic tags.
        - If False, check the object's static class tags.

    Returns
    -------
    are_tags_allowed : bool
        Whether the object's tags are in the registry of tags allowed for that object.
    """
    if not (
        isinstance(obj, BaseObject)
        or (hasattr(obj, "_tags") and hasattr(obj, "get_tags"))
    ):
        raise TypeError(
            "Input `obj` is not compatible with the BaseObject tag interface."
            f"Expected `obj` to be a BaseObject, but received {type(obj)}."
        )

    if dynamic:
        obj_tags = obj.get_tags()
        class_tags = obj.get_class_tags()
        allowed_dynamic_tags = {
            tag: details
            for tag, details in allowed_tags.items()
            if details["can_be_dynamic"]
        }
        # check that any tags that were dynamically updated are actually allowed
        # to be dynamic tags
        updated_tags = [tag for tag in obj_tags if obj_tags[tag] != class_tags[tag]]
        tags_that_should_not_update = [
            tag for tag in updated_tags if tag not in allowed_dynamic_tags
        ]
        if len(tags_that_should_not_update) > 0:
            _tags_str = "tag" if len(tags_that_should_not_update) == 1 else "tags"
            tag_error_msg = (
                f"Found {len(tags_that_should_not_update)} invalid {_tags_str} in "
                f"object {obj}.\n"
                f"The invalid tags are:\n {''.join(tags_that_should_not_update)}"
            )
        raise InvalidTagError(tag_error_msg)

    else:
        obj_tags = obj.get_class_tags()

    invalid_tags: Dict[str, str] = {}
    # Whether dynamic is True or False all tags that can't be dynamic need to be checked
    for obj_tag, obj_tag_value in obj_tags.items():
        # Step 1: check if tag is in allowed tags
        tag_allowed = obj_tag in allowed_tags
        # Default type and values being not allowed to simplify check logic
        tag_type_allowed: bool = False
        tag_value_allowed: bool = False
        # Step 2: If tag is allowed then check that tag value is an allowed type
        if tag_allowed:
            allowed_types = allowed_tags[obj_tag]["allowed_types"]
            if allowed_types == Any:
                tag_type_allowed = True
            else:
                # isinstance only accepts single type or tuple of types
                if isinstance(allowed_types, Iterable):
                    allowed_types = tuple(allowed_types)
                tag_type_allowed = isinstance(obj_tag_value, allowed_types)

            # Step 3: If tag value is allowed type see if it is one of allowed values
            if tag_type_allowed:
                allowed_values = allowed_tags[obj_tag]["allowed_values"]
                if allowed_values == Any:
                    tag_value_allowed = True
                else:
                    if isinstance(allowed_values, Iterable):
                        tag_value_allowed = obj_tag_value in allowed_values
                    else:
                        tag_value_allowed = obj_tag_value == allowed_values

                if not tag_value_allowed:
                    tag_msg = (
                        f"Expected value of tag {obj_tag} to be one of allowed "
                        f"values {allowed_values}, but found {obj_tag_value}."
                    )
            else:
                tag_msg = (
                    f"Expected value of tag {obj_tag} to be one of the allowed types "
                    f"{allowed_types}, but the value was {obj_tag_value} with type "
                    f"{type(obj_tag_value)}."
                )
        else:
            tag_msg = (
                f"Found tag {obj_tag}, but the only allowable tags are "
                f"{', '.join(allowed_tags.keys())}."
            )

        if not (tag_allowed and tag_type_allowed and tag_value_allowed):
            invalid_tags[obj_tag] = tag_msg

    # If there are any invalid tags raise an error if user requested
    if raise_error and invalid_tags:
        _tags_str = "tag" if len(invalid_tags) == 1 else "tags"
        invalid_tag_msgs = [
            tag + ": " + msg + "\n" for tag, msg in invalid_tags.items()
        ]
        tag_error_msg = (
            f"Found {len(invalid_tags)} invalid {_tags_str} in object {obj}.\n"
            f"The invalid tags are:\n {''.join(invalid_tag_msgs)}"
        )
        raise InvalidTagError(tag_error_msg)
    else:
        are_tags_allowed = len(invalid_tags) == 0
        return are_tags_allowed
