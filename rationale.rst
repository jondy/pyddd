
**Line by Line Debug Python Scripts In GDB**

Pyddd is a super-GDB debugger which could debug python scripts as the
same way to debug c program line by line in the same inferior.

Purpose
=======

Debug Python scripts line by line as debug C/C++ in GDB, so that we
can easily debug Python scripts and C/C++ extensions within GDB.

Causation
=========

I always uses Python plus C/C++ to develop my most of
applications. Generally, use GDB to debug python C/C++ extensions, and
insert extra print statements in Python scripts. There is a gdb
extension "libpython.py" within Python sources, it could print Python
frame, locals/globals variable, Python sources in GDB. But it couldn't
set breakpoints in Python scripts directly. Finally, I decided to
write a debugger to extend GDB could debug Python scripts line by
line, just like debugging c/c++.

Proposal
========

* Start to debug Python script::

  - (gdb) py-exec-file /usr/local/bin/python2.7
  - (gdb) py-file beer.py
  - (gdb) py-args 10
  - (gdb) py-start

GDB will stop at the first code line of beer.py. If use `py-run`
instead `py-start`::

  - (gdb) py-run

GDB will not stop at the begging of beer.py, until hit some
breakpoint.

Set Python arguments, for example, unbuffered binary stdout and
stderr::

  - (gdb) py-exec-args -u

* Set breakpoints in Python script::

  - (gdb) py-break 10
  - (gdb) py-break beer.py:10
  - (gdb) py-break bottle
  - (gdb) py-break beer.py:bottle
  - (gdb) py-break bottle:+3
  - (gdb) py-break bottle:-3

Set condition of breakpoints::

  - (gdb) py-break location if condition
  - (gdb) py-condition bnum condition

condition may be any valid Python expression. It will not stop if
symbol in condition isn't available in the current context.

Set temporary breakpoints, arguments are same with `py-break`::

  - (gdb) py-tbreak ...

Delete breakpoints::

  - (gdb) py-clear
  - (gdb) py-clear location
  - (gdb) py-delete [breakpoints] [range...]

Disable breakpoints::

  - (gdb) py-disable [breakpoints] [range...]
  - (gdb) py-enable [breakpoints] [range...]
  - (gdb) py-enable [breakpoints] once range...
  - (gdb) py-enable [breakpoints] count count range...
  - (gdb) py-enable [breakpoints] delete range...

Breakpoint Command Lists::

  - (gdb) py-commands [range...]
          ... command-list ...
          end

Show breakpoints::

  - (gdb) py-info [breakpoints] [range...]

* Catch exception and function call::

  - (gdb) py-catch exception name
  - (gdb) py-catch call name

GDB will stop when exception name is raised or function name is
called.

Add temporary catchpoint::

  - (gdb) py-tcatch exception name
  - (gdb) py-tcatch call name

Clear catchpoints::

  - (gdb) py-catch clear name

Show catchpoints::

  - (gdb) py-catch info [ranges...]

* Continuing and Stepping::

  - (gdb) py-continue [ignore-count]
  - (gdb) py-step [count]
  - (gdb) py-next [count]
  - (gdb) py-finish
  - (gdb) py-until
  - (gdb) py-until location
  - (gdb) py-advance location

* Examining Python Scripts::

  - (gdb) py-list linenum
  - (gdb) py-list function
  - (gdb) py-list
  - (gdb) py-list -
  - (gdb) py-list +
  - (gdb) py-list first,last
  - (gdb) py-list first,
  - (gdb) py-list ,last

* Examining Python frame stack::

  - (gdb) py-frame
  - (gdb) py-frame n
  - (gdb) py-frame function
  - (gdb) py-up [n]
  - (gdb) py-down [n]
  - (gdb) py-select-frame framespec

* Examining Python backtrace::

  - (gdb) py-bt
  - (gdb) py-bt n
  - (gdb) py-bt -n
  - (gdb) py-bt full
  - (gdb) py-bt full n
  - (gdb) py-bt full -n

* Examining Python Data::

  - (gdb) py-print expr
  - (gdb) py-locals
  - (gdb) py-locals varname
  - (gdb) py-globals
  - (gdb) py-globals varname

* Altering Python local/global variable::

  - (gdb) py-set-var name expression
  - (gdb) py-set-var /global name expression

Workaround
==========

Fortunately, Python has its line-trace mechanism, see "PySys_SetTrace"
in "Python/sysmodule.c" and "PyEval_SetTrace" in "Python/ceval.c". In
order to stop Python Scripts in GDB, we need write a trace function in
c or c++, install the trace function when run python scripts. In trace
function check all the *Python Breakpoints*, and execute a statement
which include a GDB *Breakpoint*. Here is the basic scenario:

  - Write our own trace function in C, and build it as a shared library.
  - Manage *Python Breakpoints* in this library.
  - In GDB, load this library and install trace function after start
    to debug python scripts.
  - In GDB, set a *Breakpoint* in trace function. It will execute the
    statement in this *Breakpoint* if any *Python Breakpoint* is
    hit. By this way, a *Python Breakpint* is transferred a standard
    GDB *Breakpoint*.

In order to get the lineno of each imported class/function in runtime,
The two GDB *Breakpoints* at "PyImport_ExecCodeModuleEx" and
"PyCode_New" are set.

Here is prototype of "PyImport_ExecCodeModuleEx"::

  PyObject* PyImport_ExecCodeModuleEx(char *name, PyObject *co, char *pathname);

When GDB stop at "PyImport_ExecCodeModuleEx", "name" and "pathname"
could be got from the current frame::

  set $name = (char*)($fp + sizeof($fp) + sizeof($pc))
  set $pathname = (char*)($fp + sizeof($fp) + sizeof($pc) + sizeof(char*) + sizeof(PyObject*)

For the concerned module, enable *Breakpoint* "PyCode_New"; Otherwise
disable. Because there are many python scripts are imported, only a
few are required to debug.

When GDB stop at "PyCode_New", as the same way, "name" and
"firstlineno" could be got from current frame. When name equals
"<module>", it means last code object in this module, disable this
*Breakpoint* self.


Implementation
==============

See ipa.c, init.gdb and libddd.py

Example
=======

This example is doc-tested, run the following command to test it::

  $ python testddd.py -v

* Load init.gdb of *PYDDD*::

    (gdb) source init.gdb
    No symbol table is loaded.  Use the "file" command.
    No symbol table is loaded.  Use the "file" command.
    No symbol table is loaded.  Use the "file" command.
    No symbol table is loaded.  Use the "file" command.
    No symbol table is loaded.  Use the "file" command.
    No symbol table is loaded.  Use the "file" command.
    No symbol table is loaded.  Use the "file" command.
    No symbol table is loaded.  Use the "file" command.
    (gdb)

* Specify which python is used::

    (gdb) py-exec-file python
    Reading symbols from ...python...(no debugging symbols found)...done.
    (gdb)

* Specify main script::

    (gdb) py-file beer.py
    main script is beer.py
    (gdb)

* Start debug::

    (gdb) py-start
    Add temporary catchpoint #1, catch call:<module>
    load symbols from main script
    Disabled autoload imported symbol
    [New Thread ...]
    [New Thread ...]
    Enabled autoload imported symbol
    Catch function call: <module>
    #0 <module> ( ) at beer.py:5
      >5    import sys
    Remove temporary catchpoint #1
    (gdb)

* Show sources::

    (gdb) py-list
      >5    import sys
       6
       7    n = 10
       8    if sys.argv[1:]:
       9        n = int(sys.argv[1])
      10
      11    def bottle(n):
      12        if n == 0: return "no more bottles of beer"
      13        if n == 1: return "one bottle of beer"
      14        return str(n) + " bottles of beer"
      15
    (gdb)

* Continue script::

    (gdb) py-continue
    Continuing.
    ...
    (gdb)
