""" Line edition with reader command functions"""

#>gerer les multilignes genre up le save a chaque tranche de ligne en fonction de la taille du terminal

#>>signaux a gerer ctrl z avec un reset du term + un reprint du prompt au sigcont et quitter quand c'est un ctrl c...

import os, sys, tty, termios, re, fcntl

PROMPT_LEN = len("TaskMaster $> ")

class LineEdit():
    """ Class for shell's line edition """

    def __init__(self):
        """ initialization of terminal configuration attributes """

        self.fd = sys.stderr.fileno()
        self.old = termios.tcgetattr(self.fd)
        self.new = termios.tcgetattr(self.fd)
        self.new[3] &= ~termios.ECHO & ~termios.ICANON
        self.new[3] |= termios.IEXTEN
        self.new[1] &= ~termios.OPOST
        self.new[6][termios.VTIME] = 0
        self.new[6][termios.VMIN] = 1
        self.susp = self.old[6][termios.VSUSP]#test
        """ General purpose attributes """

        self.command = []
        self.offset = 0
        self.key = ''
        self.hist = []
        self.histoffset = -1
        self.rows, self.columns = 0, 0
        self.in_prompt_len = 0
        self.pos = [0, 0]

    def run(self, hist):
        """Main part of line edition"""


        self._reset_attribute()
        self.hist = hist
        sys.stdout.write("TaskMaster $> ")
        sys.stdout.write('\x1b[s')
        sys.stdout.flush()
            
        while self.key != '\n':
            self.key = self._parse_key()    

        sys.stdout.write('\n')
        sys.stdout.flush()
        
        string = ''.join(self.command)
        string = string.strip()
        if not string:
            return []
        return string.split(' ')



    def _reset_attribute(self):
        """simple reset function to handle new commands"""

        self.command.clear()
        self.offset = 0
        self.key = ''
        self.histoffset = -1
        ret = self._get_cursor_pos()
        if ret:
            self.pos = [0, 0]
            self.pos[0] = int(ret[0])
            self.pos[1] = int(ret[1])

    def _parse_key(self):
        """Function that parse readed key and execute """

        # get winsize of our term
        self.rows, self.columns = os.popen('stty size', 'r').read().split()
        self.rows = int(self.rows)
        self.columns = int(self.columns)

        try:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.new)
            k = self._get_key()

            if not self.command:
                self.hist_mode = True

            if k == '\x1b':
                k = self._get_key()
                k = self._get_key()
                if k == 'A' or k == 'B':
                    self._history(k)
                elif k == 'D' and self.offset > 0:
                    self.offset -= 1
                    self._printcmd(self.offset)
                elif k == 'C' and self.offset < len(self.command):
                    self.offset += 1
                    self._printcmd(self.offset)
            elif k == '\x7f' and self.offset > 0:
                self._erase_key()
            elif k >= ' ' and k <= '~':
                self._add_key(k)
            elif k == '\x04':
                sys.stdout.write("\n\r")#to change
                sys.exit(0)
            elif k == '\0':
                self._printcmd(self.offset)


            sys.stdout.flush()
        finally:                                
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)
        return k


    def _get_key(self):
        """ Read part of our code with setting and resetting """
        ch = sys.stdin.read(1)
        return ch


    def _erase_key(self):
        """Delete element from our command"""
        self.hist_mode = False
        self.histoffset = -1
        self.offset -= 1
        self.command.pop(self.offset)
        self._printcmd(self.offset)


    def _add_key(self, k):
        """Add element to our command"""    
        self.hist_mode = False
        self.histoffset = -1
        self.command.insert(self.offset, k)
        self.offset += 1
        self._printcmd(self.offset)
        

    def _history(self, key):
        """Function to handle the history"""
        if self.hist_mode == True and self.hist:
            if self.command and key == 'B' and self.histoffset < -1:
                self.histoffset += 1
            if self.command and key == 'A' and self.histoffset > -len(self.hist):
                self.histoffset -= 1
            self.command = self._split(self.hist[self.histoffset])
            self.offset = len(self.command)
            self._printcmd(self.offset)


    def _split(self, word): 
        """Simple function that split history and obtain the chosen command"""
        return [char for char in word]


 
    def _printcmd(self, offset):
        """Function that update the visualization of our command"""

        sys.stdout.write('\x1b[u')
        ret = self._get_cursor_pos()
        if ret:
            self.pos = [0,0]
            self.pos[0] = int(ret[0])
            self.pos[1] = int(ret[1])
        else:#something to do if get_cursor_pos fail to replace the behavior ?
            pass

        cmd_height = int(((len(self.command) + PROMPT_LEN) / self.columns) + self.pos[0])

        if cmd_height > self.rows:
            for i in range(0, (cmd_height - self.rows)):
                sys.stdout.write(f"\x1b[{self.rows};0f")
                sys.stdout.write("\x1bD")
                sys.stdout.write('\x1b[u')

            reposition = int(self.pos[0] - (cmd_height - self.rows))
            sys.stdout.write(f"\x1b[{reposition};0f")
            sys.stdout.write("TaskMaster $> ")
            sys.stdout.write("\x1b[s")

        sys.stdout.write('\x1b[J')
        sys.stdout.write(''.join(self.command))
        
        my_column = int((self.offset + PROMPT_LEN + 1) % self.columns)
        my_line = int((self.offset + PROMPT_LEN + 1) / self.columns + self.pos[0])
        if my_column == 0:
            my_column = self.columns
            my_line -= 1
        sys.stdout.write(f"\x1b[{my_line};{my_column}f")


    def _get_cursor_pos(self):
        """Function to get and return the current position of our cursor"""
        try:

            self.new[0] &= ~termios.IXOFF#useless no ?
            self.new[0] &= ~termios.IXON#useless no ?

            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.new)
            sys.stdout.write("\x1b[6n");
            sys.stdout.flush()
            b = ''
            while True:
                b += sys.stdin.read(1)
                if b[-1] == 'R':
                    break

        finally:    
            self.new[0] |= termios.IXOFF#useless no ?
            self.new[0] |= termios.IXON#useless no ?
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)
        
        try:
            matches = re.match(r"^\x1b\[(\d*);(\d*)R", b)
            groups = matches.groups()
            return groups

        
        except AttributeError:
            return None
