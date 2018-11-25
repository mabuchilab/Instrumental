# -*- coding: utf-8 -*-
# Copyright 2015-2018 Nate Bogdanowicz
"""
Instrumental server script. Allows other machines to access and control this machine's instruments.
"""
import time
import threading
import logging
from instrumental.log import log_to_screen, DEBUG, WARNING
from instrumental.drivers.remote import ThreadedTCPServer, DEFAULT_PORT

if __name__ == "__main__":
    log_to_screen(level=DEBUG, fmt='[%(levelname)8s]%(filename)s/%(funcName)s: %(message)s')
    logging.getLogger('nicelib').setLevel(WARNING)

    HOST = ''  # Listen on all network interfaces
    server = ThreadedTCPServer((HOST, DEFAULT_PORT))
    ip, port = server.server_address
    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.daemon = True
    server_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    server.shutdown()
    server.server_close()
