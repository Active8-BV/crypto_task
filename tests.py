# coding=utf-8
"""
unit test for cryptotask
"""
__author__ = 'rabshakeh'
import unittest
from __init__ import *
from couchdb_api import gds_delete_item_on_key, gds_get_scalar_list, gds_get_key_name


class AddNumers(CryptoTask):
    """
    AddNumers
    """

    def run(self):
        """
        run
        """
        return self.m_process_data_p64s["v1"] + self.m_process_data_p64s["v2"]

#noinspection PyPep8Naming


class CryptoTaskTest(unittest.TestCase):
    """
    CryptoboTestCase
    """

    def setUp(self):
        """
        setUp
        """
        import couchdb
        import couchdb_api
        self.all_servers = ['http://127.0.0.1:5984/']
        self.db_name = 'crypto_task_test'

        for server in self.all_servers:
            if self.db_name in list(couchdb.Server(server)):
                couchdb.Server(server).delete(self.db_name)

        for server in self.all_servers:
            if self.db_name not in list(couchdb.Server(server)):
                couchdb.Server(server).create(self.db_name)

        self.dbase = couchdb_api.CouchDBServer(self.db_name, self.all_servers, memcached_server_list=["127.0.0.1:11211"])

    def tearDown(self):
        """
        tearDown
        """
        for keyid in gds_get_scalar_list(self.db_name, member="keyval"):
            print "tests.py:54", gds_get_key_name(keyid)
            gds_delete_item_on_key(self.db_name, keyid)

    def test_many_task(self):
        """
        test_many_task
        """
        tasks = []

        for i in range(0, 100):
            task = AddNumers(self.dbase, "user_1234")
            task.m_delete_me_when_done = False
            task.m_process_data_p64s = {"v1": 5,
                                        "v2": 5}

            task.start()
            tasks.append(task)

        self.cronjob = subprocess.Popen(["/usr/bin/python", "cronjob.py"], cwd="/Users/rabshakeh/workspace/cryptobox/crypto_taskworker")

        for t in tasks:
            t.join()
            self.assertEqual(t.m_result, 10)
        self.cronjob.terminate()

    def test_task(self):
        """
        test_task
        """
        task = AddNumers(self.dbase, "user_1234")
        with self.assertRaisesRegexp(TypeError, "NoneType' object has no attribute '__getitem__'"):
            task.run()

        task.m_process_data_p64s = {"v1": 5,
                                    "v2": 5}

        result = task.run()
        self.assertEqual(result, 10)
        task.start()
        task2 = CryptoTask(self.dbase, "user_1234")
        task2.load(object_id=task.object_id)
        task2.execute()
        task2.save()
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
        with self.assertRaisesRegexp(Exception, "There is no callable saved in this object"):
            self.assertIsNone(task5.execute())


if __name__ == '__main__':
    print "tests.py:112", 'crypto_task unittest'
    unittest.main()
