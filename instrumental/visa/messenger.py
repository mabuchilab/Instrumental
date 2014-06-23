from codecs import encode, decode
import socket
import errno

class Messenger(object):
    def __init__(self, socket):
        self.socket = socket
        self.buf = ''

    def send(self, message):
        # 'message' is a BYTES object and may contain non-ascii 'characters'
        if not isinstance(message, bytes):
            raise TypeError("message must be bytes object, not unicode string")
        header = encode('{}:'.format(len(message)), 'utf-8')
        try:
            self.socket.sendall(header + message)
        except socket.error as e:
            if e.errno == errno.ECONNRESET:
                # Should probably do some useful error handling for these
                print("Error: Connection reset by peer")
            elif e.errno == errno.EPIPE:
                print("Error: Broken pipe")
            raise e

    def recv(self):
        """ Returns a single received message, blocking if necessary """
        if not self.buf:
            # If buffer is empty, block for an incoming message
            self.buf = self.socket.recv(1024)
            if not self.buf:
                # We received empty buffer, let's return it
                # this usually (always?) means the stream was closed
                return self.buf

        # msg_len is length in bytes of the message which follows the 1st colon
        msg_len, self.buf = self.buf.split(b':', 1)
        msg_len = int(decode(msg_len, 'utf-8'))

        while len(self.buf) < msg_len:
            # We don't yet have the full message, keep listening for data
            self.buf += self.socket.recv(1024)

        message = self.buf[:msg_len]
        self.buf = self.buf[msg_len:]
        return message
