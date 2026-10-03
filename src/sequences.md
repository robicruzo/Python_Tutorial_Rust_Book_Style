# An Array of Sequences

Before creating Python, Guido van Rossum worked on ABC, a ten-year research
project to design a programming environment for beginners.  ABC introduced many
ideas we now consider "Pythonic": generic operations on different kinds of
sequences, built-in tuple and mapping types, structure by indentation, strong
typing without variable declarations, and more.

Python inherited from ABC its uniform handling of sequences.  Strings, lists,
byte sequences, arrays, XML elements and database results share a rich set of
common operations, including iteration, slicing, sorting and concatenation.
Knowing the variety of sequences available saves you from reinventing the
wheel, and their common interface encourages you to write functions that work
with existing and future sequence types alike.

This chapter extends the [Data Structures](datastructures.md) chapter.  It
covers list comprehensions and generator expressions in more depth, tuples used
as records and as immutable lists, unpacking, slicing, the pitfalls of `+`,
`*`, `+=` and `*=`, sorting, and specialized sequences such as arrays, memory
views and deques.  Unicode strings and byte sequences get their own chapter,
[Unicode Text Versus Bytes](unicode.md), and writing your own sequence types is
covered in [Special Methods for Sequences](sequence-protocol.md).

## Overview of Built-In Sequences

The standard library offers a rich selection of sequence types implemented in
C.  One useful way to group them is by what they hold:

*Container sequences*
: can hold items of different types, including nested containers.  Some
  examples: `list`, `tuple` and `collections.deque`.

*Flat sequences*
: hold items of one simple type.  Some examples: `str`, `bytes` and
  `array.array`.

A container sequence holds *references* to the objects it contains, which may
be of any type, while a flat sequence stores the *values* of its contents in its
own memory space, not as distinct Python objects.  A tuple of three floats, for
example, is an array of three references, each pointing to a separate `float`
object, while an `array('d')` of three floats is a single object holding a C
array of three `double` values.  Flat sequences are therefore more compact, but
they can only hold primitive machine values such as bytes, integers and floats.

> **Note**
>
> Every Python object in memory has a header with metadata.  The simplest
> Python object, a `float`, has a value field and two metadata fields:
> `ob_refcnt`, the object's reference count; `ob_type`, a pointer to the
> object's type; and `ob_fval`, a C `double` holding the value.  On a 64-bit
> build each of those fields takes 8 bytes.  That is why an array of floats is
> much more compact than a tuple of floats: the array is one object holding the
> raw values, while the tuple is several objects, the tuple itself plus each
> `float` in it.

Another way of grouping sequence types is by mutability:

*Mutable sequences*
: for example `list`, `bytearray`, `array.array` and `collections.deque`.

*Immutable sequences*
: for example `tuple`, `str` and `bytes`.

Mutable sequences support all the methods of immutable sequences plus several
more (`__setitem__()`, `__delitem__()`, `insert()`, `append()`, `extend()`,
`pop()`, `remove()`, `reverse()`, `__iadd__()`, ...).  The built-in sequence
types don't actually subclass the `Sequence` and `MutableSequence` abstract base
classes from [`collections.abc`](https://docs.python.org/3/library/collections.abc.html),
but they are registered as *virtual subclasses* of them (a mechanism explained in
[Interfaces, Protocols, and ABCs](protocols-abcs.md)), so they pass these tests:

```python
from collections import abc
issubclass(tuple, abc.Sequence)
# True
issubclass(list, abc.MutableSequence)
# True
```

Keep these two axes in mind, mutable versus immutable and container versus
flat.  They help you extrapolate what you know about one sequence type to the
others.

The most fundamental sequence type is the list, a mutable container.  You
already know lists well from [More on Lists](datastructures.md#tut-morelists), so
let's go straight to list comprehensions.

## List Comprehensions and Generator Expressions

A quick way to build a sequence is with a list comprehension, if the target is
a `list`, or with a generator expression, for any other kind of sequence.  If
you don't use these forms every day, you are probably missing chances to write
code that is both more readable and faster.  For brevity, many Python
programmers call them *listcomps* and *genexps*.

### List Comprehensions and Readability

Which of these two snippets do you find easier to read?

```python
symbols = '$¢£¥€¤'
codes = []
for symbol in symbols:
    codes.append(ord(symbol))

codes
# [36, 162, 163, 165, 8364, 164]
```

```python
symbols = '$¢£¥€¤'
codes = [ord(symbol) for symbol in symbols]
codes
# [36, 162, 163, 165, 8364, 164]
```

Anyone who knows a little Python can read the first version.  But once you
have learned listcomps, the second is easier to read because its intent is
explicit.  A `for` loop can do many different things: scan a sequence to count
or pick items, compute aggregates such as sums or averages, or any number of
other tasks.  The first snippet happens to be building a list, but you only
find that out by reading the whole loop.  A listcomp, on the other hand, always
has one purpose: to build a new list.

Of course, it is possible to abuse list comprehensions and write truly
incomprehensible code.  If you are not doing anything with the list produced,
you should not use a listcomp just to repeat some code for its side effects;
write a `for` loop.  Also try to keep listcomps short.  If one spans more than
two lines, it is probably better to break it apart or rewrite it as a plain
`for` loop.  Use your judgment: for Python, as for English, there are no
hard-and-fast rules for clear writing.

> **Tip**
>
> Line breaks are ignored inside pairs of `[]`, `{}` or `()`, so you can write
> multiline lists, listcomps, tuples, dictionaries and so on without the `\`
> line continuation escape (which silently stops working if you accidentally
> type a space after it).  Also, when those delimiters enclose a
> comma-separated series of items, a trailing comma is ignored.  Putting a comma
> after the last item of a multiline literal makes it easier for the next person
> to add an item, and reduces noise in diffs.

### Local Scope Within Comprehensions and Generator Expressions

List comprehensions, generator expressions, and their siblings the set and dict
comprehensions have a local scope that holds the variables assigned in their
`for` clauses.  However, a variable assigned with the "walrus operator" `:=`
remains accessible after the comprehension returns, unlike a local variable in
a function: [**PEP 572**](https://peps.python.org/pep-0572/) defines the scope of
the target of `:=` as the enclosing function, unless there is a `global` or
`nonlocal` declaration for it.

```python
x = 'ABC'
codes = [ord(x) for x in x]
x  # x was not clobbered: it's still bound to 'ABC'
# 'ABC'
codes
# [65, 66, 67]
codes = [last := ord(c) for c in x]
last  # last remains
# 67
c  # c is gone; it existed only inside the listcomp
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# NameError: name 'c' is not defined
```

### Listcomps Versus `map` and `filter`

Listcomps do everything the [`map()`](https://docs.python.org/3/library/functions.html#map)
and [`filter()`](https://docs.python.org/3/library/functions.html#filter) functions
do, without the contortions of Python's limited `lambda`.  Compare:

```python
symbols = '$¢£¥€¤'
beyond_ascii = [ord(s) for s in symbols if ord(s) > 127]
beyond_ascii
# [162, 163, 165, 8364, 164]
beyond_ascii = list(filter(lambda c: c > 127, map(ord, symbols)))
beyond_ascii
# [162, 163, 165, 8364, 164]
```

You might expect `map` and `filter` to be faster than the equivalent listcomp,
but that is not the case, at least not in examples like this one.  There is
more to say about `map` and `filter` in
[Functions as First-Class Objects](first-class-functions.md).

### Cartesian Products

Listcomps can build lists from the Cartesian product of two or more iterables.
The items of a Cartesian product are tuples made from items of every input
iterable, and the resulting list has a length equal to the lengths of the
inputs multiplied together.  For example, imagine you need a list of T-shirts
available in two colors and three sizes:

```python
colors = ['black', 'white']
sizes = ['S', 'M', 'L']
tshirts = [(color, size) for color in colors for size in sizes]
tshirts  # arranged by color, then size
# [('black', 'S'), ('black', 'M'), ('black', 'L'), ('white', 'S'),
#  ('white', 'M'), ('white', 'L')]
```

The resulting list is arranged as if the `for` loops were nested in the same
order as they appear in the listcomp:

```python
for color in colors:
    for size in sizes:
        print((color, size))
# ('black', 'S')
# ('black', 'M')
# ('black', 'L')
# ('white', 'S')
# ('white', 'M')
# ('white', 'L')
```

To arrange the items by size and then color, just swap the `for` clauses.
Adding a line break inside the listcomp makes the resulting order easier to
see:

```python
tshirts = [(color, size) for size in sizes
                         for color in colors]
tshirts
# [('black', 'S'), ('white', 'S'), ('black', 'M'), ('white', 'M'),
#  ('black', 'L'), ('white', 'L')]
```

The `FrenchDeck` class in [The Python Data Model](data-model.md) builds its 52
cards the same way, sorted by suit and then rank:

<!-- nocheck -->
```python
self._cards = [Card(rank, suit) for suit in self.suits
                                for rank in self.ranks]
```

Listcomps are a one-trick pony: they build lists.  To produce data for other
sequence types, use a generator expression.

### Generator Expressions

To initialize tuples, arrays and other sequences you could start from a
listcomp, but a genexp saves memory because it yields items one by one using
the iterator protocol, instead of building a whole list just to feed another
constructor.  Genexps use the same syntax as listcomps, but are enclosed in
parentheses rather than brackets:

```python
symbols = '$¢£¥€¤'
tuple(ord(symbol) for symbol in symbols)
# (36, 162, 163, 165, 8364, 164)
import array
array.array('I', (ord(symbol) for symbol in symbols))
# array('I', [36, 162, 163, 165, 8364, 164])
```

If a generator expression is the single argument in a function call, as in the
`tuple(...)` call, there is no need to duplicate the enclosing parentheses.
The `array` constructor takes two arguments, so there the parentheses around
the genexp are mandatory.  The first argument of `array` defines the storage
type used for the numbers, as you'll see in [Arrays](#arrays).

The next example uses a genexp with a Cartesian product to print a roster of
T-shirts.  Unlike the previous listcomp, the six-item list is never built in
memory: the generator expression feeds the `for` loop one item at a time.  If
the two input lists had a thousand items each, the genexp would save the cost of
building a million-item list just to feed the loop:

```python
colors = ['black', 'white']
sizes = ['S', 'M', 'L']
for tshirt in (f'{c} {s}' for c in colors for s in sizes):
    print(tshirt)
# black S
# black M
# black L
# white S
# white M
# white L
```

[Iterators, Generators, and Classic Coroutines](iterators-generators.md) explains
how generators work in detail.  Here the idea was just to show genexps used to
initialize sequences other than lists, or to produce output you don't need to
keep in memory.

## Tuples Are Not Just Immutable Lists

Some introductory texts present tuples as "immutable lists", but that sells
them short.  Tuples do double duty: they can be used as immutable lists and
also as *records with no field names*.  The second use is often overlooked, so
let's start with it.

### Tuples as Records

When a tuple holds a record, each item holds the data for one field, and the
position of the item gives it its meaning.  If you think of a tuple just as an
immutable list, the number and order of the items may or may not matter,
depending on the context.  But when a tuple is a collection of fields, the
number of items is usually fixed and their order is always important.  In the
following example, sorting any of the tuples would destroy information, because
the meaning of each field is given by its position:

```python
lax_coordinates = (33.9425, -118.408056)
city, year, pop, chg, area = ('Tokyo', 2003, 32_450, 0.66, 8014)
traveler_ids = [('USA', '31195855'), ('BRA', 'CE342567'),
    ('ESP', 'XDA205856')]
for passport in sorted(traveler_ids):
    print('%s/%s' % passport)
# BRA/CE342567
# ESP/XDA205856
# USA/31195855

for country, _ in traveler_ids:
    print(country)
# USA
# BRA
# ESP
```

Here `lax_coordinates` holds the latitude and longitude of Los Angeles
International Airport; the second line holds data about Tokyo: name, year,
population (thousands), population change (%), and area (km²); and
`traveler_ids` is a list of tuples of the form `(country_code,
passport_number)`.  As we iterate over that list, `passport` is bound to each
tuple, and the `%` formatting operator understands tuples, treating each item
as a separate field.  In the last loop, the `for` statement knows how to
retrieve the items of each tuple separately; this is called *unpacking*.  We
don't need the second item, so we assign it to `_`, a dummy variable.

> **Note**
>
> Using `_` as a dummy variable is just a convention; it's a strange but valid
> variable name.  However, in a `match`/`case` statement `_` is a wildcard that
> matches any value but is never bound to it (see
> [Pattern Matching in Depth](pattern-matching.md)).  And at the interactive
> prompt, the result of the last expression is assigned to `_`, unless the
> result is `None`.

We often think of records as data structures with named fields, and
[Data Class Builders](dataclasses.md) shows ways of creating tuples with named
fields.  But often there is no need to create a class just to name the fields,
especially if you use unpacking and avoid indexes.  Above, we assigned
`('Tokyo', 2003, 32_450, 0.66, 8014)` to `city, year, pop, chg, area` in a single
statement, and the `%` operator assigned each item of a `passport` tuple to the
corresponding slot of the format string.  Those are two examples of *tuple
unpacking*.  (The term *iterable unpacking* is gaining ground, as in the title of
[**PEP 3132**](https://peps.python.org/pep-3132/), because it works with any
iterable, as you'll see shortly.)

### Tuples as Immutable Lists

The interpreter and the standard library use tuples extensively as immutable
lists, and so should you.  This brings two key benefits:

*Clarity*
: when you see a tuple in code, you know its length will never change.

*Performance*
: a tuple uses less memory than a list of the same length, and it allows
  Python to do some optimizations.

Be aware, however, that the immutability of a tuple applies only to the
*references* it contains.  References in a tuple cannot be deleted or replaced,
but if one of them points to a mutable object and that object changes, then the
value of the tuple changes.  The next snippet creates two tuples, `a` and `b`,
that start out equal.  When the list inside `b` is changed, they are no longer
equal:

```python
a = (10, 'alpha', [1, 2])
b = (10, 'alpha', [1, 2])
a == b
# True
b[-1].append(99)
a == b
# False
b
# (10, 'alpha', [1, 2, 99])
```

Tuples with mutable items can be a source of bugs.  As
[Dictionaries and Sets](dicts-sets.md#what-is-hashable) explains, an object is
hashable only if its value can never change, and an unhashable tuple cannot be
used as a dictionary key or a set element.  If you want to find out explicitly
whether a tuple (or any object) has a fixed value, you can use the `hash()`
built-in in a function like this:

```python
def fixed(o):
    try:
        hash(o)
    except TypeError:
        return False
    return True

tf = (10, 'alpha', (1, 2))
tm = (10, 'alpha', [1, 2])
fixed(tf)
# True
fixed(tm)
# False
```

This issue is explored further in
[The Relative Immutability of Tuples](references.md#the-relative-immutability-of-tuples).

Despite that caveat, tuples are widely used as immutable lists, and they have
real performance advantages.  Python core developer Raymond Hettinger once
summarized them like this:

* To evaluate a tuple literal, the compiler generates bytecode for a tuple
  constant in one operation; for a list literal, the generated bytecode pushes
  each element as a separate constant and then builds the list.
* Given a tuple `t`, `tuple(t)` simply returns a reference to the same `t`;
  there is no need to copy.  Given a list `l`, `list(l)` must create a new copy.
* Because of its fixed length, a tuple is allocated exactly the memory it needs.
  Lists are allocated with room to spare, to amortize the cost of future
  appends.
* The references to the items of a tuple are stored in an array inside the tuple
  struct, while a list holds a pointer to an array of references stored
  elsewhere.  The indirection is needed because when a list outgrows its space,
  Python must reallocate the array of references, but it makes CPU caches less
  effective.

### Comparing Tuple and List Methods

When you use a tuple as an immutable variant of `list`, it is good to know how
similar their interfaces are.  `tuple` supports all the `list` methods that
don't add or remove items, with one exception: it lacks `__reversed__()`.  That
is just an optimization; `reversed(my_tuple)` works anyway.

| Method | `list` | `tuple` | Meaning |
|---|:-:|:-:|---|
| `s.__add__(s2)` | ● | ● | `s + s2`: concatenation |
| `s.__iadd__(s2)` | ● | | `s += s2`: in-place concatenation |
| `s.append(e)` | ● | | append one element after the last |
| `s.clear()` | ● | | delete all items |
| `s.__contains__(e)` | ● | ● | `e in s` |
| `s.copy()` | ● | | shallow copy of the list |
| `s.count(e)` | ● | ● | count occurrences of an element |
| `s.__delitem__(p)` | ● | | remove the item at position `p` |
| `s.extend(it)` | ● | | append items from iterable `it` |
| `s.__getitem__(p)` | ● | ● | `s[p]`: get the item at a position |
| `s.__getnewargs__()` | | ● | support for optimized serialization with `pickle` |
| `s.index(e)` | ● | ● | find the position of the first occurrence of `e` |
| `s.insert(p, e)` | ● | | insert element `e` before the item at position `p` |
| `s.__iter__()` | ● | ● | get an iterator |
| `s.__len__()` | ● | ● | `len(s)`: number of items |
| `s.__mul__(n)` | ● | ● | `s * n`: repeated concatenation |
| `s.__imul__(n)` | ● | | `s *= n`: in-place repeated concatenation |
| `s.__rmul__(n)` | ● | ● | `n * s`: reversed repeated concatenation |
| `s.pop([p])` | ● | | remove and return the last item, or the item at optional position `p` |
| `s.remove(e)` | ● | | remove the first occurrence of element `e` by value |
| `s.reverse()` | ● | | reverse the order of the items in place |
| `s.__reversed__()` | ● | | get an iterator to scan items from last to first |
| `s.__setitem__(p, e)` | ● | | `s[p] = e`: put `e` in position `p`, overwriting the existing item (also used to overwrite a subsequence; see [Assigning to Slices](#assigning-to-slices)) |
| `s.sort([key], [reverse])` | ● | | sort items in place, with optional keyword arguments `key` and `reverse` |

## Unpacking Sequences and Iterables

Unpacking matters because it avoids unnecessary and error-prone use of indexes
to extract elements from sequences.  It also works with any iterable as the data
source, including iterators, which don't support index notation (`[]`).  The
only requirement is that the iterable yields exactly one item per variable on
the receiving end, unless you use a star (`*`) to capture excess items, as
explained below.

The most visible form of unpacking is *parallel assignment*, that is, assigning
items from an iterable to a tuple of variables:

```python
lax_coordinates = (33.9425, -118.408056)
latitude, longitude = lax_coordinates  # unpacking
latitude
# 33.9425
longitude
# -118.408056
```

An elegant application of unpacking is swapping the values of variables
without a temporary variable:

```python
a, b = 1, 2
b, a = a, b
a, b
# (2, 1)
```

Another example is prefixing an argument with `*` when calling a function:

```python
divmod(20, 8)
# (2, 4)
t = (20, 8)
divmod(*t)
# (2, 4)
quotient, remainder = divmod(*t)
quotient, remainder
# (2, 4)
```

The last line shows another use of unpacking: letting functions return several
values in a way that is convenient for the caller.  As another example,
[`os.path.split()`](https://docs.python.org/3/library/os.path.html#os.path.split)
builds a tuple `(path, last_part)` from a filesystem path:

```python
import os
_, filename = os.path.split('/home/luciano/.ssh/id_rsa.pub')
filename
# 'id_rsa.pub'
```

### Using `*` to Grab Excess Items

Defining function parameters with `*args` to grab arbitrary excess arguments is
a classic Python feature (see [Arbitrary Argument Lists](controlflow.md#tut-arbitraryargs)).
In Python 3, the idea was extended to parallel assignment as well:

```python
a, b, *rest = range(5)
a, b, rest
# (0, 1, [2, 3, 4])
a, b, *rest = range(3)
a, b, rest
# (0, 1, [2])
a, b, *rest = range(2)
a, b, rest
# (0, 1, [])
```

In the context of parallel assignment, the `*` prefix can be applied to exactly
one variable, but that variable can appear in any position:

```python
a, *body, c, d = range(5)
a, body, c, d
# (0, [1, 2], 3, 4)
*head, b, c, d = range(5)
head, b, c, d
# ([0, 1], 2, 3, 4)
```

### Unpacking with `*` in Function Calls and Sequence Literals

[**PEP 448**](https://peps.python.org/pep-0448/) introduced more flexible syntax
for iterable unpacking.  In function calls, you can use `*` more than once:

```python
def fun(a, b, c, d, *rest):
    return a, b, c, d, rest

fun(*[1, 2], 3, *range(4, 7))
# (1, 2, 3, 4, (5, 6))
```

The `*` can also be used when defining `list`, `tuple` or `set` literals:

```python
*range(4), 4
# (0, 1, 2, 3, 4)
[*range(4), 4]
# [0, 1, 2, 3, 4]
{*range(4), 4, *(5, 6, 7)}
# {0, 1, 2, 3, 4, 5, 6, 7}
```

PEP 448 introduced similar syntax for `**`, which you'll see in
[Unpacking Mappings](dicts-sets.md#unpacking-mappings).

### Nested Unpacking

The target of an unpacking can use nesting, as in `(a, b, (c, d))`.  Python does
the right thing if the value has the same nesting structure.  In the following
script, each tuple holds a record with four fields, the last of which is a
coordinate pair:

```python
metro_areas = [
    ('Tokyo', 'JP', 36.933, (35.689722, 139.691667)),
    ('Delhi NCR', 'IN', 21.935, (28.613889, 77.208889)),
    ('Mexico City', 'MX', 20.142, (19.433333, -99.133333)),
    ('New York-Newark', 'US', 20.104, (40.808611, -74.020386)),
    ('São Paulo', 'BR', 19.649, (-23.547778, -46.635833)),
]

def main():
    print(f'{"":15} | {"latitude":>9} | {"longitude":>9}')
    for name, _, _, (lat, lon) in metro_areas:
        if lon <= 0:
            print(f'{name:15} | {lat:9.4f} | {lon:9.4f}')

if __name__ == '__main__':
    main()
```

By assigning the last field to a nested tuple, we unpack the coordinates, and
the `lon <= 0` test selects only cities in the Western hemisphere.  The output
is:

```text
                |  latitude | longitude
Mexico City     |   19.4333 |  -99.1333
New York-Newark |   40.8086 |  -74.0204
São Paulo       |  -23.5478 |  -46.6358
```

The target of an unpacking assignment can also be a list, but good use cases
are rare.  One is a database query that returns a single record (for example,
when the SQL has a `LIMIT 1` clause): you can unpack and at the same time make
sure there is exactly one result with `[record] = query_returning_single_row()`.
If the record has only one field, you can get it directly with
`[[field]] = query_returning_single_row_with_single_field()`.  Both could be
written with tuples, but don't forget that one-item tuples need a trailing
comma: the targets would be `(record,)` and `((field,),)`.  Forget a comma and
you get a silent bug.

## Pattern Matching with Sequences

Python 3.10 added *structural pattern matching* with the `match`/`case`
statement, introduced briefly in [`match` Statements](controlflow.md#tut-match).
Sequence patterns are a more powerful form of unpacking, called
*destructuring*.  For example, here is the previous loop rewritten with
`match`:

```python
def main():
    print(f'{"":15} | {"latitude":>9} | {"longitude":>9}')
    for record in metro_areas:
        match record:
            case [name, _, _, (lat, lon)] if lon <= 0:
                print(f'{name:15} | {lat:9.4f} | {lon:9.4f}')
```

Sequence patterns, along with mapping, class and other patterns, are covered in
[Pattern Matching in Depth](pattern-matching.md).

## Slicing

A common feature of `list`, `tuple`, `str` and every other sequence type in
Python is support for slicing, which is more powerful than most people
realize.  This section covers the advanced forms of slicing from the point of
view of a user; implementing slicing in your own classes is covered in
[Special Methods for Sequences](sequence-protocol.md).

### Why Slices and Ranges Exclude the Last Item

The Pythonic convention of excluding the last item in slices and ranges works
well with the zero-based indexing used in Python, C and many other languages.
Some convenient features of the convention are:

* It is easy to see the length of a slice or range when only the stop position
  is given: `range(3)` and `my_list[:3]` both produce three items.
* It is easy to compute the length of a slice or range when both start and stop
  are given: just subtract `stop - start`.
* It is easy to split a sequence in two parts at any index `x` without
  overlapping: simply take `my_list[:x]` and `my_list[x:]`.

```python
l = [10, 20, 30, 40, 50, 60]
l[:2]  # split at 2
# [10, 20]
l[2:]
# [30, 40, 50, 60]
l[:3]  # split at 3
# [10, 20, 30]
l[3:]
# [40, 50, 60]
```

The best arguments for this convention were written by the Dutch computer
scientist Edsger W. Dijkstra in a short memo titled
["Why Numbering Should Start at Zero"](https://www.cs.utexas.edu/users/EWD/transcriptions/EWD08xx/EWD831.html).
He explains why a sequence like 2, 3, ..., 12 is best written as 2 ≤ *i* < 13,
which is exactly why `'ABCDE'[1:3]` means `'BC'` and `range(2, 13)` produces
2, 3, ..., 12.

### Slice Objects

You may know that `s[a:b:c]` can specify a *stride* or *step* `c`, which makes
the resulting slice skip items.  The stride can also be negative, returning
items in reverse:

```python
s = 'bicycle'
s[::3]
# 'bye'
s[::-1]
# 'elcycib'
s[::-2]
# 'eccb'
```

You saw another example in [The Python Data Model](data-model.md), where
`deck[12::13]` picked all the aces in an unshuffled deck.

The notation `a:b:c` is valid only inside `[]` when used as the indexing or
subscript operator, and it produces a slice object: `slice(a, b, c)`.  To
evaluate `seq[start:stop:step]`, Python calls
`seq.__getitem__(slice(start, stop, step))`.  Even if you are not implementing
your own sequence types, knowing about slice objects is useful because it lets
you give names to slices, just as spreadsheets let you name ranges of cells.

Suppose you need to parse flat-file data like the following invoice.  Instead
of filling your code with hardcoded slices, you can name them.  See how
readable this makes the `for` loop at the end:

```python
invoice = """
0.....6.................................40........52...55........
1909  Pimoroni PiBrella                     $17.50    3    $52.50
1489  6mm Tactile Switch x20                 $4.95    2     $9.90
1510  Panavise Jr. - PV-201                 $28.00    1    $28.00
1601  PiTFT Mini Kit 320x240                $34.95    1    $34.95
"""
SKU = slice(0, 6)
DESCRIPTION = slice(6, 40)
UNIT_PRICE = slice(40, 52)
QUANTITY = slice(52, 55)
ITEM_TOTAL = slice(55, None)
line_items = invoice.split('\n')[2:]
for item in line_items:
    print(item[UNIT_PRICE], item[DESCRIPTION])
#     $17.50   Pimoroni PiBrella
#      $4.95   6mm Tactile Switch x20
#     $28.00   Panavise Jr. - PV-201
#     $34.95   PiTFT Mini Kit 320x240
```

Slice objects come back when we build our own collections in
[Special Methods for Sequences](sequence-protocol.md#a-sliceable-sequence).

### Multidimensional Slicing and Ellipsis

The `[]` operator can also take several indexes or slices separated by
commas.  The `__getitem__()` and `__setitem__()` special methods that handle
`[]` simply receive the indices in `a[i, j]` as a tuple.  In other words, to
evaluate `a[i, j]`, Python calls `a.__getitem__((i, j))`.

This is used, for instance, by the external NumPy package, where items of a
two-dimensional `numpy.ndarray` can be fetched with `a[i, j]` and a
two-dimensional slice is obtained with an expression like `a[m:n, k:l]`.  The
[NumPy](#numpy) section below shows this notation in action.  Except for
`memoryview`, the built-in sequence types are one-dimensional, so they support
only one index or slice, not a tuple of them.

The *ellipsis*, written with three full stops (`...`) and not `…` (Unicode
U+2026), is recognized as a token by the Python parser.  It is an alias for the
`Ellipsis` object, the single instance of the `ellipsis` class.  (No, that is not
backwards: the class name really is all lowercase, and the instance is a
built-in named `Ellipsis`, just as `bool` is lowercase but its instances are
`True` and `False`.)  As such, it can be passed as an argument to functions and
as part of a slice specification, as in `f(a, ..., z)` or `a[i:...]`.  NumPy uses
`...` as a shortcut when slicing arrays of many dimensions; for example, if `x`
is a four-dimensional array, `x[i, ...]` is a shortcut for `x[i, :, :, :,]`.

The standard library itself makes little use of `Ellipsis` or multidimensional
indexes and slices.  These syntactic features exist to support user-defined
types and extensions such as NumPy.

### Assigning to Slices

Slices are not just for extracting information from sequences; they can also
change mutable sequences in place, without rebuilding them from scratch.
Mutable sequences can be grafted, excised and otherwise modified using slice
notation on the left-hand side of an assignment or as the target of a `del`
statement:

```python
l = list(range(10))
l
# [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
l[2:5] = [20, 30]
l
# [0, 1, 20, 30, 5, 6, 7, 8, 9]
del l[5:7]
l
# [0, 1, 20, 30, 5, 8, 9]
l[3::2] = [11, 22]
l
# [0, 1, 20, 11, 5, 22, 9]
l[2:5] = 100
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# TypeError: must assign iterable to extended slice
l[2:5] = [100]
l
# [0, 1, 100, 22, 9]
```

When the target of the assignment is a slice, the right-hand side must be an
iterable object, even if it has just one item.

## Using `+` and `*` with Sequences

Python programmers expect sequences to support `+` and `*`.  Usually both
operands of `+` must be of the same sequence type; neither of them is modified,
and a new sequence of that type is created as the result of the concatenation.
To concatenate several copies of the same sequence, multiply it by an integer.
Again, a new sequence is created:

```python
l = [1, 2, 3]
l * 5
# [1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3, 1, 2, 3]
5 * 'abcd'
# 'abcdabcdabcdabcdabcd'
```

Both `+` and `*` always create a new object and never change their operands.

> **Warning**
>
> Beware of expressions like `a * n` when `a` is a sequence containing mutable
> items, because the result may surprise you.  For example, trying to initialize
> a list of lists as `my_list = [[]] * 3` results in a list with three
> references to the same inner list, which is probably not what you want.

### Building Lists of Lists

Sometimes you need to initialize a list with a certain number of nested lists,
for example to distribute students in a list of teams or to represent the
squares of a game board.  The best way to do it is with a list comprehension:

```python
board = [['_'] * 3 for i in range(3)]
board
# [['_', '_', '_'], ['_', '_', '_'], ['_', '_', '_']]
board[1][2] = 'X'
board
# [['_', '_', '_'], ['_', '_', 'X'], ['_', '_', '_']]
```

A tempting, but wrong, shortcut is this:

```python
weird_board = [['_'] * 3] * 3
weird_board
# [['_', '_', '_'], ['_', '_', '_'], ['_', '_', '_']]
weird_board[1][2] = 'O'
weird_board
# [['_', '_', 'O'], ['_', '_', 'O'], ['_', '_', 'O']]
```

The outer list is made of three references to the same inner list.  While it
is unchanged, all seems right, but placing a mark in row 1, column 2 reveals
that all the rows are aliases of the same object.  In essence, the wrong
version behaves like this code, which appends the same `row` three times:

```python
row = ['_'] * 3
board = []
for i in range(3):
    board.append(row)
```

The list comprehension, on the other hand, is equivalent to this code, which
builds a new row on each iteration:

```python
board = []
for i in range(3):
    row = ['_'] * 3
    board.append(row)

board
# [['_', '_', '_'], ['_', '_', '_'], ['_', '_', '_']]
board[2][0] = 'X'
board  # only row 2 is changed, as expected
# [['_', '_', '_'], ['_', '_', '_'], ['X', '_', '_']]
```

If either the problem or the solution here is not clear yet, relax:
[Object References, Mutability, and Recycling](references.md) explains the
mechanics and pitfalls of references and mutable objects.

### Augmented Assignment with Sequences

The augmented assignment operators `+=` and `*=` behave quite differently
depending on the first operand.  To keep things simple, let's focus on `+=`
first; the same ideas apply to `*=` and the other augmented assignment
operators.

The special method that makes `+=` work is `__iadd__()` (for "in-place
addition").  If `__iadd__()` is not implemented, Python falls back to calling
`__add__()`.  Consider `a += b`.  If `a` implements `__iadd__()`, that method is
called.  For mutable sequences such as `list`, `bytearray` and `array.array`,
`a` is changed in place; the effect is similar to `a.extend(b)`.  When `a` does
not implement `__iadd__()`, however, `a += b` has the same effect as
`a = a + b`: the expression `a + b` is evaluated first, producing a new object,
which is then bound to `a`.  In other words, the identity of the object bound to
`a` may or may not change, depending on whether `__iadd__()` is available.

For mutable sequences, it is a good bet that `__iadd__()` is implemented and
`+=` happens in place.  For immutable sequences, clearly there is no way for
that to happen.  The same is true of `*=`, which is implemented by
`__imul__()`.  Here is `*=` applied first to a mutable sequence and then to an
immutable one (your ids will differ):

```python
l = [1, 2, 3]
id(l)  # id of the initial list
# 4311953800
l *= 2
l
# [1, 2, 3, 1, 2, 3]
id(l)  # same object, with new items appended
# 4311953800
t = (1, 2, 3)
id(t)  # id of the initial tuple
# 4312681568
t *= 2
id(t)  # a new tuple was created
# 4301348296
```

Repeated concatenation of immutable sequences is inefficient, because instead
of just appending new items, the interpreter has to copy the whole target
sequence to create a new one.  (`str` is an exception: building strings with
`+=` in loops is so common that CPython optimizes for it, allocating strings
with extra room so that concatenation does not always require copying the whole
string.)

`__iadd__()` and `__imul__()` are discussed further in
[Operator Overloading](operator-overloading.md).

### A `+=` Assignment Puzzler

Try to answer without using the interpreter: what happens when you evaluate
these two lines?

<!-- nocheck -->
```python
t = (1, 2, [30, 40])
t[2] += [50, 60]
```

Choose the best answer:

1. `t` becomes `(1, 2, [30, 40, 50, 60])`.
2. `TypeError` is raised with the message `'tuple' object does not support item
   assignment`.
3. Neither.
4. Both 1 and 2.

Most people expect answer 2, but the right answer is 4, "Both 1 and 2":

```python
t = (1, 2, [30, 40])
t[2] += [50, 60]
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# TypeError: 'tuple' object does not support item assignment
t
# (1, 2, [30, 40, 50, 60])
```

Looking at the bytecode Python generates for the expression `s[a] += b` makes
it clear how this happens.  The [`dis`](https://docs.python.org/3/library/dis.html)
module disassembles it; this is the output of Python 3.13, and the exact
instructions vary between versions:

```python
import dis
dis.dis('s[a] += b')
#   0           RESUME                   0
#
#   1           LOAD_NAME                0 (s)
#               LOAD_NAME                1 (a)
#               COPY                     2
#               COPY                     2
#               BINARY_SUBSCR
#               LOAD_NAME                2 (b)
#               BINARY_OP               13 (+=)
#               SWAP                     3
#               SWAP                     2
#               STORE_SUBSCR
#               RETURN_CONST             0 (None)
```

`BINARY_SUBSCR` puts the value of `s[a]` on the top of the stack.  `BINARY_OP
(+=)` then performs the in-place addition on it; this succeeds when the value is
a mutable object, as the list inside `t` is.  Finally, `STORE_SUBSCR` assigns
`s[a] = ` the result, and that fails because `s` is the immutable tuple `t`.

This is a corner case that rarely bites anyone in practice, but there are three
lessons to take from it:

* Avoid putting mutable items in tuples.
* Augmented assignment is not an atomic operation: we just saw it raise an
  exception after doing part of its job.
* Inspecting Python bytecode is not too difficult, and it can help you see what
  is going on under the hood.

## `list.sort` Versus the `sorted` Built-In

The [`list.sort()`](https://docs.python.org/3/library/stdtypes.html#list.sort)
method sorts a list in place, that is, without making a copy.  It returns
`None` to remind you that it changes the receiver (the target of a method call,
the object bound to `self`) and does not create a new list.  This is an
important Python API convention: functions or methods that change an object in
place should return `None`, to make it clear to the caller that the receiver was
changed and no new object was created.  You can see the same behavior in
[`random.shuffle(s)`](https://docs.python.org/3/library/random.html#random.shuffle),
which shuffles the mutable sequence `s` in place and returns `None`.

> **Note**
>
> The convention of returning `None` to signal in-place changes has a drawback:
> you cannot chain calls to such methods.  Methods that return new objects
> (all the `str` methods, for example) can be chained in the *fluent interface*
> style.

By contrast, the built-in function
[`sorted()`](https://docs.python.org/3/library/functions.html#sorted) creates a new
list and returns it.  It accepts any iterable as an argument, including
immutable sequences and generators, and whatever the type of the iterable, it
always returns a newly created list.

Both `list.sort` and `sorted` take two optional keyword-only arguments:

*reverse*
: if `True`, the items are returned in descending order (that is, by reversing
  the comparison of the items).  The default is `False`.

*key*
: a one-argument function applied to each item to produce its sorting key.  For
  example, when sorting a list of strings, `key=str.lower` performs a
  case-insensitive sort, and `key=len` sorts the strings by length.  The default
  is the identity function: the items themselves are compared.

> **Tip**
>
> You can also use the optional keyword parameter `key` with the `min()` and
> `max()` built-ins and with other functions from the standard library, such as
> `itertools.groupby()` and `heapq.nlargest()`.

Here are a few examples.  They also show that Python's sorting algorithm is
*stable*, meaning it preserves the relative order of items that compare equal:

```python
fruits = ['grape', 'raspberry', 'apple', 'banana']
sorted(fruits)
# ['apple', 'banana', 'grape', 'raspberry']
fruits
# ['grape', 'raspberry', 'apple', 'banana']
sorted(fruits, reverse=True)
# ['raspberry', 'grape', 'banana', 'apple']
sorted(fruits, key=len)
# ['grape', 'apple', 'banana', 'raspberry']
sorted(fruits, key=len, reverse=True)
# ['raspberry', 'banana', 'grape', 'apple']
fruits
# ['grape', 'raspberry', 'apple', 'banana']
fruits.sort()
fruits
# ['apple', 'banana', 'grape', 'raspberry']
```

`sorted(fruits)` produces a new list sorted alphabetically (because all the
words are lowercase ASCII; see the warning below), leaving the original
unchanged.  Sorting by length keeps "grape" before "apple", both of length 5,
because the sort is stable; and for the same reason, the descending sort by
length is *not* the reverse of the ascending one.  Finally, `fruits.sort()`
sorts the list in place and returns `None`, which the interactive interpreter
does not display.

> **Warning**
>
> By default, Python sorts strings lexicographically by character code.  That
> means ASCII uppercase letters come before lowercase letters, and non-ASCII
> characters are unlikely to be sorted sensibly.
> [Sorting Unicode Text](unicode.md#sorting-unicode-text) covers proper ways of
> sorting text as humans expect.

The `key` argument is a great idea.  Some languages make you write a
two-argument comparison function returning -1, 0 or 1, like the `cmp(a, b)`
function of Python 2.  A `key` function is simpler, because you just write a
one-argument function that retrieves or computes the sorting criterion, and more
efficient, because it is called only once per item, while a comparison function
is called every time the algorithm compares two items.  With `key` you can even
sort a mixed bag of numbers and number-like strings, by deciding whether to
treat all items as integers or as strings:

```python
l = [28, 14, '28', 5, '9', '1', 0, 6, '23', 19]
sorted(l)
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# TypeError: '<' not supported between instances of 'str' and 'int'
sorted(l, key=int)
# [0, '1', 5, 6, '9', 14, 19, '23', 28, '28']
sorted(l, key=str)
# [0, '1', 14, 19, '23', 28, '28', 5, 6, '9']
```

The algorithm behind `sorted` and `list.sort` is *Timsort*, named after its
creator, core developer Tim Peters (who also wrote the Zen of Python; try
`import this`).  Timsort is adaptive: it switches between insertion sort and
merge sort strategies depending on how ordered the data already is, which pays
off because real-world data tends to contain runs of sorted items.

Once your sequences are sorted, they can be searched very efficiently.  The
[`bisect`](https://docs.python.org/3/library/bisect.html) module provides a binary
search algorithm, plus `bisect.insort()`, which inserts items while keeping a
sequence sorted:

```python
import bisect
haystack = [1, 4, 5, 6, 8, 12, 15, 20, 21, 23, 23, 26, 29, 30]
bisect.bisect(haystack, 22)  # index where 22 would be inserted
# 9
bisect.bisect_left(haystack, 23), bisect.bisect_right(haystack, 23)
# (9, 11)
bisect.insort(haystack, 22)
haystack[8:12]
# [21, 22, 23, 23]
```

A classic use of `bisect` is a table lookup by numeric ranges, such as
converting test scores to letter grades:

```python
def grade(score, breakpoints=[60, 70, 80, 90], grades='FDCBA'):
    i = bisect.bisect(breakpoints, score)
    return grades[i]

[grade(score) for score in [55, 60, 65, 70, 75, 80, 85, 90, 95]]
# ['F', 'D', 'D', 'C', 'C', 'B', 'B', 'A', 'A']
```

## When a List Is Not the Answer

The `list` type is flexible and easy to use, but depending on your
requirements there may be better options.  An array saves a lot of memory when
you need to handle millions of floating-point values.  If you are constantly
adding and removing items from opposite ends of a list, a `deque` (double-ended
queue) is a more efficient FIFO ("first in, first out") data structure.

> **Tip**
>
> If your code frequently checks whether an item is present in a collection
> (`item in my_collection`), consider using a `set` for `my_collection`,
> especially if it holds many items.  Sets are optimized for fast membership
> checking.  They are also iterable, but they are not sequences, because the
> ordering of set items is unspecified.  See [Dictionaries and Sets](dicts-sets.md).

### Arrays

If a list contains only numbers, an
[`array.array`](https://docs.python.org/3/library/array.html) is a more efficient
replacement.  Arrays support all mutable sequence operations (including
`.pop()`, `.insert()` and `.extend()`), plus extra methods for fast loading and
saving, such as `.frombytes()` and `.tofile()`.

A Python array is as lean as a C array.  An array of `float` values does not hold
full-fledged `float` instances, only the packed bytes representing their machine
values, like an array of `double` in C.  When creating an array you provide a
*typecode*, a letter that determines the C type used to store each item.  For
example, `b` is the typecode for what C calls a `signed char`, an integer from
-128 to 127.  If you create an `array('b')`, each item is stored in a single byte
and interpreted as an integer.  For large sequences of numbers this saves a lot
of memory, and Python will not let you store a number that doesn't fit the
type of the array.

The next example creates, saves and loads an array of 10 million random
floating-point numbers:

```python
from array import array
from random import random
floats = array('d', (random() for i in range(10**7)))
floats[-1]
# 0.07802343889111107
fp = open('floats.bin', 'wb')
floats.tofile(fp)
fp.close()
floats2 = array('d')
fp = open('floats.bin', 'rb')
floats2.fromfile(fp, 10**7)
fp.close()
floats2[-1]
# 0.07802343889111107
floats2 == floats
# True
```

We create an array of double-precision floats (typecode `'d'`) from a generator
expression, save it to a binary file with `tofile()`, then create an empty
array of doubles and read 10 million numbers back into it with `fromfile()`;
the contents match.  (Your random number will differ.)

As you can see, `array.tofile()` and `array.fromfile()` are easy to use.  They
are also very fast: loading 10 million doubles from a binary file takes on the
order of a tenth of a second, dozens of times faster than reading them from a
text file, which also requires parsing each line with `float()`.  The binary file
is also much smaller: 80,000,000 bytes (8 bytes per double, zero overhead),
against roughly 180 MB for the same data written as text.

> **Tip**
>
> For the specific case of numeric arrays representing binary data, such as
> raster images, Python has the `bytes` and `bytearray` types discussed in
> [Unicode Text Versus Bytes](unicode.md).

Here is how `list` and `array.array` compare:

| Method | `list` | `array` | Meaning |
|---|:-:|:-:|---|
| `s.__add__(s2)` | ● | ● | `s + s2`: concatenation |
| `s.__iadd__(s2)` | ● | ● | `s += s2`: in-place concatenation |
| `s.append(e)` | ● | ● | append one element after the last |
| `s.byteswap()` | | ● | swap bytes of all items for endianness conversion |
| `s.clear()` | ● | | delete all items |
| `s.__contains__(e)` | ● | ● | `e in s` |
| `s.copy()` | ● | | shallow copy of the list |
| `s.__copy__()` | | ● | support for `copy.copy` |
| `s.count(e)` | ● | ● | count occurrences of an element |
| `s.__deepcopy__()` | | ● | optimized support for `copy.deepcopy` |
| `s.__delitem__(p)` | ● | ● | remove the item at position `p` |
| `s.extend(it)` | ● | ● | append items from iterable `it` |
| `s.frombytes(b)` | | ● | append items from a byte sequence interpreted as packed machine values |
| `s.fromfile(f, n)` | | ● | append `n` items from binary file `f`, interpreted as packed machine values |
| `s.fromlist(l)` | | ● | append items from a list; if one causes `TypeError`, none are appended |
| `s.__getitem__(p)` | ● | ● | `s[p]`: get the item or slice at a position |
| `s.index(e)` | ● | ● | find the position of the first occurrence of `e` |
| `s.insert(p, e)` | ● | ● | insert element `e` before the item at position `p` |
| `s.itemsize` | | ● | length in bytes of each array item |
| `s.__iter__()` | ● | ● | get an iterator |
| `s.__len__()` | ● | ● | `len(s)`: number of items |
| `s.__mul__(n)` | ● | ● | `s * n`: repeated concatenation |
| `s.__imul__(n)` | ● | ● | `s *= n`: in-place repeated concatenation |
| `s.__rmul__(n)` | ● | ● | `n * s`: reversed repeated concatenation |
| `s.pop([p])` | ● | ● | remove and return the item at position `p` (default: last) |
| `s.remove(e)` | ● | ● | remove the first occurrence of element `e` by value |
| `s.reverse()` | ● | ● | reverse the order of the items in place |
| `s.__reversed__()` | ● | | get an iterator to scan items from last to first |
| `s.__setitem__(p, e)` | ● | ● | `s[p] = e`: put `e` in position `p`, overwriting an existing item or slice |
| `s.sort([key], [reverse])` | ● | | sort items in place, with optional keyword arguments `key` and `reverse` |
| `s.tobytes()` | | ● | return the items as packed machine values in a `bytes` object |
| `s.tofile(f)` | | ● | save the items as packed machine values to binary file `f` |
| `s.tolist()` | | ● | return the items as numeric objects in a `list` |
| `s.typecode` | | ● | one-character string identifying the C type of the items |

> **Tip**
>
> The `array` type has no in-place sort method like `list.sort()`.  If you need
> to sort an array, use the built-in `sorted()` function to rebuild it:
> `a = array.array(a.typecode, sorted(a))`.  To keep an array sorted while adding
> items to it, use `bisect.insort()`.

If you do a lot of work with arrays and don't know about `memoryview`, you are
missing out.

### Memory Views

The built-in [`memoryview`](https://docs.python.org/3/library/stdtypes.html#memoryview)
class is a shared-memory sequence type that lets you handle slices of arrays
without copying bytes.  It was inspired by the NumPy library.  Travis Oliphant,
lead author of NumPy, describes a memory view as essentially a generalized NumPy
array structure built into Python itself, without the math: it lets you share
memory between data structures (things like PIL images, SQLite databases, NumPy
arrays) without copying first, which is very important for large data sets.

Using notation similar to the `array` module, the `memoryview.cast()` method
lets you change the way multiple bytes are read or written as units, without
moving bits around.  `memoryview.cast()` returns yet another `memoryview`,
always sharing the same memory.  The following example creates alternative
views of the same 6 bytes, to operate on them as a 2×3 matrix or a 3×2 matrix:

```python
from array import array
octets = array('B', range(6))  # array of 6 bytes (typecode 'B')
m1 = memoryview(octets)
m1.tolist()
# [0, 1, 2, 3, 4, 5]
m2 = m1.cast('B', [2, 3])  # 2 rows and 3 columns
m2.tolist()
# [[0, 1, 2], [3, 4, 5]]
m3 = m1.cast('B', [3, 2])  # 3 rows and 2 columns
m3.tolist()
# [[0, 1], [2, 3], [4, 5]]
m2[1,1] = 22
m3[1,1] = 33
octets  # the memory is shared by octets, m1, m2 and m3
# array('B', [0, 1, 2, 33, 22, 5])
```

The power of `memoryview` can also be used to corrupt data.  The next example
changes a single byte of an item in an array of 16-bit integers:

```python
import array
numbers = array.array('h', [-2, -1, 0, 1, 2])
memv = memoryview(numbers)
len(memv)
# 5
memv[0]
# -2
memv_oct = memv.cast('B')
memv_oct.tolist()
# [254, 255, 255, 255, 0, 0, 1, 0, 2, 0]
memv_oct[5] = 4
numbers
# array('h', [-2, -1, 1024, 1, 2])
```

Here `memv` is a memory view of an array of five 16-bit signed integers
(typecode `'h'`).  Casting it to bytes (typecode `'B'`) gives `memv_oct`, which
sees the same memory as 10 bytes.  Assigning `4` to byte offset 5 puts a 4 in the
most significant byte of the third item, and a 4 in the high byte of a 2-byte
little-endian integer is 1024.

The [`struct`](https://docs.python.org/3/library/struct.html) module is a good
companion to `memoryview` when you need to parse binary records; see
[Structs and Memory Views](unicode.md#structs-and-memory-views).

### NumPy

This book focuses on what is in the standard library, but NumPy is so important
that a detour is warranted.  For advanced array and matrix operations, NumPy is
the reason Python became mainstream in scientific computing.  It implements
multidimensional, homogeneous arrays and matrix types that hold not only
numbers but also user-defined records, and provides efficient element-wise
operations.

SciPy is a library, written on top of NumPy, offering many scientific computing
algorithms from linear algebra, numerical calculus and statistics.  It is fast
and reliable because it leverages the widely used C and Fortran code base of the
Netlib Repository.  In other words, SciPy gives scientists the best of both
worlds: an interactive prompt and high-level Python interfaces, together with
industrial-strength number crunching optimized in C and Fortran.

As a very brief demo, here are some basic operations with two-dimensional
arrays.  NumPy is not part of the standard library; install it with
`python -m pip install numpy` (see [Virtual Environments and Packages](venv.md)).
By convention it is imported as `np`:

```python
import numpy as np
a = np.arange(12)  # build an ndarray with the integers 0 to 11
a
# array([ 0,  1,  2,  3,  4,  5,  6,  7,  8,  9, 10, 11])
type(a)
# <class 'numpy.ndarray'>
a.shape  # a one-dimensional, 12-element array
# (12,)
a = a.reshape(3, 4)  # change the shape, adding one dimension
a
# array([[ 0,  1,  2,  3],
#        [ 4,  5,  6,  7],
#        [ 8,  9, 10, 11]])
a[2]  # row at index 2
# array([ 8,  9, 10, 11])
a[2, 1]  # element at index 2, 1
# np.int64(9)
a[:, 1]  # column at index 1
# array([1, 5, 9])
a.transpose()  # swap columns with rows
# array([[ 0,  4,  8],
#        [ 1,  5,  9],
#        [ 2,  6, 10],
#        [ 3,  7, 11]])
```

NumPy also supports high-level operations for loading, saving and operating on
all elements of an array at once.  Assuming a text file with 10 million
floating-point numbers, one per line:

<!-- nocheck -->
```python
import numpy
floats = numpy.loadtxt('floats-10M-lines.txt')
floats[-3:]
# array([ 3016362.69195522,   535281.10514262,  4566560.44373946])
floats *= .5
floats[-3:]
# array([ 1508181.34597761,   267640.55257131,  2283280.22186973])
from time import perf_counter as pc
t0 = pc(); floats /= 3; pc() - t0
# 0.03690556302899495
numpy.save('floats-10M', floats)
floats2 = numpy.load('floats-10M.npy', 'r+')
floats2 *= 6
floats2[-3:]
# memmap([ 3016362.69195522,   535281.10514262,  4566560.44373946])
```

Here `floats *= .5` multiplies every element by 0.5, and dividing all 10 million
elements by 3 takes a few dozen milliseconds, measured with the high-resolution
[`time.perf_counter()`](https://docs.python.org/3/library/time.html#time.perf_counter).
`numpy.save()` writes the array to a binary `.npy` file, and `numpy.load()` with
mode `'r+'` loads it back as a *memory-mapped file*, which lets you process slices
of the array efficiently even if it does not fit entirely in memory.

This was just an appetizer.  NumPy and SciPy are the foundation of other
important tools such as pandas, which implements efficient array types that can
hold non-numeric data and provides import/export functions for many formats
(`.csv`, `.xls`, SQL dumps, HDF5, ...), and scikit-learn, the most widely used
machine learning toolset.  Most NumPy and SciPy functions are implemented in C
or C++ and can use all CPU cores, because they release Python's GIL (Global
Interpreter Lock).  The Dask project supports parallelizing NumPy, pandas and
scikit-learn processing across clusters of machines.  NumPy is all about
*vectorization*: applying mathematical functions to all elements of an array
without writing an explicit loop in Python, which lets the library use special
CPU vector instructions, multiple cores, or even the GPU.

### Deques and Other Queues

The `.append()` and `.pop()` methods make a `list` usable as a stack or a queue
(with `.append()` and `.pop(0)` you get FIFO behavior).  But inserting and
removing from the head of a list (the 0-index end) is costly, because the entire
list must be shifted in memory; [Using Lists as Queues](datastructures.md#tut-lists-as-queues)
already mentioned this.

The class [`collections.deque`](https://docs.python.org/3/library/collections.html#collections.deque)
is a thread-safe double-ended queue designed for fast inserting and removing at
both ends.  It is also the way to go if you need to keep a list of "last seen
items" or something like it, because a `deque` can be *bounded*, that is,
created with a fixed maximum length.  When a bounded `deque` is full and you add
a new item, it discards an item from the opposite end:

```python
from collections import deque
dq = deque(range(10), maxlen=10)
dq
# deque([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], maxlen=10)
dq.rotate(3)
dq
# deque([7, 8, 9, 0, 1, 2, 3, 4, 5, 6], maxlen=10)
dq.rotate(-4)
dq
# deque([1, 2, 3, 4, 5, 6, 7, 8, 9, 0], maxlen=10)
dq.appendleft(-1)
dq
# deque([-1, 1, 2, 3, 4, 5, 6, 7, 8, 9], maxlen=10)
dq.extend([11, 22, 33])
dq
# deque([3, 4, 5, 6, 7, 8, 9, 11, 22, 33], maxlen=10)
dq.extendleft([10, 20, 30, 40])
dq
# deque([40, 30, 20, 10, 3, 4, 5, 6, 7, 8], maxlen=10)
```

The optional `maxlen` argument sets the maximum number of items allowed in the
`deque`; it becomes a read-only `maxlen` attribute.  Rotating with `n > 0` takes
items from the right end and prepends them on the left; with `n < 0` items are
taken from the left and appended on the right.  Appending to a full deque
(`len(d) == d.maxlen`) discards items from the other end: `appendleft(-1)`
dropped the `0`, and adding three items on the right pushed out `-1`, `1` and
`2`.  Note that `extendleft(iter)` appends each successive item of its argument
to the left of the deque, so the final order of those items is reversed.

A `deque` implements almost all of the `list` methods (everything except
`sort()`) and adds a few specific to its design, like `appendleft()`,
`popleft()` and `rotate()`.  But there is a hidden cost: removing
items from the middle of a deque is not as fast.  It is really optimized for
appending and popping at the ends.  The `append()` and `popleft()` operations are
atomic, so a `deque` is safe to use as a FIFO queue in multithreaded programs
without locks.

| Method | `list` | `deque` | Meaning |
|---|:-:|:-:|---|
| `s.__add__(s2)` | ● | ● | `s + s2`: concatenation |
| `s.__iadd__(s2)` | ● | ● | `s += s2`: in-place concatenation |
| `s.append(e)` | ● | ● | append one element to the right (after the last) |
| `s.appendleft(e)` | | ● | append one element to the left (before the first) |
| `s.clear()` | ● | ● | delete all items |
| `s.__contains__(e)` | ● | ● | `e in s` |
| `s.copy()` | ● | ● | shallow copy |
| `s.__copy__()` | | ● | support for `copy.copy` (shallow copy) |
| `s.count(e)` | ● | ● | count occurrences of an element |
| `s.__delitem__(p)` | ● | ● | remove the item at position `p` |
| `s.extend(i)` | ● | ● | append items from iterable `i` to the right |
| `s.extendleft(i)` | | ● | append items from iterable `i` to the left |
| `s.__getitem__(p)` | ● | ● | `s[p]`: get the item or slice at a position |
| `s.index(e)` | ● | ● | find the position of the first occurrence of `e` |
| `s.insert(p, e)` | ● | ● | insert element `e` before the item at position `p` |
| `s.__iter__()` | ● | ● | get an iterator |
| `s.__len__()` | ● | ● | `len(s)`: number of items |
| `s.__mul__(n)` | ● | ● | `s * n`: repeated concatenation |
| `s.__imul__(n)` | ● | ● | `s *= n`: in-place repeated concatenation |
| `s.__rmul__(n)` | ● | ● | `n * s`: reversed repeated concatenation |
| `s.pop()` | ● | ● | remove and return the last item (`a_list.pop(p)` can also remove from position `p`; `deque` does not support that) |
| `s.popleft()` | | ● | remove and return the first item |
| `s.remove(e)` | ● | ● | remove the first occurrence of element `e` by value |
| `s.reverse()` | ● | ● | reverse the order of the items in place |
| `s.__reversed__()` | ● | ● | get an iterator to scan items from last to first |
| `s.rotate(n)` | | ● | move `n` items from one end to the other |
| `s.__setitem__(p, e)` | ● | ● | `s[p] = e`: put `e` in position `p`, overwriting an existing item or slice |
| `s.sort([key], [reverse])` | ● | | sort items in place, with optional keyword arguments `key` and `reverse` |

Besides `deque`, other standard library packages implement queues:

[`queue`](https://docs.python.org/3/library/queue.html)
: provides the synchronized (thread-safe) classes `SimpleQueue`, `Queue`,
  `LifoQueue` and `PriorityQueue`, which can be used for safe communication
  between threads.  All except `SimpleQueue` can be bounded by passing a
  `maxsize` argument greater than 0 to the constructor.  However, they don't
  discard items to make room as `deque` does.  Instead, when the queue is full,
  inserting a new item *blocks*: it waits until some other thread makes room by
  taking an item from the queue, which is useful to throttle the number of live
  threads.

[`multiprocessing`](https://docs.python.org/3/library/multiprocessing.html)
: implements its own unbounded `SimpleQueue` and bounded `Queue`, very similar
  to those in the `queue` package, but designed for interprocess communication.
  A specialized `multiprocessing.JoinableQueue` is provided for task management.

[`asyncio`](https://docs.python.org/3/library/asyncio-queue.html)
: provides `Queue`, `LifoQueue`, `PriorityQueue` and `JoinableQueue` with
  interfaces inspired by the classes in `queue` and `multiprocessing`, but
  adapted for managing tasks in asynchronous programming.

[`heapq`](https://docs.python.org/3/library/heapq.html)
: unlike the previous three modules, `heapq` does not implement a queue class,
  but provides functions like `heappush()` and `heappop()` that let you use a
  mutable sequence as a heap queue or priority queue.

## Summary

Mastering the standard library sequence types is a prerequisite for writing
concise, effective and idiomatic Python code.

Python sequences are often categorized as mutable or immutable, but it is also
useful to consider another axis: flat sequences and container sequences.  Flat
sequences are more compact, faster and easier to use, but they are limited to
atomic data such as numbers, characters and bytes.  Container sequences are more
flexible, but they may surprise you when they hold mutable objects, so you need
to use them carefully with nested data structures.  Python has no foolproof
immutable container sequence type: even "immutable" tuples can have their
values changed when they contain mutable items like lists or user-defined
objects.

List comprehensions and generator expressions are powerful notations for
building and initializing sequences.  If you are not yet comfortable with them,
take the time to master their basic usage.  It is not hard, and soon you will be
hooked.

Tuples play two roles: records with unnamed fields, and immutable lists.  When
you use a tuple as an immutable list, remember that its value is only guaranteed
to be fixed if all the items in it are also immutable; calling `hash(t)` is a
quick way to check.  When a tuple is used as a record, unpacking is the safest,
most readable way to extract its fields.  Beyond tuples, `*` works with lists and
iterables in many contexts, and `match`/`case` supports even more powerful
unpacking, known as destructuring.

Slicing is even more powerful than many people realize.  Multidimensional
slicing and `...` notation, as used in NumPy, can be supported by user-defined
sequences, and assigning to slices is a very expressive way of editing mutable
sequences.

Repeated concatenation as in `seq * n` is convenient and, with care, can be used
to initialize lists of lists containing immutable items.  Augmented assignment
with `+=` and `*=` behaves differently for mutable and immutable sequences: in
the latter case these operators necessarily build new sequences, while mutable
targets are usually changed in place, but not always, depending on how the
sequence is implemented.

The `sort` method and the `sorted` built-in are easy to use and flexible, thanks
to the optional `key` argument, which can also be used with `min` and `max`.
Beyond lists and tuples, the standard library provides `array.array` and
`collections.deque`, and if you do any kind of numerical processing on large
data sets, studying even a small part of NumPy and SciPy will take you a long
way.

> **See also**
>
> * The [Sorting Techniques](https://docs.python.org/3/howto/sorting.html) HOWTO
>   has several examples of advanced uses of `sorted` and `list.sort`.
> * [**PEP 3132**](https://peps.python.org/pep-3132/) (Extended Iterable
>   Unpacking) and [**PEP 448**](https://peps.python.org/pep-0448/) (Additional
>   Unpacking Generalizations) are the canonical sources on `*` unpacking.
> * [Container datatypes](https://docs.python.org/3/library/collections.html) in
>   the library reference has examples and practical recipes for `deque` and the
>   other collections.
> * Chapter 1, "Data Structures", of the *Python Cookbook*, 3rd ed., by David
>   Beazley and Brian K. Jones, has many recipes on sequences, including the trick
>   of naming slices.
