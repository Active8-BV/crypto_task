# coding=utf-8
"""

Crypto task test program. Add some tasks to the database.

This source code is property of Active8 BV
Copyright (C)

Erik de Jonge <erik@a8.nl>
Actve8 BV
Rotterdam
www.a8.nl

"""

import xmlrpclib
from couchdb_api import CouchDBServer, CouchNamedCluster
from __init__ import CryptoTask, send_error

class Add(CryptoTask):
    """ add two numbers but take a long time """

    def run(self, val1, val2):
        """ run for random seconds, update duration during runtime to enable progress monitoring
        @param val1:
        @param val2:
        """

        def add(a, b):
            return a + b

        return add(val1, val2)


def main():
    """ open couchdb and add commands, wait for completion """

    dbase_name = "command_test"
    cluster = ["http://127.0.0.1:5984/"]
    named_cluster = CouchNamedCluster(dbase_name, cluster)
    dbase = CouchDBServer()
    dbase.create(named_cluster)

    server = xmlrpclib.ServerProxy('http://localhost:8001')

    task = Add(dbase, 1)
    task.start(1, 2)

    server.process_tasks(dbase_name, cluster)

if __name__ == "__main__":
    send_error("error", "een error", "hello world")
    #main()
