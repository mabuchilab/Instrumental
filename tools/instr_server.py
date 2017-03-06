# -*- coding: utf-8 -*-
# Copyright 2015 Nate Bogdanowicz
"""
Instrumental server script. Allows other machines to access and control this machine's instruments.
"""
import threading
import logging as log
from instrumental.drivers.remote import ThreadedTCPServer, DEFAULT_PORT

if __name__ == "__main__":
    log.basicConfig(level=log.DEBUG, format='%(filename)s/%(funcName)s: %(message)s')
    HOST = ''  # Listen on all network interfaces
    server = ThreadedTCPServer((HOST, DEFAULT_PORT))
    ip, port = server.server_address
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = False
    server_thread.start()
