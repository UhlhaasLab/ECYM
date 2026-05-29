import csv
import os

import numpy as np
import soundfile as sf

#  needed for preload_tones one below (load .wav files as float32 as vpixx audio buffer expects that. also convert to mono if needed, and get the peak value for later gain calculations)
def _load_wav_float32(audiofilespath):
    # Load .wav tone files
    audiofile, samplingfreq = sf.read(audiofilespath, dtype='float32')
    if audiofile.ndim > 1:  # convert to mono if needed
        audiofile = audiofile.mean(axis=1).astype('float32')
    # create array
    audiofile = np.ascontiguousarray(audiofile, dtype=np.float32)
    peak = float(np.max(np.abs(audiofile))) or 1.0 # get max value

    return audiofile, int(samplingfreq), peak

## MAKES VOLUME SAME FOR EACH PARTICIPANT
#  just loads csv
def load_threshold_csv(subjectpath):
    # Load Subject-Specific Hearing Threshold 
    with open(subjectpath, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=',')
        row = next(reader)
    return {
        "subject_id": row["SUB"],
        "threshold_db": float(row["threshold_db"]),
        "threshold_amplitude": float(row["threshold_amplitude"]),
        }

#  then adds gains to regsitry
def assign_subject_gains(in_audio_reg, threshold_linear, per_tone_dBSL, master=1.0):
    # include gain in the register
    for name, info in in_audio_reg.items():
        peak            = info.get('peak', 1.0)
        this_dBSL       = per_tone_dBSL.get(name)
        
        if this_dBSL is None:
            raise ValueError(f"No dBSL defined for tone '{name}'")
            
        if peak is None:
            raise ValueError("peak is None – audio not loaded or computed correctly")
            
        gain            = master * threshold_linear * (10.0 ** (this_dBSL / 20.0)) / max(peak, 1e-12)
        info['gain']    = float(max(0.0, min(1.0, gain)))  # clamp to [0,1]
    return in_audio_reg

def load_trials(paradigm_name, SUB_DIR, SUB, RUN):
        sequence_file = os.path.join(SUB_DIR, f"{SUB}_{paradigm_name}_run{RUN}_trial_sequence.csv")
        if not os.path.exists(sequence_file):
            raise FileNotFoundError(f"ERROR: Sequence file not found for {SUB}!")
        with open(sequence_file, "r", encoding="utf-8") as f:
            all_trials = list(csv.DictReader(f))
 
        if not all_trials:
            raise ValueError(f"Could not find any trials in sequence file for RUN {RUN}.")

        print(f"Successfully loaded {len(all_trials)} trials (should be 640) for RUN {RUN}.")
        return all_trials