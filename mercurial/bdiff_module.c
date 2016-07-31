/*
 bdiff.c - efficient binary diff extension for Mercurial

 Copyright 2005, 2006 Matt Mackall <mpm@selenic.com>

 This software may be used and distributed according to the terms of
 the GNU General Public License, incorporated herein by reference.

 Based roughly on Python difflib
*/

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>

#include "bdiff.h"
#include "bitmanipulation.h"


static PyObject *blocks(PyObject *self, PyObject *args)
{
	PyObject *sa, *sb, *rl = NULL, *m;
	struct bdiff_line *a, *b;
	struct bdiff_hunk l, *h;
	int an, bn, count, pos = 0;

	l.next = NULL;

	if (!PyArg_ParseTuple(args, "SS:bdiff", &sa, &sb))
		return NULL;

	an = bdiff_splitlines(PyBytes_AsString(sa), PyBytes_Size(sa), &a);
	bn = bdiff_splitlines(PyBytes_AsString(sb), PyBytes_Size(sb), &b);

	if (!a || !b)
		goto nomem;

	count = bdiff_diff(a, an, b, bn, &l);
	if (count < 0)
		goto nomem;

	rl = PyList_New(count);
	if (!rl)
		goto nomem;

	for (h = l.next; h; h = h->next) {
		m = Py_BuildValue("iiii", h->a1, h->a2, h->b1, h->b2);
		PyList_SetItem(rl, pos, m);
		pos++;
	}

nomem:
	free(a);
	free(b);
	bdiff_freehunks(l.next);
	return rl ? rl : PyErr_NoMemory();
}

static PyObject *bdiff(PyObject *self, PyObject *args)
{
	char *sa, *sb, *rb;
	PyObject *result = NULL;
	struct bdiff_line *al, *bl;
	struct bdiff_hunk l, *h;
	int an, bn, count;
	Py_ssize_t len = 0, la, lb;
	PyThreadState *_save;

	l.next = NULL;

	if (!PyArg_ParseTuple(args, "s#s#:bdiff", &sa, &la, &sb, &lb))
		return NULL;

	if (la > UINT_MAX || lb > UINT_MAX) {
		PyErr_SetString(PyExc_ValueError, "bdiff inputs too large");
		return NULL;
	}

	_save = PyEval_SaveThread();
	an = bdiff_splitlines(sa, la, &al);
	bn = bdiff_splitlines(sb, lb, &bl);
	if (!al || !bl)
		goto nomem;

	count = bdiff_diff(al, an, bl, bn, &l);
	if (count < 0)
		goto nomem;

	/* calculate length of output */
	la = lb = 0;
	for (h = l.next; h; h = h->next) {
		if (h->a1 != la || h->b1 != lb)
			len += 12 + bl[h->b1].l - bl[lb].l;
		la = h->a2;
		lb = h->b2;
	}
	PyEval_RestoreThread(_save);
	_save = NULL;

	result = PyBytes_FromStringAndSize(NULL, len);

	if (!result)
		goto nomem;

	/* build binary patch */
	rb = PyBytes_AsString(result);
	la = lb = 0;

	for (h = l.next; h; h = h->next) {
		if (h->a1 != la || h->b1 != lb) {
			len = bl[h->b1].l - bl[lb].l;
			putbe32((uint32_t)(al[la].l - al->l), rb);
			putbe32((uint32_t)(al[h->a1].l - al->l), rb + 4);
			putbe32((uint32_t)len, rb + 8);
			memcpy(rb + 12, bl[lb].l, len);
			rb += 12 + len;
		}
		la = h->a2;
		lb = h->b2;
	}

nomem:
	if (_save)
		PyEval_RestoreThread(_save);
	free(al);
	free(bl);
	bdiff_freehunks(l.next);
	return result ? result : PyErr_NoMemory();
}

/*
 * If allws != 0, remove all whitespace (' ', \t and \r). Otherwise,
 * reduce whitespace sequences to a single space and trim remaining whitespace
 * from end of lines.
 */
static PyObject *fixws(PyObject *self, PyObject *args)
{
	PyObject *s, *result = NULL;
	char allws, c;
	const char *r;
	Py_ssize_t i, rlen, wlen = 0;
	char *w;

	if (!PyArg_ParseTuple(args, "Sb:fixws", &s, &allws))
		return NULL;
	r = PyBytes_AsString(s);
	rlen = PyBytes_Size(s);

	w = (char *)malloc(rlen ? rlen : 1);
	if (!w)
		goto nomem;

	for (i = 0; i != rlen; i++) {
		c = r[i];
		if (c == ' ' || c == '\t' || c == '\r') {
			if (!allws && (wlen == 0 || w[wlen - 1] != ' '))
				w[wlen++] = ' ';
		} else if (c == '\n' && !allws
			  && wlen > 0 && w[wlen - 1] == ' ') {
			w[wlen - 1] = '\n';
		} else {
			w[wlen++] = c;
		}
	}

	result = PyBytes_FromStringAndSize(w, wlen);

nomem:
	free(w);
	return result ? result : PyErr_NoMemory();
}


static char mdiff_doc[] = "Efficient binary diff.";

static PyMethodDef methods[] = {
	{"bdiff", bdiff, METH_VARARGS, "calculate a binary diff\n"},
	{"blocks", blocks, METH_VARARGS, "find a list of matching lines\n"},
	{"fixws", fixws, METH_VARARGS, "normalize diff whitespaces\n"},
	{NULL, NULL}
};

#ifdef IS_PY3K
static struct PyModuleDef bdiff_module = {
	PyModuleDef_HEAD_INIT,
	"bdiff",
	mdiff_doc,
	-1,
	methods
};

PyMODINIT_FUNC PyInit_bdiff(void)
{
	return PyModule_Create(&bdiff_module);
}
#else
PyMODINIT_FUNC initbdiff(void)
{
	Py_InitModule3("bdiff", methods, mdiff_doc);
}
#endif
