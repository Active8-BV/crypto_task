crypto_task
============

Python delayed task baseclass with strong focus on security. Follows the threading/subprocess api pattern. Uses couchdb as a backend (taskqueue).

Scalable so it can be used in a webcluster with a couchdb cluster.

Works in conjunction with crypto_taskworker

License
===========

This source code is licensed under the GNU General Public License,
Version 3. http://www.gnu.org/licenses/gpl-3.0.en.html

Copyright (C)

Erik de Jonge <erik@a8.nl>
Actve8 BV
Rotterdam
www.a8.nl


Use case
===========

Delayed excution task, for example to encrypt data. Sort of a task queue. But with complete control over where the data is at any time and who is allowed to add data to
the task queue.

The server verifies task via public private key signing.

Commands are modeled like threads or processes.

The data is stored in couchdb


Use case
===========

You define a class object with a run method, this method contains your work.

```python
class Add(CryptoTask):
    """ add two numbers """

    def run(self, val1, val2):
        return val1 + val2
```

The server is only allowed to run code from trusted clients so we have to private a private key to the base class.

This private key is used to make a RSA signature of the function code and the function parameters.

The server has a list of public keys, the authorized clients sort of speak.

```python
class Add(CryptoTask):
    """ add two numbers but take a long time """

    def get_private_key(self):
        """ required method, to encrypt and sign data """

        return get_private_key_cryptobox()

    def run(self, val1, val2):
        return val1 + val2
```

The baseclass has to variables

```python
m_progress
m_total
```

which can be read by a progress callback to show a progressbar for example

You can also specify how long the taks will take with an expected duration.

```python
class Add(CryptoTask):
    """ add two numbers but take a long time """

    m_expected_duration = 0

    def get_private_key(self):
        """ required method, to encrypt and sign data """

        return get_private_key_cryptobox()

    def run(self, val1, val2):
        """ run for random seconds, update duration during runtime to enable progress monitoring """

        import random
        duration = random.randint(1, 3)

        self.load()
        self.m_expected_duration = duration
        self.save()

        # better import locally, not sure if worker has everythign

        import time
        time.sleep(duration)
        self = self
        return val1 + val2
```

Make an instance of the class and start it.

```python
dbase_name = "command_test"
dbase = CouchDBServer(dbase_name)
addc = Add(dbase)
print "start: " + addc.display()
addc.start(self.cnt, 1)
```

This call immediatly returns.

You can wait for completion with the join function which also takes a callback for progress monitoring.

```python
        print "waiting for task completion"
        addc.join(progress_callback)
```

results are ready

```python
print "result: "+addc.display() + " --> " + str(addc.m_result)
```

and delete the command, commands are deleted after five minutes (if they are not running anymore)

```python
addc.delete()
```
