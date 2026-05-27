""" TO DO


- adapt trigger sending for responses as we have new button code....?



not urgent:
- man angry face? wenn er die nase rümpft ist bissi verstellt. auch frau die erste isch awian verstellt
"""

import sys
sys.path.insert(0, '/Users/mathilde/Library/Python/3.10/lib/python/site-packages')



from psychopy import visual, core, event
import csv, time, os, random

from EMOTION.EMOTION_init import (# triggers
                         TRIG_START, TRIG_END, TRIG_RESP_right, TRIG_RESP_left, 
                         trigger_map,                     
                         # preload
                         preload_stimuli, preload_txt)

from utils.pixel_mode           import trigger_to_RGB, draw_pixel, print_trigger_info
from utils.buttons              import collect_response, flush_buttons
from utils.buttonsNew           import read_button_press, flush_button_buffer, cleanup_and_exit, read_button_press_fast
from utils.escape_cleanup_abort import check_abort, cleanup


def run_EMOTION(device, buttonCodes, myLog, monitor, MSR, SUB, RUN, GROUP, SUB_DIR):
    # -------------------- GENERAL --------------------
    timestamp = time.strftime('%Y%m%d_%H%M%S')
    psychopy_clock = core.Clock()
    rt_clock = core.Clock()

    # -------------------- WINDOW --------------------
    monitor_settings = monitor
    win = visual.Window(
        monitor=monitor_settings['monitor_name'], size=monitor_settings['monitor_size_pix'], 
        fullscr=MSR, 
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

    # -------------------- TIMING SETUP --------------------
    # for frame rate timing (frameDur = 1.0 / win.getActualFrameRate())
    monitor_rr = monitor_settings["refresh_rate"]
    frameDur = 1.0 / monitor_rr # if monitor_rr else win.monitorFramePeriod    # use actual refresh rate if available, otherwise fallback to PsychoPy's estimate

    TRIG_FRAMES = 2 # pixel should show for 2 frames

    """
    Face:            0 → 0.10 s
    Fixation:        0.10 → jittered 1.25 - 1.75    (+0.1 = 1.35-1.85 total)  before with 250ms face it was: 1.5-2, also durschnittlich 1.75
    Response window: 0.2 → 1.0 s
    """

    face_dur = 0.10  # before it was 0.250
    face_frames = int(round(face_dur / frameDur))

    resp_open_s  = 0.20 # also change?
    resp_close_s = 1.00

    # -------------------- LOGGING SETUP --------------------
    log_file = os.path.join(SUB_DIR, f"{SUB}_group-{GROUP}_run-{RUN}_data_{timestamp}.csv")
    log_f = open(log_file, "w", newline="", encoding="utf-8")
    log_writer = csv.writer(log_f)
    log_writer.writerow([
        "run", "trial_index", "face", "face_onset_psy", "face_onset_dev", 
        "correct_key", "response_key", "is_resp_corr",# "rt_psy", 
        "rt_dev"])

    # -------------------- PRELOAD TEXT & STIMULI --------------------
    txt_dict = preload_txt(win)
    txt_finished = txt_dict["txt_finished"]
    if GROUP == 'A': instr = txt_dict["txt_intro_A"]
    else: instr = txt_dict["txt_intro_B"] # GROUP 'B'

    stim = preload_stimuli(win) # preload_stim retungs stim_dict, which contains: "fixation", "WNA", "WSA", etc. as keys, and the corresponding ImageStim objects as values
    fix = stim["fixation"] # fixation loaded here, the facecs will be loaded in the trial loop based on the trial data

    # -------------------- TRIAL LOADING --------------------
    def load_run_trials():
        sequence_file = os.path.join(SUB_DIR, f"{SUB}_group-{GROUP}_run-{RUN}_EMO_trial_sequence.csv")

        if not os.path.exists(sequence_file):
            raise FileNotFoundError(
                f"\n\ERROR: Trial sequence file not found for participant {SUB}!\n"
                f"Please run the 'EMO_init.py' script first to generate it.\n"
                f"Expected file path: {sequence_file}\n"
            )

        with open(sequence_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            all_trials = list(reader)

        current_run_trials = [t for t in all_trials if int(t['run']) == RUN]
        
        if not current_run_trials:
            raise ValueError(f"Could not find any trials for RUN {RUN} in the sequence file.")
            
        print(f"Successfully loaded {len(current_run_trials)} trials for RUN {RUN}.")
        return current_run_trials

    trials = load_run_trials()
    trials = trials[:15] # adapt after testing

    # RESPONSE MAPPING
    if GROUP == 'A':
        correct_map = {'W': 'red', 'M': 'green'}
    else:
        correct_map = {'W': 'green', 'M': 'red'}

    # ============================================================================================
    # # -------------------- INSTRUCTIONS --------------------
    # instr.draw()
    # win.flip()
    # device.updateRegisterCache() # this needed here?

    # flush_buttons(device, myLog)
    # # ADAPT use new button code!!!!!!!!!!
    # while True:
    #     button, _ = collect_response(device, myLog, buttonCodes)
    #     # ADAPT use new button code!!!!!!!!!!
    #     if button in ["red", "green"]:
    #     #if event.getKeys(keyList=['r','g','b']): # for keyboard testing: wait for any key press to start
    #         break
    #     if check_abort():
    #         core.quit()  

    # # -------------------- COUNTDOWN --------------------
    # for number in ["3", "2", "1"]:
    #     countdown_text = visual.TextStim(win, text=number, height=3, color='black')
    #     countdown_text.draw()
    #     win.flip()
    #     core.wait(1.0) # Show each number for 1 second
    # print(f"Starting EMOTION Run {RUN}...")

    # # -------------------- INITIAL FIXATION --------------------
    # for f in range(TRIG_FRAMES):
    #     fix.draw()
    #     draw_pixel(win, trigger_to_RGB(TRIG_START))
    #     win.flip()

    # # debug
    # print(f"TRIG START ON {TRIG_START}, RGB: {trigger_to_RGB(TRIG_START)}")
    # print_trigger_info(device)
    # print("")

    # for f in range(round(1.0 / frameDur) - TRIG_FRAMES):
    #     fix.draw()
    #     win.flip()

    # # debug
    # print(f"gray")
    # print_trigger_info(device)
    # print("")

    # -------------------- MAIN LOOP --------------------
    # -------------------- START EXPERIMENT --------------------
    # 1. Capture the absolute hardware start time for the whole run
    exp_start_dev = device.getTime() 
    exp_start_psy = psychopy_clock.getTime()

    # Initial fixation
    fix.draw()
    win.flip()
    core.wait(0.5)

    # -------------------- MAIN TRIAL LOOP --------------------
    for i, trial_data in enumerate(trials):
        check_abort()

        # 1. Prepare Trial Data
        stim_face   = stim[trial_data["face"]]
        face_trig   = trigger_map[trial_data["face"]]
        correct_key = correct_map[trial_data["face"][0]]
        
        # 2. Timing Calculations
        jitter_fix_dur  = random.uniform(1.25, 1.75)
        total_trial_dur = face_dur + jitter_fix_dur # 1.35s to 1.85s
        total_frames = int(round(total_trial_dur / frameDur))
        
        # 3. Initialize Tracking
        response_key = None
        
        face_onset_dev = None
        rt_dev = -1
        is_resp_corr = 0

        flush_button_buffer(device, myLog)

        # Record exactly when this specific trial begins
        trial_start_dev = device.getTime()

        # -------------------- FRAME LOOP --------------------
        # The loop is primarily frame-based for drawing and triggers
        for frameN in range(total_frames):
            
            # --- CRITICAL: TIME-BASED CUT-OFF ---
            # If we hit the total duration, stop drawing and flip to the next trial
            if (device.getTime() - trial_start_dev) >= total_trial_dur:
                break

            # --- DRAWING ---
            if frameN < face_frames:
                stim_face.draw()
                if frameN < TRIG_FRAMES:
                    draw_pixel(win, trigger_to_RGB(face_trig))
            else:
                fix.draw()

            # --- FLIP ---
            win.flip()
            
            # --- CAPTURE ONSET (RELATIVE TO RUN START) ---
            if frameN == 0:
                # Absolute hardware time (for internal math)
                abs_onset_dev = device.getTime() 
                # Relative time for your log (e.g., Trial 1 starts at ~0.001)
                face_onset_dev = abs_onset_dev - exp_start_dev
                face_onset_psy = psychopy_clock.getTime() - exp_start_psy

            # --- RESPONSE WINDOW (0.2s - 1.0s) ---
            time_since_onset = device.getTime() - abs_onset_dev
            
            if resp_open_s <= time_since_onset <= resp_close_s:
                if response_key is None:
                    btn, t_hit = read_button_press(device, myLog)#, buttonCodes)
                    if btn:
                        response_key = btn
                        # RT is simply hit time minus onset time
                        rt_dev = t_hit - abs_onset_dev
                        is_resp_corr = 1 if response_key == correct_key else 0

        # -------------------- PRECISION TIMING GATE --------------------
        # This ensures the trial doesn't end early if the frames finished fast.
        # It forces the trial to last EXACTLY the jittered duration.
        while (device.getTime() - trial_start_dev) < total_trial_dur:
            pass # High-precision wait until the exact microsecond

        # -------------------- LOGGING --------------------
        # face_onset_dev will now be 0.0, 1.4, 3.1, etc. (Run-Relative)
        log_writer.writerow([
            RUN, i + 1, trial_data["face"], 
            face_onset_psy, face_onset_dev, 
            correct_key, response_key, is_resp_corr, 
            rt_dev # RT is correct because it's calculated using the hardware clock
        ])
        log_f.flush()





"""
    for i, trial_data in enumerate(trials):
        check_abort()

        # 1. Prepare Trial Data
        stim_face   = stim[trial_data["face"]]
        face_trig   = trigger_map[trial_data["face"]]
        correct_key = correct_map[trial_data["face"][0]]  # Maps 'W' or 'M' to 'red' or 'green'
        
        # 2. Timing Calculations
        jitter_fix_dur = random.uniform(1.25, 1.75)
        total_trial_dur = face_dur + jitter_fix_dur # This is 1.35s to 1.85s
        max_frames = int(round(total_trial_dur / frameDur))
        
        # 3. Initialize Trial Tracking
        response_key = None
        t_dev_pressed = None
        t_psy_pressed = None
        face_onset_psy = None
        face_onset_dev = None
        rt_psy = -1 # why -1?
        rt_dev = -1
        is_resp_corr = 0

        # Flush device buffer before trial starts
        flush_button_buffer(device, myLog)
        device.updateRegisterCache() 
        
        # -------------------- FRAME LOOP --------------------
        trial_start_time_dev = device.getTime()

        for frameN in range(max_frames):
            # --- TIME-BASED CUT-OFF ---
            # If the current hardware time exceeds our limit, kill the trial immediately
            current_time_dev = device.getTime()
            elapsed_trial_time = current_time_dev - trial_start_time_dev
            if elapsed_trial_time >= total_trial_dur:
                break # Exit the frame loop now!
            
            # --- DRAWING PHASE ---
            if frameN < face_frames:
                # 1. Face Presentation (100ms)
                stim_face.draw()
                
                # 2. Pixel Trigger (sent on the first 2 frames)
                if frameN < TRIG_FRAMES:
                    draw_pixel(win, trigger_to_RGB(face_trig))
            else:
                # 3. Fixation (remaining jittered time)
                fix.draw()

            # --- FLIP ---
            win.flip()
            
            # --- ONSET TIMING ---
            if frameN == 0:
                face_onset_psy = psychopy_clock.getTime()
                face_onset_dev = current_time_dev # The absolute start of Trial
            
            
            # --- RESPONSE WINDOW LOGIC (200ms - 1000ms) ---
            # time_since_onset = current_time_dev - face_onset_dev
            
            # if resp_open_s <= time_since_onset <= resp_close_s:
            #     if response_key is None:
            #         # Poll device for button press
            #         btn, t_hit = read_button_press(device, myLog) #, buttonCodes)
                    
            #         if btn:
            #             response_key = btn
            #             t_dev_pressed = t_hit # Absolute hardware time
            #             rt_dev = t_dev_pressed - face_onset_dev
                        
            #             # PsychoPy equivalent for logging
            #             t_psy_pressed = psychopy_clock.getTime()
            #             rt_psy = t_psy_pressed - face_onset_psy
                        
            #             is_resp_corr = 1 if response_key == correct_key else 0
                        

        # -------------------- LOGGING --------------------
        log_writer.writerow([
            RUN, 
            i + 1, 
            trial_data["face"], 
            face_onset_psy, 
            face_onset_dev, 
            correct_key, 
            response_key, 
            is_resp_corr, 
            rt_psy, 
            rt_dev
        ])
        log_f.flush() # Save to disk every trial
    """














"""
    global_frame = 0
    next_onset_frame = 0

    for trial_data in trials:
        check_abort()
            
        fix_dur = random.uniform(1.25, 1.75)
        fix_frames  = int(round(fix_dur / frameDur))
        total_frames = face_frames + fix_frames

        # vars
        response_key = None
        rt_dev, rt_psy = "NaN", "NaN" # default to 'NaN' if no response is made
        response_collected = False
        face_onset_dev, face_onset_psy = None, None

        # resp_trigger_value = None
        # trigger_frames_left = 0
        
        flip_marks = {} # Dictionary to store lambda results

        # prepare stimulus (face + trigger, and response)
        stim_face = stim[trial_data["face"]]
        face_trig = trigger_map[trial_data["face"]]
        correct_key = correct_map[trial_data["face"][0]]  # 'W' or 'M'

        # flush BEFORE trial starts
        flush_buttons(device, myLog) # does this take time?
        # ADAPT use new button code!!!!!!!!!!

        # ---------- wait until scheduled onset ----------
        while global_frame < next_onset_frame:
            fix.draw()
            win.flip()
            global_frame += 1

        # ============= FRAME LOOP =============
        # This inner loop draws every frame for one complete trial (face + fixation)    
        for frameN in range(total_frames):

            # ------ 1. DRAW --------
            if frameN < face_frames:
                stim_face.draw()
                # Draw the initial event trigger for the first few frames
                if frameN < TRIG_FRAMES:
                    draw_pixel(win, trigger_to_RGB(face_trig))

            else:
                fix.draw()

            # # If a response was made, overlay the response trigger
            # if trigger_frames_left > 0:
            #     draw_pixel(win, trigger_to_RGB(resp_trigger_value))
            #     trigger_frames_left -= 1


            # -------- 2. TIMESTAMP ON FIRST FLIP --------
            # On the very first frame, schedule the function to get the precise onset time
            if frameN == 0: 
                # device.updateRegisterCache() # attention does this need to be commented out?
                win.callOnFlip(lambda: flip_marks.update({
                        "t_face_dev": device.getTime(),
                        "t_face_psy": psychopy_clock.getTime()}))
                
            win.flip() # This is the only flip in the trial loop
            global_frame += 1

            # After the first flip, retrieve the timestamp for this trial's onset
            if frameN == 0: 
                face_onset_dev = flip_marks.get("t_face_dev") 
                face_onset_psy = flip_marks.get("t_face_psy")

            # # debug once, after pixel settling, to check trigger values:
            # if frameN == TRIG_FRAMES - 1:
            #     print(f"trig_to_send: {face_trig}, RGB: {trigger_to_RGB(face_trig)}")
            #     print_trigger_info(device)
            #     print("")

            # ----- safety: stop trial if timing exceeded -----
            if global_frame >= next_onset_frame + total_frames:
                break
                
                
            # -------- 3. RESPONSE COLLECTION --------
            # Only check if a response hasn't been collected and we have the onset time
            if face_onset_dev is not None and not response_collected:

                # should i call updateregcache here? yes else it does not update times of device, i get onlz nan
                device.updateRegisterCache()
                t_dev_now = device.getTime()

                # within response window (200–1000 ms)
                if face_onset_dev + resp_open_s <= t_dev_now <= face_onset_dev + resp_close_s:
            
                    button_pressed, t_dev_pressed = read_button_press(device, myLog, buttonCodes)
                    # ADAPT use new button code!!!!!!!!!!
                    t_psy_pressed = psychopy_clock.getTime()

                    if button_pressed is not None:
                        response_collected = True
                        response_key = button_pressed

                        rt_dev = t_dev_pressed - face_onset_dev
                        rt_psy = t_psy_pressed - face_onset_psy

                        # # assign response trigger
                        # # ADAPT: IS THIS NEEDED IF NEW BUTTON BOX TRIGGERING
                        # if response_key == "red":
                        #     resp_trigger_value = TRIG_RESP_right
                        #     trigger_frames_left = TRIG_FRAMES
                        # elif response_key == "green":
                        #     resp_trigger_value = TRIG_RESP_left
                        #     trigger_frames_left = TRIG_FRAMES

                        rt_psy = t_psy_pressed - face_onset_psy

        # ---------- next scheduled onset ----------
        next_onset_frame += total_frames

        # -------------------- LOG --------------------
        is_resp_corr = int(response_key == correct_key) if response_key is not None else 0

        log_writer.writerow([
            RUN,
            trial_data["trial_index"],
            trial_data["face"],
            face_onset_psy,
            face_onset_dev,
            correct_key,
            response_key if response_key is not None else "NaN",
            is_resp_corr,
            rt_psy,
            rt_dev
        ])
        log_f.flush()

    # -------------------- END SCREEN & CLEANUP ---------------------
    log_f.close()

    # wait one second
    for f in range(round(1.0 / frameDur)):
        win.flip()

    # RUN END trigger (2 frames)
    for f in range(TRIG_FRAMES):
        draw_pixel(win, trigger_to_RGB(TRIG_END))
        win.flip()
    win.flip() # clear trig
    print(f"Run {RUN} finished.")


    txt_finished.draw()
    win.flip()
    core.wait(3)

    
    # device.din.stopDinLog() # this in cleanup i think
    # cleanup(device, win)
    win.close()
    #core.quit()





"""