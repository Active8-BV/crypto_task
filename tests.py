# coding=utf-8
"""
unit test for cryptotask
"""
__author__ = 'rabshakeh'
import unittest


def add_paths():
    """
    add_paths
    """
    import os
    import sys

    sys.path.append(os.path.normpath(os.path.join(os.getcwd(), "..")))


add_paths()
from __init__ import *
from couchdb_api import gds_delete_item_on_key, gds_get_scalar_list, ServerConfig, gds_delete_namespace


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
        self.db_name = 'crypto_task_test'
        self.dbase = ServerConfig(self.db_name, memcached_server_list=["127.0.0.1:11211"])

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

    def test_set_get_data(self):
        """
        test_set_get_data
        """
        gds_delete_namespace(self.dbase, self.db_name)
        task = AddNumers(self.dbase, "user_1234")
        task.set_data("hello", "world")
        self.assertEqual({'arg0': 'hello', 'arg1': 'world'}, task.m_process_data_p64s)

        task.set_data(v1="hello", v2="world")
        self.assertEqual({'v1': 'hello', 'v2': 'world'}, task.m_process_data_p64s)

        task.set_data("foo", "bar", v1="hello", v2="world")
        self.assertEqual({'arg0': 'foo', 'arg1': 'bar', 'v2': 'world', 'v1': 'hello'}, task.m_process_data_p64s)

        def f(p1, p2, v2='', v1=''):
            """
            @type p1: str
            @type p2: str
            @type v2: str
            @type v1: str
            """
            self.assertEqual("foobarhelloworld", p1+p2+v1+v2)

        args, kwargs =task.get_data_as_param()
        apply(f, args, kwargs)
        self.assertEqual("hello", task.get_data("v1"))
        with self.assertRaisesRegexp(TaskException, "get_data, key not found"):
            task.get_data("helli")
        with self.assertRaisesRegexp(TaskException, "set_data, no params given"):
            task.set_data()
        with self.assertRaisesRegexp(TaskException, "get_data_as_param, no data set"):
            task.get_data_as_param()

        a = 1
        b = ["hello", "world"]
        c = 3.0
        d = [{"foo":"bar"}, 2]
        e = "hello"
        task.set_data(self.dbase, a, b, c, d, e)
        task.save()
        task2 = AddNumers(self.dbase, "user_1234")
        task2.load(object_id=task.object_id)
        sc, a1, b1, c1, d1, e1= task2.get_data_as_param(True)
        self.assertEqual(a, a1)
        self.assertEqual(b, b1)
        self.assertEqual(c, c1)
        self.assertEqual(d, d1)
        self.assertEqual(e, e1)

        self.assertEqual(self.dbase.get_namespace(), sc.get_namespace())


if __name__ == '__main__':
    print "tests.py:136", 'crypto_task unittest'
    unittest.main(failfast=True)
