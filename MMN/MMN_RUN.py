""" Passive auditory MMN with visual distraction

TO DO
- 2 simple comprehension questions after the run
- change video!

- maybe make 1 audio sequence and just send this at the beginning, then use the whole sequence in 1 file. (its te exacte same thing then for 1 run)
    maybe also for ASSR??

"""

from psychopy import visual, core, event
import csv, time, os

from MMN.MMN_init import (STIM_DIR, SOA,
                        # triggers
                        TRIG_STD, TRIG_DDEV, 
                        TRIG_RUN_START, TRIG_RUN_END,
                        # preload
                        preload_stimuli, preload_txt)

from utils.pixel_mode           import trigger_to_RGB, draw_pixel
from utils.buttons              import collect_response, flush_buttons
from utils.escape_cleanup_abort import check_abort, cleanup


def run_MMN(device, buttonCodes, myLog, monitor, MSR, SUB, RUN, SUB_DIR):
    # -------------------- GENERAL --------------------
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    psychopy_clock = core.Clock()

    # -------------------- WINDOW --------------------
    monitor_settings = monitor
    # set fullscr to True in MSR
    win = visual.Window(
        monitor=monitor_settings['monitor_name'], size=monitor_settings['monitor_size_pix'], 
        fullscr=False, 
        units="deg", 
        color= [160, 160, 160], # slightly darker gray to increase contrast with trigger pixel
        colorSpace='rgb255', 
        screen=monitor_settings["screen_number"]
    )
    win.mouseVisible = False
    mouse = event.Mouse(visible=False)



    # number of frames = duration in sec * refresh rate in Hz (frames per second)
    monitor_rr = monitor_settings["refresh_rate"] # 120 in MSR.     60 on laptop
    frameDur = 1.0 / monitor_rr     # 0.008333s, 8.33ms in MSR.     0.016666s, 16.67ms on laptop.       1 frame last 8.33ms, then next..
    TRIG_FRAMES = 2 # pixel should show for 2 frames, = 16.66ms in MSR, 33.32ms on laptop
    soa_frames = round(SOA / frameDur) # in MSR: round(1.5s / 0.008333) = 180 frames for one SOA.

    # -------------------- LOGGING SETUP --------------------
    log_file = os.path.join(SUB_DIR, f"{SUB}_run-{RUN}_data_{timestamp}.csv")
    log_f = open(log_file, "w", newline="", encoding="utf-8")
    log_writer = csv.writer(log_f)
    log_writer.writerow([
        "run", "trial_index", "sound",
        "sound_onset_dev", "sound_onset_psy"])

    # -------------------- PRELOAD TEXT & STIMULI --------------------
    txt = preload_txt(win)
    instr = txt["txt_intro"]
    txt_finished = txt["txt_finished"]

    stim = preload_stimuli(win, STIM_DIR, SUB_DIR, device, current_run=RUN, MSR=MSR, SUB=SUB, dB_SL=35)
    # audio
    audio_reg = stim["Audio"]
    # visual 
    movie = stim["movie"]

    # -------------------- LOAD TRIALS --------------------
    def load_trials():
        sequence_file = os.path.join(SUB_DIR, f"{SUB}_MMN_run{RUN}_trial_sequence.csv")
        if not os.path.exists(sequence_file):
            raise FileNotFoundError(f"ERROR: Sequence file not found for {SUB}!")
        with open(sequence_file, "r", encoding="utf-8") as f:
            all_trials = list(csv.DictReader(f))

        if not all_trials:
            raise ValueError(f"Could not find any trials in sequence file for RUN {RUN}.")

        print(f"Successfully loaded {len(all_trials)} trials (should be 640) for RUN {RUN}.")
        return all_trials

    trials = load_trials()
    #!!!!!!!!!! only ten trials for testing, has to be removed for the whole paradigm !!!!!!!!!!
    trials = trials[:5]

    # ============================================================================================
    # # -------------------- INSTRUCTIONS --------------------
    instr.draw()
    win.flip()
    device.updateRegisterCache()

    flush_buttons(device, myLog)
    while True:
        button, _ = collect_response(device, myLog, buttonCodes)
        if button in ["red", "green"]:
        #if event.getKeys(keyList=['r','g','b']): # for keyboard testing: wait for any key press to start
            break
        if check_abort():
            core.quit()

    # -------------------- COUNTDOWN --------------------
    for number in ["3", "2", "1"]:
        countdown_text = visual.TextStim(win, text=number, height=3, color='black')
        countdown_text.draw()
        win.flip()
        core.wait(1.0) # Show each number for 1 second
    print(f"Starting MMN RUN {RUN}...")

    # -------------------- START MOVIE --------------------
    movie.setAutoDraw(True) # adapt ----------------------------> turn on
    movie.play()

    for f in range(TRIG_FRAMES):
        draw_pixel(win, trigger_to_RGB(TRIG_RUN_START))
        win.flip()

    # # debug
    # print(f"TRIG START ON {TRIG_RUN_START}, RGB: {trigger_to_RGB(TRIG_RUN_START)}")
    # print_trigger_info(device)
    # print("")

    win.flip() # Movie continues + Trigger cleared

    # play movie for 5 sec then start loop 
    for _ in range(round(5.0 / frameDur)):
        win.flip()

    # -------------------- MAIN LOOP --------------------
    frameN = 0
    trial_idx = 0 # initialize trial index (for the first sound)
    next_trial_frame = soa_frames

    sound_onset_dev = None
    sound_onset_psy = None

    flip_marks = {}

    while trial_idx < len(trials):
        check_abort()

        # ---------- check for correct time to present sound ----------
        if frameN == next_trial_frame:
            stim_info = trials[trial_idx]
            stim_type = stim_info['stim_type']
            if stim_type == "STD":
                current_trig = TRIG_STD
                sound_to_play = audio_reg['std_sound']
            else:
                current_trig = TRIG_DDEV
                sound_to_play = audio_reg['ddev_sound']

            flip_marks = {}

            # ---- SOUND + TRIGGER ----
            for trig_frame in range(TRIG_FRAMES): # shown for frame 0, and 1 (2 frames in total)
                # frame 0 => sound + trigger
                # frame 1 => just trigger pixel (to make sure trigger is visible for at least 2 frames, in case of any timing issues)
                if trig_frame == 0: # audio will only play at frame==0, but pixel will show for TRIG_FRAMES
                    if MSR:
                        # AUDIO VPIXX  -----------> ADAPT!!!!!!!!!!! make wihtout "if"?
                        # prepare audio, not execute yet. it gets executed at win.flip() below
                        infoaud_fb = sound_to_play # here we only have 1 std and 1 ddev sound. thus audio_reg['std_sound'] = std_sound, audio_reg['ddev_sound'] = ddev_sound.
                        
                        device.audio.stopSchedule()
                        device.audio.setAudioSchedule(0.0, infoaud_fb['fs'], infoaud_fb['n'], 'mono')
                        device.audio.setReadAddress(infoaud_fb['addr'])
                        device.audio.startSchedule()
                        device.updateRegCacheAfterVideoSync() # attention does this need to be commented out?

                        win.callOnFlip(lambda: flip_marks.update({"time_psy": psychopy_clock.getTime()}))
                        win.callOnFlip(lambda: flip_marks.update({"time_dev": device.getTime()}))
                        
                    else:
                        win.callOnFlip(sound_to_play.play)
                        win.callOnFlip(lambda: flip_marks.update({"time_psy": psychopy_clock.getTime()}))
                        device.updateRegisterCache() # make sure to update register cache after video sync, so that the timing is accurate. this is important for the audio trigger timing, because the audio gets scheduled at win.flip() below, which is the same time as the trigger pixel presentation. thus we want to make sure that the device register cache is updated at the same time, so that the audio trigger timing is accurate.
                        win.callOnFlip(lambda: flip_marks.update({"time_dev": device.getTime()}))
                        
                draw_pixel(win, trigger_to_RGB(current_trig))

                win.flip()

                sound_onset_dev = flip_marks.get("time_dev")
                sound_onset_psy = flip_marks.get("time_psy")

                # # debug only once per trial
                # if trig_frame == TRIG_FRAMES - 1: # -1 is needed here because trig_frame starts at 0. so if TRIG_FRAMES=2, we want to print debug info at trig_frame=1, which is the last frame of the trigger presentation.
                #     print(f"current_trig {current_trig}, RGB: {trigger_to_RGB(current_trig)}")
                #     print_trigger_info(device)
                #     print("")

            # clear trigger
            win.flip()

            # # debug gray
            # print(f"gray")
            # print_trigger_info(device)
            # print("")

            # -------- LOG ONCE PER TRIAL --------
            log_writer.writerow([
                RUN,
                trial_idx,
                stim_type,
                sound_onset_dev,
                sound_onset_psy
            ])
            log_f.flush()

            trial_idx += 1
            next_trial_frame += soa_frames  # schedule next sound

        else:
            # keep movie running
            win.flip()

        frameN += 1

    # -------------------- FINISH ---------------------
    # close csv log file
    log_f.close()

    # wait exactly one SOA
    for f in range(soa_frames):
        win.flip()

    # RUN END trigger (2 frames)
    for f in range(TRIG_FRAMES):
        draw_pixel(win, trigger_to_RGB(TRIG_RUN_END))
        win.flip()

    # clear trigger
    win.flip()

    print(f"Run {RUN} finished.")

    # Stop movie, show finished message, and clean up
    movie.stop()
    movie.setAutoDraw(False)
    txt_finished.draw()
    win.flip()
    core.wait(3)

    win.close()
