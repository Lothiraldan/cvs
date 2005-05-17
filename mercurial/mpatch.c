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

 Copyright 2005 Matt Mackall <mpm@selenic.com>

 This software may be used and distributed according to the terms
 of the GNU General Public License, incorporated herein by reference.
*/

#include <Python.h>
#include <stdlib.h>
#include <string.h>
#include <netinet/in.h>
#include <sys/types.h>

static char mpatch_doc[] = "Efficient binary patching.";

struct frag {
	int start, end, len;
	char *data;
};

struct flist {
	struct frag *base, *head, *tail;
};

static struct flist *lalloc(int size)
{
	struct flist *a;

	a = malloc(sizeof(struct flist));
	a->head = a->tail = a->base = malloc(sizeof(struct frag) * size);
	return a;
}

static void lfree(struct flist *a)
{
	free(a->base);
	free(a);
}

static int lsize(struct flist *a)
{
	return a->tail - a->head;
}

/* move hunks in source that are less cut to dest, compensating
   for changes in offset. the last hunk may be split if necessary.
*/
static int gather(struct flist *dest, struct flist *src, int cut, int offset)
{
	struct frag *d = dest->tail, *s = src->head;
	int postend, c, l;

	while (s != src->tail) {
		if (s->start + offset >= cut)
			goto exit; /* we've gone far enough */

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

			goto exit;
		}
	}

 exit:
	dest->tail = d;
	src->head = s;
	return offset;
}

/* like gather, but with no output list */
static int discard(struct flist *src, int cut, int offset)
{
	struct frag *s = src->head;
	int postend, c, l;

	while (s != src->tail) {
		if (s->start + offset >= cut)
			goto exit;

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

			goto exit;
		}
	}

 exit:
	src->head = s;
	return offset;
}

/* combine hunk lists a and b, while adjusting b for offset changes in a/
   this deletes a and b and returns the resultant list. */
static struct flist *combine(struct flist *a, struct flist *b)
{
	struct flist *c;
	struct frag *bh = b->head, *ct;
	int offset = 0, post;

	c = lalloc((lsize(a) + lsize(b)) * 2);

	while (bh != b->tail) {
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
		bh++;
		offset = post;
	}

	/* hold on to tail from a */
	memcpy(c->tail, a->head, sizeof(struct frag) * lsize(a));
	c->tail += lsize(a);
	lfree(a);
	lfree(b);
	return c;
}

/* decode a binary patch into a hunk list */
static struct flist *decode(char *bin, int len)
{
	struct flist *l;
	struct frag *lt;
	char *end = bin + len;

	/* assume worst case size, we won't have many of these lists */
	l = lalloc(len / 12);
	lt = l->tail;

	while (bin < end) {
		lt->start = ntohl(*(uint32_t *)bin);
		lt->end = ntohl(*(uint32_t *)(bin + 4));
		lt->len = ntohl(*(uint32_t *)(bin + 8));
		lt->data = bin + 12;
		bin += 12 + lt->len;
		lt++;
	}

	l->tail = lt;
	return l;
}

/* calculate the size of resultant text */
static int calcsize(int len, struct flist *l)
{
	int outlen = 0, last = 0;
	struct frag *f = l->head;

	while (f != l->tail) {
		outlen += f->start - last;
		last = f->end;
		outlen += f->len;
		f++;
	}

	outlen += len - last;
	return outlen;
}

static void apply(char *buf, char *orig, int len, struct flist *l)
{
	struct frag *f = l->head;
	int last = 0;
	char *p = buf;

	while (f != l->tail) {
		memcpy(p, orig + last, f->start - last);
		p += f->start - last;
		memcpy(p, f->data, f->len);
		last = f->end;
		p += f->len;
		f++;
	}
	memcpy(p, orig + last, len - last);
}

/* recursively generate a patch of all bins between start and end */
static struct flist *fold(PyObject *bins, int start, int end)
{
	int len;

	if (start + 1 == end) {
		/* trivial case, output a decoded list */
		PyObject *tmp = PyList_GetItem(bins, start);
		return decode(PyString_AsString(tmp), PyString_Size(tmp));
	}

	/* divide and conquer, memory management is elsewhere */
	len = (end - start) / 2;
	return combine(fold(bins, start, start + len),
		       fold(bins, start + len, end));
}

static PyObject *
patches(PyObject *self, PyObject *args)
{
	PyObject *text, *bins, *result;
	struct flist *patch;
	char *in, *out;
	int len, outlen;

	if (!PyArg_ParseTuple(args, "OO:mpatch", &text, &bins))
		return NULL;

	len = PyList_Size(bins);
	if (!len) {
		/* nothing to do */
		Py_INCREF(text);
		return text;
	}

	patch = fold(bins, 0, len);
	outlen = calcsize(PyString_Size(text), patch);
	result = PyString_FromStringAndSize(NULL, outlen);
	in = PyString_AsString(text);
	out = PyString_AsString(result);
	apply(out, in, PyString_Size(text), patch);
	lfree(patch);

	return result;
}

static PyMethodDef methods[] = {
	{"patches", patches, METH_VARARGS, "apply a series of patches\n"},
	{NULL, NULL}
};

PyMODINIT_FUNC
initmpatch(void)
{
	Py_InitModule3("mpatch", methods, mpatch_doc);
}

