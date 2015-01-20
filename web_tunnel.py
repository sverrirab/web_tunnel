# web_tunnel - see https://github.com/sverrirab/web_tunnel
#
# Generic socket tunnel.  Code is based from (permissive license):
# http://voorloopnul.com/blog/a-python-proxy-in-less-than-100-lines-of-code/
# Please see LICENSE file for more detail.
#
# This adds the possibility to automatically replace host header on the fly.
# That feature should only be used for (very) simple http requests (no https support).
#
import argparse
import re
import select
import socket
import sys
import time

__author__ = 'sab@keilir.com'

BUFFER_SIZE = 4096
DELAY = 0.01
HTTP_HEADER_RE = re.compile(
    "[GET|POST|HEAD|PUT|DELETE|CONNECT].*\r\n[H|h][O|o][S|s][T|t]:(.*?)\r\n.*\r\n\r\n",
    re.MULTILINE + re.DOTALL)


class Tunnel:
    input_list = []
    channel = {}

    def __init__(self, local_address, remote_address, replace_hostname=None, verbose=False):
        self.local_address = local_address
        self.remote_address = remote_address
        self.replace_hostname = replace_hostname
        self.verbose = verbose
        self.socket = None
        self.data = None

    def main_loop(self):
        ssocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        ssocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        ssocket.bind(self.local_address)
        ssocket.listen(16)
        self.socket = ssocket
        if self.verbose:
            print "Listening on %s" % repr(self.local_address)

        self.input_list.append(self.socket)
        while 1:
            time.sleep(DELAY)
            inputready, outputready, exceptready = select.select(self.input_list, [], [])
            for self.s in inputready:
                if self.s == self.socket:
                    self.on_accept()
                    break

                self.data = self.s.recv(BUFFER_SIZE)
                if len(self.data) == 0:
                    self.on_close()
                    break
                else:
                    self.on_recv()

    def connect(self):
        forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            forward.connect(self.remote_address)
            return forward
        except socket.error as e:
            print e
            return False

    def on_accept(self):
        forward = self.connect()
        clientsock, clientaddr = self.socket.accept()
        if forward:
            if self.verbose:
                print "%s has connected" % repr(clientaddr)
            self.input_list.append(clientsock)
            self.input_list.append(forward)
            self.channel[clientsock] = forward
            self.channel[forward] = clientsock
        else:
            print "Can't establish connection with remote server.",
            print "Closing connection with client side: %s" % repr(clientaddr)
            clientsock.close()

    def on_close(self):
        if self.verbose:
            print "%s has disconnected" % repr(self.s.getpeername())
        self.input_list.remove(self.s)
        self.input_list.remove(self.channel[self.s])
        out = self.channel[self.s]
        self.channel[out].close()  # equivalent to do self.s.close()
        self.channel[self.s].close()
        del self.channel[out]
        del self.channel[self.s]

    def on_recv(self):
        data = self.data
        if self.replace_hostname:
            header = HTTP_HEADER_RE.match(data)
            if header:
                old_host = header.group(1)
                if self.verbose:
                    print "Found HTTP header, changing %s to %s" % (old_host.strip(), self.replace_hostname)
                data = data[:header.start(1)] + " " + self.replace_hostname + data[header.end(1):]

        if self.verbose > 1:
            print "- " * 39
            print data
            print " -" * 39

        self.channel[self.s].send(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simple transparent HTTP proxy (web tunnel)")
    parser.add_argument("-a", "--local-address", dest="laddr", help="Local interface to bind to", default="localhost")
    parser.add_argument("-p", "--local-port", dest="lport", help="Local port to open", type=int, default=8880)
    parser.add_argument("-r", "--replace-hostname", dest="replace_hostname", help="Replace hostname in http requests")
    parser.add_argument("-v", "--verbose", action="count", help="Increase output verbosity")
    parser.add_argument("address", help="Address of remote machine to forward to")
    parser.add_argument("port", help="Port of remote machine to forward to", type=int)

    args = parser.parse_args()

    server = Tunnel((args.laddr, args.lport), (args.address, args.port), args.replace_hostname, args.verbose)
    try:
        server.main_loop()
    except KeyboardInterrupt:
        print "Server Stopped"
        sys.exit(1)