/*
 util.h - utility functions for interfacing with the various python APIs.

 This software may be used and distributed according to the terms of
 the GNU General Public License, incorporated herein by reference.
*/

#ifndef _HG_UTIL_H_
#define _HG_UTIL_H_

#include "compat.h"

#if PY_MAJOR_VERSION >= 3

#define IS_PY3K
/* The mapping of Python types is meant to be temporary to get Python
 * 3 to compile. We should remove this once Python 3 support is fully
 * supported and proper types are used in the extensions themselves. */
#define PyInt_Type PyLong_Type
#define PyInt_FromLong PyLong_FromLong
#define PyInt_AsLong PyLong_AsLong

#endif /* PY_MAJOR_VERSION */

typedef struct {
	PyObject_HEAD
	char state;
	int mode;
	int size;
	int mtime;
} dirstateTupleObject;

extern PyTypeObject dirstateTupleType;
#define dirstate_tuple_check(op) (Py_TYPE(op) == &dirstateTupleType)

/* This should be kept in sync with normcasespecs in encoding.py. */
enum normcase_spec {
	NORMCASE_LOWER = -1,
	NORMCASE_UPPER = 1,
	NORMCASE_OTHER = 0
};

#define MIN(a, b) (((a)<(b))?(a):(b))
/* VC9 doesn't include bool and lacks stdbool.h based on my searching */
#if defined(_MSC_VER) || __STDC_VERSION__ < 199901L
#define true 1
#define false 0
typedef unsigned char bool;
#else
#include <stdbool.h>
#endif

#endif /* _HG_UTIL_H_ */
