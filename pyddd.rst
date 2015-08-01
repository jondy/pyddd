Python Debugger - PYDDD
=======================

*PYDDD* is a super-GDB debugger which could debug python scripts as
the same way to debug c program in the same inferior.

*PYDDD* extends some corresponding GDB commands with prefix "py-" used
to debug python scripts. For examble, `py-run`, `py-break`, `py-next`
etc. Besides, some commands like "continue" work both c and python.

Additionally, when debugging python extensions (written in c/c++),
*PYDDD* could show extra information of python. For example, print a
variable of PyObject* will show the value of both c pointer and python
type (a list or dict etc.). And frame will show both c frame and
python frame.

Before debugging, start GDB.

.. code-block:: bash

  $ cd /opt/pyddd
  $ gdb
  (gdb) source init.gdb
  (gdb) py-exec-file python

.. note::

  For Windows user, even GDB is running in the cygwin, you can also
  debug python scripts with native windows python by GDB :command:
  `file`

  .. code-block:: bat
  
    (gdb) py-exec-file C:/Python26/python.exe

After that, see below chapters to debug your python scripts.

Start Python Script
===================

.. _py-file:

* py-file filename

Use filename as main python script. All the functions, classes and
method in this script are read into memory. These symbols are used to
specify breakpoint locations.

* py-file string

Use string as -c parameter pass to python program to run.

* py-args arguments

Set arguments of python scripts.

* py-run

Use the py-run command to run your python script. You must first
specify python program by command :command: `py-exec-file`.

Here is an example::

  (gdb) py-exec-file C:/Python27/python.exe
  (gdb) py-exec-args -i
  (gdb) py-file foo.py
  (gdb) py-args -k
  (gdb) py-run

gdb will execute the following shell command::

  $ C:/Python27/python.exe -i foo.py -k

* py-start

Start python script and stop at the beginning of the main script.

  => py-tcatch call "<module>"

* py-exec-args arguments

Set arguments for run python, not for python scripts.


Stop Python Script
==================

Breakpoint Location
-------------------

* linenum

Specifies the line number linenum of the current source file.

* -offset
* +offset

Specifies the line offset lines before or after the current line.

* filename:linenum

Question: if code object in same file are equal in the different
          threads?

* function

function, or method of class. function is limited in the current
running script or main script if there is no script running.

Special function "__main__" stands for the start line of main script.

* function:offset

Offset must belong to the scope of function, otherwise it's invalid
location.

* filename:function

* filename:function:offset

A breakpoint with multiple locations is displayed in the breakpoint
table using several rows—one header row, followed by one row for each
breakpoint location. The number column for a location is of the form
breakpoint-number.location-number.

Each location can be individually enabled or disabled by passing
breakpoint-number.location-number as argument to the enable and
disable commands. Note that you cannot delete the individual locations
from the list, you can only delete the entire list of locations that
belong to their parent breakpoint.

Typically, you would set a breakpoint in a python script at the
beginning of your debugging session, when the symbols are not
available. After python is running, whenever any module is imported,
GDB reevaluates all the breakpoints. When any module is removed, all
breakpoints that refer to its symbols or source lines become pending
again.

This logic works for breakpoints with multiple locations, too.

Except for having unresolved address, pending breakpoints do not
differ from regular breakpoints. You can set conditions or commands,
enable and disable them and perform other breakpoint operations.

Breakpoint Command
------------------

The meaning of syntax symbol:

  [ ] means optional argument

  | means either of list arguments

* py-break [location]

Set a breakpoint at the given location, which can specify a function
name, a line number, filename:linenum, filename:function.

filename:. means to break on every function in this file.

If filename is a relative file name, then it will match any source
file name with the same trailing components.

When called without any arguments, break sets a breakpoint at the next
instruction to be executed in the selected stack frame.

* py-break [location] if cond

Set a breakpoint with condition cond; evaluate the expression cond
each time the breakpoint is reached, and stop only if the value is
nonzero.

Argument cond must be python expression, that is to say, no
convenience variables which start with $ could be used here.

If a breakpoint has a positive ignore count and a condition, the
condition is not checked. Once the ignore count reaches zero, GDB
resumes checking the condition.

* py-rbreak regex

Set breakpoints on all functions matching the regular expression
regex. This command sets an unconditional breakpoint on all matches,
printing a list of all breakpoints it set. Once these breakpoints are
set, they are treated just like the breakpoints set with the break
command. You can delete them, disable them, or make them conditional
the same way as any other breakpoint.

The syntax of the regular expression is the standard one used with
tools like grep. Note that this is different from the syntax used by
shells, so for instance foo* matches all functions that include an fo
followed by zero or more os. There is an implicit .* leading and
trailing the regular expression you supply, so to match only functions
that begin with foo, use ^foo.

It does nothing when no script is running, or no symbols loaded.

* py-rbreak file:regex

If rbreak is called with a filename qualification, it limits the
search for functions matching the given regular expression to the
specified file.

This can be used, for example, to set breakpoints on every function in
a given file:

(gdb) py-rbreak file.py:.*

The colon separating the filename qualifier from the regex may
optionally be surrounded by spaces.

* py-tbreak args

Set a breakpoint enabled only for one stop. The args are the same as
for the py-break command, and the breakpoint is set in the same way,
but the breakpoint is automatically deleted after the first time your
python script stops there.

* py-clear

Delete any breakpoints at the next instruction to be executed in the
selected stack frame. When the innermost frame is selected, this is a
good way to delete a breakpoint where your program just stopped.

* py-clear location

Delete any breakpoints set at the specified location.

* py-delete [range]

Delete the breakpoints of the breakpoint ranges specified as
arguments. If no argument is specified, delete all python breakpoints.

* py-disable [range]

Disable the specified breakpoints—or all breakpoints, if none are
listed. A disabled breakpoint has no effect but is not forgotten. All
options such as ignore-counts, conditions and commands are remembered
in case the breakpoint is enabled again later.

* py-enable [range]

Enable the specified breakpoints (or all defined breakpoints). They
become effective once again in stopping your program.

* py-enable once range

Enable the specified breakpoints temporarily. GDB disables any of
these breakpoints immediately after stopping your program.

* py-enable count n range

Enable the specified breakpoints temporarily. GDB records count with
each of the specified breakpoints, and decrements a breakpoint’s count
when it is hit. When any count reaches 0, GDB disables that
breakpoint. If a breakpoint has an ignore count, that will be
decremented to 0 before count is affected.

* py-enable delete range

Enable the specified breakpoints to work once, then die. GDB deletes
any of these breakpoints as soon as your program stops
there. Breakpoints set by the tbreak command start out in this state.

* py-condition bnum expression

Specify python expression as the break condition for python breakpoint
number bnum. After you set a condition, breakpoint bnum stops your
python script only if the value of expression is true.

GDB does not actually evaluate expression at the time the condition
command is given.

* py-condition bnum

Remove the condition from python breakpoint number bnum. It becomes an
ordinary unconditional breakpoint.

* py-ignore bnum count

Set the ignore count of python breakpoint number bnum to count. The
next count times the breakpoint is reached, your program’s execution
does not stop; other than to decrement the ignore count, GDB takes no
action.

To make the breakpoint stop the next time it is reached, specify a
count of zero.

Python Catchpoint Command
=========================

* py-catch exception *
* py-catch exception name

A python exception being raised. If an exception name is specified at
the end of the command (eg catch exception PyExc_RuntimeError), the
debugger will stop only when this specific exception is
raised. Otherwise, the debugger stops execution when any Python
exception is raised.

"unhandle" is special exception name which is used to catch the
exception not handled by the python script.

* py-catch call function

A function call to or return from python script. The function name is
compared with co_name of code object in python script.

'?' stands for one any character in argument name, argument name ends
with "*" matches any same prefix. Especially a single asterisk matches any
name. This command could reduce the performance.

The following command can be used to debug embedded python statements
in python script:

  (gdb) py-catch call <string>

* py-tcatch event

Set a catchpoint that is enabled only for one stop. The catchpoint is
automatically deleted after the first time the event is caught.

* py-catch info

Running Script Command
======================

* py-continue [ignore-count]

Resume script execution, at the address where your script last
stopped; any breakpoints set at that address are bypassed. The
optional argument ignore-count allows you to specify a further number
of times to ignore a breakpoint at this location; its effect is like
that of ignore.

The argument ignore-count is meaningful only when your script stopped
due to a breakpoint. At other times, the argument to continue is
ignored.

* py-step [count]

Continue running your script until control reaches a different source
line, then stop it and return control to GDB.

Also, the step command only enters a function of python extension if
there is line number information for the function. Otherwise it acts
like the next command.

If specify count, continue running as in step, but do so count
times. If a breakpoint is reached before count steps, stepping stops
right away.

* py-next [count]

Continue to the next source line in the current stack frame. This is
similar to step, but function calls that appear within the line of
code are executed without stopping. Execution stops when control
reaches a different line of code at the original stack level that was
executing when you gave the next command.

An argument count is a repeat count, as for step.

* py-finish

Continue running until just after function in the selected stack frame
returns. Print the returned value (if any).

* py-until

Continue running until a source line past the current line, in the
current stack frame, is reached. This command is used to avoid single
stepping through a loop more than once. This means that when you reach
the end of a loop after single stepping though it, until makes your
script continue execution until it exits the loop. In contrast, a next
command at the end of a loop simply steps back to the beginning of the
loop, which forces you to step through the next iteration.

until always stops your program if it attempts to exit the current
stack frame.

* py-until location

Continue running your script until either the specified location is
reached, or the current stack frame returns. This form of the command
uses temporary breakpoints, and hence is quicker than until without an
argument. The specified location is actually reached only if it is in
the current frame. This implies that until can be used to skip over
recursive function invocations.

* py-advance location

Continue running the script up to the given location. An argument is
required, which should be of one of invalid location forms. Execution
will also stop upon exit from the current stack frame. This command is
similar to until, but advance will not skip over recursive function
calls, and the target location doesn’t have to be in the same frame as
the current one.

Python Frame Command
====================

* py-frame [framespec]

The frame command allows you to move from one stack frame to another,
and to print the stack frame you select. The framespec may be either
the function name of the frame or the stack frame number. Recall that
frame zero is the innermost (currently executing) frame, frame one is
the frame that called the innermost one, and so on. The
highest-numbered frame is the one for PyEval_EvalFrameEx (or
PyEval_EvalFrame).

Without an argument, frame prints the current stack frame.

* py-select-frame

The select-frame command allows you to move from one stack frame to
another without printing the frame. This is the silent version of
frame.

* py-up n

Move n frames up the stack; n defaults to 1. For positive numbers n,
this advances toward the outermost frame, to higher frame numbers, to
frames that have existed longer.

* py-down n

Move n frames down the stack; n defaults to 1. For positive numbers n,
this advances toward the innermost frame, to lower frame numbers, to
frames that were created more recently. You may abbreviate down as do.

* py-bt

Print a backtrace of the entire stack: one line per frame for all
frames in the stack.

You can stop the backtrace at any time by typing the system interrupt
character, normally Ctrl-c.  backtrace n

* py-bt n

Similar, but print only the innermost n frames.

* py-bt -n

Similar, but print only the outermost n frames.

* py-bt-full
* py-bt-full n
* py-bt-full -n

Print the values of the local variables also. As described above, n
specifies the number of frames to print.

Python Data Command
===================

* py-print /r expression

Return str(PyObject*) or repr(PyObject*) if /r specified. If
expression is valid in current frame, print error.

* py-locals

Print all locals as str(PyObject*)

* py-locals varname

Look up the given local python variable name, and print it

* py-globals

Print all globals as str(PyObject*)

* py-globals varname

Look up the given global python variable name, and print it

Alert Python Variable
=====================

* py-set-var name expression
* py-set-var /global name expression

Show Debug Parameters
=====================

* py-info args
* py-info exec-args
* py-info main-script

Example
=======

beer.py queens.py life.py

(gdb) source init.gdb

(gdb) py-exec-file python
(gdb) py-file beer.py
(gdb) py-start


Known Issues
============

* Missing object entry in multi-thread script maybe.

It's possible we'll miss some code object when debug python
multi-thread scripts, if it matches the following conditios:

  - One thread stop by a breakpoint
  - Debug threads in non-stop mode
  - The other running thread is about to create new code object

Because we hook PyCode_New by command list of c breakpoint, in
non-stop mode, that c breakpoint is ignored. So when PyCode_New
called, no object entry is created.

Appendix
========

* How to find address of "trace_trampoline" from python library in gdb

$ gdb
(gdb) exec C:/Python27/python.exe
(gdb) set args -i
(gdb) b PyEval_EvalFrameEx
No symbol table is loaded.  Use the "file" command.
Make breakpoint pending on future shared library load? (y or [n]) y

Breakpoint 1 (PyEval_EvalFrameEx) pending.
(gdb) run
Starting program: /cygdrive/c/Python27/python.exe -i
[New Thread 4084.0xcc8]

Breakpoint 1, 0x1e00f363 in python27!PyEval_EvalFrameEx ()
   from /cygdrive/c/WINDOWS/system32/python27.dll
(gdb) call PyCFunction_GetFunction(PyDict_GetItemString(PyModule_GetDict(PyImport_AddModule("sys")), "settrace"))
$1 = 503847580
(gdb) p /x $1
$2 = 0x1e081a9c
(gdb) x /15i $2
   0x1e081a9c <python27!PyFloat_AsString+204>:
    call   0x1e067c6c <python27!PyThread_start_new_thread+180>
   0x1e081aa1 <python27!PyFloat_AsString+209>:  cmp    $0xffffffff,%eax
   0x1e081aa4 <python27!PyFloat_AsString+212>:
    jne    0x1e081aa9 <python27!PyFloat_AsString+217>
   0x1e081aa6 <python27!PyFloat_AsString+214>:  xor    %eax,%eax
   0x1e081aa8 <python27!PyFloat_AsString+216>:  ret
   0x1e081aa9 <python27!PyFloat_AsString+217>:  push   %esi
   0x1e081aaa <python27!PyFloat_AsString+218>:  mov    $0x1e1ed8c4,%esi
   0x1e081aaf <python27!PyFloat_AsString+223>:  cmp    %esi,0xc(%esp)
   0x1e081ab3 <python27!PyFloat_AsString+227>:
    jne    0x1e081abb <python27!PyFloat_AsString+235>
   0x1e081ab5 <python27!PyFloat_AsString+229>:  push   $0x0
   0x1e081ab7 <python27!PyFloat_AsString+231>:  push   $0x0
   0x1e081ab9 <python27!PyFloat_AsString+233>:
    jmp    0x1e081ac4 <python27!PyFloat_AsString+244>
   0x1e081abb <python27!PyFloat_AsString+235>:  pushl  0xc(%esp)
   0x1e081abf <python27!PyFloat_AsString+239>:  push   $0x1e0d6dfe
   0x1e081ac4 <python27!PyFloat_AsString+244>:
    call   0x1e05a827 <python27!PyEval_SetTrace>

Before PyEval_SetTrace, push $0x1e0d6dfe, this is what I want.

(gdb) b *0x1e0d6dfe
(gdb) call PyEval_SetTrace(0x1e0d6dfe, 0)

* Build gdb with python and python ipa ::

  $ tar xzf gdb-7.8.1.tar.gz
  $ cd gdb-7.8.1

  # Hack gdb/configure, replace ncurses with ncursesw, after
    configure, add -lncursesw in Makefile

  $ ./configure --with-python=python --with-babeltrace=no \
    --enable-tui=no --enable-host-shared
  $ make

  $ i686-pc-mingw32-gcc -shared  -g -I/cygdrive/c/Python27/include \
      ipa.c -Wl,-lpthread -o pyddd-ipa.dll

* Print PyCodeObject created by PyCode_New ::

  PyCode_New(int argcount, int nlocals, int stacksize, int flags,
             PyObject *code, PyObject *consts, PyObject *names,
             PyObject *varnames, PyObject *freevars, PyObject *cellvars,
             PyObject *filename, PyObject *name, int firstlineno,
             PyObject *lnotab);

             filename => $ebp + 0x30
             name => $ebp + 0x34

            (gdb) break PyCode_New
              commands
                silent
                p (char*)PyString_AsString({PyObject*}($ebp+0x30))
                p (char*)PyString_AsString({PyObject*}($ebp+0x34))
                p (int)({int*}($ebp+0x38))
                # call pyddd_ipa_new_code_object_hook(
                #             {PyObject*}($ebp+0x30),
                #             {PyObject*}($ebp+0x34),
                #             (int)({int*}($ebp+0x38)),
                #             {PyObject*}($ebp+0x3c)
                #             )
                continue
              end
        
* How to start at the begin of running script:

  Add a temporary catch, as the following command:

  (gdb) py-tcatch call "<module>"

  It will stop as soon as the main script to start at first line.

* The available variables when hit a breakpoint:

    - PyFrameObject *pyddd_ipa_current_frame,
    - long pyddd_ipa_current_thread
    - char *pyddd_ipa_current_filename
    - int pyddd_ipa_current_lineno

    Extra-names for catch point:

    - char *pyddd_ipa_current_funcname  when catch a call
    - char *pyddd_ipa_current_excname   when catch a exception

    Extra-names for normal breakpoint:

    - int pyddd_ipa_current_breakpoint->bpnum
    - int pyddd_ipa_current_breakpoint->locnum


* pyddd command map list

  Note that not all of gdb commands have mapped python commands. Some
  work both c and python, the others aren't no python's.

  - Watchpoint/Catchpoint/Tracepoint aren't supported

  - GDB convenience variables aren't recognized in python breakpoint's
    condition.

    Exactly to say, it's invalid to mix python expression and GDB
    convenience variables.
