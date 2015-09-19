/*
 * Version number will finally following golden mean 1.6180339...
 *
 *   - Start with version information of "0.1.1" ("major.version.release")
 *   - Increase "release" if source code has changed at all since the
 *     last update
 *   - Increase "version" if any interfaces or export variables has been
 *     added, removed or changed. If only added something, incease the
 *     "release" consecutively. In any other case, reset it to "1".
 *   - If version increased to "0.6.?", next version would be "1.6.1".
 *
 *   The "1.6.1" would be final version, all the interfaces and export
 *   variables of pyddd-ipa will not be changed at all. After that,
 *   each release will first append a "0" at the end of old version,
 *   then increase it up to the golden mean again. For example,
 *
 *     1.6.1.0, 1.6.1.1, ... 1.6.1.8
 *     1.6.1.8.0,
 *     1.6.1.8.0.0, 1.6.1.0.1, 1.6.1.0.2, 1.6.1.0.3
 *
 * Change Logs:
 *
 *   - Version 0.1.1    jondy.zhao@gmail.com    2014-12-24
 *     * First release.
 *
 */
#include "ipa.h"
static const char *PYDDD_IPA_VERSION = "0.1.2";

#if defined(TEST_IPA)
#define static
#endif

static char* find_name_in_list(const char *name, const char *namelist);
static void pyddd_ipa_set_volatile_breakpoint(const int enabled,
                                              const long thread_id,
                                              PyFrameObject *f_frame,
                                              PyObject* co_filename,
                                              const int lineno);

static pthread_mutex_t mutex_hit_count = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t mutex_object_entry = PTHREAD_MUTEX_INITIALIZER;

struct pyddd_ipa_t_volatile_breakpoint pyddd_ipa_volatile_breakpoint={0};
struct pyddd_ipa_t_breakpoint
pyddd_ipa_breakpoint_table[PYDDD_IPA_MAX_BREAKPOINT]={0};

int pyddd_ipa_breakpoint_top=PYDDD_IPA_BREAKPOINT_PAGE;
/* Only increased to avoid crash in multi-threads */
int pyddd_ipa_breakpoint_counter=0;

/* Set when any internal python breakpoint is hit */
int pyddd_ipa_hit_flag=0;

char * pyddd_ipa_python_catch_exceptions=NULL;
char * pyddd_ipa_python_catch_functions=NULL;

/* Use function pointer, so python-ipa.dll need not bind to special
   python version */
char* (*FPyString_AsString)(PyObject *o)=NULL;
int (*FPyFrame_GetLineNumber)(PyFrameObject *frame)=NULL;
void (*FPy_DecRef)(PyObject *)=NULL;
int (*FPyObject_IsTrue)(PyObject *)=NULL;
Py_ssize_t (*FPyString_Size)(PyObject *string)=NULL;
void (*FPyEval_SetTrace)(Py_tracefunc func, PyObject *arg)=NULL;
PyThreadState* (*FPyThreadState_Get)(void)=NULL;
PyObject* (*FPyObject_Str)(PyObject *o)=NULL;
PyObject* (*FPyObject_Repr)(PyObject *o)=NULL;
PyObject* (*FPyTuple_GetItem)(PyObject *p, Py_ssize_t pos)=NULL;
PyObject* (*FPyDict_GetItem)(PyObject *p, PyObject *key)=NULL;
PyObject* (*FPyDict_GetItemString)(PyObject *p, const char *key)=NULL;
int (*FPyDict_SetItem)(PyObject *p, PyObject *key, PyObject *val)=NULL;
int (*FPyDict_SetItemString)(PyObject *p,
                             const char *key,
                             PyObject *val)=NULL;
int (*FPyDict_Next)(PyObject *p,
                    Py_ssize_t *ppos,
                    PyObject **pkey,
                    PyObject **pvalue)=NULL;
PyObject* (*FPyDict_Keys)(PyObject *p)=NULL;

PyObject* (*FPyObject_Type)(PyObject *o)=NULL;
PyObject* (*FPyObject_GetIter)(PyObject *o)=NULL;
PyObject* (*FPyIter_Next)(PyObject *o)=NULL;

void (*FPyErr_Clear)(void)=NULL;
void (*FPyErr_PrintEx)(int set_sys_last_vars)=NULL;
PyObject* (*FPyErr_Occurred)(void)=NULL;
PyObject* (*FPy_CompileStringFlags)(const char *str,
                                    const char *filename,
                                    int start,
                                    PyCompilerFlags *flags)=NULL;
PyObject* (*FPyEval_EvalCode)(PyCodeObject *co,
                              PyObject *globals,
                              PyObject *locals)=NULL;

const char *
pyddd_ipa_version(void)
{
  return PYDDD_IPA_VERSION;
}

/* Rename varialbe in breakpoint context to avoid name conflict */
#define frame pyddd_ipa_current_frame
#define thread pyddd_ipa_current_thread
#define _filename pyddd_ipa_current_filename
#define _lineno pyddd_ipa_current_lineno
#define bp pyddd_ipa_current_breakpoint
#define name pyddd_ipa_current_funcname
#define excname pyddd_ipa_current_excname

int
pyddd_ipa_trace_trampoline(PyObject *self,
                           PyFrameObject *frame,
                           int what,
                           PyObject *arg)
{
  register long thread = frame->f_tstate->thread_id;
  register int _lineno = (*FPyFrame_GetLineNumber)(frame);
  PyObject *co_filename = frame->f_code->co_filename;
  register char *_filename = (*FPyString_AsString)(co_filename);

  /* py-catch call:
     Search name within pyddd_ipa_python_catch_functions.
     */
  if (what == PyTrace_CALL) {
    char *name=(*FPyString_AsString)(frame->f_code->co_name);
    if (pyddd_ipa_python_catch_functions \
        && find_name_in_list(name, pyddd_ipa_python_catch_functions)) {
      pyddd_ipa_volatile_breakpoint.enabled = 0;
      asm("pyddd_ipa_catch_call_addr:");
      pyddd_ipa_hit_flag ++;
    };
    return 0;
  }

  /* py-catch exception:
     Search exception name within pyddd_ipa_python_catch_exceptions.
     */
  else if (what == PyTrace_EXCEPTION) {
    char *excname=(char*)((PyTypeObject*)
                          ((*FPyTuple_GetItem)(arg, 0)))->tp_name;
    if (pyddd_ipa_python_catch_exceptions
        && find_name_in_list(excname,
                             pyddd_ipa_python_catch_exceptions)) {
      pyddd_ipa_volatile_breakpoint.enabled = 0;
      asm("pyddd_ipa_catch_exception_addr:");
      pyddd_ipa_hit_flag ++;
    };
    return 0;
  }

  if (what == PyTrace_LINE) {

    /* Check volatile breakpoint */
    {
      register struct pyddd_ipa_t_volatile_breakpoint *vp;
      vp = &pyddd_ipa_volatile_breakpoint;
      if (vp->enabled
          && vp->thread_id == thread
          && (!vp->lineno
              || (vp->lineno>0 && vp->lineno == _lineno)
              || (vp->lineno<0 && -vp->lineno<_lineno))
          && (!vp->f_frame || vp->f_frame == frame)
          && (!vp->co_filename || vp->co_filename == co_filename)) {
        vp->enabled --;
        if (!vp->enabled) {
          asm("pyddd_ipa_volatile_breakpoint_addr:");
          pyddd_ipa_hit_flag ++;
          return 0;
        }
      }
    }

    /* Check normal breakpoints which at filename:lineno exactly. */
    if (_filename) {
      register struct pyddd_ipa_t_breakpoint *bp;
      int filename_size=0;
      int rindex;

      bp = pyddd_ipa_breakpoint_table;
      for (rindex = 0;
           rindex < pyddd_ipa_breakpoint_counter;
           rindex++, bp++) {

        /* Ignore deleted bpnum, disabled bpnum, not lineno, not
           thread */
        if (!bp->bpnum
            || !bp->enabled
            || (bp->thread_id && bp->thread_id != thread)
            || _lineno != bp->lineno) {
          if (bp->enabled < 0) ++(bp->enabled);
          continue;
        }
        if (bp->enabled < 0) ++(bp->enabled);

        /* Good preformace, but need more complex mechanism */
        if (bp->co_filename && bp->co_filename != co_filename)
          continue;

        /* First compare the filename size so that we can quickly
           exclude most of files. */
        if (!filename_size)
          filename_size = strlen(_filename);
        if (filename_size != bp->filename_size
            || strcmp(bp->filename, _filename))
          continue;

        pthread_mutex_lock (&mutex_hit_count);
        bp->hit_count ++;
        /* Take ignore_count into account */
        if (bp->ignore_count) {
          if (bp->hit_count == bp->ignore_count)
            bp->hit_count = 0;
          else {
            pthread_mutex_unlock (&mutex_hit_count);
            continue;
          }
        }
        pthread_mutex_unlock (&mutex_hit_count);

        /* Eval breakpoint condition */
        if (bp->condition) {
          PyObject *exprobj;
          PyObject *result;

          /* Use empty filename to avoid obj added to object entry table */
          exprobj = (*FPy_CompileStringFlags)(bp->condition,
                                              "",
                                              Py_eval_input,
                                              NULL
                                              );
          if (!exprobj) {
            (*FPyErr_Clear)();
            continue;
          }

          /* Clear flag use_tracing in current PyThreadState to avoid
             tracing evaluation self, but if the evluation expression
             includes some call of c function, and there is some
             breakpoint hit, I don't know what will happen.
          */
          frame->f_tstate->use_tracing = 0;
          result = (*FPyEval_EvalCode)((PyCodeObject*)exprobj,
                                       frame->f_globals,
                                       frame->f_locals);
          frame->f_tstate->use_tracing = 1;
          (*FPy_DecRef)(exprobj);

          if (result == NULL) {
            (*FPyErr_Clear)();
            continue;
          }

          if ((*FPyObject_IsTrue)(result) != 1) {
            (*FPy_DecRef)(result);
            continue;
          }
          (*FPy_DecRef)(result);
        }

        /* Here is c breakpoint in GDB */
        pyddd_ipa_volatile_breakpoint.enabled = 0;
        asm("pyddd_ipa_breakpoint_addr:");
        pyddd_ipa_hit_flag ++;
        break;
      }
    }
  }
  return 0;
}

int
pyddd_ipa_profile_trampoline(PyObject *self,
                             PyFrameObject *frame,
                             int what,
                             PyObject *arg)
{
  return 0;
}

#undef frame
#undef thread
#undef _filename
#undef _lineno
#undef bp
#undef name
#undef excname


/*
 * Format of namelist:
 *
 *  - Separating name pattern by one whitespace.
 *  - '?' stands for one any character in name pattern
 *  - Name patterns start with '*' match any same prefix.
 *    Espcially, name pattern "*" matches any name.
 *  - Name patterns end with '*' match any same suffix.
 *
 */
static char *
find_name_in_list(const char *name, const char *namelist)
{
  register char *s=(char*)name;
  register char *p=(char*)namelist;
  if (s && *s && p && *p)
    while (*p) {
      while (*s && (*p == *s || *p == '?'))
        p++, s++;
      /* name end */
      if (!*s) {
        if (!*p || *p == '*' || *p == ' ')
          return (char*)name;
      }
      /* asterisk match */
      else if (*p == '*') {
        p++;
        /* suffix match */
        if (*p == 0 || *p == ' ')
          return (char*)name;
        /* prefix match */
        if (*s) {
          register char *t=p;
          int i=0;
          int j=strlen(s);
          while (*t && *t != ' ' && (++i))
            t++;
          if (i <= j) {
            s += j;
            do {
              t--, s--;
            } while (*t==*s && i--);
            if (!i)
              return (char*)name;
          }
        }
      }
      /* next pattern */
      s = (char*)name;
      if ((p=strchr(p, ' ')) == NULL)
        break;
      p++;
    }
  return NULL;
}

/*
 * When you insert/update/delete breakpoints in pyddd-ipa, to be
 * sure the intefior is suspend, and there is no any running
 * thread. Or any other thread runs in non-stop mode. That is to say,
 * they can't read/write the breakpoints.
 */
void
pyddd_ipa_update_breakpoint(const int rindex,
                            const int bpnum,
                            const int locnum,
                            const long thread_id,
                            const char *condition,
                            const int ignore_count,
                            const int enabled,
                            const int lineno,
                            const char *filename
                            )
{
  register struct pyddd_ipa_t_breakpoint *p;
  assert (rindex >= 0 && rindex < PYDDD_IPA_MAX_BREAKPOINT);
  assert (bpnum>0);
  assert (filename);
  p = pyddd_ipa_breakpoint_table + rindex;

  p->locnum = locnum;
  p->thread_id = thread_id;
  p->condition = (char*)condition;
  p->ignore_count = ignore_count;
  p->hit_count = 0;
  p->enabled = enabled;
  p->lineno = lineno;
  p->filename = (char*)filename;
  p->filename_size = strlen(filename);
  p->co_filename = NULL;
  p->bpnum = bpnum;
}

int
pyddd_ipa_insert_breakpoint(const int bpnum,
                            const int locnum,
                            const long thread_id,
                            const char *condition,
                            const int ignore_count,
                            const int enabled,
                            const int lineno,
                            const char *filename
                            )
{
  register struct pyddd_ipa_t_breakpoint *p;
  register int rindex = pyddd_ipa_breakpoint_counter;

  /* Find a index in breakpoint table */
  if (rindex < pyddd_ipa_breakpoint_top)
    pyddd_ipa_breakpoint_counter ++;
  else {
    for (rindex = 0, p = pyddd_ipa_breakpoint_table;
         rindex < PYDDD_IPA_MAX_BREAKPOINT;
         rindex++, p++) {
      if (!p->bpnum)
        break;
    }
    if (rindex >= PYDDD_IPA_MAX_BREAKPOINT)
      return -1;
    if (rindex >= pyddd_ipa_breakpoint_top) {
      assert (pyddd_ipa_breakpoint_top < PYDDD_IPA_MAX_BREAKPOINT);
      pyddd_ipa_breakpoint_top += PYDDD_IPA_BREAKPOINT_PAGE;
      pyddd_ipa_breakpoint_counter ++;
    }
  }

  /* Insert a breakpoint entry */
  p = pyddd_ipa_breakpoint_table + rindex;
  pyddd_ipa_update_breakpoint(rindex, bpnum, locnum, thread_id,
                              condition, ignore_count, enabled,
                              lineno, filename);

  return rindex;
}

void
pyddd_ipa_remove_breakpoint(const int rindex)
{
  if (rindex >= 0
      && rindex < PYDDD_IPA_MAX_BREAKPOINT
      && pyddd_ipa_breakpoint_table[rindex].bpnum > 0) {
    /* In order to support multi-threads, don't decrease counter */
    pyddd_ipa_breakpoint_table[rindex].bpnum = 0;
  }
}

static void
pyddd_ipa_set_volatile_breakpoint(const int enabled,
                                  const long thread_id,
                                  PyFrameObject *f_frame,
                                  PyObject* co_filename,
                                  const int lineno)
{
  register struct pyddd_ipa_t_volatile_breakpoint *vp;
  assert(thread_id);

  vp = &pyddd_ipa_volatile_breakpoint;
  vp->enabled = enabled;
  vp->thread_id = thread_id;
  vp->f_frame = f_frame;
  vp->co_filename = co_filename;
  vp->lineno = lineno;
}

/* Running command: step, next, finish, advance, untill, advance */
int
pyddd_ipa_step_command(int count)
{
  register PyThreadState *tstate=(*FPyThreadState_Get)();
  assert (count);
  pyddd_ipa_set_volatile_breakpoint(count,
                                    tstate->thread_id,
                                    NULL,
                                    NULL,
                                    0
                                    );
  return 0;
}

int
pyddd_ipa_next_command(int count)
{
  register PyThreadState *tstate=(*FPyThreadState_Get)();
  assert (count);
  pyddd_ipa_set_volatile_breakpoint(count,
                                    tstate->thread_id,
                                    tstate->frame,
                                    NULL,
                                    0
                                    );
  return 0;
}

int
pyddd_ipa_finish_command(void)
{
  register PyThreadState *tstate=(*FPyThreadState_Get)();
  register PyFrameObject *frame=tstate->frame;
  pyddd_ipa_set_volatile_breakpoint(1,
                                    tstate->thread_id,
                                    frame->f_back,
                                    NULL,
                                    0
                                    );
  return 0;
}

int
pyddd_ipa_until_command(int lineno)
{
  register PyThreadState *tstate=(*FPyThreadState_Get)();
  register PyFrameObject *frame=tstate->frame;
  if (!lineno)
    lineno = -(*FPyFrame_GetLineNumber)(frame);
  pyddd_ipa_set_volatile_breakpoint(1,
                                    tstate->thread_id,
                                    frame->f_back,
                                    NULL,
                                    lineno
                                    );
  return 0;
}

int
pyddd_ipa_advance_command(int lineno)
{
  register PyThreadState *tstate=(*FPyThreadState_Get)();
  PyObject *co_filename = tstate->frame->f_code->co_filename;
  pyddd_ipa_set_volatile_breakpoint(1,
                                    tstate->thread_id,
                                    NULL,
                                    co_filename,
                                    lineno
                                    );
  return 0;
}

/*
 * Frame routines
 */
PyFrameObject *
pyddd_ipa_frame_older(PyFrameObject *frame)
{
  if (frame)
    return frame->f_back;
  return NULL;
}

PyFrameObject *
pyddd_ipa_frame_lookup(PyFrameObject *frame, const char *name)
{
  if (frame && name && *name)
    while (strcmp(name, (*FPyString_AsString)(frame->f_code->co_name))
           && (frame = frame->f_back));
  return frame;
}

const char *
pyddd_ipa_frame_filename(PyFrameObject *frame)
{
  if (!frame)
    frame=(*FPyThreadState_Get)()->frame;
  assert (frame);
  return (*FPyString_AsString)(frame->f_code->co_filename);
}

int
pyddd_ipa_frame_lineno(PyFrameObject *frame)
{
  if (!frame)
    frame=(*FPyThreadState_Get)()->frame;
  assert (frame);
  return (*FPyFrame_GetLineNumber)(frame);
}

const char *
pyddd_ipa_frame_name(PyFrameObject *frame)
{
  if (!frame)
    frame=(*FPyThreadState_Get)()->frame;
  assert (frame);
  return (*FPyString_AsString)(frame->f_code->co_name);
}

const char *
pyddd_ipa_frame_locals(PyFrameObject *frame)
{
  assert (frame);
  if (frame->f_locals)
    return (*FPyString_AsString) \
      ((*FPyObject_Repr)((*FPyDict_Keys)(frame->f_locals)));
  return pyddd_ipa_frame_varnames(frame);
}

const char *
pyddd_ipa_frame_globals(PyFrameObject *frame)
{
  assert (frame);
  assert (frame->f_globals);
  return (*FPyString_AsString)\
    ((*FPyObject_Repr)((*FPyDict_Keys)(frame->f_globals)));
}

const char *
pyddd_ipa_frame_varnames(PyFrameObject *frame)
{
  assert (frame);
  return (*FPyString_AsString)((*FPyObject_Repr)(frame->f_code->co_varnames));
}

const char *
pyddd_ipa_frame_cellvars(PyFrameObject *frame)
{
  assert (frame);
  return (*FPyString_AsString)((*FPyObject_Repr)(frame->f_code->co_cellvars));
}

/*
 * Get values from frame, index == -1, means got from globals
 */
const char *
pyddd_ipa_frame_values(PyFrameObject *frame, char *varname, int index)
{
  assert (frame);
  if (index == -1) {
    PyObject *key, *value;
    Py_ssize_t pos = 0;
    while ((*FPyDict_Next)(frame->f_globals, &pos, &key, &value))
      if (key && value)
        if (!strcmp(varname, (*FPyString_AsString)((*FPyObject_Str)(key))))
          return pyddd_ipa_format_object(value);
    if ((*FPyErr_Occurred)())
      (*FPyErr_PrintEx)(0);
    return NULL;
  }
  return pyddd_ipa_format_object(frame->f_localsplus[index]);
}

const char *
pyddd_ipa_frame_variable(PyFrameObject *frame, char *varname, int global)
{
  PyObject *key, *value;
  Py_ssize_t pos = 0;
  assert (frame);
  while ((*FPyDict_Next)(global ? frame->f_globals : frame->f_locals,
                         &pos,
                         &key,
                         &value
                         ))
    if (key && value)
      if (!strcmp(varname, (*FPyString_AsString)((*FPyObject_Str)(key))))
        return pyddd_ipa_format_object(value);
  if ((*FPyErr_Occurred)())
    (*FPyErr_PrintEx)(0);
  return NULL;
}

/* Alter variables in python */
int
pyddd_ipa_alter_variable(PyFrameObject *frame,
                         char *name,
                         char *expr,
                         int global
                         )
{
  PyObject *exprobj;
  PyObject *result;
  int oldvalue;
  PyThreadState *tstate=(*FPyThreadState_Get)();

  /* Use empty filename to avoid obj added to object entry table */
  exprobj = (*FPy_CompileStringFlags)(expr, "", Py_eval_input, NULL);
  if (!exprobj) {
    if ((*FPyErr_Occurred)())
      (*FPyErr_PrintEx)(0);
    return 1;
  }

  if (!frame)
    frame = tstate->frame;
  assert (frame);

  oldvalue = tstate->use_tracing;
  tstate->use_tracing = 0;
  result = (*FPyEval_EvalCode)((PyCodeObject*)exprobj,
                               frame->f_globals,
                               frame->f_locals
                               );
  tstate->use_tracing = oldvalue;
  (*FPy_DecRef)(exprobj);

  if (result){
    PyObject *p, *key, *value;
    Py_ssize_t pos = 0;
    p = global ? frame->f_globals : frame->f_locals;
    while ((*FPyDict_Next)(p, &pos, &key, &value))
      if (key && value)
        if (!strcmp(name, (*FPyString_AsString)((*FPyObject_Str)(key))))
          return (*FPyDict_SetItem)(p, key, result);
  }
  if ((*FPyErr_Occurred)())
    (*FPyErr_PrintEx)(0);
  if (result)
    (*FPy_DecRef)(result);
  return 1;
}

const char *
pyddd_ipa_eval(PyFrameObject *frame, char *expr)
{
  PyObject *exprobj;
  PyObject *result;
  PyThreadState *tstate = (*FPyThreadState_Get)();
  int oldvalue;
  assert (expr);

  /* Use empty filename to avoid obj added to object entry table */
  exprobj = (*FPy_CompileStringFlags)(expr, "", Py_eval_input, NULL);
  if (!exprobj) {
    if ((*FPyErr_Occurred)())
      (*FPyErr_PrintEx)(0);
    return NULL;
  }

  if (!frame)
    frame = tstate -> frame;
  oldvalue = tstate->use_tracing;
  tstate->use_tracing = 0;
  result = (*FPyEval_EvalCode)((PyCodeObject*)exprobj,
                               frame->f_globals,
                               frame->f_locals
                               );
  tstate->use_tracing = oldvalue;
  (*FPy_DecRef)(exprobj);

  if (!result){
    if ((*FPyErr_Occurred)())
      (*FPyErr_PrintEx)(0);
    return NULL;
  }

  (*FPy_DecRef)(result);
  /* use the result before gc works */
  return (*FPyString_AsString)((*FPyObject_Repr)(result));
}

const char *
pyddd_ipa_iter_next(PyObject *iter)
{
  PyObject *item=NULL;
  if (!iter)
    if (!(item = (*FPyIter_Next)(iter)))
      (*FPy_DecRef)(iter);
  if (!item)
    return NULL;
  (*FPy_DecRef)(item);
  return (*FPyString_AsString)(item);
}

/*
 * int, string, float => repr(o)
 * Others => ClsName
 */
const char *
pyddd_ipa_format_object(PyObject *o)
{
  assert (o);
  const char *t=((PyTypeObject*)(*FPyObject_Type)(o))->tp_name;
  if (!strcmp(t, "int") \
      && !strcmp(t, "long")
      && !strcmp(t, "float")
      && !strcmp(t, "str")
      && !strcmp(t, "unicode"))
    return t;
  return (*FPyString_AsString)((*FPyObject_Repr)(o));
}

/* end of ipa.c */
