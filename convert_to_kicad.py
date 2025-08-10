#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
spice2kicad_netlist.py
Convert a simple SPICE-like connection description (as in the user sample)
into a KiCad 5 "export (version D)" netlist suitable for Read Netlist/PCB flow.

Assumptions:
- Supports C*, R*, RLED discrete lines:   <REF> <NET1> <NET2> <VALUE>
- Supports XU2 (HD44780) and XU1 (LPC2148) blocks with line continuations "\".
- Treats "0", "GND", "gnd", "VGND" as the GND net.
- Leaves VCC (5V) and VDD (3.3V) as distinct nets (as in your text).
- Produces minimal libparts for Device:C, Device:R, LCD_HD44780, and LPC2148.
- Generates deterministic tstamp placeholders.

Adjust the pin maps or footprints below if needed.
"""

import argparse
import datetime
import re
from collections import defaultdict, OrderedDict

# ---------------------------- Configuration ---------------------------- #

# LCD (HD44780) pin name -> pin number
LCD_PINS = OrderedDict([
    ("VSS", "1"), ("VDD", "2"), ("VO", "3"),
    ("RS", "4"),  ("RW",  "5"), ("E",  "6"),
    ("DB0","7"),  ("DB1", "8"), ("DB2","9"), ("DB3","10"),
    ("DB4","11"), ("DB5","12"), ("DB6","13"), ("DB7","14"),
    ("A","15"),   ("K","16"),
])

# LPC2148: only the pins we use (plus VDD/VSS placeholders)
MCU_PINS = {
    "P0.21": "1",
    "P0.22": "2",
    "P0.14": "41",
    "P0.15": "45",
    "P0.16": "46",
    "P0.17": "47",
    "P0.18": "53",
    "P0.19": "54",
    "P0.20": "55",
    "P0.23": "58",
    "VDD": "100",
    "VSS": "101",
}

# Default footprints (change to your libs if desired)
FOOT_C = "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P2.50mm"
FOOT_R = "Resistor_THT:R_Axial_DIN0204_L3.6mm_D1.6mm_P2.54mm_Vertical"
FOOT_LCD = "Display:LCD-Character_16x2"
FOOT_MCU = "Package_QFP:LQFP-64_10x10mm_P0.5mm"

# Library URIs (adjust to your install paths)
LIB_URIS = {
    "Device": r"C:\Program Files\KiCad\share\kicad\library/Device.lib",
    "LCD_HD44780": r"C:\Libraries\LCD_HD44780.lib",
    "MCU_NXP_ARM": r"C:\Program Files\KiCad\share\kicad\library/MCU_NXP_ARM.lib",
}

# ---------------------------- Helpers ---------------------------- #

def sanitize_net(n: str) -> str:
    """Normalize ground and trim."""
    if n is None:
        return "~"
    n = n.strip()
    if n in ("0", "GND", "gnd", "VGND"):
        return "GND"
    return n

def strip_inline_comment(s: str) -> str:
    """Remove inline '; ...' comments."""
    return s.split(";", 1)[0]

def read_records(lines):
    """
    Collapse multi-line blocks using trailing '\' and drop '*' comment lines.
    Returns a list of logical records (strings).
    """
    recs, buf = [], ""
    for raw in lines:
        line = strip_inline_comment(raw.rstrip("\n"))
        if not line.strip():
            continue
        if line.lstrip().startswith("*"):
            continue
        # handle continuation by trailing backslash
        if line.rstrip().endswith("\\"):
            line = line.rstrip()
            line = line[:-1].rstrip()  # drop trailing '\'
            buf += (line + " ")
            continue
        else:
            buf += line
            if buf.strip():
                recs.append(" ".join(buf.split()))  # compress whitespace
            buf = ""
    if buf.strip():
        recs.append(" ".join(buf.split()))
    return recs

def tstamp_gen(start_hex=0x5F000001):
    """Simple incremental hex tstamp generator (string)."""
    n = start_hex
    while True:
        yield f"{n:08X}"
        n += 1

# ---------------------------- Core parse ---------------------------- #

class NetlistBuilder:
    def __init__(self):
        # components: ref -> dict(meta)
        self.components = OrderedDict()
        # nets: name -> list of (ref, pin)
        self.nets = defaultdict(list)
        # tstamp generator
        self._ts = tstamp_gen()

    def add_r(self, ref, n1, n2, value):
        self.components.setdefault(ref, {
            "value": value, "footprint": FOOT_R,
            "lib": "Device", "part": "R",
            "desc": "Resistor",
            "tstamp": next(self._ts)
        })
        self._add_conn(n1, ref, "1")
        self._add_conn(n2, ref, "2")

    def add_c(self, ref, n1, n2, value):
        self.components.setdefault(ref, {
            "value": value, "footprint": FOOT_C,
            "lib": "Device", "part": "C",
            "desc": "Unpolarized capacitor",
            "tstamp": next(self._ts)
        })
        self._add_conn(n1, ref, "1")
        self._add_conn(n2, ref, "2")

    def ensure_lcd(self):
        if "U2" not in self.components:
            self.components["U2"] = {
                "value": "LCD_HD44780",
                "footprint": FOOT_LCD,
                "lib": "LCD_HD44780", "part": "LCD_HD44780",
                "desc": "Alphanumeric LCD w/HD44780 controller",
                "tstamp": next(self._ts)
            }

    def ensure_mcu(self):
        if "U1" not in self.components:
            self.components["U1"] = {
                "value": "LPC2148",
                "footprint": FOOT_MCU,
                "lib": "MCU_NXP_ARM", "part": "LPC2148",
                "desc": "NXP LPC2148 ARM7 MCU",
                "tstamp": next(self._ts)
            }

    def add_lcd_map(self, mapping: dict):
        """mapping: pin-name -> net-name"""
        self.ensure_lcd()
        for pin_name, pin_num in LCD_PINS.items():
            if pin_name in mapping:
                net = sanitize_net(mapping[pin_name])
                self._add_conn(net, "U2", pin_num)

    def add_mcu_map(self, mapping: dict):
        """mapping: pin-name (e.g., P0.14) -> net-name"""
        self.ensure_mcu()
        for k, v in mapping.items():
            if k in MCU_PINS:
                net = sanitize_net(v)
                self._add_conn(net, "U1", MCU_PINS[k])

    def _add_conn(self, net, ref, pin):
        net = sanitize_net(net)
        self.nets[net].append((ref, pin))

# ---------------------------- SPICE-ish parsing ---------------------------- #

ASSIGN_RE = re.compile(r"^([A-Za-z0-9\.\_]+)=([^\s]+)$")

def parse_assignment_tokens(tokens):
    """Return dict of key=value from tokens like 'P0.14=NET_RS'."""
    out = {}
    for t in tokens:
        m = ASSIGN_RE.match(t)
        if m:
            out[m.group(1)] = m.group(2)
    return out

def handle_record(rec, nb: NetlistBuilder):
    tok = rec.split()
    if not tok:
        return
    head = tok[0].upper()

    if head.startswith(".END"):
        return  # ignore

    # Discrete capacitors: C1 NET1 NET2 VALUE
    if head.startswith("C") and head[1:].isdigit():
        ref = tok[0]
        n1, n2, val = tok[1], tok[2], tok[3]
        nb.add_c(ref, n1, n2, val)
        return

    # Resistors: R1 / R2 / RLED NET1 NET2 VALUE
    if head.startswith("R"):
        ref = tok[0]
        # sanity: must have at least R ? ? value
        if len(tok) >= 4:
            n1, n2, val = tok[1], tok[2], tok[3]
            nb.add_r(ref, n1, n2, val)
        return

    # XU2 ... LCD_HD44780.subckt
    if head == "XU2":
        # remove trailing subckt token if present
        tokens = [t for t in tok[1:] if not t.endswith(".subckt")]
        mapping = parse_assignment_tokens(tokens)
        nb.add_lcd_map(mapping)
        return

    # XU1 ... LPC2148.subckt
    if head == "XU1":
        tokens = [t for t in tok[1:] if not t.endswith(".subckt")]
        mapping = parse_assignment_tokens(tokens)
        nb.add_mcu_map(mapping)
        return

    # Voltage sources or others: ignore for connectivity
    # e.g., VCC VCC 0 DC 5V, etc.

# ---------------------------- Netlist writing ---------------------------- #

def kicad_netlist(nb: NetlistBuilder, title="8-bit LCD ↔ LPC2148 Interface",
                  sch_name="LCD_LPC2148.sch", tool="Eeschema (5.x)"):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    today = datetime.date.today().isoformat()

    # Component -> net connections already built.
    # Build a stable net order (GND first, then VCC, VDD, VO, then alpha)
    all_nets = list(nb.nets.keys())
    priority = {"GND": 0, "VCC": 1, "VDD": 2, "VO": 3}
    all_nets.sort(key=lambda n: (priority.get(n, 100), n))

    # Assign codes starting at 1
    net_code = {n: i+1 for i, n in enumerate(all_nets)}

    # Components block
    comp_lines = []
    for ref, c in nb.components.items():
        comp_lines.append(f"""    (comp (ref {ref})
      (value {c['value']})
      (footprint {c['footprint']})
      (datasheet ~)
      (libsource (lib {c['lib']}) (part {c['part']}) (description "{c['desc']}"))
      (sheetpath (names /) (tstamps /))
      (tstamp {c['tstamp']}))""")

    # libparts block (minimal set)
    libparts = f"""
    (libpart (lib Device) (part C)
      (description "Unpolarized capacitor")
      (docs ~)
      (footprints
        (fp C_*))
      (fields
        (field (name Reference) C)
        (field (name Value) C))
      (pins
        (pin (num 1) (name ~) (type passive))
        (pin (num 2) (name ~) (type passive))))
    (libpart (lib Device) (part R)
      (description "Resistor")
      (docs ~)
      (footprints
        (fp R_*))
      (fields
        (field (name Reference) R)
        (field (name Value) R))
      (pins
        (pin (num 1) (name ~) (type passive))
        (pin (num 2) (name ~) (type passive))))
    (libpart (lib LCD_HD44780) (part LCD_HD44780)
      (description "HD44780-based character LCD (16-pin)")
      (docs ~)
      (footprints
        (fp LCD*))
      (fields
        (field (name Reference) U)
        (field (name Value) LCD_HD44780))
      (pins
{chr(10).join([f"        (pin (num {num}) (name {name}) (type {'power_in' if name in ('VSS','VDD','A','K') else ('input' if name in ('RS','RW','E','VO') else 'bidirectional')}))" for name, num in LCD_PINS.items()])}
      ))
    (libpart (lib MCU_NXP_ARM) (part LPC2148)
      (description "NXP LPC2148 ARM7 microcontroller")
      (docs ~)
      (footprints
        (fp *LQFP*))
      (fields
        (field (name Reference) U)
        (field (name Value) LPC2148))
      (pins
{chr(10).join([f"        (pin (num {pnum}) (name {pname}) (type {'power_in' if pname in ('VDD','VSS') else 'bidirectional'}))" for pname, pnum in sorted(MCU_PINS.items(), key=lambda x: int(x[1]))])}
      ))"""

    # libraries block
    lib_lines = []
    for logical, uri in LIB_URIS.items():
        lib_lines.append(f"""    (library (logical {logical})
      (uri "{uri}"))""")

    # nets block
    net_lines = []
    for n in all_nets:
        nodes = nb.nets[n]
        # skip empty nets (should not happen)
        if not nodes:
            continue
        net_lines.append(f"""    (net (code {net_code[n]}) (name {n})
{chr(10).join([f"      (node (ref {ref}) (pin {pin}))" for ref, pin in nodes])}
    )""")

    # Put it all together
    out = f"""(export (version D)
  (design
    (source "{sch_name}")
    (date "{now}")
    (tool "{tool}")
    (sheet (number 1) (name /) (tstamps /)
      (title_block
        (title "{title}")
        (company)
        (rev v1)
        (date {today})
        (source {sch_name})
        (comment (number 1) (value "Converted from SPICE-like netlist"))
        (comment (number 2) (value "RW tied low; LCD backlight via RLED"))
        (comment (number 3) (value "VCC=5V, VDD=3.3V"))
        (comment (number 4) (value "")))))
  (components
{chr(10).join(comp_lines)})
  (libparts
{libparts}
  )
  (libraries
{chr(10).join(lib_lines)})
  (nets
{chr(10).join(net_lines)}
  )
)
"""
    return out

# ---------------------------- Main ---------------------------- #

def main():
    ap = argparse.ArgumentParser(description="Convert SPICE-like LCD↔LPC2148 description to KiCad 5 netlist.")
    ap.add_argument("-i", "--input", required=True, help="Input SPICE-like file")
    ap.add_argument("-o", "--output", required=True, help="Output KiCad netlist (.net)")
    ap.add_argument("--title", default="8-bit LCD ↔ LPC2148 Interface", help="Title block name")
    ap.add_argument("--sch", default="LCD_LPC2148.sch", help="Source schematic name shown in netlist")
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        lines = f.readlines()

    nb = NetlistBuilder()
    for rec in read_records(lines):
        handle_record(rec, nb)

    # Ensure required ties exist if user provided minimal lines:
    # (not strictly needed if source already includes them)
    # e.g., If RW or K mapped to 0, they are already connected via add_lcd_map.

    text = kicad_netlist(nb, title=args.title, sch_name=args.sch)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(text)

    print(f"Wrote KiCad netlist to: {args.output}")

if __name__ == "__main__":
    main()