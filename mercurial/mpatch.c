/*
 mpatch.c - efficient binary patching for Mercurial

 This implements a patch algorithm that's O(m + nlog n) where m is the
 size of the output and n is the number of patches.

 Given a list of binary patches, it unpacks each into a hunk list,
 then combines the hunk lists with a treewise recursion to form a
 single hunk list. This hunk list is then applied to the original
 text.

 The text (or binary) fragments are copied directly from their source
 Python objects into a preallocated output string to avoid the
 allocation of intermediate Python objects. Working memory is about 2x
 the total number of hunks.

 Copyright 2005, 2006 Matt Mackall <mpm@selenic.com>

 This software may be used and distributed according to the terms
 of the GNU General Public License, incorporated herein by reference.
*/

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdlib.h>
#include <string.h>

#include "util.h"
#include "bitmanipulation.h"
#include "compat.h"

static char mpatch_doc[] = "Efficient binary patching.";
static PyObject *mpatch_Error;

struct mpatch_frag {
	int start, end, len;
	const char *data;
};

struct mpatch_flist {
	struct mpatch_frag *base, *head, *tail;
};

static struct mpatch_flist *lalloc(ssize_t size)
{
	struct mpatch_flist *a = NULL;

	if (size < 1)
		size = 1;

	a = (struct mpatch_flist *)malloc(sizeof(struct mpatch_flist));
	if (a) {
		a->base = (struct mpatch_frag *)malloc(sizeof(struct mpatch_frag) * size);
		if (a->base) {
			a->head = a->tail = a->base;
			return a;
		}
		free(a);
		a = NULL;
	}
	if (!PyErr_Occurred())
		PyErr_NoMemory();
	return NULL;
}

static void mpatch_lfree(struct mpatch_flist *a)
{
	if (a) {
		free(a->base);
		free(a);
	}
}

static ssize_t lsize(struct mpatch_flist *a)
{
	return a->tail - a->head;
}

/* move hunks in source that are less cut to dest, compensating
   for changes in offset. the last hunk may be split if necessary.
*/
static int gather(struct mpatch_flist *dest, struct mpatch_flist *src, int cut,
	int offset)
{
	struct mpatch_frag *d = dest->tail, *s = src->head;
	int postend, c, l;

	while (s != src->tail) {
		if (s->start + offset >= cut)
			break; /* we've gone far enough */

		postend = offset + s->start + s->len;
		if (postend <= cut) {
			/* save this hunk */
			offset += s->start + s->len - s->end;
			*d++ = *s++;
		}
		else {
			/* break up this hunk */
			c = cut - offset;
			if (s->end < c)
				c = s->end;
			l = cut - offset - s->start;
			if (s->len < l)
				l = s->len;

			offset += s->start + l - c;

			d->start = s->start;
			d->end = c;
			d->len = l;
			d->data = s->data;
			d++;
			s->start = c;
			s->len = s->len - l;
			s->data = s->data + l;

			break;
		}
	}

	dest->tail = d;
	src->head = s;
	return offset;
}

/* like gather, but with no output list */
static int discard(struct mpatch_flist *src, int cut, int offset)
{
	struct mpatch_frag *s = src->head;
	int postend, c, l;

	while (s != src->tail) {
		if (s->start + offset >= cut)
			break;

		postend = offset + s->start + s->len;
		if (postend <= cut) {
			offset += s->start + s->len - s->end;
			s++;
		}
		else {
			c = cut - offset;
			if (s->end < c)
				c = s->end;
			l = cut - offset - s->start;
			if (s->len < l)
				l = s->len;

			offset += s->start + l - c;
			s->start = c;
			s->len = s->len - l;
			s->data = s->data + l;

			break;
		}
	}

	src->head = s;
	return offset;
}

/* combine hunk lists a and b, while adjusting b for offset changes in a/
   this deletes a and b and returns the resultant list. */
static struct mpatch_flist *combine(struct mpatch_flist *a,
	struct mpatch_flist *b)
{
	struct mpatch_flist *c = NULL;
	struct mpatch_frag *bh, *ct;
	int offset = 0, post;

	if (a && b)
		c = lalloc((lsize(a) + lsize(b)) * 2);

	if (c) {

		for (bh = b->head; bh != b->tail; bh++) {
			/* save old hunks */
			offset = gather(c, a, bh->start, offset);

			/* discard replaced hunks */
			post = discard(a, bh->end, offset);

			/* insert new hunk */
			ct = c->tail;
			ct->start = bh->start - offset;
			ct->end = bh->end - post;
			ct->len = bh->len;
			ct->data = bh->data;
			c->tail++;
			offset = post;
		}

		/* hold on to tail from a */
		memcpy(c->tail, a->head, sizeof(struct mpatch_frag) * lsize(a));
		c->tail += lsize(a);
	}

	mpatch_lfree(a);
	mpatch_lfree(b);
	return c;
}

/* decode a binary patch into a hunk list */
static struct mpatch_flist *mpatch_decode(const char *bin, ssize_t len)
{
	struct mpatch_flist *l;
	struct mpatch_frag *lt;
	int pos = 0;

	/* assume worst case size, we won't have many of these lists */
	l = lalloc(len / 12 + 1);
	if (!l)
		return NULL;

	lt = l->tail;

	while (pos >= 0 && pos < len) {
		lt->start = getbe32(bin + pos);
		lt->end = getbe32(bin + pos + 4);
		lt->len = getbe32(bin + pos + 8);
		lt->data = bin + pos + 12;
		pos += 12 + lt->len;
		if (lt->start > lt->end || lt->len < 0)
			break; /* sanity check */
		lt++;
	}

	if (pos != len) {
		if (!PyErr_Occurred())
			PyErr_SetString(mpatch_Error, "patch cannot be decoded");
		mpatch_lfree(l);
		return NULL;
	}

	l->tail = lt;
	return l;
}

/* calculate the size of resultant text */
static ssize_t mpatch_calcsize(ssize_t len, struct mpatch_flist *l)
{
	ssize_t outlen = 0, last = 0;
	struct mpatch_frag *f = l->head;

	while (f != l->tail) {
		if (f->start < last || f->end > len) {
			if (!PyErr_Occurred())
				PyErr_SetString(mpatch_Error,
				                "invalid patch");
			return -1;
		}
		outlen += f->start - last;
		last = f->end;
		outlen += f->len;
		f++;
	}

	outlen += len - last;
	return outlen;
}

static int mpatch_apply(char *buf, const char *orig, ssize_t len,
	struct mpatch_flist *l)
{
	struct mpatch_frag *f = l->head;
	int last = 0;
	char *p = buf;

	while (f != l->tail) {
		if (f->start < last || f->end > len) {
			if (!PyErr_Occurred())
				PyErr_SetString(mpatch_Error,
				                "invalid patch");
			return 0;
		}
		memcpy(p, orig + last, f->start - last);
		p += f->start - last;
		memcpy(p, f->data, f->len);
		last = f->end;
		p += f->len;
		f++;
	}
	memcpy(p, orig + last, len - last);
	return 1;
}

/* recursively generate a patch of all bins between start and end */
static struct mpatch_flist *mpatch_fold(PyObject *bins, ssize_t start,
	ssize_t end)
{
	ssize_t len, blen;
	const char *buffer;

	if (start + 1 == end) {
		/* trivial case, output a decoded list */
		PyObject *tmp = PyList_GetItem(bins, start);
		if (!tmp)
			return NULL;
		if (PyObject_AsCharBuffer(tmp, &buffer, &blen))
			return NULL;
		return mpatch_decode(buffer, blen);
	}

	/* divide and conquer, memory management is elsewhere */
	len = (end - start) / 2;
	return combine(mpatch_fold(bins, start, start + len),
		       mpatch_fold(bins, start + len, end));
}

static PyObject *
patches(PyObject *self, PyObject *args)
{
	PyObject *text, *bins, *result;
	struct mpatch_flist *patch;
	const char *in;
	char *out;
	Py_ssize_t len, outlen, inlen;

	if (!PyArg_ParseTuple(args, "OO:mpatch", &text, &bins))
		return NULL;

	len = PyList_Size(bins);
	if (!len) {
		/* nothing to do */
		Py_INCREF(text);
		return text;
	}

	if (PyObject_AsCharBuffer(text, &in, &inlen))
		return NULL;

	patch = mpatch_fold(bins, 0, len);
	if (!patch)
		return NULL;

	outlen = mpatch_calcsize(inlen, patch);
	if (outlen < 0) {
		result = NULL;
		goto cleanup;
	}
	result = PyBytes_FromStringAndSize(NULL, outlen);
	if (!result) {
		result = NULL;
		goto cleanup;
	}
	out = PyBytes_AsString(result);
	if (!mpatch_apply(out, in, inlen, patch)) {
		Py_DECREF(result);
		result = NULL;
	}
cleanup:
	mpatch_lfree(patch);
	return result;
}

/* calculate size of a patched file directly */
static PyObject *
patchedsize(PyObject *self, PyObject *args)
{
	long orig, start, end, len, outlen = 0, last = 0, pos = 0;
	Py_ssize_t patchlen;
	char *bin;

	if (!PyArg_ParseTuple(args, "ls#", &orig, &bin, &patchlen))
		return NULL;

	while (pos >= 0 && pos < patchlen) {
		start = getbe32(bin + pos);
		end = getbe32(bin + pos + 4);
		len = getbe32(bin + pos + 8);
		if (start > end)
			break; /* sanity check */
		pos += 12 + len;
		outlen += start - last;
		last = end;
		outlen += len;
	}

	if (pos != patchlen) {
		if (!PyErr_Occurred())
			PyErr_SetString(mpatch_Error, "patch cannot be decoded");
		return NULL;
	}

	outlen += orig - last;
	return Py_BuildValue("l", outlen);
}

static PyMethodDef methods[] = {
	{"patches", patches, METH_VARARGS, "apply a series of patches\n"},
	{"patchedsize", patchedsize, METH_VARARGS, "calculed patched size\n"},
	{NULL, NULL}
};

#ifdef IS_PY3K
static struct PyModuleDef mpatch_module = {
	PyModuleDef_HEAD_INIT,
	"mpatch",
	mpatch_doc,
	-1,
	methods
};

PyMODINIT_FUNC PyInit_mpatch(void)
{
	PyObject *m;

	m = PyModule_Create(&mpatch_module);
	if (m == NULL)
		return NULL;

	mpatch_Error = PyErr_NewException("mercurial.mpatch.mpatchError",
					  NULL, NULL);
	Py_INCREF(mpatch_Error);
	PyModule_AddObject(m, "mpatchError", mpatch_Error);

	return m;
}
#else
PyMODINIT_FUNC
initmpatch(void)
{
	Py_InitModule3("mpatch", methods, mpatch_doc);
	mpatch_Error = PyErr_NewException("mercurial.mpatch.mpatchError",
					  NULL, NULL);
}
#endif
