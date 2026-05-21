import sys
sys.path.insert(0, '/Users/mathilde/Library/Python/3.10/lib/python/site-packages')

import os
import random
import csv
from psychopy import visual

# -------------------------- PATHS -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # script location
STIM_DIR = os.path.join(BASE_DIR, "EMO-stimuli", "faces", "realistic")

# -------------------------- TRIGGERS (161-254) -----------------------
# use trigger numbers below 255 so it stays onyl in the G channel
# and use trigger numbers above 160 so it actually goes UP. To make the signal go UP (to a higher voltage or a higher integer value in analysis), you must use numbers strictly greater than 160.

TRIG_START = 241
TRIG_END   = 242

# i have 20 trigger codes which i want to space between 161 and 254. so if i take steps of 4, i can have 20 codes: 161, 165, 169, ..., 241. this gives me enough room to add more codes in the future if needed.
# trigger codes in steps of 4:
TRIG_WNA, TRIG_WSA, TRIG_WFA, TRIG_WAA, TRIG_WHA = 162, 166, 170, 174, 178
TRIG_WNB, TRIG_WSB, TRIG_WFB, TRIG_WAB, TRIG_WHB = 182, 186, 190, 194, 198
TRIG_MNA, TRIG_MSA, TRIG_MFA, TRIG_MAA, TRIG_MHA = 202, 206, 210, 214, 218
TRIG_MNB, TRIG_MSB, TRIG_MFB, TRIG_MAB, TRIG_MHB = 222, 226, 230, 234, 238

TRIG_RESP_right = 247
TRIG_RESP_left  = 252

trigger_map = { "WNA": TRIG_WNA, "WSA": TRIG_WSA, "WFA": TRIG_WFA, "WAA": TRIG_WAA, "WHA": TRIG_WHA,
                "WNB": TRIG_WNB, "WSB": TRIG_WSB, "WFB": TRIG_WFB, "WAB": TRIG_WAB, "WHB": TRIG_WHB,
                "MNA": TRIG_MNA, "MSA": TRIG_MSA, "MFA": TRIG_MFA, "MAA": TRIG_MAA, "MHA": TRIG_MHA,
                "MNB": TRIG_MNB, "MSB": TRIG_MSB, "MFB": TRIG_MFB, "MAB": TRIG_MAB, "MHB": TRIG_MHB }


# -------------------------- GENERATE TRIAL SEQUENCE --------------------------
def create_participant_sequences(sub_dir, sub_id, current_run, group_id):
    """ Generates 1 trial sequences csv per run.
        Checks if the file already exists to prevent overwriting.

    Naming of the faces is done using a 3-letter code:
        - 1st letter: W (woman) or M (man)
        - 2nd letter: N (neutral), S (sad), F (fearful), A (angry), H (happy)
        - 3rd letter: A or B (two different versions per category)
    
    Psydorandomization logic:
    - 5 blocks of 40 trials each (200 trials total)
    - Each block contains 2 of each of the 20 face types
    - Within each block, trials are shuffled with the following constraints:
        1. No identical face codes can be adjacent (e.g., WNA cannot be immediately followed by WNA).
        2. No more than 3 trials of the same emotion can occur in a row (e.g., you cannot have WNA, WNB, MNA, WAA in a row because that would be 3 "Neutral" emotions in a row).
    - in each block, there should be no more than 4 trials with the same sex in a row
    """
    os.makedirs(sub_dir, exist_ok=True)
    sequence_file = os.path.join(sub_dir, f"{sub_id}_group-{group_id}_run-{current_run}_EMO_trial_sequence.csv")

    if os.path.exists(sequence_file):
        print(f"INFO: Sequence file already exists for {sub_id}. Skipping.")
        return

    face_list = [
        "WNA","WSA","WFA","WAA", "WNB","WSB","WFB","WAB", "WHA","WHB",
        "MNA","MSA","MFA","MAA", "MNB","MSB","MFB","MAB", "MHA","MHB"
    ]
    
    # 5 blocks of 40 = 200 trials total
    num_blocks = 5
    trials_per_block = 40
    full_sequence = []

    def get_emotion(face_code):
        return face_code[1] # Extracts N, S, F, A, or H

    print(f"GENERATING: New sequence for {sub_id}, run {current_run}...")

    for b in range(num_blocks):
        # Create a pool for this block (each face type appears twice)
        block_pool = face_list * 2
        
        while True:
            random.shuffle(block_pool)
            valid = True
            
            # Temporary sequence to test against existing trials
            test_seq = full_sequence + block_pool
            
            # Start checking from the end of the previous block to ensure smooth transitions
            # We check from the start of the current block minus 3 (to catch emotion streaks)
            check_start = max(1, len(full_sequence) - 3)
            
            for i in range(check_start, len(test_seq)):
                # Constraint 1: No identical codes back-to-back
                if test_seq[i] == test_seq[i-1]:
                    valid = False
                    break
                
                # Constraint 2: Max 3 of same emotion in a row
                if i >= 3:
                    emotions = [get_emotion(f) for f in test_seq[i-3:i+1]]
                    if len(set(emotions)) == 1: # All 4 are the same
                        valid = False
                        break

                # Constraint 3: Max 4 of same sex in a row
                # adapt if needed (if the script breaks as it cant find the sequence. but should work like this)
                if i >= 4:
                    sexes = [f[0] for f in test_seq[i-4:i+1]]
                    if len(set(sexes)) == 1: # All 5 are the same
                        valid = False
                        break

            if valid:
                full_sequence = test_seq
                break
            # If invalid, the 'while True' loop shuffles the block_pool again

    # Prepare data for CSV
    all_trials = []
    for i, face in enumerate(full_sequence, start=1):
        all_trials.append({
            "run": current_run,
            "trial_index": i,
            "face": face,
            "emotion": get_emotion(face) # Useful for analysis later
        })

    # Write to file
    with open(sequence_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_trials[0].keys())
        writer.writeheader()
        writer.writerows(all_trials)
    
    print(f"SUCCESS: Sequence created with {len(full_sequence)} trials.")

# -------------------------- PRELOAD STIMULI AND TEXT ---------------
def preload_stimuli(win):
    fixation_angle 	= 17  # -------------> visual angle in degrees. adapt if size needs change

    # load .png files
    face_list = [ "WNA","WSA","WFA","WAA","WHA","WNB","WSB","WFB","WAB","WHB","MNA","MSA","MFA","MAA","MHA","MNB","MSB","MFB","MAB","MHB"]
    stim_dict = { "fixation": visual.ImageStim(win, image=os.path.join(STIM_DIR, 'fix.png'), size=fixation_angle, pos=(0,1.5))}
    
    for face_code in face_list:
        stim_dict[face_code] = visual.ImageStim(win, image=os.path.join(STIM_DIR, f'{face_code}.png'), size=fixation_angle, pos=(0,1.5))
    
    return stim_dict # stim_dict contains: "fixation", "WNA", "WSA", "WFA", etc. as keys, and the corresponding ImageStim objects as values

def preload_txt(win):
    txt_intro_A = visual.TextStim(win, text="Drücken Sie den rechten/roten Knopf, wenn Sie eine Frau sehen, \n\n und den linken/grünen Knopf, wenn Sie einen Mann sehen. \n\n \n\n Drücken Sie einen beliebigen Knopf um zu starten.", height=1, pos=(0, 0), units='deg', color='black')
    txt_intro_B = visual.TextStim(win, text="Drücken Sie den rechten/roten Knopf, wenn Sie einen Mann sehen, \n\n und den linken/grünen Knopf, wenn Sie eine Frau sehen. \n\n \n\n Drücken Sie einen beliebigen Knopf um zu starten.", height=1, pos=(0, 0), units='deg', color='black')
    txt_finished = visual.TextStim(win, text="Dieser Durchgang ist beendet.\n Vielen Dank. \n\n Bitte warten Sie auf Anweisungen.", height=1, pos=(0, 0), units='deg', color='black')
    return {"txt_intro_A": txt_intro_A, "txt_intro_B": txt_intro_B, "txt_finished": txt_finished}
