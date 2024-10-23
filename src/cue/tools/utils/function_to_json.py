import inspect
from typing import Any, Optional, get_type_hints


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
        # Remove Any from type_map
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
        # Handle **kwargs separately
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            # Define kwargs as an object with additionalProperties
            param_info = {
                "type": "object",
                "description": f"Parameter '{param_name}' for function '{func.__name__}'.",
                "additionalProperties": True,
            }
            parameters[param_name] = param_info
            continue

        param_type = type_hints.get(param_name, Any)

        # Determine if the parameter is Optional
        is_optional = False
        origin = getattr(param_type, "__origin__", None)
        if origin is Optional:
            is_optional = True
            # Extract the actual type from Optional
            args = getattr(param_type, "__args__", [])
            if args:
                param_type = args[0]

        # Map the parameter type
        json_type = type_map.get(param_type, "string")  # Default to "string" if type not found

        param_info = {
            "type": json_type,
            "description": f"Parameter '{param_name}' for function '{func.__name__}'.",
        }

        # Handle default values
        if param.default != inspect.Parameter.empty:
            param_info["default"] = param.default
        else:
            if not is_optional:
                required.append(param_name)

        # Handle complex types
        if param_type == Any:
            # Replace "Any" with "object" allowing additional properties
            param_info["type"] = "object"
            param_info["additionalProperties"] = True

        parameters[param_name] = param_info

    # Handle the 'required' list: Only include parameters that are not optional and have no default
    return {
        "type": "function",
        "function": {
            "name": func.__name__,
            "description": func.__doc__.strip() if func.__doc__ else f"Function '{func.__name__}'.",
            "parameters": {"type": "object", "properties": parameters, "required": required},
        },
    }
