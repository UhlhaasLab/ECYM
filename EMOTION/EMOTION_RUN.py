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
from utils.buttonsNew           import flush_button_buffer, cleanup_and_exit, read_button_press, read_button_press_fast, enable_din_dout_passthrough_pixel_mode
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
    Fixation:        0.10 → jittered 1.25 - 1.75
    Response window: 0.2 → 1.0 s
    """

    face_dur = 0.100  # before it was 0.250
    face_frames = int(round(face_dur / frameDur))

    resp_open_s  = 0.200 # also change?
    resp_close_s = 1.000

    # -------------------- LOGGING SETUP --------------------
    log_file = os.path.join(SUB_DIR, f"{SUB}_group-{GROUP}_run-{RUN}_data_{timestamp}.csv")
    log_f = open(log_file, "w", newline="", encoding="utf-8")
    log_writer = csv.writer(log_f)
    log_writer.writerow([
        "run", "trial_index", "face", "face_onset_psy", "face_onset_dev", 
        "correct_key", "response_key", "is_resp_corr", "rt_psy", "rt_dev"])

    # -------------------- PRELOAD TEXT & STIMULI --------------------
    txt_dict = preload_txt(win)
    txt_finished = txt_dict["txt_finished"]
    if GROUP == 'A': instr = txt_dict["txt_intro_A"]
    else: instr = txt_dict["txt_intro_B"] # GROUP 'B'

    stim = preload_stimuli(win) # preload_stim retungs stim_dict, which contains: "fixation", "WNA", "WSA", etc. as keys, and the corresponding ImageStim objects as values
    fix = stim["fixation"] # fixation loaded here, the facecs will be loaded in the trial loop based on the trial data

    # -------------------- TRIAL LOADING --------------------
    def load_run_trials():
        """
        Loads trials for the current run from the master sequence CSV.
        Exits with an error if the master file is not found.
        """
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
    #!!!!!!!!!! only ten trials for testing, has to be removed for the whole paradigm !!!!!!!!!!
    #trials = trials[:20]

    # RESPONSE MAPPING
    if GROUP == 'A':
        correct_map = {'W': 'red', 'M': 'green'}
    else:
        correct_map = {'W': 'green', 'M': 'red'}

    # ============================================================================================
    # -------------------- INSTRUCTIONS --------------------
    instr.draw()
    win.flip()
    # device.updateRegisterCache() # this needed here?
    flush_buttons(device, myLog)
    # ADAPT use new button code?
    while True:
        button, _ = collect_response(device, myLog, buttonCodes)
        # ADAPT use new button code?
        if button in ["red", "green"]:
        #if event.getKeys(keyList=['r','g','b']): # for keyboard testing: wait for any key press to start
            break
        if check_abort():
            core.quit()  
            
    
    enable_din_dout_passthrough_pixel_mode()
    
    # -------------------- COUNTDOWN --------------------
    for number in ["3", "2", "1"]:
        countdown_text = visual.TextStim(win, text=number, height=3, color='black')
        countdown_text.draw()
        win.flip()
        core.wait(1.0) # Show each number for 1 second
    print(f"Starting EMOTION Run {RUN}...")

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

    # -------------------- MAIN LOOP --------------------
    for trial_data in trials:
        check_abort()
            
        fix_dur = random.uniform(1.25, 1.75)              
        fix_frames  = int(round(fix_dur / frameDur))
        total_frames = face_frames + fix_frames

        # initialize variables
        response_key = None
        rt_dev, rt_psy = "NaN", "NaN"
        response_collected = False

        face_onset_dev, face_onset_psy = None, None

        resp_trigger_value = None
        trigger_frames_left = 0
        
        flip_marks = {} # Dictionary to store lambda results

        # prepare stimulus (face + trigger, and response)
        stim_face = stim[trial_data["face"]]
        face_trig = trigger_map[trial_data["face"]]
        correct_key = correct_map[trial_data["face"][0]]  # 'W' or 'M'

        # flush BEFORE frame trial starts
        flush_button_buffer(device, myLog) 
        # ADAPT use new button code?

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

            # If a response was made, overlay the response trigger
            # if trigger_frames_left > 0:
                # draw_pixel(win, trigger_to_RGB(resp_trigger_value))
                # trigger_frames_left -= 1


            # -------- 2. TIMESTAMP ON FIRST FLIP --------
            # On the very first frame, schedule the function to get the precise onset time
            if frameN == 0: 
                # device.updateRegisterCache() # attention does this need to be commented out?
                win.callOnFlip(lambda: flip_marks.update({
                        "t_face_dev": device.getTime(),
                        "t_face_psy": psychopy_clock.getTime()}))

            win.flip() # This is the only flip in the trial loop

            # After the first flip, retrieve the timestamp for this trial's onset
            if frameN == 0:
                face_onset_dev = flip_marks.get("t_face_dev")
                face_onset_psy = flip_marks.get("t_face_psy")

            # # debug once, after pixel settling, to check trigger values:
            # if frameN == TRIG_FRAMES - 1:
            #     print(f"trig_to_send: {face_trig}, RGB: {trigger_to_RGB(face_trig)}")
            #     print_trigger_info(device)
            #     print("")
                
   
            # -------- 3. RESPONSE COLLECTION --------
            # Only check if a response hasn't been collected and we have the onset time
            if face_onset_dev is not None and not response_collected:
                
                # should i call updateregcache here? yes else it does not update times of device, i get onlz nan. but this takes time, we wanted to take it out of the button boxes
                device.updateRegisterCache()
                t_dev_now = device.getTime()
                
                # within response window (200–1000 ms)
                if face_onset_dev + resp_open_s <= t_dev_now <= face_onset_dev + resp_close_s:
                    
                    button_pressed, t_dev_pressed = read_button_press_fast(device, myLog, buttonCodes)
                    # ADAPT use new button code!!!!!!!!!!
                    t_psy_pressed = psychopy_clock.getTime()
                    
                    if button_pressed is not None:
                        response_collected = True
                        response_key = button_pressed
                        
                        rt_dev = t_dev_pressed - face_onset_dev
                        rt_psy = t_psy_pressed - face_onset_psy
                        
                        
                        """
                        # assign response trigger
                        # ADAPT: THIS  not NEEDED IF NEW BUTTON BOX TRIGGERING
                        if response_key == "red":
                            resp_trigger_value = TRIG_RESP_right
                            trigger_frames_left = TRIG_FRAMES
                        elif response_key == "green":
                            resp_trigger_value = TRIG_RESP_left
                            trigger_frames_left = TRIG_FRAMES
                        """


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