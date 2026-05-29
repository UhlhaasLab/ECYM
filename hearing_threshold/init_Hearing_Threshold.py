import os
import numpy as np
from psychopy import visual, sound

from utils.load import _load_wav_float32, load_threshold_csv, assign_subject_gains

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
    common_fs       = None

    for name, p in paths.items():
        x, fs, peak = _load_wav_float32(p)
        x = np.asarray(x, dtype=np.float32).squeeze() # Ensure it's 1D
        # x = np.asarray(x, dtype=np.float32).ravel() # chatgpt recommended this. dario?
        
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
        
    base_addr = AUDIO_BASE_ADDR  # start address to be written
    buf_bytes = int(vpdevice.audio.getBufferSize())
    
    print(f"[AUDIO] base address (bytes): {base_addr}")
    print(f"[AUDIO] buffer size (bytes): {buf_bytes}")
    print(f"[AUDIO] total samples to write: {total_samples} -> {total_samples * 2} bytes")

    # build one big bank
    all_arrays = [loaded[name][0] for name in paths.keys()]
    audio_bank = np.concatenate(all_arrays).astype(np.float32)

    # writes at 16e6 internally; passing base_addr keeps intent consistent
    vpdevice.audio.writeAudioBuffer(audio_bank, bufferAddress=base_addr)
    vpdevice.updateRegisterCache() # dario is this needed this update here? victoria said she doesnt need it

    # offsets + registry
    offset_samples = 0
    for name in paths.keys():
        x, fs, peak, n_samples = loaded[name]
        
        addr_bytes = base_addr + offset_samples * 2    # ADAPT  ?? * 4? i dont need the offset soo much (especially not for ASSR). but for MMN i have 2 tones, so i need to make sure they are stored at different addresses. if each sample is 4 bytes (float32), then the offset in bytes should be offset_samples * 4. but if vpixx expects the offset in samples, then it should just be offset_samples * 2 because vpixx might internally multiply by 2 to get byte address. i need to check this. for now i will assume that the offset in the registry is in samples, not bytes, so i will just put offset_samples here without multiplying by 2 or 4. but i will keep the base_addr in bytes when writing to the buffer, because that is what vpixx expects.
        
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

# --------------------------PRELOAD STIMULI AND TEXT ---------------
# dB_SL=60 or 65 or 50
def preload_stimuli(win, stimulipath, subjectpath, vpdevice, MSR, dB_SL):
    fixation_angle = 1 # 0.5 # 0.5 looks good, maybe a bit too small? ----> ADAPT

    if MSR:
        # ======= AUDITORY
        # create tone registers
        audio_reg = preload_tones(vpdevice, {
           'clicktrain': os.path.join(stimulipath, 'clicktrain_40Hz_500ms.wav')
        })

        # load threshold & add gains
        thr_info  = load_threshold_csv(os.path.join(subjectpath, "round_2_hearing_threshold_1000.csv"))
        thr_lin   = thr_info["threshold_amplitude"]
        audio_reg = assign_subject_gains(audio_reg, threshold_linear=thr_lin, per_tone_dBSL={'clicktrain': dB_SL})  # ADAPTED FROM this/darios: ={'Aud_X': dB_SL, 'Aud_Y': dB_SL, 'Aud_FB': dB_SL-10})
        print(audio_reg)        

        # ======= VISUAL
        fix_dot = visual.Circle(win, radius=fixation_angle/2, fillColor="black", lineColor="black", pos=(0, 0), units="deg")
        arrow_vertices = [(-0.5, 0.8), (0.5, 0.0), (-0.5, -0.8)]
        arrow_stim = visual.ShapeStim(win, vertices=arrow_vertices, closeShape=True, fillColor="black", lineColor="black")

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

        clicktrain_file = os.path.join(stimulipath, "clicktrain_40Hz_500ms.wav")
        Audio = sound.Sound(str(clicktrain_file), sampleRate=FS, volume=SOUND_VOLUME)

        # ======= VISUAL
        fix_dot = visual.Circle(win, radius=fixation_angle/2, fillColor="black", lineColor="black", pos=(0, 0), units="deg")
        arrow_vertices = [(-0.5, 0.8), (0.5, 0.0), (-0.5, -0.8)]
        arrow_stim = visual.ShapeStim(win, vertices=arrow_vertices, closeShape=True, fillColor="black", lineColor="black")
        
    return {"Audio": Audio, "fix_dot": fix_dot, "arrow_stim": arrow_stim}
