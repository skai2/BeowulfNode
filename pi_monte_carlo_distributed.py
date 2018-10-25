#!/usr/bin/env python3

from node import Node
import random as r
import math as m

def distributed_monte_carlo(node, points):
    # Number of darts that land inside.
    inside = 0
    # Total number of darts to throw.
    total = points
    # Iterate for the number of darts.
    for i in range(0, total):
        # Generate random x, y in [0, 1].
        x2 = r.random()**2
        y2 = r.random()**2
        # Increment if inside unit circle.
        if m.sqrt(x2 + y2) < 1.0:
            inside += 1

    # inside / total = pi / 4
    pi = (float(inside) / total) * 4

    # It works!
    print(pi)



class NodeCMD(Cmd):
    def do_init(self):
        """Initializes the node."""
        self.node = Node(debug=True)
        print('---- Pi Monte Carlo Node Started')

    def do_quit(self):
        """Terminates the node."""
        self.node.kill()
        raise SystemExit

    def do_calculate(self, args):
        args = args.split()
        if len(args) != 1:
            print('---- Invalid arguments!')
            return
        distributed_monte_carlo(self.node, int(args[0]))



if __name__ == '__main__':
    cmd = NodeCMD()
    cmd.do_init()
    cmd.prompt = ''
    cmd.cmdloop('')
