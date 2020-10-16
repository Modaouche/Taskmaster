"""A module which assemble a program with its settings."""

import time

class Program():
    """Make a dictionary package of a program with its settings."""

    def __init__(self, prog_name, settings):
        """Initialize some attributes to fetch program and settings."""
        self.prog_name = prog_name
        self.settings = settings
        self.program = {}
        self.processes = self._build()

    def _build(self):
        """Organize program and settings into a dictionary."""
#        print(type(self.settings.copy()))
#        print("----------")
        self.program['settings'] = self.settings.copy()
        self.program[self.prog_name] = self._set_processes()

    def _set_processes(self):
        """Set one or more processes in terms of 'numprocs' setting."""
        numprocs = self.program['settings']['numprocs']
        
        processes = {}
        if numprocs == 1:
            processes[self.prog_name] = [None, None, False, False, None, self.settings['startsecs'], self.settings['startretries'], -1, None, 0]
        elif numprocs > 1:
            for i in range(numprocs):
                processes[self.prog_name + '_' + str(i)] = [None, None, False, False, None, self.settings['startsecs'], self.settings['startretries'], -1, None, 0]
            #print(processes)
#        print(processes)
#        time.sleep(10)
        return processes
