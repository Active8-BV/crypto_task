# coding=utf-8
"""
unit test for cryptotask
"""
__author__ = 'rabshakeh'
import unittest
from __init__ import *
from couchdb_api import gds_delete_item_on_key, gds_get_scalar_list


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
        import couchdb_api
        self.all_servers = ['http://127.0.0.1:5984/']
        self.db_name = 'crypto_task_test'
        self.dbase = couchdb_api.ServerConfig(self.db_name, memcached_server_list=["127.0.0.1:11211"])

    def tearDown(self):
        """
        tearDown
        """
        for keyid in gds_get_scalar_list(self.db_name, member="keyval"):
            gds_delete_item_on_key(self.db_name, keyid)

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
    print "tests.py:79", 'crypto_task unittest'
    unittest.main()
