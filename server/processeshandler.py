"""A module which handle processes by launching them and fetch info."""

import os
import sys
import copy
import time
import subprocess
import threading
from datetime import datetime
from subprocess import TimeoutExpired
from server_socket import Communication_S
from program import Program
from client_request import ClientRequest


class ProcessesHandler():
    """A class which contains information about processes."""

    INFO = "INFO"
    ERROR = "ERROR"
    CRIT = "CRIT"
    WARN = "WARN"

    SPAWNED = "spawned"
    SUCCESS = "success"
    EXITED = "exited"
    GAVE_UP = "gave up"

    CMDNOTFOUND = "can't find command "
    PERMISSIONDENIED = "PERMISSIONDENIED"
    SPAWNERR = "spawnerr"

    RUNNING = "RUNNING"
    RESTARTING = "restarting"
    AUTORESTART = "autorestart"

    UNEXPECTED = True

    PROCESS = 0
    OPTIONS = 1

    PROCESS = 0         # subprocess object
    TIMESTAMP = 1       # timestamp of the process
    RUNNING = 2         # Process running ? True : False
    EXITED = 3          # Process exited ? True : False
    EXITCODE = 4        # Exitcodes expected for the process
    STARTSECS = 5       # If the process is still running  after STARTSECS, then it enter into RUNNING state
    STARTRETRIES = 6    # Number of times we can restart the process
    STATE = 7
    PID = 8
    FATAL = 3
    BACKOFF = 4
    FAIL = 9

    STDOUT = "out"
    STDERR = "err"

    def __init__(self, taskmaster):
        """Initialize attributes for processes handler"""
        self.taskmaster = taskmaster
        self.progs_conf = taskmaster.config.programs
#        print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
#        print(taskmaster.config.programs)
#        print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
#        time.sleep(50)
        self.datas = []
        self.datas_right = False
        self.commands = []
        self.programs = []
        self.lock_commands = threading.Lock()
        self.lock_datas = threading.Lock()
        self.communication = Communication_S(self)
        self.client_request = ClientRequest(self)
        self.umask = None
        self.procs_timestamp = {}
        self.lock_reload = threading.Lock()

    def run(self):
        """launch every processes inside the dictionary 'programs'."""
        self.umask = self.taskmaster.config.umask
        self._set_processes_arch()
#        print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
#        print(self.progs_conf)
#        print("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
        self._launcher()
        
        t = threading.Thread(target=self.communication)
        t.start()
        while True:
            self.lock_reload.acquire()
            self.client_request()
            self._check_programs_state()
            self.lock_reload.release()

    def _check_programs_state(self):
        """Browse each program to probe them processes."""
        i = 0
        while i < len(self.programs):
            self._probe_program_processes(self.programs[i])
            i += 1

    def _probe_program_processes(self, program):
        """Get information whether the processes are running or not."""
        for k in program.keys():
            if k != 'settings':
                procs = program[k]
                # print(procs)
                for n in procs.keys():
                    self._check_proc_state(n, procs[n], program['settings'])

    def _check_proc_state(self, name, proc_settings, prog_settings):
        """Verify if the process is running or not."""
        proc = proc_settings[self.PROCESS]
        if proc is not None:
            deltatime = time.time() - proc_settings[self.TIMESTAMP]

            if (proc.poll() is None \
                and not proc_settings[self.RUNNING] \
                and deltatime >= proc_settings[self.STARTSECS]) \
                    or (not proc_settings[self.RUNNING] and proc_settings[self.STARTSECS] == 0):
                proc_settings[self.RUNNING] = True
                proc_settings[self.STATE] = 0
                self._print_event(self.INFO, self.RUNNING, name, startsecs=proc_settings[self.STARTSECS])

            elif proc.poll() is not None and proc_settings[self.RUNNING]:
#                print("B--__-_--__--_--______--___---_--_--_----_--------__")
#                print(proc)
#                print("******************************************************")
#                print(proc_settings)
#                print("******************************************************")
#                print(proc_settings[self.PROCESS])
#                print("B--__-_--__--_--______--___---_--_--_----_--------__")
                self._print_event(self.INFO, self.EXITED, name, returncode=proc.returncode,
                                  exitcode=proc_settings[self.EXITCODE])
                proc_settings[self.PROCESS] = None
                proc_settings[self.RUNNING] = False
                proc_settings[self.EXITED] = True
                proc_settings[self.STATE] = 1

                if prog_settings['autorestart'] == 'unexpected' and prog_settings['exitcodes'] != proc.returncode \
                        or prog_settings['autorestart'] == True:
                    self._start_process(name, proc_settings, prog_settings)

            elif proc.poll() is not None and not proc_settings[self.RUNNING]:
                alive = None
                if not proc_settings[self.RUNNING]:
                    alive = False
                if proc_settings[self.PROCESS] is not None:
                    self._print_event(self.INFO, self.EXITED, name, returncode=proc.returncode,
                                  exitcode=proc_settings[self.EXITCODE], alive=alive)

                proc_settings[self.PROCESS] = None
                proc_settings[self.EXITED] = True
                proc_settings[self.STATE] = 1
                if proc_settings[self.STARTRETRIES] > 0:
                    proc_settings[self.STATE] = self.BACKOFF
                    proc_settings[self.STARTRETRIES] -= 1
                    time.sleep(0.1)
                    self._start_process(name, proc_settings, prog_settings)
                elif not proc_settings[self.RUNNING]:
                    proc_settings[self.STATE] = self.FATAL
                    self._print_event(self.INFO, self.GAVE_UP, name)
        elif proc is None and proc_settings[self.FAIL] == -1:
            if proc_settings[self.STARTRETRIES] > 0:
                proc_settings[self.STATE] = self.BACKOFF
                proc_settings[self.STARTRETRIES] -= 1
                time.sleep(0.1)
                self._start_process(name, proc_settings, prog_settings)
            elif proc_settings[self.STARTRETRIES] == 0:
                proc_settings[self.STARTRETRIES] -= 1
                proc_settings[self.STATE] = self.FATAL
                self._print_event(self.INFO, self.GAVE_UP, name)

    def _print_event(self, target, event, name, startsecs=None, pid=None, returncode=0, exitcode=None, alive=None):
        """Display when a new event occurs."""
        print(datetime.strftime(datetime.now(), "%Y-%m-%d %I:%M:%S, "), end='')
        if target == self.INFO:
            print("INFO ", end='')
            if event == self.SPAWNED:
                print("spawned: "
                      f"'{name}' with pid {pid}")
            elif event == self.RUNNING:
                print("success: "
                      f"{name} entered RUNNING state, "
                      f"process has stayed up for > than {startsecs} seconds (startsecs)")
            elif event == self.EXITED:
                print("exited: "
                      f"{name} (exit status {returncode}, ", end='')
                if returncode != exitcode or alive == False:
                    print("not expected)")
                else:
                    print("expected)")
            elif event == self.GAVE_UP:
                print("gave up: "
                      f"{name} entered FATAL state, too many start retries too quickly")
            elif event == self.CMDNOTFOUND:
                print("spawnerr: can't find command " f"'{name}'")
            elif event == self.SPAWNERR:
                print("spawnerr: unknown error making dispatchers for " f"'{name}'")
        elif target == self.CRIT:
            print("CRIT ", end='')
            if event == self.PERMISSIONDENIED:
                print("permission denied: "
                      f"'{name}'")

    def _fetch_progam_names(self):
        """Fetch program names of the data structure."""
        i = 0
        prog_names = []
        for i in range(len(self.programs)):
            for k in self.programs[i].keys():
                if k != 'settings':
                    prog_names.append(k)
        return prog_names

    def _set_processes_arch(self):
        """Build the data structure and architecture for the processes."""
        prog_names = self._fetch_progam_names()
        for prog_name, settings in self.progs_conf.items():
            if prog_name not in prog_names:
                program = Program(prog_name, settings)
                self.programs.append(program.program)
            else:
                for i in range(len(self.programs)):
                    if prog_name in self.programs[i].keys():
                        ret = self.client_request._compare_settings(self.programs[i]['settings'], settings)
                        if ret is True:
                            self.client_request._stop_program(prog_name)
                            program = Program(prog_name, settings)
                            self.programs[i] = program.program
                        continue

    def _launcher(self):
        """Launch all program's processes with autostart == True."""
        i = 0
        if self.umask is not None:
            os.umask(self.umask)
        while i < len(self.programs):
            program = self.programs[i]
            i += 1
            if program['settings']['autostart']:
                for k in program:
                    if k != 'settings':
                        procs = program[k]
                        for name in procs:
                            self._start_process(name, procs[name], program['settings'])

    def _open_stream(self, filename):
        """Create a log file and return the stream associated."""
        # print(self.umask)
        try:
            # print(filename)
            f = open(filename, 'w')
        except PermissionError:
            return -1
        except FileNotFoundError:
            return -2
        except IOError as e:
            return -3
        else:
            return f

    def _popen_options_handler(self, proc_name, prog_settings):
        """Prepare all the options before the popen call."""
        settings = {}
        settings['env'] = os.environ.copy()
        if prog_settings['env']:
            settings['env'].update(prog_settings['env'])
        settings['command'] = prog_settings['command'].split()
        if prog_settings['stdout_logfile'] == 'AUTO':
            settings['stdout_logfile'] = self._open_stream(proc_name + self.STDOUT)
        elif prog_settings['stdout_logfile'] == None:
            settings['stdout_logfile'] = subprocess.PIPE
        else:
            settings['stdout_logfile'] = self._open_stream(prog_settings['stdout_logfile'])

        if prog_settings['stderr_logfile'] == 'AUTO':
            settings['stderr_logfile'] = self._open_stream(proc_name + self.STDERR)
        elif prog_settings['stderr_logfile'] == None:
            settings['stderr_logfile'] = subprocess.PIPE
        else:
            settings['stderr_logfile'] = self._open_stream(prog_settings['stderr_logfile'])

        if prog_settings['directory'] is not None:
            settings['directory'] = prog_settings['directory']
        else:
            settings['directory'] = None
        settings['umask'] = None
        if prog_settings['umask'] is not None:
            settings['umask'] = prog_settings['umask']
        return settings

    def _start_process(self, proc_name, proc_settings, prog_settings):
        """Start a process using subprocess module."""
        settings = self._popen_options_handler(proc_name, prog_settings)
        #        if settings['stdout_logfile'] < 0 or settings['stderr_logfile'] < 0:
        #            return 0
        saved_umask = os.umask(0)
        if settings['umask']:
            os.umask(settings['umask'])
        try:
            proc = subprocess.Popen(
                settings['command'],
                stdin= -1,
                stdout=settings['stdout_logfile'],
                stderr=settings['stderr_logfile'],
                cwd=settings['directory'],
                env=settings['env'],
            )
            proc_settings[self.PID] = proc.pid
        except FileNotFoundError as e:
            proc_settings[self.PROCESS] = None
            proc_settings[self.FAIL] = -1
            self._print_event(self.INFO, self.CMDNOTFOUND, settings['command'][0])
            return -1
        except PermissionError as e:
            proc_settings[self.PROCESS] = None
            proc_settings[self.FAIL] = -1
            self._print_event(self.CRIT, self.PERMISSIONDENIED, settings['directory'])
            return -1
        except OSError as e:
            proc_settings[self.FAIL] = -1
            print(f"CRIT {e}")
            return -1
        else:
            if ((settings['stdout_logfile'] is int and settings['stdout_logfile'] < 0) and settings['stdout_logfile'] != subprocess.PIPE) \
                    or (settings['stderr_logfile'] is int and settings['stderr_logfile'] < 0) and settings['stderr_logfile'] != subprocess.PIPE:
                proc_settings[self.PROCESS] = None
                proc_settings[self.FAIL] = -1
                self._print_event(self.INFO, self.SPAWNERR, proc_name)
                return -1
            else:
                self._print_event(self.INFO, self.SPAWNED, proc_name, pid=proc.pid)
                proc_settings[self.PROCESS] = proc
                proc_settings[self.TIMESTAMP] = time.time()
                proc_settings[self.PID] = proc.pid
                proc_settings[self.STATE] = -1
                proc_settings[self.EXITCODE] = prog_settings['exitcodes']
        os.umask(saved_umask)
        return 0

    def _check_processes(self):
        """check the status of the processes."""
        for prog_name, (proc, options) in self.procs.items():
            if not options['running']:
                if self._try_running(prog_name, proc, options) == -1:
                    self._try_restart(prog_name, proc, options)

    #            elif options['running']:
    #                if self._process_exited(prog_name, options):
    #                     self._restart_process(prog_name)

    def _try_running(self, prog_name, proc, options):
        """
        Set the the process to a running state
        if and only if the diff between now and
        the 'process timestamp' > startsecs
        """
        self.startsecs = options['startsecs']
        self.deltatime = time.time() - options['timestamp']
        if self.deltatime >= self.startsecs and not self.procs[prog_name][self.OPTIONS]['exited']:
            options['running'] = True
            print(self.procs[prog_name][self.OPTIONS]['running'])
            options['startretries'] = 0
            self._print_status(self.INFO, self.SUCCESS, prog_name, True)
            return 0
        return -1

    def _try_restart(self, prog_name, proc, options):
        """Try to restart the process."""
        if self.deltatime > self.startsecs and not options['running']:
            if self.programs[prog_name]['startretries'] > options['startretries']:
                #                print("-----")
                #                print(options['startretries'])
                #                print("-----")
                self._print_status(self.INFO, self.EXITED, prog_name, True)
                self._restart_process(prog_name)
                self.procs[prog_name][self.OPTIONS]['startretries'] += 1
                print(self.procs[prog_name][self.OPTIONS]['startretries'])
            elif not options['gave_up']:
                options['gave_up'] = True
                self._print_status(self.INFO, self.EXITED, prog_name, True)
                self._print_status(self.INFO, self.GAVE_UP, prog_name)
                # del self.procs[prog_name]

    #    def _process_exited(self, prog_name, options):
    #        """
    #        Either autorestart == unexpected and exitcodes != process.returncode,
    #        or autorestart == True, then it allows by returning > 0 to restart the
    #        process.
    #        """
    #        proc = self.procs[prog_name][self.PROCESS]
    #        if proc.poll() is not None:
    #            if not options['exited']:
    #                self.procs[prog_name][self.OPTIONS]['exited'] = True
    #                self._print_status(self.INFO, self.EXITED, prog_name)
    #            if options['autorestart'] == True \
    #            or (options['autorestart'] == 'unexpected' \
    #            and options['exitcodes'] != proc.returncode):
    #                return 1
    #        return 0

    def _print_status(self, type_msg, status, prog_name, poll=None):
        """Display the current state of a process."""
        if type_msg == self.INFO:
            print("INFO ", end='')
            if status == self.SPAWNED:
                print(f"{self.SPAWNED}: '{prog_name}' "
                      f"with pid {self.procs[prog_name][self.PROCESS].pid}")
            elif status == self.SUCCESS:
                print(f"{self.SUCCESS}: {prog_name} "
                      f"entered {self.RUNNING} state, "
                      "process has stayed up for > than "
                      f"{self.programs[prog_name]['startsecs']} "
                      "seconds (startsecs)")
            elif status == self.EXITED:
                print(f"{self.EXITED}: {prog_name} "
                      f"(exit status {self.procs[prog_name][self.PROCESS].returncode}; ", end='')
                exitcode = self.procs[prog_name][self.PROCESS].returncode
                if exitcode != self.programs[prog_name]['exitcodes'] or poll:
                    print("not expected)")
                else:
                    print("expected)")
            elif status == self.GAVE_UP:
                print(f"{self.GAVE_UP}: {prog_name} "
                      "entered FATAL state, too many start retries too quickly")
