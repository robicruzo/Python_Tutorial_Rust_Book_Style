# Unicode Text Versus Bytes

Humans use text; computers speak bytes.  Python 3 draws a sharp line between
strings of human text and sequences of raw bytes, and implicit conversion of
byte sequences to Unicode text is a thing of the past.  This chapter deals with
Unicode strings, binary sequences, and the encodings used to convert between
them.  It expands on the [Text](introduction.md#tut-strings) section of the
informal introduction and on [Reading and Writing Files](inputoutput.md#tut-files).

Depending on the kind of work you do, you may think that understanding Unicode
is not important.  That is unlikely, and in any case there is no escaping the
`str` versus `bytes` divide.  As a bonus, you'll find that the specialized binary
sequence types have features that the "all-purpose" `str` of Python 2 lacked.
This chapter covers:

* characters, code points and byte representations;
* the unique features of binary sequences: `bytes`, `bytearray` and `memoryview`;
* encodings for full Unicode and legacy character sets;
* avoiding and dealing with encoding errors;
* best practices when handling text files;
* the default encoding trap and standard I/O issues;
* safe Unicode text comparisons with normalization;
* utility functions for normalization, case folding and brute-force diacritic
  removal;
* proper sorting of Unicode text;
* character metadata in the Unicode database;
* dual-mode interfaces that handle `str` and `bytes`.

## Character Issues

The concept of a "string" is simple enough: a string is a sequence of
characters.  The problem lies in the definition of "character".  Today the best
definition we have is a *Unicode character*.  Accordingly, the items you get out
of a Python 3 `str` are Unicode characters, not raw bytes.

The Unicode standard explicitly separates the identity of characters from
specific byte representations:

* The identity of a character, its *code point*, is a number from 0 to
  1,114,111 (base 10), shown in the Unicode standard as 4 to 6 hex digits with a
  "U+" prefix, from U+0000 to U+10FFFF.  For example, the code point for the
  letter A is U+0041, the Euro sign is U+20AC, and the musical symbol G clef is
  assigned to code point U+1D11E.  Only a fraction of the valid code points have
  characters assigned to them so far.
* The actual bytes that represent a character depend on the *encoding* in use.
  An encoding is an algorithm that converts code points to byte sequences and
  vice versa.  The code point for the letter A (U+0041) is encoded as the single
  byte `\x41` in UTF-8, or as the bytes `\x41\x00` in UTF-16LE.  As another
  example, UTF-8 requires three bytes, `\xe2\x82\xac`, to encode the Euro sign
  (U+20AC), but in UTF-16LE it is encoded as two bytes: `\xac\x20`.

Converting from code points to bytes is *encoding*; converting from bytes to
code points is *decoding*:

```python
s = 'café'
len(s)  # the str 'café' has four Unicode characters
# 4
b = s.encode('utf8')  # encode str to bytes using UTF-8
b  # bytes literals have a b prefix
# b'caf\xc3\xa9'
len(b)  # "é" is encoded as two bytes in UTF-8
# 5
b.decode('utf8')  # decode bytes to str using UTF-8
# 'café'
```

> **Tip**
>
> If you need a memory aid to tell `.decode()` from `.encode()`, convince
> yourself that byte sequences can be cryptic machine core dumps, while Unicode
> `str` objects are "human" text.  It then makes sense that you *decode* bytes to
> `str` to get human-readable text, and you *encode* `str` to bytes for storage or
> transmission.

Although the Python 3 `str` is pretty much the Python 2 `unicode` type with a new
name, the Python 3 `bytes` is not simply the old `str` renamed, and there is also
the closely related `bytearray` type.  So let's look at the binary sequence types
before going further into encoding and decoding.

## Byte Essentials

There are two basic built-in types for binary sequences: the immutable `bytes`
and the mutable `bytearray`.  (The Python documentation sometimes uses the
generic term "byte string" for both; this book avoids that confusing term.)

Each item in a `bytes` or `bytearray` is an integer from 0 to 255, not a
one-character string as in the Python 2 `str`.  However, a slice of a binary
sequence always produces a binary sequence of the same type, including slices
of length 1:

```python
cafe = bytes('café', encoding='utf_8')  # bytes can be built from a str, given an encoding
cafe
# b'caf\xc3\xa9'
cafe[0]  # each item is an integer in range(256)
# 99
cafe[:1]  # slices of bytes are also bytes, even slices of a single byte
# b'c'
cafe_arr = bytearray(cafe)
cafe_arr  # bytearray has no literal syntax; it shows as bytearray() with a bytes literal
# bytearray(b'caf\xc3\xa9')
cafe_arr[-1:]  # a slice of bytearray is also a bytearray
# bytearray(b'\xa9')
```

> **Note**
>
> The fact that `my_bytes[0]` retrieves an `int` but `my_bytes[:1]` returns a
> `bytes` sequence of length 1 is only surprising because we are used to
> Python's `str` type, where `s[0] == s[:1]`.  For all other sequence types in
> Python, one item is not the same as a slice of length 1.

Although binary sequences are really sequences of integers, their literal
notation reflects the fact that ASCII text is often embedded in them.
Therefore, four different displays are used, depending on each byte value:

* for bytes with decimal codes 32 to 126, from space to `~` (tilde), the ASCII
  character itself is used;
* for bytes corresponding to tab, newline, carriage return and `\`, the escape
  sequences `\t`, `\n`, `\r` and `\\` are used;
* if both string delimiters `'` and `"` appear in the byte sequence, the whole
  sequence is delimited by `'`, and any `'` inside is escaped as `\'`;
* for other byte values, a hexadecimal escape sequence is used (for example,
  `\x00` is the null byte).

That is why you see `b'caf\xc3\xa9'` above: the first three bytes `b'caf'` are in
the printable ASCII range, and the last two are not.

Both `bytes` and `bytearray` support every `str` method except those that do
formatting (`format`, `format_map`) and those that depend on Unicode data,
including `casefold`, `isdecimal`, `isidentifier`, `isnumeric`, `isprintable` and
`encode`.  This means you can use familiar string methods like `endswith`,
`replace`, `strip`, `translate`, `upper` and dozens of others with binary
sequences, only with `bytes` and not `str` arguments.  The regular expression
functions in the `re` module also work on binary sequences, if the regex is
compiled from a binary sequence instead of a `str`.  And the `%` operator works
with binary sequences too ([**PEP 461**](https://peps.python.org/pep-0461/)).

Binary sequences have a class method that `str` doesn't have, called `fromhex`,
which builds a binary sequence by parsing pairs of hex digits optionally
separated by spaces; and the inverse instance method, `hex`:

```python
bytes.fromhex('31 4B CE A9')
# b'1K\xce\xa9'
b'1K\xce\xa9'.hex(' ')
# '31 4b ce a9'
```

The other ways of building `bytes` or `bytearray` instances are calling their
constructors with:

* a `str` and an `encoding` keyword argument;
* an iterable providing items with values from 0 to 255;
* an object that implements the *buffer protocol* (for example `bytes`,
  `bytearray`, `memoryview` or `array.array`), which copies the bytes from the
  source object to the newly created binary sequence.

> **Warning**
>
> Older versions of Python let you call `bytes` or `bytearray` with a single
> integer to create a binary sequence of that size filled with null bytes.  That
> signature was deprecated and then removed from `bytes` (it still works for
> `bytearray`).  Use `bytes(n)` only if you know what you are doing; see
> [**PEP 467**](https://peps.python.org/pep-0467/).

Building a binary sequence from a buffer-like object is a low-level operation
that may involve type casting:

```python
import array
numbers = array.array('h', [-2, -1, 0, 1, 2])  # typecode 'h': short integers (16 bits)
octets = bytes(numbers)  # a copy of the bytes that make up numbers
octets  # the 10 bytes that represent the 5 short integers
# b'\xfe\xff\xff\xff\x00\x00\x01\x00\x02\x00'
```

Creating a `bytes` or `bytearray` object from any buffer-like source always
copies the bytes.  In contrast, `memoryview` objects let you share memory
between binary data structures, as you saw in
[Memory Views](sequences.md#memory-views).

### Structs and Memory Views

The [`struct`](https://docs.python.org/3/library/struct.html) module provides
functions to parse packed bytes into a tuple of fields of different types and to
perform the opposite conversion, from a tuple into packed bytes.  `struct` is
used with `bytes`, `bytearray` and `memoryview` objects.

Suppose you need to read the header of a GIF image.  The first ten bytes of a GIF
file contain a 3-byte signature (`b'GIF'`), a 3-byte version (`b'87a'` or
`b'89a'`), and then the image width and height as two 16-bit little-endian
unsigned integers.  The format string `'<3s3sHH'` describes that layout: `<`
means little-endian, `3s3s` means two sequences of 3 bytes, and `HH` means two
16-bit unsigned integers:

```python
import struct
fmt = '<3s3sHH'
header = b'GIF89a+\x02\xe6\x00' + bytes(20)  # pretend these are the first bytes of a file
img = memoryview(header)
header_view = img[:10]  # slicing a memoryview creates a new memoryview, without copying bytes
bytes(header_view)
# b'GIF89a+\x02\xe6\x00'
struct.unpack(fmt, header_view)  # signature, version, width, height
# (b'GIF', b'89a', 555, 230)
del header_view
del img
```

With a real file you would read the data with
`with open('filter.gif', 'rb') as fp: img = memoryview(fp.read())`.  Note that
slicing a `memoryview` returns a new `memoryview` sharing the same memory, without
copying.  Deleting the views at the end releases the memory associated with them.

## Basic Encoders/Decoders

The Python distribution bundles more than 100 *codecs* (encoder/decoders) for
text-to-byte conversion and vice versa.  Each codec has a name, like `'utf_8'`,
and often aliases, such as `'utf8'`, `'utf-8'` and `'U8'`, which you can use as the
`encoding` argument of functions like `open()`, `str.encode()`, `bytes.decode()`
and so on.  Here is the same text encoded as three different byte sequences:

```python
for codec in ['latin_1', 'utf_8', 'utf_16']:
    print(codec, 'El Niño'.encode(codec), sep='\t')
# latin_1	b'El Ni\xf1o'
# utf_8	b'El Ni\xc3\xb1o'
# utf_16	b'\xff\xfeE\x00l\x00 \x00N\x00i\x00\xf1\x00o\x00'
```

Some encodings, like ASCII and even the multibyte GB2312, cannot represent every
Unicode character.  The UTF encodings, however, are designed to handle every
Unicode code point.  A representative sample of encodings:

`latin1`, a.k.a. `iso8859_1`
: important because it is the basis for other encodings, such as `cp1252`, and
  for Unicode itself: the `latin1` byte values are the first 256 code points.

`cp1252`
: a useful `latin1` superset created by Microsoft, adding symbols like curly
  quotes and € (euro); some Windows apps call it "ANSI", but it was never a real
  ANSI standard.

`cp437`
: the original character set of the IBM PC, with box-drawing characters.
  Incompatible with `latin1`, which appeared later.

`gb2312`
: legacy standard to encode the simplified Chinese ideographs used in mainland
  China; one of several widely deployed multibyte encodings for Asian
  languages.

`utf-8`
: the most common 8-bit encoding on the web, by far: well over 95% of websites
  use it.

`utf-16le`
: one form of the UTF 16-bit encoding scheme; all UTF-16 encodings support code
  points beyond U+FFFF through escape sequences called *surrogate pairs*.

> **Note**
>
> UTF-16 superseded the original 16-bit Unicode 1.0 encoding, UCS-2, back in
> 1996.  UCS-2 is still used in some systems despite being deprecated since the
> last century, but it only supports code points up to U+FFFF, and more than half
> of the allocated code points are now above U+FFFF, including the all-important
> emojis.

```python
for char in 'A¿Ã€':
    print(char, f'U+{ord(char):04X}',
          char.encode('latin_1', errors='replace'),
          char.encode('cp1252', errors='replace'),
          char.encode('utf_8'), char.encode('utf_16le'), sep='\t')
# A	U+0041	b'A'	b'A'	b'A'	b'A\x00'
# ¿	U+00BF	b'\xbf'	b'\xbf'	b'\xc2\xbf'	b'\xbf\x00'
# Ã	U+00C3	b'\xc3'	b'\xc3'	b'\xc3\x83'	b'\xc3\x00'
# €	U+20AC	b'?'	b'\x80'	b'\xe2\x82\xac'	b'\xac '
```

## Understanding Encode/Decode Problems

Although there is a generic `UnicodeError` exception, the error reported by
Python is usually more specific: either a `UnicodeEncodeError` (when converting
`str` to binary sequences) or a `UnicodeDecodeError` (when reading binary
sequences into `str`).  Loading Python modules may also raise `SyntaxError` when
the source encoding is unexpected.

> **Tip**
>
> The first thing to note when you get a Unicode error is the exact type of the
> exception.  Is it a `UnicodeEncodeError`, a `UnicodeDecodeError`, or some other
> error (e.g., `SyntaxError`) that mentions an encoding problem?  To solve the
> problem, you have to understand it first.

### Coping with `UnicodeEncodeError`

Most non-UTF codecs handle only a small subset of the Unicode characters.  When
converting text to bytes, if a character is not defined in the target encoding,
`UnicodeEncodeError` is raised, unless special handling is requested by passing
an `errors` argument to the encoding method or function:

```python
city = 'São Paulo'
city.encode('utf_8')  # the UTF encodings handle any str
# b'S\xc3\xa3o Paulo'
city.encode('utf_16')
# b'\xff\xfeS\x00\xe3\x00o\x00 \x00P\x00a\x00u\x00l\x00o\x00'
city.encode('iso8859_1')  # iso8859_1 also works for this string
# b'S\xe3o Paulo'
city.encode('cp437')  # cp437 can't encode the 'ã'
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
#   File "/.../lib/python3/encodings/cp437.py", line 12, in encode
#     return codecs.charmap_encode(input,errors,encoding_map)
# UnicodeEncodeError: 'charmap' codec can't encode character '\xe3' in
# position 1: character maps to <undefined>
city.encode('cp437', errors='ignore')
# b'So Paulo'
city.encode('cp437', errors='replace')
# b'S?o Paulo'
city.encode('cp437', errors='xmlcharrefreplace')
# b'S&#227;o Paulo'
```

The default error handler, `'strict'`, raises `UnicodeEncodeError`.  The
`errors='ignore'` handler skips characters that cannot be encoded; this is
usually a very bad idea, leading to silent data loss.  When encoding,
`errors='replace'` substitutes unencodable characters with `'?'`; data is also
lost, but users get a clue that something is amiss.  `'xmlcharrefreplace'`
replaces unencodable characters with an XML entity.  If you can't use UTF and
you can't afford to lose data, that is the only option.

> **Note**
>
> The codecs error handling is extensible.  You may register extra strings for
> the `errors` argument by passing a name and an error-handling function to
> [`codecs.register_error()`](https://docs.python.org/3/library/codecs.html#codecs.register_error).

ASCII is a common subset of all the encodings you are likely to meet, so encoding
should always work if the text is made exclusively of ASCII characters.  The
`str.isascii()` method checks whether a string is 100% pure ASCII.  If it is, you
should be able to encode it to bytes in any encoding without raising
`UnicodeEncodeError`.

### Coping with `UnicodeDecodeError`

Not every byte holds a valid ASCII character, and not every byte sequence is
valid UTF-8 or UTF-16.  So when you assume one of these encodings while
converting a binary sequence to text, you get a `UnicodeDecodeError` if
unexpected bytes are found.  On the other hand, many legacy 8-bit encodings like
`'cp1252'`, `'iso8859_1'` and `'koi8_r'` are able to decode any stream of bytes,
including random noise, without reporting errors.  If your program assumes the
wrong 8-bit encoding, it will silently decode garbage.

> **Tip**
>
> Garbled characters are known as *gremlins* or *mojibake* (文字化け, Japanese for
> "transformed text").

```python
octets = b'Montr\xe9al'  # "Montréal" encoded as latin1; '\xe9' is the byte for "é"
octets.decode('cp1252')  # Windows 1252 works because it is a superset of latin1
# 'Montréal'
octets.decode('iso8859_7')  # ISO-8859-7 is for Greek: '\xe9' is misinterpreted, no error
# 'Montrιal'
octets.decode('koi8_r')  # KOI8-R is for Russian: '\xe9' is the Cyrillic letter "И"
# 'MontrИal'
octets.decode('utf_8')  # the UTF-8 codec detects that octets is not valid UTF-8
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe9 in position 5:
# invalid continuation byte
octets.decode('utf_8', errors='replace')
# 'Montr�al'
```

With `'replace'` error handling, the `\xe9` is replaced by "�" (code point
U+FFFD), the official Unicode `REPLACEMENT CHARACTER`, intended to represent
unknown characters.

### `SyntaxError` When Loading Modules with Unexpected Encoding

UTF-8 is the default source encoding for Python 3 (see
[Source Code Encoding](interpreter.md#tut-source-encoding)).  If you load a `.py`
module containing non-UTF-8 data and no encoding declaration, you get a message
like this:

```text
SyntaxError: Non-UTF-8 code starting with '\xe1' in file ola.py on line
  1, but no encoding declared; see https://peps.python.org/pep-0263/
  for details
```

A likely scenario is opening a `.py` file created on Windows with `cp1252`.  The
error happens even on Windows, because the default encoding for Python source is
UTF-8 on all platforms.  To fix it, add a magic `coding` comment at the top of
the file:

<!-- nocheck -->
```python
# coding: cp1252

print('Olá, Mundo!')
```

> **Tip**
>
> Now that Python source code is no longer limited to ASCII and defaults to the
> excellent UTF-8 encoding, the best "fix" for source code in legacy encodings
> like `'cp1252'` is to convert it to UTF-8 and not bother with `coding` comments.
> If your editor does not support UTF-8, it's time to switch.

### How to Discover the Encoding of a Byte Sequence

How do you find the encoding of a byte sequence?  Short answer: you can't.  You
must be told.

Some communication protocols and file formats, like HTTP and XML, contain
headers that explicitly say how the content is encoded.  You can be sure that
some byte streams are not ASCII because they contain byte values over 127, and
the way UTF-8 and UTF-16 are built also limits the possible byte sequences.

In fact, the way UTF-8 was designed makes it almost impossible for a random
sequence of bytes, or even a nonrandom sequence from a non-UTF-8 encoding, to be
decoded accidentally as garbage in UTF-8 instead of raising `UnicodeDecodeError`.
UTF-8 escape sequences never use ASCII characters, and they have bit patterns
that make it very hard for random data to be valid UTF-8 by accident.  So if you
can decode some bytes containing codes above 127 as UTF-8, they are probably
UTF-8.  A pragmatic decoding strategy for data from legacy systems is to try UTF-8
first and, on `UnicodeDecodeError`, fall back to `cp1252`.  It is ugly but
effective.

Beyond that, considering that human languages also have their rules and
restrictions, once you assume that a stream of bytes is plain human text it may
be possible to sniff out its encoding using heuristics and statistics.  For
example, if `b'\x00'` bytes are common, it is probably a 16- or 32-bit encoding,
not an 8-bit scheme, because null characters in plain text are bugs.  When the
byte sequence `b'\x20\x00'` appears often, it is more likely to be the space
character (U+0020) in UTF-16LE than the obscure U+2000 `EN QUAD` character.

That is how the [Chardet](https://pypi.org/project/chardet/) package works to
guess one of more than 30 supported encodings.  Chardet is a library you can use
in your programs, and it also includes a command-line utility, `chardetect`:

```console
$ chardetect 04-text-byte.asciidoc
04-text-byte.asciidoc: utf-8 with confidence 0.99
```

Although binary sequences of encoded text usually don't carry explicit hints of
their encoding, the UTF formats may prepend a byte-order mark to the textual
content.

### BOM: A Useful Gremlin

You may have noticed a couple of extra bytes at the beginning of the UTF-16
encoded sequence earlier.  Here they are again:

```python
u16 = 'El Niño'.encode('utf_16')
u16
# b'\xff\xfeE\x00l\x00 \x00N\x00i\x00\xf1\x00o\x00'
```

The bytes are `b'\xff\xfe'`.  That is a BOM, a *byte-order mark*, denoting the
"little-endian" byte ordering of the Intel CPU where the encoding was
performed.  On a little-endian machine, the least significant byte of each code
point comes first: the letter `'E'`, code point U+0045 (decimal 69), is encoded at
byte offsets 2 and 3 as 69 and 0:

```python
list(u16)
# [255, 254, 69, 0, 108, 0, 32, 0, 78, 0, 105, 0, 241, 0, 111, 0]
```

On a big-endian CPU the encoding would be reversed: `'E'` would be encoded as 0
and 69.  To avoid confusion, the UTF-16 encoding prepends the text with the
special invisible character `ZERO WIDTH NO-BREAK SPACE` (U+FEFF).  On a
little-endian system it is encoded as `b'\xff\xfe'` (decimal 255, 254).  Because,
by design, there is no U+FFFE character in Unicode, the byte sequence
`b'\xff\xfe'` must mean the `ZERO WIDTH NO-BREAK SPACE` in a little-endian
encoding, so the codec knows which byte ordering to use.

There is a variant of UTF-16, UTF-16LE, that is explicitly little-endian, and
another that is explicitly big-endian, UTF-16BE.  If you use them, no BOM is
generated:

```python
u16le = 'El Niño'.encode('utf_16le')
list(u16le)
# [69, 0, 108, 0, 32, 0, 78, 0, 105, 0, 241, 0, 111, 0]
u16be = 'El Niño'.encode('utf_16be')
list(u16be)
# [0, 69, 0, 108, 0, 32, 0, 78, 0, 105, 0, 241, 0, 111]
```

If present, the BOM is supposed to be filtered out by the UTF-16 codec, so that
you get only the actual text contents of the file, without the leading `ZERO
WIDTH NO-BREAK SPACE`.  The Unicode standard says that a UTF-16 file with no BOM
should be assumed to be UTF-16BE, but since the Intel x86 architecture is
little-endian, there is plenty of little-endian UTF-16 with no BOM in the wild.

The whole issue of endianness only affects encodings that use words of more than
one byte, like UTF-16 and UTF-32.  One big advantage of UTF-8 is that it produces
the same byte sequence regardless of machine endianness, so no BOM is needed.
Nevertheless, some Windows applications (notably Notepad) add a BOM to UTF-8
files anyway, and Excel depends on the BOM to detect a UTF-8 file; otherwise it
assumes the content is encoded with a Windows code page.  This UTF-8 encoding
with BOM is called UTF-8-SIG in Python's codec registry.  The character U+FEFF
encoded in UTF-8-SIG is the three-byte sequence `b'\xef\xbb\xbf'`, so if a file
starts with those three bytes, it is probably a UTF-8 file with a BOM.

> **Tip**
>
> Using the UTF-8-SIG codec when *reading* UTF-8 files is harmless, because it
> reads files with or without a BOM correctly and does not return the BOM itself.
> When *writing*, use plain UTF-8 for general interoperability.  For example,
> Python scripts can be made executable on Unix systems if they start with the
> comment `#!/usr/bin/env python3`; the first two bytes of the file must be
> `b'#!'` for that to work, and a BOM breaks that convention.  If you have a
> specific requirement to export data to applications that need the BOM, use
> UTF-8-SIG, but be aware that the `codecs` documentation says: "In UTF-8, the
> use of the BOM is discouraged and should generally be avoided."

## Handling Text Files

The best practice for handling text I/O is the "Unicode sandwich".  Bytes
should be decoded to `str` as early as possible on input (for example, when
opening a file for reading).  The "filling" of the sandwich is the business logic
of your program, where text handling is done exclusively on `str` objects.  You
should never be encoding or decoding in the middle of other processing.  On
output, `str` is encoded to bytes as late as possible.  Most web frameworks work
like that, and you rarely touch bytes when using them.  In Django, for example,
your views should output Unicode `str`; Django itself takes care of encoding the
response to bytes, using UTF-8 by default.

Python 3 makes it easy to follow this advice, because the `open()` built-in does
the necessary decoding when reading and encoding when writing files in text
mode, so all you get from `my_file.read()` and pass to `my_file.write(text)` are
`str` objects.  Using text files is therefore apparently simple.  But if you rely
on default encodings, you will get bitten.

Consider this session.  Can you spot the bug?

<!-- nocheck -->
```python
open('cafe.txt', 'w', encoding='utf_8').write('café')
# 4
open('cafe.txt').read()
# 'cafÃ©'
```

The bug: UTF-8 was specified when writing the file but not when reading it, so
Python assumed the system default file encoding, which on this Windows machine
was code page 1252, and the trailing bytes of the file were decoded as the
characters `'Ã©'` instead of `'é'`.  The same statements on a recent GNU/Linux or
macOS machine work perfectly, because there the default encoding is UTF-8,
giving the false impression that everything is fine.  And if the `encoding`
argument were omitted when writing as well, the file would be read back correctly,
but the program would generate files with different byte contents depending on
the platform, or even on locale settings within the same platform, creating
compatibility problems.

> **Warning**
>
> Code that has to run on multiple machines or on multiple occasions should
> never depend on encoding defaults.  Always pass an explicit `encoding=`
> argument when opening text files, because the default may change from one
> machine to the next, or from one day to the next.

A curious detail in that session is that `write` reports that four characters
were written, but the next line reads five.  Here is a closer inspection, again
as run on Windows:

<!-- nocheck -->
```python
fp = open('cafe.txt', 'w', encoding='utf_8')
fp  # by default, open uses text mode and returns a TextIOWrapper
# <_io.TextIOWrapper name='cafe.txt' mode='w' encoding='utf_8'>
fp.write('café')  # write on a TextIOWrapper returns the number of characters written
# 4
fp.close()
import os
os.stat('cafe.txt').st_size  # UTF-8 encodes 'é' as 2 bytes, 0xc3 and 0xa9
# 5
fp2 = open('cafe.txt')  # no explicit encoding: the default comes from the locale
fp2
# <_io.TextIOWrapper name='cafe.txt' mode='r' encoding='cp1252'>
fp2.encoding
# 'cp1252'
fp2.read()  # in cp1252, 0xc3 is "Ã" and 0xa9 is the copyright sign
# 'cafÃ©'
fp3 = open('cafe.txt', encoding='utf_8')  # opening the file with the correct encoding
fp3
# <_io.TextIOWrapper name='cafe.txt' mode='r' encoding='utf_8'>
fp3.read()
# 'café'
fp4 = open('cafe.txt', 'rb')  # 'rb' opens the file for reading in binary mode
fp4  # the result is a BufferedReader, not a TextIOWrapper
# <_io.BufferedReader name='cafe.txt'>
fp4.read()  # reading it returns bytes, as expected
# b'caf\xc3\xa9'
```

> **Tip**
>
> Do not open text files in binary mode unless you need to analyze the file
> contents to determine the encoding, and even then, you should be using
> Chardet instead of reinventing the wheel.  Ordinary code should only use binary
> mode to open binary files, like raster images.

### Beware of Encoding Defaults

Several settings affect the encoding defaults for I/O in Python.  This script
explores them:

<!-- nocheck -->
```python
import locale
import sys

expressions = """
        locale.getpreferredencoding()
        type(my_file)
        my_file.encoding
        sys.stdout.isatty()
        sys.stdout.encoding
        sys.stdin.isatty()
        sys.stdin.encoding
        sys.stderr.isatty()
        sys.stderr.encoding
        sys.getdefaultencoding()
        sys.getfilesystemencoding()
    """

my_file = open('dummy', 'w')

for expression in expressions.split():
    value = eval(expression)
    print(f'{expression:>30} -> {value!r}')
```

On GNU/Linux and macOS the output shows that UTF-8 is used everywhere:

```console
$ python3 default_encodings.py
 locale.getpreferredencoding() -> 'UTF-8'
                 type(my_file) -> <class '_io.TextIOWrapper'>
              my_file.encoding -> 'UTF-8'
           sys.stdout.isatty() -> True
           sys.stdout.encoding -> 'utf-8'
            sys.stdin.isatty() -> True
            sys.stdin.encoding -> 'utf-8'
           sys.stderr.isatty() -> True
           sys.stderr.encoding -> 'utf-8'
      sys.getdefaultencoding() -> 'utf-8'
   sys.getfilesystemencoding() -> 'utf-8'
```

Before Python 3.15, on Windows the output could look like this instead:

```console
> chcp
Active code page: 437
> python default_encodings.py
 locale.getpreferredencoding() -> 'cp1252'
                 type(my_file) -> <class '_io.TextIOWrapper'>
              my_file.encoding -> 'cp1252'
           sys.stdout.isatty() -> True
           sys.stdout.encoding -> 'utf-8'
            sys.stdin.isatty() -> True
            sys.stdin.encoding -> 'utf-8'
           sys.stderr.isatty() -> True
           sys.stderr.encoding -> 'utf-8'
      sys.getdefaultencoding() -> 'utf-8'
   sys.getfilesystemencoding() -> 'utf-8'
```

`chcp` shows the active code page for the console: 437.  The most important
setting is `locale.getpreferredencoding()`, `'cp1252'` here, because text files
use it by default.  The output was going to the console, so
`sys.stdout.isatty()` is `True`, and the console encoding is UTF-8, not the code
page reported by `chcp`: that has been the case since
[**PEP 528**](https://peps.python.org/pep-0528/), implemented in Python 3.6.  The
same release implemented [**PEP 529**](https://peps.python.org/pep-0529/), which
changed the Windows filesystem encoding (used for names of directories and
files) from Microsoft's proprietary MBCS to UTF-8.  However, if the output of the
script were redirected to a file, `sys.stdout.isatty()` would become `False` and
`sys.stdout.encoding` would be set by `locale.getpreferredencoding()`, while
`sys.stdin.encoding` and `sys.stderr.encoding` remained `utf-8`.

That means a script like the following works when printing to a Windows console,
but could break when its output was redirected to a file:

<!-- nocheck -->
```python
import sys
from unicodedata import name

print(sys.version)
print()
print('sys.stdout.isatty():', sys.stdout.isatty())
print('sys.stdout.encoding:', sys.stdout.encoding)
print()

test_chars = [
    '\N{HORIZONTAL ELLIPSIS}',       # exists in cp1252, not in cp437
    '\N{INFINITY}',                  # exists in cp437, not in cp1252
    '\N{CIRCLED NUMBER FORTY TWO}',  # not in cp437 or in cp1252
]

for char in test_chars:
    print(f'Trying to output {name(char)}:')
    print(char)
```

The script uses the `'\N{}'` escape for Unicode literals, where you write the
official name of the character inside the braces.  It is rather verbose, but
explicit and safe: Python raises `SyntaxError` if the name doesn't exist, which is
much better than writing a hex number that could be wrong.  When redirected to a
file encoded as `cp1252`, printing `'∞'` raised `UnicodeEncodeError`, because
`cp1252` has no INFINITY character.

To summarize the different encoding settings:

* If you omit the `encoding` argument when opening a file, the default is given by
  `locale.getpreferredencoding()`, unless *UTF-8 mode* is enabled.
* The encoding of `sys.stdout`, `sys.stdin` and `sys.stderr` is UTF-8 for
  interactive I/O, or defined by `locale.getpreferredencoding()` if the
  output/input is redirected to/from a file (again, unless UTF-8 mode is on).
  The `PYTHONIOENCODING` environment variable can override it.
* `sys.getdefaultencoding()` is used internally by Python in implicit conversions
  of binary data to/from `str`.  Changing this setting is not supported.
* `sys.getfilesystemencoding()` is used to encode/decode filenames (not file
  contents).  It is used when `open()` gets a `str` argument for the filename; if
  the filename is given as a `bytes` argument, it is passed unchanged to the OS.

> **Note**
>
> *UTF-8 mode* ([**PEP 540**](https://peps.python.org/pep-0540/)) makes Python
> ignore the locale encoding and use UTF-8 for files, standard streams and
> filenames.  It can be enabled with `python -X utf8` or the `PYTHONUTF8=1`
> environment variable, and as of Python 3.15 it is enabled by default on every
> platform ([**PEP 686**](https://peps.python.org/pep-0686/)).  You can check it
> with `sys.flags.utf8_mode`, and `locale.getencoding()` still tells you the
> locale encoding the operating system would have used.  This removes most of
> the traps described above, but the advice stands: be explicit about encodings,
> because your code may run on older versions, or with UTF-8 mode disabled, or
> read files produced by programs that don't use UTF-8.

The documentation of `locale.getpreferredencoding()` says that it "only returns a
guess".  Therefore, the best advice about encoding defaults is: do not rely on
them.  You will avoid a lot of pain if you follow the advice of the Unicode
sandwich and are always explicit about the encodings in your programs.

Unfortunately, Unicode is painful even if you get your bytes correctly converted
to `str`.  The next two sections cover subjects that are simple in ASCII-land but
get quite complex on planet Unicode: text normalization (converting text to a
uniform representation for comparisons) and sorting.

## Normalizing Unicode for Reliable Comparisons

String comparisons are complicated by the fact that Unicode has *combining
characters*: diacritics and other marks that attach to the preceding character,
appearing as one when printed.  For example, the word "café" may be composed in
two ways, using four or five code points, but the result looks exactly the same:

```python
s1 = 'café'
s2 = 'cafe\N{COMBINING ACUTE ACCENT}'
s1, s2
# ('café', 'café')
len(s1), len(s2)
# (4, 5)
s1 == s2
# False
```

Placing `COMBINING ACUTE ACCENT` (U+0301) after "e" renders "é".  In the Unicode
standard, sequences like `'é'` and `'e\u0301'` are called *canonical equivalents*,
and applications are supposed to treat them as the same.  But Python sees two
different sequences of code points and considers them not equal.

The solution is [`unicodedata.normalize()`](https://docs.python.org/3/library/unicodedata.html#unicodedata.normalize).
Its first argument is one of four strings: `'NFC'`, `'NFD'`, `'NFKC'` and `'NFKD'`.
*Normalization Form C* (NFC) composes the code points to produce the shortest
equivalent string, while NFD decomposes, expanding composed characters into base
characters and separate combining characters.  Both make comparisons work as
expected:

```python
from unicodedata import normalize
s1 = 'café'
s2 = 'cafe\N{COMBINING ACUTE ACCENT}'
len(s1), len(s2)
# (4, 5)
len(normalize('NFC', s1)), len(normalize('NFC', s2))
# (4, 4)
len(normalize('NFD', s1)), len(normalize('NFD', s2))
# (5, 5)
normalize('NFC', s1) == normalize('NFC', s2)
# True
normalize('NFD', s1) == normalize('NFD', s2)
# True
```

Keyboard drivers usually generate composed characters, so text typed by users is
in NFC by default.  However, to be safe, it may be good to normalize strings with
`normalize('NFC', user_text)` before saving them.  NFC is also the normalization
form recommended by the W3C.

Some single characters are normalized by NFC into another single character.  The
symbol for the ohm (Ω), the unit of electrical resistance, is normalized to the
Greek uppercase omega.  They are visually identical, but they compare as unequal,
so it is essential to normalize to avoid surprises:

```python
from unicodedata import normalize, name
ohm = '\u2126'
name(ohm)
# 'OHM SIGN'
ohm_c = normalize('NFC', ohm)
name(ohm_c)
# 'GREEK CAPITAL LETTER OMEGA'
ohm == ohm_c
# False
normalize('NFC', ohm) == normalize('NFC', ohm_c)
# True
```

The other two normalization forms are NFKC and NFKD, where the letter K stands for
"compatibility".  These are stronger forms of normalization, affecting the
so-called *compatibility characters*.  Although one goal of Unicode is to have a
single "canonical" code point for each character, some characters appear more
than once for compatibility with preexisting standards.  For example, the `MICRO
SIGN`, `µ` (U+00B5), was added to Unicode to support round-trip conversion to
`latin1`, which includes it, even though the same character is part of the Greek
alphabet with code point U+03BC (`GREEK SMALL LETTER MU`).  So the micro sign is
considered a compatibility character.

In the NFKC and NFKD forms, each compatibility character is replaced by a
*compatibility decomposition* of one or more characters that are considered a
"preferred" representation, even if there is some formatting loss (ideally,
formatting should be the job of external markup, not of Unicode).  For example,
the compatibility decomposition of the one-half fraction `'½'` (U+00BD) is the
sequence of three characters `'1/2'`, and the compatibility decomposition of the
micro sign `'µ'` (U+00B5) is the lowercase mu `'μ'` (U+03BC).  Here is NFKC in
practice:

```python
from unicodedata import normalize, name
half = '\N{VULGAR FRACTION ONE HALF}'
print(half)
# ½
normalize('NFKC', half)
# '1⁄2'
for char in normalize('NFKC', half):
    print(char, name(char), sep='\t')
# 1	DIGIT ONE
# ⁄	FRACTION SLASH
# 2	DIGIT TWO
four_squared = '4²'
normalize('NFKC', four_squared)
# '42'
micro = 'µ'
micro_kc = normalize('NFKC', micro)
micro, micro_kc
# ('µ', 'μ')
ord(micro), ord(micro_kc)
# (181, 956)
name(micro), name(micro_kc)
# ('MICRO SIGN', 'GREEK SMALL LETTER MU')
```

Although `'1⁄2'` is a reasonable substitute for `'½'`, and the micro sign really is
a lowercase Greek mu, converting `'4²'` to `'42'` changes the meaning.  An
application could store `'4²'` as `'4<sup>2</sup>'`, but `normalize` knows nothing
about formatting.  Therefore NFKC or NFKD may lose or distort information, but
they can produce convenient intermediate representations for searching and
indexing.

Unfortunately, with Unicode everything is always more complicated than it first
seems.  For the `VULGAR FRACTION ONE HALF`, NFKC produced 1 and 2 joined by
`FRACTION SLASH`, instead of `SOLIDUS`, the familiar slash with ASCII code 47.  So
searching for the three-character ASCII sequence `'1/2'` would not find the
normalized Unicode sequence.  (Curiously, the micro sign is considered a
compatibility character but the ohm symbol is not.  As a result, NFC doesn't touch
the micro sign but changes the ohm symbol to capital omega, while NFKC and NFKD
change both into Greek characters.)

> **Warning**
>
> NFKC and NFKD normalization cause data loss and should be applied only in
> special cases like search and indexing, not for permanent storage of text.

### Case Folding

*Case folding* is essentially converting all text to lowercase, with some
additional transformations.  It is supported by the
[`str.casefold()`](https://docs.python.org/3/library/stdtypes.html#str.casefold)
method.  For any string `s` containing only `latin1` characters, `s.casefold()`
produces the same result as `s.lower()`, with only two exceptions: the micro sign
`'µ'` is changed to the Greek lowercase mu (which looks the same in most fonts),
and the German Eszett or "sharp s" (`ß`) becomes "ss":

```python
micro = 'µ'
name(micro)
# 'MICRO SIGN'
micro_cf = micro.casefold()
name(micro_cf)
# 'GREEK SMALL LETTER MU'
micro, micro_cf
# ('µ', 'μ')
eszett = 'ß'
name(eszett)
# 'LATIN SMALL LETTER SHARP S'
eszett_cf = eszett.casefold()
eszett, eszett_cf
# ('ß', 'ss')
```

There are nearly 300 code points for which `str.casefold()` and `str.lower()` return
different results.  As usual with anything related to Unicode, case folding is a
hard issue with plenty of linguistic special cases, but the Python core team made
an effort to provide a solution that hopefully works for most users.

### Utility Functions for Normalized Text Matching

As you've seen, NFC and NFD are safe to use and allow sensible comparisons
between Unicode strings.  NFC is the best normalized form for most applications,
and `str.casefold()` is the way to go for case-insensitive comparisons.  If you
work with text in many languages, a pair of functions like `nfc_equal` and
`fold_equal` are useful additions to your toolbox:

```python
from unicodedata import normalize

def nfc_equal(str1, str2):
    return normalize('NFC', str1) == normalize('NFC', str2)

def fold_equal(str1, str2):
    return (normalize('NFC', str1).casefold() ==
            normalize('NFC', str2).casefold())

s1 = 'café'
s2 = 'cafe\u0301'
s1 == s2
# False
nfc_equal(s1, s2)
# True
nfc_equal('A', 'a')
# False
s3 = 'Straße'
s4 = 'strasse'
s3 == s4
# False
nfc_equal(s3, s4)
# False
fold_equal(s3, s4)
# True
fold_equal(s1, s2)
# True
fold_equal('A', 'a')
# True
```

Beyond Unicode normalization and case folding, which are both part of the
Unicode standard, sometimes it makes sense to apply deeper transformations, like
changing `'café'` into `'cafe'`.

### Extreme "Normalization": Taking Out Diacritics

Search engines ignore diacritics (accents, cedillas and so on), at least in some
contexts.  Removing diacritics is not a proper form of normalization, because it
often changes the meaning of words and may produce false positives when
searching.  But it helps cope with some facts of life: people are sometimes lazy
or unsure about the correct use of diacritics, and spelling rules change over
time, meaning that accents come and go in living languages.

Outside of searching, getting rid of diacritics also makes for more readable
URLs, at least in Latin-based languages.  The URL for the Wikipedia article about
São Paulo is `https://en.wikipedia.org/wiki/S%C3%A3o_Paulo`, where `%C3%A3` is the
URL-escaped UTF-8 rendering of the single letter "ã".  The form
`https://en.wikipedia.org/wiki/Sao_Paulo` is much easier to recognize, even if it is
not the right spelling.

To remove all diacritics from a `str`, you can use a function like this:

```python
import unicodedata
import string

def shave_marks(txt):
    """Remove all diacritic marks"""
    norm_txt = unicodedata.normalize('NFD', txt)
    shaved = ''.join(c for c in norm_txt
                     if not unicodedata.combining(c))
    return unicodedata.normalize('NFC', shaved)
```

It decomposes all characters into base characters and combining marks, filters
out all combining marks, and recomposes the remaining characters.  Here it is in
use:

```python
order = '“Herr Voß: • ½ cup of Œtker™ caffè latte • bowl of açaí.”'
shave_marks(order)  # only the letters "è", "ç" and "í" were replaced
# '“Herr Voß: • ½ cup of Œtker™ caffe latte • bowl of acai.”'
Greek = 'Ζέφυρος, Zéfiro'
shave_marks(Greek)  # both "έ" and "é" were replaced
# 'Ζεφυρος, Zefiro'
```

`shave_marks` works, but maybe it goes too far.  Often the reason to remove
diacritics is to change Latin text to pure ASCII, but `shave_marks` also changes
non-Latin characters, like Greek letters, which will never become ASCII just by
losing their accents.  So it makes sense to analyze each base character and to
remove attached marks only if the base character is a letter of the Latin
alphabet:

```python
def shave_marks_latin(txt):
    """Remove all diacritic marks from Latin base characters"""
    norm_txt = unicodedata.normalize('NFD', txt)
    latin_base = False
    preserve = []
    for c in norm_txt:
        if unicodedata.combining(c) and latin_base:
            continue  # ignore diacritic on Latin base char
        preserve.append(c)
        # if it isn't a combining char, it's a new base char
        if not unicodedata.combining(c):
            latin_base = c in string.ascii_letters
    shaved = ''.join(preserve)
    return unicodedata.normalize('NFC', shaved)

shave_marks_latin(Greek)
# 'Ζέφυρος, Zefiro'
```

The function skips combining marks when the base character is Latin, keeps every
other character, and each time it sees a character that is not a combining mark,
it records whether that new base character is Latin.

An even more radical step is to replace common symbols in Western texts (curly
quotes, em dashes, bullets and so on) with ASCII equivalents:

```python
single_map = str.maketrans("""‚ƒ„ˆ‹‘’“”•–—˜›""",
                           """'f"^<''""---~>""")

multi_map = str.maketrans({
    '€': 'EUR',
    '…': '...',
    'Æ': 'AE',
    'æ': 'ae',
    'Œ': 'OE',
    'œ': 'oe',
    '™': '(TM)',
    '‰': '<per mille>',
    '†': '**',
    '‡': '***',
})

multi_map.update(single_map)

def dewinize(txt):
    """Replace Win1252 symbols with ASCII chars or sequences"""
    return txt.translate(multi_map)

def asciize(txt):
    no_marks = shave_marks_latin(dewinize(txt))
    no_marks = no_marks.replace('ß', 'ss')
    return unicodedata.normalize('NFKC', no_marks)
```

[`str.maketrans()`](https://docs.python.org/3/library/stdtypes.html#str.maketrans)
builds a mapping table for `str.translate()`: `single_map` maps characters to
characters, and `multi_map` maps characters to strings; the two tables are then
merged.  `dewinize` does not affect ASCII or `latin1` text, only the Microsoft
additions to `latin1` in `cp1252`.  `asciize` applies `dewinize`, removes diacritical
marks, replaces the Eszett with "ss" (not using case folding, because we want to
preserve case), and finally applies NFKC normalization to replace characters with
their compatibility equivalents:

```python
order = '“Herr Voß: • ½ cup of Œtker™ caffè latte • bowl of açaí.”'
dewinize(order)  # curly quotes, bullets and ™ were replaced
# '"Herr Voß: - ½ cup of OEtker(TM) caffè latte - bowl of açaí."'
asciize(order)  # dewinize, drop diacritics, replace 'ß'
# '"Herr Voss: - 1⁄2 cup of OEtker(TM) caffe latte - bowl of acai."'
```

> **Warning**
>
> Different languages have their own rules for removing diacritics.  For
> example, Germans change `'ü'` into `'ue'`.  Our `asciize` function is not that
> refined, so it may or may not be suitable for your language.

To summarize, these functions go far beyond standard normalization and perform
deep surgery on the text, with a good chance of changing its meaning.  Only you
can decide whether to go so far, knowing the target language, your users, and how
the transformed text will be used.

## Sorting Unicode Text

Python sorts sequences of any type by comparing the items in each sequence one
by one.  For strings, this means comparing the code points.  Unfortunately, this
produces unacceptable results for anyone who uses non-ASCII characters.
Consider sorting a list of fruits grown in Brazil:

```python
fruits = ['caju', 'atemoia', 'cajá', 'açaí', 'acerola']
sorted(fruits)
# ['acerola', 'atemoia', 'açaí', 'caju', 'cajá']
```

Sorting rules vary between locales, but in Portuguese and many other languages
that use the Latin alphabet, accents and cedillas rarely make a difference when
sorting (they matter only when they are the only difference between two words, in
which case the word with a diacritic comes after the plain one).  So "cajá" is
sorted as "caja" and must come before "caju".  The sorted list should be:

```python
['açaí', 'acerola', 'atemoia', 'cajá', 'caju']
```

The standard way to sort non-ASCII text in Python is the
[`locale.strxfrm()`](https://docs.python.org/3/library/locale.html#locale.strxfrm)
function which, according to the `locale` documentation, "transforms a string to
one that can be used in locale-aware comparisons".  To enable it, you must first
set a suitable locale for your application, and hope that the OS supports it:

<!-- nocheck -->
```python
import locale
my_locale = locale.setlocale(locale.LC_COLLATE, 'pt_BR.UTF-8')
print(my_locale)
fruits = ['caju', 'atemoia', 'cajá', 'açaí', 'acerola']
sorted_fruits = sorted(fruits, key=locale.strxfrm)
print(sorted_fruits)
```

On GNU/Linux with the `pt_BR.UTF-8` locale installed, this prints the correct
result:

```text
pt_BR.UTF-8
['açaí', 'acerola', 'atemoia', 'cajá', 'caju']
```

So you need to call `setlocale(LC_COLLATE, «your_locale»)` before using
`locale.strxfrm` as the sort key.  There are some caveats, though:

* Because locale settings are global, calling `setlocale` in a library is not
  recommended.  Your application or framework should set the locale when the
  process starts, and should not change it afterward.
* The locale must be installed on the OS, otherwise `setlocale` raises a
  `locale.Error: unsupported locale setting` exception.
* You must know how to spell the locale name.
* The locale must be correctly implemented by the makers of the OS.  On macOS,
  for example, `setlocale(LC_COLLATE, 'pt_BR.UTF-8')` may succeed without
  complaints while `sorted(fruits, key=locale.strxfrm)` still produces the same
  incorrect result as `sorted(fruits)`.

So the standard library solution to internationalized sorting works, but seems
to be well supported only on GNU/Linux, and even there it depends on locale
settings, creating deployment headaches.  Fortunately, there is a simpler
solution.

### Sorting with the Unicode Collation Algorithm

James Tauber created [pyuca](https://pypi.org/project/pyuca/), a pure-Python
implementation of the Unicode Collation Algorithm (UCA).  It is easy to use:

<!-- nocheck -->
```python
import pyuca
coll = pyuca.Collator()
fruits = ['caju', 'atemoia', 'cajá', 'açaí', 'acerola']
sorted_fruits = sorted(fruits, key=coll.sort_key)
sorted_fruits
# ['açaí', 'acerola', 'atemoia', 'cajá', 'caju']
```

This is simple and works on GNU/Linux, macOS and Windows.  pyuca does not take the
locale into account.  If you need to customize the sorting, you can provide the
path to a custom collation table to the `Collator()` constructor; out of the box it
uses `allkeys.txt`, a copy of the Default Unicode Collation Element Table bundled
with the project.

> **Tip**
>
> pyuca has a single sorting algorithm that does not respect the sorting order of
> individual languages.  For instance, Ä in German sorts between A and B, while in
> Swedish it comes after Z.  [PyICU](https://pypi.org/project/PyICU/) works like
> `locale` without changing the locale of the process, and it is also needed if you
> want to change the case of iİ/ıI in Turkish.  PyICU includes an extension that
> must be compiled, so it may be harder to install than pyuca, which is pure Python.

That collation table is one of the many data files that make up the Unicode
database, our next subject.

## The Unicode Database

The Unicode standard provides an entire database, in the form of several
structured text files, that includes not only the table mapping code points to
character names, but also metadata about the individual characters and how they
are related.  For example, the Unicode database records whether a character is
printable, is a letter, is a decimal digit, or is some other numeric symbol.
That's how the `str` methods `isalpha`, `isprintable`, `isdecimal` and `isnumeric`
work.  `str.casefold` also uses information from a Unicode table.

> **Note**
>
> The `unicodedata.category(char)` function returns the two-letter category of
> `char` from the Unicode database.  The higher-level `str` methods are easier to
> use.  For example, `label.isalpha()` returns `True` if every character in
> `label` belongs to one of these categories: `Lm`, `Lt`, `Lu`, `Ll` or `Lo`.  To
> learn what those codes mean, look up "General Category" in the Unicode
> character property documentation.

### Finding Characters by Name

The [`unicodedata`](https://docs.python.org/3/library/unicodedata.html) module has
functions to retrieve character metadata, including `unicodedata.name()`, which
returns a character's official name in the standard:

```python
from unicodedata import name
name('A')
# 'LATIN CAPITAL LETTER A'
name('ã')
# 'LATIN SMALL LETTER A WITH TILDE'
name('♛')
# 'BLACK CHESS QUEEN'
name('😸')
# 'GRINNING CAT FACE WITH SMILING EYES'
```

You can use `name()` to build applications that let users search for characters by
name.  The following command-line script, `cf.py`, takes one or more words as
arguments and lists the characters that have those words in their official Unicode
names.  Note the `if` statement in the `find` function: it uses the `.issubset()`
method to quickly test whether all the words in the query set appear in the list of
words built from the character's name.  Thanks to Python's rich set interface, we
don't need a nested `for` loop and another `if` to implement this check:

```python
#!/usr/bin/env python3
import sys
import unicodedata

START, END = ord(' '), sys.maxunicode + 1

def find(*query_words, start=START, end=END):
    query = {w.upper() for w in query_words}
    for code in range(start, end):
        char = chr(code)
        name = unicodedata.name(char, None)
        if name and query.issubset(name.split()):
            print(f'U+{code:04X}\t{char}\t{name}')

def main(words):
    if words:
        find(*words)
    else:
        print('Please provide words to find.')

if __name__ == '__main__':
    main(sys.argv[1:])
```

The script sets defaults for the range of code points to search.  `find` accepts
`query_words` and optional keyword-only arguments to limit the range of the
search, to make testing easier.  It converts `query_words` into a set of
uppercased strings, gets the Unicode character for each code, and gets the name of
the character, or `None` if the code point is unassigned.  If there is a name, it
splits it into a list of words and checks that the query set is a subset of that
list; if so, it prints a line with the code point in `U+9999` format, the
character, and its name.  Here it finds smiling cats:

```console
$ ./cf.py cat smiling
U+1F638	😸	GRINNING CAT FACE WITH SMILING EYES
U+1F63A	😺	SMILING CAT FACE WITH OPEN MOUTH
U+1F63B	😻	SMILING CAT FACE WITH HEART-SHAPED EYES
```

> **Note**
>
> Emoji support varies widely across operating systems and applications, and
> whether a character displays at all depends on the fonts available to your
> terminal.

### Numeric Meaning of Characters

The `unicodedata` module includes functions to check whether a Unicode character
represents a number and, if so, its numeric value for humans, as opposed to its
code point number.  This script shows `unicodedata.name()` and
`unicodedata.numeric()`, along with the `.isdigit()` and `.isnumeric()` methods of
`str`:

```python
import unicodedata
import re

re_digit = re.compile(r'\d')

sample = '1\xbc\xb2\u0969\u136b\u216b\u2466\u2480\u3285'

for char in sample:
    print(f'U+{ord(char):04x}',
          char.center(6),
          're_dig' if re_digit.match(char) else '-',
          'isdig' if char.isdigit() else '-',
          'isnum' if char.isnumeric() else '-',
          f'{unicodedata.numeric(char):5.2f}',
          unicodedata.name(char),
          sep='\t')
# U+0031	  1   	re_dig	isdig	isnum	 1.00	DIGIT ONE
# U+00bc	  ¼   	-	-	isnum	 0.25	VULGAR FRACTION ONE QUARTER
# U+00b2	  ²   	-	isdig	isnum	 2.00	SUPERSCRIPT TWO
# U+0969	  ३   	re_dig	isdig	isnum	 3.00	DEVANAGARI DIGIT THREE
# U+136b	  ፫   	-	isdig	isnum	 3.00	ETHIOPIC DIGIT THREE
# U+216b	  Ⅻ   	-	-	isnum	12.00	ROMAN NUMERAL TWELVE
# U+2466	  ⑦   	-	isdig	isnum	 7.00	CIRCLED DIGIT SEVEN
# U+2480	  ⒀   	-	-	isnum	13.00	PARENTHESIZED NUMBER THIRTEEN
# U+3285	  ㊅   	-	-	isnum	 6.00	CIRCLED IDEOGRAPH SIX
```

Each line shows the code point in `U+0000` format, the character centered in a
`str` of length 6, `re_dig` if the character matches the regular expression
`r'\d'`, `isdig` if `char.isdigit()` is `True`, `isnum` if `char.isnumeric()` is
`True`, the numeric value formatted with width 5 and 2 decimal places, and the
Unicode character name.

The sixth column, the result of `unicodedata.numeric(char)`, shows that Unicode
knows the numeric value of symbols that represent numbers.  So if you want to
create a spreadsheet application that supports Tamil digits or Roman numerals, go
for it!  The output also shows that the regular expression `r'\d'` matches the
digit "1" and the Devanagari digit 3, but not some other characters that
`isdigit` considers digits.  The `re` module is not as savvy about Unicode as it
could be; the [`regex`](https://pypi.org/project/regex/) module on PyPI was designed
to eventually replace `re` and provides better Unicode support.

## Dual-Mode `str` and `bytes` APIs

The standard library has functions that accept `str` or `bytes` arguments and
behave differently depending on the type.  Some examples can be found in the `re`
and `os` modules.

### `str` Versus `bytes` in Regular Expressions

If you build a regular expression with `bytes`, patterns such as `\d` and `\w` only
match ASCII characters; if these patterns are given as `str`, they match Unicode
digits or letters beyond ASCII.  This script compares how letters, ASCII digits,
superscripts and Tamil digits are matched by `str` and `bytes` patterns:

```python
import re

re_numbers_str = re.compile(r'\d+')
re_words_str = re.compile(r'\w+')
re_numbers_bytes = re.compile(rb'\d+')
re_words_bytes = re.compile(rb'\w+')

text_str = ("Ramanujan saw \u0be7\u0bed\u0be8\u0bef"
            " as 1729 = 1³ + 12³ = 9³ + 10³.")

text_bytes = text_str.encode('utf_8')

print(f'Text\n  {text_str!r}')
print('Numbers')
print('  str  :', re_numbers_str.findall(text_str))
print('  bytes:', re_numbers_bytes.findall(text_bytes))
print('Words')
print('  str  :', re_words_str.findall(text_str))
print('  bytes:', re_words_bytes.findall(text_bytes))
# Text
#   'Ramanujan saw ௧௭௨௯ as 1729 = 1³ + 12³ = 9³ + 10³.'
# Numbers
#   str  : ['௧௭௨௯', '1729', '1', '12', '9', '10']
#   bytes: [b'1729', b'1', b'12', b'9', b'10']
# Words
#   str  : ['Ramanujan', 'saw', '௧௭௨௯', 'as', '1729', '1³', '12³', '9³', '10³']
#   bytes: [b'Ramanujan', b'saw', b'as', b'1729', b'1', b'12', b'9', b'10']
```

The first two regular expressions are of the `str` type, the last two of the `bytes`
type.  The text to search contains the Tamil digits for 1729; its logical line
continues until the right parenthesis, and the two string literals are joined at
compile time (see [String literal concatenation](https://docs.python.org/3/reference/lexical_analysis.html#string-concatenation)).
A `bytes` string is needed to search with the `bytes` regular expressions.  The
`str` pattern `r'\d+'` matches the Tamil and ASCII digits; the `bytes` pattern
`rb'\d+'` matches only the ASCII bytes for digits.  The `str` pattern `r'\w+'` matches
letters, superscripts, Tamil and ASCII digits; the `bytes` pattern `rb'\w+'` matches
only the ASCII bytes for letters and digits.

This trivial example makes one point: you can use regular expressions on `str` and
`bytes`, but in the second case, bytes outside the ASCII range are treated as
nondigits and nonword characters.  For `str` regular expressions, there is a
`re.ASCII` flag that makes `\w`, `\W`, `\b`, `\B`, `\d`, `\D`, `\s` and `\S` perform
ASCII-only matching.

### `str` Versus `bytes` in `os` Functions

The GNU/Linux kernel is not Unicode savvy, so in the real world you may find
filenames made of byte sequences that are not valid in any sensible encoding
scheme and cannot be decoded to `str`.  File servers with clients using a variety
of operating systems are particularly prone to this problem.

To work around it, all `os` module functions that accept filenames or pathnames
take arguments as `str` or `bytes`.  If such a function is called with a `str`
argument, the argument is automatically converted using the codec named by
`sys.getfilesystemencoding()`, and the OS response is decoded with the same codec.
This is almost always what you want, in keeping with the Unicode sandwich.  But if
you must deal with (and perhaps fix) filenames that cannot be handled that way,
you can pass `bytes` arguments to the `os` functions to get `bytes` return values.
This lets you deal with any file or pathname, no matter how many gremlins you
find:

<!-- nocheck -->
```python
os.listdir('.')
# ['abc.txt', 'digits-of-π.txt']
os.listdir(b'.')
# [b'abc.txt', b'digits-of-\xcf\x80.txt']
```

The second filename is "digits-of-π.txt" (with the Greek letter pi).  Given a
`bytes` argument, `listdir` returns filenames as bytes: `b'\xcf\x80'` is the UTF-8
encoding of the Greek letter pi.

To help with manual handling of `str` or `bytes` sequences that are filenames or
pathnames, the `os` module provides the special encoding and decoding functions
`os.fsencode(name_or_path)` and `os.fsdecode(name_or_path)`.  Both accept an
argument of type `str`, `bytes`, or an object implementing the `os.PathLike`
interface.

## Summary

We started by dismissing the notion that 1 character == 1 byte.  As the world
adopts Unicode, we need to keep the concept of text strings separate from the
binary sequences that represent them in files, and Python 3 enforces this
separation.

After a brief overview of the binary sequence types (`bytes`, `bytearray` and
`memoryview`), we looked at encoding and decoding, with a sampling of important
codecs, followed by ways to prevent or deal with the infamous `UnicodeEncodeError`,
`UnicodeDecodeError`, and the `SyntaxError` caused by the wrong encoding in Python
source files.

In theory, the encoding of a byte sequence cannot be detected without metadata,
but in practice Chardet pulls it off pretty well for a number of popular
encodings.  Byte-order marks are the only encoding hint commonly found in UTF-16
and UTF-32 files, and sometimes in UTF-8 files as well.

Opening text files is easy except for one pitfall: the `encoding=` keyword
argument is not mandatory, but it should be.  If you fail to specify the encoding,
you end up with a program that generates "plain text" that is incompatible across
platforms, due to conflicting default encodings.  UTF-8 mode, now the default,
removes much of that pain, but explicit is still better than implicit.

Unicode provides multiple ways of representing some characters, so normalizing is a
prerequisite for text matching.  Besides normalization and case folding, we wrote
utility functions you can adapt to your needs, including drastic transformations
like removing all accents.  We sorted Unicode text correctly with the standard
`locale` module (with some caveats) and with the external pyuca package.  Finally,
we used the Unicode database to write a character finder in a couple dozen lines of
code, glanced at other Unicode metadata, and looked at dual-mode interfaces where
some functions can be called with `str` or `bytes` arguments, producing different
results.

> **See also**
>
> * The [Unicode HOWTO](https://docs.python.org/3/howto/unicode.html) in the Python
>   documentation approaches the subject from several angles, from a historical
>   introduction to syntax details, codecs, regular expressions, filenames and
>   best practices for Unicode-aware I/O.
> * Ned Batchelder's PyCon US 2012 talk "Pragmatic Unicode, or, How Do I Stop the
>   Pain?" popularized the Unicode sandwich, and he provides a full transcript
>   along with the slides and video.
> * [Standard Encodings](https://docs.python.org/3/library/codecs.html#standard-encodings)
>   in the `codecs` documentation lists the encodings Python supports.
> * Victor Stinner's free book *Programming with Unicode* covers Unicode in general,
>   as well as tools and APIs in the main operating systems and several languages,
>   including Python.
> * Since Python 3.3, the interpreter stores each `str` using the most economical
>   fixed-width layout for its contents: one byte per code point if all characters
>   are in the `latin1` range, otherwise two or four
>   ([**PEP 393**](https://peps.python.org/pep-0393/)).  One consequence is that a
>   single emoji can quadruple the memory used by an otherwise ASCII string.
