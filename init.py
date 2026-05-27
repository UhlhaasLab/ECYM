import sys
# sys.path.insert(0, '/Users/mathilde/Library/Python/3.10/lib/python/site-packages')
sys.path.insert(0, r"C:\Program Files\PsychoPy\Lib\site-packages")

from psychopy import monitors

from pypixxlib.datapixx import DATAPixx3

from utils.buttonsNew import enable_din_dout_passthrough_pixel_mode

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

    monitor_config = config["monitor"] 

    # Set Monitor
    monitor = monitors.Monitor(monitor_config["monitor_name"]) 
    monitor.setWidth(monitor_config["monitor_width_cm"])  
    monitor.setDistance(monitor_config["viewing_distance_cm"])  
    monitor.setSizePix(monitor_config["monitor_size_pix"])
    monitor.save()


    # Set monitor and return information 
    return monitor_config
