# -*- coding: utf-8 -*-
# ======================================================================
# Script runner for the Music Single-Domain-Task-Battery (Music-SDTB)
# Behavioral session launcher for mixed PsychoPy and Expyriment protocols
#
# How to run the script:
# python script_runner.py <pc_type> <subject_number> <session_number> <line_number_from_session_plan>
# Example:
# python script_runner.py win 48 1 7
# ======================================================================

import csv
import re
import subprocess
import sys
from pathlib import Path


# %%
# ============================== PATHS =================================

ROOT = Path(__file__).resolve().parent

INPUTS_DIR = ROOT / "inputs" / "behavioral-sessions_inputs"
OUTPUT_DIR = ROOT / "data"
EXPY_DIR = ROOT / "expy_protocols"
PP_DIR = ROOT / "pp_protocols"


# %%
# ============================ ENVIRONMENTS ============================

EXPY_ENV = r"C:\Users\music-sdtb\anaconda3\envs\expy010-py3711\python.exe"
PP_ENV = r"C:\Users\music-sdtb\anaconda3\envs\psychopy202225-py3923\python.exe"

STIMTRACKER = "n"


# %%
# ============================== SCRIPTS ===============================

EXPY_SCRIPT = "music-sdtb_bauto_single.py"

PP_SCRIPTS = {
    "production": "one_st_audio_production.py",
    "perception": "one_st_audio_perception.py",
    "notemporal": "one_st_audio_NTFD.py",
}


# %%
# ============================= FUNCTIONS ==============================

# Parse the command line arguments passed to the runner.
def parse_arguments():
    assert len(sys.argv) == 5, (
        "Usage: python script_runner.py <pc_type> <subject_number> "
        "<session_number> <line_number_from_session_plan>"
    )

    pc_type = sys.argv[1]
    subject_no = int(sys.argv[2])
    session_no = int(sys.argv[3])
    start_line = int(sys.argv[4])

    return pc_type, subject_no, session_no, start_line


# Load the behavioral session plan for the selected subject/session.
def load_plan(subject_no, session_no):
    plan_path = INPUTS_DIR / (
        "sub-%02d" % subject_no
    ) / (
        "ses-%02d" % session_no
    ) / (
        "plan_sub-%02d" % subject_no + "_ses-%02d" % session_no + ".tsv"
    )

    with open(plan_path, newline="") as plan_file:
        plan = [
            row[0].strip()
            for row in csv.reader(plan_file, delimiter="\t")
            if row and row[0].strip()
        ]

    return plan


# Parse one line from the session plan.
def parse_plan_entry(plan_entry):
    task_name, run_number = re.match("(.*)_run-(.*)", plan_entry).groups()
    modality, protocol = task_name.split("_", 1)

    return task_name, modality, protocol, int(run_number)


# Show the current runner prompt before launching the next protocol.
def display_prompt(previous_entry, previous_line, current_entry, current_line):
    if previous_entry is None:
        previous_text = "None"
    else:
        _, prev_modality, prev_protocol, prev_run = parse_plan_entry(previous_entry)
        previous_text = (
            f"{prev_modality} {prev_protocol} run {prev_run} | "
            f"line {previous_line}"
        )

    _, current_modality, current_protocol, current_run = parse_plan_entry(
        current_entry
    )
    current_text = (
        f"{current_modality} {current_protocol} run {current_run} | "
        f"line {current_line}"
    )

    print("")
    print("--------------------------------------------------")
    print(f"Previous: {previous_text}")
    print(f"Next:     {current_text}")

    while True:
        answer = input(
            "Press ENTER to continue, B to go back, N to go next, "
            "or Q to quit: "
        )
        answer = answer.strip().lower()
        print("--------------------------------------------------")

        if answer == "":
            return "continue"
        if answer == "b":
            return "back"
        if answer == "n":
            return "forward"
        if answer == "q":
            return "quit"

        print(
            "Please press ENTER to continue, B to go back, N to go next, "
            "or Q to quit."
        )


# Get the environment, folder, and script for the selected protocol.
def get_launch_info(modality, protocol):
    if modality == "audio":
        env = PP_ENV
        protocol_dir = PP_DIR
        script = PP_SCRIPTS[protocol]
    elif modality == "visual":
        env = EXPY_ENV
        protocol_dir = EXPY_DIR
        script = EXPY_SCRIPT
    else:
        raise ValueError("Unknown modality: " + modality)

    return env, protocol_dir, script


# Launch one protocol as a child process.
def run_protocol(env, protocol_dir, script, pc_type, subject_no, session_no,
                 protocol_number, stimtracker=None):
    command = [
        env,
        str(protocol_dir / script),
        pc_type,
        str(subject_no),
        str(session_no),
        str(protocol_number),
    ]

    if stimtracker is not None:
        command.append(stimtracker)

    return subprocess.run(command, cwd=str(protocol_dir))


# %%
# ============================== RUNNER ================================

# Run the behavioral session from the selected line to the end of the plan.
def main():
    pc_type, subject_no, session_no, start_line = parse_arguments()
    plan = load_plan(subject_no, session_no)

    next_line = start_line

    while next_line <= len(plan):
        current_line = next_line
        previous_line = current_line - 1

        if previous_line > 0:
            previous_entry = plan[previous_line - 1]
        else:
            previous_entry = None
            previous_line = None

        current_entry = plan[current_line - 1]

        action = display_prompt(
            previous_entry, previous_line, current_entry, current_line
        )
        if action == "quit":
            print("Session runner quit.")
            return
        if action == "back":
            if current_line > 1:
                next_line = current_line - 1
            else:
                print("Already at first line!")
                next_line = current_line
            continue
        if action == "forward":
            if current_line < len(plan):
                next_line = current_line + 1
            else:
                print("Already at last line!")
                next_line = current_line
            continue

        _, modality, protocol, run_number = parse_plan_entry(current_entry)
        env, protocol_dir, script = get_launch_info(modality, protocol)

        if modality == "audio":
            protocol_number = run_number
            stimtracker = STIMTRACKER
        else:
            protocol_number = current_line
            stimtracker = None

        result = run_protocol(
            env, protocol_dir, script, pc_type, subject_no, session_no,
            protocol_number, stimtracker
        )

        if result.returncode == 120:
            print("Protocol aborted by user. Continuing to next line.")
        elif result.returncode != 0:
            print("Protocol exited with return code %d." % result.returncode)
            return

        next_line = current_line + 1

    print("Session complete. No more runs in plan.")


if __name__ == "__main__":
    main()
