import os, json, sys
import importlib.util
import argparse

from pathlib import Path
from psychopy import core

from init import button_box, stim_monitor
from MMN.MMN_RUN import run_MMN
from EMOTION.EMOTION_RUN import run_EMOTION
from ASSR.ASSR_RUN import run_ASSR
from hearing_threshold.Run_Hearing_Threshold import run_hearing_threshold
from utils.escape_cleanup_abort import cleanup
from utils.help_funcs import input_to_continue, should_skip

# --------------- INPUT ARGS TO START THE SCRIPT ----------------
#sub and group required; MSR=1, ht=1 and start with first paradigm run 1 as default
parser = argparse.ArgumentParser()
parser.add_argument('--sub', type=str, required=True, help='Subject ID, e.g. 01')
parser.add_argument('--group', type=str, required=True, help='A or B (EMOTION paradigm)')
parser.add_argument('--msr', type=int, default=1, help='1 = MSR, 0 = no')
parser.add_argument('--start', type=str, default="ASSR" ,help='Paradigm to start with')
parser.add_argument('--run', type=int, default=1, help='Run to start with')
parser.add_argument('--ht', type=int, default=1, help='Measure hearing threshold: 1=yes, 0=no')
args = parser.parse_args()

SUB   = args.sub
GROUP = args.group
MSR   = args.msr
START_PARADIGM = args.start
START_RUN = args.run
HT = args.ht

# ------------------------ PARADIGMS ---------------------------
paradigms = [{"name": "ASSR", "runs": [1, 2]}, # 1= PAS, 2 = ATT
             {"name": "EMOTION", "runs": [1, 2]}, #, 3, 4]}, 
             {"name": "MMN", "runs": [1, 2]}]

# -------------------- GENERATE SEQUENCES ----------------------
# Define Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # script location
DATA_DIR = os.path.join(BASE_DIR, "DATA")
for paradigm in paradigms:
    DIR  = os.path.join(DATA_DIR, paradigm["name"], SUB)
    os.makedirs(DIR, exist_ok=True) # make the folder if doesn't exist already

    # load e.g. MMN/MMN_init.py dynamically
    spec = importlib.util.spec_from_file_location(
        paradigm['name'],
        os.path.join(BASE_DIR, paradigm["name"], f"{paradigm['name']}_init.py")
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[paradigm["name"]] = module
    spec.loader.exec_module(module)

    for run in paradigm['runs']:
        module.create_participant_sequences(
            sub_dir=DIR,
            sub_id=SUB,
            current_run=run,
            group_id = GROUP
        )

input_to_continue("SEQ", 0, SUB)

# Load config-file for setup
with open(Path(BASE_DIR)/"config.json") as f:
    config = json.load(f)

monitor = stim_monitor(config)
device, buttonCodes, myLog = button_box(config)

# ----------------- RUN HEARING THRESHOLD ----------------------
if HT:
    SUB_DIR = os.path.join(DATA_DIR, "HEARING THRESHOLD", SUB)
    os.makedirs(SUB_DIR, exist_ok=True)
    print("Measuring Hearing Threshold.")
    run_hearing_threshold(device, buttonCodes, myLog, SUB, SUB_DIR)
    input_to_continue("Hearing Threshold", 0, SUB)

# ----------------------- RUN ASSR ----------------------------
paradigm = next(p for p in paradigms if p["name"] == "ASSR")
SUB_DIR = os.path.join(DATA_DIR, paradigm["name"], SUB)
print("Paradigm: ASSR.")
for RUN in paradigm["runs"]:
    if should_skip(paradigms, "ASSR", RUN, START_PARADIGM, START_RUN):
        print(f"Skipping ASSR run {RUN}.")
        continue
    run_ASSR(device, buttonCodes, myLog, monitor, MSR, SUB, RUN, SUB_DIR)
    input_to_continue(paradigm["name"], RUN, SUB)
print("ASSR paradigm done.")

# ----------------------- RUN EMOTION ----------------------------
paradigm = next(p for p in paradigms if p["name"] == "EMOTION")
SUB_DIR = os.path.join(DATA_DIR, paradigm["name"], SUB)
print("Paradigm: EMOTION.")
for RUN in paradigm["runs"]:
    if should_skip(paradigms, "EMOTION", RUN, START_PARADIGM, START_RUN):
        print(f"Skipping EMOTION run {RUN}.")
        continue
    run_EMOTION(device, buttonCodes, myLog, monitor, MSR, SUB, RUN, GROUP, SUB_DIR)
    input_to_continue(paradigm["name"], RUN, SUB)
print("EMOTION paradigm done.")

# ------------------------- RUN MMN -----------------------------
paradigm = next(p for p in paradigms if p["name"] == "MMN")
SUB_DIR = os.path.join(DATA_DIR, paradigm["name"], SUB)
print("Paradigm: MMN.")
for RUN in paradigm["runs"]:
    if should_skip(paradigms, "MMN", RUN, START_PARADIGM, START_RUN):
        print(f"Skipping MMN run {RUN}.")
        continue
    run_MMN(device, buttonCodes, myLog, monitor, MSR, SUB, RUN, SUB_DIR)
    input_to_continue(paradigm["name"], RUN, SUB)
print("MMN paradigm done.")

print("All paradigms done.")

# ----------------------- CLEANUP & QUIT -------------------------
device.din.stopDinLog() # this in cleanup i think
cleanup()
core.quit()