import socket, pickle, errno
LENGTH_MAX = 32

class Communication_C():
    """Class for server exchange"""

    def __init__(self):
        self.host = socket.gethostname()
        self.port = 9002
        self.connected = False
        self.cmd = ''
        self.answer = '' 

    def __call__(self, command):
        """ Main part of our class, send -> receive -> treatment """

        self.cmd = ' '.join(command)
        self.cmd = self.cmd.strip()
        msg_len = f'{str(len(self.cmd)):>{LENGTH_MAX}}'

        if len(msg_len) > LENGTH_MAX:
            return "Dude, what is this length..."

        if self.connected == False:
            if self._connection() == False:
                return self.answer
        
        # - Beginning
        
        self.answer = self._sending(self.cmd, msg_len)
        if self.answer != True:
            return self.answer 

        self.answer = self._receive(False)
        self.answer = self.answer.decode("utf-8")
        
        if self.answer == "status":
            self.answer = self._receive(True)
        
        elif self.answer == "started":
            self.answer = self._receive(True)

        elif self.answer == "stopped":
            self.answer = self._receive(True)

        elif self.answer == "restarted":
            self.answer = self._receive(True)

        elif self.answer == "reloaded":
            self.answer = "Server Reload: reload taskmaster."

        elif self.answer == "shutdown":
            self.answer = "Server Shutdown: end of communication."
            self.client_sock.close()
            self.connected = False

        else:
            self.answer = f"Communication error: {self.answer}."

        return self.answer


    def _sending(self, msg, msg_len):#va etre un envois pickled (je confirme)
        """
            Sending method which send first the length of the msg,
            then the msg itself. Finally a recv is called for confirmation
        """
        try:
            self.client_sock.send(bytes(msg_len + msg, "utf-8"))
            return True

        except:
            self.connected = False
            return "Communication error: Could'nt send to the server."

#
    def _receive(self, pickled):
        """
            Pickled == True  -> To receive the entire information from the server

            Pickled == False -> Receive the length of the next msg or the cmd
                                without args (to know how to treat the next cmd)
        """
        reply = b"retry"

        while reply == b"retry":
            try:
                reply_len = self.client_sock.recv(LENGTH_MAX)
                reply = self.client_sock.recv(int(reply_len.lstrip()))
                if pickled == True:
                    reply = pickle.loads(reply)

            except IOError as e:
                if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                    self.connected = False
                    self.client_sock.close()
                    reply = b"Could'nt receive from the server: IO error"
                
                else:
                    reply = b"retry"
            
            except ValueError:
                self.connected = False
                self.client_sock.close()
                reply = bytes(f"Could'nt receive from the server: Seems to be closed",\
                                "utf-8")

            except Exception as e:
                self.connected = False
                self.client_sock.close()
                reply = bytes(f"Could'nt receive from the server: {e}", "utf-8")

        return reply


    def _connection(self):
        """ Connection part of our class """
        #parsing connexion with checking command if she spec exceptionnal port|host or open .conf

        try:
            self.client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_sock.connect((self.host, self.port))
            self.client_sock.setblocking(False)
            self.connected = True
            return True

        except:
            self.answer = "Communication error: Could'nt connect to the server."
            self.connected = False
            return False
