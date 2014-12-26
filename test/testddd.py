"""
This script is used to test gdb user document.

It read test doc from ../rationale.rst, then replace the line like

    $(gdb) cmd

    with

    >>> pyddd.command ( cmd )

so doctest can run the gdb command and compare the output.

"""
import multiprocessing
import os
import re
import select
import socket
import subprocess
import sys
import threading
import time

PROMPT = '(gdb) '
DOCPREFIX = '>>> pyddd.command("'

args = './gdb.exe', '--data-directory=./', '--quiet', '-nx'

class PyDDD(object):

    BUFSIZE = 4096
    def __init__(self):
        super(PyDDD, self).__init__()
        self.sockets = socket.socketpair()
        self._gdb = subprocess.Popen(
            args,
            stdout=self.sockets[0],
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            )

    def start(self):
        # Clean output
        self.read_stdout()

    def stop(self):
        self.command('quit')

    def command(self, line):
        self._gdb.stdin.write(('%s\n' % line).encode())
        time.sleep(.5)
        self.read_stdout()

    def read_stdout(self):
        while select.select(self.sockets, [], [], .5)[0]:
            buf = self.sockets[1].recv(PyDDD.BUFSIZE)
            if buf.endswith(PROMPT):
                sys.stdout.write (buf[:-1])
                break
            sys.stdout.write (buf)

    def call(self, lines):
        p = subprocess.Popen(
            args,
            bufsize=PyDDD.BUFSIZE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.PIPE,
            )
        outdata, errdata = p.communicate(lines)
        print (outdata)

def make_test_file(src):
    filename = '~tmp%s~' % os.path.basename(src)
    with open(filename, 'w') as ft:
        with open(src, 'r') as fs:
            for line in fs.readlines():
                if line.strip().startswith(PROMPT):
                    ft.write(line[:-1].replace(PROMPT, DOCPREFIX))
                    ft.write('")\n')
                else:
                    ft.write(line)
    return filename

if __name__ == "__main__":
    import doctest
    pyddd = PyDDD()
    pyddd.start()
    # doctest.testmod()
    filename = '../rationale.rst'
    if os.path.exists(filename):
        tmpfile = make_test_file(filename)
        doctest.testfile(
            tmpfile,
            globs=globals(),
            optionflags=doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE,
            )
        os.remove(tmpfile)
    pyddd.stop()
