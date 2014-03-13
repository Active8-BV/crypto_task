# coding=utf-8
"""
unit test for cryptotask
"""
__author__ = 'rabshakeh'


def add_paths():
    """
    add_paths
    """
    import os
    import sys
    sys.path.append(os.path.normpath(os.path.join(os.getcwd(), "..")))


add_paths()
import unittest
from __init__ import *
from couchdb_api import ServerConfig, gds_delete_namespace
import threading


class AddNumers(CryptoTask):
    """
    AddNumers
    """

    def run(self, a, b):
        """
        @type a: int
        @type b: int
        """
        return a + b


class CryptoTaskTest(unittest.TestCase):
    """
    CryptoboTestCase
    """

    def setUp(self):
        """
        setUp
        """
        self.db_name = 'crypto_task_test'
        self.serverconfig = ServerConfig(self.db_name)
        self.serverconfig.rs_flush_namespace()

    def test_set_get_data(self):
        """
        test_set_get_data
        """
        gds_delete_namespace(self.serverconfig)
        task = AddNumers(self.serverconfig, "user_1234")
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
            self.assertEqual("foobarhelloworld", p1 + p2 + v1 + v2)

        args, kwargs = task.get_data_as_param()
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
        d = [{"foo": "bar"}, 2]
        e = "hello"
        task.set_data(self.serverconfig, a, b, c, d, e)
        task.save()
        task2 = AddNumers(self.serverconfig, "user_1234")
        task2.load(object_id=task.object_id)
        sc, a1, b1, c1, d1, e1 = task2.get_data_as_param(True)
        self.assertEqual(a, a1)
        self.assertEqual(b, b1)
        self.assertEqual(c, c1)
        self.assertEqual(d, d1)
        self.assertEqual(e, e1)
        self.assertEqual(self.serverconfig.get_namespace(), sc.get_namespace())

    def test_var(self):
        """
        test_var
        """
        task = AddNumers(self.serverconfig)

        with self.assertRaisesRegexp(TaskException, "start: no crypto_user_object_id set"):
            task.start(1, 1)

        task = AddNumers(self.serverconfig, "user_1234")

        with self.assertRaisesRegexp(TaskException, "get_data, no data set"):
            task.get_data("foo")

        with self.assertRaisesRegexp(TaskException, "get_data_as_param, no data set"):
            task.get_data_as_param()

    def test_task_run_not_implemented(self):
        """
        test_task_run_not_implemented
        """
        task = CryptoTask(self.serverconfig, "user_1234")

        with self.assertRaisesRegexp(TaskException, "no run method on class implemented"):
            task.execute()

    def test_task_run(self):
        """
        test_task_run
        """
        task = AddNumers(self.serverconfig, "user_1234")
        result = task.run(5, 6)
        self.assertEqual(result, 11)
        self.assertEqual(task.m_result, '')
        self.assertEqual(task.execution_time(), 0)

        with self.assertRaisesRegexp(TaskException, "total_execution_time: m_stop_execution not set"):
            task.total_execution_time()

        with self.assertRaisesRegexp(TaskException, "callable not dict"):
            #noinspection PyTypeChecker
            task.execute_callable(None)

    def test_task_execute(self):
        """
        test_task_execute
        """
        task = AddNumers(self.serverconfig, "user_1234")
        task.execute(5, 6)
        task.execute(5, 6)
        self.assertEqual(task.m_result, 11)
        self.assertTrue(task.total_execution_time() > 0)
        self.assertTrue(task.execution_time() > 0)
        self.assertTrue(task.life_time() > 0)

    def test_task_execute_save(self):
        """
        test_task_execute_save
        """
        task = AddNumers(self.serverconfig, "user_1234")
        task.start(5, 6)
        task2 = CryptoTask(self.serverconfig, "user_1234")
        task2.load(object_id=task.object_id)
        task2.execute()
        self.assertEqual(task2.m_result, 11)
        task3 = CryptoTask(self.serverconfig, "user_1234")
        task3.load(object_id=task.object_id)
        self.assertEqual(task3.m_result, 11)

    def test_task_execute_join(self):
        """
        test_task_execute_join
        """
        task = AddNumers(self.serverconfig, "user_1234")
        task.start(5, 6)
        task2 = CryptoTask(self.serverconfig, "user_1234")
        task2.load(object_id=task.object_id)
        task2.execute()
        task2.join()
        self.assertEqual(task2.m_result, 11)
        task3 = CryptoTask(self.serverconfig, "user_1234")

        with self.assertRaisesRegexp(TaskException, "could not load task"):
            task3.load(object_id=task.object_id)

    def test_task_execute_join_time_out(self):
        """
        test_task_execute_join2
        """
        task = AddNumers(self.serverconfig, "user_1234")
        task.start(5, 6)

        with self.assertRaisesRegexp(TaskException, "crypto_task_add-numers timed out"):
            task.join(max_wait_seconds=0.3)

    def test_task_execute_join_wait(self):
        """
        test_task_execute_join_wait
        """
        task = [AddNumers(self.serverconfig, "user_1234")]

        def execute():
            """
            execute
            """
            print "tests.py:206", "execute"
            task[0].execute(5, 6)

        threading.Timer(0.5, execute).start()
        task[0].join(max_wait_seconds=2)
        self.assertEqual(task[0].m_result, 11)


if __name__ == '__main__':  # pragma: no cover
    unittest.main(failfast=True)  # pragma: no cover
