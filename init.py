import sys
sys.path.insert(0, '/Users/mathilde/Library/Python/3.10/lib/python/site-packages')

from psychopy import monitors

from pypixxlib.datapixx import DATAPixx3

# -------------------------- INITIALIZE VPIXX DEVICE --------------------------
def button_box(config):
    device = DATAPixx3()

    ## PIXEL MODE
    device.dout.enablePixelModeGB() # enable once
    device.updateRegisterCache() 

    ## BUTTONBOX
    # Initialize buttons
    button_info = config["buttons"]
    button_codes = button_info["buttonCodes"]
    button_codes = {int(k): v for k, v in button_codes.items()} #convert format of keys in dict (str -> int)

    exitButton  = button_info["exitButton"]

    myLog = device.din.setDinLog(12e6, 1000) # uses the first 8 DIN slots for buttonbox
    device.din.startDinLog()
    device.updateRegisterCache()

    return device, button_codes, myLog

## MONITOR
def stim_monitor(config):
        
    viewing_distance_cm = 40
    monitor_width_cm    = 28.7
    monitor_size_pix    = [1440, 900]
    monitor_name        = "Laptop"
    refresh_rate        = 60
    screen_number       = 0

    # Set Monitor
    monitor = monitors.Monitor(monitor_name) 
    monitor.setWidth(monitor_width_cm)  
    monitor.setDistance(viewing_distance_cm)  
    monitor.setSizePix(monitor_size_pix)
    monitor.save()


    # Set monitor and return information
    return {
        "monitor_size_pix":     monitor_size_pix,
        "monitor_name":         monitor_name,
        "refresh_rate":         refresh_rate,
        "viewing_distance_cm":  viewing_distance_cm,
        "monitor_width_cm":     monitor_width_cm,
        "screen_number":        screen_number
    }

