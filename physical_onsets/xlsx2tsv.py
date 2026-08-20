#!/usr/bin/env python3

"""
Convert an Excel file with multiple sheets into separate TSV files.

author: Ana Luisa Pinho
email: agrilopi@uwo.ca

Creation: 16th of March 2026
Last Update: April 2026  

Compatibility: Python 3.10.16
"""

import os
import pandas as pd

# Paths
home_dir = os.path.expanduser("~")
script_dir = os.path.dirname(os.path.abspath(__file__))

# Input Excel file
input_dir = os.path.join(
    home_dir, 'Dropbox', 'CentralDocs', 'western_postdoc',
    'music-sdtb_project', 'physical-onset_analysis', 'cedrus_analysis',
    '5.psychopy_ptb-st_only-audio_april2026',
)
xlsx_file = os.path.join(
    input_dir, 
    'raw-files_extraction',
    'rawEventTimings_20260415.xlsx')

# Output directory
out_dir = os.path.join(script_dir,
                       'data_psychopy_ptb-st_audio-only_april2026')
os.makedirs(out_dir, exist_ok=True)

# Read all sheets
sheets = pd.read_excel(xlsx_file, sheet_name=None)

for sheet_name, df in sheets.items():

    # Make sheet name filesystem-safe
    safe_name = "".join(
        c if c.isalnum() or c in " _-." else "_"
        for c in sheet_name
    )

    out_file = os.path.join(out_dir, f"{safe_name}.tsv")

    df.to_csv(out_file, sep="\t", index=False)