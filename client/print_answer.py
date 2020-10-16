import time

class Print_answer():
    """ A class which print answers"""

    def __init__(self):
        """ Initialize attibute for the Parser """


    def __call__(self, to_print):
        """Part of code which parse sort/organize answers and dump them properly""" 

        if type(to_print) is list:
            for val in to_print:
                if type(val) is str:
                    proc_stat = val.split(' ')
                    if len(proc_stat) == 2:
                        print(f"{proc_stat[0]} {proc_stat[1]}")

                    else:
                        if proc_stat[0] == 'NOT_FOUND':
                            print("Server error: process not found.")
                        elif proc_stat[0] == 'ERROR':
                            print("Server error: the process could not be started.")
                        else:
                            print(f"{proc_stat[0]}")

        elif type(to_print) is dict:
            prog_name = ''
            for key, val in to_print.items():
                if val == None:
                    prog_name = key
                    continue
                if prog_name != '':
                    print(f"{prog_name}:{key:20} ", end='')
                else:
                    print(f"{key:20} ", end='')

                if len(val) == 9:
                    if val[6] == -1:
                        print(f"STARTING")

                    elif val[6] == 0:
                        print(f"{'RUNNING'.ljust(10)}pid {val[7]}, uptime ", end='')
                        print(f"{time.strftime('%H:%M:%S', time.gmtime(time.time() - val[0]))}")
                    elif val[6] == 1:
                        print(f"{'EXITED'.ljust(10)}", end='')

                    elif val[6] == 2:
                        print(f"{'STOPPED'.ljust(10)}", end='')

                    elif val[6] == 3:
                        print(f"{'FATAL'.ljust(10)}Process log may have details")

                    elif val[6] == 4:
                        b_off = True
                        print(f"{'BACKOFF'.ljust(10)} Exited too quickly")

                    if val[6] == 1 or val[6] == 2:
                        print(f"{time.strftime('%b %d %I:%M %p', time.localtime(val[0]))}")

                else:
                    print(f"{'ERROR'.ljust(10)}Process not launched, launch it with 'start {key}'")

        else:
            if type(to_print) == bytes:
                print(to_print.decode("utf-8"))
            else:
                print(to_print)
