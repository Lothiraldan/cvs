import io
import random
import struct
import sys

try:
    import unittest2 as unittest
except ImportError:
    import unittest

import zstd

from .common import OpCountingBytesIO


if sys.version_info[0] >= 3:
    next = lambda it: it.__next__()
else:
    next = lambda it: it.next()


class TestDecompressor_decompress(unittest.TestCase):
    def test_empty_input(self):
        dctx = zstd.ZstdDecompressor()

        with self.assertRaisesRegexp(zstd.ZstdError, 'input data invalid'):
            dctx.decompress(b'')

    def test_invalid_input(self):
        dctx = zstd.ZstdDecompressor()

        with self.assertRaisesRegexp(zstd.ZstdError, 'input data invalid'):
            dctx.decompress(b'foobar')

    def test_no_content_size_in_frame(self):
        cctx = zstd.ZstdCompressor(write_content_size=False)
        compressed = cctx.compress(b'foobar')

        dctx = zstd.ZstdDecompressor()
        with self.assertRaisesRegexp(zstd.ZstdError, 'input data invalid'):
            dctx.decompress(compressed)

    def test_content_size_present(self):
        cctx = zstd.ZstdCompressor(write_content_size=True)
        compressed = cctx.compress(b'foobar')

        dctx = zstd.ZstdDecompressor()
        decompressed  = dctx.decompress(compressed)
        self.assertEqual(decompressed, b'foobar')

    def test_max_output_size(self):
        cctx = zstd.ZstdCompressor(write_content_size=False)
        source = b'foobar' * 256
        compressed = cctx.compress(source)

        dctx = zstd.ZstdDecompressor()
        # Will fit into buffer exactly the size of input.
        decompressed = dctx.decompress(compressed, max_output_size=len(source))
        self.assertEqual(decompressed, source)

        # Input size - 1 fails
        with self.assertRaisesRegexp(zstd.ZstdError, 'Destination buffer is too small'):
            dctx.decompress(compressed, max_output_size=len(source) - 1)

        # Input size + 1 works
        decompressed = dctx.decompress(compressed, max_output_size=len(source) + 1)
        self.assertEqual(decompressed, source)

        # A much larger buffer works.
        decompressed = dctx.decompress(compressed, max_output_size=len(source) * 64)
        self.assertEqual(decompressed, source)

    def test_stupidly_large_output_buffer(self):
        cctx = zstd.ZstdCompressor(write_content_size=False)
        compressed = cctx.compress(b'foobar' * 256)
        dctx = zstd.ZstdDecompressor()

        # Will get OverflowError on some Python distributions that can't
        # handle really large integers.
        with self.assertRaises((MemoryError, OverflowError)):
            dctx.decompress(compressed, max_output_size=2**62)

    def test_dictionary(self):
        samples = []
        for i in range(128):
            samples.append(b'foo' * 64)
            samples.append(b'bar' * 64)
            samples.append(b'foobar' * 64)

        d = zstd.train_dictionary(8192, samples)

        orig = b'foobar' * 16384
        cctx = zstd.ZstdCompressor(level=1, dict_data=d, write_content_size=True)
        compressed = cctx.compress(orig)

        dctx = zstd.ZstdDecompressor(dict_data=d)
        decompressed = dctx.decompress(compressed)

        self.assertEqual(decompressed, orig)

    def test_dictionary_multiple(self):
        samples = []
        for i in range(128):
            samples.append(b'foo' * 64)
            samples.append(b'bar' * 64)
            samples.append(b'foobar' * 64)

        d = zstd.train_dictionary(8192, samples)

        sources = (b'foobar' * 8192, b'foo' * 8192, b'bar' * 8192)
        compressed = []
        cctx = zstd.ZstdCompressor(level=1, dict_data=d, write_content_size=True)
        for source in sources:
            compressed.append(cctx.compress(source))

        dctx = zstd.ZstdDecompressor(dict_data=d)
        for i in range(len(sources)):
            decompressed = dctx.decompress(compressed[i])
            self.assertEqual(decompressed, sources[i])


class TestDecompressor_copy_stream(unittest.TestCase):
    def test_no_read(self):
        source = object()
        dest = io.BytesIO()

        dctx = zstd.ZstdDecompressor()
        with self.assertRaises(ValueError):
            dctx.copy_stream(source, dest)

    def test_no_write(self):
        source = io.BytesIO()
        dest = object()

        dctx = zstd.ZstdDecompressor()
        with self.assertRaises(ValueError):
            dctx.copy_stream(source, dest)

    def test_empty(self):
        source = io.BytesIO()
        dest = io.BytesIO()

        dctx = zstd.ZstdDecompressor()
        # TODO should this raise an error?
        r, w = dctx.copy_stream(source, dest)

        self.assertEqual(r, 0)
        self.assertEqual(w, 0)
        self.assertEqual(dest.getvalue(), b'')

    def test_large_data(self):
        source = io.BytesIO()
        for i in range(255):
            source.write(struct.Struct('>B').pack(i) * 16384)
        source.seek(0)

        compressed = io.BytesIO()
        cctx = zstd.ZstdCompressor()
        cctx.copy_stream(source, compressed)

        compressed.seek(0)
        dest = io.BytesIO()
        dctx = zstd.ZstdDecompressor()
        r, w = dctx.copy_stream(compressed, dest)

        self.assertEqual(r, len(compressed.getvalue()))
        self.assertEqual(w, len(source.getvalue()))

    def test_read_write_size(self):
        source = OpCountingBytesIO(zstd.ZstdCompressor().compress(
            b'foobarfoobar'))

        dest = OpCountingBytesIO()
        dctx = zstd.ZstdDecompressor()
        r, w = dctx.copy_stream(source, dest, read_size=1, write_size=1)

        self.assertEqual(r, len(source.getvalue()))
        self.assertEqual(w, len(b'foobarfoobar'))
        self.assertEqual(source._read_count, len(source.getvalue()) + 1)
        self.assertEqual(dest._write_count, len(dest.getvalue()))


class TestDecompressor_decompressobj(unittest.TestCase):
    def test_simple(self):
        data = zstd.ZstdCompressor(level=1).compress(b'foobar')

        dctx = zstd.ZstdDecompressor()
        dobj = dctx.decompressobj()
        self.assertEqual(dobj.decompress(data), b'foobar')

    def test_reuse(self):
        data = zstd.ZstdCompressor(level=1).compress(b'foobar')

        dctx = zstd.ZstdDecompressor()
        dobj = dctx.decompressobj()
        dobj.decompress(data)

        with self.assertRaisesRegexp(zstd.ZstdError, 'cannot use a decompressobj'):
            dobj.decompress(data)


def decompress_via_writer(data):
    buffer = io.BytesIO()
    dctx = zstd.ZstdDecompressor()
    with dctx.write_to(buffer) as decompressor:
        decompressor.write(data)
    return buffer.getvalue()


class TestDecompressor_write_to(unittest.TestCase):
    def test_empty_roundtrip(self):
        cctx = zstd.ZstdCompressor()
        empty = cctx.compress(b'')
        self.assertEqual(decompress_via_writer(empty), b'')

    def test_large_roundtrip(self):
        chunks = []
        for i in range(255):
            chunks.append(struct.Struct('>B').pack(i) * 16384)
        orig = b''.join(chunks)
        cctx = zstd.ZstdCompressor()
        compressed = cctx.compress(orig)

        self.assertEqual(decompress_via_writer(compressed), orig)

    def test_multiple_calls(self):
        chunks = []
        for i in range(255):
            for j in range(255):
                chunks.append(struct.Struct('>B').pack(j) * i)

        orig = b''.join(chunks)
        cctx = zstd.ZstdCompressor()
        compressed = cctx.compress(orig)

        buffer = io.BytesIO()
        dctx = zstd.ZstdDecompressor()
        with dctx.write_to(buffer) as decompressor:
            pos = 0
            while pos < len(compressed):
                pos2 = pos + 8192
                decompressor.write(compressed[pos:pos2])
                pos += 8192
        self.assertEqual(buffer.getvalue(), orig)

    def test_dictionary(self):
        samples = []
        for i in range(128):
            samples.append(b'foo' * 64)
            samples.append(b'bar' * 64)
            samples.append(b'foobar' * 64)

        d = zstd.train_dictionary(8192, samples)

        orig = b'foobar' * 16384
        buffer = io.BytesIO()
        cctx = zstd.ZstdCompressor(dict_data=d)
        with cctx.write_to(buffer) as compressor:
            compressor.write(orig)

        compressed = buffer.getvalue()
        buffer = io.BytesIO()

        dctx = zstd.ZstdDecompressor(dict_data=d)
        with dctx.write_to(buffer) as decompressor:
            decompressor.write(compressed)

        self.assertEqual(buffer.getvalue(), orig)

    def test_memory_size(self):
        dctx = zstd.ZstdDecompressor()
        buffer = io.BytesIO()
        with dctx.write_to(buffer) as decompressor:
            size = decompressor.memory_size()

        self.assertGreater(size, 100000)

    def test_write_size(self):
        source = zstd.ZstdCompressor().compress(b'foobarfoobar')
        dest = OpCountingBytesIO()
        dctx = zstd.ZstdDecompressor()
        with dctx.write_to(dest, write_size=1) as decompressor:
            s = struct.Struct('>B')
            for c in source:
                if not isinstance(c, str):
                    c = s.pack(c)
                decompressor.write(c)


        self.assertEqual(dest.getvalue(), b'foobarfoobar')
        self.assertEqual(dest._write_count, len(dest.getvalue()))


class TestDecompressor_read_from(unittest.TestCase):
    def test_type_validation(self):
        dctx = zstd.ZstdDecompressor()

        # Object with read() works.
        dctx.read_from(io.BytesIO())

        # Buffer protocol works.
        dctx.read_from(b'foobar')

        with self.assertRaisesRegexp(ValueError, 'must pass an object with a read'):
            dctx.read_from(True)

    def test_empty_input(self):
        dctx = zstd.ZstdDecompressor()

        source = io.BytesIO()
        it = dctx.read_from(source)
        # TODO this is arguably wrong. Should get an error about missing frame foo.
        with self.assertRaises(StopIteration):
            next(it)

        it = dctx.read_from(b'')
        with self.assertRaises(StopIteration):
            next(it)

    def test_invalid_input(self):
        dctx = zstd.ZstdDecompressor()

        source = io.BytesIO(b'foobar')
        it = dctx.read_from(source)
        with self.assertRaisesRegexp(zstd.ZstdError, 'Unknown frame descriptor'):
            next(it)

        it = dctx.read_from(b'foobar')
        with self.assertRaisesRegexp(zstd.ZstdError, 'Unknown frame descriptor'):
            next(it)

    def test_empty_roundtrip(self):
        cctx = zstd.ZstdCompressor(level=1, write_content_size=False)
        empty = cctx.compress(b'')

        source = io.BytesIO(empty)
        source.seek(0)

        dctx = zstd.ZstdDecompressor()
        it = dctx.read_from(source)

        # No chunks should be emitted since there is no data.
        with self.assertRaises(StopIteration):
            next(it)

        # Again for good measure.
        with self.assertRaises(StopIteration):
            next(it)

    def test_skip_bytes_too_large(self):
        dctx = zstd.ZstdDecompressor()

        with self.assertRaisesRegexp(ValueError, 'skip_bytes must be smaller than read_size'):
            dctx.read_from(b'', skip_bytes=1, read_size=1)

        with self.assertRaisesRegexp(ValueError, 'skip_bytes larger than first input chunk'):
            b''.join(dctx.read_from(b'foobar', skip_bytes=10))

    def test_skip_bytes(self):
        cctx = zstd.ZstdCompressor(write_content_size=False)
        compressed = cctx.compress(b'foobar')

        dctx = zstd.ZstdDecompressor()
        output = b''.join(dctx.read_from(b'hdr' + compressed, skip_bytes=3))
        self.assertEqual(output, b'foobar')

    def test_large_output(self):
        source = io.BytesIO()
        source.write(b'f' * zstd.DECOMPRESSION_RECOMMENDED_OUTPUT_SIZE)
        source.write(b'o')
        source.seek(0)

        cctx = zstd.ZstdCompressor(level=1)
        compressed = io.BytesIO(cctx.compress(source.getvalue()))
        compressed.seek(0)

        dctx = zstd.ZstdDecompressor()
        it = dctx.read_from(compressed)

        chunks = []
        chunks.append(next(it))
        chunks.append(next(it))

        with self.assertRaises(StopIteration):
            next(it)

        decompressed = b''.join(chunks)
        self.assertEqual(decompressed, source.getvalue())

        # And again with buffer protocol.
        it = dctx.read_from(compressed.getvalue())
        chunks = []
        chunks.append(next(it))
        chunks.append(next(it))

        with self.assertRaises(StopIteration):
            next(it)

        decompressed = b''.join(chunks)
        self.assertEqual(decompressed, source.getvalue())

    def test_large_input(self):
        bytes = list(struct.Struct('>B').pack(i) for i in range(256))
        compressed = io.BytesIO()
        input_size = 0
        cctx = zstd.ZstdCompressor(level=1)
        with cctx.write_to(compressed) as compressor:
            while True:
                compressor.write(random.choice(bytes))
                input_size += 1

                have_compressed = len(compressed.getvalue()) > zstd.DECOMPRESSION_RECOMMENDED_INPUT_SIZE
                have_raw = input_size > zstd.DECOMPRESSION_RECOMMENDED_OUTPUT_SIZE * 2
                if have_compressed and have_raw:
                    break

        compressed.seek(0)
        self.assertGreater(len(compressed.getvalue()),
                           zstd.DECOMPRESSION_RECOMMENDED_INPUT_SIZE)

        dctx = zstd.ZstdDecompressor()
        it = dctx.read_from(compressed)

        chunks = []
        chunks.append(next(it))
        chunks.append(next(it))
        chunks.append(next(it))

        with self.assertRaises(StopIteration):
            next(it)

        decompressed = b''.join(chunks)
        self.assertEqual(len(decompressed), input_size)

        # And again with buffer protocol.
        it = dctx.read_from(compressed.getvalue())

        chunks = []
        chunks.append(next(it))
        chunks.append(next(it))
        chunks.append(next(it))

        with self.assertRaises(StopIteration):
            next(it)

        decompressed = b''.join(chunks)
        self.assertEqual(len(decompressed), input_size)

    def test_interesting(self):
        # Found this edge case via fuzzing.
        cctx = zstd.ZstdCompressor(level=1)

        source = io.BytesIO()

        compressed = io.BytesIO()
        with cctx.write_to(compressed) as compressor:
            for i in range(256):
                chunk = b'\0' * 1024
                compressor.write(chunk)
                source.write(chunk)

        dctx = zstd.ZstdDecompressor()

        simple = dctx.decompress(compressed.getvalue(),
                                 max_output_size=len(source.getvalue()))
        self.assertEqual(simple, source.getvalue())

        compressed.seek(0)
        streamed = b''.join(dctx.read_from(compressed))
        self.assertEqual(streamed, source.getvalue())

    def test_read_write_size(self):
        source = OpCountingBytesIO(zstd.ZstdCompressor().compress(b'foobarfoobar'))
        dctx = zstd.ZstdDecompressor()
        for chunk in dctx.read_from(source, read_size=1, write_size=1):
            self.assertEqual(len(chunk), 1)

        self.assertEqual(source._read_count, len(source.getvalue()))
