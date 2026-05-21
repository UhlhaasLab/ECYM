from psychopy import event, core

from psychopy import event, core

def escape_check(vpdevice=None, currentwindow=None):
    if event.getKeys(['escape']):
        print("Experiment terminated by user (ESC).")

        # --- Handle VPixx device if present ---
        if vpdevice is not None:
            # Stop DIN logging if running
            try:
                if hasattr(vpdevice, "din"):
                    vpdevice.din.stopDinLog()
            except Exception:
                pass  # ignore errors if not started / not available

            # Make sure registers are updated and device closed
            try:
                vpdevice.updateRegisterCache()
            except Exception:
                pass
            try:
                vpdevice.close()
            except Exception:
                pass

        # --- Close PsychoPy window and quit ---
        try:
            if currentwindow is not None:
                currentwindow.close()
        except Exception:
            pass

        core.quit()

