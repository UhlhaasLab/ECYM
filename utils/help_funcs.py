

def input_to_continue(paradigm_name, RUN, SUB):

    answer = ''
    while answer != SUB:
        if paradigm_name == "SEQ":
            answer = input(f"All sequence files are generated. Enter Sub ID. Then press Enter to continue.")
        else:
            answer = input(f"{paradigm_name} Run {RUN} done. Enter Sub ID. Then press Enter to continue.")


def should_skip(paradigms, paradigm_name, run, START_PARADIGM, START_RUN):

    idx = next(i for i, p in enumerate(paradigms) if p["name"] == START_PARADIGM)
    paradigms_to_skip = [p["name"] for p in paradigms[:idx]] 

    if paradigm_name in paradigms_to_skip:
        return True
    elif paradigm_name == START_PARADIGM:
        if run < START_RUN:
            return True
    else:
        return False
