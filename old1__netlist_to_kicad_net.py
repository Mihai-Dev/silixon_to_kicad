import sys
import re
from collections import defaultdict

# Default footprints for common components
FOOTPRINTS = {
    'C': 'Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P2.50mm',
    'R': 'Resistor_THT:R_Axial_DIN0204_L3.6mm_D1.6mm_P2.54mm_Vertical',
    'LED': 'LED_THT:LED_D3.0mm',
    'U': 'Package_DIP:DIP-28_W7.62mm',  # Default for ICs, can be improved
    'XU': 'Package_DIP:DIP-28_W7.62mm',
    'RLED': 'Resistor_THT:R_Axial_DIN0204_L3.6mm_D1.6mm_P2.54mm_Vertical',
    'VCC': 'power:VCC',
    'VDD': 'power:VDD',
    'VGND': 'power:GND',
    'R_PHOTO': 'OptoDevice:R_LDR_4.9x4.2mm_P2.54mm_Vertical',
    'SW': 'LoPower2:SW_PUSH_L6mm_W3.5mm_H5mm',
    'J': 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical',
}

def get_footprint(ref, value):
    if ref.startswith('C'):
        return FOOTPRINTS['C']
    if ref.startswith('RLED'):
        return FOOTPRINTS['RLED']
    if ref.startswith('R'):
        return FOOTPRINTS['R']
    if ref.startswith('LED') or ref.startswith('D'):
        return FOOTPRINTS['LED']
    if ref.startswith('U') or ref.startswith('XU'):
        return FOOTPRINTS['U']
    if ref.startswith('SW'):
        return FOOTPRINTS['SW']
    if ref.startswith('J'):
        return FOOTPRINTS['J']
    if ref.startswith('VCC'):
        return FOOTPRINTS['VCC']
    if ref.startswith('VDD'):
        return FOOTPRINTS['VDD']
    if ref.startswith('VGND'):
        return FOOTPRINTS['VGND']
    return 'Unknown'

POWER_REFS = {'VCC', 'VDD', 'GND', 'VGND', '0'}

def is_power_ref(ref):
    ref_upper = ref.upper()
    return ref_upper in POWER_REFS or ref_upper.startswith('VCC') or ref_upper.startswith('VDD') or ref_upper.startswith('GND') or ref_upper == '0'

def parse_netlist(filename):
    components = {}
    net_to_nodes = defaultdict(list)  # net_name -> list of (ref, pin)
    pin_maps = {}  # ref -> {pin: net}
    with open(filename) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('*') or line.startswith('.END'):
                continue
            tokens = re.split(r'\s+', line)
            ref = tokens[0]
            if is_power_ref(ref):
                continue  # Skip power components
            # Multi-pin component (IC, subckt, etc): XU1 P0.14=NET_RS ...
            if any('=' in t for t in tokens[1:]):
                value = tokens[-1] if not '=' in tokens[-1] else ''
                pin_net_pairs = [t for t in tokens[1:] if '=' in t]
                pin_map = {}
                for pair in pin_net_pairs:
                    pin, net = pair.split('=')
                    pin_map[pin] = net
                    net_to_nodes[net].append((ref, pin))
                components[ref] = {
                    'ref': ref,
                    'value': value,
                    'pin_map': pin_map,
                }
                pin_maps[ref] = pin_map
            # Simple 2-pin component: R1 VCC 0 10k
            elif len(tokens) >= 4:
                conn1 = tokens[1]
                conn2 = tokens[2]
                value = ' '.join(tokens[3:])
                pin_map = {'1': conn1, '2': conn2}
                net_to_nodes[conn1].append((ref, '1'))
                net_to_nodes[conn2].append((ref, '2'))
                components[ref] = {
                    'ref': ref,
                    'value': value,
                    'pin_map': pin_map,
                }
                pin_maps[ref] = pin_map
    return components, net_to_nodes, pin_maps

HEADER = '''(export (version D)
  (design
    (source "~")
    (date "~")
    (tool "~")
    (sheet (number 1) (name /) (tstamps /)
      (title_block
        (title "~")
        (company)
        (rev ~)
        (date ~)
        (source ~)
        (comment (number 1) (value ""))
        (comment (number 2) (value ""))
        (comment (number 3) (value ""))
        (comment (number 4) (value ""))))
'''

def get_libsource(ref, value):
    # Use only standard KiCad libraries and part names
    if ref.startswith('C'):
        return '(libsource (lib Device) (part C) (description "Unpolarized capacitor"))'
    if ref.startswith('R') and not ref.startswith('RLED'):
        return '(libsource (lib Device) (part R) (description Resistor))'
    if ref.startswith('D'):
        return '(libsource (lib Device) (part LED) (description "Light emitting diode"))'
    if ref.startswith('U') or ref.startswith('XU'):
        return '(libsource (lib Device) (part U) (description "Integrated Circuit"))'
    if ref.startswith('SW'):
        return '(libsource (lib Switch) (part SW_Push) (description "Push button switch, generic, two pins"))'
    if ref.startswith('J'):
        # Try to guess connector type by value or ref
        if '03' in ref or '3' in value:
            return '(libsource (lib Connector) (part Conn_01x03_Male) (description "Generic connector, single row, 01x03"))'
        if '04' in ref or '4' in value:
            return '(libsource (lib Connector) (part Conn_01x04_Male) (description "Generic connector, single row, 01x04"))'
        if '06' in ref or '6' in value:
            return '(libsource (lib Connector) (part Conn_01x06_Male) (description "Generic connector, single row, 01x06"))'
        if 'AVR' in value:
            return '(libsource (lib Connector) (part AVR-ISP-6) (description "Atmel 6-pin ISP connector"))'
        if 'Screw' in value or 'Battery' in value:
            return '(libsource (lib Connector) (part Screw_Terminal_01x02) (description "Generic screw terminal, single row, 01x02"))'
        return '(libsource (lib Connector) (part Conn_01x02_Male) (description "Generic connector, single row, 01x02"))'
    if ref.startswith('RLED'):
        return '(libsource (lib Device) (part R) (description Resistor))'
    if ref.startswith('R_PHOTO'):
        return '(libsource (lib Device) (part R_PHOTO) (description Photoresistor))'
    return '(libsource (lib Device) (part R) (description Resistor))'  # fallback to Device:R

def get_libpart_info(ref, value, pin_maps):
    # Returns (lib, part, description, pins, footprints, fields)
    # Use only standard KiCad libraries and part names
    if ref.startswith('C'):
        return ('Device', 'C', 'Unpolarized capacitor', [('1', '~'), ('2', '~')], ['C_*'], [('Reference', 'C'), ('Value', 'C')])
    if ref.startswith('R') and not ref.startswith('RLED'):
        return ('Device', 'R', 'Resistor', [('1', '~'), ('2', '~')], ['R_*'], [('Reference', 'R'), ('Value', 'R')])
    if ref.startswith('D'):
        return ('Device', 'LED', 'Light emitting diode', [('1', 'K'), ('2', 'A')], ['LED*', 'LED_SMD:*', 'LED_THT:*'], [('Reference', 'D'), ('Value', 'LED')])
    if ref.startswith('U') or ref.startswith('XU'):
        # Use actual pin names from pin_maps if available
        pins = []
        if ref in pin_maps:
            for pin in pin_maps[ref]:
                pins.append((pin, pin))
        else:
            pins = [(str(i), f'Pin_{i}') for i in range(1, 9)]
        return ('Device', 'U', 'Integrated Circuit', pins, ['DIP*W7.62mm*'], [('Reference', 'U'), ('Value', 'U')])
    if ref.startswith('SW'):
        return ('Switch', 'SW_Push', 'Push button switch, generic, two pins', [('1', '1'), ('2', '2')], ['SW*'], [('Reference', 'SW'), ('Value', 'SW_Push')])
    if ref.startswith('J'):
        # Guess pin count from value or ref
        if '03' in ref or '3' in value:
            pins = [(str(i), f'Pin_{i}') for i in range(1, 4)]
            return ('Connector', 'Conn_01x03_Male', 'Generic connector, single row, 01x03', pins, ['Connector*:*_1x??_*'], [('Reference', 'J'), ('Value', 'Conn_01x03_Male')])
        if '04' in ref or '4' in value:
            pins = [(str(i), f'Pin_{i}') for i in range(1, 5)]
            return ('Connector', 'Conn_01x04_Male', 'Generic connector, single row, 01x04', pins, ['Connector*:*_1x??_*'], [('Reference', 'J'), ('Value', 'Conn_01x04_Male')])
        if '06' in ref or '6' in value:
            pins = [(str(i), f'Pin_{i}') for i in range(1, 7)]
            return ('Connector', 'Conn_01x06_Male', 'Generic connector, single row, 01x06', pins, ['Connector*:*_1x??_*'], [('Reference', 'J'), ('Value', 'Conn_01x06_Male')])
        if 'AVR' in value:
            pins = [(str(i), n) for i, n in enumerate(['MISO', 'VCC', 'SCK', 'MOSI', '~RST', 'GND'], 1)]
            return ('Connector', 'AVR-ISP-6', 'Atmel 6-pin ISP connector', pins, ['IDC?Header*2x03*', 'Pin?Header*2x03*'], [('Reference', 'J'), ('Value', 'AVR-ISP-6')])
        if 'Screw' in value or 'Battery' in value:
            pins = [('1', 'Pin_1'), ('2', 'Pin_2')]
            return ('Connector', 'Screw_Terminal_01x02', 'Generic screw terminal, single row, 01x02', pins, ['TerminalBlock*:*'], [('Reference', 'J'), ('Value', 'Screw_Terminal_01x02')])
        pins = [('1', 'Pin_1'), ('2', 'Pin_2')]
        return ('Connector', 'Conn_01x02_Male', 'Generic connector, single row, 01x02', pins, ['Connector*:*_1x??_*'], [('Reference', 'J'), ('Value', 'Conn_01x02_Male')])
    if ref.startswith('RLED'):
        return ('Device', 'R', 'Resistor', [('1', '~'), ('2', '~')], ['R_*'], [('Reference', 'R'), ('Value', 'R')])
    if ref.startswith('R_PHOTO'):
        return ('Device', 'R_PHOTO', 'Photoresistor', [('1', '~'), ('2', '~')], ['*LDR*', 'R?LDR*'], [('Reference', 'R'), ('Value', 'R_PHOTO')])
    return ('Device', 'R', 'Resistor', [('1', '~'), ('2', '~')], ['R_*'], [('Reference', 'R'), ('Value', 'R')])

def write_kicad_netlist(components, net_to_nodes, pin_maps, outfile):
    # Write header (matches example.net lines 2-16)
    outfile.write(HEADER)
    outfile.write('  (components\n')
    comp_list = list(components.values())
    for idx, comp in enumerate(comp_list):
        ref = comp['ref']
        value = comp['value']
        footprint = get_footprint(ref, value)
        libsource = get_libsource(ref, value)
        outfile.write(f'    (comp (ref {ref})\n')
        # Write value field, handling parenthetical comments
        value_str = f'      (value {value}'
        if value.strip().endswith(')'):
            outfile.write(f'{value_str})\n')
        else:
            outfile.write(f'{value_str})\n')
        outfile.write(f'      (footprint {footprint})\n')
        outfile.write(f'      (datasheet ~)\n')
        outfile.write(f'      {libsource}\n')
        outfile.write(f'      (sheetpath ~)\n')
        # For the last component, close with three brackets
        if idx == len(comp_list) - 1:
            outfile.write(f'      (tstamp ~)))\n')
        else:
            outfile.write(f'      (tstamp ~))\n')
    # Write libparts section
    # Collect unique (lib, part) pairs
    libparts = {}
    for comp in components.values():
        ref = comp['ref']
        value = comp['value']
        lib, part, desc, pins, footprints, fields = get_libpart_info(ref, value, pin_maps)
        key = (lib, part)
        # For multi-pin parts, prefer the one with the most pins
        if key not in libparts or len(pins) > len(libparts[key]['pins']):
            libparts[key] = {
                'lib': lib,
                'part': part,
                'desc': desc,
                'pins': pins,
                'footprints': footprints,
                'fields': fields,
            }
    outfile.write('  (libparts\n')
    for lp in libparts.values():
        outfile.write(f'    (libpart (lib {lp["lib"]}) (part {lp["part"]})\n')
        outfile.write(f'      (description "{lp["desc"]}")\n')
        outfile.write('      (footprints\n')
        for fp in lp['footprints']:
            outfile.write(f'        (fp {fp})\n')
        outfile.write('      )\n')
        outfile.write('      (fields\n')
        for fname, fval in lp['fields']:
            outfile.write(f'        (field (name {fname}) {fval})\n')
        outfile.write('      )\n')
        outfile.write('      (pins\n')
        for num, name in lp['pins']:
            outfile.write(f'        (pin (num {num}) (name {name}) (type passive))\n')
        outfile.write('      )\n')
        outfile.write('    )\n')
    outfile.write('  )\n')
    # Write nets
    outfile.write('  (nets\n')
    net_code = 1
    for net_name, nodes in net_to_nodes.items():
        outfile.write(f'    (net (code {net_code}) (name {net_name})\n')
        for ref, pin in nodes:
            outfile.write(f'      (node (ref {ref}) (pin {pin}))\n')
        outfile.write('    )\n')  # Only close the net, not nets
        net_code += 1
    outfile.write('  )\n')  # Close nets after all are written
    outfile.write(')\n')  # Only one closing parenthesis for export

def main():
    if len(sys.argv) != 3:
        print("Usage: python netlist_to_kicad_net.py input_netlist.txt output_kicad.net")
        sys.exit(1)
    in_file = sys.argv[1]
    out_file = sys.argv[2]
    components, net_to_nodes, pin_maps = parse_netlist(in_file)
    with open(out_file, 'w') as f:
        write_kicad_netlist(components, net_to_nodes, pin_maps, f)

if __name__ == '__main__':
    main() 