# The Python Data Model

One of Python's best qualities is its consistency.  Once you have worked with
the language for a while, you can start making informed, correct guesses about
features that are new to you.

If you learned another object-oriented language first, though, you may find it
odd to write `len(collection)` rather than `collection.len()`.  This apparent
oddity is the tip of an iceberg, and once you understand the iceberg you
understand much of what people mean by "Pythonic" code.  The iceberg is called
the *Python Data Model*, and it is the interface you use to make your own
objects work with the most idiomatic features of the language.

You can think of the data model as a description of Python as a framework.  It
formalizes the interfaces of the language's own building blocks: sequences,
functions, iterators, coroutines, classes, context managers, and so on.  When
you use a framework, you spend much of your time writing methods that the
framework calls.  The same thing happens when you build classes that take part
in the data model: the interpreter invokes *special methods* to carry out basic
operations on objects, usually in response to some piece of special syntax.

Special method names always begin and end with two underscores.  For example,
the syntax `obj[key]` is supported by the
[`__getitem__()`](https://docs.python.org/3/reference/datamodel.html#object.__getitem__)
special method.  To evaluate `my_collection[key]`, the interpreter calls
`my_collection.__getitem__(key)`.

You implement special methods when you want your objects to support and
interact with fundamental language constructs such as:

* collections;
* attribute access;
* iteration, including asynchronous iteration with `async for`;
* operator overloading;
* function and method invocation;
* string representation and formatting;
* asynchronous programming with `await`;
* object creation and destruction;
* managed contexts with the `with` and `async with` statements.

> **Note**
>
> Special methods are often called *magic methods*, but there is nothing magical
> about them: they are fully documented, and they let ordinary programmers
> emulate the behavior of the built-in types.  Pythonistas usually pronounce a
> name like `__getitem__` as "dunder-getitem"; "dunder" is short for "double
> underscore before and after", which is why special methods are also known as
> *dunder methods*.  The "Lexical Analysis" chapter of the language reference
> warns that any use of `__*__` names that does not follow explicitly
> documented use is subject to breakage without warning, so don't invent dunder
> names of your own.

## A Pythonic Card Deck

The following class is simple, but it shows how much you gain by implementing
just two special methods, `__getitem__()` and `__len__()`:

```python
import collections

Card = collections.namedtuple('Card', ['rank', 'suit'])

class FrenchDeck:
    ranks = [str(n) for n in range(2, 11)] + list('JQKA')
    suits = 'spades diamonds clubs hearts'.split()

    def __init__(self):
        self._cards = [Card(rank, suit) for suit in self.suits
                                        for rank in self.ranks]

    def __len__(self):
        return len(self._cards)

    def __getitem__(self, position):
        return self._cards[position]
```

The first thing to notice is the use of
[`collections.namedtuple()`](https://docs.python.org/3/library/collections.html#collections.namedtuple)
to build a simple class representing individual cards.  `namedtuple` makes
classes whose instances are just bundles of fields with no custom methods, like
a database record.  Here it gives the cards a readable representation:

```python
beer_card = Card('7', 'diamonds')
beer_card
# Card(rank='7', suit='diamonds')
```

The real point of the example, however, is the `FrenchDeck` class.  It is
short, but it packs a punch.  To begin with, like any standard Python
collection, a deck responds to the `len()` function by returning the number of
cards in it:

```python
deck = FrenchDeck()
len(deck)
# 52
```

Reading specific cards from the deck, say the first or the last, is easy thanks
to the `__getitem__()` method:

```python
deck[0]
# Card(rank='2', suit='spades')
deck[-1]
# Card(rank='A', suit='hearts')
```

Should we write a method to pick a random card?  There is no need: the
standard library already has a function that returns a random item from a
sequence, [`random.choice()`](https://docs.python.org/3/library/random.html#random.choice),
and it works on a deck just as it works on a list:

```python
from random import choice
choice(deck)
# Card(rank='3', suit='hearts')
choice(deck)
# Card(rank='K', suit='spades')
```

(Your cards will differ, of course.)  We have just seen two advantages of using
special methods to take part in the data model:

* Users of your classes don't have to memorize arbitrary method names for
  standard operations.  ("How do I get the number of items?  Is it `.size()`,
  `.length()`, or something else?")
* It is easier to benefit from the rich standard library and avoid reinventing
  the wheel, as with `random.choice()`.

But it gets better.  Because our `__getitem__()` delegates to the `[]`
operator of the `self._cards` list, the deck automatically supports slicing.
Here is how to look at the top three cards of a brand-new deck, and then pick
just the aces by starting at index 12 and skipping 13 cards at a time:

```python
deck[:3]
# [Card(rank='2', suit='spades'), Card(rank='3', suit='spades'),
#  Card(rank='4', suit='spades')]
deck[12::13]
# [Card(rank='A', suit='spades'), Card(rank='A', suit='diamonds'),
#  Card(rank='A', suit='clubs'), Card(rank='A', suit='hearts')]
```

Just by implementing `__getitem__()`, the deck is also iterable, forwards and
backwards:

```python
for card in deck:
    print(card)
# Card(rank='2', suit='spades')
# Card(rank='3', suit='spades')
# Card(rank='4', suit='spades')
# ...

for card in reversed(deck):
    print(card)
# Card(rank='A', suit='hearts')
# Card(rank='K', suit='hearts')
# Card(rank='Q', suit='hearts')
# ...
```

Iteration is often implicit.  If a collection has no `__contains__()` method,
the `in` operator falls back to a sequential scan, so `in` works with our
deck because the deck is iterable:

```python
Card('Q', 'hearts') in deck
# True
Card('7', 'beasts') in deck
# False
```

How about sorting?  A common way of ranking cards is by rank, with aces
highest, and then by suit in the order spades (highest), hearts, diamonds and
clubs (lowest).  Here is a function that ranks cards by that rule, returning
`0` for the 2 of clubs and `51` for the ace of spades:

```python
suit_values = dict(spades=3, hearts=2, diamonds=1, clubs=0)

def spades_high(card):
    rank_value = FrenchDeck.ranks.index(card.rank)
    return rank_value * len(suit_values) + suit_values[card.suit]
```

Given `spades_high`, we can list the deck in order of increasing rank:

```python
for card in sorted(deck, key=spades_high):
    print(card)
# Card(rank='2', suit='clubs')
# Card(rank='2', suit='diamonds')
# Card(rank='2', suit='hearts')
# ... (46 cards omitted)
# Card(rank='A', suit='diamonds')
# Card(rank='A', suit='hearts')
# Card(rank='A', suit='spades')
```

Although `FrenchDeck` implicitly inherits from `object`, most of its behavior
is not inherited at all.  It comes from taking part in the data model and from
*composition*: by implementing `__len__()` and `__getitem__()`, `FrenchDeck`
behaves like a standard Python sequence and benefits from core language
features (iteration, slicing) and from the standard library (`random.choice()`,
`reversed()`, `sorted()`).  Thanks to composition, both methods simply delegate
their work to a list object, `self._cards`.

> **Note**
>
> As written, a `FrenchDeck` cannot be shuffled, because it is immutable: the
> cards and their positions cannot change unless you break encapsulation and
> handle the `_cards` attribute directly.  In
> [Interfaces, Protocols, and ABCs](protocols-abcs.md) we fix that by adding a
> one-line `__setitem__()` method.

## How Special Methods Are Used

The first thing to know about special methods is that they are meant to be
called by the Python interpreter, not by you.  You don't write
`my_object.__len__()`.  You write `len(my_object)` and, if `my_object` is an
instance of a class you defined, Python calls the `__len__()` method you
implemented.

The interpreter takes a shortcut, however, for built-in types such as `list`,
`str` and `bytearray`, and for extensions like NumPy arrays.  Variable-sized
collections written in C include a struct called `PyVarObject` with an
`ob_size` field holding the number of items.  If `my_object` is one of those
built-ins, `len(my_object)` just reads that field, which is much faster than
calling a method.

More often than not, the special method call is implicit.  For example, the
statement `for i in x:` actually calls `iter(x)`, which in turn may call
`x.__iter__()` if it exists, or fall back on `x.__getitem__()`, as in the
`FrenchDeck` example.

Normally your code should not contain many direct calls to special methods.
Unless you are doing a lot of metaprogramming, you should be *implementing*
special methods far more often than *invoking* them.  The only special method
that user code commonly calls directly is `__init__()`, to invoke the
initializer of a superclass from your own `__init__()`.

If you do need the effect of a special method, it is usually better to call the
related built-in function (`len()`, `iter()`, `str()`, and so on).  These
built-ins call the corresponding special method, but they often provide extra
services and, for built-in types, they are faster than method calls.  You will
see an example in [Using `iter()` with a callable](iterators-generators.md#using-iter-with-a-callable).

In the next sections we look at some of the most important uses of special
methods: emulating numeric types, representing objects as strings, giving
objects a Boolean value, and implementing collections.

<a id="dm-vector"></a>

### Emulating Numeric Types

Several special methods let your objects respond to operators such as `+`.
[Operator Overloading](operator-overloading.md) covers this in detail; here the
goal is just to show special methods at work in another simple example.

We will write a class to represent two-dimensional Euclidean vectors, like
those used in math and physics.  (The built-in `complex` type can represent
two-dimensional vectors, but our class can grow into an *n*-dimensional one,
and in [Special Methods for Sequences](sequence-protocol.md) it will.)

It helps to start designing a class's interface by writing down how you want
to use it.  Vector addition should produce a new `Vector`, displayed in a
friendly way:

<!-- nocheck -->
```python
v1 = Vector(2, 4)
v2 = Vector(2, 1)
v1 + v2
# Vector(4, 5)
```

The built-in `abs()` function returns the absolute value of integers and
floats and the magnitude of complex numbers, so to be consistent our class
should also use `abs()` for the magnitude of a vector:

<!-- nocheck -->
```python
v = Vector(3, 4)
abs(v)
# 5.0
```

We can also implement the `*` operator to perform scalar multiplication, that
is, multiplying a vector by a number to get a new vector with the same
direction and a scaled magnitude:

<!-- nocheck -->
```python
v * 3
# Vector(9, 12)
abs(v * 3)
# 15.0
```

Here is a `Vector` class that implements these operations through the special
methods `__repr__()`, `__abs__()`, `__add__()` and `__mul__()`, plus
`__bool__()`, which we'll discuss in a moment:

```python
import math

class Vector:

    def __init__(self, x=0, y=0):
        self.x = x
        self.y = y

    def __repr__(self):
        return f'Vector({self.x!r}, {self.y!r})'

    def __abs__(self):
        return math.hypot(self.x, self.y)

    def __bool__(self):
        return bool(abs(self))

    def __add__(self, other):
        x = self.x + other.x
        y = self.y + other.y
        return Vector(x, y)

    def __mul__(self, scalar):
        return Vector(self.x * scalar, self.y * scalar)
```

The class implements five special methods besides the familiar `__init__()`,
yet none of them is called directly, either inside the class or in the usage
examples above.  As mentioned before, the interpreter is the only frequent
caller of most special methods.

Notice that `__add__()` and `__mul__()` both build and return a new `Vector`
and leave their operands alone: `self` and `other` are only read.  That is the
expected behavior of infix operators: create new objects and don't touch the
operands.

> **Note**
>
> As written, this class lets you multiply a `Vector` by a number, but not a
> number by a `Vector`, which breaks the commutative property of scalar
> multiplication.  The special method `__rmul__()`, explained in
> [Operator Overloading](operator-overloading.md), fixes that.

### String Representation

The `__repr__()` special method is called by the
[`repr()`](https://docs.python.org/3/library/functions.html#repr) built-in to get
the string representation of an object for inspection.  Without a custom
`__repr__()`, the interactive interpreter would display a `Vector` as something
like `<Vector object at 0x10e100070>`.

The interactive interpreter and the debugger call `repr()` on the results of
the expressions they evaluate, and so do the `%r` placeholder of `%`
formatting and the `!r` conversion field of f-strings and `str.format()`.

The f-string in our `__repr__()` uses `!r` to get the standard representation
of each attribute.  That is good practice, because it shows the crucial
difference between `Vector(1, 2)` and `Vector('1', '2')`.  The second would not
work in this example, since the constructor's arguments should be numbers, not
strings.

The string returned by `__repr__()` should be unambiguous and, when possible,
match the source code needed to re-create the object.  That is why our
representation looks like a call to the class constructor, `Vector(3, 4)`.

By contrast, `__str__()` is called by the
[`str()`](https://docs.python.org/3/library/stdtypes.html#str) built-in and used
implicitly by `print()`.  It should return a string suitable for display to end
users.  Often the string returned by `__repr__()` is friendly enough, and you
don't need `__str__()` at all: the implementation inherited from `object` falls
back on `__repr__()`.

> **Tip**
>
> Programmers coming from languages with a `toString` method tend to implement
> `__str__()` and not `__repr__()`.  If you implement only one of these special
> methods in Python, choose `__repr__()`.

### Boolean Value of a Custom Type

Although Python has a `bool` type, it accepts any object in a Boolean context:
the expression controlling an `if` or `while` statement, or the operands of
`and`, `or` and `not`.  To decide whether a value `x` is *truthy* or *falsy*,
Python applies `bool(x)`, which returns either `True` or `False`.

By default, instances of user-defined classes are truthy, unless the class
implements `__bool__()` or `__len__()`.  Basically, `bool(x)` calls
`x.__bool__()` and uses the result.  If `__bool__()` is not implemented, Python
tries `x.__len__()`, and if that returns zero, `bool()` returns `False`;
otherwise it returns `True`.

Our `__bool__()` is conceptually simple: it returns `False` if the magnitude of
the vector is zero and `True` otherwise.  It converts the magnitude with
`bool(abs(self))` because `__bool__()` must return an actual Boolean.  Outside
`__bool__()` methods, you rarely need to call `bool()` explicitly, because any
object can be used in a Boolean context.

A faster implementation of `Vector.__bool__()` is this:

```python
def __bool__(self):
    return bool(self.x or self.y)
```

It is harder to read, but it avoids the trip through `abs()`, `__abs__()`, the
squares and the square root.  The explicit conversion is still needed, because
`or` returns one of its operands as is: `x or y` evaluates to `x` if `x` is
truthy, and to `y`, whatever it is, otherwise.

### Collection API

All of Python's essential collection types are described by abstract base
classes (ABCs) in the [`collections.abc`](https://docs.python.org/3/library/collections.abc.html)
module.  ABCs are covered in [Interfaces, Protocols, and ABCs](protocols-abcs.md);
here the goal is just a panoramic view of how the main collection interfaces
are built out of special methods.

At the top of the hierarchy sit three ABCs, each with a single special method.
The `Collection` ABC (new in Python 3.6) unifies them, because every collection
should support all three:

* `Iterable`, with `__iter__()`, supports `for`, unpacking, and other forms of
  iteration;
* `Sized`, with `__len__()`, supports the `len()` built-in;
* `Container`, with `__contains__()`, supports the `in` operator.

Python does not require concrete classes to inherit from any of these ABCs.
Any class that implements `__len__()` satisfies the `Sized` interface.

Three very important specializations of `Collection` are:

* `Sequence`, formalizing the interface of built-ins like `list` and `str`;
* `Mapping`, implemented by `dict`, `collections.defaultdict`, and others;
* `Set`, the interface of the `set` and `frozenset` built-in types.

Only `Sequence` is also `Reversible`, because sequences allow arbitrary
ordering of their contents, while mappings and sets do not.  (Since Python 3.7
`dict` is officially "ordered", but that only means that key insertion order is
preserved; you cannot rearrange the keys however you like.)  Each of these has
a mutable counterpart, `MutableSequence`, `MutableMapping` and `MutableSet`,
which adds methods such as `__setitem__()`, `__delitem__()`, `append()`,
`pop()` and `add()`.

All the special methods in the `Set` ABC implement infix operators.  For
example, `a & b` computes the intersection of the sets `a` and `b`, and is
implemented by `__and__()`.

[An Array of Sequences](sequences.md) and [Dictionaries and Sets](dicts-sets.md)
cover the standard library's sequences, mappings and sets in detail.

## Overview of Special Methods

The [Data Model](https://docs.python.org/3/reference/datamodel.html) chapter of
the language reference lists more than 80 special method names.  More than
half of them implement arithmetic, bitwise and comparison operators.  The
following tables give an overview of what is available.

The first table lists special methods other than those used for operators and
core math functions like `abs()`.  Most of them are covered somewhere in this
book, including recent additions such as the asynchronous special methods
(`__anext__()` and friends, added in Python 3.5) and the class customization
hook `__init_subclass__()` (Python 3.6).

| Category | Method names |
|---|---|
| String/bytes representation | `__repr__` `__str__` `__format__` `__bytes__` `__fspath__` |
| Conversion to number | `__bool__` `__complex__` `__int__` `__float__` `__hash__` `__index__` |
| Emulating collections | `__len__` `__getitem__` `__setitem__` `__delitem__` `__contains__` |
| Iteration | `__iter__` `__aiter__` `__next__` `__anext__` `__reversed__` |
| Callable or coroutine execution | `__call__` `__await__` |
| Context management | `__enter__` `__exit__` `__aenter__` `__aexit__` |
| Instance creation and destruction | `__new__` `__init__` `__del__` |
| Attribute management | `__getattr__` `__getattribute__` `__setattr__` `__delattr__` `__dir__` |
| Attribute descriptors | `__get__` `__set__` `__delete__` `__set_name__` |
| Abstract base classes | `__instancecheck__` `__subclasscheck__` |
| Class metaprogramming | `__prepare__` `__init_subclass__` `__class_getitem__` `__mro_entries__` |

Infix and numeric operators are supported by the special methods in the next
table.  The most recent names are `__matmul__()`, `__rmatmul__()` and
`__imatmul__()`, added in Python 3.5 to support `@` as an infix operator for
matrix multiplication.

| Operator category | Symbols | Method names |
|---|---|---|
| Unary numeric | `-` `+` `abs()` | `__neg__` `__pos__` `__abs__` |
| Rich comparison | `<` `<=` `==` `!=` `>` `>=` | `__lt__` `__le__` `__eq__` `__ne__` `__gt__` `__ge__` |
| Arithmetic | `+` `-` `*` `/` `//` `%` `@` `divmod()` `round()` `**` `pow()` | `__add__` `__sub__` `__mul__` `__truediv__` `__floordiv__` `__mod__` `__matmul__` `__divmod__` `__round__` `__pow__` |
| Reversed arithmetic | (arithmetic operators with swapped operands) | `__radd__` `__rsub__` `__rmul__` `__rtruediv__` `__rfloordiv__` `__rmod__` `__rmatmul__` `__rdivmod__` `__rpow__` |
| Augmented assignment arithmetic | `+=` `-=` `*=` `/=` `//=` `%=` `@=` `**=` | `__iadd__` `__isub__` `__imul__` `__itruediv__` `__ifloordiv__` `__imod__` `__imatmul__` `__ipow__` |
| Bitwise | `&` `\|` `^` `<<` `>>` `~` | `__and__` `__or__` `__xor__` `__lshift__` `__rshift__` `__invert__` |
| Reversed bitwise | (bitwise operators with swapped operands) | `__rand__` `__ror__` `__rxor__` `__rlshift__` `__rrshift__` |
| Augmented assignment bitwise | `&=` `\|=` `^=` `<<=` `>>=` | `__iand__` `__ior__` `__ixor__` `__ilshift__` `__irshift__` |

Python calls a *reversed* operator method on the second operand when the
corresponding method on the first operand cannot be used.  *Augmented
assignments* are shortcuts that combine an infix operator with variable
assignment, as in `a += b`.  Both are explained in detail in
[Operator Overloading](operator-overloading.md).

## Why `len` Is Not a Method

The short answer comes from the Zen of Python: "practicality beats purity."
As described above, `len(x)` runs very fast when `x` is an instance of a
built-in type: for the built-in objects of CPython no method is called at all,
and the length is simply read from a field of a C struct.  Getting the number of
items in a collection is a very common operation, and it must be efficient for
basic and diverse types such as `str`, `list` and `memoryview`.

In other words, `len` is not called as a method because it gets special
treatment as part of the data model, just like `abs`.  But thanks to the
special method `__len__()`, you can also make `len()` work with your own
objects.  That is a fair compromise between the need for efficient built-in
objects and the consistency of the language.  Again from the Zen of Python:
"Special cases aren't special enough to break the rules."

> **Note**
>
> If you think of `abs` and `len` as unary operators, you may be more inclined
> to forgive their functional look, as opposed to the method-call syntax you
> might expect in an object-oriented language.  In fact, ABC, a direct ancestor
> of Python that pioneered many of its features, had a `#` operator equivalent
> to `len` (you wrote `#s`).  Used as an infix operator, `x#s` counted the
> occurrences of `x` in `s`, which in Python you get as `s.count(x)`.

## Summary

By implementing special methods, your objects can behave like the built-in
types, which enables the expressive coding style the community considers
Pythonic.

A basic requirement for a Python object is to provide usable string
representations of itself: one for debugging and logging, another for
presentation to end users.  That is why `__repr__()` and `__str__()` both exist.

Emulating sequences, as `FrenchDeck` does, is one of the most common uses of
special methods; database libraries, for example, often return query results
wrapped in sequence-like collections.  Making the most of the existing sequence
types is the subject of [An Array of Sequences](sequences.md), and implementing
your own sequences is covered in [Special Methods for Sequences](sequence-protocol.md).

Thanks to operator overloading, Python offers a rich selection of numeric
types, from the built-ins to [`decimal.Decimal`](https://docs.python.org/3/library/decimal.html)
and [`fractions.Fraction`](https://docs.python.org/3/library/fractions.html), all
supporting the infix arithmetic operators, and libraries like NumPy support
infix operators on matrices and tensors.  Implementing operators, including
reversed operators and augmented assignment, is shown in
[Operator Overloading](operator-overloading.md).

> **See also**
>
> * The [Data Model](https://docs.python.org/3/reference/datamodel.html) chapter of
>   *The Python Language Reference* is the canonical source for this chapter
>   and for much of what follows.
> * What the Python documentation calls the "data model", most authors would
>   call the *object model*: the properties of objects in general in a specific
>   programming language.  A more academic name is *metaobject protocol*, an
>   interface for the core constructs of a language, a term made popular by
>   *The Art of the Metaobject Protocol* by Kiczales, des Rivières and Bobrow.
>   A rich metaobject protocol is what lets you extend a language with new
>   programming paradigms from inside the language itself.
