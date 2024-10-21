import inspect
from typing import Any, get_type_hints


def function_to_json(func) -> dict:
    """
    Converts a Python function into a JSON-serializable dictionary
    that describes the function's signature, including its name,
    description, and parameters.

    Args:
        func: The function to be converted.

    Returns:
        A dictionary representing the function's signature in the desired JSON format.
    """
    type_map = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
        Any: "any",
        type(None): "null",
    }

    try:
        signature = inspect.signature(func)
        # Pass the function's global namespace to resolve type hints correctly
        type_hints = get_type_hints(func, globalns=func.__globals__)
    except ValueError as e:
        raise ValueError(f"Failed to get signature for function '{func.__name__}': {str(e)}")

    parameters = {}
    required = []

    for param_name, param in signature.parameters.items():
        param_type = type_hints.get(param_name, Any)
        json_type = type_map.get(param_type, "string")
        param_info = {
            "type": json_type,
            "description": f"Parameter '{param_name}' for function '{func.__name__}'.",
        }

        if param.default != inspect.Parameter.empty:
            param_info["default"] = param.default
        else:
            required.append(param_name)

        parameters[param_name] = param_info

    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": func.__doc__.strip() if func.__doc__ else f"Function '{func.__name__}'.",
            "parameters": {"type": "object", "properties": parameters, "required": required},
        },
    }
