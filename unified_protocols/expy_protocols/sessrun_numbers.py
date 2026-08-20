# -*- coding: utf-8 -*-
# ======================================================================
# Script to add missing session number and
# change index run number from 0 to 1 in logfiles
#
# Author: Ana Luísa Pinho
#
# email: agrilopi@uwo.ca
#
# Created: July 2022
# Last Update: May 2023
#
# Compatibility: Python 3.7.11
# ======================================================================

import os
import glob
import csv
import re


dic_subsess = {4: [1], 7: [1, 2, 3], 8: [1, 2], 9: [1]}

for subject in list(dic_subsess.keys()):
    for session in dic_subsess[subject]:
        fpath = os.path.join('data', 'sessrun_versions', 'sub-%02d' % subject,
                             'ses-%02d' % session)
        for f in glob.glob(fpath + '/*_withsessrun.xpd'):
            os.remove(f)
        listxpd = glob.glob(fpath + '/*.xpd')
        listxpd.sort()
        for xpd in listxpd:
            with open(xpd) as f:
                xpd_table = f.readlines()
            xpd_table = [row.replace('\n', '') for row in xpd_table]
            new_listxpd = []
            for line in xpd_table:
                if line[:1] != '#':
                    line = line.split(",")
                    if line[0] == 'subject_id':
                        # Add "session_number" tag to the title row
                        line.insert(1, 'session_number')
                    else:
                        # Add session number to each row
                        line.insert(1, str(session))
                        # Change run_number index from 0 to 1
                        run_number = int(line[2])
                        line[2] = str(run_number+1)
                    line = ','.join(line)
                new_listxpd.extend([line])
            fname = re.match('.*/(.*).xpd', xpd).groups()[0]
            outfname = os.path.join(fpath, fname + '_withsessrun.xpd')
            with open(outfname, 'w') as f:
                for entry in new_listxpd:
                    f.write(entry)
                    f.write('\n')
