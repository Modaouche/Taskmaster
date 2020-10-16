"""Taskmaster client to interact with the server"""
"""Command : status, start [prog_name], stop [prog_name], restart [prog_name|all], reload, shutdown"""

import sys
from line_edition import LineEdit
from cmd_parser import CmdParser
from client_socket import Communication_C
from signal_handler import Sig
from print_answer import Print_answer

class TaskMasterCtl():
    """ A class which launch a supervisorclt program like. """

    def __init__(self):
        """ Initialize attibute for Taskmasterctl """
        self.command_parser = CmdParser()
        self.line_edition = LineEdit()
        self.communication = Communication_C()
        self.print_answer = Print_answer()
        self.sighdl = Sig()
        sys.argv.pop(0)
        self.args = sys.argv
        self.history = []
        self.command = []
        self.answer = {}


    def run(self):
        """ Run the choice of the user """
        self.sighdl.signal_handler()

        if len(self.args) == 0:
            self._run_as_shell()
        else:
            self._run_as_argument()


    def _run_as_shell(self):
        """ Method that run a shell """

        while True:
            self.command = self.line_edition.run(self.history)
            if self.command:
                self.history.append(' '.join(self.command))

            self.command = self.command_parser.run(self.command)
            if not self.command:
                continue
            if self.command[0] == "exit":
                self.command.clear()
                break
            self.answer = self.communication(self.command)
            self.print_answer(self.answer)
            self.command.clear()

    def _run_as_argument(self):
        """ Method that run according to the arguments sended """
        self.command = self.command_parser.run(self.args)
        if self.command:
            if self.command[0] == "exit":
                return
            self.answer = self.communication(self.command)
            self.print_answer(self.answer)
        
        self.command.clear()


if __name__ == "__main__":
    tm_ctl = TaskMasterCtl()
    tm_ctl.run()
