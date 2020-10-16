import sys, os, signal

from configparser import ConfigParser
from signals import Signals
from daemon import Daemonization
from processeshandler import ProcessesHandler

import time

class TaskMaster():
    """A class which launch a supervisor program like."""

    def __init__(self, pathname):
        """Initialize attributes for taskmaster."""

#        self.flag_args = 0
#        self._check_args()
        self.filename = pathname
        self.config = ConfigParser(self)
        self.processes = ProcessesHandler(self)
        self.signals = Signals(self, self.processes)
#        self.signals = Signals()
    
    def run(self):
        """The main loop for the whole program."""
       
#        self.signals._signals_handler()

        self.signals.sigint_handler()
        self.config.parse()
        print("##################################################")
        print(self.config.programs)
        print("##################################################")
#        time.sleep(50)
        self.signals.sighup_handler()
        self.processes.run()


if __name__ == '__main__':
    
    PIDFILE = '/tmp/server_daemon.pid'

    if len(sys.argv) <= 1 or (len(sys.argv) == 2 and sys.argv[1] == '-n'):
        print("Usage: {}   [config_file]\trun daemonized server by default\n".format(sys.argv[0])
                + '\t\t    -n [config_file]\toption to run in the foreground.\n'\
                + '\t\t    -s\t\t\tto stop the daemon already running', file=sys.stderr)
        raise SystemExit(1)

    elif sys.argv[1] == '-n':
        sys.argv.pop(0)
        pathname = os.getcwd() + '/' + sys.argv[1]
    
    elif sys.argv[1] == '-s':
        if os.path.exists(PIDFILE):
            with open(PIDFILE) as f:
                os.kill(int(f.read()), signal.SIGTERM)
        else:
            print('Taskmaster: Not running.', file=sys.stderr)
            raise SystemExit(1)

        print('Taskmaster: Process ended.', file=sys.stderr)
        raise SystemExit(0)

    else:
        pathname = os.getcwd() + '/' + sys.argv[1]
        dm = Daemonization()
        try:
            dm.daemonize(PIDFILE,\
                        stdout='/tmp/serverd_out.log',\
                        stderr='/tmp/serverd_err.log')
        except RuntimeError as e:
            print(e, file=sys.stderr)
            raise SystemExit(1)

    tm = TaskMaster(pathname)
    tm.run()
