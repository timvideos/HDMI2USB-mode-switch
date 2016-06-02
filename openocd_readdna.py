#!/usr/bin/env python
# vim: set ts=4 sw=4 et sts=4 ai:

import subprocess
import re
import sys

output = subprocess.check_output("""\
openocd --file board/%s.cfg -c "init; xc6s_print_dna xc6s.tap; exit"
""" % sys.argv[1], shell=True, stderr=subprocess.STDOUT)

for line in output.splitlines():
    line = line.decode('utf-8')
    if not line.startswith('DNA = '):
       continue

    dna = re.match("DNA = ([10]*) \((0x[01-9a-f]*)\)", line)
    binv, hexv = dna.groups()
    binc = int(binv, 2)
    hexc = int(hexv, 16)
    assert binc == hexc

    hexs = hex(hexc)
    import barcode
    b = barcode.get('Code128', hexs[2:])
    b.save('barcode_dna', {'module_height': 10, 'module_width': 0.25, 'font_size': 12, 'text_distance': 5, 'human': 'DNA - %s' % hexs})
    
    
