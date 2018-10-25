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



# NODE -------------------------------------------------------------------------
# ------------------------------------------------------------------------------

class Node():
    def __init__(self, debug):
        self.DEBUG = debug
        self.ID = str(random.randint(11111111, 99999999))
        self.BASE_PORT = 12345
        self.DISCOVERY_HOST = Node.getBroadcastIP()
        self.DISCOVERY_PORT = Node.getBroadcastPort(self.BASE_PORT)
        self.NODE_HOST = Node.getIP()
        self.NODE_PORT = random.randint(1025, 65535+1)
        self.messages = Queue()
        self.peerlist = {}
        self.reversepeer = {}
        self.discovering = Event()
        self.listening = Event()
        Thread(target=self.discoverer, args=(self.discovering,)).start()
        Thread(target=self.listener, args=(self.listening,)).start()
        if self.DEBUG:
            print('\n-<<[(Node %s)-(%s, %5d)]>>-' % \
                (self.ID, self.NODE_HOST, self.NODE_PORT))

    def kill(self):
        self.discovering.clear()
        self.listening.clear()

    def peers(self):
        if self.DEBUG:
            for peer in self.peerlist.keys():
                print("peer %s-(%s, %5d)" % \
                    (peer, self.peerlist[peer][0], self.peerlist[peer][1]))
            print('done')
        return self.peerlist



# NET INFO ---------------------------------------------------------------------
# ------------------------------------------------------------------------------

    def getIP():
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]

    def getBroadcastIP():
        if os.name == 'nt':
            return Node.getIP()
        else:
            return '<broadcast>'

    def getBroadcastPort(port):
        if os.name == 'nt':
            port += Node.getNodeCount()
        return port

    def getNodeCount():
        count = 0
        for proc in psutil.process_iter():
            if proc.name() == "python.exe":
                count += 1
        return count



# DISCOVERER -------------------------------------------------------------------
# ------------------------------------------------------------------------------

    def discoverer(self, discovering):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            try:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((self.DISCOVERY_HOST, self.DISCOVERY_PORT))
                s.settimeout(1)
            except Exception as e:
                print(e)
                sys.exit()
            discovering.set()
            while discovering.is_set():
                try:
                    message, addr = s.recvfrom(1024)
                    Thread(target=self.handle_message, args=(message, addr,)).start()
                except socket.timeout as e:
                    self.send_message(
                        id = 0,
                        message = 'HeyBrah-'+self.NODE_HOST+'-'+str(self.NODE_PORT)+'-'+self.ID,
                        discovery = True
                    )
                    for peer in self.peerlist.copy().keys():
                        tuple = self.peerlist[peer]
                        if time.time() - tuple[2] > 10:
                            del self.peerlist[peer]
                            del self.reversepeer[(tuple[0], tuple[1])]
                    time.sleep(random.random())
                except Exception as e:
                    print(e)
            s.close()



# LISTENER ---------------------------------------------------------------------
# ------------------------------------------------------------------------------

    def listener(self, listening):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((self.NODE_HOST, self.NODE_PORT))
                s.listen(5)
                s.settimeout(1)
            except Exception as e:
                print(e)
            listening.set()
            while listening.is_set():
                try:
                    client, addr = s.accept()
                    Thread(target=self.handle_connection, args=(client, addr,)).start()
                except socket.timeout as e:
                    pass
                except Exception as e:
                    print(e)
            s.close()



# MESSAGE HANDLERS -------------------------------------------------------------
# ------------------------------------------------------------------------------

    def handle_connection(self, client, addr):
        message = client.recv(1024)
        self.handle_message(message, addr)
        client.close()

    def handle_message(self, message, addr):
        message = message.decode('utf-8')
        split = message.split('-')
        message = '-'.join(split[1:])
        if split[0] == 'HeyBrah':
            if not (split[1] == self.NODE_HOST and int(split[2]) == self.NODE_PORT):
                self.peerlist[split[3]] = (split[1], int(split[2]), time.time())
                self.reversepeer[(split[1], int(split[2]))] = split[3]
            return ''
        else:
            if self.DEBUG:
                print("from %s %s" % (split[0], message))
            self.messages.put(message)

    def send_message(self, id, message, discovery=False):
        if id == 0:
            ip = self.DISCOVERY_HOST
            port = self.DISCOVERY_PORT
        else:
            try:
                ip = self.peerlist[str(id)][0]
                port = self.peerlist[str(id)][1]
            except KeyError as e:
                if self.DEBUG:
                    print('---- Invalid peer ->', e)
                return
        try:
            if discovery:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind((self.NODE_HOST, self.NODE_PORT))
                    prange = 1
                    if os.name == 'nt':
                        prange += Node.getNodeCount()
                    for iport in range(self.BASE_PORT, self.BASE_PORT + prange):
                        s.sendto(message.encode('utf-8'), (ip, iport))
            else:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect((ip, port))
                    message = self.ID + '-' + message
                    s.sendall(message.encode('utf-8'))
        except Exception as e:
            print(e)



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
        self.node.peers()

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
