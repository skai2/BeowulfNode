#!/usr/bin/env python3

import socket
from threading import Thread, Event
from queue import Queue
from cmd import Cmd
import random
import time



class Node():
# MAIN -------------------------------------------------------------------------
# ------------------------------------------------------------------------------
    def __init__(self, debug):
        self.DEBUG = debug
        self.ID = str(random.randint(111111, 999999))
        self.DISCOVERY_HOST = '<broadcast>'
        self.DISCOVERY_PORT = 12345
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
            print('-<<[(Node %s)-(%s, %5d)]>>-' % \
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

# LISTENERS ----------------------------------------------------------------------
# ------------------------------------------------------------------------------

    def discoverer(self, discovering):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((self.DISCOVERY_HOST, self.DISCOVERY_PORT))
            except Exception as e:
                print(e)
            s.settimeout(1)
            discovering.set()
            while discovering.is_set():
                try:
                    message, addr = s.recvfrom(1024)
                    Thread(target=self.handle_message, args=(message, addr,)).start()
                except socket.timeout as e:
                    self.send_message(0, 'HeyBrah-'+self.NODE_HOST+'-'+str(self.NODE_PORT)+'-'+self.ID)
                    for peer in self.peerlist.copy().keys():
                        tuple = self.peerlist[peer]
                        if time.time() - tuple[2] > 10:
                            del self.peerlist[peer]
                            del self.reversepeer[(tuple[0], tuple[1])]
                    time.sleep(random.random())
                except Exception as e:
                    print(e)
            s.close()

    def listener(self, listening):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((self.NODE_HOST, self.NODE_PORT))
            except Exception as e:
                print(e)
            listening.set()
            while listening.is_set():
                try:
                    message, addr = s.recvfrom(1024)
                    Thread(target=self.handle_message, args=(message, addr,)).start()
                except Exception as e:
                    print(e)
            s.close()

    def handle_message(self, message, addr):
        message = message.decode('utf-8')
        split = message.split('-')
        if split[0] == 'HeyBrah':
            if not (split[1] == self.NODE_HOST and int(split[2]) == self.NODE_PORT):
                self.peerlist[split[3]] = (split[1], int(split[2]), time.time())
                self.reversepeer[(split[1], int(split[2]))] = split[3]
            return ''
        else:
            if self.DEBUG:
                print("from %s %s" % (self.reversepeer[addr], message))
            self.messages.put(message)

# SENDERS ----------------------------------------------------------------------
# ------------------------------------------------------------------------------

    def getIP():
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]

    def send_message(self, id, message):
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
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((self.NODE_HOST, self.NODE_PORT))
                s.sendto(message.encode('utf-8'), (ip, port))
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
