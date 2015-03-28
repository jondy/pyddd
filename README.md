Pyddd
=====

Pyddd is a super-GDB debugger which could debug python scripts as the
same way to debug c program line by line in the same inferior.

Download
========

Since Pyddd is written in the Python language, you need to install
Python (the required version is at least 2.6).

You can also download a snapshot from the Git repository:

* as a `.tar.gz <https://github.com/jondy/pyddd/archive/master.tar.gz>`__
  file or
* as a `.zip <https://github.com/jondy/pyddd/archive/master.zip>`_ file

Installation
============

Linux
-----

* First, you need build GDB with Python.
* Then, unzip Pyddd package, build pyddd-ipa.

.. code-block:: bash

   $ gcc -g -I/usr/include/python2.7 -Wl,-lpthread -shared -o \
   python-ipa.so ipa.c

Windows
-------

* First, you need install Cygwin.
* Next, build GDB with Python in Cygwin.
* Then, unzip Pyddd package, open Cygwin Terminal, build pyddd-ipa.

.. code-block:: bash

   $ gcc -g -I/usr/include/python2.7 -Wl,-lpthread -shared -o \
   python-ipa.dll ipa.c

Quick Start
===========

After installation, invoke the command prompt, go to the directory
with Pyddd installed and run those commands:

.. code-block:: bash

  $ gdb
  (gdb) source init.gdb
  (gdb) exec-file python
  (gdb) py-file foo.py
  (gdb) py-start

For more, see pyddd.rst and rationale.rst

