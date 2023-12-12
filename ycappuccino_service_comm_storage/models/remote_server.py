from ycappuccino_core.models.decorators  import Item, Property, Empty
from ycappuccino_storage.models.model import Model
from ycappuccino_core.decorator_app import App

import hashlib
import os

@Empty()
def empty():
    _empty = RemoteServer()
    _empty.id("remote_server")
    return _empty

@App(name="ycappuccino_service_comm_storage")
@Item(collection="remoteServers",name="remoteServer", plural="remoteServers",  secure_write=True, secure_read=True)
class RemoteServer(Model):
    def __init__(self, a_dict=None):
        super().__init__(a_dict)
        self._host = None
        self._port = None
        self._scheme = None

    @Property(name="scheme")
    def scheme(self, a_value):
        self._scheme = a_value

    @Property(name="host")
    def host(self, a_value):
        self._host = a_value

    @Property(name="port")
    def port(self, a_value):
        self._port = a_value

    def get_scheme(self):
        return self._scheme

    def get_host(self):
        return self._host

    def get_port(self):
        return self._port




empty()