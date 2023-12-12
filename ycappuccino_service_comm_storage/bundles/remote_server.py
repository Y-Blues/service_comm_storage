#app="all"
from ycappuccino_core import executor_service, framework
from ycappuccino_core.api import IActivityLogger, IConfiguration, YCappuccino
import logging
from pelix.ipopo.decorators import ComponentFactory, Requires, Validate, Invalidate, Property, Provides, Instantiate, BindField, UnbindField
import pelix.http
from jsonrpclib.SimpleJSONRPCServer import SimpleJSONRPCServer
from ycappuccino_core.executor_service import Callable
from jsonrpclib.threadpool import ThreadPool
from ycappuccino_core.decorator_app import Layer
from ycappuccino_service_comm.api import IRemoteClientFactory, IRemoteServer
from ycappuccino_service_comm_storage.models.remote_server import RemoteServer
from ycappuccino_storage.api import IManager

_logger = logging.getLogger(__name__)

service = None

def call(a_params):
    """ call service"""
    global service
    service.execute(a_params)

def ask_service():
    """" return list of service """
    global service
    service.ask_service()


class ThreadRemoteServer(Callable):

    def __init__(self, a_service):
        super(ThreadRemoteServer, self).__init__("ThreadRemoteServer")
        self._service = a_service
        self._pool = ThreadPool(max_threads=10, min_threads=0)
        self._server = None
    # Setup the thread pool: between 0 and 10 threads

    def run(self):

        self._server = SimpleJSONRPCServer((self._service.get_host(), self._service.get_port()))
        self._server.set_notification_pool(self._pool)
        self._server.register_function(call)
        #self._server.register_function(test)

        self._server.serve_forever()
        try:
            self._server.serve_forever()
        finally:
            # Stop the thread pool (let threads finish their current task)
            self._pool.stop()
            self._server.set_notification_pool(None)

@ComponentFactory('RemoteServerServer-Factory')
@Provides(specifications=[IRemoteServer.name, YCappuccino.name])
@Requires("_log", IActivityLogger.name, spec_filter="'(name=main)'")
@Requires("_config", IConfiguration.name)
@Requires('_components', YCappuccino.name,optional=True,aggregate=True)
@Requires('_manager_remote_server', IManager.name,spec_filter="'(item_id=remoteServer)'")
@Requires('_remote_client_factory', IRemoteClientFactory.name)
@Instantiate("RemoteServerServer")
@Layer(name="ycappuccino_service_comm_storage")
class RemoteServerServer(IRemoteServer):

    def __init__(self):
        super().__init__()
        global service
        service = self
        self._components = None
        self._map_component = {}
        self._threadExecutor = None
        self._manager_remote_server = None
        self._remote_client_factory = None
        self._host = framework.app_params["service_comm.host"] if framework.app_params is not None and "service_comm.host" in framework.app_params else "localhost"
        self._scheme = framework.app_params["service_comm.scheme"] if framework.app_params is not None and "service_comm.scheme" in framework.app_params else "http"
        self._port = framework.app_params["service_comm.port"] if framework.app_params is not None and "service_comm.port" in framework.app_params else 8080
        self._log = None

    def ask_service(self):
        print("test")

    @BindField("_components")
    def bind_components(self, field, a_service, a_service_reference):
        for interface in a_service_reference.get_properties()["objectClass"]:
            if interface not in self._map_component:
                self._map_component[interface] = []
            self._map_component[interface].append(a_service)

    def get_host(self):
        return self._host

    def get_port(self):
        return self._port

    @UnbindField("_components")
    def unbind_components(self, field, a_service, a_service_reference):
        for interface in a_service_reference.get_properties()["objectClass"]:
            self._map_component[interface].remove(a_service)

    def check_and_create_remote_server(self):
        w_subject = self.get_token_subject("bootstrap", "system")
        w_offset = 0
        none = False
        list_ids = []
        while not none:
            list_remote_server = self._manager_remote_server.get_many("remoteServer", {"offset":w_offset, "size":50}, w_subject )
            none = len(list_remote_server) <= 0
            for remote_server in list_remote_server:
                if remote_server.get_host() != self._host or remote_server.get_port() != self._port or remote_server.get_scheme() != self._scheme:
                    list_ids.append(remote_server._id)
                    self._remote_client_factory.create.create_remote_client(remote_server)
            w_offset=w_offset+50
        # delete all remote client that doesn't work
        for w_id  in list_ids:
            if w_id not in self._remote_client_factory.get_list_remote_client().keys():
                self._manager_remote_server.remove("remoteServer", w_id, w_subject)

        w_server = RemoteServer()
        w_server.id("{}_{}_{}".format(self._scheme,self._host,self._port))
        w_server.scheme(self._scheme)
        w_server.host(self._host)
        w_server.port( self._port)

        self._manager_remote_server.up_sert_model(w_server._id, w_server, w_subject)

    @Validate
    def validate(self, context):
        self._log.info("RemoteServer validating")
        self.check_and_create_remote_server()
        self._threadExecutor = executor_service.new_executor("ThreadRemoteServer")
        _callable = ThreadRemoteServer(self)
        self._threadExecutor.submit(_callable);
        self._log.info("RemoteServer validated")

    @Invalidate
    def invalidate(self, context):
        self._log.info("RemoteServer invalidating")
        self._threadExecutor.shutdown()
        self._log.info("RemoteServer invalidated")
