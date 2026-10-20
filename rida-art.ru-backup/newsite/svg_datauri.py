# -*- coding: utf-8 -*-
"""Превращает bg-toys*.svg в data URI для CSS (out/<имя>.datauri.txt). Аргумент — имя svg, по умолчанию bg-toys.svg."""
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
name = sys.argv[1] if len(sys.argv) > 1 else 'bg-toys.svg'
s = open(os.path.join(HERE, name), encoding='utf-8').read()
s = re.sub(r'<!--.*?-->', '', s, flags=re.S)
s = re.sub(r'>\s+<', '><', s).strip().replace('"', "'")
e = urllib.parse.quote(s, safe=" ='/:;,.-()")
out = os.path.join(HERE, 'out', os.path.splitext(name)[0] + '.datauri.txt')
open(out, 'w', encoding='utf-8').write(e)
print(len(e))
print(e)
