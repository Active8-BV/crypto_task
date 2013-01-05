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

import xmlrpclib
from couchdb_api import CouchDBServer, CouchNamedCluster
from __init__ import CryptoTask

class Add(CryptoTask):
    """ add two numbers but take a long time """

    def run(self, val1, val2):
        """ run for random seconds, update duration during runtime to enable progress monitoring
        @param val1:
        @param val2:
        """

        def add(a, b):
            return a + b

        return self.run_critical_section(add, val1, val2)


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

    task = Add(dbase, 1)
    task.start(1, 2)

    server.process_tasks(dbase_name, cluster)

if __name__ == "__main__":
    main()
