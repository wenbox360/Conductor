# Generates a design code file from the boilerplate code

import json

def import_pins(input_json):
    pin_list = []
    for sensorMap in input_json['mappings']:
        pin_str = "#define "
        pin_str += sensorMap['partId'].upper() +"_" + sensorMap['id'] + "_PIN "
        pin_str += str(sensorMap['pins'][0]) + " "
        pin_list.append(pin_str)