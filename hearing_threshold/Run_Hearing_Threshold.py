import sys
import soundfile as sf
import csv
import argparse
import os
import numpy as np
from psychopy import visual, event, core

from pathlib import Path

from hearing.utils_general import escape_check
from hearing.utils_response import collect_response, flush_vpixx_events

from init_Hearing_Threshold import (_load_wav_float32, device, buttonCodes, myLog, stim_monitor)



audio_sampling_frequency    = 44100 # from darios script

subject_id  = 'TEST_05.12'
# --- CLI args ---
#parser = argparse.ArgumentParser(description="Measure hearing threshold with an adaptive staircase.")
#parser.add_argument("subject_id", help="Subject identifier, e.g. pkm07")
#args = parser.parse_args()
#subject_id = args.subject_id




# --------- Setup folders
script_folder = os.path.dirname(os.path.abspath(__file__))

# data folder
ECYM_folder = Path(script_folder).parent
subject_folder  = os.path.join(ECYM_folder, "DATA", "hearing_threshold_DATA", subject_id)
os.makedirs(subject_folder, exist_ok=True) # make the folder if doesn't exist already

# Load test tone 1kHz
sound_dir = os.path.join(script_folder, "tone")
test_tone, tone_fs, peak_amp   = _load_wav_float32(os.path.join(sound_dir, 'tone_1000Hz.wav'))





# Create window
win = visual.Window([800, 600], fullscr=True, color="black", units="pix", screen=2)   

# Initialize window to deliver instructions/text  
msg = visual.TextStim(win, text="", height=50, color="white", units="pix")



# Parameters for threshold measurement
THRESH_tone_initial_db          = -40
THRESH_tone_max_db              = 0
THRESH_step_schedule            = [20, 10, 2]
THRESH_switch_after_reversals   = [2, 3]
THRESH_total_reversals          = 8
THRESH_avg_reversals            = 6

# Starting address to preload Tone 
TEST_TONE_ADDR = int(16e6)
# Write audio into Datapixx 
device.audio.writeAudioBuffer(test_tone, bufferAddress=TEST_TONE_ADDR)
device.updateRegisterCache()

# Store metadata for later playback
test_tone_sound = {
    "addr": TEST_TONE_ADDR,
    "fs":   tone_fs,           # e.g. audio_sampling_frequency
    "n":    len(test_tone),
    "gain": 0.0,               # or whatever linear gain you want
}

# Run Experiment
# Clear events
event.clearEvents() 
for rounds in range(2):

    # initialize run
    current_step_index      = 0
    step_db                 = THRESH_step_schedule[current_step_index]
    amp_db                  = THRESH_tone_initial_db

    if rounds == 0:
        # Present instructions for first round
        msg.text = (
            "Sie werden Töne hören.\n"
            "Drücken Sie die linke Taste (GRÜN), wenn Sie diese hören, oder die rechte Taste (ROT) wenn nicht.\n\n"
            "Um zu beginnen, drücken Sie eine beliebige Taste.")
        msg.draw()
    else:
        # Present instructions for second round
        msg.text = (
            "Lass uns das noch einmal machen. Sie werden Töne hören.\n"
            "Drücken Sie die linke Taste (GRÜN), wenn Sie diese hören, oder die rechte Taste (ROT) wenn nicht.\n\n"
            "Um zu beginnen, drücken Sie eine beliebige Taste.")
        msg.draw()
    win.flip()

    # Wait until a key is pressed to start
    key_pressed = None
    while key_pressed is None:
        key_pressed, t_event = collect_response(device, myLog, buttonCodes)
        core.wait(0.01)

    # Initialize staircase
    reversals       = []
    reversal_count  = 0
    last_direction  = None

    amp_db = THRESH_tone_initial_db
    current_step_index = 0
    step_db = THRESH_step_schedule[current_step_index]

    while reversal_count < THRESH_total_reversals:
        # Make a pause before presenting the next tone
        if current_step_index > 0:
            core.wait(0.3)
        # Convert dB to linear amplitude (0–1)
        amp_linear = 10**(amp_db / 20.0)
        amp_linear_clamped = max(0.0, min(0.99, amp_linear))

        device.audio.stopSchedule()
        device.audio.setAudioSchedule(0.0, test_tone_sound['fs'], test_tone_sound['n'], 'mono')
        device.audio.setVolume(amp_linear_clamped)
        device.audio.setReadAddress(test_tone_sound['addr'])

        print("[DEVICE] audio buffer size (samples):", device.audio.getBufferSize())
        print("[PLAY]  addr in dict:", test_tone_sound["addr"])
        print("[PLAY]  getReadAddress():", device.audio.getReadAddress())
        print("[PLAY]  n scheduled:", test_tone_sound["n"])

        device.audio.startSchedule()
        device.updateRegCacheAfterVideoSync()   # tone starts on this flip

        # Present text / tone (stubbed)
        msg.text = "Töne"
        msg.draw()
        win.flip()
        core.wait(0.5 + 0.3)

        # Response window
        msg.text = "Haben Sie die Töne gehört? (GRÜN = Ja, ROT = Nein)"
        msg.draw()
        win.flip()

        # Allow to quit experiment by pressing ESC
        escape_check(device, win)

        # Collect response 
        key_pressed = None
        while key_pressed is None:
            # Allow to quit experiment by pressing ESC
            escape_check(device, win)
            key_pressed, t_event = collect_response(device, myLog, buttonCodes)
            core.wait(0.01)

        # Clear button presses after response
        core.wait(0.01)
        flush_vpixx_events(device, myLog)
        
        
        # Did they hear it?
        heard = int(key_pressed.upper() == "GREEN")

        # Current trial level (for logging reversals)
        stim_level_db = amp_db

        # Direction on this trial
        new_direction = "down" if heard else "up"

        # Check for reversal BEFORE updating amp_db
        if last_direction is not None and new_direction != last_direction:
            reversals.append(stim_level_db)
            reversal_count += 1
            print(f"Reversal {reversal_count} at {stim_level_db:.1f} dB")

            if current_step_index < len(THRESH_switch_after_reversals) and \
               reversal_count == THRESH_switch_after_reversals[current_step_index]:
                current_step_index += 1
                step_db = THRESH_step_schedule[current_step_index]
                print(f"Switching to step size: {step_db} dB")

        # Update level for next trial
        if heard:
            amp_db -= step_db
        else:
            amp_db = min(amp_db + step_db, THRESH_tone_max_db)
        last_direction = new_direction

    # Estimate threshold 
    if len(reversals) > THRESH_avg_reversals:
        threshold_db = float(np.mean(reversals[-THRESH_avg_reversals:]))
        threshold_linear = 10**(threshold_db / 20)
        result = (
            f"Threshold estimate:\n"
            f"{threshold_db:.1f} dB (re: max = 1.0)\n"
            f"Linear amplitude: {threshold_linear:.5f}\n"
            f"Use amplitude = {10**((threshold_db + 70)/20):.5f} for 70 dB SL"
        )
    else:
        threshold_db = None
        result = "Threshold not reliably reached."

    # Display and save
    print(result)
    msg.text = "Drücken Sie eine belibige Taste, um weiterzumachen"
    msg.draw(); win.flip()
    key_pressed = None
    while key_pressed is None:
        key_pressed, t_event = collect_response(device, myLog, buttonCodes)
        core.wait(0.01)

    # Clear button presses after response is detected
    core.wait(0.01)              
    flush_vpixx_events(device, myLog)   

    # Store values as .csv
    if threshold_db is not None:
        out_path = os.path.join(subject_folder, 'round_' + str(rounds + 1) + '_hearing_threshold_1000.csv')
        with open(out_path, "w", newline='', encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["subject_id", "threshold_db", "threshold_amplitude"])
            writer.writerow([subject_id, f"{threshold_db:.2f}", f"{threshold_linear:.5f}"])
    print('Threshold: ', threshold_db)
    
# Close
device.close()
win.close()
core.quit()
