import json
from tools.tools import read_file, write_to_file

available_tools = {
    "read_file": read_file,
    "write_to_file": write_to_file,
}


def get_tools_json() -> list[dict]:
    json_array_string = read_file("tools/tools.json")
    return json.loads(json_array_string)


tools_list = get_tools_json()
