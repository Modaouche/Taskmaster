"""A module for handling signals sent by children processes."""

import os
import signal, socket
from datetime import datetime

LENGTH_MAX = 32

class Signals():
    """A class for signals handling."""

    def __init__(self, taskmaster, processes_handler):
        """Initialize attributes for signals."""
        self.taskmaster = taskmaster
        self.processes_handler = processes_handler
        self.host = socket.gethostname()
        self.port = 9002

    def _stop_and_exit(self, sig, frame):
        """Stop all processes and exit the program gracefully"""
        print(datetime.strftime(datetime.now(), "%Y-%m-%d %I:%M:%S, "), end='')
        print("WARN received SIGINT indicating exit request")
        self.processes_handler.client_request._stop_all()
        self.processes_handler.communication.close()
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        os.kill(os.getpid(), signal.SIGINT)

    def _reload_config(self, sig, frame):
        """Reload the configuration file."""
        print(datetime.strftime(datetime.now(), "%Y-%m-%d %I:%M:%S, "), end='')
        print("WARN received SIGHUP indicating reload request")
        self.processes_handler.client_request._reload_handler()

    def sigint_handler(self):
        """Handle SIGINT"""
        signal.signal(signal.SIGINT, self._stop_and_exit)

    def sighup_handler(self):
        """Handle  SIGHUP"""
        signal.signal(signal.SIGHUP, self._reload_config)
