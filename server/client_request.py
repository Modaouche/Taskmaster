import sys
import copy
import threading
import time
import os
import signal

class ClientRequest():
    """ Client request for the server part"""

    INFO = "INFO"

    PROCESS = 0
    RUNNING = 2
    EXITED = 3
    EXITCODE = 4

    STATE = 7
    STOPPED = 2
    FATAL = 2
    PID = 8

    def __init__(self, processesHandler):
        """initialize attributes"""
        self.processesHandler = processesHandler
        self.communication = self.processesHandler.communication
        self.lock_commands = self.processesHandler.lock_commands
        self.lock_datas = self.processesHandler.lock_datas
        self.lock_commands.acquire()
        self.commands = self.processesHandler.commands
        self.lock_commands.release()
        self.communication = processesHandler.communication
        self.procs_state = []

    def __call__(self):
        """main part of our class"""
        self.lock_commands.acquire()
        if self.commands:
            print("commands:")
            print(self.commands)
            while self.commands:
                cmd = self.commands.pop()
                self.procs_state.clear()
                if cmd[0] == 'stop' or cmd[0] == 'restart':
                    self._stop_handler(cmd)
                if cmd[0] == 'start' or cmd[0] == 'restart':
                    self._start_handler(cmd)
                elif cmd[0] == 'status':
                    self._status_handler()
                elif cmd[0] == 'reload':
                    self._reload_handler()
                elif cmd[0] == 'shutdown':
                    self._shutdown_handler()

                self.lock_datas.acquire()
                if cmd[0] != 'status':
                    self.processesHandler.datas = self.procs_state
                if cmd[0] != 'reload':
                    self.processesHandler.datas_right = True
                self.lock_datas.release()

        self.lock_commands.release()

    def _compare_settings(self, settings, new_settings):
        """Compare a program settings with new settings from a reload."""
        for k1, v1 in settings.items():
            for k2, v2 in new_settings.items():
                if k1 == k2 and v1 != v2:
#                    print("A__-__--_--__----___-_--_-_-------_----___---_____--__---")
#                    print(v1)
#                    print(v2)
#                    print("A__-__--_--__----___-_--_-_-------_----___---_____--__---")
                    return True
        return False

    def _reload_handler(self):
        """Reload the configuration file"""
        self.processesHandler.taskmaster.config.parse()
        self.processesHandler._set_processes_arch()
        self._start_all()
       # print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")
       # print(self.processesHandler.programs)
       # print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^")

    def _set_signal(self, settings):
        """Set the appropriate signal according to the process settings"""
        if settings['stopsignal'] == "KILL":
            return signal.SIGKILL
        if settings['stopsignal'] == "QUIT":
            return signal.SIGQUIT
        if settings['stopsignal'] == "USR1":
            return signal.SIGUSR1
        if settings['stopsignal'] == "USR2":
            return signal.SIGUSR2
        if settings['stopsignal'] == "HUP":
            return signal.SIGHUP
        if settings['stopsignal'] == "INT":
            return signal.SIGINT
        return signal.SIGTERM

    def _program_exists(self, prog_name):
        """Check if the program name received exists"""
        keys = []
        programs = self.processesHandler.programs
        for program in programs:
            for k in program:
                if k != 'settings':
                    keys.append(k)
        if prog_name not in keys:
            return -1
        return 0

    def _process_exists(self, i, prog_name, proc_name):
        """Check if the process name received exists"""
        program = self.processesHandler.programs[i][prog_name]
        if proc_name not in program:
            return -1
        return 0

    def _stop_all(self):
        """Stop all processes form all programs."""
        i = 0
        while i < len(self.processesHandler.programs):
            program = self.processesHandler.programs[i]
            for k in program:
                if k != 'settings':
                    procs = program[k]
                    for name in procs:
                        if procs[name][self.PROCESS] is not None:
                            if procs[name][self.PROCESS].poll() is None:
                                if program['settings']['stopwaitsecs'] > 0:
                                    time.sleep(program['settings']['stopwaitsecs'])
                                if procs[name][self.PROCESS].poll() is None:
                                    os.kill(procs[name][self.PID], self._set_signal(program['settings']))
                                    os.waitpid(procs[name][self.PID], 0)
                                procs[name][self.PROCESS] = None
                                procs[name][self.STATE] = self.STOPPED
                                self.processesHandler._print_event(self.INFO, self.EXITED, name,
                                                  returncode=-1,
                                                  exitcode=procs[name][self.EXITCODE])
                                self.procs_state.append(k + ":" + name + " stopped")
                            else:
                                self.procs_state.append("ERROR")
            i += 1

    def _stop_program(self, prog_name):
        """Stop all processes form all programs."""
        i = 0
        if self._program_exists(prog_name) == -1:
            self.procs_state.append("NOT_FOUND")
            return -1
        while i < len(self.processesHandler.programs):
            program = self.processesHandler.programs[i]
            for k in program:
                if k != 'settings':
                    if k == prog_name:
                        procs = program[k]
                        for name in procs:
                            if procs[name][self.PROCESS] is not None:
                                if procs[name][self.PROCESS].poll() is None:
                                    if program['settings']['stopwaitsecs'] > 0:
                                        time.sleep(program['settings']['stopwaitsecs'])
                                    if procs[name][self.PROCESS].poll() is None:
                                        os.kill(procs[name][self.PID], self._set_signal(program['settings']))
                                        os.waitpid(procs[name][self.PID], 0)
                                    procs[name][self.PROCESS] = None
                                    procs[name][self.STATE] = self.STOPPED
                                    self.processesHandler._print_event(self.INFO, self.EXITED, name,
                                                                       returncode=-1,
                                                                       exitcode=procs[name][self.EXITCODE])
                                    self.procs_state.append(k + ":" + name + " stopped")
                                else:
                                    self.procs_state.append("ERROR")
            i += 1

    def _stop_process(self, prog_name, proc_name):
        """Stop all processes form all programs."""
        i = 0
        if self._program_exists(prog_name) == -1:
            self.procs_state.append("NOT_FOUND")
            return -1
        while i < len(self.processesHandler.programs):
            program = self.processesHandler.programs[i]
            for k in program:
                if k != 'settings':
                    if k == prog_name:
                        if self._process_exists(i, prog_name, proc_name) == -1:
                            self.procs_state.append("NOT_FOUND")
                            return -1
                        procs = program[k]
                        for name in procs:
                            if name == proc_name:
                                if procs[name][self.PROCESS] is not None:
                                    if procs[name][self.PROCESS].poll() is None:
                                        if program['settings']['stopwaitsecs'] > 0:
                                            time.sleep(program['settings']['stopwaitsecs'])
                                        if procs[name][self.PROCESS].poll() is None:
                                            os.kill(procs[name][self.PID], self._set_signal(program['settings']))
                                            os.waitpid(procs[name][self.PID], 0)
                                        procs[name][self.PROCESS] = None
                                        procs[name][self.STATE] = self.STOPPED
                                        self.processesHandler._print_event(self.INFO, self.EXITED, name,
                                                                           returncode=-1,
                                                                           exitcode=procs[name][self.EXITCODE])
                                        self.procs_state.append(k + ":" + name + " stopped")
                                    else:
                                        self.procs_state.append("ERROR")
            i += 1

    def _stop_handler(self, cmd):
        """Handle the stop of a specific program of process."""
        if len(cmd) == 1:
            return self._stop_all()
        elif len(cmd) == 2:
            splitted_cmd = cmd[1].split(':')
            if len(splitted_cmd) == 1:
                return self._stop_program(cmd[1])
            elif len(splitted_cmd) == 2:
                return self._stop_process(splitted_cmd[0], splitted_cmd[1])
            else:
                print("ERROR: Too much separators for the argument...", file=sys.stderr)

    def _reset_proc_settings(self, proc_settings, prog_settings):
        """Reset all the process settings"""
        proc_settings = [None, None, False, False, None, prog_settings['startsecs'], prog_settings['startretries'], -1, None, 0]
        return proc_settings

    def _start_all(self):
        """start every each program."""
        i = 0
        while i < len(self.processesHandler.programs):
            program = self.processesHandler.programs[i]
            for k in program:
                if k != 'settings':
                    procs = program[k]
                    for name in procs:
                        if procs[name][self.PROCESS] is None:
                            procs[name] = self._reset_proc_settings(procs[name], program['settings'])
                            ret = self.processesHandler._start_process(name, procs[name], program['settings'])
                            self.lock_datas.acquire()
                            if ret == 0:
                                self.procs_state.append(k + ":" + name + " started")
                            else:
                                self.procs_state.append("ERROR")
                            self.lock_datas.release()
            i += 1

    def _start_program(self, prog_name):
        """Start the program 'prog_name'"""
        i = 0
        found_flag = False
        while i < len(self.processesHandler.programs):
            program = self.processesHandler.programs[i]
            for k in program:
                if k != 'settings':
                    if k == prog_name:
                        found_flag = True
                        procs = program[k]
                        for name in procs:
                            if procs[name][self.PROCESS] is None:
                                procs[name] = self._reset_proc_settings(procs[name], program['settings'])
                                ret = self.processesHandler._start_process(name, procs[name], program['settings'])
                                if ret == 0:
                                    self.procs_state.append(k + ":" + name + " started")
                                else:
                                    self.procs_state.append("ERROR")
                        break
#            print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
#            print(self.procs_state)
#            print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
            i += 1
        if not found_flag:
            self.procs_state.append("NOT_FOUND")

    def _start_process(self, prog_name, proc_name):
        """Start the specific process 'proc_name'"""
        i = 0
        found_flag = False
        while i < len(self.processesHandler.programs):
            program = self.processesHandler.programs[i]
            for k in program:
                if k != 'settings':
                    if k == prog_name:
                        procs = program[k]
                        for k in procs:
                            if k == proc_name:
                                found_flag = True
                                if procs[proc_name][self.PROCESS] is None:
                                    procs[proc_name] = self._reset_proc_settings(procs[proc_name], program['settings'])
                                    ret = self.processesHandler._start_process(proc_name, procs[proc_name], program['settings'])
                                    if ret == 0:
                                        self.procs_state.append(k + ":" + proc_name + " started")
                                    else:
                                        self.procs_state.append("ERROR")
                                    break
            i += 1
        if not found_flag:
            self.procs_state.append("NOT_FOUND")
#        print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
#        print(self.procs_state)
#        print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")

    def _start_handler(self, cmd):
        """Handle the start of a specific program or process."""
        if len(cmd) == 1:
            return self._start_all()
        elif len(cmd) == 2:
            splitted_cmd = cmd[1].split(':')
            if len(splitted_cmd) == 1:
                return self._start_program(cmd[1])
            elif len(splitted_cmd) == 2:
                return self._start_process(splitted_cmd[0], splitted_cmd[1])
            else:
                print("ERROR: Too much separators for the argument...", file=sys.stderr)

    def _status_handler(self):
        """Fetch all the datas of every program"""
        self.lock_datas.acquire()
        self.processesHandler.datas = self.processesHandler.programs
        self.lock_datas.release()

    def _shutdown_handler(self):
        """Shutdown the taskmaster server"""
        self.lock_commands.release()
        self.communication.close()
        raise SystemExit(0)
