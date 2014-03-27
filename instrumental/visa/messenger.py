from codecs import encode, decode

class Messenger(object):
    def __init__(self, socket):
        self.socket = socket
        self.buf = ''

    def send(self, message):
        # 'message' is a BYTES object and may contain non-ascii 'characters'
        header = encode('{}:'.format(len(message)), 'utf-8')
        self.socket.sendall(header + message)

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
