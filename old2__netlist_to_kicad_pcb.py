import json
import re

# File paths
NETLIST_FILE = 'silixon_netlist.txt'
BOM_FILE = 'silixon_bom.json'
PCB_JSON_FILE = 'silixon_pcb.json'
OUTPUT_FILE = 'output.kicad_pcb'

# Generic footprints and drawing parameters
GENERIC_FOOTPRINTS = {
    'resistor': {
        'name': 'Resistor_THT:R_Axial_DIN0204_L3.6mm_D1.6mm_P2.54mm_Vertical',
        'pad_distance': 2.54,
        'pad_size': 1.4,
        'drill': 0.7,
    },
    'capacitor': {
        'name': 'Capacitor_THT:C_Disc_D3.8mm_W2.6mm_P2.50mm',
        'pad_distance': 2.5,
        'pad_size': 1.2,
        'drill': 0.8,
    },
    'mcu': {
        'name': 'Package_DIP:DIP-16_W7.62mm',
        'pins': 16,
        'pad_size': 1.2,
        'drill': 0.8,
        'width': 7.62,
        'length': 20,
    },
    'lcd': {
        'name': 'Display_Character:LCD-016N002L',
        'pins': 16,
        'pad_size': 1.2,
        'drill': 0.8,
        'width': 60,
        'length': 20,
    },
    'default': {
        'name': 'TestPoint:TestPoint_2.54mm',
        'pad_distance': 2.54,
        'pad_size': 1.2,
        'drill': 0.8,
    }
}

# --- Templates for real KiCad footprints (from example.kicad_pcb) ---
RESISTOR_FOOTPRINT = '''  (footprint "Resistor_THT:R_Axial_DIN0204_L3.6mm_D1.6mm_P2.54mm_Vertical"
    (layer "F.Cu")
    (at {x:.2f} {y:.2f} {rot})
    (descr "Resistor, Axial_DIN0204 series, Axial, Vertical, pin pitch=2.54mm, 0.167W, length*diameter=3.6*1.6mm^2, http://cdn-reichelt.de/documents/datenblatt/B400/1_4W%23YAG.pdf")
    (tags "Resistor Axial_DIN0204 series Axial Vertical pin pitch 2.54mm 0.167W length 3.6mm diameter 1.6mm")
    (property "Reference" "{ref}" (at 1.397 -1.397 {rot}) (layer "F.SilkS"))
    (property "Value" "{value}" (at 1.27 1.92 {rot}) (layer "F.Fab"))
    (property "Datasheet" "" (at 0 0 {rot}) (layer "F.Fab") (hide yes))
    (property "Description" "" (at 0 0 {rot}) (layer "F.Fab") (hide yes))
    (path "")
    (attr through_hole)
    (fp_line (start 0.92 0) (end 1.54 0) (layer "F.SilkS") (width 0.12))
    (fp_circle (center 0 0) (end 0.92 0) (layer "F.SilkS") (width 0.12) (fill no))
    (fp_line (start 3.49 -1.05) (end -1.05 -1.05) (layer "F.CrtYd") (width 0.05))
    (fp_line (start -1.05 -1.05) (end -1.05 1.05) (layer "F.CrtYd") (width 0.05))
    (fp_line (start 3.49 1.05) (end 3.49 -1.05) (layer "F.CrtYd") (width 0.05))
    (fp_line (start -1.05 1.05) (end 3.49 1.05) (layer "F.CrtYd") (width 0.05))
    (fp_line (start 0 0) (end 2.54 0) (layer "F.Fab") (width 0.1))
    (fp_circle (center 0 0) (end 0.8 0) (layer "F.Fab") (width 0.1) (fill no))
    (fp_text user "${{REFERENCE}}" (at 1.27 -1.92 {rot}) (layer "F.Fab"))
    (pad "1" thru_hole circle (at 0 0 {rot}) (size 1.4 1.4) (drill 0.7) (layers "*.Cu" "*.Mask"))
    (pad "2" thru_hole oval (at 2.54 0 {rot}) (size 1.4 1.4) (drill 0.7) (layers "*.Cu" "*.Mask"))
    (embedded_fonts no)
    (model "${{KISYS3DMOD}}/Resistor_THT.3dshapes/R_Axial_DIN0204_L3.6mm_D1.6mm_P2.54mm_Vertical.wrl" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))
  )\n'''

CAPACITOR_FOOTPRINT = '''  (footprint "Capacitor_THT:C_Disc_D3.8mm_W2.6mm_P2.50mm"
    (layer "F.Cu")
    (at {x:.2f} {y:.2f} {rot})
    (descr "C, Disc series, Radial, pin pitch=2.50mm, , diameter*width=3.8*2.6mm^2, Capacitor, http://www.vishay.com/docs/45233/krseries.pdf")
    (tags "C Disc series Radial pin pitch 2.50mm  diameter 3.8mm width 2.6mm Capacitor")
    (property "Reference" "{ref}" (at 1.27 -1.651 {rot}) (layer "F.SilkS"))
    (property "Value" "{value}" (at 1.25 2.55 {rot}) (layer "F.Fab"))
    (property "Datasheet" "" (at 0 0 {rot}) (layer "F.Fab") (hide yes))
    (property "Description" "" (at 0 0 {rot}) (layer "F.Fab") (hide yes))
    (path "")
    (attr through_hole)
    (fp_line (start -0.77 1.42) (end 3.27 1.42) (layer "F.SilkS") (width 0.12))
    (fp_line (start -0.77 0.795) (end -0.77 1.42) (layer "F.SilkS") (width 0.12))
    (fp_line (start 3.27 0.795) (end 3.27 1.42) (layer "F.SilkS") (width 0.12))
    (fp_line (start -0.77 -1.42) (end -0.77 -0.795) (layer "F.SilkS") (width 0.12))
    (fp_line (start -0.77 -1.42) (end 3.27 -1.42) (layer "F.SilkS") (width 0.12))
    (fp_line (start 3.27 -1.42) (end 3.27 -0.795) (layer "F.SilkS") (width 0.12))
    (fp_line (start -1.05 1.55) (end 3.55 1.55) (layer "F.CrtYd") (width 0.05))
    (fp_line (start 3.55 1.55) (end 3.55 -1.55) (layer "F.CrtYd") (width 0.05))
    (fp_line (start -1.05 -1.55) (end -1.05 1.55) (layer "F.CrtYd") (width 0.05))
    (fp_line (start 3.55 -1.55) (end -1.05 -1.55) (layer "F.CrtYd") (width 0.05))
    (fp_line (start -0.65 1.3) (end 3.15 1.3) (layer "F.Fab") (width 0.1))
    (fp_line (start 3.15 1.3) (end 3.15 -1.3) (layer "F.Fab") (width 0.1))
    (fp_line (start -0.65 -1.3) (end -0.65 1.3) (layer "F.Fab") (width 0.1))
    (fp_line (start 3.15 -1.3) (end -0.65 -1.3) (layer "F.Fab") (width 0.1))
    (fp_text user "${{REFERENCE}}" (at 1.25 0 {rot}) (layer "F.Fab"))
    (pad "1" thru_hole circle (at 0 0 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "2" thru_hole circle (at 2.5 0 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (embedded_fonts no)
    (model "${{KISYS3DMOD}}/Capacitor_THT.3dshapes/C_Disc_D3.8mm_W2.6mm_P2.50mm.wrl" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))
  )\n'''

DIP28_FOOTPRINT = '''  (footprint "Package_DIP:DIP-28_W7.62mm"
    (layer "F.Cu")
    (at {x:.2f} {y:.2f} {rot})
    (descr "28-lead though-hole mounted DIP package, row spacing 7.62 mm (300 mils)")
    (tags "THT DIP DIL PDIP 2.54mm 7.62mm 300mil")
    (property "Reference" "{ref}" (at 3.937 0.635 {rot}) (layer "F.SilkS"))
    (property "Value" "{value}" (at 3.81 35.35 {rot}) (layer "F.Fab"))
    (property "Datasheet" "" (at 0 0 {rot}) (layer "F.Fab") (hide yes))
    (property "Description" "" (at 0 0 {rot}) (layer "F.Fab") (hide yes))
    (path "")
    (attr through_hole)
    (fp_line (start 1.16 -1.33) (end 1.16 34.35) (layer "F.SilkS") (width 0.12))
    (fp_line (start 1.16 34.35) (end 6.46 34.35) (layer "F.SilkS") (width 0.12))
    (fp_line (start 2.81 -1.33) (end 1.16 -1.33) (layer "F.SilkS") (width 0.12))
    (fp_line (start 6.46 -1.33) (end 4.81 -1.33) (layer "F.SilkS") (width 0.12))
    (fp_line (start 6.46 34.35) (end 6.46 -1.33) (layer "F.SilkS") (width 0.12))
    (fp_arc (start 4.81 -1.33) (mid 3.81 -0.33) (end 2.81 -1.33) (layer "F.SilkS") (width 0.12))
    (fp_line (start -1.1 -1.55) (end -1.1 34.55) (layer "F.CrtYd") (width 0.05))
    (fp_line (start -1.1 34.55) (end 8.7 34.55) (layer "F.CrtYd") (width 0.05))
    (fp_line (start 8.7 -1.55) (end -1.1 -1.55) (layer "F.CrtYd") (width 0.05))
    (fp_line (start 8.7 34.55) (end 8.7 -1.55) (layer "F.CrtYd") (width 0.05))
    (fp_line (start 0.635 -0.27) (end 1.635 -1.27) (layer "F.Fab") (width 0.1))
    (fp_line (start 0.635 34.29) (end 0.635 -0.27) (layer "F.Fab") (width 0.1))
    (fp_line (start 1.635 -1.27) (end 6.985 -1.27) (layer "F.Fab") (width 0.1))
    (fp_line (start 6.985 -1.27) (end 6.985 34.29) (layer "F.Fab") (width 0.1))
    (fp_line (start 6.985 34.29) (end 0.635 34.29) (layer "F.Fab") (width 0.1))
    (fp_text user "${{REFERENCE}}" (at 3.81 16.51 {rot}) (layer "F.Fab"))
    (pad "1" thru_hole rect (at 0 0 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "2" thru_hole oval (at 0 2.54 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "3" thru_hole oval (at 0 5.08 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "4" thru_hole oval (at 0 7.62 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "5" thru_hole oval (at 0 10.16 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "6" thru_hole oval (at 0 12.7 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "7" thru_hole oval (at 0 15.24 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "8" thru_hole oval (at 0 17.78 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "9" thru_hole oval (at 0 20.32 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "10" thru_hole oval (at 0 22.86 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "11" thru_hole oval (at 0 25.4 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "12" thru_hole oval (at 0 27.94 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "13" thru_hole oval (at 0 30.48 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "14" thru_hole oval (at 0 33.02 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "15" thru_hole oval (at 7.62 33.02 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "16" thru_hole oval (at 7.62 30.48 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "17" thru_hole oval (at 7.62 27.94 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "18" thru_hole oval (at 7.62 25.4 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "19" thru_hole oval (at 7.62 22.86 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "20" thru_hole oval (at 7.62 20.32 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "21" thru_hole oval (at 7.62 17.78 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "22" thru_hole oval (at 7.62 15.24 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "23" thru_hole oval (at 7.62 12.7 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "24" thru_hole oval (at 7.62 10.16 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "25" thru_hole oval (at 7.62 7.62 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "26" thru_hole oval (at 7.62 5.08 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "27" thru_hole oval (at 7.62 2.54 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (pad "28" thru_hole oval (at 7.62 0 {rot}) (size 1.6 1.6) (drill 0.8) (layers "*.Cu" "*.Mask"))
    (embedded_fonts no)
    (model "${{KISYS3DMOD}}/Package_DIP.3dshapes/DIP-28_W7.62mm.wrl" (offset (xyz 0 0 0)) (scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))
  )\n'''

# Load BOM and PCB JSON
with open(BOM_FILE) as f:
    bom = {c['reference']: c for c in json.load(f)}
with open(PCB_JSON_FILE) as f:
    pcb_json = json.load(f)
    board = pcb_json.get('board', {})
    board_width = board.get('width', 80)
    board_height = board.get('height', 36)

# Parse netlist
components = []
nets = set()
with open(NETLIST_FILE) as f:
    lines = f.readlines()
    for line in lines:
        line = line.strip()
        if not line or line.startswith('*') or line == '.END':
            continue
        m = re.match(r'([A-Z0-9]+)\s+(.+)', line)
        if m:
            ref = m.group(1)
            rest = m.group(2)
            if ref in bom:
                comps = rest.split()
                nets.update(comps[:-1])
                components.append(ref)
        elif line.startswith('X'):
            ref = line.split()[0]
            if ref in bom:
                components.append(ref)

# Assign net numbers
net_map = {n: i+1 for i, n in enumerate(sorted(nets))}

# KiCad PCB header (full, from example.kicad_pcb)
kicad_header = '''(kicad_pcb
	(version 20241229)
	(generator "pcbnew")
	(generator_version "9.0")
	(general
		(thickness 1.6)
		(legacy_teardrops no)
	)
	(paper "A4")
	(layers
		(0 "F.Cu" signal)
		(2 "B.Cu" signal)
		(9 "F.Adhes" user)
		(11 "B.Adhes" user)
		(13 "F.Paste" user)
		(15 "B.Paste" user)
		(5 "F.SilkS" user)
		(7 "B.SilkS" user)
		(1 "F.Mask" user)
		(3 "B.Mask" user)
		(17 "Dwgs.User" user)
		(19 "Cmts.User" user)
		(21 "Eco1.User" user)
		(23 "Eco2.User" user)
		(25 "Edge.Cuts" user)
		(27 "Margin" user)
		(31 "F.CrtYd" user)
		(29 "B.CrtYd" user)
		(35 "F.Fab" user)
		(33 "B.Fab" user)
	)
	(setup
		(pad_to_mask_clearance 0.051)
		(solder_mask_min_width 0.25)
		(allow_soldermask_bridges_in_footprints no)
		(tenting front back)
		(pcbplotparams
			(layerselection 0x00000000_00000000_55555555_575555ff)
			(plot_on_all_layers_selection 0x00000000_00000000_00000000_02000000)
			(disableapertmacros no)
			(usegerberextensions no)
			(usegerberattributes yes)
			(usegerberadvancedattributes no)
			(creategerberjobfile no)
			(dashed_line_dash_ratio 12.000000)
			(dashed_line_gap_ratio 3.000000)
			(svgprecision 4)
			(plotframeref no)
			(mode 1)
			(useauxorigin no)
			(hpglpennumber 1)
			(hpglpenspeed 20)
			(hpglpendiameter 15.000000)
			(pdf_front_fp_property_popups yes)
			(pdf_back_fp_property_popups yes)
			(pdf_metadata yes)
			(pdf_single_document no)
			(dxfpolygonmode yes)
			(dxfimperialunits yes)
			(dxfusepcbnewfont yes)
			(psnegative no)
			(psa4output no)
			(plot_black_and_white yes)
			(plotinvisibletext no)
			(sketchpadsonfab no)
			(plotpadnumbers no)
			(hidednponfab no)
			(sketchdnponfab yes)
			(crossoutdnponfab yes)
			(subtractmaskfromsilk no)
			(outputformat 4)
			(mirror no)
			(drillshape 0)
			(scaleselection 1)
			(outputdirectory "gerbers/")
		)
	)
'''

# Write nets
net_section = '  (net 0 "")\n'
for net, num in net_map.items():
    net_section += f'  (net {num} "{net}")\n'

# Centering and spacing
center_x = board_width / 2
center_y = board_height / 2
spacing_x = 10
spacing_y = 10
start_x = center_x - (spacing_x * (len(components)-1) / 2)
start_y = center_y

# Write footprints with generic drawing
footprint_section = ''
for idx, ref in enumerate(components):
    bom_entry = bom.get(ref, {})
    value = bom_entry.get('value', '')
    ctype = bom_entry.get('type', '').lower()
    # Pick generic footprint
    fp = GENERIC_FOOTPRINTS.get(ctype, GENERIC_FOOTPRINTS['default'])
    x = start_x + idx * spacing_x
    y = start_y
    if ctype == 'resistor':
        footprint_section += RESISTOR_FOOTPRINT.format(x=x, y=y, rot=90, ref=ref, value=value)
    elif ctype == 'capacitor':
        footprint_section += CAPACITOR_FOOTPRINT.format(x=x, y=y, rot=0, ref=ref, value=value)
    elif ctype == 'mcu':
        footprint_section += DIP28_FOOTPRINT.format(x=x, y=y, rot=0, ref=ref, value=value)
    else:
        # Default: single test point
        footprint_section += (
            f'  (footprint "{fp["name"]}"\n'
            f'    (layer "F.Cu")\n'
            f'    (at {x:.2f} {y:.2f} 0)\n'
            f'    (property "Reference" "{ref}" (at 0 2 0) (layer "F.SilkS"))\n'
            f'    (property "Value" "{value}" (at 0 -2 0) (layer "F.Fab"))\n'
            f'    (pad "1" thru_hole circle (at 0 0) (size {fp["pad_size"]} {fp["pad_size"]}) (drill {fp["drill"]}) (layers "F.Cu" "B.Cu" "F.Mask"))\n'
            f'  )\n'
        )

# Add minimal board outline (Edge.Cuts)
outline_section = (
    f'  (gr_line (start 0 0) (end {board_width} 0) (layer "Edge.Cuts") (width 0.05))\n'
    f'  (gr_line (start {board_width} 0) (end {board_width} {board_height}) (layer "Edge.Cuts") (width 0.05))\n'
    f'  (gr_line (start {board_width} {board_height}) (end 0 {board_height}) (layer "Edge.Cuts") (width 0.05))\n'
    f'  (gr_line (start 0 {board_height}) (end 0 0) (layer "Edge.Cuts") (width 0.05))\n'
)

# Close file
kicad_footer = ')\n'

with open(OUTPUT_FILE, 'w') as f:
    f.write(kicad_header)
    f.write(net_section)
    f.write(footprint_section)
    f.write(outline_section)
    f.write(kicad_footer)

print(f"Wrote {OUTPUT_FILE}") 