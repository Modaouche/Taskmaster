"""Argument parser"""
"""Command : status, start [prog_name], stop [prog_name], restart [prog_name], reload, shutdown"""

class CmdParser():
    """ A class which parse arguments of our program. """

    def __init__(self):
        """ Initialize attibute for the Parser """

        self.command = []
        self.multi_param_cmd = ["status", "start", "stop", "restart", "exit"]


    def run(self, args):
        """ main parsing of argument parser [tm restart all]"""

        if not args:
            return self.command

        if args[0] == "shutdown" or args[0] == "reload":
            self.command.append(args[0])
            if len(args) > 1:
                print(f"Error: {args[0]} accepts no arguments")
        
        elif self._check_multi_param(args):
            for arg in args:
                self.command.append(arg)

        return self.command


    def _check_multi_param(self, args):
        """ for start, stop restart status """
        
        for i in range(len(self.multi_param_cmd)):
            if self.multi_param_cmd[i] == args[0]:
                return True

        print (f"Error: {args[0]}, unknow command" )
        return False
