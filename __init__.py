# coding=utf-8

"""

Python delayed task baseclass with strong focus on security. Follows the threading/subprocess api pattern. Uses couchdb as a backend (taskqueue).

This source code is licensed under the GNU General Public License,
Version 3. http://www.gnu.org/licenses/gpl-3.0.en.html

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
import crypto_api
import mailer
import traceback
import StringIO
from couchdb_api import SaveObject


def send_error(displayfrom, subject, body):
    """ send email error report to administrator
    @param displayfrom:
    @param subject:
    @param body:
    """

    debug = True
    if debug:
        print "== send error =="
        print subject
        print
        print body
        print
        return
    settings = {}
    email = mailer.Email(settings)
    email.reply_email = email.to_email = ("erik@a8.nl", displayfrom)
    email.subject = subject
    email.body = mailer.Body(body, txt=body)
    email.send()


def make_p_callable(the_callable, params):
    """ takes a function with parameters and converts it to a pickle
    @param the_callable:
    @param params:
    """

    p_callable = {"marshaled_bytecode": marshal.dumps(the_callable.func_code),
                  "pickled_name": pickle.dumps(the_callable.func_name),
                  "pickled_arguments": pickle.dumps(the_callable.func_defaults),
                  "pickled_closure": pickle.dumps(the_callable.func_closure), "params": params}
    return p_callable

class CryptoTask(SaveObject):
    """ async execution, where the function 'run' is securely saved in couchdb. """

    # the pickled executable

    m_callable_p64s = None

    # result after execution

    m_result = ""

    # execution done

    m_done = False

    # was the execution successful, false if an exception in the callable occurred

    m_success = False

    # class created

    m_created_time = None

    # time execution started

    m_start_execution = None

    # time execution stopped

    m_stop_execution = None

    # the signature of the pickled executable

    m_signature_p64s = None

    # max time the execution may run

    m_max_lifetime = 60 * 5

    # progress counter

    m_progress = 0

    # total for progress calculation

    m_total = 100

    # time in seconds the execution will take, for progress calculation

    m_expected_duration = 0

    # execution is running

    m_running = False

    # the object type

    m_command_object = None

    # public keys of the command queue

    public_keys = []

    # id of the user to which the task belongs

    m_crypto_user_object_id = None

    # data to operate on

    m_process_data = None

    # delete the task when completed

    m_delete_me_when_done = True

    def __init__(self, dbase, object_id=None, crypto_user_object_id=None):
        super(CryptoTask, self).__init__(dbase=dbase,
                                         comment="this object represents a command and stores intermediary results",
                                         object_id=object_id)

        self.m_command_object = self.get_object_type()
        self.object_type = "CryptoTask"
        self.m_created_time = time.time()
        self.m_crypto_user_object_id = crypto_user_object_id

    def display(self):
        """ display string """

        return self.m_command_object + " / " + self.object_id

    def save(self, *argc, **argv):
        """
            save the task
        @param argc:
        @param *argc:
        @param argv:
        @param **argv: 
        """

        super(CryptoTask, self).save(*argc, **argv)
        return self.object_id

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
        """ verify the callable, unpack, and call
        @param p_callable:
        """

        the_callable = types.FunctionType(marshal.loads(p_callable["marshaled_bytecode"]), globals(),
                                          pickle.loads(p_callable["pickled_name"]),
                                          pickle.loads(p_callable["pickled_arguments"]),
                                          pickle.loads(p_callable["pickled_closure"]))

        return the_callable(self, *p_callable["params"])

    def set_execution_timer(self):
        """ start the timer """

        self.m_start_execution = time.time()
        self.m_running = True
        self.save()

    def execute(self):
        """ set up structures and execute """

        if self.m_done:
            return
        if not self.m_callable_p64s:
            raise Exception("There is no callable saved in this object")
        if not self.m_start_execution:
            self.set_execution_timer()

        #noinspection PyBroadException,PyUnusedLocal
        try:
            result = self.execute_callable(self.m_callable_p64s)
            success = True
        except Exception, exc:
            sioexc = StringIO.StringIO()
            traceback.print_exc(file=sioexc)
            success = False
            result = sioexc.getvalue()

        self.load()
        self.m_result = result
        self.m_success = success
        self.m_running = False
        self.m_callable_p64s = None
        self.m_done = True
        self.m_stop_execution = time.time()
        self.save()
        if self.m_delete_me_when_done:
            self.delete()

    #noinspection PyUnusedLocal,PyUnresolvedReferences
    def start(self, *argc, **argv):
        """ start the asynchronous excution of this task
        @param *argc:
        @param **argv:
        @param argc:
        @param argv:
        """
        argv = argv

        if not self.m_crypto_user_object_id:
            raise Exception("CryptoTask:start -> no crypto_user_object_id given")

        #noinspection PyUnresolvedReferences
        dict_callable = make_p_callable(self.run, argc)
        dict_callable["m_command_object"] = self.m_command_object

        self.m_callable_p64s = dict_callable

        self.save()

    def join(self, progressf=None):
        """ wait for completion of this task
        @param progressf:
        """

        if not self._dbase:
            raise Exception("No valid database avila")
        last_progress = 0
        while self.load():
            if self.m_done:
                return
            if progressf:
                if self.m_progress:
                    if last_progress != self.m_progress:
                        progressf(self.object_id, self.m_progress, self.m_total)
                        last_progress = self.m_progress
            time.sleep(0.5)
        return
