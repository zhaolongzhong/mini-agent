import json
from tools import read_file


def get_tools_json():
    json_array_string = read_file("tools.json")
    return json.loads(json_array_string)
