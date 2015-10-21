# -*- coding: utf-8 -*-
# Copyright 2015 Nate Bogdanowicz
"""
Support for instruments on remote servers.
"""

from __future__ import absolute_import, unicode_literals, print_function
import atexit
import socket
import struct
import logging as log
import cPickle as pickle

from . import instrument, list_instruments, Instrument
from .. import conf

# Python 2 and 3 support
try:
    import socketserver
except ImportError:
    import SocketServer as socketserver

DEFAULT_PORT = 28265

# Header format is:
# 1 unsigned byte - message id
# 8 unsigned bytes - message length in bytes (not including header)
STRUCT = struct.Struct('!BQ')


class RemoteError(Exception):
    pass


class RemoteTimeoutError(RemoteError):
    pass


class Messenger(object):
    """Low-level messenger used to send and receive discrete, numbered byte-level messages"""
    def __init__(self):
        self.leftover = None

    def _send_message(self, message, id):
        encoded = self.encode(message, id, len(message))
        try:
            self.sock.sendall(encoded)
        except socket.timeout:
            raise RemoteTimeoutError("Timed out while sending message data")
        except Exception as e:
            raise RemoteError("Socket error while sending message data: {}".format(str(e)))

    def _recv_message(self):
        if self.leftover:
            bytes_recd = len(self.leftover)
            chunks = [self.leftover]
        else:
            bytes_recd = 0
            chunks = []

        while bytes_recd < 9:
            try:
                chunk = self.sock.recv(4096)
            except socket.timeout:
                raise RemoteTimeoutError("Timed out while waiting for message data")
            except Exception as e:
                raise RemoteError("Socket error while waiting for message data: {}".format(str(e)))

            chunks.append(chunk)
            bytes_recd += len(chunk)
            if not chunk:
                if bytes_recd == 0:
                    return None
                raise RuntimeError("Socket connection ended unexpectedly")

        id, length = self.read_header(b''.join(chunks))

        while bytes_recd < length+9:
            try:
                chunk = self.sock.recv(4096)
            except socket.timeout:
                raise RemoteTimeoutError("Timed out while waiting for message data")
            except Exception as e:
                raise RemoteError("Socket error while waiting for message data: {}".format(str(e)))

            chunks.append(chunk)
            bytes_recd += len(chunk)
            if not chunk:
                raise RuntimeError("Socket connection ended unexpectedly")

        full_msg = b''.join(chunks)
        chunks = [full_msg[9+length:]]
        return full_msg[9:], id

    @staticmethod
    def encode(message, id, length):
        return STRUCT.pack(id, length) + message

    @staticmethod
    def decode(message):
        id, length = STRUCT.unpack(message[:9])
        return message[9:], id, length

    @staticmethod
    def read_header(message):
        id, length = STRUCT.unpack(message[:9])
        return id, length


class Session(object):
    """High-level session"""
    @staticmethod
    def serialize(obj):
        return pickle.dumps(obj)

    @staticmethod
    def deserialize(data):
        return pickle.loads(data)


class ClientMessenger(Messenger):
    def __init__(self, host, port):
        super(ClientMessenger, self).__init__()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(2.0)
        self.sock.connect((host, port))
        self.host = host
        self.curr_id = 0

    def make_request(self, request_bytes):
        """Send request bytes to the server, and return its response bytes"""
        id = self.curr_id
        self.curr_id = (self.curr_id + 1) % 256
        self._send_message(request_bytes, id)
        response_bytes, resp_id = self._recv_message()

        if resp_id != id:
            raise RuntimeError("Message IDs do not match")

        return response_bytes

    def close(self):
        self.sock.close()


class ClientSession(Session):
    def __init__(self, host, port, server):
        self.host = host
        self.port = port
        self.server = server
        try:
            self.messenger = ClientMessenger(host, port)
        except socket.timeout:
            raise RemoteTimeoutError("Could not connect to host at {}:{}; timed out".format(host, port))
        except Exception as e:
            raise RemoteError("Socket error while connecting to host: {}".format(str(e)))

    def close(self):
        self.messenger.close()

    def request(self, **message_dict):
        message = self.serialize(message_dict)
        response = self.messenger.make_request(message)
        response_obj = self.deserialize(response)
        if isinstance(response_obj, Exception):
            raise response_obj
        return response_obj

    def list_instruments(self):
        instr_list = self.request(command='list')
        for instr in instr_list:
            instr['server'] = self.server
        return instr_list

    def instrument(self, params):
        response = self.request(command='create', params=params)
        response._session = self
        return response

    def get_obj_attr(self, obj_id, attr):
        obj = self.request(command='attr', obj_id=obj_id, attr=attr)
        if isinstance(obj, RemoteObject):
            obj._session = self
        return obj

    def get_obj_item(self, obj_id, key):
        obj = self.request(command='item', obj_id=obj_id, key=key)
        if isinstance(obj, RemoteObject):
            obj._session = self
        return obj

    def get_obj_call(self, obj_id, *args, **kwargs):
        obj = self.request(command='call', obj_id=obj_id, args=args, kwargs=kwargs)
        if isinstance(obj, RemoteObject):
            obj._session = self
        return obj


class ServerMessenger(Messenger):
    """Server-side session representing a connection to a client"""
    def __init__(self, socket):
        super(ServerMessenger, self).__init__()
        self.sock = socket
        self.curr_id = None

    def listen(self):
        """Listen for an incoming byte message. Returns None if connection was closed"""
        full_msg = self._recv_message()
        if full_msg:
            msg, id = full_msg
            self.curr_id = id
            return msg
        return None

    def respond(self, response_bytes):
        """Respond (in bytes) to a message received via listen()"""
        if self.curr_id is None:
            raise Exception("Invalid message id. respond() must be used to respond to a "
                            "message received via listen()")
        self._send_message(response_bytes, self.curr_id)


class ServerSession(Session):
    def __init__(self, socket):
        self.command_handler = {
            'create': self.handle_create,
            'list': self.handle_list,
            'attr': self.handle_attr,
            'item': self.handle_item,
            'call': self.handle_call
        }
        self.messenger = ServerMessenger(socket)
        self.next_obj_id = 0
        self.obj_table = {}  # id -> object
        self.remote_obj_pairs = []  # (object, RemoteObject)

    def handle_create(self, request):
        params = request['params'].copy()
        params.pop('server')  # Needed to force instrument() to look locally
        inst = instrument(params)
        id = self.new_obj_id()
        self.obj_table[id] = inst
        remote_obj = RemoteInstrument(request['params'], id, None, dir(inst), repr(inst))
        self.remote_obj_pairs.append((inst, remote_obj))
        return remote_obj

    def handle_list(self, request):
        return list_instruments()

    def handle_attr(self, request):
        obj_id = request['obj_id']
        obj = self.obj_table[obj_id]
        return getattr(obj, request['attr'])

    def handle_item(self, request):
        obj_id = request['obj_id']
        obj = self.obj_table[obj_id]
        return obj[request['key']]

    def handle_call(self, request):
        obj_id = request['obj_id']
        obj = self.obj_table[obj_id]
        return obj(*request['args'], **request['kwargs'])

    def handle_none(self, request):
        return Exception("Unknown command")

    def new_obj_id(self):
        id = self.next_obj_id
        self.next_obj_id += 1
        return id

    def serialize(self, obj):
        parent_serialize = super(ServerSession, self).serialize

        # Don't try to serialize objects already in remote_obj_pairs
        for local_obj, remote_obj in self.remote_obj_pairs:
            if local_obj is obj:
                obj = remote_obj
                break

        try:
            bytes = parent_serialize(obj)
        except TypeError:
            bytes = parent_serialize(self.new_remote_obj(obj))
        return bytes

    def new_remote_obj(self, obj):
        new_id = self.new_obj_id()
        self.obj_table[new_id] = obj
        remote_obj = RemoteObject(new_id, dir(obj), repr(obj))
        self.remote_obj_pairs.append((obj, remote_obj))
        return remote_obj

    def handle_requests(self):
        while True:
            message_bytes = self.messenger.listen()
            if message_bytes is None:
                log.info("Received EOF, closing connection.")
                break

            request = self.deserialize(message_bytes)
            log.debug(request)
            command = request.pop('command')

            try:
                handler = self.command_handler.get(command, self.handle_none)
                response = handler(request)
            except Exception as e:
                log.exception(e)
                response = e

            self.messenger.respond(self.serialize(response))

        # Clean up before we exit
        for obj in self.obj_table.values():
            if isinstance(obj, Instrument):
                try:
                    obj.close()
                except:
                    pass


class ThreadedTCPRequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        log.info("Opening connection to client...")
        session = ServerSession(self.request)
        session.handle_requests()


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class RemoteObject(object):
    def __init__(self, id, dirlist, reprname, session=None):
        self._obj_id = id
        self._reprname = "<Remote {}>".format(reprname)
        self._session = session
        self._dirlist = dirlist

    def __enter__(self):
        return self.__getattr__('__enter__')()

    def __exit__(self, type, value, traceback):
        # Can't pickle a traceback object, so we don't send it, and hope for the best...
        return self.__getattr__('__exit__')(type, value, None)

    def __dir__(self):
        return self._dirlist

    def __repr__(self):
        return self._reprname

    def __getattr__(self, name):
        return self._session.get_obj_attr(self._obj_id, name)

    def __getitem__(self, key):
        return self._session.get_obj_item(self._obj_id, key)

    def __call__(self, *args, **kwargs):
        return self._session.get_obj_call(self._obj_id, *args, **kwargs)

    def __getstate__(self):
        return dict(_obj_id=self._obj_id, _session=self._session,
                    _dirlist=self._dirlist, _reprname=self._reprname)

    def __setstate__(self, dict):
        self.__dict__ = dict


class RemoteInstrument(RemoteObject, Instrument):
    def __init__(self, params, id, session, dirlist, reprname):
        super(RemoteInstrument, self).__init__(id, dirlist, reprname, session)
        self._param_dict = params

    def __getstate__(self):
        dict = super(RemoteInstrument, self).__getstate__()
        dict.update(_param_dict=self._param_dict)
        return dict


def client_session(server):
    """Get the session connected to `server`. Creates one if it doesn't exist yet."""
    if server in conf.servers:
        host = conf.servers[server]
    else:
        host = server

    split = host.rsplit(':', 1)
    if len(split) == 2:
        host = split[0]
        port = int(split[1])
    else:
        host = host
        port = DEFAULT_PORT

    if (host, port) not in client_session.sessions:
        client_session.sessions[(host, port)] = ClientSession(host, port, server)
    return client_session.sessions[(host, port)]
client_session.sessions = {}


@atexit.register
def _cleanup_sessions():
    for session in client_session.sessions.values():
        session.close()
