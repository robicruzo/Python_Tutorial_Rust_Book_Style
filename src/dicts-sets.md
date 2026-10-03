# Dictionaries and Sets

You use dictionaries in every Python program.  If not directly in your code,
then indirectly, because the `dict` type is a fundamental part of Python's
implementation.  Class and instance attributes, module namespaces and function
keyword arguments are some of the core constructs represented by dictionaries
in memory, and `__builtins__.__dict__` stores all the built-in types, objects
and functions.  It has been said, only half jokingly, that Python is basically
dicts wrapped in loads of syntactic sugar.

Because of their crucial role, Python dicts are highly optimized, and they keep
getting improvements.  Hash tables are the engines behind their performance.
Other built-in types based on hash tables are `set` and `frozenset`.  These offer
richer interfaces and operators than the sets you may have met in other
popular languages.  In particular, Python sets implement all the fundamental
operations of set theory, like union, intersection and subset tests, which lets
you express algorithms declaratively, without lots of nested loops and
conditionals.

This chapter builds on [Dictionaries](datastructures.md#tut-dictionaries) and
[Sets](datastructures.md#tut-sets) from the Data Structures chapter.  It covers:

* modern syntax to build and handle dicts and mappings, including enhanced
  unpacking and pattern matching;
* the common methods of mapping types;
* special handling for missing keys;
* the variations of `dict` in the standard library;
* the `set` and `frozenset` types;
* the practical implications of hash tables for the behavior of sets and
  dictionaries.

## Modern `dict` Syntax

The next sections describe syntax features to build, unpack and process
mappings.  Some are old, but may be new to you; others require Python 3.9 (the
`|` operator) or 3.10 (`match`/`case`).

### `dict` Comprehensions

The syntax of listcomps and genexps was adapted long ago to *dict
comprehensions* (and set comprehensions, which you'll see later).  A *dictcomp*
builds a `dict` instance by taking `key: value` pairs from any iterable.  Here
are two dictionaries built from the same list of tuples:

```python
dial_codes = [
    (880, 'Bangladesh'),
    (55,  'Brazil'),
    (86,  'China'),
    (91,  'India'),
    (62,  'Indonesia'),
    (81,  'Japan'),
    (234, 'Nigeria'),
    (92,  'Pakistan'),
    (7,   'Russia'),
    (1,   'United States'),
]
country_dial = {country: code for code, country in dial_codes}
country_dial
# {'Bangladesh': 880, 'Brazil': 55, 'China': 86, 'India': 91, 'Indonesia': 62,
#  'Japan': 81, 'Nigeria': 234, 'Pakistan': 92, 'Russia': 7, 'United States': 1}
{code: country.upper()
    for country, code in sorted(country_dial.items())
    if code < 70}
# {55: 'BRAZIL', 62: 'INDONESIA', 7: 'RUSSIA', 1: 'UNITED STATES'}
```

An iterable of key-value pairs like `dial_codes` could be passed directly to
the `dict` constructor, but in the first dictcomp we swap the pairs, so that
`country` is the key and `code` is the value.  The second dictcomp sorts
`country_dial` by name, swaps the pairs back, uppercases the values, and keeps
only the items with `code < 70`.

If you are used to listcomps, dictcomps are a natural next step.  If you are
not, the spread of the comprehension syntax makes it more profitable than ever
to become fluent in it.

### Unpacking Mappings

[**PEP 448**](https://peps.python.org/pep-0448/) improved support for mapping
unpacking in two ways.  First, you can apply `**` to more than one argument in a
function call.  This works when the keys are all strings and unique across all
arguments, because duplicate keyword arguments are forbidden:

```python
def dump(**kwargs):
    return kwargs

dump(**{'x': 1}, y=2, **{'z': 3})
# {'x': 1, 'y': 2, 'z': 3}
```

Second, `**` can be used inside a `dict` literal, also multiple times:

```python
{'a': 0, **{'x': 1}, 'y': 2, **{'z': 3, 'x': 4}}
# {'a': 0, 'x': 4, 'y': 2, 'z': 3}
```

In this case duplicate keys are allowed: later occurrences overwrite earlier
ones, as you can see from the value mapped to `x`.  This syntax can be used to
merge mappings, but there is a more direct way.

### Merging Mappings with `|`

Since Python 3.9, you can use `|` and `|=` to merge mappings.  This makes sense,
since these are also the set union operators.  The `|` operator creates a new
mapping:

```python
d1 = {'a': 1, 'b': 3}
d2 = {'a': 2, 'b': 4, 'c': 6}
d1 | d2
# {'a': 2, 'b': 4, 'c': 6}
```

Usually the new mapping has the same type as the left operand, `d1` here, but
it can have the type of the right operand when user-defined types are involved,
according to the operator overloading rules explained in
[Operator Overloading](operator-overloading.md).  To update an existing mapping
in place, use `|=`.  Continuing the example, `d1` was not changed by `|`, but now
it is:

```python
d1
# {'a': 1, 'b': 3}
d1 |= d2
d1
# {'a': 2, 'b': 4, 'c': 6}
```

> **Tip**
>
> If you need to support Python 3.8 or earlier, the "Motivation" section of
> [**PEP 584**](https://peps.python.org/pep-0584/) gives a good summary of other
> ways to merge mappings.

### Pattern Matching with Mappings

The `match`/`case` statement supports subjects that are mappings.  Mapping
patterns look like `dict` literals, but they match instances of any actual or
virtual subclass of `collections.abc.Mapping`.  Different kinds of patterns can
be combined and nested, which makes pattern matching a powerful tool for
processing records structured as nested mappings and sequences, like those you
often read from JSON APIs and from databases with semi-structured schemas.  The
following function extracts the names of creators from media records:

```python
def get_creators(record: dict) -> list:
    match record:
        case {'type': 'book', 'api': 2, 'authors': [*names]}:
            return names
        case {'type': 'book', 'api': 1, 'author': name}:
            return [name]
        case {'type': 'book'}:
            raise ValueError(f"Invalid 'book' record: {record!r}")
        case {'type': 'movie', 'director': name}:
            return [name]
        case _:
            raise ValueError(f'Invalid record: {record!r}')
```

The first case matches any mapping with `'type': 'book'`, `'api': 2`, and an
`'authors'` key mapped to a sequence, and returns the items of the sequence as a
new list.  The second matches a mapping with `'type': 'book'`, `'api': 1` and an
`'author'` key mapped to any object, and returns that object inside a list.  Any
other mapping with `'type': 'book'` is invalid.  The fourth case handles movies,
and anything else raises `ValueError`.

This function shows some useful practices for handling semi-structured data
such as JSON records: include a field describing the kind of record (for
example, `'type': 'movie'`); include a field identifying the schema version (for
example, `'api': 2`), to allow for future evolution of public APIs; and have
`case` clauses to handle invalid records of a specific type (for example,
`'book'`) as well as a catch-all.  Here is how it behaves:

```python
b1 = dict(api=1, author='Douglas Hofstadter',
        type='book', title='Gödel, Escher, Bach')
get_creators(b1)
# ['Douglas Hofstadter']
from collections import OrderedDict
b2 = OrderedDict(api=2, type='book',
        title='Python in a Nutshell',
        authors='Martelli Ravenscroft Holden'.split())
get_creators(b2)
# ['Martelli', 'Ravenscroft', 'Holden']
get_creators({'type': 'book', 'pages': 770})
# Traceback (most recent call last):
#     ...
# ValueError: Invalid 'book' record: {'type': 'book', 'pages': 770}
get_creators('Spam, spam, spam')
# Traceback (most recent call last):
#     ...
# ValueError: Invalid record: 'Spam, spam, spam'
```

Note that the order of the keys in the patterns is irrelevant, even when the
subject is an `OrderedDict` like `b2`.

Unlike sequence patterns, mapping patterns succeed on partial matches: `b1` and
`b2` include a `'title'` key that does not appear in any `'book'` pattern, yet
they match.  There is no need to use `**extra` to match extra key-value pairs,
but if you want to capture them as a `dict`, you can prefix one variable with
`**`.  It must be the last one in the pattern, and `**_` is forbidden because it
would be redundant:

```python
food = dict(category='ice cream', flavor='vanilla', cost=199)
match food:
    case {'category': 'ice cream', **details}:
        print(f'Ice cream details: {details}')
# Ice cream details: {'flavor': 'vanilla', 'cost': 199}
```

Later in this chapter you'll meet `defaultdict` and other mappings where
`d[key]` lookups succeed because missing items are created on the fly.  In the
context of pattern matching, however, a match succeeds only if the subject
already has the required keys at the top of the `match` statement.  The
automatic handling of missing keys is not triggered, because pattern matching
always uses the `d.get(key, sentinel)` method, where `sentinel` is a special
marker value that cannot occur in user data.

[Pattern Matching in Depth](pattern-matching.md) covers all the kinds of
patterns together.

## Standard API of Mapping Types

The [`collections.abc`](https://docs.python.org/3/library/collections.abc.html)
module provides the `Mapping` and `MutableMapping` ABCs describing the
interfaces of `dict` and similar types.  `Mapping` inherits from `Collection`
(and therefore from `Sized`, `Iterable` and `Container`) and adds the concrete
methods `__getitem__()`, `__contains__()`, `__eq__()`, `__ne__()`, `get()`,
`items()`, `keys()` and `values()`; `MutableMapping` adds `__setitem__()`,
`__delitem__()`, `clear()`, `pop()`, `popitem()`, `setdefault()` and `update()`.

The main value of the ABCs is documenting and formalizing the standard
interfaces for mappings, and serving as criteria for `isinstance` tests in code
that needs to support mappings in a broad sense:

```python
from collections import abc
my_dict = {}
isinstance(my_dict, abc.Mapping)
# True
isinstance(my_dict, abc.MutableMapping)
# True
```

> **Tip**
>
> Using `isinstance` with an ABC is often better than checking whether a
> function argument is of the concrete `dict` type, because then alternative
> mapping types can be used.  [Interfaces, Protocols, and ABCs](protocols-abcs.md)
> discusses this in detail.

To implement a custom mapping, it is easier to extend `collections.UserDict`, or
to wrap a `dict` by composition, than to subclass these ABCs.  The `UserDict`
class and all the concrete mapping classes in the standard library encapsulate
the basic `dict` in their implementation, which in turn is built on a hash
table.  Therefore they all share the limitation that the keys must be
*hashable* (the values need not be, only the keys).

### What Is Hashable

Here is part of the definition of
[hashable](https://docs.python.org/3/glossary.html#term-hashable) adapted from
the Python glossary:

> An object is hashable if it has a hash code which never changes during its
> lifetime (it needs a `__hash__()` method), and can be compared to other
> objects (it needs an `__eq__()` method).  Hashable objects which compare equal
> must have the same hash code.

Numeric types and the flat immutable types `str` and `bytes` are all hashable.
Container types are hashable if they are immutable and all the objects they
contain are also hashable.  A `frozenset` is always hashable, because every
element it contains must be hashable by definition.  A `tuple` is hashable only
if all its items are hashable:

```python
tt = (1, 2, (30, 40))
hash(tt)
# 8027212646858338501
tl = (1, 2, [30, 40])
hash(tl)
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# TypeError: unhashable type: 'list'
tf = (1, 2, frozenset([30, 40]))
hash(tf)
# -4118419923444501110
```

The hash code of an object may differ depending on the version of Python, the
machine architecture, and a *salt* added to the hash computation of strings
and bytes for security reasons (see [**PEP 456**](https://peps.python.org/pep-0456/)).
The hash code of a correctly implemented object is guaranteed to be constant
only within one Python process.

User-defined types are hashable by default, because their hash code is derived
from their `id()`, and the `__eq__()` method inherited from `object` simply
compares object ids.  If an object implements a custom `__eq__()` that takes its
internal state into account, it is hashable only if its `__hash__()` always
returns the same hash code.  In practice, this requires that `__eq__()` and
`__hash__()` only use instance attributes that never change during the life of
the object.  [A Pythonic Object](pythonic-object.md#a-hashable-vector2d)
shows how to do that.

### Overview of Common Mapping Methods

The basic interface of mappings is quite rich.  The following table shows the
methods implemented by `dict` and two popular variations defined in the
`collections` module, `defaultdict` and `OrderedDict` (optional arguments are
enclosed in `[...]`):

| Method | `dict` | `defaultdict` | `OrderedDict` | Meaning |
|---|:-:|:-:|:-:|---|
| `d.clear()` | ● | ● | ● | remove all items |
| `d.__contains__(k)` | ● | ● | ● | `k in d` |
| `d.copy()` | ● | ● | ● | shallow copy |
| `d.__copy__()` | | ● | | support for `copy.copy(d)` |
| `d.default_factory` | | ● | | callable invoked by `__missing__` to set missing values (an attribute set by the user, not a method) |
| `d.__delitem__(k)` | ● | ● | ● | `del d[k]`: remove the item with key `k` |
| `d.fromkeys(it, [initial])` | ● | ● | ● | new mapping from the keys in an iterable, with an optional initial value (defaults to `None`) |
| `d.get(k, [default])` | ● | ● | ● | get the item with key `k`; return `default` or `None` if missing |
| `d.__getitem__(k)` | ● | ● | ● | `d[k]`: get the item with key `k` |
| `d.items()` | ● | ● | ● | get a view over the items: `(key, value)` pairs |
| `d.__iter__()` | ● | ● | ● | get an iterator over the keys |
| `d.keys()` | ● | ● | ● | get a view over the keys |
| `d.__len__()` | ● | ● | ● | `len(d)`: number of items |
| `d.__missing__(k)` | | ● | | called when `__getitem__` cannot find the key |
| `d.move_to_end(k, [last])` | | | ● | move `k` to the first or last position (`last` is `True` by default) |
| `d.__or__(other)` | ● | ● | ● | `d1 \| d2`: new mapping merging `d1` and `d2` (Python 3.9+) |
| `d.__ior__(other)` | ● | ● | ● | `d1 \|= d2`: update `d1` with `d2` (Python 3.9+) |
| `d.pop(k, [default])` | ● | ● | ● | remove and return the value at `k`, or `default` or `None` if missing |
| `d.popitem()` | ● | ● | ● | remove and return the last inserted item as `(key, value)` |
| `d.__reversed__()` | ● | ● | ● | `reversed(d)`: iterator over the keys from last to first inserted |
| `d.__ror__(other)` | ● | ● | ● | `other \| d`: reversed union operator (Python 3.9+) |
| `d.setdefault(k, [default])` | ● | ● | ● | if `k in d`, return `d[k]`; else set `d[k] = default` and return it |
| `d.__setitem__(k, v)` | ● | ● | ● | `d[k] = v`: put `v` at `k` |
| `d.update(m, [**kwargs])` | ● | ● | ● | update `d` with items from a mapping or an iterable of `(key, value)` pairs |
| `d.values()` | ● | ● | ● | get a view over the values |

(`OrderedDict.popitem(last=False)` removes the first item inserted instead, FIFO
style; plain `dict` and `defaultdict` don't take that argument.)

The way `d.update(m)` handles its first argument `m` is a prime example of *duck
typing*: it first checks whether `m` has a `keys` method and, if it does,
assumes it is a mapping.  Otherwise, `update()` falls back to iterating over
`m`, assuming its items are `(key, value)` pairs.  The constructors of most
Python mappings use the logic of `update()` internally, which means they can be
initialized from other mappings or from any iterable producing `(key, value)`
pairs.

A subtle mapping method is `setdefault()`.  It avoids redundant key lookups when
you need to update the value of an item in place, as the next section shows.

### Inserting or Updating Mutable Values

In line with Python's fail-fast philosophy, `d[k]` raises an error when `k` is
not an existing key.  Pythonistas know that `d.get(k, default)` is an
alternative to `d[k]` whenever a default value is more convenient than handling
`KeyError`.  However, when you retrieve a mutable value in order to update it,
there is a better way.

Consider a script to index text, producing a mapping where each key is a word
and the value is a list of the positions where that word occurs, as pairs of
`(line_number, column_number)`.  Run on a file containing the Zen of Python, it
would print something like this:

```console
$ python3 index0.py zen.txt
a [(19, 48), (20, 53)]
Although [(11, 1), (16, 1), (18, 1)]
ambiguity [(14, 16)]
and [(15, 23)]
are [(21, 12)]
aren [(10, 15)]
at [(16, 38)]
bad [(19, 50)]
be [(15, 14), (16, 27), (20, 50)]
beats [(11, 23)]
Beautiful [(3, 1)]
better [(3, 14), (4, 13), (5, 11), (6, 12), (7, 9), (8, 11), (17, 8), (18, 25)]
...
```

Here is a suboptimal version of that script, written to show one case where
`dict.get` is not the best way to handle a missing key:

<!-- nocheck -->
```python
"""Build an index mapping word -> list of occurrences"""

import re
import sys

WORD_RE = re.compile(r'\w+')

index = {}
with open(sys.argv[1], encoding='utf-8') as fp:
    for line_no, line in enumerate(fp, 1):
        for match in WORD_RE.finditer(line):
            word = match.group()
            column_no = match.start() + 1
            location = (line_no, column_no)
            # this is ugly; coded like this to make a point
            occurrences = index.get(word, [])
            occurrences.append(location)
            index[word] = occurrences

# display in alphabetical order
for word in sorted(index, key=str.upper):
    print(word, index[word])
```

The three lines dealing with `occurrences` get the list of occurrences for
`word`, or `[]` if it is not found; append the new location; and put the
changed list back into `index`, which requires a second search through the
dictionary.  (In the `key=` argument of `sorted`, we are not calling
`str.upper`, just passing a reference to that method so that `sorted` can use it
to normalize the words for sorting.  That is an example of using a method as a
first-class function, the subject of
[Functions as First-Class Objects](first-class-functions.md).)

Those three lines can be replaced by a single line using `dict.setdefault`:

<!-- nocheck -->
```python
"""Build an index mapping word -> list of occurrences"""

import re
import sys

WORD_RE = re.compile(r'\w+')

index = {}
with open(sys.argv[1], encoding='utf-8') as fp:
    for line_no, line in enumerate(fp, 1):
        for match in WORD_RE.finditer(line):
            word = match.group()
            column_no = match.start() + 1
            location = (line_no, column_no)
            index.setdefault(word, []).append(location)

# display in alphabetical order
for word in sorted(index, key=str.upper):
    print(word, index[word])
```

`setdefault` gets the list of occurrences for `word`, or sets it to `[]` if it is
not found; and since it returns the value, the list can be updated without a
second search.  In other words, the end result of this line:

<!-- nocheck -->
```python
my_dict.setdefault(key, []).append(new_value)
```

is the same as running:

<!-- nocheck -->
```python
if key not in my_dict:
    my_dict[key] = []
my_dict[key].append(new_value)
```

except that the latter code performs at least two searches for `key` (three if
it is not found), while `setdefault` does it all with a single lookup.

A related issue, handling missing keys on any lookup and not only when
inserting, is the subject of the next section.

## Automatic Handling of Missing Keys

Sometimes it is convenient to have mappings that return some made-up value when
a missing key is searched.  There are two main approaches: use a `defaultdict`
instead of a plain `dict`, or subclass `dict` (or any other mapping type) and add
a `__missing__()` method.

### `defaultdict`: Another Take on Missing Keys

A [`collections.defaultdict`](https://docs.python.org/3/library/collections.html#collections.defaultdict)
creates items with a default value on demand whenever a missing key is searched
with `d[k]` syntax.  When you create a `defaultdict`, you provide a callable that
produces a default value whenever `__getitem__()` is passed a nonexistent key.
For example, given `dd = defaultdict(list)`, if `'new-key'` is not in `dd`, the
expression `dd['new-key']` does the following:

1. calls `list()` to create a new list;
2. inserts the list into `dd` using `'new-key'` as the key;
3. returns a reference to that list.

The callable that produces the default values is held in an instance attribute
named `default_factory`.  Here is yet another version of the word index script:

<!-- nocheck -->
```python
"""Build an index mapping word -> list of occurrences"""

import collections
import re
import sys

WORD_RE = re.compile(r'\w+')

index = collections.defaultdict(list)
with open(sys.argv[1], encoding='utf-8') as fp:
    for line_no, line in enumerate(fp, 1):
        for match in WORD_RE.finditer(line):
            word = match.group()
            column_no = match.start() + 1
            location = (line_no, column_no)
            index[word].append(location)

# display in alphabetical order
for word in sorted(index, key=str.upper):
    print(word, index[word])
```

We create a `defaultdict` with the `list` constructor as `default_factory`.  If
`word` is not yet in the index, `default_factory` is called to produce the
missing value, an empty list, which is assigned to `index[word]` and returned,
so the `.append(location)` operation always succeeds.

If no `default_factory` is provided, the usual `KeyError` is raised for missing
keys.

> **Warning**
>
> The `default_factory` of a `defaultdict` is only invoked to provide default
> values for `__getitem__()` calls, not for the other methods.  If `dd` is a
> `defaultdict` and `k` is a missing key, `dd[k]` calls `default_factory` to
> create a default value, but `dd.get(k)` still returns `None`, and `k in dd` is
> `False`.

The mechanism that makes `defaultdict` work by calling `default_factory` is the
`__missing__()` special method.

### The `__missing__` Method

Underlying the way mappings deal with missing keys is the aptly named
`__missing__()` method.  It is not defined in the base `dict` class, but `dict` is
aware of it: if you subclass `dict` and provide a `__missing__()` method, the
standard `dict.__getitem__()` calls it whenever a key is not found, instead of
raising `KeyError`.

Suppose you'd like a mapping where keys are converted to `str` when looked up.
A concrete use case is a device library for the Internet of Things, where a
programmable board with general-purpose I/O pins (a Raspberry Pi or an Arduino,
say) is represented by a `Board` class with a `pins` attribute mapping physical
pin identifiers to pin software objects.  The physical identifier may be just a
number or a string like `"A0"` or `"P9_12"`.  For consistency all keys in
`board.pins` should be strings, but it is also convenient to look up a pin by
number, as in `my_arduino.pins[13]`, so that beginners are not tripped up when
they want to blink the LED on pin 13.  Here is how such a mapping should behave:

<!-- nocheck -->
```python
d = StrKeyDict0([('2', 'two'), ('4', 'four')])
d['2']
# 'two'
d[4]
# 'four'
d[1]
# Traceback (most recent call last):
#   ...
# KeyError: '1'
d.get('2')
# 'two'
d.get(4)
# 'four'
d.get(1, 'N/A')
# 'N/A'
2 in d
# True
1 in d
# False
```

And here is a class `StrKeyDict0` that implements that behavior:

```python
class StrKeyDict0(dict):

    def __missing__(self, key):
        if isinstance(key, str):
            raise KeyError(key)
        return self[str(key)]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __contains__(self, key):
        return key in self.keys() or str(key) in self.keys()

d = StrKeyDict0([('2', 'two'), ('4', 'four')])
d[4]
# 'four'
d.get(1, 'N/A')
# 'N/A'
2 in d
# True
```

`StrKeyDict0` inherits from `dict`.  (A better way to create a user-defined
mapping type is to subclass `collections.UserDict`, as you'll see shortly; here
we subclass `dict` just to show that `__missing__()` is supported by the built-in
`dict.__getitem__()`.)  `__missing__()` checks whether the key is already a
`str`: if it is, and it is missing, it raises `KeyError`; otherwise it builds a
`str` from the key and looks it up.  The `get` method delegates to
`__getitem__()` by using the `self[key]` notation, which gives `__missing__()` the
opportunity to act; if `KeyError` is raised, `__missing__()` already failed, so
`get` returns the default.  Finally, `__contains__()` searches for the unmodified
key (the instance may contain non-`str` keys), and then for a `str` built from
it.

Take a moment to consider why the `isinstance(key, str)` test is necessary in
`__missing__()`.  Without it, the method would work for any key `k`, `str` or not,
whenever `str(k)` produced an existing key.  But if `str(k)` is not an existing
key, you'd have an infinite recursion: the last line, `self[str(key)]`, would
call `__getitem__()` with that `str` key, which in turn would call
`__missing__()` again.

`__contains__()` is also needed for consistent behavior, because `k in d` calls
it, and the method inherited from `dict` does not fall back on
`__missing__()`.  There is a subtle detail in the implementation: it does not
check for the key in the usual Pythonic way, `k in my_dict`, because `str(key)
in self` would call `__contains__()` recursively.  We avoid that by looking up the
key explicitly in `self.keys()`.  A search like `k in my_dict.keys()` is
efficient even for very large mappings, because `dict.keys()` returns a view,
which is similar to a set, as you'll see in
[Set Operations on `dict` Views](#set-operations-on-dict-views).  (Do remember,
though, that in ordinary code `k in my_dict` does the same job and is faster,
because it avoids the attribute lookup to find `.keys`.)  The check for the
unmodified key, `key in self.keys()`, is necessary for correctness because
`StrKeyDict0` does not force all keys to be `str`; its only goal is to make
searching friendlier.

### Inconsistent Usage of `__missing__` in the Standard Library

User-defined classes derived from standard library mappings may or may not use
`__missing__()` as a fallback in their implementations of `__getitem__()`, `get`
or `__contains__()`.  Consider these minimal scenarios:

*A `dict` subclass*
: implementing only `__missing__()` and no other method.  `__missing__()` may be
  called only on `d[k]`, which uses the `__getitem__()` inherited from `dict`.

*A `collections.UserDict` subclass*
: likewise implementing only `__missing__()`.  The `get` method inherited from
  `UserDict` calls `__getitem__()`, so `__missing__()` may be called to handle
  lookups with `d[k]` and `d.get(k)`.

*An `abc.Mapping` subclass with the simplest possible `__getitem__()`*
: implementing `__missing__()` and the required abstract methods, with a
  `__getitem__()` that does not call `__missing__()`.  `__missing__()` is never
  triggered.

*An `abc.Mapping` subclass with `__getitem__()` calling `__missing__()`*
: `__missing__()` is triggered for missing key lookups made with `d[k]`,
  `d.get(k)` and `k in d`.

If your subclass implements `__getitem__()`, `get` and `__contains__()`, you can
make those methods use `__missing__()` or not, depending on your needs.  The point
is that you must be careful when subclassing standard library mappings to use
`__missing__()`, because the base classes behave differently by default.  Don't
forget that `setdefault` and `update` are also affected by key lookup.  And
depending on the logic of your `__missing__()`, you may need special logic in
`__setitem__()` too, to avoid inconsistent or surprising behavior, as the
[`UserDict` example](#subclassing-userdict-instead-of-dict) below shows.

## Variations of `dict`

This section is an overview of the mapping types in the standard library
besides `defaultdict`, which was covered above.

### `collections.OrderedDict`

Now that the built-in `dict` keeps keys ordered (since Python 3.6, officially
since 3.7), the most common reason to use
[`OrderedDict`](https://docs.python.org/3/library/collections.html#collections.OrderedDict)
is writing code that is backward compatible with earlier versions.  Still, the
documentation lists some remaining differences between `dict` and
`OrderedDict`, here reordered by their relevance in daily use:

* The equality operation for `OrderedDict` checks for matching order.
* The `popitem()` method of `OrderedDict` has a different signature: it accepts
  an optional argument to specify which item is popped.
* `OrderedDict` has a `move_to_end()` method to efficiently reposition an
  element to an endpoint.
* The regular `dict` was designed to be very good at mapping operations;
  tracking insertion order was secondary.
* `OrderedDict` was designed to be good at reordering operations; space
  efficiency, iteration speed and the performance of update operations were
  secondary.
* Algorithmically, `OrderedDict` handles frequent reordering operations better
  than `dict`, which makes it suitable for tracking recent accesses, for example
  in an LRU cache.

```python
from collections import OrderedDict
dict(a=1, b=2) == dict(b=2, a=1)
# True
OrderedDict(a=1, b=2) == OrderedDict(b=2, a=1)
# False
od = OrderedDict.fromkeys('abcde')
od.move_to_end('b')
''.join(od)
# 'acdeb'
od.popitem(last=False)
# ('a', None)
```

### `collections.ChainMap`

A [`ChainMap`](https://docs.python.org/3/library/collections.html#collections.ChainMap)
instance holds a list of mappings that can be searched as one.  The lookup is
performed on each input mapping in the order it appears in the constructor call,
and succeeds as soon as the key is found in one of them:

```python
d1 = dict(a=1, b=3)
d2 = dict(a=2, b=4, c=6)
from collections import ChainMap
chain = ChainMap(d1, d2)
chain['a']
# 1
chain['c']
# 6
```

A `ChainMap` does not copy the input mappings, but holds references to them.
Updates and insertions affect only the first input mapping:

```python
chain['c'] = -1
d1
# {'a': 1, 'b': 3, 'c': -1}
d2
# {'a': 2, 'b': 4, 'c': 6}
```

`ChainMap` is useful for implementing interpreters for languages with nested
scopes, where each mapping represents a scope context, from the innermost
enclosing scope to the outermost.  The documentation has several examples,
including this snippet inspired by the basic rules of variable lookup in Python:

<!-- nocheck -->
```python
import builtins
pylookup = ChainMap(locals(), globals(), vars(builtins))
```

[Pattern Matching in Depth](pattern-matching.md#environment-with-chainmap) shows a
`ChainMap` subclass used in an interpreter for a subset of the Scheme language.

### `collections.Counter`

A [`Counter`](https://docs.python.org/3/library/collections.html#collections.Counter)
is a mapping that holds an integer count for each key.  Updating an existing key
adds to its count.  It can be used to count instances of hashable objects, or as
a *multiset*: pretend each key is an element of the set, and the count is the
number of occurrences of that element.  `Counter` implements the `+` and `-`
operators to combine tallies, and other useful methods such as
`most_common([n])`, which returns an ordered list of tuples with the *n* most
common items and their counts.  Here is `Counter` counting letters in words:

```python
import collections
ct = collections.Counter('abracadabra')
ct
# Counter({'a': 5, 'b': 2, 'r': 2, 'c': 1, 'd': 1})
ct.update('aaaaazzz')
ct
# Counter({'a': 10, 'z': 3, 'b': 2, 'r': 2, 'c': 1, 'd': 1})
ct.most_common(3)
# [('a', 10), ('z', 3), ('b', 2)]
```

Note that `'b'` and `'r'` are tied in third place, but `ct.most_common(3)` shows
only three counts.

### `shelve.Shelf`

The [`shelve`](https://docs.python.org/3/library/shelve.html) module provides
persistent storage for a mapping of string keys to Python objects serialized in
the `pickle` binary format.  The curious name makes sense when you realize that
pickle jars are stored on shelves.  The `shelve.open()` function returns a
`shelve.Shelf` instance, a simple key-value DBM database backed by the `dbm`
module, with these characteristics:

* `shelve.Shelf` subclasses `abc.MutableMapping`, so it provides the essential
  methods you expect of a mapping type.
* In addition, it provides a few I/O management methods, like `sync` and
  `close`.
* A `Shelf` instance is a context manager, so you can use a `with` block to make
  sure it is closed after use.
* Keys and values are saved whenever a new value is assigned to a key.
* The keys must be strings.
* The values must be objects that the `pickle` module can serialize.

```python
import shelve
with shelve.open('spam_db') as db:
    db['eggs'] = {'count': 3, 'colors': ['white', 'brown']}

with shelve.open('spam_db') as db:
    print(db['eggs'])
# {'count': 3, 'colors': ['white', 'brown']}
```

> **Warning**
>
> `pickle` is easy to use in the simplest cases, but it has several drawbacks,
> including security: never unpickle data from an untrusted source.  Read the
> documentation of the `shelve`, `dbm` and `pickle` modules for details and
> caveats, and consider other serialization formats such as JSON
> (see [Saving structured data with json](inputoutput.md#tut-json)).

`OrderedDict`, `ChainMap`, `Counter` and `Shelf` are ready to use but can also be
customized by subclassing.  In contrast, `UserDict` is intended only as a base
class to be extended.

### Subclassing `UserDict` Instead of `dict`

It is better to create a new mapping type by extending
[`collections.UserDict`](https://docs.python.org/3/library/collections.html#collections.UserDict)
than `dict`.  You can see why when you try to extend `StrKeyDict0` to make sure
that any keys added to the mapping are stored as `str`.

The main reason is that the built-in has some implementation shortcuts that end
up forcing you to override methods that you can just inherit from `UserDict`
with no problems.  (The exact problem with subclassing `dict` and other
built-ins is covered in
[Subclassing Built-In Types Is Tricky](inheritance.md#subclassing-built-in-types-is-tricky).)
Note that `UserDict` does not inherit from `dict`, but uses composition: it has
an internal `dict` instance, called `data`, which holds the actual items.  This
avoids undesired recursion when coding special methods like `__setitem__()`, and
simplifies the coding of `__contains__()`.

Thanks to `UserDict`, `StrKeyDict` is more concise than `StrKeyDict0`, yet it
does more: it stores all keys as `str`, avoiding unpleasant surprises if the
instance is built or updated with data containing nonstring keys:

```python
import collections

class StrKeyDict(collections.UserDict):

    def __missing__(self, key):
        if isinstance(key, str):
            raise KeyError(key)
        return self[str(key)]

    def __contains__(self, key):
        return str(key) in self.data

    def __setitem__(self, key, item):
        self.data[str(key)] = item

d = StrKeyDict([(2, 'two'), ('4', 'four')])
sorted(d.keys())
# ['2', '4']
d.update({6: 'six'})
d[6], d.get(6), 6 in d
# ('six', 'six', True)
```

`__missing__()` is exactly as before.  `__contains__()` is simpler: we can assume
all stored keys are `str`, and we can check `self.data` instead of invoking
`self.keys()`.  `__setitem__()` converts any key to a `str`; this method is easy to
override when we can delegate to the `self.data` attribute.

Because `UserDict` extends `abc.MutableMapping`, the remaining methods that make
`StrKeyDict` a full-fledged mapping are inherited from `UserDict`,
`MutableMapping` or `Mapping`.  The latter have several useful concrete methods,
despite being ABCs.  Two are worth noting:

`MutableMapping.update`
: This powerful method can be called directly, but it is also used by
  `__init__()` to load the instance from other mappings, from iterables of
  `(key, value)` pairs, and from keyword arguments.  Because it uses
  `self[key] = value` to add items, it ends up calling our `__setitem__()`.

`Mapping.get`
: In `StrKeyDict0` we had to code our own `get` to return the same results as
  `__getitem__()`, but here we inherit `Mapping.get`, which is implemented exactly
  like `StrKeyDict0.get`.

> **Note**
>
> [**PEP 455**](https://peps.python.org/pep-0455/) proposed adding a
> `TransformDict` to `collections`, more general than `StrKeyDict` and
> preserving the keys as provided, before the transformation is applied.  The
> PEP was rejected in 2015, but its idea is a nice exercise.

## Immutable Mappings

The mapping types provided by the standard library are all mutable, but you may
need to prevent users from changing a mapping by accident.  A concrete use case
is, again, the hardware library mentioned above: the `board.pins` mapping
represents the physical GPIO pins on the device, which can't be changed by
software, so any change to the mapping would make it inconsistent with the
physical reality.

The [`types`](https://docs.python.org/3/library/types.html#types.MappingProxyType)
module provides a wrapper class called `MappingProxyType` which, given a mapping,
returns a `mappingproxy` instance that is a read-only but *dynamic* proxy for the
original mapping.  Updates to the original can be seen through the proxy, but
changes cannot be made through it:

```python
from types import MappingProxyType
d = {1: 'A'}
d_proxy = MappingProxyType(d)
d_proxy
# mappingproxy({1: 'A'})
d_proxy[1]  # items in d can be seen through d_proxy
# 'A'
d_proxy[2] = 'x'  # changes cannot be made through d_proxy
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# TypeError: 'mappingproxy' object does not support item assignment
d[2] = 'B'
d_proxy  # d_proxy is dynamic: any change in d is reflected
# mappingproxy({1: 'A', 2: 'B'})
d_proxy[2]
# 'B'
```

In the hardware scenario, the constructor of a concrete `Board` subclass would
fill a private mapping with the pin objects and expose it to clients through a
public `.pins` attribute implemented as a `mappingproxy`.  That way clients could
not add, remove or change pins by accident.

## Dictionary Views

The `dict` methods `.keys()`, `.values()` and `.items()` return instances of
classes called `dict_keys`, `dict_values` and `dict_items`.  These *dictionary
views* are read-only projections of the internal data structures of the `dict`.
They avoid the memory overhead of the equivalent Python 2 methods, which
returned lists duplicating data already in the dictionary.  Here are some basic
operations supported by all dictionary views:

```python
d = dict(a=10, b=20, c=30)
values = d.values()
values  # the repr of a view shows its content
# dict_values([10, 20, 30])
len(values)
# 3
list(values)  # views are iterable
# [10, 20, 30]
reversed(values)  # views implement __reversed__
# <dict_reversevalueiterator object at 0x10e9e7310>
values[0]  # but you can't use [] to get individual items
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# TypeError: 'dict_values' object is not subscriptable
```

A view object is a dynamic proxy.  If the source `dict` is updated, you
immediately see the changes through an existing view:

```python
d['z'] = 99
d
# {'a': 10, 'b': 20, 'c': 30, 'z': 99}
values
# dict_values([10, 20, 30, 99])
```

The classes `dict_keys`, `dict_values` and `dict_items` are internal: they are not
available via `__builtins__` or any standard library module, and even if you get
a reference to one of them, you can't use it to create a view from scratch in
Python code:

```python
values_class = type({}.values())
v = values_class()
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# TypeError: cannot create 'dict_values' instances
```

The `dict_values` class is the simplest view: it implements only `__len__()`,
`__iter__()` and `__reversed__()`.  In addition, `dict_keys` and `dict_items`
implement several set methods, almost as many as `frozenset`; more on that in
[Set Operations on `dict` Views](#set-operations-on-dict-views).

## Practical Consequences of How `dict` Works

The hash table implementation of `dict` is very efficient, but it is important to
understand the practical effects of the design:

* Keys must be hashable objects, implementing proper `__hash__()` and `__eq__()`
  methods as described in [What Is Hashable](#what-is-hashable).
* Item access by key is very fast.  A `dict` may have millions of keys, but
  Python can locate a key directly by computing its hash code and deriving an
  index offset into the hash table, with the possible overhead of a small number
  of tries to find a matching entry.
* Key ordering is preserved as a side effect of a more compact memory layout
  for `dict` introduced in CPython 3.6, which became an official language
  feature in 3.7.
* Despite the compact layout, dicts inevitably have a significant memory
  overhead.  The most compact internal data structure for a container would be
  an array of pointers to the items (that's how tuples are stored).  A hash table
  needs to store more data per entry, and Python needs to keep at least a third
  of the hash table rows empty to remain efficient.
* To save memory, avoid creating instance attributes outside of the `__init__()`
  method.

That last tip comes from the fact that, by default, Python stores instance
attributes in a special `__dict__` attribute, which is a `dict` attached to each
instance (unless the class defines `__slots__`, as explained in
[Saving Memory with `__slots__`](pythonic-object.md#saving-memory-with-__slots__)).
Since [**PEP 412**](https://peps.python.org/pep-0412/) (key-sharing dictionaries)
was implemented in Python 3.3, instances of a class can share a common hash
table, stored with the class.  That common table is shared by the `__dict__` of
each new instance that has the same attribute names as the first instance of the
class when `__init__()` returns.  Each instance `__dict__` can then hold only its
own attribute values, as a simple array of pointers.  Adding an instance
attribute after `__init__()` forces Python to create a new hash table just for the
`__dict__` of that one instance.  According to PEP 412, this optimization reduces
memory use by 10% to 20% in object-oriented programs.

## Set Theory

Sets are not new in Python, but they are still somewhat underused.  The `set`
type and its immutable sibling `frozenset` first appeared as modules in Python
2.3 and were promoted to built-ins in Python 2.6.  (In this chapter, "set" means
both `set` and `frozenset`.)

A set is a collection of unique objects.  A basic use case is removing
duplicates:

```python
l = ['spam', 'spam', 'eggs', 'spam', 'bacon', 'eggs']
set(l)
# {'eggs', 'spam', 'bacon'}
list(set(l))
# ['eggs', 'spam', 'bacon']
```

(The order of the elements may differ on your machine.)

> **Tip**
>
> If you want to remove duplicates but also preserve the order of the first
> occurrence of each item, you can use a plain `dict`:
>
> ```python
> dict.fromkeys(l).keys()
> # dict_keys(['spam', 'eggs', 'bacon'])
> list(dict.fromkeys(l).keys())
> # ['spam', 'eggs', 'bacon']
> ```

Set elements must be hashable.  The `set` type is not hashable, so you can't
build a set with nested `set` instances.  But `frozenset` is hashable, so you can
have `frozenset` elements inside a `set`.

In addition to enforcing uniqueness, the set types implement many set
operations as infix operators: given two sets `a` and `b`, `a | b` returns their
union, `a & b` their intersection, `a - b` the difference, and `a ^ b` the
symmetric difference.  Smart use of set operations can reduce both the line
count and the execution time of programs, and make code easier to read and
reason about, by removing loops and conditional logic.

For example, imagine you have a large set of email addresses (the `haystack`)
and a smaller set of addresses (the `needles`), and you need to count how many
needles occur in the haystack.  Thanks to set intersection, that is one line:

<!-- nocheck -->
```python
found = len(needles & haystack)
```

Without the intersection operator, you'd have to write:

<!-- nocheck -->
```python
found = 0
for n in needles:
    if n in haystack:
        found += 1
```

The first version runs slightly faster.  The second works for any iterable
`needles` and `haystack`, while the first requires both to be sets.  But if you
don't have sets on hand, you can always build them on the fly:

<!-- nocheck -->
```python
found = len(set(needles) & set(haystack))

# another way:
found = len(set(needles).intersection(haystack))
```

There is an extra cost involved in building the sets, of course, but if either
the needles or the haystack is already a set, these alternatives may be cheaper
than the loop.  Any of them can search for 1,000 elements in a haystack of
10,000,000 items in a fraction of a millisecond, a fraction of a microsecond per
element.

Besides the extremely fast membership test (thanks to the underlying hash
table), the `set` and `frozenset` types provide a rich interface to create new
sets or, in the case of `set`, to change existing ones.  First, a note about
syntax.

### Set Literals

The syntax of set literals, `{1}`, `{1, 2}` and so on, looks exactly like the math
notation, with one important exception: there is no literal notation for the
empty `set`, so you must write `set()`.

> **Warning**
>
> Don't forget that to create an empty `set` you must use the constructor
> without an argument: `set()`.  If you write `{}`, you're creating an empty
> `dict`.

The standard string representation of sets always uses the `{...}` notation,
except for the empty set:

```python
s = {1}
type(s)
# <class 'set'>
s
# {1}
s.pop()
# 1
s
# set()
```

Literal set syntax like `{1, 2, 3}` is both faster and more readable than calling
the constructor (`set([1, 2, 3])`).  The latter is slower because Python has to
look up the `set` name to fetch the constructor, then build a list, and finally
pass it to the constructor, while a literal like `{1, 2, 3}` is handled by a
specialized `BUILD_SET` bytecode.  (Try `dis.dis('{1}')` and
`dis.dis('set([1])')` to compare.)

There is no special syntax for `frozenset` literals; they must be created by
calling the constructor.  Their standard representation looks like a
constructor call:

```python
frozenset(range(10))
# frozenset({0, 1, 2, 3, 4, 5, 6, 7, 8, 9})
```

### Set Comprehensions

Set comprehensions (*setcomps*) were added together with dictcomps.  Here is a
set of the Latin-1 characters that have the word "SIGN" in their Unicode names:

```python
from unicodedata import name
{chr(i) for i in range(32, 256) if 'SIGN' in name(chr(i),'')}
# {'§', '=', '¢', '#', '¤', '<', '¥', 'µ', '×', '$', '¶', '£', '©',
#  '°', '+', '÷', '±', '>', '¬', '®', '%'}
```

The [`unicodedata.name()`](https://docs.python.org/3/library/unicodedata.html#unicodedata.name)
function returns the name of a character.  The order of the output changes from
one Python process to the next, because of the salted hash mentioned in
[What Is Hashable](#what-is-hashable).

## Practical Consequences of How Sets Work

The `set` and `frozenset` types are both implemented with a hash table, which
has these effects:

* Set elements must be hashable objects, implementing proper `__hash__()` and
  `__eq__()` methods.
* Membership testing is very efficient.  A set may have millions of elements,
  but an element can be located directly by computing its hash code and deriving
  an index offset, with the possible overhead of a few tries to find a matching
  element or exhaust the search.
* Sets have a significant memory overhead compared to a low-level array of
  pointers to their elements, which would be more compact but also much slower
  to search beyond a handful of elements.
* Element ordering depends on insertion order, but not in a useful or reliable
  way.  If two elements are different but have the same hash code, their
  position depends on which one is added first.
* Adding elements to a set may change the order of existing elements.  The
  algorithm becomes less efficient if the hash table is more than two-thirds
  full, so Python may need to move and resize the table as it grows.  When that
  happens, elements are reinserted and their relative order may change.

### Set Operations

Many set methods are special methods that overload operators, such as `&` and
`>=`.  Some operators and methods change the target set in place (`&=`,
`difference_update()` and so on).  Such operations make no sense in the ideal
world of mathematical sets, and are not implemented in `frozenset`.

> **Tip**
>
> The infix operators require both operands to be sets, but all the other
> methods take one or more iterable arguments.  For example, to produce the union
> of four collections `a`, `b`, `c` and `d`, you can call `a.union(b, c, d)`, where
> `a` must be a set, but `b`, `c` and `d` can be iterables of any type that produce
> hashable items.  To create a new set with the union of four iterables, instead
> of updating an existing set, you can write `{*a, *b, *c, *d}`.

Mathematical set operations either produce a new set or update the target set in
place, if it is mutable:

| Math | Python operator | Method | Description |
|---|---|---|---|
| S ∩ Z | `s & z` | `s.__and__(z)` | intersection of `s` and `z` |
| | `z & s` | `s.__rand__(z)` | reversed `&` operator |
| | | `s.intersection(it, ...)` | intersection of `s` and all sets built from iterables `it`, etc. |
| | `s &= z` | `s.__iand__(z)` | `s` updated with the intersection of `s` and `z` |
| | | `s.intersection_update(it, ...)` | `s` updated with the intersection of `s` and all sets built from iterables `it`, etc. |
| S ∪ Z | `s \| z` | `s.__or__(z)` | union of `s` and `z` |
| | `z \| s` | `s.__ror__(z)` | reversed `\|` |
| | | `s.union(it, ...)` | union of `s` and all sets built from iterables `it`, etc. |
| | `s \|= z` | `s.__ior__(z)` | `s` updated with the union of `s` and `z` |
| | | `s.update(it, ...)` | `s` updated with the union of `s` and all sets built from iterables `it`, etc. |
| S \ Z | `s - z` | `s.__sub__(z)` | relative complement, or difference, between `s` and `z` |
| | `z - s` | `s.__rsub__(z)` | reversed `-` operator |
| | | `s.difference(it, ...)` | difference between `s` and all sets built from iterables `it`, etc. |
| | `s -= z` | `s.__isub__(z)` | `s` updated with the difference between `s` and `z` |
| | | `s.difference_update(it, ...)` | `s` updated with the difference between `s` and all sets built from iterables `it`, etc. |
| S ∆ Z | `s ^ z` | `s.__xor__(z)` | symmetric difference (the complement of the intersection `s & z`) |
| | `z ^ s` | `s.__rxor__(z)` | reversed `^` operator |
| | | `s.symmetric_difference(it)` | complement of `s & set(it)` |
| | `s ^= z` | `s.__ixor__(z)` | `s` updated with the symmetric difference of `s` and `z` |
| | | `s.symmetric_difference_update(it, ...)` | `s` updated with the symmetric difference of `s` and all sets built from iterables `it`, etc. |

These are the set predicates, operators and methods that return `True` or
`False`:

| Math | Python operator | Method | Description |
|---|---|---|---|
| S ∩ Z = ∅ | | `s.isdisjoint(z)` | `s` and `z` are disjoint (no elements in common) |
| e ∈ S | `e in s` | `s.__contains__(e)` | element `e` is a member of `s` |
| S ⊆ Z | `s <= z` | `s.__le__(z)` | `s` is a subset of the `z` set |
| | | `s.issubset(it)` | `s` is a subset of the set built from the iterable `it` |
| S ⊂ Z | `s < z` | `s.__lt__(z)` | `s` is a proper subset of the `z` set |
| S ⊇ Z | `s >= z` | `s.__ge__(z)` | `s` is a superset of the `z` set |
| | | `s.issuperset(it)` | `s` is a superset of the set built from the iterable `it` |
| S ⊃ Z | `s > z` | `s.__gt__(z)` | `s` is a proper superset of the `z` set |

In addition to the operators and methods derived from set theory, the set types
implement other methods of practical use:

| Method | `set` | `frozenset` | Description |
|---|:-:|:-:|---|
| `s.add(e)` | ● | | add element `e` to `s` |
| `s.clear()` | ● | | remove all elements of `s` |
| `s.copy()` | ● | ● | shallow copy of `s` |
| `s.discard(e)` | ● | | remove element `e` from `s` if it is present |
| `s.__iter__()` | ● | ● | get an iterator over `s` |
| `s.__len__()` | ● | ● | `len(s)` |
| `s.pop()` | ● | | remove and return an element from `s`, raising `KeyError` if `s` is empty |
| `s.remove(e)` | ● | | remove element `e` from `s`, raising `KeyError` if `e not in s` |

A few examples:

```python
a = {1, 2, 3, 4}
b = {3, 4, 5}
a & b, a | b, a - b, a ^ b
# ({3, 4}, {1, 2, 3, 4, 5}, {1, 2}, {1, 2, 5})
{3, 4} <= a, {3, 4} < a, a.isdisjoint({7, 8})
# (True, True, True)
a.union([10, 20], range(3))
# {0, 1, 2, 3, 4, 10, 20}
a |= b
a
# {1, 2, 3, 4, 5}
```

## Set Operations on `dict` Views

The view objects returned by `.keys()` and `.items()` are remarkably similar to
`frozenset`:

| Method | `frozenset` | `dict_keys` | `dict_items` | Description |
|---|:-:|:-:|:-:|---|
| `s.__and__(z)` | ● | ● | ● | `s & z` (intersection of `s` and `z`) |
| `s.__rand__(z)` | ● | ● | ● | reversed `&` operator |
| `s.__contains__()` | ● | ● | ● | `e in s` |
| `s.copy()` | ● | | | shallow copy of `s` |
| `s.difference(it, ...)` | ● | | | difference between `s` and iterables `it`, etc. |
| `s.intersection(it, ...)` | ● | | | intersection of `s` and iterables `it`, etc. |
| `s.isdisjoint(z)` | ● | ● | ● | `s` and `z` are disjoint (no elements in common) |
| `s.issubset(it)` | ● | | | `s` is a subset of iterable `it` |
| `s.issuperset(it)` | ● | | | `s` is a superset of iterable `it` |
| `s.__iter__()` | ● | ● | ● | get an iterator over `s` |
| `s.__len__()` | ● | ● | ● | `len(s)` |
| `s.__or__(z)` | ● | ● | ● | `s \| z` (union of `s` and `z`) |
| `s.__ror__()` | ● | ● | ● | reversed `\|` operator |
| `s.__reversed__()` | | ● | ● | get an iterator over `s` in reverse order |
| `s.__rsub__(z)` | ● | ● | ● | reversed `-` operator |
| `s.__sub__(z)` | ● | ● | ● | `s - z` (difference between `s` and `z`) |
| `s.symmetric_difference(it)` | ● | | | complement of `s & set(it)` |
| `s.union(it, ...)` | ● | | | union of `s` and iterables `it`, etc. |
| `s.__xor__()` | ● | ● | ● | `s ^ z` (symmetric difference of `s` and `z`) |
| `s.__rxor__()` | ● | ● | ● | reversed `^` operator |

In particular, `dict_keys` and `dict_items` implement the special methods that
support the powerful set operators `&` (intersection), `|` (union), `-`
(difference) and `^` (symmetric difference).  For example, with `&` it is easy to
get the keys that appear in two dictionaries:

```python
d1 = dict(a=1, b=2, c=3, d=4)
d2 = dict(b=20, d=40, e=50)
d1.keys() & d2.keys()
# {'b', 'd'}
```

Note that the result of `&` is a `set`.  Even better, the set operators of
dictionary views are compatible with `set` instances:

```python
s = {'a', 'e', 'i'}
d1.keys() & s
# {'a'}
d1.keys() | s
# {'a', 'c', 'b', 'd', 'i', 'e'}
```

> **Warning**
>
> A `dict_items` view only works as a set if all the values in the `dict` are
> hashable.  Attempting set operations on a `dict_items` view with an unhashable
> value raises `TypeError: unhashable type 'T'`, with `T` as the type of the
> offending value.  A `dict_keys` view, on the other hand, can always be used as a
> set, because every key is hashable by definition.

Using set operators with views will save you many loops and `if` statements when
inspecting the contents of dictionaries.  Let Python's efficient implementation
in C work for you!

## Summary

Dictionaries are a keystone of Python.  Over the years, the familiar
`{k1: v1, k2: v2}` literal syntax was enhanced to support unpacking with `**`,
pattern matching, and dict comprehensions.

Beyond the basic `dict`, the standard library offers handy, ready-to-use
specialized mappings like `defaultdict`, `ChainMap` and `Counter`, all defined in
the `collections` module.  With the new `dict` implementation, `OrderedDict` is not
as useful as before, but it remains for backward compatibility and has specific
characteristics that `dict` lacks, such as taking key order into account in `==`
comparisons.  Also in `collections` is `UserDict`, an easy-to-use base class for
custom mappings.

Two powerful methods available in most mappings are `setdefault` and `update`.
`setdefault` can update items holding mutable values, for example in a `dict` of
lists, without a second search for the same key.  `update` allows bulk insertion
or overwriting of items from any other mapping, from iterables of `(key, value)`
pairs, and from keyword arguments; mapping constructors use it internally.  You
can also use `|=` to update a mapping, and `|` to create a new one from the union
of two mappings.

A clever hook in the mapping interface is `__missing__()`, which lets you
customize what happens when a key is not found by `d[k]`.

The `collections.abc` module provides the `Mapping` and `MutableMapping` ABCs as
standard interfaces, useful for runtime type checking, and there are also ABCs
for `Set` and `MutableSet`.  `MappingProxyType` from the `types` module creates an
immutable façade for a mapping you want to protect from accidental change.

Dictionary views eliminated the memory overhead of methods that built lists
duplicating data in the target `dict`, and `dict_keys` and `dict_items` support the
most useful operators and methods of `frozenset`.

> **See also**
>
> * [collections — Container datatypes](https://docs.python.org/3/library/collections.html)
>   includes examples and practical recipes with several mapping types, and the
>   source code of `Lib/collections/__init__.py` is a great reference for anyone
>   who wants to create a new mapping type.
> * [**PEP 3106**](https://peps.python.org/pep-3106/) is where Guido van Rossum
>   introduced dictionary views for Python 3.
> * Raymond Hettinger's talk "Modern Dictionaries" (PyCon 2017) and Brandon
>   Rhodes's "The Dictionary Even Mightier" explain the compact, ordered dict
>   implementation; the CPython files `Objects/dictobject.c` and
>   `Objects/dictnotes.txt` have all the details.
> * [**PEP 218**](https://peps.python.org/pep-0218/) documents the rationale for
>   adding sets to Python.
