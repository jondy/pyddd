Pyddd
=====

Pyddd is a super-GDB debugger which could debug python scripts as the
same way to debug c program line by line in the same inferior.

Download
========

You can also download a snapshot from the Git repository:

* as a `.tar.gz <https://github.com/jondy/pyddd/archive/master.tar.gz>`__
  file or
* as a `.zip <https://github.com/jondy/pyddd/archive/master.zip>`__ file

Installation
============

Since Pyddd is written in the Python language, you need to install
Python (the required version is at least 2.6).

Linux
-----

* Rebuild GDB with Python and reinstall it.

.. code-block:: bash

  $ tar xzf gdb-7.8.1.tar.gz
  $ cd gdb-7.8.1
  $ ./configure --with-python=python --with-babeltrace=no \
    --enable-tui=no --enable-host-shared
  $ make

* Extract Pyddd package.
* Build pyddd-ipa.

.. code-block:: bash

  $ gcc -g -I/usr/include/python2.7 -Wl,-lpthread -shared -o \
    python-ipa.so ipa.c

Windows
-------

* Install Cygwin.
* Rebuild GDB with Python in Cygwin and reinstall it.

.. code-block:: bash

  $ tar xzf gdb-7.8.1.tar.gz
  $ cd gdb-7.8.1
  $ ./configure --with-python=python --with-babeltrace=no \
    --enable-tui=no --enable-host-shared
  $ make

* Unzip Pyddd package.
* Open Cygwin Terminal, build pyddd-ipa.

.. code-block:: bash

  $ gcc -g -I/usr/include/python2.7 -Wl,-lpthread -shared -o \
    python-ipa.dll ipa.c

Quick Start
===========

After installation, invoke the command prompt, go to the directory
in which Pyddd installed and run those commands:

.. code-block:: bash

  $ gdb
  (gdb) source init.gdb
  (gdb) py-exec-file python
  (gdb) py-file foo.py
  (gdb) py-start

For more, see pyddd.rst and rationale.rst

