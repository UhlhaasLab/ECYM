""" written by Johanna Prugger.

- for now it sends triggers when correct response. can take out right? as i will have new button box code.

DARIO:
- updateReg cache use after trigger pres??? -> need to make it so, that it doesnt take up too much time with the update

end:
- check if trial seq is correct

"""

import random, csv, time, os
from psychopy import visual, core, event, sound

from ASSR.ASSR_init import (BASE_DIR, STIM_DIR, SOA, ARROW_DUR,
                        # triggers
                        TRIG_START, TRIG_END,
                        TRIG_SOUND_no_arr, TRIG_L_ARR, TRIG_R_ARR, 
                        # vpixx
                        # preload
                        preload_stimuli, preload_txt)

from utils.pixel_mode           import trigger_to_RGB, draw_pixel, print_trigger_info
from utils.buttonsNew           import read_button_press, flush_button_buffer, cleanup_and_exit, read_button_press_fast, enable_din_dout_passthrough_pixel_mode
from utils.escape_cleanup_abort import check_abort, cleanup


def run_ASSR(device, buttonCodes, myLog, monitor, MSR, SUB, CONDITION, SUB_DIR):
    # -------------------- GENERAL --------------------
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    psychopy_clock = core.Clock()

    # -------------------- WINDOW --------------------------------
    monitor_settings =  monitor

    win = visual.Window(
        monitor=monitor_settings['monitor_name'], size=monitor_settings['monitor_size_pix'], 
        fullscr=True, # set fullscr to True in MSR
        units="deg", 
        #color=[212, 212, 212],
        color= [160, 160, 160], # slightly darker gray to increase contrast with trigger pixel
        colorSpace='rgb255', 
        #colorSpace='rgb',
        #colorSpace='rgb1',
        screen=monitor_settings["screen_number"]
    )
    win.mouseVisible = False
    mouse = event.Mouse(visible=False)

    # number of frames = duration in sec * refresh rate in Hz (frames per second)
    monitor_rr = monitor_settings["refresh_rate"] # 120 in MSR.     60 on laptop
    frameDur = 1.0 / monitor_rr # 0.008333s, 8.33ms in MSR.     0.016666s, 16.67ms on laptop.       1 frame last 8.33ms, then next..
    TRIG_FRAMES = 2 # pixel should show for 2 frames, = 16.66ms in MSR, 33.32ms on laptop
    soa_frames = round(SOA / frameDur) # in MSR: round(1.5s / 0.008333) = 180 frames for one SOA.

    # -------------------- LOGGING SETUP --------------------
    log_file = os.path.join(SUB_DIR, f"{SUB}_{CONDITION}_log_{timestamp}.csv")
    log_f = open(log_file, "w", newline="", encoding="utf-8")
    log_writer = csv.writer(log_f)
    log_writer.writerow(["trial_index","arrow","sound_onset_psy","sound_onset_dev",
                        "arrow_onset_psy","arrow_onset_dev","response_key","rt_psy","rt_dev"])

    # -------------------- PRELOAD TEXT & STIMULI --------------------
    txt_dict = preload_txt(win)
    instr = txt_dict["txt_intro_PAS"] if CONDITION == "PAS" else txt_dict["txt_intro_ATT"]
    txt_finished = txt_dict["txt_finished"]

    stim = preload_stimuli(win, STIM_DIR, BASE_DIR, device, MSR, SUB, dB_SL=55) # adapt. check db_sl

    # audio
    audio_reg = stim["Audio"]
    # vis
    fix = stim["fix_dot"]
    arrow_stim = stim["arrow_stim"]

    # -------------------- LOAD TRIALS ------------------------
    def load_trials():
        master_sequence_file = os.path.join(SUB_DIR, f"{SUB}_ASSR_master_trial_sequence.csv")
        if not os.path.exists(master_sequence_file):
            raise FileNotFoundError(f"ERROR: Master sequence file not found for {SUB}!")
        with open(master_sequence_file, "r", encoding="utf-8") as f:
            trials = list(csv.DictReader(f))
        print(f"Successfully loaded {len(trials)} trials.")
        return trials

    trials = load_trials()
    trials = trials[:5]

    # ---------------- PRECOMPUTE ONCE ----------------
    arrow_frames = round(ARROW_DUR / frameDur)
    next_onset_frame = 0
    trial_specs = []

    for trial_data in trials:
        arrow_type = trial_data["arrow"]

        if arrow_type == "none":
            stim = fix
            trig = TRIG_SOUND_no_arr
        elif arrow_type == "left":
            trig = TRIG_L_ARR
            stim = ("arrow", 180)
        else:
            trig = TRIG_R_ARR
            stim = ("arrow", 0)

        trial_specs.append({
            "trial_index": trial_data["trial_index"],
            "arrow": arrow_type,
            "stim": stim,
            "trigger": trig
        })

    # -------------------- INSTRUCTIONS --------------------
    instr.draw()
    win.flip()
    device.updateRegisterCache()

    flush_button_buffer(device, myLog)
    while True:
        button, _ = read_button_press(device, myLog) # read VPixx buttonbox
        if button in ["red"]:
        #if event.getKeys(keyList=['r']): # for keyboard testing, psychopy
            break
        if check_abort(): 
            core.quit()
    
    # -------------------- COUNTDOWN --------------------
    for number in ["3", "2", "1"]:
        countdown_text = visual.TextStim(win, text=number, height=3, color='black')
        countdown_text.draw()
        win.flip()
        core.wait(1.0) # Show each number for 1 second
    print(f"Starting subject {SUB}, ASSR CONDITION {CONDITION}...")

    # -------------------- INITIAL FIXATION --------------------
    for f in range(TRIG_FRAMES):
        fix.draw()
        draw_pixel(win, trigger_to_RGB(TRIG_START))
        win.flip()

    # debug
    print(f"TRIG START ON {TRIG_START}, RGB: {trigger_to_RGB(TRIG_START)}")
    print_trigger_info(device)
    print("")

    for f in range(round(1.0 / frameDur) - TRIG_FRAMES):
        fix.draw()
        win.flip()

    # debug
    print(f"gray")
    print_trigger_info(device)
    print("")

    # -------------------- LOOP --------------------
    global_frame = 0
    # last_onset_dev = None # just for debug

    for trial in trial_specs:
        
        flip_marks = {}

        response_key = "NaN"
        rt_dev = "NaN"
        rt_psy = "NaN"
        response_collected = False

        flush_button_buffer(device, myLog)

        # ---------- wait until scheduled onset
        while global_frame < next_onset_frame:
            fix.draw()
            win.flip()
            global_frame += 1

        # ---------- onset timestamps
        sound_onset_dev = None
        sound_onset_psy = None
        arrow_onset_dev = None
        arrow_onset_psy = None
            
        infoaud_fb = audio_reg['clicktrain']
        device.audio.stopSchedule()
        device.audio.setAudioSchedule(0.0, infoaud_fb['fs'], infoaud_fb['n'], 'mono')
        device.audio.setVolume(infoaud_fb['gain']) # i had to add this here else i wouldn't hear it
        device.audio.setReadAddress(infoaud_fb['addr'])

        # ---------- trial frames
        for frameN in range(soa_frames):
            check_abort()
            
            if trial["arrow"] != "none":
                arrow_stim.ori = trial["stim"][1]
                if frameN < arrow_frames:
                    arrow_stim.draw()
                else:
                    fix.draw()
            else:
                fix.draw()
                
            # trigger
            if frameN < TRIG_FRAMES:
                draw_pixel(win, trigger_to_RGB(trial["trigger"]))

            # exact onset
            if frameN == 0:
                
                # win.callOnFlip(audio_reg.play) # psychopy
                
                win.callOnFlip(lambda: device.audio.startSchedule()) # audio for device, alternative syntax
                win.callOnFlip(lambda: device.updateRegisterCache()) # check with dario if this is needed
                # win.callOnFlip(lambda: device.updateRegCacheAfterVideoSync()) # make sure audio starts right after video sync
            
                win.callOnFlip(lambda: flip_marks.update({
                    "dev": device.getTime(),
                    "psy": psychopy_clock.getTime()
                }))
                
            win.flip()
            
            # # debug
            # if frameN == 2:
            #     print(f"")
            #     print_trigger_info(device)
            #     # debug done
            
            # # debug
            # if frameN == 3:
            #     print(f"")
            #     print_trigger_info(device)
            #     # debug done
            
            global_frame += 1
            
            # store onset
            if frameN == 0:
                
                sound_onset_dev = flip_marks["dev"]
                sound_onset_psy = flip_marks["psy"]
                
                if trial["arrow"] != "none":
                    arrow_onset_dev = sound_onset_dev
                    arrow_onset_psy = sound_onset_psy
                    
            # response
            if CONDITION == "ATT" and not response_collected:
                
                response = read_button_press(device, myLog)
                
                if response is not None:
                    device.updateRegisterCache()
                    
                    button_pressed, t_dev_pressed = response
                    t_psy_pressed = psychopy_clock.getTime()
                    
                    if button_pressed == "red":
                        
                        response_collected = True
                        
                        rt_dev = t_dev_pressed - sound_onset_dev
                        rt_psy = t_psy_pressed - sound_onset_psy
                        
                        if trial["arrow"] == "right":
                            response_key = "red"
                        elif trial["arrow"] == "left":
                            response_key = False
        
        next_onset_frame += soa_frames

        # ---------- log
        log_writer.writerow([
            trial["trial_index"],
            trial["arrow"],
            sound_onset_psy,
            sound_onset_dev,
            arrow_onset_psy,
            arrow_onset_dev,
            response_key,
            rt_psy,
            rt_dev
        ])
        log_f.flush()
        
        # # just for debug:
        # if last_onset_dev is not None:
        #     print(f"Trial {trial['trial_index']} SOA: {sound_onset_dev - last_onset_dev: .4f}s")
        # last_onset_dev = sound_onset_dev
        # # just for debug end
            
            
    # wait one soa
    for f in range(soa_frames):
        win.flip()

    # RUN END trigger (2 frames)
    for f in range(TRIG_FRAMES):
        draw_pixel(win, trigger_to_RGB(TRIG_END))
        win.flip()
    win.flip() # clear trig
    print(f"Condition {CONDITION} finished.")


    txt_finished.draw()
    win.flip()
    core.wait(3)

    win.close()