# coding=utf-8
"""
unit test for cryptotask
"""
__author__ = 'rabshakeh'
import unittest
import pycouchdb
from couchdb_api import CouchDBServer, CouchNamedCluster
from __init__ import *


class AddNumers(CryptoTask):
    """
    AddNumers
    """

    def run(self):
        """
        run
        """
        return self.m_process_data_p64s["v1"] + self.m_process_data_p64s["v2"]


class CryptoTaskTest(unittest.TestCase):
    """
    CryptoboTestCase
    """

    def setUp(self):
        """
        setUp
        """
        self.all_servers = ['http://127.0.0.1:5984/']
        self.db_name = 'crypto_task_test'

        for server in self.all_servers:
            if self.db_name in pycouchdb.Server(server):
                pycouchdb.Server(server).delete(self.db_name)

        for server in self.all_servers:
            if self.db_name not in pycouchdb.Server(server):
                pycouchdb.Server(server).create(self.db_name)

        self.named_cluster = CouchNamedCluster(self.db_name, self.all_servers, [])
        self.dbase = CouchDBServer(db_named_cluster=self.named_cluster, memcached_server_list=[])

    def tearDown(self):
        """
        tearDown
        """
        for server in self.all_servers:
            if self.db_name in pycouchdb.Server(server):
                pycouchdb.Server(server).delete(self.db_name)

    def test_task(self):
        """
        test_task
        """
        task = AddNumers(self.dbase, "user_1234")
        with self.assertRaisesRegexp(TypeError, "NoneType' object has no attribute '__getitem__'"):
            task.run()

        task.m_process_data_p64s = {"v1": 5, "v2": 5}
        result = task.run()
        self.assertEqual(result, 10)
        task.start()
        task2 = CryptoTask(self.dbase, "user_1234")
        task2.load(object_id=task.object_id)
        task2.execute()
        task3 = CryptoTask(self.dbase, "user_1234")
        task3.load(object_id=task.object_id)
        self.assertEqual(task3.m_result, 10)
        task4 = CryptoTask(self.dbase, "user_1234")
        task4.load(object_id=task.object_id)
        result_again = task4.execute()
        self.assertEqual(result_again, 10)
        task3.delete()
        task5 = CryptoTask(self.dbase, "user_1234")
        task5.load(object_id=task.object_id)
        self.assertIsNone(task5.execute())


if __name__ == '__main__':
    print "tests.py:86", 'crypto_task unittest'
    unittest.main()
