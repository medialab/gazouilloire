#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division
from __future__ import print_function

import os
import sys
from random import random

try:
    input_csv = sys.argv[1]
    output_size_mo = int(sys.argv[2])
except Exception as e:
    sys.stderr.write("USAGE: bin/samplize.py INPUT_CSV OUTPUT_SIZE_MO\n")
    exit("%s: %s" % (type(e), e))

if not os.path.exists(input_csv) or not os.path.isfile(input_csv):
    exit("ERROR INPUT_CSV file %s does not exist" % input_csv)
input_size_mo = os.path.getsize(input_csv) / 1024. / 1024
ratio = min(1, output_size_mo / input_size_mo)

sys.stderr.write("Extracting %.1f%% of file %s of %.1fMo\n" %
                 (100*ratio, input_csv, input_size_mo))
header_done = False
with open(input_csv) as f:
    for line in f.readlines():
        if not header_done:
            print(line)
            header_done = True
            continue
        if ratio >= 1 or random() <= ratio:
            print(line)
