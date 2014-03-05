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
import pickle
import uuid
import subprocess
import inflection
from Crypto import Random
import mailer
from couchdb_api import SaveObjectGoogle, console, console_warning, DocNotFoundException, MemcachedServer


def send_error(displayfrom, subject, body):
    """
    @type displayfrom: str
    @type subject: str
    @type body: str
    """
    if "lycia" in subprocess.check_output("hostname"):
        console_warning("send_error", subject, body)
        return

    class Settings(object):
        """
        Settings
        """
        email_from_email = ""
        email_from = ""

    settings = Settings()
    settings.email_from_email = "erik@a8.nl"
    settings.email_from = displayfrom
    settings.email_host = "mail.active8.nl"
    settings.email_host_password = "48fi0b"
    settings.email_host_user = "erik@active8.nl"
    email = mailer.Email(settings)
    #email.reply_email = ("erik@a8.nl", displayfrom)
    email.to_email = ("sysadmin@a8.nl", "sysadmin@a8.nl")
    email.subject = subject
    #email.email_from = displayfrom
    email.body = mailer.Body(body, txt=body)
    email.send()


def make_p_callable(the_callable, params):
    """
    @type the_callable:
    @type params: tuple
    """
    p_callable = {"marshaled_bytecode": marshal.dumps(the_callable.func_code),
                  "pickled_name": pickle.dumps(the_callable.func_name),
                  "pickled_arguments": pickle.dumps(the_callable.func_defaults),
                  "pickled_closure": pickle.dumps(the_callable.func_closure),
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


class CryptoTask(SaveObjectGoogle):
    """
    CryptoTask
    """

    def __init__(self, serverconfig, crypto_user_object_id=None):
        """ async execution, where the function 'run' is securely run in a new process """
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
        # delete the task when completed
        self.m_delete_me_when_done = True
        self.object_type = "CryptoTask"
        self.m_command_object = self.get_object_type()
        self.m_created_time = time.time()
        self.m_crypto_user_object_id = crypto_user_object_id
        object_id = inflection.underscore(self.object_type) + "_" + str(uuid.uuid4().hex) + ":" + inflection.underscore(self.m_command_object).replace("_", "-")
        super(CryptoTask, self).__init__(serverconfig=serverconfig, comment="this object represents a command and stores intermediary results", object_id=object_id)
        self.object_type = "CryptoTask"
        self.m_extra_indexed_keys = ["m_done", "m_success", "m_created_time", "m_start_execution", "m_progress", "m_running", "m_command_object", "m_crypto_user_object_id", "m_delete_me_when_done"]

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
        get_data
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

    def display(self):
        """ display string """
        return self.m_command_object + " / " + self.object_id

    def set_high_priority(self):
        """
        10 is highest
        """
        self.m_priority = 10

    def set_medium_priority(self):
        """
        ordering task queue
        """
        self.m_priority = 5

    def total_execution_time(self):
        """ calculate total time """
        if self.m_stop_execution:
            return self.m_stop_execution - self.m_start_execution
        raise Exception("total_execution_time: m_stop_execution not set")

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
        @type p_callable: str
        """
        if not isinstance(p_callable, dict):
            return False
        the_callable = types.FunctionType(marshal.loads(p_callable["marshaled_bytecode"]), globals(), pickle.loads(p_callable["pickled_name"]), pickle.loads(p_callable["pickled_arguments"]), pickle.loads(p_callable["pickled_closure"]))
        return the_callable(self, *p_callable["params"])

    def execute(self):
        """ set up structures and execute """
        if self.m_done:
            return self.m_result

        if not self.m_callable_p64s:
            raise Exception("There is no callable saved in this object")

        self.m_start_execution = time.time()
        self.m_running = True
        Random.atfork()
        self.m_result = self.execute_callable(self.m_callable_p64s)
        self.m_success = True
        self.m_running = False
        self.m_callable_p64s = None
        self.m_done = True
        self.m_stop_execution = time.time()
        self.save(store_in_datastore=False)

    #noinspection PyMethodMayBeStatic
    def run(self):
        """
        @raise RunError:
        """
        console_warning("run not implemented, don not use this class directly but inherit and override run")
        return None

    #noinspection PyUnusedLocal
    def start(self, *argc, **argv):
        """
        start
        @param argc:
        @type argc:
        @param argv:
        @type argv:
        """
        if not self.m_crypto_user_object_id:
            raise Exception("CryptoTask:start no crypto_user_object_id given")

            #noinspection PyUnresolvedReferences
        dict_callable = make_p_callable(self.run, argc)
        dict_callable["m_command_object"] = self.m_command_object
        self.m_callable_p64s = dict_callable
        self.save(store_in_datastore=False)
        mc = MemcachedServer(self.get_serverconfig().get_memcached_server_list(), "taskserver")
        mc.set("runtasks", True)

    def join(self, progressf=None):
        """
        @type progressf: str, None
        """
        if not self.serverconfig:
            raise Exception("No valid database avila")

        last_progress = 0

        #noinspection PyExceptClausesOrder
        try:
            loaded = self.load()
        except DocNotFoundException:
            loaded = False
        except Exception, e:
            console_warning(str(e))
            loaded = False

        while loaded:
            if self.m_done:
                return

            if progressf:
                if self.m_progress:
                    if last_progress != self.m_progress:
                        progressf(self.object_id, self.m_progress, self.m_total)
                        last_progress = self.m_progress

            time.sleep(0.1)
            mc = MemcachedServer(self.get_serverconfig().get_memcached_server_list(), "taskserver")
            mc.set("runtasks", True)

            #noinspection PyExceptClausesOrder
            try:
                loaded = self.load()
            except DocNotFoundException:
                loaded = False
            except Exception, e:
                console("task already deleted", str(e))
                loaded = False

        return
