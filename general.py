import sys
sys.path.insert(0, '/Users/mathilde/Library/Python/3.10/lib/python/site-packages')

import os, json
import importlib.util
import argparse

from pathlib import Path
from psychopy import core

from init import button_box, stim_monitor
from MMN.MMN_RUN import run_MMN
from EMOTION.EMOTION_RUN import run_EMOTION
from ASSR.ASSR_RUN import run_ASSR
from utils.escape_cleanup_abort import cleanup
from utils.buttonsNew import enable_din_dout_passthrough_pixel_mode
from utils.help_funcs import input_to_continue

# --------------- INPUT ARGS TO START THE SCRIPT ----------------
parser = argparse.ArgumentParser()
parser.add_argument('--sub',   type=str, required=True,       help='Subject ID, e.g. 01')
parser.add_argument('--group', type=str, default='A',         help='A or B (EMOTION paradigm)')
parser.add_argument('--msr',   type=int, default=0,           help='1 = MSR, 0 = no')
args = parser.parse_args()

SUB   = args.sub
GROUP = args.group
MSR   = args.msr

# ------------------------ PARADIGMS ---------------------------
paradigms = [{"name": "ASSR", "runs": [1]}, 
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

input('Sequence files generated. Press Enter to continue with first paradigm.')

# Load config-file for setup
with open(Path(BASE_DIR)/"config.json") as f:
    config = json.load(f)

monitor = stim_monitor(config)
device, buttonCodes, myLog = button_box(config)
enable_din_dout_passthrough_pixel_mode() 


# # ----------------------- RUN ASSR ----------------------------
# paradigm = next(p for p in paradigms if p["name"] == "ASSR")
# SUB_DIR = os.path.join(DATA_DIR, paradigm["name"], SUB)
# print("Paradigm: ASSR.")
# for RUN in paradigm["runs"]:
#     run_ASSR(device, buttonCodes, myLog, monitor, MSR, SUB, RUN, SUB_DIR)
#     input(f"ASSR run {RUN} done. Press Enter to continue.")


# ----------------------- RUN EMOTION ----------------------------
paradigm = next(p for p in paradigms if p["name"] == "EMOTION")
SUB_DIR = os.path.join(DATA_DIR, paradigm["name"], SUB)
print("Paradigm: EMOTION.")
for RUN in paradigm["runs"]:
    run_EMOTION(device, buttonCodes, myLog, monitor, MSR, SUB, RUN, GROUP, SUB_DIR)
    #input(f"EMOTION run {RUN} done. Press Enter to continue.")
    input_to_continue(paradigm["name"], RUN, SUB)
print("EMOTION paradigm done.")

# ------------------------- RUN MMN -----------------------------
paradigm = next(p for p in paradigms if p["name"] == "MMN")
SUB_DIR = os.path.join(DATA_DIR, paradigm["name"], SUB)
print("Paradigm: MMN.")
for RUN in paradigm["runs"]:
    run_MMN(device, buttonCodes, myLog, monitor, MSR, SUB, RUN, SUB_DIR)
    input_to_continue(paradigm["name"], RUN, SUB)
print("ASSR paradigm done.")

print("All paradigms done.")

# ----------------------- CLEANUP & QUIT -------------------------
device.din.stopDinLog() # this in cleanup i think
cleanup()
core.quit()