#/usr/bin/env python
# -*- coding: utf-8 -*-

import csv

with open('liste_sans_doublons.csv') as f:
    uniqs = list(csv.DictReader(f))

uid = lambda x: x['Compte twitter'].lstrip('@').strip().lower()

CRs = []
with open('liste_CR.csv') as f:
    for r in list(csv.DictReader(f)):
        CRs.append(uid(r))
CPs = []
with open('liste_CP.csv') as f:
    for r in list(csv.DictReader(f)):
        CPs.append(uid(r))

headers = ['Compte twitter','Nom',u'Prénom','CR','CP']
print (u",".join(headers)).encode('utf-8')
for u in uniqs:
    v = uid(u)
    for k in u:
        u[k] = u[k].strip().decode('utf-8')
    u['CR'] = str((v in CRs))
    u['CP'] = str((v in CPs))
    print ','.join([u[h.encode('utf8')].encode('utf8') for h in headers])

