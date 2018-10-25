#!/usr/bin/env python3

from cmd import Cmd
from node import Node
from threading import Thread, Event
import random as r
import math as m



class BNode(Cmd):

    def do_init(self):
        """Initializes the node."""
        self.node = Node(debug=True)
        self.helping = Event()
        self.helper = Thread(target=self.__helper).start()
        print('init Pi Monte Carlo Node Started')

    def do_quit(self, args):
        """Terminates the node."""
        self.helping.clear()
        self.node.kill()
        raise SystemExit

    def do_list(self, args):
        peers = self.node.peers()
        for peer in peers.keys():
            print("peer %s-(%s, %5d)" % \
                (peer, peers[peer][0], peers[peer][1]))
        print('done')

    def do_calc(self, args):
        args = args.split()
        if len(args) != 1:
            print('---- Invalid arguments!')
            return
        self.peers = self.node.peers()
        self.distributed_monte_carlo(int(args[0]))

    def distributed_monte_carlo(self, points):
        count = len(self.peers)
        for peer in self.peers:
            self.node.send_message(peer, 'calculate-' + str(m.ceil(points/count)))
        received = 0
        points_inside = 0
        while received < count:
            if not self.node.messages.empty():
                message = self.node.messages.get()
                split = message['contents'].split('-')
                print(split[0])
                if split[0] == 'results':
                    points_inside += int(split[1])
                    received += 1
        # inside / total = pi / 4
        pi = (float(points_inside) / points) * 4
        # It works!
        print('calc Pi=', pi)

    def __helper(self):
        self.helping.set()
        while self.helping.is_set():
            if not self.node.messages.empty():
                message = self.node.messages.get()
                split = message['contents'].split('-')
                if split[0] == 'calculate':
                    print('calc Processing', split[1], 'points for', message['sender'])
                    points_inside = 0
                    for i in range(int(split[1])):
                        # Generate random x, y in [0, 1].
                        x = r.random()**2
                        y = r.random()**2
                        # Increment if inside unit circle.
                        if m.sqrt(x + y) < 1.0:
                            points_inside += 1
                    print('send results')
                    self.node.send_message(message['sender'], 'results-'+str(points_inside))



if __name__ == '__main__':
    cmd = BNode()
    cmd.do_init()
    cmd.prompt = ''
    cmd.cmdloop('')
