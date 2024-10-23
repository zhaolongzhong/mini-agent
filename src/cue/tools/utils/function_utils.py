from typing import Dict


def get_definition_by_model(func: Dict, model: str) -> Dict:
    """Convert func json based on model"""
    if "claude" not in model:
        return func

    # If the tool already has the Claude format, return as is
    if "input_schema" in func:
        return func

    # If the tool has a nested function structure, convert it
    function_data = func.get("function")
    if function_data:
        return {
            "name": function_data.get("name"),
            "description": function_data.get("description"),
            "input_schema": function_data.get("parameters"),
        }

    return func
