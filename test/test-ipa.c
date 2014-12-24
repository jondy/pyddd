#include "../ipa.h"

extern int pyddd_ipa_hit_flag;

extern struct pyddd_ipa_t_volatile_breakpoint
pyddd_ipa_volatile_breakpoint;
extern struct pyddd_ipa_t_breakpoint pyddd_ipa_breakpoint_table[];

extern int pyddd_ipa_breakpoint_top;
extern int pyddd_ipa_breakpoint_counter;

extern char * pyddd_ipa_python_catch_exceptions;
extern char * pyddd_ipa_python_catch_functions;

static void 
init_func(void)
{
#if PY_MAJOR_VERSION ==3
  FPyString_AsString     = PyBytes_AsString;
  FPyString_Size         = PyBytes_Size;
#else
  FPyString_AsString     = PyString_AsString;
  FPyString_Size         = PyString_Size;
#endif

  FPyFrame_GetLineNumber = PyFrame_GetLineNumber;
  FPy_CompileStringFlags = Py_CompileStringFlags;
  FPyEval_EvalCode       = PyEval_EvalCode;
  FPyEval_SetTrace       = PyEval_SetTrace;
  FPy_DecRef             = Py_DecRef;
  FPyObject_IsTrue       = PyObject_IsTrue;
  FPyThreadState_Get     = PyThreadState_Get;
  FPyObject_Str          = PyObject_Str;
  FPyObject_Repr         = PyObject_Repr;
  FPyTuple_GetItem       = PyTuple_GetItem;
  FPyDict_GetItem        = PyDict_GetItem;
  FPyDict_GetItemString  = PyDict_GetItemString;
  FPyDict_SetItem        = PyDict_SetItem;
  FPyDict_SetItemString  = PyDict_SetItemString;
  FPyDict_Next           = PyDict_Next;
  FPyDict_Keys           = PyDict_Keys;
  FPyObject_GetIter      = PyObject_GetIter;
  FPyObject_Type         = PyObject_Type;
  FPyIter_Next           = PyIter_Next;
  FPyErr_Clear           = PyErr_Clear;
  FPyErr_PrintEx         = PyErr_PrintEx;
  FPyErr_Occurred        = PyErr_Occurred;
}

static PyFrameObject *
make_test_frame(char *code, char *filename)
{
  PyCodeObject *co_code;
  PyObject *f_locals, *f_globals;
  PyThreadState *tstate=(*FPyThreadState_Get)();
  PyFrameObject *frame=tstate->frame;

  co_code = (PyCodeObject*)Py_CompileStringFlags(code,
                                                 filename,
                                                 Py_file_input,
                                                 NULL);
  if (!co_code) {
    if (PyErr_Occurred())
      PyErr_PrintEx(0);
    return NULL;
  }

  f_locals = Py_BuildValue("{sisss(ii)}",
                           "i", 2,
                           "name", "jondy",
                           "rlist", 3, 5
                           );
  f_globals = Py_BuildValue("{si}",
                           "i", 4
                            );
  assert (f_locals && f_globals);
  return PyFrame_New(tstate, co_code, f_globals, f_locals);
}

/*
 * test find_name_in_list
 */
extern char* find_name_in_list(const char *name, const char *namelist);
void test_find_name_in_list(void)
{
  assert (!find_name_in_list (NULL, NULL));
  assert (!find_name_in_list ("", NULL));
  assert (!find_name_in_list ("foo", NULL));

  assert (find_name_in_list ("foo", "foo"));
  assert (find_name_in_list ("foo", "f?o"));
  assert (find_name_in_list ("foo", "f*"));
  assert (find_name_in_list ("foo", "*o"));
  assert (find_name_in_list ("foo", "f*o"));

  assert (find_name_in_list ("foo", "hello foo"));
  assert (find_name_in_list ("foo", "hello f?o"));
  assert (find_name_in_list ("foo", "hello f*"));
  assert (find_name_in_list ("foo", "hello *o"));
  assert (find_name_in_list ("foo", "hello f*o"));

  assert (find_name_in_list ("foo", "hello foo fight"));
  assert (find_name_in_list ("foo", "hello f?o fight"));
  assert (find_name_in_list ("foo", "hello f* fight"));
  assert (find_name_in_list ("foo", "hello *o fight"));
  assert (find_name_in_list ("foo", "hello f*o fight"));

  assert (!find_name_in_list ("foo", "fo"));
  assert (!find_name_in_list ("foo", "f?"));
  assert (!find_name_in_list ("foo", "f*b"));
  assert (!find_name_in_list ("foo", "*ooo"));
  assert (!find_name_in_list ("foo", "*koo"));

  assert (!find_name_in_list ("foo", "hello fo"));
  assert (!find_name_in_list ("foo", "hello f?"));
  assert (!find_name_in_list ("foo", "hello f*b"));
  assert (!find_name_in_list ("foo", "hello *ooo"));
  assert (!find_name_in_list ("foo", "hello *koo"));

  assert (!find_name_in_list ("foo", "hello fo fight"));
  assert (!find_name_in_list ("foo", "hello f? fight"));
  assert (!find_name_in_list ("foo", "hello f*b fight"));
  assert (!find_name_in_list ("foo", "hello *ooo fight"));
  assert (!find_name_in_list ("foo", "hello *koo fight"));
}

void test_pyddd_ipa_insert_breakpoint(void)
{
#define ft pyddd_ipa_insert_breakpoint
  int n=pyddd_ipa_breakpoint_top;
  int i=pyddd_ipa_breakpoint_counter;
  int k=n/2;
  for (; n ; n--, i++)
    assert (i == ft(i+1, 0, 0, NULL, 0, 1, 0, "foo.py"));

  pyddd_ipa_remove_breakpoint (k);
  assert (k == ft(i+1, 0, 0, NULL, 0, 1, 0, "foo.py"));

  n=pyddd_ipa_breakpoint_top;
  assert (n == ft(i+2, 0, 0, NULL, 0, 1, 0, "foo.py"));
#undef ft
}

void test_pyddd_ipa_frame_variable(void)
{
#define ft pyddd_ipa_frame_variable
  PyFrameObject *frame;
  frame = make_test_frame("", "");
  assert (frame);
  assert (*ft(frame, "i", 0) == 0x32);
  assert (*ft(frame, "i", 1) == 0x34);
  Py_DECREF((PyObject*)frame);
#undef ft
}

void test_pyddd_ipa_alter_variable(void)
{
#define ft pyddd_ipa_alter_variable
#define ft2 pyddd_ipa_frame_variable
  PyFrameObject *frame;
  frame = make_test_frame("", "");
  assert (frame);
  assert (!ft(frame, "i", "7*3", 0));
  assert (!strcmp(ft2(frame, "i", 0), "21"));

  assert (!ft(frame, "i", "4*7", 1));
  assert (!strcmp(ft2(frame, "i", 1), "28"));

  Py_DECREF((PyObject*)frame);
#undef ft
#undef ft2
}

void test_pyddd_ipa_eval(void)
{
#define ft pyddd_ipa_eval
  PyFrameObject *frame;
  frame = make_test_frame("", "");
  assert (frame);
  assert (*ft(frame, "i*3") == 0x36);
  assert (*ft(frame, "rlist[1]") == 0x35);
  Py_DECREF((PyObject*)frame);
#undef ft
}

void test_pyddd_ipa_frame_locals(void)
{
#define ft pyddd_ipa_frame_locals
  PyFrameObject *frame;
  char *s;
  frame = make_test_frame("i+=2", "foo.py");
  assert (frame);
  s = (char*)ft(frame);  
  assert(s && strstr(s, "'i'") && strstr(s, "'name'") && strstr(s, "'rlist'"));
  Py_DECREF((PyObject*)frame);
#undef ft
}

void test_pyddd_ipa_frame_globals(void)
{
#define ft pyddd_ipa_frame_globals
  PyFrameObject *frame;
  char *s;
  frame = make_test_frame("i+=2", "foo.py");
  assert (frame);
  s = (char*)ft(frame);  
  assert(s && strstr(s, "'i'"));
  Py_DECREF((PyObject*)frame);
#undef ft
}

void test_pyddd_ipa_format_object(void)
{
#define ft pyddd_ipa_format_object
  char *s;
  PyObject *p;

  p = Py_BuildValue("i", 5);
  s = (char*)ft(p);
  assert (s && !strcmp(s, "5"));
  Py_DECREF(p);

  p = Py_BuildValue("I", 2L);
  s = (char*)ft(p);
  assert (s && !strcmp(s, "2"));
  Py_DECREF(p);

  p = Py_BuildValue("f", 1.618);
  s = (char*)ft(p);
  assert (s && !strcmp(s, "1.618"));
  Py_DECREF(p);

  p = Py_BuildValue("s", "pyddd");
  s = (char*)ft(p);
  assert (s && !strcmp(s, "'pyddd'"));
  Py_DECREF(p);

#undef ft
}
   
void test_pyddd_ipa_trace_trampoline(void)
{
  int i;
#define ft pyddd_ipa_trace_trampoline
  PyFrameObject *frame;
  frame = make_test_frame("j=2", "foo.py");
  assert (frame);

  pyddd_ipa_hit_flag = 0;
  ft(NULL, frame, PyTrace_LINE, NULL);
  assert (!pyddd_ipa_hit_flag);

  pyddd_ipa_step_command(1);
  ft(NULL, frame, PyTrace_LINE, NULL);
  assert (pyddd_ipa_hit_flag == 1);

  pyddd_ipa_next_command(1);
  ft(NULL, frame, PyTrace_LINE, NULL);
  assert (pyddd_ipa_hit_flag == 2);

  pyddd_ipa_volatile_breakpoint.enabled = 0;
  pyddd_ipa_hit_flag = 0;
  pyddd_ipa_insert_breakpoint(1, 0, 0, NULL, 0, 1, 10, "foo.py");
  pyddd_ipa_insert_breakpoint(1, 0, 0, NULL, 0, 0, 1, "foo.py");
  ft(NULL, frame, PyTrace_LINE, NULL);
  assert (!pyddd_ipa_hit_flag);
  
  i = pyddd_ipa_insert_breakpoint(1, 0, 0, NULL, 0, 1, 1, "foo.py");
  pyddd_ipa_hit_flag = 0;
  ft(NULL, frame, PyTrace_LINE, NULL);
  ft(NULL, frame, PyTrace_LINE, NULL);
  assert (pyddd_ipa_hit_flag == 2);

  pyddd_ipa_hit_flag = 0;
  pyddd_ipa_update_breakpoint(i, 1, 0, 0, NULL, 3, 1, 1, "foo.py");
  ft(NULL, frame, PyTrace_LINE, NULL);
  ft(NULL, frame, PyTrace_LINE, NULL);
  ft(NULL, frame, PyTrace_LINE, NULL);
  ft(NULL, frame, PyTrace_LINE, NULL);
  ft(NULL, frame, PyTrace_LINE, NULL);
  assert (pyddd_ipa_hit_flag == 1);

  pyddd_ipa_hit_flag = 0;
  pyddd_ipa_update_breakpoint(i, 1, 0, 0, "i==1", 0, 1, 1, "foo.py");
  ft(NULL, frame, PyTrace_LINE, NULL);
  assert (!pyddd_ipa_hit_flag);

  pyddd_ipa_hit_flag = 0;
  pyddd_ipa_update_breakpoint(i, 1, 0, 0, "i==2", 0, 1, 1, "foo.py");
  ft(NULL, frame, PyTrace_LINE, NULL);
  assert (pyddd_ipa_hit_flag == 1);

  
  Py_DECREF((PyObject*)frame);

#undef ft
}

int
main(int argc, char **argv)
{
  init_func();
  test_find_name_in_list();
  test_pyddd_ipa_insert_breakpoint();

  Py_SetProgramName(argv[0]);
  Py_Initialize();
  PySys_SetArgvEx(argc, argv, 0);

  test_pyddd_ipa_trace_trampoline();
  test_pyddd_ipa_frame_variable();

  test_pyddd_ipa_alter_variable();
  test_pyddd_ipa_eval();
  test_pyddd_ipa_frame_locals();
  test_pyddd_ipa_frame_globals();

  test_pyddd_ipa_format_object();

  Py_Exit(0);
  return 0;
}
