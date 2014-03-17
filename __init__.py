# coding=utf-8
"""
Python delayed task baseclass with strong focus on security. Follows the threading/subprocess api pattern. Uses couchdb as a backend (taskqueue).
This source code is property of Active8 BV
Copyright (C)
Erik de Jonge <erik@a8.nl>
Actve8 BV
Rotterdam
www.a8.nl
"""
import time
import marshal
import types
import cPickle
import uuid
import inflection
from Crypto import Random
from crypto_data import SaveObjectGoogle, console, RedisServer, RedisEventWaitTimeout, strcmp, handle_ex


def make_p_callable(the_callable, params):
    """
    @type the_callable:
    @type params: tuple
    """
    p_callable = {"marshaled_bytecode": marshal.dumps(the_callable.func_code),
                  "pickled_name": cPickle.dumps(the_callable.func_name),
                  "pickled_arguments": cPickle.dumps(the_callable.func_defaults),
                  "pickled_closure": cPickle.dumps(the_callable.func_closure),
                  "params": params}

    return p_callable


class RunError(Exception):
    """
    RunError
    """
    pass


class TaskSaveError(Exception):
    """
    TaskSaveError
    """
    pass


class TaskException(Exception):
    """
    TaskException
    """
    pass


class TaskTimeOut(Exception):
    """
    TaskTimeOut
    """
    pass


class CryptoTask(SaveObjectGoogle):
    """
    CryptoTask
    """

    def __init__(self, serverconfig, crypto_user_object_id=None, verbose=False):
        """ async execution, where the function 'run' is securely run in a new process """
        self.verbose = verbose
        # priority higher is sooner
        self.m_priority = 0
        # the pickled executable
        self.m_callable_p64s = None
        # result after execution
        self.m_result = ""
        # execution done
        self.m_done = False
        # was the execution successful, false if an exception in the callable occurred
        self.m_success = False
        # possible stored exception
        self.m_exception_pickle = None
        # stored exception base64
        self.m_b64_exception = ""
        # class created
        self.m_created_time = None
        # time execution started
        self.m_start_execution = None
        # time execution stopped
        self.m_stop_execution = None
        # the signature of the pickled executable
        self.m_signature_p64s = None
        # max time the execution may run
        self.m_max_lifetime = 60 * 5
        # progress counter
        self.m_progress = 0
        # total for progress calculation
        self.m_total = 100
        # time in seconds the execution will take, for progress calculation
        self.m_expected_duration = 0
        # execution is running
        self.m_running = False
        # the object type
        self.m_command_object = None
        # public keys of the command queue
        self.public_keys = []
        # id of the user to which the task belongs
        self.m_crypto_user_object_id = None
        # data to operate on
        self.m_process_data_p64s = None
        self.object_type = "CryptoTask"
        self.m_command_object = self.get_object_type()
        self.m_created_time = time.time()
        self.m_crypto_user_object_id = crypto_user_object_id
        object_id = inflection.underscore(self.object_type) + "_" + str(uuid.uuid4().hex) + ":" + inflection.underscore(self.m_command_object).replace("_", "-")
        super(CryptoTask, self).__init__(serverconfig=serverconfig, comment="this object represents a command and stores intermediary results", object_id=object_id)
        self.object_type = "CryptoTask"
        self.m_extra_indexed_keys = ["m_done", "m_success", "m_created_time", "m_start_execution", "m_progress", "m_running", "m_command_object", "m_crypto_user_object_id"]

    def set_data(self, *args, **kwargs):
        """
        @param args:
        @param kwargs:
        """
        cnt = 0
        self.m_process_data_p64s = {}

        for i in args:
            self.m_process_data_p64s["arg" + str(cnt)] = i
            cnt += 1

        for k in kwargs:
            self.m_process_data_p64s[k] = kwargs[k]
            cnt += 1

        if cnt == 0:
            raise TaskException("set_data, no params given")

    def get_data_as_param(self, only_args=False):
        """
        @type only_args: bool
        """
        if self.m_process_data_p64s is None:
            raise TaskException("get_data_as_param, no data set")

        args = []
        kwargs = {}
        cnt = 0

        for k in self.m_process_data_p64s:
            cnt += 1

            if k.startswith("arg"):
                args.append(self.m_process_data_p64s[k])
            else:
                kwargs[k] = self.m_process_data_p64s[k]

        if cnt == 0:
            raise TaskException("get_data_as_param, no data set")

        if only_args:
            return args
        return args, kwargs

    def get_data(self, key):
        """
        @type key: str
        """
        if self.m_process_data_p64s is None:
            raise TaskException("get_data, no data set")

        if key in self.m_process_data_p64s:
            return self.m_process_data_p64s[key]

        raise TaskException("get_data, key not found")

    def total_execution_time(self):
        """ calculate total time """
        if self.m_stop_execution:
            return self.m_stop_execution - self.m_start_execution
        raise TaskException("total_execution_time: m_stop_execution not set")

    def execution_time(self):
        """ calculate running time """
        if not self.m_start_execution:
            return 0

        return time.time() - self.m_start_execution

    def life_time(self):
        """ calculate life time of object """
        return time.time() - self.m_created_time

    def execute_callable(self, p_callable):
        """
        @type p_callable: dict
        """
        if not isinstance(p_callable, dict):
            raise TaskException("callable not dict")

        the_callable = types.FunctionType(marshal.loads(p_callable["marshaled_bytecode"]), globals(), cPickle.loads(p_callable["pickled_name"]), cPickle.loads(p_callable["pickled_arguments"]), cPickle.loads(p_callable["pickled_closure"]))
        return the_callable(self, *p_callable["params"])

    def execute(self, *args):
        """
        @param args:
        """
        if self.m_done:
            return self.m_result

        if not self.m_callable_p64s:
            self.save_callable(args)

        self.m_start_execution = time.time()
        self.m_running = True
        Random.atfork()
        try:
            self.m_result = self.execute_callable(self.m_callable_p64s)
            self.m_success = True
        except Exception, ex:
            excstr = handle_ex(ex, give_string=True)
            self.m_exception_pickle = excstr
            self.m_success = False
        finally:
            self.m_running = False
            self.m_callable_p64s = None
            self.m_done = True
            self.m_stop_execution = time.time()
            self.save(use_datastore=False)

    def save_callable(self, *argc):
        """
        @param argc:
        @type argc:
        """
        if hasattr(self, "run"):
            dict_callable = make_p_callable(self.run, *argc)
            dict_callable["m_command_object"] = self.m_command_object
            self.m_callable_p64s = dict_callable
            self.save(use_datastore=False)
        else:
            raise TaskException("no run method on class implemented")

    def start(self, *argc):
        """
        @param argc:
        @type argc:
        """
        if not self.m_crypto_user_object_id:
            raise TaskException("start: no crypto_user_object_id set")

        self.save_callable(argc)
        rs = RedisServer("taskserver", verbose=self.verbose)
        rs.list_push("tasks", self.object_id)
        rs.event_emit("runtasks", self.get_serverconfig().get_namespace())

    def human_object_name(self, object_name):
        """
        @type object_name: str
        """
        cnt = 0
        ot = object_name.replace(":", "_")
        ots = ot.split("_")
        ot = ""

        for e in ots:
            if cnt != 2:
                ot += e
                ot += "_"
            cnt += 1

        object_name = ot.rstrip("_")
        return object_name

    def join(self, max_wait_seconds=None):
        """
        @type max_wait_seconds: float, None
        """
        if self.m_done is True:
            self.delete(delete_from_datastore=False)
            return True

        rs = RedisServer("taskserver", verbose=self.verbose)

        def taskdone(taskid):
            """
            @type taskid: str
            """
            if self.verbose:
                console("taskdone", taskid, self.object_id)

            if strcmp(taskid, self.object_id):
                self.load()

                if self.m_done:
                    self.delete(delete_from_datastore=False)

                raise TaskException(self.m_exception_pickle)
            else:
                # keep waiting
                return True

        try:
            subscription = rs.event_subscribe("taskdone", taskdone)
            subscription.join(max_wait_seconds)
        except RedisEventWaitTimeout:
            object_name = self.human_object_name(self.object_id)
            raise TaskTimeOut(str(object_name) + " timed out")

        return True

    def load(self, object_id=None, serverconfig=None, force_load=False, use_datastore=True):
        """
        @type object_id: str, None
        @type serverconfig: ServerConfig, None
        @type force_load: bool
        @type use_datastore: bool
        """
        result = super(CryptoTask, self).load(object_id, serverconfig, force_load, use_datastore)

        if not result:
            raise TaskException("could not load task")
