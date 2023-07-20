from typing import Optional, Union, Type, Any, get_origin, get_args
import inspect


def extract_id_class(annotation) -> Type[Any]:
    if inspect.isclass(annotation):
        return annotation

    elif get_origin(annotation) is Union:
        args = get_args(annotation)
        for arg in args:
            if inspect.isclass(arg) and arg is not type(None):
                return arg
        raise ValueError("Unknown annotation: {}".format(annotation))

    elif get_origin(annotation) is Optional:
        arg = get_args(annotation)[0]
        if inspect.isclass(arg):
            return arg
        else:
            raise ValueError("Unknown annotation: {}".format(annotation))
    else:
        raise ValueError("Unknown annotation: {}".format(annotation))
