"""convert between siliXon project using pcb.json and _netlist.txt to give kicad_converted.net"""


import json
import re
from pathlib import Path
import random
import datetime


def preamble():
    today = datetime.date.today().isoformat()
    return f"""(export (version D)
  (design
    (tool "Eeschema (5.0.2)-1")
    (sheet (number 1) (name /) (tstamps /)
      (title_block
        (title "Exported from siliXon project")
        (company)
        (rev v1)
        (date {today})
        (comment (number 1) (value ""))
        )))"""



    """EXAMPLE:
    (components
    (comp (ref U1)
      (value ATmega328P-PU)
      (footprint Package_DIP:DIP-28_W7.62mm)
      (datasheet http://ww1.microchip.com/downloads/en/DeviceDoc/ATmega328_P%20AVR%20MCU%20with%20picoPower%20Technology%20Data%20Sheet%2040001984A.pdf)
      (libsource (lib atmega48pv-10pu) (part ATmega328P-PU) (description "20MHz, 32kB Flash, 2kB SRAM, 1kB EEPROM, DIP-28"))
      (sheetpath (names /) (tstamps /))
      (tstamp 5C6402EE))
    (comp (ref U2)
      (value NRF24L01)
      (footprint LoPower2:nRF24L01)
      (datasheet http://www.nordicsemi.com/eng/content/download/2730/34105/file/nRF24L01_Product_Specification_v2_0.pdf)
      (libsource (lib RF) (part NRF24L01_Breakout) (description "Ultra low power 2.4GHz RF Transceiver, Carrier PCB"))
      (sheetpath (names /) (tstamps /))
      (tstamp 5C64041E))"""
    

def parse_components(json_path: str) -> str:
    """Return a KiCad (components ...) section generated from silixon_pcb.json."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    comps = data.get("components", [])
    footprint_map = {
        "resistor": "Resistor_SMD:R_0402_1005Metric",
        "capacitor": "Capacitor_SMD:C_0805_2012Metric",
        "switch": "Button_Switch_THT:SW_PUSH_6mm",
        "lcd": "Display:LCD-016N002L",
        "mcu": "Package_QFP:LQFP-64_10x10mm_P0.5mm",
    }

    lines = ["(components"]
    for c in comps:
        ref = c.get("uid", "U?")
        value = c.get("value", "")
        ctype = c.get("type", "").lower()
        footprint = footprint_map.get(ctype) or c.get("component_path", "").split("/")[-1]
        description = f"{ctype} {value}".strip()
        # Minimal lib + part placeholders
        lib = ctype or "lib"
        part = value or ref
        tstamp = ref  # simple deterministic placeholder

        lines.append(f"  (comp (ref {ref})")
        lines.append(f"    (value {value})")
        lines.append(f"    (footprint {footprint})")
        lines.append(f"    (datasheet ~)")
        lines.append(f"    (libsource (lib {lib}) (part {part}) (description \"{description}\"))")
        lines.append(f"    (sheetpath (names /) (tstamps /))")
        lines.append(f"    (tstamp 000000-{random.randint(0, 0xFFFFF):06x}-{tstamp}))")

    lines.append(")")
    return "\n".join(lines)

"""def parse_connections(netlist_file: str): """


""" EXAMPLE:
    (libparts
        (libpart (lib Connector) (part AVR-ISP-6)
        (description "Atmel 6-pin ISP connector")
        (docs " ~")
        (footprints
            (fp IDC?Header*2x03*)
            (fp Pin?Header*2x03*))
        (fields
            (field (name Reference) J)
            (field (name Value) AVR-ISP-6))
        (pins
            (pin (num 1) (name MISO) (type passive))
            (pin (num 2) (name VCC) (type power_in))
            (pin (num 3) (name SCK) (type passive))
            (pin (num 4) (name MOSI) (type passive))
            (pin (num 5) (name ~RST) (type passive))
            (pin (num 6) (name GND) (type power_in))))
        (libpart (lib Connector) (part Conn_01x03_Male)
        (description "Generic connector, single row, 01x03, script generated (kicad-library-utils/schlib/autogen/connector/)")
        (docs ~)
        (footprints
            (fp Connector*:*_1x??_*))
        (fields
            (field (name Reference) J)
            (field (name Value) Conn_01x03_Male))
        (pins
            (pin (num 1) (name Pin_1) (type passive))
            (pin (num 2) (name Pin_2) (type passive))
            (pin (num 3) (name Pin_3) (type passive))))
        (libpart (lib Connector) (part Conn_01x04_Male)
        (description "Generic connector, single row, 01x04, script generated (kicad-library-utils/schlib/autogen/connector/)")
        (docs ~)
        (footprints
            (fp Connector*:*_1x??_*))
        (fields
            (field (name Reference) J)
            (field (name Value) Conn_01x04_Male))
        (pins
            (pin (num 1) (name Pin_1) (type passive))
            (pin (num 2) (name Pin_2) (type passive))
            (pin (num 3) (name Pin_3) (type passive))
            (pin (num 4) (name Pin_4) (type passive))))"""

def parse_libparts(json_path: str, netlist_path: str = "silixon_netlist.txt") -> str:
    """Return a KiCad (libparts ...) section generated from silixon_pcb.json and silixon_netlist.txt."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    components = data.get("components", [])

    # Parse netlist to extract ordered pin names for parts starting with X (subcircuits)
    ref_pin_order = {}
    if Path(netlist_path).is_file():
        with open(netlist_path, "r", encoding="utf-8") as nf:
            raw_lines = [ln.rstrip() for ln in nf]

        # Merge continuation lines ending with "\" into single logical lines
        logical = []
        buf = ""
        for ln in raw_lines:
            line = ln.strip()
            if not line or line.startswith("*"):  # skip comments / empty
                if buf:
                    logical.append(buf.strip())
                    buf = ""
                continue
            if line.endswith("\\"):
                buf += " " + line[:-1].strip()
            else:
                buf += " " + line
                logical.append(buf.strip())
                buf = ""
        if buf:
            logical.append(buf.strip())

        for line in logical:
            # Subcircuit instances start with X<ref> ...
            if line.startswith("X") and len(line) > 2:
                tokens = line.split()
                inst = tokens[0]  # e.g. XU2
                ref = inst[1:]    # U2
                pin_names = []
                # Tokens after the instance until we hit something that looks like a .subckt name (endswith .subckt)
                for tok in tokens[1:]:
                    if tok.upper().endswith(".SUBCKT"):
                        break
                    if "=" in tok:
                        left, _right = tok.split("=", 1)
                        pin_names.append(left)
                if pin_names:
                    ref_pin_order[ref] = pin_names

    lib_map = {
        "resistor": "Resistor",
        "capacitor": "Capacitor",
        "switch": "Switch",
        "lcd": "Display",  # treat LCD like a connector-style symbol
        "mcu": "MCU"
    }

    footprint_patterns = {
        "resistor": "Resistor*",
        "capacitor": "Capacitor*",
        "switch": "SW*",
        "lcd": "Display*",
        "mcu": "QFP*"
    }

    power_names = {"VCC", "VDD", "VSS", "GND", "0"}

    def pin_type(name: str) -> str:
        upper = name.upper()
        if upper in power_names:
            return "power_in"
        return "passive"

    lines = ["(libparts"]
    for comp in components:
        ctype = comp.get("type", "").lower()
        ref = comp.get("uid", "U?")
        value = comp.get("value", "")
        pins_from_json = comp.get("pins", [])
        # Prefer order from netlist if available
        ordered_pin_names = ref_pin_order.get(ref, pins_from_json)

        # Fallback: if still empty, skip
        if not ordered_pin_names:
            continue

        lib = lib_map.get(ctype, "Generic")
        footprint_pat = footprint_patterns.get(ctype, f"{lib}*")
        description = f"{ctype} {value}".strip()

        lines.append(f"    (libpart (lib {lib}) (part {value or ref})")
        lines.append(f"    (description \"{description}\")")
        lines.append(f"    (docs ~)")
        lines.append(f"    (footprints")
        lines.append(f"        (fp {footprint_pat}))")
        lines.append(f"    (fields")
        lines.append(f"        (field (name Reference) {ref[0] if ref else 'U'})")
        lines.append(f"        (field (name Value) {value or ref}))")
        lines.append(f"    (pins")

        # Assign numeric pin numbers sequentially
        for idx, pname in enumerate(ordered_pin_names, start=1):
            # If the name is purely numeric, follow example style Pin_#
            display_name = f"Pin_{pname}" if pname.isdigit() else pname
            lines.append(f"        (pin (num {idx}) (name {display_name}) (type {pin_type(pname)}))")

        lines.append(f"    ))")  # close libpart

    lines.append(")")
    return "\n".join(lines)


"""EXAMPLE:
    (libraries
        (library (logical Connector)
        (uri "C:\\Program Files\\KiCad\\share\\kicad\\library/Connector.lib"))
        (library (logical Device)
        (uri "C:\\Program Files\\KiCad\\share\\kicad\\library/Device.lib"))
        (library (logical RF)
        (uri "C:\\Program Files\\KiCad\\share\\kicad\\library/RF.lib"))
        (library (logical Regulator_Linear)
        (uri "C:\\Program Files\\KiCad\\share\\kicad\\library/Regulator_Linear.lib"))
        (library (logical Sensor_Temperature)
        (uri "C:\\Program Files\\KiCad\\share\\kicad\\library/Sensor_Temperature.lib"))
        (library (logical Switch)
        (uri "C:\\Program Files\\KiCad\\share\\kicad\\library/Switch.lib"))
        (library (logical atmega48pv-10pu)
        (uri "C:/Users/Mark/Documents/KiCAD projects/symbols/atmega48pv-10pu.lib")))"""

def parse_libraries(json_path: str) -> str:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    components = data.get("components", [])

    # Must mirror lib_map in parse_libparts to stay consistent
    lib_map = {
        "resistor": "Resistor",
        "capacitor": "Capacitor",
        "switch": "Switch",
        "lcd": "Connector",
        "mcu": "MCU"
    }

    ordered_libs = []
    seen = set()
    for comp in components:
        ctype = comp.get("type", "").lower()
        lib = lib_map.get(ctype, "Generic")
        if lib not in seen:
            ordered_libs.append(lib)
            seen.add(lib)

    def uri_for(lib: str) -> str:
        # Placeholder URI pattern (adjust as needed)
        return f"./symbols/{lib}.lib"

    lines = ["(libraries"]
    for lib in ordered_libs:
        lines.append(f"  (library (logical {lib})")
        lines.append(f"    (uri \"{uri_for(lib)}\"))")
    lines.append(")")
    return "\n".join(lines)

"""EXAMPLE:
    (nets
        (net (code 1) (name SDA)
        (node (ref U1) (pin 27))
        (node (ref R10) (pin 1))
        (node (ref J4) (pin 1)))
        (net (code 2) (name SCL)
        (node (ref J4) (pin 2))
        (node (ref U1) (pin 28))
        (node (ref R9) (pin 2)))
        (net (code 3) (name LIGHTPOWER)
        (node (ref U1) (pin 6))
        (node (ref R7) (pin 2)))
        (net (code 4) (name LIGHTPIN)
        (node (ref R7) (pin 1))
        (node (ref R8) (pin 1))
        (node (ref U1) (pin 25)))
        (net (code 5) (name VCC1)
        (node (ref R9) (pin 1))
        (node (ref U1) (pin 7))
        (node (ref J3) (pin 3))
        (node (ref R10) (pin 2))
        (node (ref U3) (pin 3))
        (node (ref C4) (pin 1))
        (node (ref R2) (pin 2))
        (node (ref J2) (pin 2))
        (node (ref U2) (pin 2))
        (node (ref C3) (pin 1))
        (node (ref J4) (pin 4))
        (node (ref C1) (pin 1)))
        (net (code 6) (name Earth)
        (node (ref C2) (pin 2))
        (node (ref U1) (pin 22))
        (node (ref U3) (pin 1))
        (node (ref SW1) (pin 2))
        (node (ref J2) (pin 6))
        (node (ref U5) (pin 3))
        (node (ref C3) (pin 2))
        (node (ref J1) (pin 1))
        (node (ref C4) (pin 2))
        (node (ref C5) (pin 1))
        (node (ref D3) (pin 1))
        (node (ref J4) (pin 3))
        (node (ref J3) (pin 1))
        (node (ref D2) (pin 1))
        (node (ref R8) (pin 2))
        (node (ref C1) (pin 2))
        (node (ref U1) (pin 8))
        (node (ref D1) (pin 1))
        (node (ref U2) (pin 1))
        (node (ref J5) (pin 3))
        (node (ref R6) (pin 1)))
        (net (code 7) (name "BAT(+)")
        (node (ref J1) (pin 2))
        (node (ref U3) (pin 2))
        (node (ref R5) (pin 2))
        (node (ref C2) (pin 1)))
        (net (code 8) (name YELLED)
        (node (ref R3) (pin 2))
        (node (ref U1) (pin 13)))
        (net (code 9) (name "Net-(D1-Pad2)")
        (node (ref D1) (pin 2))
        (node (ref R1) (pin 1)))
        (net (code 10) (name SCK)
        (node (ref J2) (pin 3))
        (node (ref U2) (pin 5))
        (node (ref R1) (pin 2))
        (node (ref U1) (pin 19)))
        (net (code 11) (name VBAT)
        (node (ref R5) (pin 1))
        (node (ref R6) (pin 2))
        (node (ref U1) (pin 24)))
        (net (code 12) (name "Net-(D2-Pad2)")
        (node (ref D2) (pin 2))
        (node (ref R3) (pin 1)))
        (net (code 13) (name RESET)
        (node (ref R2) (pin 1))
        (node (ref SW1) (pin 1))
        (node (ref U1) (pin 1))
        (node (ref C6) (pin 2))
        (node (ref J2) (pin 5)))
        (net (code 14) (name "Net-(D3-Pad2)")
        (node (ref D3) (pin 2))
        (node (ref R4) (pin 1)))
        (net (code 15) (name REDLED)
        (node (ref U1) (pin 14))
        (node (ref R4) (pin 2)))
        (net (code 16) (name "Net-(C5-Pad2)")
        (node (ref C5) (pin 2))
        (node (ref U1) (pin 20)))
        (net (code 17) (name "Net-(U1-Pad5)")
        (node (ref U1) (pin 5)))
        (net (code 18) (name TEMPPOWER)
        (node (ref J5) (pin 1))
        (node (ref U5) (pin 1))
        (node (ref U1) (pin 11)))
        (net (code 19) (name EXT_TEMPPIN)
        (node (ref U1) (pin 26))
        (node (ref J5) (pin 2)))
        (net (code 20) (name IRQ)
        (node (ref U2) (pin 8))
        (node (ref U1) (pin 4)))
        (net (code 21) (name TEMPPIN)
        (node (ref U5) (pin 2))
        (node (ref U1) (pin 23)))
        (net (code 22) (name "Net-(U1-Pad21)")
        (node (ref U1) (pin 21)))
        (net (code 23) (name "Net-(U1-Pad10)")
        (node (ref U1) (pin 10)))
        (net (code 24) (name "Net-(U1-Pad9)")
        (node (ref U1) (pin 9)))
        (net (code 25) (name "Net-(U1-Pad12)")
        (node (ref U1) (pin 12)))
        (net (code 26) (name MISO)
        (node (ref J2) (pin 1))
        (node (ref U1) (pin 18))
        (node (ref U2) (pin 7)))
        (net (code 27) (name MOSI)
        (node (ref U1) (pin 17))
        (node (ref J2) (pin 4))
        (node (ref U2) (pin 6)))
        (net (code 28) (name ~CSN)
        (node (ref U2) (pin 4))
        (node (ref U1) (pin 16)))
        (net (code 29) (name CE)
        (node (ref U1) (pin 15))
        (node (ref U2) (pin 3)))
        (net (code 30) (name "Net-(J3-Pad2)")
        (node (ref J3) (pin 2)))
        (net (code 31) (name "Net-(C6-Pad1)")
        (node (ref J3) (pin 6))
        (node (ref C6) (pin 1)))
        (net (code 32) (name TXD)
        (node (ref J3) (pin 5))
        (node (ref U1) (pin 3)))
        (net (code 33) (name RXD)
        (node (ref U1) (pin 2))
        (node (ref J3) (pin 4)))))
        """

def parse_nets(json_path: str, netlist_path: str = "silixon_netlist.txt") -> str:
    """
    Build a (nets ...) section by correlating:
      - Pins declared in silixon_pcb.json (defines pin ordering -> pin numbers)
      - Electrical connectivity described in silixon_netlist.txt
    Rules:
      * For primitive parts (R1, C1, etc.): first N tokens after ref (where N = pin count) are nets.
      * For subcircuit instances (XRef ... PIN=NET ... name.subckt): use explicit PIN=NET pairs.
      * If the netlist references a pin name not present in JSON, append that pin name at the end
        (assigning the next sequential pin number) so it still appears in nets output.
      * Ground aliases "0" become GND.
      * Quote net names that contain characters outside [A-Za-z0-9_~] or contain parentheses.
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    comps = data.get("components", [])

    # Pin ordering (list) and mapping name->num for each component reference
    comp_pin_order: dict[str, list[str]] = {}
    comp_pin_name_to_num: dict[str, dict[str, str]] = {}

    for c in comps:
        ref = c.get("uid")
        pins = c.get("pins", [])
        comp_pin_order[ref] = list(pins)
        comp_pin_name_to_num[ref] = {pname: str(i) for i, pname in enumerate(pins, start=1)}

    # net_name -> list[(ref, pin_num)]
    net_nodes: dict[str, list[tuple[str, str]]] = {}
    net_order: list[str] = []

    def normalize_net(raw: str) -> str:
        raw = raw.strip()
        if raw == "0":
            return "GND"
        return raw

    def quote_net(name: str) -> str:
        # Add quotes if contains non-simple chars or parentheses
        if not name:
            return name
        if any(ch.isspace() for ch in name) or any(ch in name for ch in '()"\''):
            return f"\"{name}\""
        # KiCad examples also quote Net-(X-PadY) forms; detect parentheses
        if "(" in name or ")" in name or "-" in name and name.startswith("Net-"):
            return f"\"{name}\""
        return name

    def add_node(net: str, ref: str, pin_num: str):
        if net not in net_nodes:
            net_nodes[net] = []
            net_order.append(net)
        if (ref, pin_num) not in net_nodes[net]:
            net_nodes[net].append((ref, pin_num))

    def ensure_pin(ref: str, pin_name: str) -> str | None:
        """
        Ensure pin_name exists for ref; if missing, append to ordering and assign new number.
        Return pin number (as string) or None if ref unknown.
        """
        if ref not in comp_pin_order:
            return None
        mapping = comp_pin_name_to_num[ref]
        if pin_name in mapping:
            return mapping[pin_name]
        # Append dynamically
        comp_pin_order[ref].append(pin_name)
        new_num = str(len(comp_pin_order[ref]))
        mapping[pin_name] = new_num
        return new_num

    # Parse netlist text
    netlist_file = Path(netlist_path)
    if netlist_file.is_file():
        raw = netlist_file.read_text(encoding="utf-8").splitlines()

        # Merge backslash continuations
        logical: list[str] = []
        buf = ""
        for ln in raw:
            line = ln.strip()
            if not line or line.startswith("*") or line.upper().startswith(".END"):
                if buf:
                    logical.append(buf.strip())
                    buf = ""
                continue
            if line.endswith("\\"):
                buf += (" " if buf else "") + line[:-1].strip()
            else:
                buf += (" " if buf else "") + line
                logical.append(buf.strip())
                buf = ""
        if buf:
            logical.append(buf.strip())

        for line in logical:
            if not line:
                continue

            # Subcircuit style: XU1 ...
            if line.startswith("X") and len(line) > 2:
                toks = line.split()
                inst = toks[0]          # XU1
                ref = inst[1:]          # U1
                for tok in toks[1:]:
                    # Stop at subckt name token
                    if tok.lower().endswith(".subckt"):
                        break
                    if "=" not in tok:
                        continue
                    pin_name, net_name = tok.split("=", 1)
                    net_name = normalize_net(net_name)
                    pin_num = ensure_pin(ref, pin_name)
                    if pin_num:
                        add_node(net_name, ref, pin_num)
                continue

            # Primitive component: REF NET1 NET2 [NET3 ...] VALUE...
            toks = line.split()
            if not toks:
                continue
            ref = toks[0]
            if ref in comp_pin_order:
                pin_needed = len(comp_pin_order[ref])
                # If no declared pins (unlikely), skip
                if pin_needed == 0:
                    continue
                # Extract nets for however many pins we have declared (or available tokens)
                nets_slice = toks[1:1 + pin_needed]
                for idx, net_name in enumerate(nets_slice, start=1):
                    net_name = normalize_net(net_name)
                    add_node(net_name, ref, str(idx))

    # Build output
    lines = ["(nets"]
    for code, net_name in enumerate(net_order, start=1):
        nodes = net_nodes[net_name]
        lines.append(f"  (net (code {code}) (name {quote_net(net_name)})")
        for ref, pin in nodes:
            lines.append(f"    (node (ref {ref}) (pin {pin}))")
        lines.append("  )")
    lines.append(")")
    return "\n".join(lines)

def build_netlist(json_path: str, netlist_path: str = "silixon_netlist.txt") -> str:
    return "\n".join([
        preamble(),
        parse_components(json_path),
        parse_libparts(json_path, netlist_path),
        parse_libraries(json_path),
        parse_nets(json_path, netlist_path),
    ]) + ")\n"

if __name__ == "__main__":
    json_path = "silixon_pcb.json"
    netlist_path = "silixon_netlist.txt"
    netlist_text = build_netlist(json_path, netlist_path)
    out_path = Path("silixon_proj_to_kicad.net")
    out_path.write_text(netlist_text, encoding="utf-8")
    print(f"Wrote {out_path}")

