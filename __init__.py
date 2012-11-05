# pylint: disable-msg=C0103
# pylint: enable-msg=C0103
# tempfile regex format
#
#!/usr/bin/python
# -*- coding: utf-8 -*-

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
    """ send email error report to administrator """

    debug = True
    if debug:
        print "== send error =="
        print subject
        print
        print body
        print
        return

    email = mailer.Email()
    email.reply_email = email.to_email = ("erik@a8.nl", displayfrom)
    email.subject = subject
    email.body = mailer.Body(body, txt=body)
    email.send()


def make_p_callable(the_callable, params):
    """ takes a function with parameters and converts it to a pickle """

    p_callable = {}
    p_callable["marshaled_bytecode"] = marshal.dumps(the_callable.func_code)
    p_callable["pickled_name"] = pickle.dumps(the_callable.func_name)
    p_callable["pickled_arguments"] = pickle.dumps(the_callable.func_defaults)
    p_callable["pickled_closure"] = pickle.dumps(the_callable.func_closure)
    p_callable["params"] = params
    return p_callable


def get_public_key_application():
    """ the public key of the application, the queue worker has the private key """

    return """  -----BEGIN PUBLIC KEY-----
                MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuPUGtdCh4bYHVb+mTnZ+
                GIo8h2Yl8NmlW08QjKs0Y5XDnI99tYenjFilXUJNquqJN3TvGxv4jgJOcZZQ4hSF
                Y2s49iB6PxDsF48j5BCFPkKwSpriqsK0ZIuhpM71hb5JgSMDnJ/UQmwnA+sGsIaA
                JRR7UNfa6lmKf7Ld54o/H62UYypImsSLB0SEC4apm9Camg+vz9r8EOONdGZJznYW
                4RltCVw3223jC1KPxK/EpMVs8kXg1TPpeWqVwYZvMcyiF+NfquHxCqVtZNEufb30
                yOq4DPS4lqYRO6sXVFSAdV4ilyn6k/ju95yklW3odPRBVGrp66bgFUQ7+1EGzNf/
                EQIDAQAB
                -----END PUBLIC KEY-----""".strip()


class CryptoTask(SaveObject):
    """ async execution, where the function 'run' is securely saved in couchdb. """

    # the pickled executable

    m_callable_p64s = None

    # result after execution

    m_result = ""

    # execution done

    m_done = False

    # was the execution succesfull, false if an exception in the callable occured

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

    # time in seconds the excution will take, for progress calculation

    m_expected_duration = 0

    # excution is running

    m_running = False

    # the object type

    m_command_object = None

    # public keys of the command queue

    public_keys = []

    def __init__(self, dbase=None, object_id=None):
        if object_id:
            self.object_id = object_id
        self.m_command_object = self.get_object_type()
        self.public_keys.append(get_public_key_application())
        self.object_type = "CryptoTask"
        super(CryptoTask, self).__init__(dbase=dbase, comment="this object represents a command and stores intermediary results")
        self.m_created_time = time.time()

    def display(self):
        """ display string """

        return self.m_command_object + " / " + self.object_id

    def save(self, *argc, **argv):
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

    def execute_callable(self, p_callable, signature):
        """ verify the callable, unpack, and call """

        verified = False
        for public_key in self.public_keys:
            if crypto_api.verify(public_key, pickle.dumps(str(p_callable["params"]) + str(p_callable["marshaled_bytecode"])), signature):
                verified = True
                break
        if not verified:
            raise Exception("The callable could not be verified")

        the_callable = types.FunctionType(marshal.loads(p_callable["marshaled_bytecode"]), globals(), pickle.loads(p_callable["pickled_name"]),
                                          pickle.loads(p_callable["pickled_arguments"]), pickle.loads(p_callable["pickled_closure"]))
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

        # general exception
        # pylint: disable-msg=W0703

        result = None
        success = False
        try:
            result = self.execute_callable(self.m_callable_p64s, self.m_signature_p64s)
            success = True
        except Exception, exc:
            exc = exc
            sioexc = StringIO.StringIO()
            traceback.print_exc(file=sioexc)
            success = False
            result = sioexc.getvalue()

        # pylint: enable-msg=W0703

        self.load()
        self.m_result = result
        self.m_success = success
        self.m_running = False
        self.m_callable_p64s = None
        self.m_done = True
        self.m_stop_execution = time.time()
        self.save()

    def start(self, *argc, **argv):
        """ start the asynchronous excution of this task """

        argv = argv

        # no member found
        # pylint: disable-msg=E1101

        dict_callable = make_p_callable(self.run, argc)
        dict_callable["m_command_object"] = self.m_command_object

        # pylint: enable-msg=E1101

        self.m_signature_p64s = crypto_api.sign(self.get_private_key(), pickle.dumps(str(dict_callable["params"]) + str(dict_callable["marshaled_bytecode"])))

        # no member found
        # pylint: disable-msg=E1101

        self.m_callable_p64s = dict_callable

        # pylint: enable-msg=E1101

        self.save()

    def get_private_key(self):
        """ get private key of the execution engine """

        self = self
        raise Exception("get_private_key is not implemented, should return private key in RSA form")

    def join(self, progressf=None):
        """ wait for completion of this task """

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
