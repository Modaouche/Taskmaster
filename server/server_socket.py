import socket, pickle, select, sys, time
LENGTH_MAX = 32

class Communication_S():

    def __init__(self, processesHandler):
        """Initialize attributes for sockets."""

        self.processesHandler = processesHandler
        self.lock_commands = self.processesHandler.lock_commands
        self.lock_datas = self.processesHandler.lock_datas
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind((socket.gethostname(), 9002))
        self.server_sock.listen()
        self.sockets_list = [self.server_sock]

    def __call__(self):
        """ Main part of server exchange """ 
        
        self.lock_commands.acquire()
        cmd = self.processesHandler.commands
        self.lock_commands.release()
        while True:
            if cmd:
                continue
            
            read_sockets, _, exception_sockets = select.select(self.sockets_list,\
                                                                [],\
                                                                self.sockets_list)
            for notified_socket in read_sockets:
                if notified_socket == self.server_sock:
                    client_socket, client_address = self.server_sock.accept()

                    self.sockets_list.append(client_socket)
                    print('Accepted new connection from {}:{}'.format(*client_address))

                else:
                    msg = self._receive(notified_socket)

                    if msg == False:
                        print('End of connection from a client.')
                        self.sockets_list.remove(notified_socket)
                        continue

                    #Split msg into list with ' ' separator
                    #Then add a parser in every if elif statement the client's will
                    #(with the given cmd)
                    self.lock_commands.acquire()
                    cmd.insert(0, msg.split(' '))
                    self.lock_commands.release()

                    if cmd[0][0] == "status":
                        self._sending(notified_socket, b"status", False)
                        datas = self._get_datas()
                        self._sending(notified_socket, datas, True)

                    elif cmd[0][0] == "start":
                        self._sending(notified_socket, b"started", False)
                        datas = self._get_datas()
                        self._sending(notified_socket, datas, True)

                    elif cmd[0][0] == "stop":
                        self._sending(notified_socket, b"stopped", False)
                        datas = self._get_datas()
                        self._sending(notified_socket, datas, True)

                    elif cmd[0][0] == "restart":
                        self._sending(notified_socket, b"restarted", False)
                        datas = self._get_datas()
                        self._sending(notified_socket, datas, True)

                    elif cmd[0][0] == "reload":
                        self._sending(notified_socket, b"reloaded", False)

                    elif cmd[0][0] == "shutdown":
                        self._sending(notified_socket, b"shutdown", False)
                        raise SystemExit(0)
                        
                    else:
                        self._sending(notified_socket, b"Error", False)
            
            for notified_socket in exception_sockets:
                self.sockets_list.remove(notified_socket)
            
        #a mettre dans les signaux->self.communication.close()


    def _sending(self, sock, datas, pickled):
        """
            Sending method:
            1) if pickled == True, pickle the msg to be sent
            2) prepare the length of the msg
            3) send len_msg + msg itself
        """
        try:
            if pickled == True:
                to_send = pickle.dumps(self._copy(datas))
                self.processesHandler.datas = []
                self.processesHandler.datas_right = False
                self.lock_datas.release()

            else:
                to_send = datas

            to_send_len = bytes(f'{str(len(to_send)):>{LENGTH_MAX}}', "utf-8")
            sock.send(to_send_len + to_send)

        except Exception as e:
            print("Communication error: Could'nt send information.", file= sys.stderr)
            print(e, file=sys.stderr)


    def _receive(self, client_sock):
        """
            Receive method:
            2) receive the length of the msg
            3) receive the msg itself
        """
        try:
            msg_len = client_sock.recv(LENGTH_MAX)
            if not len(msg_len):
                return False
            msg = client_sock.recv(int(msg_len.lstrip()))

        except:
            return False

        return msg.decode("utf-8")


    def _copy(self, datas):
        """ Personal deepcopy function """
        if not datas:
            return []

        result = {}
        for data in datas:
            if type(data) is str:
                if type(result) is dict:
                    result = []
                result.append(data)
                continue

            for k, v in data.items():
                if k == "settings":
                    continue
                result.update({k : None})
                for k, v in v.items():
                    value = []
                    for val in v:
                        if type(val) is int or type(val) is float or type(val) is bool:
                            value.append(val)
                    result.update({k : value})

        return result
   
    def _get_datas(self):
        """get ran programs/processes informations from the main program as thread"""
        self.lock_datas.acquire()
        while self.processesHandler.datas_right == False:
            self.lock_datas.release()
            time.sleep(0.1)
            self.lock_datas.acquire()

        datas = self.processesHandler.datas
        return datas

    #def accept_connect(self):
    #    self.clientsocket, self.address = self.server_sock.accept()
    #    print(f"Connection from {self.address} has been established.")

    def close(self):
        self.server_sock.close()
