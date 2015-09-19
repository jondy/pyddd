#if !defined(__PYDDD_IPA_H__)
#define __PYDDD_IPA_H__

#include "Python.h"
#include "frameobject.h"
#include "code.h"
#include "node.h"

#include <pthread.h>

#define PYDDD_IPA_BREAKPOINT_PAGE 256
#define PYDDD_IPA_MAX_BREAKPOINT 1024

/*
 * Internal used to support step/next/until/advance/finish commands.
 *
 * ignore_count is in GDB side, not in python-ipa.
 */
struct pyddd_ipa_t_volatile_breakpoint {
  int enabled;
  long thread_id;
  PyFrameObject *f_frame;
  PyObject *co_filename;
  int lineno;
};

struct pyddd_ipa_t_breakpoint {
  int bpnum;                    /* GDB bpnum */
  int locnum;                   /* Location number */
  long thread_id;               /* Thread id, 0 means any thread */
  char *condition;              /* Python condition expression */
  int ignore_count;             /* Ignore count */
  int hit_count;
  int enabled;                  /* 0 or 1 */

  int lineno;                   /* > 0 */
  char *filename;               /* NOT NULL */
  int filename_size;            /* Size of filename */
  PyObject *co_filename;        /* 0 means unresolved address */
};

const char * pyddd_ipa_version(void);

int
pyddd_ipa_trace_trampoline(PyObject *self,
                           PyFrameObject *frame,
                           int what,
                           PyObject *arg);
int
pyddd_ipa_profile_trampoline(PyObject *self,
                             PyFrameObject *frame,
                             int what,
                             PyObject *arg);

int
pyddd_ipa_insert_breakpoint(const int bpnum,
                            const int locnum,
                            const long thread_id,
                            const char *condition,
                            const int ignore_count,
                            const int enabled,
                            const int lineno,
                            const char *filename
                            );
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
                            );
void pyddd_ipa_remove_breakpoint(const int rindex);

int pyddd_ipa_step_command(int count);
int pyddd_ipa_next_command(int count);
int pyddd_ipa_finish_command(void);
int pyddd_ipa_until_command(int lineno);
int pyddd_ipa_advance_command(int lineno);

PyFrameObject * pyddd_ipa_frame_older(PyFrameObject *frame);
PyFrameObject * pyddd_ipa_frame_lookup(PyFrameObject *frame, const char *name);
const char * pyddd_ipa_frame_filename(PyFrameObject *frame);
int pyddd_ipa_frame_lineno(PyFrameObject *frame);
const char * pyddd_ipa_frame_name(PyFrameObject *frame);
const char * pyddd_ipa_frame_locals(PyFrameObject *frame);
const char * pyddd_ipa_frame_globals(PyFrameObject *frame);
const char * pyddd_ipa_frame_varnames(PyFrameObject *frame);
const char * pyddd_ipa_frame_cellvars(PyFrameObject *frame);
const char * pyddd_ipa_frame_values(PyFrameObject *frame,
                                    char *varname,
                                    int index);
const char * pyddd_ipa_frame_variable(PyFrameObject *frame,
                                      char *varname,
                                      int global);

int pyddd_ipa_alter_variable(PyFrameObject *frame,
                             char *name,
                             char *expr,
                             int global);
const char *pyddd_ipa_eval(PyFrameObject *frame, char *expr);
const char *pyddd_ipa_iter_next(PyObject *iter);
const char *pyddd_ipa_format_object(PyObject *o);

/* In Python3, it is PyBytes_AsString/PyBytes_Size */
#define FPyString_AsString pyddd_ipa_pystring_asstring
#define FPyString_Size pyddd_ipa_pystring_size
#define FPyFrame_GetLineNumber pyddd_ipa_pyframe_getlinenumber
#define FPy_CompileStringFlags pyddd_ipa_py_compilestringflags
#define FPyEval_EvalCode pyddd_ipa_pyeval_evalcode
#define FPyEval_SetTrace pyddd_ipa_pyeval_settrace
#define FPy_DecRef pyddd_ipa_py_decref
#define FPyObject_IsTrue pyddd_ipa_pyobject_istrue
#define FPyThreadState_Get pyddd_ipa_pythreadstate_get
#define FPyObject_Str pyddd_ipa_pyobject_str
#define FPyObject_Repr pyddd_ipa_pyobject_repr
#define FPyTuple_GetItem pyddd_ipa_pytuple_getitem
#define FPyDict_GetItem pyddd_ipa_pydict_getitem
#define FPyDict_GetItemString pyddd_ipa_pydict_getitemstring
#define FPyDict_SetItem pyddd_ipa_pydict_setitem
#define FPyDict_SetItemString pyddd_ipa_pydict_setitemstring
#define FPyDict_Keys pyddd_ipa_pydict_keys
#define FPyDict_Next pyddd_ipa_pydict_next
#define FPyObject_Type pyddd_ipa_pyobject_type
#define FPyObject_GetIter pyddd_ipa_pyobject_getiter
#define FPyIter_Next pyddd_ipa_pyiter_next
#define FPyErr_Clear pyddd_ipa_pyerr_clear
#define FPyErr_PrintEx pyddd_ipa_pyerr_printex
#define FPyErr_Occurred pyddd_ipa_pyerr_occurred

extern char* (*FPyString_AsString)(PyObject *o);
extern int (*FPyFrame_GetLineNumber)(PyFrameObject *frame);
extern void (*FPy_DecRef)(PyObject *);
extern int (*FPyObject_IsTrue)(PyObject *);
extern Py_ssize_t (*FPyString_Size)(PyObject *string);
extern void (*FPyEval_SetTrace)(Py_tracefunc func, PyObject *arg);
extern PyThreadState* (*FPyThreadState_Get)(void);
extern PyObject* (*FPyObject_Str)(PyObject *o);
extern PyObject* (*FPyObject_Repr)(PyObject *o);
extern PyObject* (*FPyTuple_GetItem)(PyObject *p, Py_ssize_t pos);
extern PyObject* (*FPyDict_GetItem)(PyObject *p, PyObject *key);
extern PyObject* (*FPyDict_GetItemString)(PyObject *p, const char *key);
extern int (*FPyDict_SetItem)(PyObject *p, PyObject *key, PyObject *val);
extern int (*FPyDict_SetItemString)(PyObject *p,
                                    const char *key,
                                    PyObject *val);
extern PyObject* (*FPyDict_Keys)(PyObject *p);
extern int (*FPyDict_Next)(PyObject *p,
                           Py_ssize_t *ppos,
                           PyObject **pkey,
                           PyObject **pvalue);

extern PyObject* (*FPyObject_Type)(PyObject *o);
extern PyObject* (*FPyObject_GetIter)(PyObject *o);
extern PyObject* (*FPyIter_Next)(PyObject *o);

extern void (*FPyErr_Clear)(void);
extern void (*FPyErr_PrintEx)(int set_sys_last_vars);
extern PyObject* (*FPyErr_Occurred)(void);
extern PyObject* (*FPy_CompileStringFlags)(const char *str,
                                           const char *filename,
                                           int start,
                                           PyCompilerFlags *flags);
extern PyObject* (*FPyEval_EvalCode)(PyCodeObject *co,
                                     PyObject *globals,
                                     PyObject *locals);

#endif  /* __PYDDD_IPA_H__ */
/* end of ipa.h */
