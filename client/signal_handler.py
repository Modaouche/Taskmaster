import signal, termios, sys, fcntl, time, os

class Sig():

    def __init__(self):
        """Attributes for signal handler"""
        self.fd = sys.stderr.fileno()
        self.old = termios.tcgetattr(self.fd)
        self.new = None
        self.cc = self.old[6][termios.VSUSP]


    def signal_handler(self):
        signal.signal(signal.SIGINT, self._sigend)
        signal.signal(signal.SIGTERM, self._sigend)
        signal.signal(signal.SIGQUIT, self._sigend)
        signal.signal(signal.SIGCONT, signal.SIG_IGN)
        signal.signal(signal.SIGTSTP, self._sigsleep)
        signal.signal(signal.SIGWINCH, self._sigresize)


    def _sigend(self, signum, cur_sf):
        """End signal Handler"""
        try:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)
            print("\nEnd of Taskmasterctl.")
            sys.exit(0)

        except termios.error as num:
            print(f"\nError sigend : {num}")


    def _sigsleep(self, signum, cur_sf):
        """sleep signal Handler"""
        try:
            if os.isatty(self.fd):
                if self.new == None:
                    self.new = termios.tcgetattr(self.fd)
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)
                self.old = None
                sys.stdout.write("\r\nSleep of Taskmasterctl.\n\r")
                signal.signal(signal.SIGCONT, self._sigwake)
                signal.signal(signal.SIGTSTP, signal.SIG_DFL)
                fcntl.ioctl(self.fd, termios.TIOCSTI, self.cc)

        except termios.error as num:
            print(f"\nError sigsleep : {num}")


    def _sigwake(self, signum, cur_sf):
        """continue signal Handler"""
        try:
            if self.old == None:
                self.old = termios.tcgetattr(self.fd)
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.new)# check error ?
            signal.signal(signal.SIGTSTP, self._sigsleep)
            sys.stdout.write("\rTaskMaster $> ")
            sys.stdout.write('\x1b[s')
            self._sigresize(0, None)

        except termios.error as num:
            print(f"\nError sigwake : {num}")
            signal.signal(signal.SIGTSTP, self._sigsleep)

    def _sigresize(self, signum, cur_sf):
        fcntl.ioctl(self.fd, termios.TIOCSTI, "")

