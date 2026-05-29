import os, random, csv
import numpy as np
from psychopy import visual, sound
import soundfile as sf

from pathlib import Path

from utils.load import load_threshold_csv, assign_subject_gains, _load_wav_float32

# -------------------------- STIM PATH -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # script location
STIM_DIR = os.path.join(BASE_DIR, "MMN-stimuli")

MOVIE_RUN1  = os.path.join(STIM_DIR, "Pink_Panther_cartoon_1.mp4")
MOVIE_RUN2  = os.path.join(STIM_DIR, "Pink_Panther_cartoon_1.mp4") # -----------> ADAPT which movie? fur now just ppanther_1, should be _2
# Dictionary to map run number to movie file. This will be used in the preload function.
MOVIE_FOR_RUN = {1: MOVIE_RUN1, 2: MOVIE_RUN2}

# -------------------------- TRIGGERS (161-254) --------------------
# use trigger numbers below 255 so it stays only in the G channel
# and use trigger numbers above 160 so it actually goes UP. To make the signal go UP (to a higher voltage or a higher integer value in analysis), you must use numbers strictly greater than 160.
TRIG_RUN_START  = 162
TRIG_RUN_END    = 172

TRIG_STD        = 200
TRIG_DDEV       = 240

# ------------------- TRIAL STRUCTURE ----------------------------
SOA = 0.5 # stimulus onset asynchrony (time between sound onsets)

# -------------------------- GENERATE TRIAL SEQUENCE --------------------------
def create_participant_sequences(sub_dir, sub_id, current_run, group_id):
    """generates sequence for the specified run and saves it to a CSV. This function is run once per participant per run.
    
    Pseydorandomization logic:
        - Each run has 640 trials: 576 STDs and 64 DDEVs
        - The first 20 trials are always STDs
        - Every DDEV is preceded by at least 3 STDs.
    """
    sequence_file = os.path.join(sub_dir, f"{sub_id}_MMN_run{current_run}_trial_sequence.csv")
    
    # Check if file already exists to avoid overwriting
    if os.path.exists(sequence_file):
        print(f"INFO: Sequence file for {sub_id} and run {current_run} already exists. No action taken.")
        return

    print(f"GENERATING sequence file for subject {sub_id}, run {current_run}...")
    
    # Experiment Constants PER RUN
    TOTAL_TRIALS = 640
    DDEVS_PER = 64
    STDS_PER = TOTAL_TRIALS - DDEVS_PER # Should be 576
    INITIAL_STDS = 20
    MIN_STDS_BEFORE_DDEV = 3

    # === GENERATING SEQUENCE FOR CURRENT RUN === #

    # --- Step 1: Handle the fixed start of the sequence ---
    # The first 20 trials are always standards.
    initial_sequence = ["STD"] * INITIAL_STDS
        
    # --- Step 2: Calculate standards for the rest of the sequence ---
    # All 64 deviants will be placed in the remaining part of the trial list.
    # Each of these deviants requires a "buffer" of 3 standards immediately before it.
    stds_for_buffer = DDEVS_PER * MIN_STDS_BEFORE_DDEV # 64 * 3 = 192
    
    # Calculate the remaining standards that are "free" to be placed anywhere.
    stds_available_after_start = STDS_PER - INITIAL_STDS # 576 - 20 = 556
    free_stds_to_distribute = stds_available_after_start - stds_for_buffer # 556 - 192 = 364

    # --- Step 3: Distribute the "free" standards into slots ---
    # We have 65 possible slots to place these free standards:
    # one before the first deviant block, 63 between the blocks, and one after the last block.
    num_slots = DDEVS_PER + 1
    stds_in_slots = [0] * num_slots
    
    for _ in range(free_stds_to_distribute):
        # Add one standard to a randomly chosen slot
        random_slot = random.randint(0, num_slots - 1)
        stds_in_slots[random_slot] += 1
        
    # --- Step 4: Construct the randomized part of the sequence ---
    # Build the sequence by combining the free standards and the mandatory 'SSS D' blocks.
    #First add inital sequence of 20 Stds to final sequence
    final_sequence = initial_sequence
    mandatory_block = ["STD"] * MIN_STDS_BEFORE_DDEV + ["DDEV"]

    for i in range(DDEVS_PER):
        # Add the free standards for the slot before this deviant
        final_sequence.extend(["STD"] * stds_in_slots[i])
        # Add the mandatory block itself
        final_sequence.extend(mandatory_block)
        
    # Add the final slot of free standards at the very end
    final_sequence.extend(["STD"] * stds_in_slots[-1])

    # --- Sanity Checks (Crucial to ensure logic is correct) ---
    assert len(final_sequence) == TOTAL_TRIALS
    assert final_sequence.count("DDEV") == DDEVS_PER
    assert final_sequence.count("STD") == STDS_PER
    # Check that every DDEV is preceded by at least 3 STDs
    for i, stim in enumerate(final_sequence):
        if stim == "DDEV":
            # Ensure there's enough space before it and the preceding 3 are STDs
            assert i >= MIN_STDS_BEFORE_DDEV
            assert final_sequence[i-3:i] == ["STD", "STD", "STD"]

    # Convert the generated list into the dictionary format for the master CSV file, so that it cointains trial_index and stim_type for each trial
    rows = []
    for trial_index, stim_type in enumerate(final_sequence, start=1):
        rows.append({
            "trial_index": trial_index,
            "stim_type": stim_type
        })
    
    with open(sequence_file, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["trial_index", "stim_type"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"SUCCESS: Sequence file created at {sequence_file}")

# -------------------------- AUDIO SETTINGS --------------------------
FS = 48000 # audio sample rate. audio_sampling_frequency # chage to new one, 44000 i think

AUDIO_BASE_ADDR = int(16e6) # adress in vpixx device (where the audio gets stored)

## 1. LOAD AUDIO FILES AS FLOAT32 INTO VPixx AUDIO BUFFER
    
#  this actually loads them into buffer + creates registry for all samples 
def preload_tones(vpdevice, paths):
    # preload tones into buffer
    reg = {}
    vpdevice.audio.stopSchedule()

    # check length
    loaded          = {}
    total_samples   = 0
    common_fs       = None # assume same samling freq

    for name, p in paths.items():
        x, fs, peak = _load_wav_float32(p)
        x = np.asarray(x, dtype=np.float32).squeeze()
        
        if x.ndim != 1:
            raise ValueError(f"Tone '{name}' is not mono (shape {x.shape})")
            
        if common_fs is None:
            common_fs = fs
        elif fs != common_fs:
            raise ValueError(
                f"All tones must have same fs; '{name}' has {fs}, expected {common_fs}"
            )
            
        n_samples       = len(x)
        loaded[name]    = (x, fs, peak, n_samples)
        total_samples   += n_samples
        
    base_addr = AUDIO_BASE_ADDR # start address to be written
    buf_bytes = int(vpdevice.audio.getBufferSize())
    
    print(f"[AUDIO] base address (bytes): {base_addr}")
    print(f"[AUDIO] buffer size (bytes): {buf_bytes}")
    print(f"[AUDIO] total samples to write: {total_samples} -> {total_samples * 2} bytes")

    # build one big bank
    all_arrays = [loaded[name][0] for name in paths.keys()]
    audio_bank = np.concatenate(all_arrays).astype(np.float32)

    # writes at 16e6 internally; passing base_addr keeps intent consistent
    vpdevice.audio.writeAudioBuffer(audio_bank, bufferAddress=base_addr)
    vpdevice.updateRegisterCache()

    # offsets + registry
    offset_samples = 0
    for name in paths.keys():
        x, fs, peak, n_samples = loaded[name]
        
        addr_bytes = base_addr + offset_samples * 4
        
        reg[name] = {
            "addr": addr_bytes,
            "offset_samples": offset_samples,
            "n": n_samples,
            "fs": fs,
            "peak": peak,
            "gain": None,
        }
        
        print(
            f"[AUDIO] tone '{name}': addr={addr_bytes}, "
            f"n={n_samples}, offset_samples={offset_samples}"
        )
        
        offset_samples += n_samples
    return reg

# -------------------------- PRELOAD STIMULI AND TEXT ---------------
# Reserve a thin strip at the left edge so the trigger pixel is not covered by movie content.
movie_size_adjuster = 3 # eg 3 = make movie 1/3 of the screen size

def preload_stimuli(win, stimulipath, subjectpath, vpdevice, current_run, MSR, SUB):

    if MSR:
        # ======= AUDITORY
        # create tone registers
        audio_reg = preload_tones(vpdevice, {
           'std_sound':   os.path.join(stimulipath, 'sounds', 'STD_633Hz_50ms.wav'),
           'ddev_sound':  os.path.join(stimulipath, 'sounds', 'DDEV_1000Hz_100ms.wav')
        })

        # load threshold & add gains
        BASE_DIR_up = Path(BASE_DIR).parent
        csv_path  = os.path.join(BASE_DIR_up, "DATA", "HEARING THRESHOLD", SUB, "round_2_hearing_threshold_1000.csv")
        thr_info  = load_threshold_csv(csv_path)
        thr_lin   = thr_info["threshold_amplitude"]
        audio_reg = assign_subject_gains(audio_reg, threshold_linear=thr_lin, per_tone_dBSL={'std_sound': dB_SL, 'ddev_sound': dB_SL + 40})
        print(audio_reg)  

        # ======= VISUAL
        # Select the correct movie file based on the run number
        selected_movie_file = MOVIE_FOR_RUN[current_run]
        
        win_w, win_h = win.size  # in pixels
        movie = visual.MovieStim(
            win,
            selected_movie_file,
            loop=True,
            noAudio=True,
            size=(win_w/movie_size_adjuster, win_h/movie_size_adjuster),
            pos=(0,0),
            units='pix'
        )
    
    else:
        # ======= AUDITORY
        FS = 48000 
        HEARING_THRESHOLD = 0.0007
    
        DB_ABOVE_THRESHOLD = 60
        attenuation_factor = 10 ** (DB_ABOVE_THRESHOLD / 20)
        SOUND_VOLUME = HEARING_THRESHOLD * attenuation_factor
        SOUND_VOLUME = min(SOUND_VOLUME, 1.0)

        if SOUND_VOLUME > 1.0:
            print(f"WARNING: volume {SOUND_VOLUME:.2f} too high, capping at 1.0")
            SOUND_VOLUME = 1.0
        else:
            print(f"Sound volume set to {SOUND_VOLUME:.4f}")

        std_sound_file  = os.path.join(STIM_DIR, "sounds",  "STD_633Hz_50ms.wav")
        ddev_sound_file = os.path.join(STIM_DIR, "sounds", "DDEV_1000Hz_100ms.wav")

        audio_reg = {
           'std_sound':  sound.Sound(str(std_sound_file), sampleRate=FS, volume=SOUND_VOLUME),
           'ddev_sound': sound.Sound(str(ddev_sound_file), sampleRate=FS, volume=SOUND_VOLUME)
        }

        # ======= VISUAL
        # Select the correct movie file based on the run number
        selected_movie_file = MOVIE_FOR_RUN[current_run]
        
        win_w, win_h = win.size  # in pixels
        movie = visual.MovieStim(
            win,
            selected_movie_file,
            loop=True,
            noAudio=True,
            size=(win_w/movie_size_adjuster, win_h/movie_size_adjuster),
            pos=(0,0),
            units='pix'
        )

    return {"Audio": audio_reg, "movie": movie}


def preload_txt(win):
    txt_intro = visual.TextStim(win, text="Sie werden einen Film sehen.\n\n Bitte konzentrieren Sie sich auf den Film und ignorieren Sie die Töne.\n\n Drücken Sie einen beliebigen Knopf um zu starten.", height=1, pos=(0, 0), units='deg', color='black')
    txt_finished = visual.TextStim(win, text="Dieser Durchgang ist beendet.\n Vielen Dank. \n\n Bitte warten Sie auf Anweisungen.", height=1, pos=(0, 0), units='deg', color='black')
    return {"txt_intro": txt_intro, "txt_finished": txt_finished}


