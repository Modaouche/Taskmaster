import atexit, os
import signal, sys

class Daemonization():
    """class that permit to daemonize taskmaster"""

    def __init__(self):
        """Initialize our attributes"""

    def daemonize(self, pidfile, *,
                            stdin='/dev/null',
                            stdout='/dev/null',
                            stderr='/dev/null'):
        """"""
        self.pidfile = pidfile
        if os.path.exists(pidfile):
            raise RuntimeError('Taskmaster: Already running.')
        
        # First fork (detaches from parent)
        try:
            if os.fork() > 0:
                raise SystemExit(0)
        # Parent exit
        except OSError as e:
            raise RuntimeError('Taskmaster: fork #1 failed.')
        
        os.chdir('/')
        os.umask(0)
        os.setsid()
        
        # Second fork (relinquish session leadership)
        try:
            if os.fork() > 0:
                raise SystemExit(0)
        except OSError as e:
            raise RuntimeError('Taskmaster: fork #2 failed.')
        
        # Flush I/O buffers
        sys.stdout.flush()
        sys.stderr.flush()
        
        # Replace file descriptors for stdin, stdout, and stderr
        with open(stdin, 'rb', 0) as f:
            os.dup2(f.fileno(), sys.stdin.fileno())
        with open(stdout, 'ab', 0) as f:
            os.dup2(f.fileno(), sys.stdout.fileno())
        with open(stderr, 'ab', 0) as f:
            os.dup2(f.fileno(), sys.stderr.fileno())
        
        # Write the PID file
        with open(pidfile,'w') as f:
            print(os.getpid(),file=f)
        # Arrange to have the PID file removed on exit/signal
        atexit.register(lambda: os.remove(pidfile))
        # Signal handler for termination (required)

        signal.signal(signal.SIGTERM, self._sigterm_handler)


    def _sigterm_handler(self, signo, frame):
        os.remove(self.pidfile)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        os.kill(os.getpid(), signal.SIGTERM)
