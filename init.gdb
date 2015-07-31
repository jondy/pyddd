#
# gdb init script for pyddd.
#
dont-repeat

define python-ipa-initialize
  dont-repeat
  if $pyddd_ipa_linux_platform
      set $python_ipa_handle = dlopen("pyddd-ipa.so", 2)
  else
      set $python_ipa_handle = LoadLibraryA("pyddd-ipa.dll")
  end
  set $python_ipa_trace_flag = PyEval_SetTrace(pyddd_ipa_trace_trampoline, 0)
  set $python_major_version = *(char*)Py_GetVersion()
  if $python_major_version == 0x33
      set var pyddd_ipa_pystring_asstring = PyBytes_AsString
      set var pyddd_ipa_pystring_size = PyBytes_Size
  else
      set var pyddd_ipa_pystring_asstring = PyString_AsString
      set var pyddd_ipa_pystring_size = PyString_Size
  end
  set var pyddd_ipa_pyobject_str = PyObject_Str
  set var pyddd_ipa_pyobject_repr = PyObject_Repr
  set var pyddd_ipa_pyframe_getlinenumber = PyFrame_GetLineNumber
  set var pyddd_ipa_py_compilestringflags = Py_CompileStringFlags
  set var pyddd_ipa_pyeval_evalcode = PyEval_EvalCode
  set var pyddd_ipa_pyeval_settrace = PyEval_SetTrace
  set var pyddd_ipa_py_decref = Py_DecRef
  set var pyddd_ipa_pyobject_istrue = PyObject_IsTrue
  set var pyddd_ipa_pythreadstate_get = PyThreadState_Get
  set var pyddd_ipa_pytuple_getitem = PyTuple_GetItem
  set var pyddd_ipa_pydict_getitem = PyDict_GetItem
  set var pyddd_ipa_pydict_getitemstring = PyDict_GetItemString
  set var pyddd_ipa_pydict_setitem = PyDict_SetItem
  set var pyddd_ipa_pydict_setitemstring = PyDict_SetItemString
  set var pyddd_ipa_pydict_next = PyDict_Next
  set var pyddd_ipa_pydict_keys = PyDict_Keys
  set var pyddd_ipa_pyobject_type = PyObject_Type
  set var pyddd_ipa_pyobject_getiter = PyObject_GetIter
  set var pyddd_ipa_pyiter_next = PyIter_Next
  set var pyddd_ipa_pyerr_clear = PyErr_Clear
  set var pyddd_ipa_pyerr_printex = PyErr_PrintEx
  set var pyddd_ipa_pyerr_occurred = PyErr_Occurred

  # upload breakpoints and catchpoints
  python-ipa-load-data

  # clear python frame
  python-ipa-frame teardown
end

alias py-exec-file = file

def py-start
  dont-repeat
  py-tcatch call <module>
  py-run
end

alias py-continue = continue

def py-step
  if $argc == 0
    call pyddd_ipa_step_command (1)
  else
    call pyddd_ipa_step_command ($arg0)
  end
  continue
end

def py-next
  if $argc == 0
    call pyddd_ipa_next_command (1)
  else
    call pyddd_ipa_next_command ($arg0)
  end
  continue
end

def py-finish
  call pyddd_ipa_finish_command()
  continue
end

def py-until
  if $argc == 0
    call pyddd_ipa_until_command (0)
  else
    call pyddd_ipa_until_command ($arg0)
  end
  continue
end

def py-advance
  call pyddd_ipa_until_command ($arg0)
  continue
end

def py-select-frame
  if $argc == 1 && $arg0 >= 0
    python-ipa-frame select $arg0
  end
end

def py-frame
  if $argc == 1
    python-ipa-frame select $arg0
  end
  python-ipa-frame print
end

def py-up
  if $argc == 0
    python-ipa-frame select +1
  else
    python-ipa-frame select $arg0
  end
  python-ipa-frame print
end

def py-down
  if $argc == 0
    python-ipa-frame select -1
  else
    python-ipa-frame select $arg0
  end
  python-ipa-frame print
end

def py-bt
  if $argc == 0
    python-ipa-frame bt
  else
    if $argc == 1
      python-ipa-frame bt $arg0
    else
      if $argc == 2
        python-ipa-frame bt $arg0 $arg1
      else
        if $argc == 3
          python-ipa-frame bt $arg0 $arg1 $arg2
        end
      end
    end
  end
end

def py-print
  print (char*)pyddd_ipa_eval(0, $arg0)
end

def py-set-var
  if $arg0[0] == '/'
    if $arg[[1] == 'g'
      call pyddd_ipa_alter_variable(0, $arg1, $arg2, 1)
    else
      call pyddd_ipa_alter_variable(0, $arg1, $arg2, 0)
    end
  else
    call pyddd_ipa_alter_variable(0, $arg0, $arg1, 0)
  end
end

define hook-continue
  python-ipa-frame teardown
end

define py-list
  if $argc == 0
    python-ipa-frame sources
  else
    if $argc == 1
      python-ipa-frame sources $arg0
    else
      if $argc == 2
        python-ipa-frame sources $arg0 $arg1
      end
    end
  end
end

python
import libddd
end

alias -a pr = py-run

alias -a ps = py-step
alias -a pn = py-next
alias -a pu = py-until

alias -a pb = py-break
alias -a pc = py-catch
alias -a ptb = py-tbreak
alias -a ptc = py-tcatch

alias -a pf = py-frame
alias -a pbt = py-bt
alias -a pup = py-up
alias -a pdo = py-down

alias -a pl = py-list
alias -a pif = py-info

alias -a pp = py-print
alias -a psv = py-set-var

alias -a psf = py-symbol-file

# end of init.gdb
