#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
#############################################################
#                                                           #
#      Copyright @ 2014, 2015 Dashingsoft corp.             #
#      All rights reserved.                                 #
#                                                           #
#      pyddd                                                #
#                                                           #
#      Version: 0.1.2                                       #
#                                                           #
#############################################################
#
#
#  @File: libddd.py
#
#  @Author: Jondy Zhao(jondy.zhao@gmail.com)
#
#  @Create Date: 2014/12/18
#
#  @Description:
#
#   GDB Extension script.
#
from __future__ import with_statement

import ast
import fnmatch
import locale
import os
import sys
import string

import gdb
from gdb.FrameDecorator import FrameDecorator

#################################################################
#
# Part: Shared Data
#
#################################################################

_python_main_script = ''
_python_exec_arguments = ''
_python_script_arguments = ''

_python_frame_stack = []
_python_frame_index = -1
_python_breakpoint_table = []
_python_catchpoint_table = []

# Used to filter python imported module by fnmatch
_imported_script_filters = {'includes' : [], 'excludes' : []}
_imported_script_symbol_table = {}
# Save symbol add by command py-symbol-file
_python_script_symbol_table = {}

#################################################################
#
# Part: Utils
#
#################################################################

gdb_eval = lambda s : gdb.parse_and_eval(s)
gdb_eval_str = lambda s : gdb.parse_and_eval(s).string()
gdb_eval_int = lambda s : int(gdb.parse_and_eval(s))
gdb_output = lambda s, sep='\n' : sys.stdout.write (s + sep)
target_has_execution = lambda : gdb.selected_inferior ().pid

def list_pending_python_breakpoints(filename=None):
    for bp in _python_breakpoint_table:
        if bp.is_valid() and bp.state \
            and (filename is None or bp.filename == filename):
            yield bp

def list_python_breakpoints(bpnums=None):
    for bp in _python_breakpoint_table:
        if bp.is_valid() and (bpnums is None or bp.bpnum in bpnums):
            yield bp

def find_python_breakpoint(bpnum):
    for bp in _python_breakpoint_table:
        if bp.is_valid() and bp.bpnum == bpnum:
            return bp

def list_python_catchpoints(name=None, bpnums=None):
    for bp in _python_catchpoint_table:
        if bp.is_valid() \
            and (name is None or bp.filename == name) \
            and (bpnums is None or bp.bpnum in bpnums):
            yield bp

def get_symbol_table(filename):
    return _imported_script_symbol_table.get(
                filename,
                _python_script_symbol_table.get(filename, {})
                )
def resolve_filename_breakpoints(filename):
    for bp in list_pending_python_breakpoints(filename):
        if bp._resolve(get_symbol_table(filename)):
            bp._load()

def python_ipa_load_catchpoint():
    if target_has_execution():
        gdb.execute('set var pyddd_ipa_python_catch_exceptions = %s' % \
            build_catch_patterns('exception'))
        gdb.execute('set var pyddd_ipa_python_catch_functions = %s' % \
            build_catch_patterns('call'))

def build_catch_patterns(name):
    return '"%s"' % ' '.join(
        [c.lineno for c in list_python_catchpoints(name) if c.enabled]
        )

def python_breakpoint_hit_command_list():
    '''Do after a python script breakpoint is hit.'''
    gdb.execute('python-ipa-frame setup')
    gdb.execute('python-ipa-frame print')
    i = PythonIPAFrameCommand.current_lineno()
    gdb.execute('python-ipa-frame sources %d, %d' % (i, i))

#################################################################
#
# Part: Internal Breakpoint and Normal Python Breakpoint
#
#################################################################

class PythonInternalExceptionCatchpoint (gdb.Breakpoint):
    '''This is an internal breakpoint to catch exception. '''

    def __init__(self):
        super(PythonInternalExceptionCatchpoint, self).__init__(
            "pyddd_ipa_catch_exception_addr",
            internal=True,
            )
        self.silent = True

    def stop (self):
        name = gdb_eval_str('pyddd_ipa_current_excname')
        gdb_output ('Catch exception: %s' % name)
        python_breakpoint_hit_command_list()
        self._clear(excname)
        return True

    def _clear(self, name):
        '''Clear temporary catchpoint.'''
        bplist = []
        for bp in list_python_catchpoints('exception'):
            if bp.temporary and bp.lineno == name:
                bplist.append(bp)
        for bp in bplist:
            _python_catchpoint_table.remove(bp)
            gdb_output ('Remove temporary catchpoint #%d' % bp.bpnum)
        if len(bplist):
            python_ipa_load_catchpoint()

class PythonInternalCallCatchpoint (gdb.Breakpoint):
    '''This is an internal breakpoint to catch function call. '''

    def __init__(self):
        super(PythonInternalCallCatchpoint, self).__init__(
            "pyddd_ipa_catch_call_addr",
            internal=True,
            )
        self.silent = True

    def stop (self):
        name = gdb_eval_str('pyddd_ipa_current_funcname')
        gdb_output ('Catch function call: %s' % name)
        python_breakpoint_hit_command_list()
        self._clear(name)
        return True

    def _clear(self, name):
        '''Clear temporary catchpoint.'''
        bplist = []
        for bp in list_python_catchpoints('call'):
            if bp.temporary and bp.lineno == name:
                bplist.append(bp)
        for bp in bplist:
            _python_catchpoint_table.remove(bp)
            gdb_output ('Remove temporary catchpoint #%d' % bp.bpnum)
        if len(bplist):
            python_ipa_load_catchpoint()

class PythonInternalLineBreakpoint (gdb.Breakpoint):
    '''This is an internal breakpoint. '''

    def __init__(self):
        super(PythonInternalLineBreakpoint, self).__init__(
            spec="pyddd_ipa_breakpoint_addr",
            internal=True,
            )
        self.silent = True

    def stop (self):
        # update hit count of all breakpoints from pyddd ipa
        rtable = gdb.parse_and_eval('pyddd_ipa_breakpoint_table')
        for bp in list_python_breakpoints():
            if bp.rindex != -1:
                bp.hit_count = int(rtable[bp.rindex]['hit_count'])
        # stop at bpnum
        bpnum = gdb_eval_int('pyddd_ipa_current_breakpoint->bpnum')
        locnum = gdb_eval_int('pyddd_ipa_current_breakpoint->locnum')
        # update all the python breakpoints
        bp = find_python_breakpoint(bpnum)
        if bp is None:
            gdb_output ('Breakpoint #%d (not found)\n' % bpnum)
        else:
            # print bpinfo
            bp._info()
            # if bp is temporary, remove it
            if bp.temporary:
                _python_breakpoint_table.pop(bp)
                bp._unload()
        python_breakpoint_hit_command_list()
        return True

    def __setattr__(self, name, value):
        # For this internal breakpoint, ignore_count always equals 0
        #
        # When run command "py-continue ignore_count", it will set
        # ignore_count of this internal breakpoint. It's not excepted,
        # so we clear it here.
        if name == 'ignore_count':
            value = 0
        gdb.Breakpoint.__setattr__(self, name, value)

class PythonInternalVolatileBreakpoint (gdb.Breakpoint):
    '''This is an internal breakpoint. '''

    def __init__(self):
        super(PythonInternalVolatileBreakpoint, self).__init__(
            spec="pyddd_ipa_volatile_breakpoint_addr",
            internal=True,
            )
        self.silent = True

    def stop (self):
        python_breakpoint_hit_command_list()
        return True

class PythonInternalStartupBreakpoint (gdb.Breakpoint):
    '''This is an internal breakpoint. '''
    def __init__(self, spec):
        super(PythonInternalStartupBreakpoint, self).__init__(
            spec=spec,
            internal=True,
            )
        self.silent = True
        self.enabled = False

    def stop (self):
        gdb.execute('python-ipa-initialize')
        gdb.execute('py-symbol-file enable autoload')
        self.enabled = False
        return False

class PythonInternalImportModuleBreakpoint (gdb.Breakpoint):
    '''This is an internal breakpoint.

        PyObject* PyImport_ExecCodeModuleEx(
            char *name,
            PyObject *co,
            char *pathname)
    '''

    def __init__(self, cobp):
        super(PythonInternalImportModuleBreakpoint, self).__init__(
            spec="PyImport_ExecCodeModuleEx",
            internal=True,
            )
        self.silent = True
        self.enabled = False
        self._cobp = cobp
        self._argoffset = None
        self._exprs = \
            '{char*}($fp+0x%x)', \
            '{PyObject*}($fp+0x%x)', \
            '{char*}($fp+0x%x)'
        self._args = \
            'sizeof($fp)+sizeof($pc)', \
            'sizeof($fp)+sizeof($pc)+sizeof(char*)', \
            'sizeof($fp)+sizeof($pc)+sizeof(char*)+sizeof(PyObject*)'

    def stop (self):
        '''Filter module'''
        pathname = self._argvalue(2)
        name = self._argvalue(0)
        enabled = True
        for s in _imported_script_filters['includes']:
            if fnmatch.fnmatch(pathname, s):
                enabled = True
                break
            elif enabled:
                enabled = False
        if enabled:
            for s in _imported_script_filters['excludes']:
                if fnmatch.fnmatch(pathname, s):
                    enabled = False
                    break
        self._cobp.enabled = enabled
        return False

    def _argvalue(self, index):
        if self._argoffset is None:
            self._argoffset = \
                gdb_eval_int(self._args[0]), \
                gdb_eval_int(self._args[1]), \
                gdb_eval_int(self._args[2])
        return gdb_eval_str(self._exprs[index] % self._argoffset[index])

class PythonInternalNewCodeObjectBreakpoint (gdb.Breakpoint):
    '''This is an internal breakpoint.
        PyCodeObject *PyCode_New(int argcount,
                                 int nlocals,
                                 int stacksize,
                                 int flags,
                                 PyObject *code,
                                 PyObject *consts,
                                 PyObject *names,
                                 PyObject *varnames,
                                 PyObject *freevars,
                                 PyObject *cellvars,
                                 PyObject *filename,
                                 PyObject *name,
                                 int firstlineno,
                                 PyObject *lnotab)
    '''
    def __init__(self):
        super(PythonInternalNewCodeObjectBreakpoint, self).__init__(
            spec="PyCode_New",
            internal=True,
            )
        self.silent = True
        self.enabled = False
        self._symbol_table = {}
        self._argoffset = None
        self._exprs = \
            '(char*)(PyString_AsString({PyObject*}($fp+0x%x)))', \
            '(char*)(PyString_AsString({PyObject*}($fp+0x%x)))', \
            '(int)({int*}($fp+0x%x))'
        self._args = \
            'sizeof($fp)+sizeof($pc)+sizeof(int)*4+sizeof(PyObject*)*6', \
            'sizeof($fp)+sizeof($pc)+sizeof(int)*4+sizeof(PyObject*)*7', \
            'sizeof($fp)+sizeof($pc)+sizeof(int)*4+sizeof(PyObject*)*8'

    def stop (self):
        self._add_symbol(
            self._argvalue(0).string(),
            self._argvalue(1).string(),
            int(self._argvalue(2)),
            )
        return False

    def _argvalue(self, index):
        if self._argoffset is None:
            self._argoffset = \
                gdb_eval_int(self._args[0]), \
                gdb_eval_int(self._args[1]), \
                gdb_eval_int(self._args[2])
        return gdb_eval(self._exprs[index] % self._argoffset[index])

    def _add_symbol(self, filename, symbol, lineno):
        if symbol == '<module>':
            self.enabled = False
            _imported_script_symbol_table[filename] = self._symbol_table
            self._symbol_table = {}
            resolve_filename_breakpoints(filename)
        else:
            self._symbol_table[symbol] = lineno

#################################################################
#
# Part: Python Script Breakpoint
#
#################################################################

class PythonBreakpoint (object):
    '''Python script breakpoint, includes extra fields:
        rindex          Index in python-ipa

        filename/lineno Address of this breakpoint if not multiple

        state           0  fixed
                        1  pending
                        2  resolved
        In future:

        multiloc        A tuple for breakpoint has multiple addresses
          (rindex, enabled, hit_count, filename, lineno), ...
    '''
    BP_COUNTER = 0
    def __init__(self, spec, temporary=0):
        super(PythonBreakpoint, self).__init__()
        self.rindex = -1
        self.location = spec
        self.enabled = 1
        self.temporary = temporary
        self.thread = 0
        self.ignore_count = 0
        self.hit_count = 0
        self.condition = 0
        self.visible = 1

        self.filename = None
        self.lineno = 0
        self.multiloc = None
        self.state = 0
        self._parse(spec)

        self.BP_COUNTER += 1
        self.bpnum = self.BP_COUNTER

    def is_valid (self):
        return True

    def _parse(self, spec):
        '''Resolve location to filename:lineno.'''
        arglist = spec.split(':')
        n = len(arglist)
        if n == 0:
            self._parse0()
        elif n == 1:
            self._parse1(*arglist)
        elif n == 2:
            self._parse2(*arglist)
        elif n == 3:
            self._parse3(*arglist)
        else:
            raise gdb.GdbError('Invalid breakpoint spec "%s"' % spec)

    def _parse0(self):
        filename = PythonIPAFrameCommand.current_filename()
        if filename is None:
            raise gdb.GdbError('There is no script')
        self.filename = filename
        self.lineno = PythonIPAFrameCommand.current_lineno()
        self.state = 0

    def _parse1(self, arg):
        filename = PythonIPAFrameCommand.current_filename()
        if filename is None:
            raise gdb.GdbError('There is no script')
        try:
            offset = int(arg)
        except ValueError:
            offset = None
        if offset is None:
            self._parsen(filename, arg)
        else:
            lineno = offset
            if arg[0] in '+-':
                lineno += PythonIPAFrameCommand.current_lineno()
            if lineno <= 0:
                raise gdb.GdbError('Invalid breakpoint location')
            self.filename = filename
            self.lineno = lineno
            self.state = 0

    def _parse2(self, arg1, arg2):
        if arg1.lower().endswith('.py'):
            if arg2.isdigit():
                self.filename = arg1
                self.lineno = arg2
                self.state = 0
            else:
                self._parsen(arg1, arg2)
        elif arg2.isdigit():
            k = int(arg2)
            self._parsen(PythonIPAFrameCommand.current_filename(), arg1)
            if self.state == 2:
                self.lineno += k
        elif arg1 in ('exception', 'call'):
            self.filename = arg1
            self.lineno = arg2
            self.state = 0
        else:
            raise gdb.GdbError('Invalid breakpoint location')

    def _parse3(self, filename, funcname, offset):
        k = int(offset)
        self._parsen(filename, funcname)
        if self.state == 2:
            self.lineno += k

    def _parsen(self, filename, funcname):
        if self._resolve(get_symbol_table(filename)):
            self.filename = filename

    def _resolve(self, symtable):
        '''Only find first location, multi-location is not implemented.'''
        self.state = 1
        for name in symtable:
            if self.location == name:
                self.lineno = symtable[name]
                self.state = 2
                return True

    def _load(self):
        if target_has_execution():
            s = string.Template(
                '$bpnum, $locnum, $thread, $condition, ' \
                ' $ignore_count, $enabled, $lineno, "$filename"'
                ).substitute(self.__dict__, locnum=0)
            if self.rindex == -1:
                i = gdb_eval_int('pyddd_ipa_insert_breakpoint(%s)' % s)
                self.rindex = i
            else:
                gdb.execute('call pyddd_ipa_update_breakpoint(%d, %s)' \
                    % (self.rindex, s))

    def _unload(self):
        if target_has_execution() and self.rindex != -1:
            gdb.execute('call pyddd_ipa_remove_breakpoint(%d)' % self.rindex)

    def _info(self):
        gdb_output ('bpnum=%d, location=%s, hit_count=%s' % \
            (self.bpnum, self.location, self.hit_count))

#################################################################
#
# Part: Extend Commands
#
#################################################################

#  Internal commands:
#    python-ipa-download-data
#    python-ipa-frame
#
#  Start commands:
#    py-file
#    py-args
#    py-run
#    py-start
#    py-exec-args
#
#  Breakpoint commands:
#    py-break
#    py-tbreak
#    py-rbreak
#    py-clear
#    py-catch
#    py-tcatch
#
#  Other commands:
#    py-symbol-file
#    py-info
#
class PythonIPALoadDataCommand(gdb.Command):
    '''
    Upload python breakpoints and catchpoints to python-ipa
    when python library is loaded (internaly used only).

    Usage: python-ipa-load-data
    '''

    def __init__(self):
        gdb.Command.__init__ (self,
                              'python-ipa-load-data',
                              gdb.COMMAND_NONE,
                              gdb.COMPLETE_NONE,
                              )

    def invoke(self, args, from_tty):
        self.dont_repeat()
        # upload catchpoints to python-ipa
        python_ipa_load_catchpoint()
        # upload breakpoints to python-ipa
        for bp in list_python_breakpoints():
            # Reset rindex, force new breakpoint in ipa
            bp.rindex = -1
            if bp.filename is not None:
                bp._load()
            elif bp.multiloc is not None:
                raise NotImplementedError('multi-locations')

class PythonFileCommand(gdb.Command):
    '''
    Set main python script

    Usage: py-file filename
           py-file "string"

    If argument is filename, then set main script as filename.
    If argument is string, use -c command to run this string.
    '''

    def __init__(self):
        gdb.Command.__init__ (self,
                              'py-file',
                              gdb.COMMAND_FILES,
                              gdb.COMPLETE_FILENAME,
                              )

    def invoke(self, args, from_tty):
        global _python_main_script
        self.dont_repeat()
        _python_main_script = args
        gdb_output ('main script is %s' % _python_main_script)

class PythonSymbolFileCommand(gdb.Command):
    '''
    Mange python script's symbol table

    Usage: py-symbol-file FILENAME
           py-symbol-file add FILENAME
    Parse FILENAME, get lineno of each function/class, add to symbol
    table. These information is used to resolve symbol in breakpoint
    location to filename:lineno.

    Usage: py-symbol-file clear
    Clear the whole symbol table.

    Usage: py-symbol-file clear autoload
    Clear only those symbol file imported in running time.

    Usage: py-symbol-file clear FILENAME
    Clear all the symbol belong to FILENAME.

    Usage: py-symbol-file info
    Show all the information about python symbol files.

    Usage: py-symbol-file filter PATTERN
           py-symbol-file filter !PATTERN
    Add include/exclude PATTERN (format of fnmatch) to filter
    those imported scripts in runtime. Only those match include
    PATTERN and not match exclude PATTERN could be added symbol
    table.

    Usage: py-symbol-file filter clear
    Clear all the filters.

    Usage: py-symbol-file disable autoload
           py-symbol-file enable autoload
    Disable/enable autoload imported symbol in runtime.

    '''
    def __init__(self):
        gdb.Command.__init__ (self,
                              'py-symbol-file',
                              gdb.COMMAND_FILES,
                              gdb.COMPLETE_FILENAME,
                              )
        self._cobp = PythonInternalNewCodeObjectBreakpoint()
        self._imbp = PythonInternalImportModuleBreakpoint(self._cobp)

    def invoke(self, args, from_tty):
        self.dont_repeat()
        try:
            cmd, args = args.split(' ', 1)
        except Exception:
            cmd, args = args, ''
        if 'disable'.startswith(cmd):
            self._imbp.enabled = False
            self._cobp.enabled = False
            gdb_output('Disabled autoload imported symbol')
        elif 'enable'.startswith(cmd):
            self._imbp.enabled = True
            gdb_output('Enabled autoload imported symbol')
        elif 'clear'.startswith(cmd):
            self._clear(args)
        elif 'add'.startswith(cmd):
            self._add(args)
        elif 'filter'.startswith(cmd):
            self._filter(args)
        elif 'info'.startswith(cmd):
            self._info(args)
        else:
            self._add(args)

    def _clear(self, args):
        if args == '':
            _imported_script_symbol_table.clear()
            _python_script_symbol_table.clear()
            gdb_output ('All of python symbol tables are cleared')
        else:
            if 'autoload'.startswith(args):
                _imported_script_symbol_table.clear()
                gdb_output ('Imported python symbol tables are cleared')
            elif args in _python_script_symbol_table:
                _python_script_symbol_table.pop(args)
                gdb_output ('Remove "%s" from python symbol table' % args)
            else:
                gdb_output ('No "%s" in python symbol table' % args)

    def _add(self, args):
        arglist = gdb.string_to_argv(args)
        for filename in arglist:
            if os.path.exists(filename):
                s = PythonSymbolList(filename)
                s.load()
                _python_script_symbol_table[filename] = dict(s)
                gdb_output ('Add "%s" to python symbol table' % filename)
            else:
                raise gdb.GdbError('File "%s" not found' % filename)

    def _update(self, args):
        raise NotImplementedError('py-symbol-file update')

    def _info(self, args):
        gdb_output ('Autoload imported symbol state: %s' % \
            'enabled' if self._imbp.enabled else 'disabled')
        gdb_output ('Include filters: %s' % \
            str(_imported_script_filters['includes']))
        gdb_output ('Exclude filters: %s' % \
            str(_imported_script_filters['excludes']))
        gdb_output ('Python symbol tables:')
        gdb_output (' '.join(_python_script_symbol_table.keys()))
        gdb_output ('Auto imported symbol tables:')
        gdb_output (' '.join(_imported_script_symbol_table.keys()))

    def _filter(self, args):
        if 'clear'.startswith(args):
            for k in _imported_script_filters:
                _imported_script_filters[:] = []
            gdb_output ('Python symbol filters are cleared')
        else:
            for arg in gdb.string_to_argv(args):
                if arg[0] == '!':
                    _imported_script_filters['excludes'].append(arg[1:])
                    gdb_output ('Added exclude filter "%s"' % arg[1:])
                else:
                    _imported_script_filters['includes'].append(arg)
                    gdb_output ('Added include filter "%s"' % arg)

class PythonRunCommand(gdb.Command):
    '''
    Run main python script

    Usage: py-run
    Wrap gdb command 'run', set args to call python, for example,
      (gdb) exec-file python
      (gdb) py-file main.py
      (gdb) py-args --help
      (gdb) py-exec-args -i
      (gdb) py-run

    py-run will set args before call gdb command 'run' like this:
        gdb.execute('set args -i main.py --help')
    '''
    def __init__(self):
        gdb.Command.__init__ (self,
                              'py-run',
                              gdb.COMMAND_RUNNING,
                              gdb.COMPLETE_NONE,
                              )
        self._internal_bplist = \
            PythonInternalStartupBreakpoint('PySys_SetArgv'), \
            PythonInternalStartupBreakpoint('PySys_SetArgvEx')

    def invoke(self, args, from_tty):
        self.dont_repeat()
        for bp in self._internal_bplist:
            bp.enabled = True
        if os.path.exists(_python_main_script):
            fmt = 'set args %s %s %s'
            gdb_output ('load symbols from main script')
            s = PythonSymbolList(_python_main_script)
            s.load()
            _python_script_symbol_table[_python_main_script] = dict(s)
        else:
            fmt = 'set args %s -c "%s" %s'
        gdb.execute(fmt % (_python_exec_arguments,
            _python_main_script,
            _python_script_arguments))
        gdb.execute('py-symbol-file disable autoload')
        gdb.execute('run')

class PythonCatchpointCommand(gdb.Command):
    '''
    Create python script catchpoints.

    Usage: py-catch exception NAME
    Stop when exception NAME raised

    Usage: py-catch call NAME
    Stop when call function NAME

    Usage: py-catch info
    Show all catchpoints.
    '''
    def __init__(self, name='py-catch', temporary=False):
        gdb.Command.__init__ (self,
                              name,
                              gdb.COMMAND_BREAKPOINTS,
                              gdb.COMPLETE_COMMAND,
                              )
        self._temporary = temporary

    def invoke(self, args, from_tty):
        self.dont_repeat()
        if args == '':
            self._info()
        else:
            try:
                cmd, subargs = args.split(' ', 1)
            except Exception:
                cmd = args
                subargs = ''
            if 'exception'.startswith(cmd):
                self._catchpoint(cmd, subargs)
            elif 'call'.startswith(cmd):
                self._catchpoint(cmd, subargs)
            elif 'info'.startswith(cmd):
                self._info(subargs)
            else:
                raise NotImplementedError(cmd)

    def _catchpoint(self, kind, args):
        if self._temporary:
            prefix = 'Add temporary catchpoint'
        else:
            prefix = 'Add catchpoint'
        for c in args.split(' '):
            spec = '%s:%s' % (kind, c)
            cp = PythonBreakpoint(spec, temporary=self._temporary)
            _python_catchpoint_table.append(cp)
            gdb_output (
                '%s #%d, catch %s' % (prefix, cp.bpnum, spec)
                )
        if args != '':
            python_ipa_load_catchpoint()

    def _info(self, arg=None):
        for bp in list_python_catchpoints(arg):
            s = 'Temporary catchpoint' if bp.temporary else 'Catchpoint'
            gdb_output ('%s #%d, catch %s:%s' % \
                (bp.bpnum, s, bp.filename,bp.lineno,)
                )

class PythonTempCatchpointCommand(PythonCatchpointCommand):
    '''
    Create temporary python script catchpoints.

    Usage: py-tcatch ARGUMENTS
    Same as py-catch, but the catchpoint will be deleted once hit.
    '''
    def __init__(self):
        super(PythonTempCatchpointCommand, self).__init__(
            name='py-tcatch',
            temporary=True,
            )

class PythonBreakpointCommand(gdb.Command):
    '''
    Create python script breakpoints.

    Usage: py-break
    Add breakpoint in the current file and current lineno.

    Usage: py-break LINENO
    Add breakpoint in the LINENO of current file.

    Usage: py-break FUNCTION
    Add breakpoint in the FUNCTION of current file.

    Usage: py-break FILENAME:LINENO
    Add breakpoint in the FILENAME:LINEO

    Usage: py-break FILENAME:FUNCTION
    Add breakpoint in the FILENAME:FUNCTION

    Usage: py-break location if cond
    Argument cond must be python expression, it means no convenience
    variables which start with $ could be used here.
    '''
    def __init__(self, name='py-break', temporary=False):
        gdb.Command.__init__ (self,
                              name,
                              gdb.COMMAND_BREAKPOINTS,
                              gdb.COMPLETE_LOCATION,
                              )
        self._temporary = temporary

    def invoke(self, args, from_tty):
        self.dont_repeat()
        arglist = gdb.string_to_argv(args)
        try:
            spec = arglist[0]
        except IndexError:
            spec = ''
        bp = PythonBreakpoint(spec, temporary=self._temporary)
        try:
            bp.condition = arglist[2]
        except IndexError:
            pass
        _python_breakpoint_table.append(bp)
        bp._load()
        bp._info()

class PythonTempBreakpointCommand(PythonBreakpointCommand):
    '''
    Create temporary python script breakpoints.

    Usage: py-tbreak ARGUMENTS
    Same as py-break, but the breakpoint will be deleted once hit.
    '''
    def __init__(self):
        super(PythonTempBreakpointCommand, self).__init__(
            name='py-tbreak',
            temporary=True
            )

class PythonClearCommand(gdb.Command):
    '''
    Clear python script breakpoints or catchpoints.

    Usage: py-clear
    Clear breakpoints in the current line of current file.

    Usage: py-clear [break] LOCATION
    Clear breakpoints in LOCATION

    Usage: py-clear catch NAME
    Clear catchpoint NAME
    '''
    def __init__(self):
        gdb.Command.__init__ (self,
                              'py-clear',
                              gdb.COMMAND_BREAKPOINTS,
                              gdb.COMPLETE_LOCATION,
                              )

    def invoke(self, args, from_tty):
        self.dont_repeat()
        if args.startswith('break'):
            if ' ' in args:
                args = args.split(' ', 1)[1]
            self._clear_breakpoint(args)
        elif args.startswith('catch'):
            if ' ' in args:
                args = args.split(' ', 1)[1]
            self._clear_catchpoint(args)
        else:
            self._clear_breakpoint(args)

    def _clear_breakpoint(self, location):
        bp = PythonBreakpoint(location)
        filename = bp.filename
        lineno = bp.lineno
        bplist = []
        for bp in list_python_breakpoints():
            if bp.lineno == lineno and bp.filename == filename:
                bplist.append(bp)
        for bp in bplist:
            _python_breakpoint_table.remove(bp)
            gdb_output('Remove breakpoint #%d' % bp.bpnum)
            bp._unload()

    def _clear_catchpoint(self, name):
        bplist = []
        for bp in list_python_catchpoints():
            if bp.lineno == name:
                bplist.append(bp)
        for bp in bplist:
            _python_catchpoint_table.remove(bp)
            gdb_output('Remove catchpoint #%d' % bp.bpnum)
        # upload catchpoint
        python_ipa_load_catchpoint()

class PythonDeleteCommand(gdb.Command):
    '''
    Delete python script breakpoints or catchpoints.

    Usage: py-delete
    Delete all the breakpoints.

    Usage: py-delete [break] RANGES
    Delete the breakpoints list in RANGES, for example

      $(gdb) py-delete 5 6 8

    Usage: py-delete catch
    Delete all the catchpoints.

    Usage: py-delete catch RANGES
    Delete the catchpoints list in RANGES.
    '''
    def __init__(self):
        gdb.Command.__init__ (self,
                              'py-delete',
                              gdb.COMMAND_BREAKPOINTS,
                              gdb.COMPLETE_NONE,
                              )

    def invoke(self, args, from_tty):
        self.dont_repeat()
        if args.startswith('break'):
            if ' ' in args:
                args = args.split(' ', 1)[1]
            self._delete_breakpoints(args)
        elif args.startswith('catch'):
            if ' ' in args:
                args = args.split(' ', 1)[1]
            self._delete_catchpoint(args)
        else:
            self._delete_breakpoints(args)

    def _delete_breakpoints(self, args):
        if args == '':
            _python_breakpoint_table[:] = []
        else:
            arglist = [int(x) for x in args.split()]
            for bp in list_python_breakpoints(arglist):
                _python_breakpoint_table.remove(bp)
                gdb_output ('Remove breakpoint #%d' % bp.bpnum)
                bp._unload()

    def _delete_catchpoints(self, args):
        if args == '':
            _python_catchpoint_table[:] = []
        else:
            arglist = [int(x) for x in args.split()]
            for bp in list_python_catchpoints(None, arglist):
                _python_catchpoint_table.remove(bp)
                gdb_output ('Remove catchpoint #%d' % bp.bpnum)
        # upload catchpoints
        python_ipa_load_catchpoint()

class PythonEnableCommand(gdb.Command):
    '''
    Enable python script breakpoints.

    Usage: py-enable RANGES
    Enable the breakpoints list in RANGES.

    Usage: py-enable once RANGES
    Enable the breakpoints list in RANGES once, it will be disabled
    after hit.

    Usage: py-enable count N RANGES
    Enable the breakpoints list in RANGES N times, after that it will
    be disabled.

    Usage: py-enable delete RANGES
    After those breakpoints are hit, they'll be deleted.
    '''
    def __init__(self):
        gdb.Command.__init__ (self,
                              'py-enable',
                              gdb.COMMAND_BREAKPOINTS,
                              gdb.COMPLETE_NONE,
                              )

    def invoke(self, args, from_tty):
        self.dont_repeat()
        if args.startswith('once'):
            args = args.split(' ', 1)[1]
            self._enable_breakpoints(args, enabled=-1)
        elif args.startswith('delete'):
            args = args.split(' ', 1)[1]
            self._enable_breakpoints(args, temporary=True)
        elif args.startswith('count'):
            _x, n, args = args.split(' ', 2)
            self._enable_breakpoints(args, enabled=-int(n))
        else:
            self._enable_breakpoints(args)

    def _enable_breakpoints(self, args, enabled=0, temporary=False):
        arglist = [int(x) for x in args.split()]
        for bp in list_python_breakpoints(arglist):
            if enabled:
                bp.enabled = enabled
                if enabled > 0:
                    gdb_output ('Enabled breakpoint #%d')
                else:
                    gdb_output ('Enabled breakpoint #%d for %d times' % \
                        (bp.bpnum, -enabled)
                        )
            if temporary:
                bp.temporary = temporary
                gdb_output ('Make breakpoint #%d volatile' % bp.bpnum)
            bp._load()

class PythonDisableCommand(gdb.Command):
    '''
    Disable python script breakpoints.

    Usage: py-disable
    Disable all the breakpoints.

    Usage: py-disable RANGES
    Disable the breakpoints list in RANGES.
    '''
    def __init__(self):
        gdb.Command.__init__ (self,
                              'py-disable',
                              gdb.COMMAND_BREAKPOINTS,
                              gdb.COMPLETE_NONE,
                              )

    def invoke(self, args, from_tty):
        self.dont_repeat()
        if args == '':
            arglist = None
        else:
            arglist = [int(x) for x in gdb.string_to_argv(args)]
        for bp in list_python_breakpoints(arglist):
            bp.enabled = 0
            gdb_output ('Disable breakpoint #%d' % bp.bpnum)
            bp._load()

class PythonInfoCommand(gdb.Command):
    '''
    Show pyddd information.

    Usage: py-info args
    Show python script arguments.

    Usage: py-info exec-args
    Show arguments used to run python.

    Usage: py-info file
    Show python main script.

    Usage: py-info locals
    Usage: py-info globals
    Usage: py-info frame
    Show information of current frame.

    Usage: py-info catchpoints
    Show all the of catchpoints.

    Usage: py-info catchpoints RANGES
    Show the information of catchpoints in the RANGES

    Usage: py-info [breakpoints]
    Show all the breakpoints.

    Usage: py-info [breakpoints] RANGES
    Show the information of breakpoints in the RANGES
    '''
    def __init__(self):
        gdb.Command.__init__ (self, 'py-info', gdb.COMMAND_STATUS)

    def invoke(self, args, from_tty):
        self.dont_repeat()
        if 'args'.startswith(args):
            gdb_output ('Script arguments: %s' % _python_script_arguments)
        elif 'exec-args'.startswith(args):
            gdb_output ('Python arguments: %s' % _python_exec_arguments)
        elif 'file'.startswith(args):
            gdb_output ('Main script: %s' % _python_main_script)
        elif 'locals'.startswith(args):
            gdb.execute('python-ipa-frame locals')
        elif 'globals'.startswith(args):
            gdb.execute('python-ipa-frame globals')
        elif 'frame'.startswith(args):
            gdb.execute('python-ipa-frame print verbose')
        elif 'catchpoints'.startswith(args):
            if ' ' in args:
                arglist = [int(x) for x in args.split()[1:]]
            else:
                arglist = None
            for bp in list_python_catchpoints(None, arglist):
                bp._info()
        else:
            if ' ' in args:
                arglist = [int(x) for x in args.split() if x.isdigital()]
            else:
                arglist = None
            for bp in list_python_breakpoints(arglist):
                bp._info()

#################################################################
#
# Part: Python Frame (PyFrameObject*)
#
#################################################################

class PythonFrame(object):
    '''
    Wrapper for PyFrameObject*, adding various methods.

    _frame is gdb.Value
    '''
    def __init__(self, frame):
        self._frame = frame
        self._filename = None
        self._lineno = None
        self._listlineno = None
        self._listsize = gdb.parameter('listsize')
        self._name = None
        self._args = None
        self._locals = None
        self._globals = None

    def select(self):
        '''Print frame info.'''
        return True

    def _expr(self, name):
        return 'pyddd_ipa_frame_%s((PyFrameObject*)%s)' \
            % (name, self._frame)

    def older(self):
        return self._frame.dereference()['f_back']

    def info_filename(self):
        if self._filename is None:
            self._filename = gdb_eval_str(self._expr('filename'))
        return self._filename

    def info_lineno(self):
        if self._lineno is None:
            self._lineno = gdb_eval_int(self._expr('lineno'))
        return self._lineno

    def info_listlineno(self):
        if self._listlineno is None:
            self._listlineno = self._lineno
        return self._listlineno

    def info_name(self):
        if self._name is None:
            self._name = gdb_eval_str(self._expr('name'))
        return self._name

    def info_args(self):
        if self._args is None:
            code = self._frame.dereference()['f_code']
            argcount = code.dereference()['co_argcount']
            varnames = eval(gdb_eval_str(self._expr('varnames')))
            self._args = []
            for i in range(argcount):
                name = varnames[i]
                expr = self._expr('values')[:-1] + ', 0, %d)'
                value = gdb_eval_str(expr % i)
                self._args.append((name, value))
        return self._args

    def info_locals(self):
        if self._locals is None:
            self._locals = {}
            code = self._frame.dereference()['f_code']
            nlocals = code.dereference()['co_nlocals']
            varnames = eval(gdb_eval_str(self._expr('varnames')))
            cellvars = eval(gdb_eval_str(self._expr('cellvars')))
            expr = self._expr('values')[:-1] + ', 0, %d)'
            assert nlocals <= len(varnames)
            for i in range(nlocals):
                name = varnames[i]
                expr = self._expr('values')[:-1] + ', 0, %d)'
                self._locals[name] = gdb_eval_str(expr % i)
            j = nlocals
            for name in cellvars:
                expr = self._expr('values')[:-1] + ', 0, %d)'
                self._locals[name] = gdb_eval_str(expr % j)
                j += 1
        return self._locals

    def info_globals(self):
        if self._globals is None:
            self._globals = {}
            expr = self._expr('variable')[:-1] + ', "%s", 0)'
            names = eval(gdb_eval_str(self._expr('globals')))
            for s in names:
                self._globals[s] = gdb_eval_str(expr % s)
        return self._globals

    def info_sources(self, args):
        #
        # list lineno
        # list function
        #   Print lines centered around line in the current source file.
        # list
        #   Print more lines.
        # list +
        #   Print lines just after the lines last printed.
        # list -
        #   Print lines just before the lines last printed.
        # list first, last
        # list first,
        # list ,last
        #
        listsize = gdb.parameter('listsize')
        offset = listsize / 2 + self._listsize / 2
        if args == '' or args == '+':
            self._listlineno = self.info_listlineno() + offset
            self._listsize = listsize
            start = self._listlineno - self._listsize / 2
            end = self._listlineno + self._listsize / 2
        elif args == '-':
            self._listlineno = self.info_listlineno() - offset
            if self._listlineno < 1:
                self._listlineno = 1
            self._listsize = listsize
            start = self._listlineno - self._listsize / 2
            end = self._listlineno + self._listsize / 2
        elif ',' in args:
            first, last = args.split(',', 1)
            start = self.info_listlineno() if first == '' else int(first)
            end = self.info_listlineno() if last == '' else int(last)
            self._listsize = end - start + 1
            if listsize < 1:
                raise gdb.GdbError('Invalid line spec')
            self._listlineno = (start + end) / 2
        else:
            try:
                self._listlineno = int(args)
            except ValueError:
                self._listlineno = self._function_lineno(args)
            self._listsize = listsize
            if self._listlineno < 1:
                raise gdb.GdbError('Invalid line spec')
            start = self._listlineno - self._listsize / 2
            end = self._listlineno + self._listsize / 2
        if start < 1:
            start = 1
        with open(self.info_filename(), 'r') as f:
            all_lines = f.readlines()
            # start and end are 1-based, all_lines is 0-based;
            # so [start-1:end] as a python slice gives us [start, end] as a
            # closed interval
            for i, line in enumerate(all_lines[start-1:end]):
                linestr = str(i+start)
                # Highlight current line:
                if i + start == self.info_lineno():
                    linestr = '>' + linestr
                sys.stdout.write('%4s    %s' % (linestr, line))

    def _function_lineno(self, name):
        for k, v in get_symbol_table(self.info_filename()).items():
            if k == name:
                return v
        return 0

    def _print(self, level=0, verbose=False):
        #
        # print frame infoformation, output format:
        #
        #   #0 name (arg1=value1, ...) at filename:lineno
        #
        #   Or,
        #
        #   name (arg1=value1,
        #         arg2=value2,
        #         ...
        #         )
        #   at filename:lineno
        #
        # verbose mode,
        #
        #   Stack level 0, frame in functionname (filename:lineno)
        #     called by frame in functionname (filename:lineno)
        #
        #   Arglist:
        #     name1=type, value
        #     name2=type, value
        #
        #   Locals:
        #     name1=type, value
        #     name2=type. value
        #
        result = ['#%d' % level, self.info_name(), '(']
        for k, v in self.info_args():
            result.append('%s=%s,' % (k, v[:32]))
        result.append(')')
        result.append('at %s:%d' % (self.info_filename(), self.info_lineno()))
        gdb_output (' '.join(result))
        if verbose:
            for k, v in self.info_locals().items():
                if k not in self.info_args():
                    gdb_output ('  %s=%s' % (k, v))

class PythonIPAFrameCommand(gdb.Command):
    '''
    Manage python frame (internal command).

    Usage: python-ipa-frame cmd [args]

        cmd = setup | teardown | select | print | source | backtrace \
            locals | globals

        for cmd 'select', args is empty or framespec
             n | +n | -n | name

        for cmd 'backtrace', args is empty or
            i
            full
            full i
    '''
    def __init__(self):
        gdb.Command.__init__ (
            self,
            'python-ipa-frame',
            gdb.COMMAND_STACK
            )

    @classmethod
    def is_valid(cls):
        return _python_frame_index >= 0

    @classmethod
    def current_frame(cls):
        try:
            return _python_frame_stack[_python_frame_index]
        except IndexError:
            return None

    @classmethod
    def current_filename(cls):
        try:
            return _python_frame_stack[_python_frame_index].info_filename()
        except IndexError:
            return None

    @classmethod
    def current_lineno(cls):
        try:
            return _python_frame_stack[_python_frame_index].info_lineno()
        except IndexError:
            return None

    def invoke(self, args, from_tty):
        self.dont_repeat()
        if args == 'setup':
            self._setup()
        elif args == 'teardown':
            self._teardown()
        elif not args == '':
            try:
                cmd, subargs = args.split(' ', 1)
            except ValueError:
                cmd = args
                subargs = ''
            if cmd == 'select':
                self._select(subargs)
            elif cmd == 'print':
                self._print(subargs)
            elif cmd == 'backtrace' or cmd == 'bt':
                self._backtrace(subargs)
            elif cmd == 'sources':
                self._source(subargs)
            elif cmd == 'locals':
                self._locals(subargs)
            elif cmd == 'globals':
                self._globals(subargs)
            else:
                raise NotImplementedError(cmd)
        return True

    def _setup(self):
        global _python_frame_index
        _python_frame_stack[:] = [
            PythonFrame(gdb_eval('pyddd_ipa_current_frame'))
            ]
        _python_frame_index = 0

    def _teardown(self):
        global _python_frame_index
        _python_frame_index = -1

    def _push(self, n):
        frame = _python_frame_stack[-1]
        while n:
            f = frame.older()
            if f == 0:
                break
            frame = PythonFrame(f)
            _python_frame_stack.append(frame)
            n -= 1
        return n

    def _select(self, args):
        global _python_frame_index
        if args != '':
            if args[0] == '+':
                n = int(args[1:])
                _python_frame_index += n
                try:
                    _python_frame_stack[_python_frame_index]
                    k = 0
                except IndexError:
                    k = len(_python_frame_stack)
                if k:
                    d = self._push(k - _python_frame_index + 1)
                    _python_frame_index -= d

            elif args[0] == '-':
                n = int(args[1:])
                _python_frame_index -= n
                if _python_frame_index < 0:
                    _python_frame_index = 0

            elif args[0].isdigital():
                n = int(args)
                try:
                    _python_frame_stack[n]
                    _python_frame_index = n
                except IndexError:
                    pass
                if _python_frame_index != n:
                    d = self._push(len(_python_frame_stack) - n + 1)
                    _python_frame_index = n - d
            else:
                _python_frame_index = 0
                for frame in _python_frame_stack:
                    if frame._name == args:
                        break
                    _python_frame_index += 1
                else:
                    frame = _python_frame_stack[-1]
                    while True:
                        f = frame.older()
                        if f == 0:
                            break
                        frame = PythonFrame(f)
                        _python_frame_stack.append(frame)
                        if frame.info_name() == args:
                            break
                        _python_frame_index += 1

    def _print(self, args):
        verbose = args!=''
        frame = _python_frame_stack[_python_frame_index]
        frame._print(level=_python_frame_index, verbose=verbose)

    def _source(self, args):
        frame = _python_frame_stack[_python_frame_index]
        frame.info_sources(args)

    def _locals(self, args):
        frame = _python_frame_stack[_python_frame_index]
        gdb_output ('Locals:')
        for k, v in frame.info_locals().items():
            if k not in self.info_args():
                gdb_output ('  %s=%s' % (k, v))

    def _globals(self, args):
        frame = _python_frame_stack[_python_frame_index]
        gdb_output ('Globals:')
        for k, v in frame.info_globals().items():
            if k not in self.info_args():
                gdb_output ('  %s=%s' % (k, v))

    def _backtrace(self, args):
        if args[:4] == 'full':
            verbose = True
            args = args[4:].strip()
        else:
            verbose = False
        if args == '':
            start = 0
            n = -1
        else:
            if args[0] == '-':
                n = int(args[1:])
                start = _python_frame_index + n
                if start < 0:
                    start = 0
                    n = _python_frame_index + 1
            else:
                n = int(args)
                start = _python_frame_index
        try:
            while n:
                try:
                    frame = _python_frame_stack[start]
                except IndexError:
                    frame = None
                if frame is None:
                    frame = _python_frame_stack[-1]
                    while n:
                        f = frame.older()
                        if f == 0:
                            break
                        frame = PythonFrame(f)
                        _python_frame_stack.append(frame)
                        frame._print(level=start, verbose=verbose)
                        start += 1
                        n -= 1
                    break
                frame._print(level=start, verbose=verbose)
                start += 1
                n -= 1
        except KeyboardInterrupt:
            pass

#################################################################
#
# Part: Parse Script
#
#################################################################

class PythonSymbolList(list):
    '''
    Parse python scripts to a list like
        (name, lineno), ...
    name is any function/class/method in the python script
    '''
    def __init__(self, filename=None):
        super(PythonSymbolList, self).__init__()
        self.filename = filename
        if filename is not None:
            self.load(filename)

    def visit(self, level, node):
        if isinstance(node, ast.mod):
            for child in ast.iter_child_nodes(node):
                self.visit(level, child)

        elif isinstance(node, ast.FunctionDef):
            self.append((node.name, node.lineno))
            for child in node.body:
                self.visit(level+1, child)

        elif isinstance(node, ast.ClassDef):
            self.append((node.name, node.lineno))
            for child in node.body:
                self.visit(level+1, child)

    def reload(self):
        del self[:]
        self.load()

    def load(self, filename=None):
        if filename is None:
            filename = self.filename
        else:
            self.filename = filename
        if filename is None:
            return
        f = open(filename, 'r')
        try:
            node = ast.parse('\n'.join(f.readlines()))
            self.visit(0, node)
        finally:
            f.close()

#################################################################
#
# Part: GDB Frame Decorator (Not Used)
#
#################################################################

# We divide gdb.Frame into:
#   - "python frames":
#       - "bytecode frames" i.e. PyEval_EvalFrameEx
#       - "other python frames": things that are of interest from a python
#         POV, but aren't bytecode (e.g. GC, GIL)
#   - everything else

class PythonFrameDecorator(FrameDecorator):

    def __init__(self, fobj):
        super(PythonFrameDecorator, self).__init__(fobj)

    def function(self):
        frame = self.inferior_frame()
        name = str(frame.name())
        if self.is_python_frame:
            pass
        return name

    def is_python_frame(self):
        '''Is this a PyEval_EvalFrameEx frame, or some other important
        frame? (see is_other_python_frame for what "important" means in this
        context)'''
        if self.is_evalframeex():
            return True
        if self.is_other_python_frame():
            return True
        return False

    def is_evalframeex(self):
        '''Is this a PyEval_EvalFrameEx frame?'''
        if self.inferior_frame().name() == 'PyEval_EvalFrameEx':
            '''
            I believe we also need to filter on the inline
            struct frame_id.inline_depth, only regarding frames with
            an inline depth of 0 as actually being this function

            So we reject those with type gdb.INLINE_FRAME
            '''
            if self.inferior_frame().type() == gdb.NORMAL_FRAME:
                # We have a PyEval_EvalFrameEx frame:
                return True

        return False

    def is_other_python_frame(self):
        '''Is this frame worth displaying in python backtraces?
        Examples:
          - waiting on the GIL
          - garbage-collecting
          - within a CFunction
         If it is, return a descriptive string
         For other frames, return False
         '''
        if self.is_waiting_for_gil():
            return 'Waiting for the GIL'
        elif self.is_gc_collect():
            return 'Garbage-collecting'
        else:
            # Detect invocations of PyCFunction instances:
            older = self.older()
            if older and older._gdbframe.name() == 'PyCFunction_Call':
                # Within that frame:
                #   "func" is the local containing the PyObject* of the
                # PyCFunctionObject instance
                #   "f" is the same value, but cast to (PyCFunctionObject*)
                #   "self" is the (PyObject*) of the 'self'
                try:
                    # Use the prettyprinter for the func:
                    func = older._gdbframe.read_var('func')
                    return str(func)
                except RuntimeError:
                    return 'PyCFunction invocation (unable to read "func")'

        # This frame isn't worth reporting:
        return False

    def is_waiting_for_gil(self):
        '''Is this frame waiting on the GIL?'''
        # This assumes the _POSIX_THREADS version of Python/ceval_gil.h:
        name = self.inferior_frame().name()
        if name:
            return 'pthread_cond_timedwait' in name

    def is_gc_collect(self):
        '''Is this frame "collect" within the garbage-collector?'''
        return self.inferior_frame().name() == 'collect'

class FrameFilter():

    def __init__(self):
        self.name = "PyshieldPythonFilter"
        self.priority = 100
        self.enabled = True

        # Register this frame filter with the global frame_filters
        # dictionary.
        # gdb.frame_filters[self.name] = self

    def filter(self, frame_iter):
        import itertools
        frame_iter = itertools.imap(PythonFrameDecorator,
                                    frame_iter)
        return frame_iter

#################################################################
#
# Part: Main Code
#
#################################################################

# Create internal python breakpoints
PythonInternalExceptionCatchpoint()
PythonInternalCallCatchpoint()
PythonInternalLineBreakpoint()
PythonInternalVolatileBreakpoint()

# Register commands
PythonIPALoadDataCommand()
PythonIPAFrameCommand()
PythonFileCommand()
PythonSymbolFileCommand()
PythonRunCommand()
PythonBreakpointCommand()
PythonTempBreakpointCommand()
PythonCatchpointCommand()
PythonTempCatchpointCommand()
PythonClearCommand()
PythonDeleteCommand()
PythonEnableCommand()
PythonDisableCommand()
PythonInfoCommand()

# Clear imported symbol table when the inferior exits
gdb.events.exited.connect (
    lambda e : _imported_script_symbol_table.clear()
    )

gdb.execute('set $pyddd_ipa_linux_platform = %d' % sys.platform.startswith('linux'))
# End of libddd.py
