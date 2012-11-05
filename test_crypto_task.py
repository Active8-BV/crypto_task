# pylint: disable-msg=C0103
# pylint: enable-msg=C0103
# tempfile regex format
#
#!/usr/bin/python
# -*- coding: utf-8 -*-

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

from couchdb_api import CouchDBServer
from __init__ import CryptoTask
from argparse import ArgumentParser

class Add(CryptoTask):
    """ this task raises an exception """

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
