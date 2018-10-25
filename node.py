#!/usr/bin/env python3

import socket
from threading import Thread, Event
from queue import Queue
from cmd import Cmd
import random
import time
import os
import sys
import psutil

# P2P Node class usage info
# Attributes:
#       Node.messages         -> A buffer (of type queue) of received messages.
# Methods:
#       Node.send_message(id, message) -> Sends a message to node by id.
#       Node.peers()          -> Returns a list of connected nodes' ids.
#       Node.kill()           -> Terminates node.

# NODE -------------------------------------------------------------------------
# ------------------------------------------------------------------------------

class Node():
    def __init__(self, debug):
        self.messages = Queue()
        self.__DEBUG = debug
        self.__ID = str(random.randint(11111111, 99999999))
        self.__BASE_PORT = 12345
        self.__DISCOVERY_HOST = Node.__getBroadcastIP()
        self.__DISCOVERY_PORT = Node.__getBroadcastPort(self.__BASE_PORT)
        self.__DISCOVERY_PING = 1
        self.__DISCONNECT_TIMEOUT = 10
        self.__NODE_HOST = Node.__getIP()
        self.__NODE_PORT = random.randint(1025, 65535+1)
        self.__peerlist = {}
        self.__reversepeer = {}
        self.__discovering = Event()
        self.__listening = Event()
        Thread(target=self.__discoverer).start()
        Thread(target=self.__listener).start()
        if self.__DEBUG:
            print('\n-<<[ (Node %s)-(%s, %5d) ]>>-' % \
                (self.__ID, self.__NODE_HOST, self.__NODE_PORT))

    def kill(self):
        self.__discovering.clear()
        self.__listening.clear()

    def peers(self, print=False):
        if print:
            for peer in self.__peerlist.keys():
                print("peer %s-(%s, %5d)" % \
                    (peer, self.__peerlist[peer][0], self.__peerlist[peer][1]))
            print('done')
        return self.__peerlist



# NET INFO ---------------------------------------------------------------------
# ------------------------------------------------------------------------------

    def __getIP():
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]

    def __getBroadcastIP():
        if os.name == 'nt':
            return Node.__getIP()
        else:
            return '<broadcast>'

    def __getBroadcastPort(port):
        if os.name == 'nt':
            port += Node.__getNodeCount()
        return port

    def __getNodeCount():
        count = 0
        for proc in psutil.process_iter():
            if proc.name() == "python.exe":
                count += 1
        return count



# DISCOVERER -------------------------------------------------------------------
# ------------------------------------------------------------------------------

    def __discoverer(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((self.__DISCOVERY_HOST, self.__DISCOVERY_PORT))
            except Exception as e:
                print(e)
                sys.exit()
            self.__discovering.set()
            while self.__discovering.is_set():
                try:
                    s.settimeout(self.__DISCOVERY_PING)
                    message, addr = s.recvfrom(1024)
                    Thread(target=self.__handle_message, args=(message, addr,)).start()
                except socket.timeout as e:
                    self.send_message(
                        id = 0,
                        message = 'HeyBrah-'+self.__NODE_HOST+'-'+str(self.__NODE_PORT)+'-'+self.__ID,
                        discovery = True
                    )
                    for peer in self.__peerlist.copy().keys():
                        tuple = self.__peerlist[peer]
                        if time.time() - tuple[2] > self.__DISCONNECT_TIMEOUT:
                            del self.__peerlist[peer]
                            del self.__reversepeer[(tuple[0], tuple[1])]
                            if self.__DEBUG:
                                print('node', peer, 'disconnected')
                except Exception as e:
                    print(e)
            s.close()



# LISTENER ---------------------------------------------------------------------
# ------------------------------------------------------------------------------

    def __listener(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((self.__NODE_HOST, self.__NODE_PORT))
                s.listen(0)
                s.settimeout(1)
            except Exception as e:
                print(e)
            self.__listening.set()
            while self.__listening.is_set():
                try:
                    client, addr = s.accept()
                    Thread(target=self.__handle_connection, args=(client, addr,)).start()
                except socket.timeout as e:
                    pass
                except Exception as e:
                    print(e)
            s.close()



# MESSAGE HANDLERS -------------------------------------------------------------
# ------------------------------------------------------------------------------

    def __handle_connection(self, client, addr):
        message = client.recv(1024)
        self.__handle_message(message, addr)
        client.close()

    def __handle_message(self, message, addr):
        message = message.decode('utf-8')
        split = message.split('-')
        message = '-'.join(split[1:])
        if split[0] == 'HeyBrah':
            if not (split[1] == self.__NODE_HOST and int(split[2]) == self.__NODE_PORT):
                if self.__DEBUG and split[3] not in self.__peerlist:
                    print('node', split[3], 'connected')
                self.__peerlist[split[3]] = (split[1], int(split[2]), time.time())
                self.__reversepeer[(split[1], int(split[2]))] = split[3]
            return ''
        else:
            if self.__DEBUG:
                print("from %s %s" % (split[0], message))
            self.messages.put({'sender':split[0], 'contents':message})

    def send_message(self, id, message, discovery=False):
        if id == 0:
            ip = self.__DISCOVERY_HOST
            port = self.__DISCOVERY_PORT
        else:
            try:
                ip = self.__peerlist[str(id)][0]
                port = self.__peerlist[str(id)][1]
            except KeyError as e:
                if self.__DEBUG:
                    print('---- Invalid peer ->', e)
                return
        try:
            if discovery:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind((self.__NODE_HOST, self.__NODE_PORT))
                    prange = 1
                    if os.name == 'nt':
                        prange += Node.__getNodeCount()
                    for iport in range(self.__BASE_PORT, self.__BASE_PORT + prange):
                        s.sendto(message.encode('utf-8'), (ip, iport))
            else:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((ip, port))
                    message = self.__ID + '-' + message
                    s.sendall(message.encode('utf-8'))
        except Exception as e:
            print('---- Send to ->', id, 'failed:', e)



# CMD --------------------------------------------------------------------------
# ------------------------------------------------------------------------------

class NodeCMD(Cmd):
    def do_quit(self, args):
        """Terminates the node."""
        self.node.kill()
        raise SystemExit

    def do_init(self, args=None):
        """Initializes the node."""
        self.node = Node(debug=True)

    def do_list(self, args):
        '''Lists all peers.'''
        self.node.peers(print=True)

    def do_send(self, args):
        """Sends a message."""
        args = args.split()
        message = 'test'
        id = 0
        if len(args) >= 1:
            id = args[0]
        if len(args) >= 2:
            message = args[1]
        if len(args) >= 3:
            for arg in args[2:]:
                message = message + ' ' + arg
        self.node.send_message(id, message)

if __name__ == '__main__':
    cmd = NodeCMD()
    cmd.do_init()
    cmd.prompt = ''
    cmd.cmdloop('')
