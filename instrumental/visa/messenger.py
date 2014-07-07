from codecs import encode, decode
import socket
import errno

class Messenger(object):
    def __init__(self, socket, is_server=False):
        self.socket = socket
        self.buf = ''
        self.message_id = None
        self.is_server = is_server
        self.current_id = 0

    def send(self, message):
        # 'message' is a BYTES object and may contain non-ascii 'characters'
        if not isinstance(message, bytes):
            raise TypeError("message must be bytes object, not unicode string")

        if self.is_server:
            # Server needs to recall the id of the message it received
            id = self.message_id
        else:
            # Client needs to remember the id of the message it is sending
            self.message_id = id = self.current_id
            self.current_id += 1

        header = encode('{}:{}:'.format(len(message), id), 'utf-8')
        try:
            self.socket.sendall(header + message)
            self.last_msg_id = id
        except socket.error as e:
            if e.errno == errno.ECONNRESET:
                # Should probably do some useful error handling for these
                print("Error: Connection reset by peer")
            elif e.errno == errno.EPIPE:
                print("Error: Broken pipe")
            raise e

    def recv(self):
        """ Returns a single received message, blocking if necessary.

        If self.is_server is False, it uses the message id from the previous
        'send()' call to verify that we're receiving the right response. If the
        id doesn't match, skip the message and try the next one. This feature
        exists for when a server is unable to reply within the FakeVISA
        timeout, but replies after it. We need some way to clear out this
        response.

        If self.is_server is True, we save the message id for our later reply.
        """
        if not self.buf:
            # If buffer is empty, block for an incoming message
            self.buf = self.socket.recv(1024)
            if not self.buf:
                # We received empty buffer, let's return it
                # this usually (always?) means the stream was closed
                return self.buf

        # msg_len is length in bytes of the message which follows the 1st colon
        msg_len, msg_id, self.buf = self.buf.split(b':', 2)
        msg_len = int(decode(msg_len, 'utf-8'))
        msg_id = int(decode(msg_id, 'utf-8'))

        while len(self.buf) < msg_len:
            # We don't yet have the full message, keep listening for data
            self.buf += self.socket.recv(1024)

        message = self.buf[:msg_len]
        self.buf = self.buf[msg_len:]

        if self.is_server:
            # Save message id for later
            self.message_id = msg_id
        else:
            if msg_id < self.message_id:
                # Try again
                message = self.recv()
            elif msg_id > self.message_id:
                raise Exception("Never received a response from the server")
                
        return message
