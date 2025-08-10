"""convert between siliXon project using pcb.json and _netlist.txt to give kicad_converted.net"""


import json
import re
from pathlib import Path

def parse_components(netlist_file):
    """Parse connections from pcb"""


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
    
    
    connections = {}
    nets = {}
    net_list = []  # Add this to track net order
    net_counter = 1
    
   