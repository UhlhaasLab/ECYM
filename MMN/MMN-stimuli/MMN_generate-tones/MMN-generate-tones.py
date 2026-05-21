"""Generates:
    Standard tone: 633 Hz, 50 ms
    Double-deviant tone: 1000 Hz, 100 ms
Applies 5 ms cosine-squared rise and fall ramps
Uses a standard 44.1 kHz sampling rate
Saves tones as WAV files
Normalizes amplitude to avoid clipping


parameters taken from AMP SCZ:
https://www.nature.com/articles/s41537-025-00622-0#Sec9
which states "In the MMN paradigm, auditory stimuli consisted of 90% standard tones (633 Hz, 50 ms duration) and 10% pitch+duration “double-deviant” tones (1000 Hz, 100 ms duration) presented in a pseudorandom sequence. Tones were presented with 5 ms rise and fall times and a 500 ms stimulus onset asynchrony (SOA). A total of 3200 tones were presented over 5 separate runs, with each run starting with 20 standards to facilitate participant’s initial formation of a memory trace for the standard and the corresponding expectation that standards would recur."
"""

import numpy as np
from scipy.io.wavfile import write
from pathlib import Path
import os

############# 
fs = 48000  # sampling rate (Hz)
# dario: I think the device accept values from 8k to 96k. For the purpose of the assr, i think you could use 44.1 or 48k that should not matter as both are more than sufficient. I think what is critical is that you select correctly the sampling rate based on how you created your file
#############





# outdir should be in the same folder as this script
out_dir = Path(__file__)

ramp_duration = 0.005  # 5 ms rise/fall

# WHAT TO MAKE? Tone definitions
tones = {
    "STD_633Hz_50ms.wav": {
        "frequency": 633,
        "duration": 0.050
    },
    "DDEV_1000Hz_100ms.wav": {
        "frequency": 1000,
        "duration": 0.100
    }
}


# HELPER GENERATE IT! a tone with cosine-squared ramps
def generate_tone(freq, duration, fs, ramp_duration):
    t = np.linspace(0, duration, int(fs * duration), endpoint=False)
    tone = np.sin(2 * np.pi * freq * t)

    # Create cosine-squared ramp
    ramp_samples = int(fs * ramp_duration)
    ramp = np.sin(np.linspace(0, np.pi / 2, ramp_samples)) ** 2

    envelope = np.ones_like(tone)
    envelope[:ramp_samples] = ramp
    envelope[-ramp_samples:] = ramp[::-1]

    tone *= envelope

    # Normalize
    tone /= np.max(np.abs(tone))
    return tone


# CREATE AND SAVE
for filename, params in tones.items():
    tone = generate_tone(
        freq=params["frequency"],
        duration=params["duration"],
        fs=fs,
        ramp_duration=ramp_duration
    ) 

    write(filename, fs, tone.astype(np.float32))
    print(f"Saved {filename} in location: {os.path.abspath(filename)}")
