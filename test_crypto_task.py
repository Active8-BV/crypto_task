# coding=utf-8
"""

Crypto task test program. Add some tasks to the database.

This source code is licensed under the GNU General Public License,
Version 3. http://www.gnu.org/licenses/gpl-3.0.en.html

Copyright (C)

Erik de Jonge <erik@a8.nl>
Actve8 BV
Rotterdam
www.a8.nl

"""

import threading
import xmlrpclib
from couchdb_api import CouchDBServer, CouchNamedCluster
from __init__ import CryptoTask


def _get_private_key():
    """ the private key of the queue worker """

    return """  -----BEGIN RSA PRIVATE KEY-----
                MIIEogIBAAKCAQEAuPUGtdCh4bYHVb+mTnZ+GIo8h2Yl8NmlW08QjKs0Y5XDnI99
                tYenjFilXUJNquqJN3TvGxv4jgJOcZZQ4hSFY2s49iB6PxDsF48j5BCFPkKwSpri
                qsK0ZIuhpM71hb5JgSMDnJ/UQmwnA+sGsIaAJRR7UNfa6lmKf7Ld54o/H62UYypI
                msSLB0SEC4apm9Camg+vz9r8EOONdGZJznYW4RltCVw3223jC1KPxK/EpMVs8kXg
                1TPpeWqVwYZvMcyiF+NfquHxCqVtZNEufb30yOq4DPS4lqYRO6sXVFSAdV4ilyn6
                k/ju95yklW3odPRBVGrp66bgFUQ7+1EGzNf/EQIDAQABAoIBAAz/Apqx7z4J6VgI
                IGpw/wlAZWJqNg5HbMwOsS4BNawtsNIGbyHbR1WgQPZdm1GAK2YfLFHuVDe+R77J
                fiN0p67FsPnybESULtK09yOmWYZ3byW+3mB7T+ukuBX5iNz98vJFAJL31BVavh8T
                W6P5v3VbjBKxKCvBYO76JYeIekkCbX7VssWN7sFLyoELMwIzudTgQ0j/LU8IbDtF
                bqGQnvNOkbed3qbWjOWMJjd19BFZzjOjSguHAgulZ3hRNiOwuCePmE8fQTSOq1MX
                4x4WtQuz4sc03jPMg3sVksEAwXBvWnW4j4uTarbECezdPV20MLKWN2UztQIjCHxQ
                ZNixXEECgYEAvIuCB+hKNhdtRxKXm1qc22OqIWa90DVlAI9Ms4izyO05YheSekME
                RvNxqSeQ3gbmFIiQKDeVOhoQGTDVeMvWSdl/vFqyVJdlMqqU1w31NoFNW/uLffjv
                hObtCKK6Hx+78+ssVPgHSFrQ+ZCXqEFy1QkguGM6Tj8CVeS+n1nMs3kCgYEA+yDq
                mHZmTTJoydnf4FBIQic3BFyivcYpevSvMJho8J48KCznsIwrznQ2v2M9gKT+x5Jg
                Lt6aihbysLnKkJ2BnFP5BSuhgBveHdU91K+rN3JslDXmHvMsYxqznXoYGqqzT3eC
                1Hck8ibJvVBgfqJE3H2a6ehQbbYDC6Yd0bxp6lkCgYBF+DvUNWc89aqvIn4ywAjP
                /geIB7nPR9FoyMU9JzEZErgl5/uK9c3jirqWfMFtNAA0hI2C70Wo3z00LAQ8pOCs
                XVPjEYF2lQyQJe/Ac0SZ6phL12jn4fb5Sj2S49jQbhVxKsgz7Cu/tTwyMW+mmEtG
                NfH3m5NqsEVsnMwFFO07eQKBgBwYXqaX+HIChb6vZWCPGsZr5LfUNVDN7q4W2dKx
                +muRCGHmRDV4OR5r2gQnciYGT4q8UY5s0RVJ4/TplEQBmxKGQoHVk8flVkA4Lyaw
                UJNvdb5PGWO1CO49eoLPugqhtlXZpQVoHvYIaOGJMIJ6XQHd+4rXtsfPaR/Qgd2J
                GsBhAoGANUugVuSRog0y6KiMSkMuky4/Uj7ChKnfLosuSss3FkntBdwfk7AXUlUM
                bLMIX/aIr9zebk811WuPAc0TpcmoAykEF8fEn0wcHuF8F2bq4X6MNQjEbjcQrkK4
                S0tILBdmRDMfHKf8UNsFr1K3o4+PmRmAt1RTU9+QmZ/h5YZEkYM=
                -----END RSA PRIVATE KEY-----""".strip()


class Add(CryptoTask):
    """ add two numbers but take a long time """

    m_expected_duration = 0

    def get_private_key(self):
        """ required method, to encrypt and sign data """

        return _get_private_key()

    def run(self, val1, val2):
        """ run for random seconds, update duration during runtime to enable progress monitoring
        @param val1:
        @param val2:
        """

        import random

        duration = random.randint(1, 3)

        self.load()
        self.m_expected_duration = duration
        self.save()

        # better import locally, not sure if worker has everything

        import time

        time.sleep(duration)
        return val1 + val2


class AddCrash(CryptoTask):
    """ this task raises an exception """

    def get_private_key(self):
        """ required method, to encrypt and sign data """

        return _get_private_key()

    #noinspection PyUnusedLocal
    def run(self, val1, val2):
        """ divide by zero exception
        @param val1:
        @param val2:
        """

        val1 = 5 / 0
        return val1 + val2


def progress_callback(oid, progress, total):
    """ callback function for the join method
    @param oid:
    @param progress:
    @param total:
    """

    dbase_name = "command_test"
    named_cluster = CouchNamedCluster(dbase_name, ["http://127.0.0.1:5984/"])
    dbase = CouchDBServer(named_cluster)
    command = CryptoTask(dbase, object_id=oid)
    command.load()
    print command.display(), "->", progress, "of", total


class AddTest(threading.Thread):
    """ run a test """

    def __init__(self, cnt, result):
        self.cnt = cnt
        self.result = result
        threading.Thread.__init__(self)

    def run(self):
        """
            run the test
        """
        dbase_name = "command_test"
        named_cluster = CouchNamedCluster(dbase_name, ["http://127.0.0.1:5984/"])
        dbase = CouchDBServer(named_cluster)
        addc = Add(dbase)
        print "start: " + addc.display()
        addc.start(self.cnt, 1)
        print "waiting for task completion"
        addc.join(progress_callback)
        print "result: " + addc.display() + " --> " + str(addc.m_result)
        self.result.append(str(addc.m_result))
        addc.delete()


def main():
    """ open couchdb and add commands, wait for completion """

    dbase_name = "command_test"
    cluster = ["http://127.0.0.1:5984/"]
    named_cluster = CouchNamedCluster(dbase_name, cluster)
    dbase = CouchDBServer()
    dbase.create(named_cluster)

    server = xmlrpclib.ServerProxy('http://localhost:8001')

    # delete all previous commands
    for task in Add(dbase).collection():
        if task.m_done:
            print "result:", task.display() + " --> " + str(task.m_result)
            print "deleting: ", task.display()
        task.delete()

    task_list = []
    result_list = []
    testitems = 2

    for i in range(0, testitems):
        addtest = AddTest(i, result_list)
        addtest.start()
        task_list.append(addtest)

    server.process_tasks(dbase_name, cluster)

    for test in task_list:
        test.join()

    result_list = [int(i) for i in result_list]
    result_list.sort()
    for i in result_list:
        print i

    print
    print "testok?", [i + 1 for i in range(0, testitems)] == result_list
    print

    add_ex = AddCrash(dbase)
    print "start: " + add_ex.display()
    add_ex.start(5, 4)
    server.process_tasks(dbase_name, cluster)
    add_ex.join()

    print "exception test, succes is false", add_ex.m_success
    add_ex.delete()

if __name__ == "__main__":
    main()
