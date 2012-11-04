# pylint: disable-msg=C0103
# pylint: enable-msg=C0103
# tempfile regex format
#
# pylint: disable-msg=C0111
# missing docstring
#
# pylint: disable-msg=W0232
# no __init__ method
#
# pylint: disable-msg=R0903
# to few public methods
#
# DISABLED_ylint: disable-msg=R0201
# method could be a function
#
#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import marshal
import types
import pickle
import crypto_api
import mailer
import traceback
import StringIO
from couchdb_api import CouchDBServer, SaveObject
from argparse import ArgumentParser

def send_error(subject, body):
    debug = True
    if debug:
        print "== send error =="
        print subject
        print
        print body
        print
        return

    email = mailer.Email()
    email.reply_email = email.to_email = ("erik@a8.nl", "Cryptobox")
    email.subject = subject
    email.body = mailer.Body(body, txt=body)
    email.send()


def make_p_callable(the_callable, params):
    p_callable = {}
    p_callable["marshaled_bytecode"] = marshal.dumps(the_callable.func_code)
    p_callable["pickled_name"] = pickle.dumps(the_callable.func_name)
    p_callable["pickled_arguments"] = pickle.dumps(the_callable.func_defaults)
    p_callable["pickled_closure"] = pickle.dumps(the_callable.func_closure)
    p_callable["params"] = params
    return p_callable


class CallableVerifyError(Exception):
    pass


class NoCallable(Exception):
    pass


class PivateKeyNotImplemented(Exception):
    pass


def get_public_key_cryptobox():
    return """  -----BEGIN PUBLIC KEY-----
                MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuPUGtdCh4bYHVb+mTnZ+
                GIo8h2Yl8NmlW08QjKs0Y5XDnI99tYenjFilXUJNquqJN3TvGxv4jgJOcZZQ4hSF
                Y2s49iB6PxDsF48j5BCFPkKwSpriqsK0ZIuhpM71hb5JgSMDnJ/UQmwnA+sGsIaA
                JRR7UNfa6lmKf7Ld54o/H62UYypImsSLB0SEC4apm9Camg+vz9r8EOONdGZJznYW
                4RltCVw3223jC1KPxK/EpMVs8kXg1TPpeWqVwYZvMcyiF+NfquHxCqVtZNEufb30
                yOq4DPS4lqYRO6sXVFSAdV4ilyn6k/ju95yklW3odPRBVGrp66bgFUQ7+1EGzNf/
                EQIDAQAB
                -----END PUBLIC KEY-----""".strip()

class NoDatabase(Exception):
    pass

class CBCommand(SaveObject):
    m_callable_p64s = None
    m_result = ""
    m_done = False
    m_success = False
    m_info = {}
    m_created_time = None
    m_start_execution = None
    m_stop_execution = None
    m_signature_p64s = None
    m_max_lifetime = 60 * 5
    m_progress = 0
    m_total = 100
    m_expected_duration = 0
    m_running = False
    m_command_object = None
    public_keys = []

    def __init__(self, dbase=None, object_id=None):
        if object_id:
            self.object_id = object_id
        self.m_command_object = self.get_object_type()
        self.public_keys.append(get_public_key_cryptobox())
        self.object_type = "CBCommand"
        super(CBCommand, self).__init__(dbase=dbase, comment="this object represents a command and stores intermediary results")
        self.m_created_time = time.time()

    def save(self, *argc, **argv):
        #if len(self.collection())>
        #raise Exception("The command queue is full")
        super(CBCommand, self).save(*argc, **argv)
        return self.object_id

    def total_execution_time(self):
        if self.m_stop_execution:
            return self.m_stop_execution - self.m_start_execution
        raise Exception("total_execution_time: m_stop_execution not set")

    def execution_time(self):
        if not self.m_start_execution:
            return 0
        return time.time() - self.m_start_execution

    def life_time(self):
        return time.time() - self.m_created_time

    def execute_callable(self, p_callable, signature):
        verified = False
        for public_key in self.public_keys:
            if crypto_api.verify(public_key, pickle.dumps(str(p_callable["params"]) + str(p_callable["marshaled_bytecode"])), signature):
                verified = True
                break
        if not verified:
            raise CallableVerifyError("The callable could not be verified")

        the_callable = types.FunctionType(marshal.loads(p_callable["marshaled_bytecode"]), globals(), pickle.loads(p_callable["pickled_name"]),
                                          pickle.loads(p_callable["pickled_arguments"]), pickle.loads(p_callable["pickled_closure"]))
        return the_callable(self, *p_callable["params"])

    def set_execution_timer(self):
        self.m_start_execution = time.time()
        self.m_running = True
        self.save()

    def execute(self):
        if self.m_done:
            return
        if not self.m_callable_p64s:
            raise NoCallable("There is no callable saved in this object")
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
        self = self
        raise PivateKeyNotImplemented("get_private_key_cryptobox is not implemented, should return private key in RSA form")

    def join(self, progressf=None):
        if not self._dbase:
            raise NoDatabase("No valid database avila")
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

class Add(CBCommand):
    def run(self, val1, val2):
        self = self
        val1 = 5 / 0
        return val1 + val2

class Test(SaveObject):
    m_val1 = "yes"


def main():
    parser = ArgumentParser()
    parser.add_argument("-w", "--workers", dest="workers", help="start N worker process", metavar="N")
    args = parser.parse_args()
    args = args

    dbase_name = "command_test"
    dbase = CouchDBServer(dbase_name)

    test = Test(dbase)
    for ttt in test.collection():
        ttt.delete()
    test.save()

    addc = Add(dbase)

    for i in addc.collection():
        i.delete()

    addc.start(5, 4)

    for i in addc.collection():
        i.execute()
        print "run", i.running_time()
        print "life", i.life_time()
        print "exec", i.execution_time()
        i.delete()




if __name__ == "__main__":
    main()
