

def input_to_continue(paradigm_name, RUN, SUB):

    answer = ''
    while answer != SUB:
        answer = input(f"{paradigm_name} Run {RUN} done. Enter the Sub ID. Then press Enter to continue.")
