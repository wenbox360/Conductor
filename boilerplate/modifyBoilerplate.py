# Generates a design code file from the boilerplate code

import json

def import_pins(input_json):
    pin_list = []
    for sensorMap in input_json['mappings']:
        pin_str = "#define "
        pin_str += sensorMap['partId'].upper() + "_PIN "
        pin_str += str(sensorMap['pins'][0]) + " "
        pin_list.append(pin_str)
    return pin_list

def import_includes(input_json, function_map):
    include_list = []
    for sensorMap in input_json['mappings']:
        include_list.append(function_map[sensorMap['partId']]["include"])
    return include_list

def import_sensor_functions(input_json, function_map):
    function_list = []
    for sensorMap in input_json['mappings']:
        for pin in function_map[sensorMap['partId']]["function"]:
            function_list.append(pin)
    return function_list

def make_unique(input_json, functions_json):
    with open(functions_json, "r") as f:
        functions = f.read()
    with open(input_json, "r") as f:
        input = f.read()
    function_map = json.loads(functions)
    pin_maps = json.loads(input)
    pin_list = import_pins(pin_maps)
    function_list = import_sensor_functions(pin_maps, function_map)
    include_list = import_includes(pin_maps, function_map)

    with open("boilerplate/unique.c", "w") as f:
        f.write("// Include Libraries\n")
        for include in include_list:
            f.write(include + "\n")
        f.write("// Pin Definitions\n")
        for pin in pin_list:
            f.write(pin + "\n")
        f.write("\n// Sensor Functions\n")
        for function in function_list:
            f.write(function + "\n\n")


if __name__ == "__main__":
    make_unique("boilerplate/pinMap.json", "boilerplate/boilerplate.json") # Example usage - probably need to modify pinMap.json