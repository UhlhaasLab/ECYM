# VPIXX utils to collect responses
def collect_response(vpdevice, myLog_collect, buttonCodes):
    # Collect responses. Ignore if not red/green
    vpdevice.updateRegisterCache()
    vpdevice.din.getDinLogStatus(myLog_collect)
    newEvents = myLog_collect["newLogFrames"]
    # Check events
    if newEvents > 0:
        eventList = vpdevice.din.readDinLog(myLog_collect, newEvents)
        for t_event, code in eventList:
            # Check if code is known and corresponds to red/green only
            if code in buttonCodes:
                buttonID = buttonCodes[code]
                if buttonID not in ("red", "green"):
                    # Ignore any button that's not red or green
                    continue
                print(f"Button pressed: {buttonID.upper()}")
                return buttonID, t_event
    return None, None


def flush_vpixx_events(vpdevice, myLog_collect):
    # clear responses
    while True:
        vpdevice.updateRegisterCache()
        vpdevice.din.getDinLogStatus(myLog_collect)
        n = myLog_collect.get("newLogFrames", 0)
        if not n:
            break
        vpdevice.din.readDinLog(myLog_collect, n)


