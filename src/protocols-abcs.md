# Interfaces, Protocols, and ABCs

> Program to an interface, not an implementation.
>
> — Gamma, Helm, Johnson, Vlissides, *Design Patterns*

Object-oriented programming is all about interfaces.  The best approach to
understanding a type in Python is knowing the methods it provides — its interface —
as discussed in [Types Are Defined by Supported Operations](type-hints-functions.md#types-are-defined-by-supported-operations).

Depending on the programming language, there are one or more ways of defining and
using interfaces.  Python has four of them, and they complement each other:

**Duck typing**
: Python's default approach to typing from the beginning.  An object is acceptable if
  it supports the operations you need, whatever its class.  We've been relying on it
  since [The Python Data Model](data-model.md).

**Goose typing**
: The approach supported by abstract base classes (ABCs), which relies on runtime
  checks of objects against ABCs with `isinstance()` and `issubclass()`.  Goose typing
  is a major subject of this chapter.

**Static typing**
: The traditional approach of statically typed languages like C and Java, supported
  by the [`typing`](https://docs.python.org/3/library/typing.html) module and enforced
  by external type checkers such as Mypy or Pyright.  Most of
  [Type Hints in Functions](type-hints-functions.md) and
  [More About Type Hints](type-hints-more.md) is about static typing.

**Static duck typing**
: An approach made popular by the Go language, supported by subclasses of
  `typing.Protocol` and also enforced by external type checkers.

You can picture these four approaches as the quadrants of a "typing map".  The top half
holds the approaches checked at runtime by the interpreter alone (duck typing and
goose typing); the bottom half holds those that need an external static checker
(static duck typing and static typing).  The left half is *structural* — it looks at
which methods an object provides, regardless of the name of its class — while the
right half is *nominal*, depending on objects having explicitly named types or
superclasses.  It doesn't make sense to dismiss any of the four; each has different
pros and cons.

This chapter covers three of the four quadrants: the two kinds of protocols (the
structural half), how to make duck typing safer, goose typing with ABCs, and the design
of static protocols.

## Two Kinds of Protocols

The word *protocol* has different meanings in computer science depending on context.
A network protocol such as HTTP specifies commands that a client can send to a server,
such as `GET`, `PUT` and `HEAD`.  An *object protocol* specifies methods that an object
must provide to fulfill a role.  The `FrenchDeck` example in
[The Python Data Model](data-model.md) demonstrated one object protocol, the sequence
protocol: the methods that allow a Python object to behave as a sequence.

Implementing a full protocol may require several methods, but often it is OK to
implement only part of it.  Consider this `Vowels` class:

```python
class Vowels:
    def __getitem__(self, i):
        return 'AEIOU'[i]

v = Vowels()
v[0]
# 'A'
v[-1]
# 'U'
for c in v:
    print(c)

# A
# E
# I
# O
# U
'E' in v
# True
'Z' in v
# False
```

Implementing `__getitem__()` is enough to allow retrieving items by index, and also to
support iteration and the `in` operator.  The `__getitem__()` special method is really
the key to the sequence protocol.  The Python/C API Reference Manual says that
`PySequence_Check()` returns 1 for Python classes with a `__getitem__()` method unless
they are `dict` subclasses.

We expect a sequence to also support `len()`, by implementing `__len__()`.  `Vowels`
has no `__len__()` method, but it still behaves as a sequence in some contexts, and that
may be enough for our purposes.  That is why a protocol is often described as an
"informal interface".  That is also how protocols are understood in Smalltalk, the first
object-oriented programming environment to use that term.  Except in pages about
network programming, most uses of the word "protocol" in the Python documentation refer
to these informal interfaces.

Since [**PEP 544**](https://peps.python.org/pep-0544/) (Python 3.8), the word
"protocol" has a second, closely related meaning in Python.  As we saw in
[Static Protocols](type-hints-functions.md#static-protocols), PEP 544 lets us create
subclasses of `typing.Protocol` to define one or more methods that a class must
implement (or inherit) to satisfy a static type checker.  When we need to be specific,
we'll use these terms:

**Dynamic protocol**
: The informal protocols Python always had.  Dynamic protocols are implicit, defined by
  convention, and described in the documentation.  Python's most important dynamic
  protocols are supported by the interpreter itself, and are documented in the
  [Data model](https://docs.python.org/3/reference/datamodel.html) chapter of the
  Language Reference.

**Static protocol**
: A protocol as defined by PEP 544.  A static protocol has an explicit definition: a
  `typing.Protocol` subclass.

There are two key differences between them:

* An object may implement only part of a dynamic protocol and still be useful; but to
  fulfill a static protocol, the object must provide every method declared in the
  protocol class, even if your program doesn't need them all.
* Static protocols can be verified by static type checkers, but dynamic protocols
  can't.

Both kinds of protocols share the essential characteristic that a class never needs to
declare that it supports a protocol by name, i.e., by inheritance.  In addition to
static protocols, Python provides another way of defining an explicit interface in
code: an abstract base class.  The rest of this chapter covers dynamic and static
protocols, as well as ABCs.

## Programming Ducks

Let's start our discussion of dynamic protocols with two of the most important in
Python: the sequence and iterable protocols.  The interpreter goes out of its way to
handle objects that provide even a minimal implementation of those protocols.

### Python Digs Sequences

The philosophy of the Python Data Model is to cooperate with essential dynamic
protocols as much as possible.  When it comes to sequences, Python tries hard to work
with even the simplest implementations.

The `Sequence` interface is formalized as an ABC in
[`collections.abc`](https://docs.python.org/3/library/collections.abc.html):
`Sequence` inherits from `Reversible` and `Collection`, and `Collection` in turn
inherits from `Sized`, `Iterable` and `Container`.  A correct subclass of `Sequence`
must implement `__getitem__()` and `__len__()` (from `Sized`); all the other methods —
`__contains__()`, `__iter__()`, `__reversed__()`, `index()` and `count()` — are
concrete, so subclasses can inherit their implementations, or provide better ones.

But the interpreter and built-in sequences like `list` and `str` do not rely on that
ABC at all.  It's only a description of what a full-fledged sequence is expected to
support.

> **Tip**
>
> Most ABCs in the `collections.abc` module exist to formalize interfaces that are
> implemented by built-in objects and are implicitly supported by the interpreter —
> both of which predate the ABCs themselves.  The ABCs are useful as starting points for
> new classes, and to support explicit type checking at runtime (goose typing) as well
> as type hints for static type checkers.

Now, recall the `Vowels` class.  It does not inherit from `abc.Sequence` and it only
implements `__getitem__()`.  There is no `__iter__()` method, yet `Vowels` instances are
iterable because — as a fallback — if Python finds a `__getitem__()` method, it tries to
iterate over the object by calling that method with integer indexes starting with 0.
Because Python is smart enough to iterate over `Vowels` instances, it can also make the
`in` operator work even when the `__contains__()` method is missing: it does a
sequential scan to check if an item is present.

In summary, given the importance of sequence-like data structures, Python manages to
make iteration and the `in` operator work by invoking `__getitem__()` when `__iter__()`
and `__contains__()` are unavailable.

The original `FrenchDeck` does not subclass `abc.Sequence` either, but it does
implement both methods of the sequence protocol:

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

Many of the things you can do with a `FrenchDeck` work because of the special treatment
Python gives to anything vaguely resembling a sequence.  The iterable protocol in
Python represents an extreme form of duck typing: the interpreter tries two different
methods to iterate over objects.

To be clear, these behaviors are implemented in the interpreter itself, mostly in C.
They do not depend on methods from the `Sequence` ABC.  For example, the concrete
methods `__iter__()` and `__contains__()` in the `Sequence` class emulate the built-in
behaviors of the interpreter.  If you are curious, read their source code in
[`Lib/_collections_abc.py`](https://github.com/python/cpython/blob/main/Lib/_collections_abc.py).

Now let's study another example emphasizing the dynamic nature of protocols — and why
static type checkers have no chance of dealing with them.

### Monkey Patching: Implementing a Protocol at Runtime

*Monkey patching* is dynamically changing a module, class or function at runtime, to
add features or fix bugs.  For example, the gevent networking library monkey patches
parts of Python's standard library to allow lightweight concurrency without threads or
`async`/`await`.

The `FrenchDeck` class is missing an essential feature: it cannot be shuffled.  It
doesn't need its own `shuffle` method, because there is already
[`random.shuffle()`](https://docs.python.org/3/library/random.html#random.shuffle),
documented as "Shuffle the sequence *x* in place":

```python
from random import shuffle
l = list(range(10))
shuffle(l)
l
# [5, 2, 9, 7, 8, 3, 1, 4, 0, 6]
```

> **Tip**
>
> When you follow established protocols, you improve your chances of leveraging
> existing standard library and third-party code, thanks to duck typing.

However, if we try to shuffle a `FrenchDeck` instance, we get an exception:

```python
deck = FrenchDeck()
shuffle(deck)
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
#   File ".../random.py", line 361, in shuffle
#     x[i], x[j] = x[j], x[i]
#     ~^^^
# TypeError: 'FrenchDeck' object does not support item assignment
```

The error message is clear: `'FrenchDeck' object does not support item assignment`.
The problem is that `shuffle` operates *in place*, by swapping items inside the
collection, and `FrenchDeck` only implements the *immutable* sequence protocol.
Mutable sequences must also provide a `__setitem__()` method.

Because Python is dynamic, we can fix this at runtime, even at the interactive
console:

```python
def set_card(deck, position, card):
    deck._cards[position] = card

FrenchDeck.__setitem__ = set_card
shuffle(deck)
deck[:5]
# [Card(rank='3', suit='hearts'), Card(rank='4', suit='diamonds'), Card(rank='4',
# suit='clubs'), Card(rank='7', suit='hearts'), Card(rank='9', suit='spades')]
```

We create a function that takes `deck`, `position` and `card` as arguments, and assign
that function to an attribute named `__setitem__` in the `FrenchDeck` class.  Now
`deck` can be shuffled, because we added the necessary method of the mutable sequence
protocol.

The signature of the `__setitem__()` special method is defined in the Language
Reference in [Emulating container types](https://docs.python.org/3/reference/datamodel.html#emulating-container-types).
Here the arguments are named `deck, position, card` — and not `self, key, value` as in
the Language Reference — to show that every Python method starts life as a plain
function, and naming the first argument `self` is merely a convention (see
[Method Objects](classes.md#tut-methodobjects)).  This is OK in a console session, but in
a Python source file it's much better to use `self`, `key` and `value` as documented.

The trick is that `set_card` knows that the `deck` object has an attribute named
`_cards`, and `_cards` must be a mutable sequence.  The `set_card` function is then
attached to the `FrenchDeck` class as the `__setitem__()` special method.  This is an
example of monkey patching: changing a class or module at runtime, without touching the
source code.  Monkey patching is powerful, but the code that does the actual patching is
very tightly coupled with the program to be patched, often handling private and
undocumented attributes.

Besides being an example of monkey patching, this highlights the dynamic nature of
protocols in dynamic duck typing: `random.shuffle` doesn't care about the class of the
argument, it only needs the object to implement methods from the mutable sequence
protocol.  It doesn't even matter if the object was "born" with the necessary methods
or if they were somehow acquired later.

> **Note**
>
> Monkey patching has a bad reputation.  If abused, it leads to systems that are hard to
> understand and maintain, and two libraries that patch the same target may step on each
> other's toes.  Unlike Ruby and JavaScript, Python does not let you monkey patch the
> built-in types: you can be certain that a `str` object will always have the same
> methods.  That limitation is an advantage.  The Adapter design pattern solves the same
> problem as our patch by implementing a whole new class.

Duck typing doesn't need to be wildly unsafe or hard to debug.  The next section shows
some useful code patterns to detect dynamic protocols without resorting to explicit
checks.

### Defensive Programming and "Fail Fast"

Defensive programming is like defensive driving: a set of practices to enhance safety
even when faced with careless programmers — or drivers.

Many bugs cannot be caught except at runtime, even in mainstream statically typed
languages (that's why automated testing is necessary).  In a dynamically typed language,
"fail fast" is excellent advice for safer and easier-to-maintain programs.  Failing fast
means raising runtime errors as soon as possible, for example, rejecting invalid
arguments right at the beginning of a function body.

Here is one example: when you write code that accepts a sequence of items to process
internally as a `list`, don't enforce a `list` argument by type checking.  Instead, take
the argument and immediately build a `list` from it.  The `LottoBlower` class later in
this chapter does exactly that:

<!-- nocheck -->
```python
def __init__(self, iterable):
    self._balls = list(iterable)
```

That way you make your code more flexible, because the `list()` constructor handles any
iterable that fits in memory.  If the argument is not iterable, the call will fail fast
with a very clear `TypeError` exception, right when the object is initialized.  If you
want to be more explicit, you can wrap the `list()` call with `try`/`except` to
customize the error message — but use that extra code only on an external API, because
the problem would be easy to see for maintainers of the codebase.  Either way, the
offending call will appear near the end of the traceback, making it straightforward to
fix.  If you don't catch the invalid argument in the class constructor, the program will
blow up later, when some other method of the class needs to operate on `self._balls` and
it is not a `list`.  Then the root cause will be harder to find.

Of course, calling `list()` on the argument would be bad if the data shouldn't be
copied, either because it's too large or because the function, by design, needs to
change it in place for the benefit of the caller, like `random.shuffle` does.  In that
case, a runtime check like `isinstance(x, abc.MutableSequence)` would be the way to go.

If you are afraid of getting an infinite generator — not a common issue — you can begin
by calling `len()` on the argument.  This would reject iterators, while safely dealing
with tuples, arrays and other existing or future classes that fully implement the
`Sequence` interface.  Calling `len()` is usually very cheap, and an invalid argument
will raise an error immediately.

On the other hand, if any iterable is acceptable, then call `iter(x)` as soon as
possible to obtain an iterator, as we'll see in
[Iterators, Generators, and Classic Coroutines](iterators-generators.md).  Again, if `x`
is not iterable, this will fail fast with an easy-to-debug exception.

In the cases just described, a type hint could catch some problems earlier, but not all
problems.  Recall that the type `Any` is consistent-with every other type, and type
inference may cause a variable to be tagged with `Any`.  When that happens, the type
checker is in the dark.  In addition, type hints are not enforced at runtime.  Fail fast
is the last line of defense.

Defensive code leveraging duck types can also include logic to handle different types
without using `isinstance()` or `hasattr()` tests.  One example is how we might emulate
the handling of the `field_names` argument in `collections.namedtuple`: `field_names`
accepts a single string with identifiers separated by spaces or commas, or a sequence of
identifiers.  Here is how to do it with duck typing:

```python
def parse_field_names(field_names):
    try:
        field_names = field_names.replace(',', ' ').split()  # assume it's a string (EAFP)
    except AttributeError:  # sorry, field_names doesn't quack like a str
        pass  # assume it's already an iterable of names
    field_names = tuple(field_names)  # make our own copy, and make sure it's iterable
    if not all(s.isidentifier() for s in field_names):
        raise ValueError('field_names must all be valid identifiers')
    return field_names

parse_field_names('x, y z')
# ('x', 'y', 'z')
parse_field_names(['lat', 'lon'])
# ('lat', 'lon')
parse_field_names('1st 2nd')
# Traceback (most recent call last):
#   ...
# ValueError: field_names must all be valid identifiers
```

We first assume it's a string — *EAFP*, "it's easier to ask forgiveness than
permission" (see the [glossary](https://docs.python.org/3/glossary.html#term-EAFP)) — and
convert commas to spaces and split the result into a list of names.  If
`AttributeError` was raised, `field_names` is not a `str` and we assume it was already
an iterable of names.  To make sure it's an iterable and to keep our own copy, we create
a tuple out of what we have.  A tuple is more compact than a list, and it also prevents
our code from changing the names by mistake.  Finally, `str.isidentifier()` ensures every
name is valid.

This is one situation where duck typing is more expressive than static type hints.
There is no way to spell a type hint that says "`field_names` must be a string of
identifiers separated by spaces or commas".  The `namedtuple` signature in typeshed
annotates it as `str | Iterable[str]`, which is OK as far as it goes, but is not enough
to catch all possible problems.

After reviewing dynamic protocols, we move to a more explicit form of runtime type
checking: goose typing.

## Goose Typing

> An abstract class represents an interface.
>
> — Bjarne Stroustrup, creator of C++

Python doesn't have an `interface` keyword.  We use abstract base classes to define
interfaces for explicit type checking at runtime — also supported by static type
checkers.  The Python Glossary entry for
[abstract base class](https://docs.python.org/3/glossary.html#term-abstract-base-class)
has a good explanation of the value they bring to duck-typed languages:

> Abstract base classes complement duck-typing by providing a way to define interfaces
> when other techniques like `hasattr()` would be clumsy or subtly wrong (for example
> with magic methods).  ABCs introduce virtual subclasses, which are classes that don't
> inherit from a class but are still recognized by `isinstance()` and `issubclass()`;
> see the `abc` module documentation.

*Goose typing* is a runtime type checking approach that leverages ABCs.  The term was
coined by Alex Martelli, who also helped spread "duck typing".  His argument goes like
this.

Biologists used to classify species by *phenetics*: similarities of morphology and
behavior — observable traits.  The analogy to duck typing is strong.  But parallel
evolution often produces similar traits among species that are actually unrelated, and
similar "accidental similarities" happen in programming too.  Consider the classic
example:

```python
class Artist:
    def draw(self): ...

class Gunslinger:
    def draw(self): ...

class Lottery:
    def draw(self): ...
```

The mere existence of a method named `draw`, callable without arguments, is far from
sufficient to assure us that two objects `x` and `y` such that `x.draw()` and `y.draw()`
can be called are in any way exchangeable or abstractly equivalent.  Nothing about the
semantics of such calls can be inferred.  We need a knowledgeable programmer to
positively assert that such an equivalence holds!

In biology, this led to *cladistics*: classifying by characteristics inherited from
common ancestors, rather than ones independently evolved — DNA analysis reclassified
several waterfowl that had long been grouped by looks.  By loose analogy, Martelli
recommends *supplementing* (not replacing) duck typing with goose typing:
`isinstance(obj, cls)` is now just fine… as long as `cls` is an abstract base class —
in other words, `cls`'s metaclass is `abc.ABCMeta`.  You can find many useful existing
ABCs in `collections.abc` (and additional ones in the `numbers` module).

Among the many conceptual advantages of ABCs over concrete classes, Python's ABCs add
one major practical advantage: the `register` class method, which lets end-user code
"declare" that a certain class becomes a "virtual" subclass of an ABC.  The registered
class must meet the ABC's method name and signature requirements, and more importantly
the underlying semantic contract, but it need not have been developed with any
awareness of the ABC, and in particular need not inherit from it.  This goes a long way
toward breaking the rigidity and strong coupling that make inheritance something to use
with much more caution than typically practiced.

Sometimes you don't even need to register a class for an ABC to recognize it as a
subclass!  That's the case for ABCs whose essence boils down to a few special methods:

```python
class Struggle:
    def __len__(self): return 23

from collections import abc
isinstance(Struggle(), abc.Sized)
# True
```

As you see, `abc.Sized` recognizes `Struggle` as "a subclass", with no need for
registration, since implementing the special method named `__len__` is all it takes.
(It's supposed to be implemented with the proper syntax — callable without arguments —
and semantics — returning a nonnegative integer denoting an object's "length"; any code
that implements a specially named method with arbitrary, noncompliant syntax and
semantics has much worse problems anyway.)

So Martelli's advice is: whenever you're implementing a class embodying any of the
concepts represented in the ABCs in `numbers`, `collections.abc` or another framework
you may be using, be sure (if needed) to subclass it from, or register it into, the
corresponding ABC.  At the start of programs using a library that omitted to do that,
perform the registrations yourself; then, when you must check for (most typically) an
argument being, say, "a sequence", check whether
`isinstance(the_arg, collections.abc.Sequence)`.

And, don't define custom ABCs (or metaclasses) in production code.  If you feel the urge
to do so, it's likely a case of "all problems look like a nail" syndrome for somebody who
just got a shiny new hammer.

To summarize, goose typing entails:

* Subclassing from ABCs to make it explicit that you are implementing a previously
  defined interface.
* Runtime type checking using ABCs instead of concrete classes as the second argument
  for `isinstance` and `issubclass`.

Inheriting from an ABC is more than implementing the required methods: it's also a clear
declaration of intent by the developer.  That intent can also be made explicit by
registering a virtual subclass.  For example, given the `FrenchDeck` class, to make it
pass a check like `issubclass(FrenchDeck, Sequence)`, you can make it a virtual subclass
of the `Sequence` ABC with these lines (details in
[A Virtual Subclass of an ABC](#a-virtual-subclass-of-an-abc)):

```python
from collections.abc import Sequence
Sequence.register(FrenchDeck)
# <class '__main__.FrenchDeck'>
issubclass(FrenchDeck, Sequence)
# True
```

The use of `isinstance` and `issubclass` becomes more acceptable if you are checking
against ABCs instead of concrete classes.  Used with concrete classes, type checks limit
polymorphism — an essential feature of object-oriented programming.  With ABCs these
tests are more flexible: if a component does not implement an ABC by subclassing — but
does implement the required methods — it can always be registered after the fact so it
passes those explicit type checks.

> **Warning**
>
> Even with ABCs, excessive use of `isinstance` checks may be a code smell — a symptom of
> bad OO design.  It's usually not OK to have a chain of `if`/`elif`/`elif` with
> `isinstance` checks performing different actions depending on the type of object: you
> should be using polymorphism for that, i.e., design your classes so that the
> interpreter dispatches calls to the proper methods, instead of hardcoding the dispatch
> logic.  (When you do need type-based dispatch in a function, consider
> [`functools.singledispatch`](decorators.md#single-dispatch-generic-functions) or a
> [`match` statement](pattern-matching.md) with class patterns.)

On the other hand, it's OK to perform an `isinstance` check against an ABC if you must
enforce an API contract: "Dude, you have to implement this if you want to call me," as
technical reviewer Lennart Regebro put it.  That's particularly useful in systems that
have a plug-in architecture.  Outside of frameworks, duck typing is often simpler and
more flexible than type checks.

Finally, restraint is needed in the creation of ABCs.  Excessive use of ABCs would impose
ceremony in a language that became popular because it is practical and pragmatic.  As
Martelli put it: ABCs are meant to encapsulate very general concepts introduced by a
framework — things like "a sequence" and "an exact number".  Most readers don't need to
write any new ABCs, just use existing ones correctly, to get 99.9% of the benefits without
serious risk of misdesign.

Now let's see goose typing in practice.

### Subclassing an ABC

Following Martelli's advice, we'll leverage an existing ABC,
`collections.abc.MutableSequence`, before daring to invent our own.  Here `FrenchDeck2`
is explicitly declared a subclass of `MutableSequence`:

```python
from collections import namedtuple, abc

Card = namedtuple('Card', ['rank', 'suit'])

class FrenchDeck2(abc.MutableSequence):
    ranks = [str(n) for n in range(2, 11)] + list('JQKA')
    suits = 'spades diamonds clubs hearts'.split()

    def __init__(self):
        self._cards = [Card(rank, suit) for suit in self.suits
                                        for rank in self.ranks]

    def __len__(self):
        return len(self._cards)

    def __getitem__(self, position):
        return self._cards[position]

    def __setitem__(self, position, value):  # all we need to enable shuffling...
        self._cards[position] = value

    def __delitem__(self, position):  # ...but MutableSequence forces us to implement this
        del self._cards[position]

    def insert(self, position, value):  # ...and this, its third abstract method
        self._cards.insert(position, value)
```

`__setitem__()` is all we need to enable shuffling, but subclassing `MutableSequence`
forces us to implement `__delitem__()`, an abstract method of that ABC.  We are also
required to implement `insert`, another abstract method of `MutableSequence`.

Python does not check for the implementation of the abstract methods at import time
(when the module is loaded and compiled), but only at runtime when we actually try to
instantiate the class.  Then, if we fail to implement any of the abstract methods, we
get a `TypeError` exception with a message such as `"Can't instantiate abstract class
FrenchDeck2 without an implementation for abstract methods '__delitem__', 'insert'"`.
That's why we must implement `__delitem__()` and `insert`, even if our examples do not
need those behaviors: the `MutableSequence` ABC demands them.

Not all methods of the `Sequence` and `MutableSequence` ABCs are abstract.  You can ask
an ABC which methods are abstract:

```python
sorted(abc.MutableSequence.__abstractmethods__)
# ['__delitem__', '__getitem__', '__len__', '__setitem__', 'insert']
```

To write `FrenchDeck2` as a subclass of `MutableSequence`, we had to pay the price of
implementing `__delitem__()` and `insert`, which our examples did not require.  In
return, `FrenchDeck2` inherits five concrete methods from `Sequence`: `__contains__()`,
`__iter__()`, `__reversed__()`, `index` and `count`.  From `MutableSequence`, it gets
another six methods: `append`, `reverse`, `extend`, `pop`, `remove` and `__iadd__()` —
which supports the `+=` operator for in-place concatenation.

```python
deck2 = FrenchDeck2()
deck2.pop()
# Card(rank='A', suit='hearts')
len(deck2)
# 51
deck2.index(Card('Q', 'hearts'))
# 49
```

The concrete methods in each `collections.abc` ABC are implemented in terms of the
public interface of the class, so they work without any knowledge of the internal
structure of instances.

> **Tip**
>
> As the coder of a concrete subclass, you may be able to override methods inherited
> from ABCs with more efficient implementations.  For example, `__contains__()` works by
> doing a sequential scan of the sequence, but if your concrete sequence keeps its items
> sorted, you can write a faster `__contains__()` that does a binary search using the
> [`bisect`](stdlib2.md#tut-list-tools) module.

To use ABCs well, you need to know what's available.  We'll review the collections ABCs
next.

### ABCs in the Standard Library

The standard library provides many ABCs.  Most are defined in the `collections.abc`
module, but there are others: you can find ABCs in the `io` and `numbers` packages, for
example.  But the most widely used are in `collections.abc`.

> **Note**
>
> There are two modules named `abc` in the standard library.  Here we are talking about
> `collections.abc`.  To reduce loading time, that module is implemented outside of the
> `collections` package — in `Lib/_collections_abc.py` — so it's imported separately from
> `collections`.  The other `abc` module is just `abc` (i.e., `Lib/abc.py`) where the
> `abc.ABC` class is defined.  Every ABC depends on the `abc` module, but we don't need to
> import it ourselves except to create a brand-new ABC.

The documentation of `collections.abc` has a
[nice table](https://docs.python.org/3/library/collections.abc.html#collections-abstract-base-classes)
summarizing the ABCs, their relationships, and their abstract and concrete methods
(called "mixin methods").  There is plenty of multiple inheritance going on there.
[Inheritance: For Better or for Worse](inheritance.md) is devoted to multiple
inheritance, but for now it's enough to say that it is usually not a problem when ABCs
are concerned.  Here are the main clusters:

**`Iterable`, `Container`, `Sized`**
: Every collection should either inherit from these ABCs or implement compatible
  protocols.  `Iterable` supports iteration with `__iter__()`, `Container` supports the
  `in` operator with `__contains__()`, and `Sized` supports `len()` with `__len__()`.

**`Collection`**
: This ABC has no methods of its own, but was added in Python 3.6 to make it easier to
  subclass from `Iterable`, `Container` and `Sized`.

**`Sequence`, `Mapping`, `Set`**
: These are the main immutable collection types, and each has a mutable subclass:
  `MutableSequence`, `MutableMapping` and `MutableSet`.

**`MappingView`**
: The objects returned from the mapping methods `.items()`, `.keys()` and `.values()`
  implement the interfaces defined in `ItemsView`, `KeysView` and `ValuesView`,
  respectively.  The first two also implement the rich interface of `Set`, with all the
  operators we saw in [Set Operations](dicts-sets.md).

**`Iterator`**
: Note that `Iterator` subclasses `Iterable`.  We discuss this further in
  [Iterators, Generators, and Classic Coroutines](iterators-generators.md).

**`Callable`, `Hashable`**
: These are not collections, but `collections.abc` was the first package to define ABCs
  in the standard library, and these two were deemed important enough to be included.
  They support type checking objects that must be callable or hashable.

**`Buffer`**
: Added in Python 3.12 ([**PEP 688**](https://peps.python.org/pep-0688/)) for objects
  implementing the buffer protocol, such as `bytes`, `bytearray`, `memoryview` and
  `array.array`.

There are also ABCs for asynchronous programming — `Awaitable`, `Coroutine`,
`AsyncIterable`, `AsyncIterator` and `AsyncGenerator` — which we'll meet in
[Asynchronous Programming](asyncio.md).

For callable detection, the `callable(obj)` built-in function is more convenient than
`isinstance(obj, Callable)`.  If `isinstance(obj, Hashable)` returns `False`, you can be
certain that `obj` is not hashable.  But if the return is `True`, it may be a false
positive, as the next note explains.

> **Warning**
>
> It's easy to misinterpret the results of `isinstance` and `issubclass` tests against
> the `Hashable` and `Iterable` ABCs.
>
> If `isinstance(obj, Hashable)` returns `True`, that only means that the class of `obj`
> implements or inherits `__hash__()`.  But if `obj` is a tuple containing unhashable
> items, then `obj` is not hashable, despite the positive result of the `isinstance`
> check.  Duck typing provides the most accurate way to determine if an instance is
> hashable: call `hash(obj)`.  That call will raise `TypeError` if `obj` is not hashable.
>
> On the other hand, even when `isinstance(obj, Iterable)` returns `False`, Python may
> still be able to iterate over `obj` using `__getitem__()` with 0-based indices, as we
> saw with `Vowels`.  The documentation for `collections.abc.Iterable` states: "The only
> reliable way to determine whether an object is iterable is to call `iter(obj)`."

```python
from collections.abc import Hashable, Iterable
t = (1, 2, [30, 40])
isinstance(t, Hashable)
# True
hash(t)
# Traceback (most recent call last):
#   ...
# TypeError: unhashable type: 'list'
isinstance(Vowels(), Iterable)
# False
list(iter(Vowels()))
# ['A', 'E', 'I', 'O', 'U']
```

After looking at some existing ABCs, let's practice goose typing by implementing an ABC
from scratch and putting it to use.  The goal here is not to encourage everyone to start
creating ABCs left and right, but to learn how to read the source code of the ABCs you'll
find in the standard library and other packages.

### Defining and Using an ABC

ABCs, like descriptors and metaclasses, are tools for building frameworks.  But they
also have use cases in type hints: as discussed in
[Abstract Base Classes](type-hints-functions.md#abstract-base-classes), using ABCs
instead of concrete types in function argument type hints gives more flexibility to the
caller.

To justify creating an ABC, we need to come up with a context for using it as an
extension point in a framework.  So here is our context: imagine you need to display
advertisements on a website or a mobile app in random order, but without repeating an ad
before the full inventory of ads is shown.  Now let's assume we are building an ad
management framework called ADAM.  One of its requirements is to support user-provided
nonrepeating random-picking classes.  To make it clear to ADAM users what is expected of
a "nonrepeating random-picking" component, we'll define an ABC.

In the literature about data structures, "stack" and "queue" describe abstract
interfaces in terms of physical arrangements of objects.  We'll follow suit and use a
real-world metaphor to name our ABC: bingo cages and lottery blowers are machines
designed to pick items at random from a finite set, without repeating, until the set is
exhausted.  The ABC will be named `Tombola`, after the Italian name of bingo and the
tumbling container that mixes the numbers.

The `Tombola` ABC has four methods.  The two abstract methods are:

`.load(...)`
: Put items into the container.

`.pick()`
: Remove one item at random from the container, returning it.

The concrete methods are:

`.loaded()`
: Return `True` if there is at least one item in the container.

`.inspect()`
: Return a tuple built from the items currently in the container, without changing its
  contents (the internal ordering is not preserved).

Here is the definition of the `Tombola` ABC:

```python
import abc

class Tombola(abc.ABC):  # to define an ABC, subclass abc.ABC

    @abc.abstractmethod
    def load(self, iterable):
        """Add items from an iterable."""

    @abc.abstractmethod
    def pick(self):
        """Remove item at random, returning it.

        This method should raise `LookupError` when the instance is empty.
        """

    def loaded(self):  # an ABC may include concrete methods
        """Return `True` if there's at least 1 item, `False` otherwise."""
        return bool(self.inspect())

    def inspect(self):
        """Return a sorted tuple with the items currently inside."""
        items = []
        while True:
            try:
                items.append(self.pick())
            except LookupError:
                break
        self.load(items)
        return tuple(sorted(items))
```

To define an ABC, subclass `abc.ABC`.  An abstract method is marked with the
[`@abstractmethod`](https://docs.python.org/3/library/abc.html#abc.abstractmethod)
decorator, and often its body is empty except for a docstring.  (Before ABCs existed,
abstract methods would raise `NotImplementedError` to signal that subclasses were
responsible for their implementation.)  The docstring of `pick` instructs implementers
to raise `LookupError` if there are no items to pick.

An ABC may include concrete methods, but concrete methods in an ABC must rely only on
the interface defined by the ABC (i.e., other concrete or abstract methods or properties
of the ABC).  We can't know how concrete subclasses will store the items, but we can
build the `inspect` result by emptying the `Tombola` with successive calls to `.pick()`,
and then use `.load(...)` to put everything back.

> **Tip**
>
> An abstract method can actually have an implementation.  Even if it does, subclasses
> will still be forced to override it, but they will be able to invoke the abstract
> method with `super()`, adding functionality to it instead of implementing from
> scratch.

The code for `.inspect()` is silly, but it shows that we can rely on `.pick()` and
`.load(...)` to inspect what's inside the `Tombola` — without knowing how the items are
actually stored.  The point of this example is to highlight that it's OK to provide
concrete methods in ABCs, as long as they only depend on other methods in the interface.
Being aware of their internal data structures, concrete subclasses of `Tombola` may
always override `.inspect()` with a smarter implementation, but they don't have to.

The `.loaded()` method has one line, but it's expensive: it calls `.inspect()` to build
the tuple just to apply `bool()` on it.  This works, but a concrete subclass can do much
better, as we'll see.

Note that our roundabout implementation of `.inspect()` requires that we catch a
`LookupError` thrown by `self.pick()`.  The fact that `self.pick()` may raise
`LookupError` is also part of its interface, but there is no way to make this explicit in
Python, except in the documentation.

We chose the `LookupError` exception because of its place in the
[exception hierarchy](https://docs.python.org/3/library/exceptions.html#exception-hierarchy)
in relation to `IndexError` and `KeyError`, the most likely exceptions to be raised by
the data structures used to implement a concrete `Tombola`:

```text
BaseException
 └── Exception
      └── LookupError
           ├── IndexError
           └── KeyError
```

`IndexError` is the `LookupError` subclass raised when we try to get an item from a
sequence with an index beyond the last position; `KeyError` is raised when we use a
nonexistent key to get an item from a mapping.  Therefore, implementations can raise
`LookupError`, `IndexError`, `KeyError`, or a custom subclass of `LookupError` to comply
(see [Handling Exceptions](errors.md#tut-handling) for how `except` clauses match
subclasses).

We now have our very own `Tombola` ABC.  To witness the interface checking performed by
an ABC, let's try to fool `Tombola` with a defective implementation:

```python
class Fake(Tombola):  # declare Fake as a subclass of Tombola
    def pick(self):
        return 13

Fake  # the class was created, no errors so far
# <class '__main__.Fake'>
f = Fake()
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# TypeError: Can't instantiate abstract class Fake without an implementation for abstract method 'load'
```

`TypeError` is raised when we try to instantiate `Fake`.  The message is very clear:
`Fake` is considered abstract because it failed to implement `load`, one of the abstract
methods declared in the `Tombola` ABC.

So we have our first ABC defined, and we put it to work validating a class.  We'll soon
subclass the `Tombola` ABC, but first we must cover some ABC coding rules.

### ABC Syntax Details

The standard way to declare an ABC is to subclass `abc.ABC` or any other ABC.  (Older
code uses the `metaclass` keyword — `class Tombola(metaclass=abc.ABCMeta):` — which is
what `abc.ABC` does for you; metaclasses are covered in
[Class Metaprogramming](class-metaprogramming.md).)

Besides the `ABC` base class and the `@abstractmethod` decorator, the `abc` module
defines the `@abstractclassmethod`, `@abstractstaticmethod` and `@abstractproperty`
decorators.  However, these last three are deprecated, because it's possible to stack
decorators on top of `@abstractmethod`, making the others redundant.  For example, the
preferred way to declare an abstract class method is:

<!-- nocheck -->
```python
class MyABC(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def an_abstract_classmethod(cls, ...):
        pass
```

> **Warning**
>
> The order of stacked function decorators matters, and in the case of
> `@abstractmethod`, the documentation is explicit: "When `abstractmethod()` is applied
> in combination with other method descriptors, it should be applied as the innermost
> decorator."  In other words, no other decorator may appear between `@abstractmethod`
> and the `def` statement.

Now that we've got these ABC syntax issues covered, let's put `Tombola` to use by
implementing two concrete descendants of it.

### Subclassing the `Tombola` ABC

Given the `Tombola` ABC, we'll now develop two concrete subclasses that satisfy its
interface.  The `BingoCage` class below is a variation of the one in
[User-Defined Callable Types](first-class-functions.md#user-defined-callable-types),
using a better randomizer.  This `BingoCage` implements the required abstract methods
`load` and `pick`:

```python
import random

class BingoCage(Tombola):  # BingoCage explicitly extends Tombola

    def __init__(self, items):
        self._randomizer = random.SystemRandom()
        self._items = []
        self.load(items)  # delegate initial loading to the .load() method

    def load(self, items):
        self._items.extend(items)
        self._randomizer.shuffle(self._items)

    def pick(self):
        try:
            return self._items.pop()
        except IndexError:
            raise LookupError('pick from empty BingoCage')

    def __call__(self):
        return self.pick()
```

Pretend we'll use this for online gaming:
[`random.SystemRandom`](https://docs.python.org/3/library/random.html#random.SystemRandom)
implements the `random` API on top of the `os.urandom(...)` function, which provides
random bytes "suitable for cryptographic use", according to the `os` module docs.
Instead of the plain `random.shuffle()` function, we use the `.shuffle()` method of our
`SystemRandom` instance.  `__call__()` is not needed to satisfy the `Tombola` interface,
but there's no harm in adding extra methods.

`BingoCage` inherits the expensive `loaded` and the silly `inspect` methods from
`Tombola`.  Both could be overridden with much faster one-liners, as in the next example.
The point is: we can be lazy and just inherit the suboptimal concrete methods from an
ABC.  The methods inherited from `Tombola` are not as fast as they could be for
`BingoCage`, but they do provide correct results for any `Tombola` subclass that
correctly implements `pick` and `load`:

```python
cage = BingoCage(range(5))
cage.inspect()
# (0, 1, 2, 3, 4)
cage.loaded()
# True
picks = {cage() for _ in range(5)}
sorted(picks)
# [0, 1, 2, 3, 4]
cage.loaded()
# False
cage.pick()
# Traceback (most recent call last):
#   ...
# LookupError: pick from empty BingoCage
```

Here is a very different but equally valid implementation of the `Tombola` interface.
Instead of shuffling the "balls" and popping the last, `LottoBlower` pops from a random
position:

```python
import random

class LottoBlower(Tombola):

    def __init__(self, iterable):
        self._balls = list(iterable)  # accept any iterable, build a list

    def load(self, iterable):
        self._balls.extend(iterable)

    def pick(self):
        try:
            position = random.randrange(len(self._balls))
        except ValueError:
            raise LookupError('pick from empty LottoBlower')
        return self._balls.pop(position)

    def loaded(self):  # override loaded to avoid calling inspect
        return bool(self._balls)

    def inspect(self):  # override inspect with a one-liner
        return tuple(sorted(self._balls))
```

The initializer accepts any iterable: the argument is used to build a list.  The
`random.randrange(...)` function raises `ValueError` if the range is empty, so we catch
that and raise `LookupError` instead, to be compatible with `Tombola`.  Otherwise the
randomly selected item is popped from `self._balls`.  We override `loaded` to avoid
calling `inspect` (as `Tombola.loaded` does): we can make it faster by working with
`self._balls` directly — no need to build a whole new tuple.  And we override `inspect`
with a one-liner.

This illustrates an idiom worth mentioning: in `__init__()`, `self._balls` stores
`list(iterable)` and not just a reference to `iterable` (i.e., we did not merely assign
`self._balls = iterable`, aliasing the argument).  As mentioned in
[Defensive Programming and "Fail Fast"](#defensive-programming-and-fail-fast), this
makes our `LottoBlower` flexible because the `iterable` argument may be any iterable
type.  At the same time, we make sure to store its items in a `list` so we can pop
items.  And even if we always get lists as the `iterable` argument, `list(iterable)`
produces a copy of the argument, which is a good practice considering we will be
removing items from it and the client might not expect that the provided list will be
changed (see [Defensive Programming with Mutable Parameters](references.md#defensive-programming-with-mutable-parameters)).

We now come to the crucial dynamic feature of goose typing: declaring virtual subclasses
with the `register` method.

### A Virtual Subclass of an ABC

An essential characteristic of goose typing — and one reason why it deserves a waterfowl
name — is the ability to register a class as a *virtual subclass* of an ABC, even if it
does not inherit from it.  When doing so, we promise that the class faithfully implements
the interface defined in the ABC, and Python will believe us without checking.  If we
lie, we'll be caught by the usual runtime exceptions.

This is done by calling a `register` class method on the ABC.  The registered class then
becomes a virtual subclass of the ABC, and will be recognized as such by `issubclass`,
but it does not inherit any methods or attributes from the ABC.

> **Warning**
>
> Virtual subclasses do not inherit from their registered ABCs, and are not checked for
> conformance to the ABC interface at any time, not even when they are instantiated.
> Also, static type checkers don't understand virtual subclasses.

The `register` method is usually invoked as a plain function (see
[Usage of `register` in Practice](#usage-of-register-in-practice)), but it can also be
used as a decorator.  Here we use the decorator syntax and implement `TomboList`, a
real subclass of `list` and a virtual subclass of `Tombola`:

```python
from random import randrange

@Tombola.register  # TomboList is registered as a virtual subclass of Tombola
class TomboList(list):  # TomboList extends list

    def pick(self):
        if self:  # TomboList inherits its boolean behavior from list
            position = randrange(len(self))
            return self.pop(position)  # our pick calls self.pop, inherited from list
        else:
            raise LookupError('pop from empty TomboList')

    load = list.extend  # TomboList.load is the same as list.extend

    def loaded(self):
        return bool(self)

    def inspect(self):
        return tuple(sorted(self))

# Tombola.register(TomboList)  # the alternative, without decorator syntax
```

`TomboList` inherits its boolean behavior from `list`, which returns `True` if the list
is not empty.  `TomboList.load` is the same as `list.extend`, and `loaded` delegates to
`bool`.  (The same trick used with `load` doesn't work with `loaded`, because the `list`
type does not implement `__bool__()`, the method we'd have to bind to `loaded`.  The
`bool()` built-in doesn't need `__bool__()` to work because it can also use `__len__()`;
see [Truth Value Testing](https://docs.python.org/3/library/stdtypes.html#truth).)

It's always possible to call `register` as in the commented line at the end, and it's
useful to do so when you need to register a class that you do not maintain, but which
does fulfill the interface.

Because of the registration, the functions `issubclass` and `isinstance` act as if
`TomboList` is a subclass of `Tombola`:

```python
issubclass(TomboList, Tombola)
# True
t = TomboList(range(100))
isinstance(t, Tombola)
# True
```

However, inheritance is guided by a special class attribute named `__mro__` — the Method
Resolution Order.  It basically lists the class and its superclasses in the order Python
uses to search for methods (there's a whole section about it in
[Multiple Inheritance and Method Resolution Order](inheritance.md#multiple-inheritance-and-method-resolution-order)).
If you inspect the `__mro__` of `TomboList`, you'll see that it lists only the "real"
superclasses — `list` and `object`:

```python
TomboList.__mro__
# (<class '__main__.TomboList'>, <class 'list'>, <class 'object'>)
```

`Tombola` is not in `TomboList.__mro__`, so `TomboList` does not inherit any methods from
`Tombola`.

This concludes our `Tombola` ABC case study.  In the next section, we'll address how the
`register` ABC function is used in the wild.

### Usage of `register` in Practice

Above we used `Tombola.register` as a class decorator, but it's more widely deployed as a
function to register classes defined elsewhere.  For example, in the source code for the
`collections.abc` module, the built-in types `tuple`, `str`, `range` and `memoryview` are
registered as virtual subclasses of `Sequence`, like this:

<!-- nocheck -->
```python
Sequence.register(tuple)
Sequence.register(str)
Sequence.register(range)
Sequence.register(memoryview)
```

Several other built-in types are registered to ABCs in `_collections_abc.py`.  Those
registrations happen only when that module is imported, which is OK because you'll have
to import it anyway to get the ABCs.  For example, you need to import `MutableMapping`
from `collections.abc` to perform a check like `isinstance(my_dict, MutableMapping)`.

Subclassing an ABC or registering with an ABC are both explicit ways of making our
classes pass `issubclass` checks — as well as `isinstance` checks, which also rely on
`issubclass`.  But some ABCs support structural typing as well.  The next section
explains.

### Structural Typing with ABCs

ABCs are mostly used with nominal typing.  When a class `Sub` explicitly inherits from
`AnABC`, or is registered with `AnABC`, the name of `AnABC` is linked to the `Sub` class —
and that's how, at runtime, `issubclass(Sub, AnABC)` returns `True`.

In contrast, structural typing is about looking at the structure of an object's public
interface to determine its type: an object is consistent-with a type if it implements the
methods defined in the type.  Dynamic and static duck typing are two approaches to
structural typing.

It turns out that some ABCs also support structural typing.  Recall the `Struggle` class
from the beginning of this section, now with an added test using `issubclass`:

```python
class Struggle:
    def __len__(self): return 23

from collections import abc
isinstance(Struggle(), abc.Sized)
# True
issubclass(Struggle, abc.Sized)
# True
```

Class `Struggle` is considered a subclass of `abc.Sized` by the `issubclass` function
(and, consequently, by `isinstance` as well) because `abc.Sized` implements a special
class method named `__subclasshook__()`.  The `__subclasshook__()` for `Sized` checks
whether the class argument has an attribute named `__len__`.  If it does, then it is
considered a virtual subclass of `Sized`.  Here is the definition of `Sized` from
`Lib/_collections_abc.py`:

<!-- nocheck -->
```python
class Sized(metaclass=ABCMeta):

    __slots__ = ()

    @abstractmethod
    def __len__(self):
        return 0

    @classmethod
    def __subclasshook__(cls, C):
        if cls is Sized:
            return _check_methods(C, "__len__")
        return NotImplemented
```

The helper `_check_methods()` looks for an attribute named `__len__` in the `__dict__` of
any class listed in `C.__mro__` (i.e., `C` and its superclasses).  If it finds one, the
hook returns `True`, signaling that `C` is a virtual subclass of `Sized`.  Otherwise it
returns `NotImplemented` to let the subclass check proceed.  (A method set to `None` in a
class counts as explicitly blocked; that's how a class can opt out of a protocol, the way
`__hash__ = None` makes a class unhashable.)

That's how `__subclasshook__()` allows ABCs to support structural typing.  You can
formalize an interface with an ABC, you can make `isinstance` checks against that ABC,
and still have a completely unrelated class pass an `issubclass` check because it
implements a certain method (or because it does whatever it takes to convince a
`__subclasshook__()` to vouch for it).

Is it a good idea to implement `__subclasshook__()` in our own ABCs?  Probably not.  All
the implementations of `__subclasshook__()` in the Python source code are in ABCs like
`Sized` that declare just one special method, and they simply check for that special
method name.  Given their "special" status, you can be pretty sure that any method named
`__len__` does what you expect.  But even in the realm of special methods and
fundamental ABCs, it can be risky to make such assumptions.  For example, mappings
implement `__len__()`, `__getitem__()` and `__iter__()`, but they are rightly not
considered subtypes of `Sequence`, because you can't retrieve items using integer
offsets or slices.  That's why the `abc.Sequence` class does not implement
`__subclasshook__()`.

For ABCs that you and I may write, a `__subclasshook__()` would be even less dependable.
We should not believe that any class named `Spam` that implements or inherits `load`,
`pick`, `inspect` and `loaded` is guaranteed to behave as a `Tombola`.  It's better to let
the programmer affirm it by subclassing `Spam` from `Tombola`, or registering it with
`Tombola.register(Spam)`.

## Static Protocols

Static protocols were introduced in [Static Protocols](type-hints-functions.md#static-protocols),
in the chapter about type hints in functions, because static type checking without
protocols doesn't handle Pythonic APIs very well.  We will wrap up this chapter by
illustrating static protocols with two simple examples, and a discussion of numeric ABCs
and protocols.

### The Typed `double` Function

When introducing Python to programmers more used to statically typed languages, one
favorite example is this simple `double` function:

```python
def double(x):
    return x * 2

double(1.5)
# 3.0
double('A')
# 'AA'
double([10, 20, 30])
# [10, 20, 30, 10, 20, 30]
from fractions import Fraction
double(Fraction(2, 5))
# Fraction(4, 5)
```

Before static protocols were introduced, there was no practical way to add type hints to
`double` without limiting its possible uses.  Thanks to duck typing, `double` works even
with types from the future, such as the enhanced `Vector` class that we'll see in
[Overloading `*` for Scalar Multiplication](operator-overloading.md#overloading--for-scalar-multiplication):

<!-- nocheck -->
```python
double(Vector([11.0, 12.0, 13.0]))
# Vector([22.0, 24.0, 26.0])
```

The initial implementation of type hints in Python was a nominal type system: the name of
a type in an annotation had to match the name of the type of the actual arguments — or
the name of one of its superclasses.  Since it's impossible to name all types that
implement a protocol by supporting the required operations, duck typing could not be
described by type hints before Python 3.8.

Now, with `typing.Protocol` we can tell a type checker that `double` takes an argument
`x` that supports `x * 2`.  Here's how:

```python
from typing import Protocol, Self

class Repeatable(Protocol):
    def __mul__(self, repeat_count: int) -> Self: ...

def double[RT: Repeatable](x: RT) -> RT:
    return x * 2
```

`__mul__` is the essence of the `Repeatable` protocol.  The `self` parameter is usually
not annotated — its type is assumed to be the class — and the
[`Self`](https://docs.python.org/3/library/typing.html#typing.Self) return type
(Python 3.11+) says the result type is the same as the type of `self`.  Note that
`repeat_count` is limited to `int` in this protocol.  `RT` is a type parameter bounded
by `Repeatable` (using the [**PEP 695**](https://peps.python.org/pep-0695/) syntax
introduced in Python 3.12; see
[Bounded type variables](type-hints-functions.md#bounded-type-variables)): the type
checker will require that the actual type implements `Repeatable`.

Now the type checker is able to verify that the `x` parameter is an object that can be
multiplied by an integer, and the return value has the same type as `x`.  This example
shows why PEP 544 is titled "Protocols: Structural subtyping (static duck typing)".  The
nominal type of the actual argument `x` given to `double` is irrelevant as long as it
quacks — that is, as long as it implements `__mul__`.

### Runtime Checkable Static Protocols

On the typing map, `typing.Protocol` appears in the static checking half.  However, when
defining a `typing.Protocol` subclass, you can use the
[`@runtime_checkable`](https://docs.python.org/3/library/typing.html#typing.runtime_checkable)
decorator to make that protocol support `isinstance`/`issubclass` checks at runtime.
This works because `typing.Protocol` is an ABC, therefore it supports the
`__subclasshook__()` we saw in [Structural Typing with ABCs](#structural-typing-with-abcs).

The `typing` module includes several ready-to-use protocols that are runtime checkable.
Here are two of them, quoted from the `typing` documentation:

`class typing.SupportsComplex`
: An ABC with one abstract method, `__complex__`.

`class typing.SupportsFloat`
: An ABC with one abstract method, `__float__`.

These protocols are designed to check numeric types for "convertibility": if an object
`o` implements `__complex__()`, then you should be able to get a `complex` by invoking
`complex(o)` — because the `__complex__()` special method exists to support the
`complex()` built-in function.  Here is the source code for the `typing.SupportsComplex`
protocol:

<!-- nocheck -->
```python
@runtime_checkable
class SupportsComplex(Protocol):
    """An ABC with one abstract method __complex__."""

    __slots__ = ()

    @abstractmethod
    def __complex__(self) -> complex:
        pass
```

The key is the `__complex__` abstract method.  (The `__slots__` attribute is irrelevant
here — it's the optimization covered in
[Saving Memory with `__slots__`](pythonic-object.md#saving-memory-with-__slots__).)
During static type checking, an object will be considered consistent-with the
`SupportsComplex` protocol if it implements a `__complex__` method that takes only `self`
and returns a `complex`.  Thanks to `@runtime_checkable`, that protocol can also be used
with `isinstance` checks:

```python
from typing import SupportsComplex
import numpy as np
c64 = np.complex64(3+4j)  # complex64 is one of the complex types provided by NumPy
isinstance(c64, complex)  # none of them subclasses the built-in complex
# False
isinstance(c64, SupportsComplex)  # but they implement __complex__, so they comply
# True
c = complex(c64)  # therefore you can create built-in complex objects from them
c
# (3+4j)
isinstance(c, SupportsComplex)  # the built-in complex has __complex__ too (3.11+)
# True
complex(c)
# (3+4j)
```

An alternative would be to use the `Complex` ABC, defined in the
[`numbers`](https://docs.python.org/3/library/numbers.html) module.  The built-in
`complex` type and the NumPy `complex64` and `complex128` types are all registered as
virtual subclasses of `numbers.Complex`, therefore this works:

```python
import numbers
isinstance(c, numbers.Complex)
# True
isinstance(c64, numbers.Complex)
# True
```

The `numbers` ABCs were once recommended for this kind of check, but that's no longer
good advice, because those ABCs are not recognized by static type checkers, as we'll see
in [The `numbers` ABCs and Numeric Protocols](#the-numbers-abcs-and-numeric-protocols).

This example demonstrates that a runtime checkable protocol works with `isinstance`, but
it turns out this is not a particularly good use case of `isinstance`, as the next note
explains.

> **Tip**
>
> If you're using an external type checker, there is one advantage of explicit
> `isinstance` checks: when you write an `if` statement where the condition is
> `isinstance(o, MyType)`, then the type checker can infer that inside the `if` block,
> the type of the `o` object is consistent-with `MyType`.  This is called *type
> narrowing*.

#### Duck typing is your friend

Very often at runtime, duck typing is the best approach for type checking: instead of
calling `isinstance` or `hasattr`, just try the operations you need to do on the object,
and handle exceptions as needed.  Given an object `o` that you need to use as a complex
number, this would be one approach:

<!-- nocheck -->
```python
if isinstance(o, (complex, SupportsComplex)):
    # do something that requires `o` to be convertible to complex
    ...
else:
    raise TypeError('o must be convertible to complex')
```

The goose typing approach would be to use the `numbers.Complex` ABC:

<!-- nocheck -->
```python
if isinstance(o, numbers.Complex):
    # do something with `o`, an instance of `Complex`
    ...
else:
    raise TypeError('o must be an instance of Complex')
```

However, it's often better to leverage duck typing and do this using the EAFP
principle:

<!-- nocheck -->
```python
try:
    c = complex(o)
except TypeError as exc:
    raise TypeError('o must be convertible to complex') from exc
```

And, if all you're going to do is raise a `TypeError` anyway, then omit the
`try`/`except`/`raise` statements and just write this:

<!-- nocheck -->
```python
c = complex(o)
```

In this last case, if `o` is not an acceptable type, Python will raise an exception with
a very clear message.  For example, this is what you get if `o` is a tuple (the exact
wording varies across versions):

```text
TypeError: complex() first argument must be a string or a number, not 'tuple'
```

The duck typing approach is much better in this case.

Now that we've seen how to use static protocols at runtime with preexisting types like
`complex` and `numpy.complex64`, we need to discuss the limitations of runtime checkable
protocols.

### Limitations of Runtime Protocol Checks

We've seen that type hints are generally ignored at runtime, and this also affects the use
of `isinstance` or `issubclass` checks against static protocols.  For example, any class
with a `__float__()` method is considered — at runtime — a virtual subclass of
`SupportsFloat`, even if the `__float__()` method does not return a `float`.

Here is a cautionary tale.  In Python 3.9, the `complex` type had a `__float__()` method,
but it existed only to raise `TypeError` with an explicit message: "can't convert complex
to float".  So in Python 3.9, `isinstance(3+4j, SupportsFloat)` returned `True`, which was
misleading: the runtime check suggested that you can convert a `complex` to `float`, but
in fact that raised a type error.  The specific issue with `complex` was fixed in Python
3.10 with the removal of `complex.__float__()`:

```python
from typing import SupportsFloat
isinstance(3+4j, SupportsFloat)
# False
```

But the overall issue remains: `isinstance`/`issubclass` checks only look at the presence
or absence of methods, without checking their signatures, much less their type
annotations.  And this is not about to change, because such type checks at runtime would
have an unacceptable performance cost: type checking is not just a matter of checking
whether the type of `x` is `T`; it's about determining that the type of `x` is
consistent-with `T`, which may be expensive.

> **Note**
>
> Since Python 3.12, `isinstance()` checks against runtime checkable protocols use
> [`inspect.getattr_static()`](https://docs.python.org/3/library/inspect.html#inspect.getattr_static)
> to look up attributes, so they no longer trigger properties or `__getattr__()` on the
> object being checked.  They are also noticeably faster than before, but still much
> slower than `isinstance()` against a concrete class.

Now let's see how to implement a static protocol in a user-defined class.

### Supporting a Static Protocol

Recall the `Vector2d` class we built in [A Pythonic Object](pythonic-object.md).  Given
that a `complex` number and a `Vector2d` instance both consist of a pair of floats, it
makes sense to support conversion from `Vector2d` to `complex`.  Here are the methods to
add to `Vector2d` for that, plus a `fromcomplex` class method for the inverse operation:

<!-- nocheck -->
```python
def __complex__(self):
    return complex(self.x, self.y)

@classmethod
def fromcomplex(cls, datum):
    return cls(datum.real, datum.imag)  # assumes datum has .real and .imag attributes
```

Given the preceding code, and the `__abs__()` method `Vector2d` already had, we get
these features:

<!-- nocheck -->
```python
from typing import SupportsComplex, SupportsAbs
v = Vector2d(3, 4)
isinstance(v, SupportsComplex)
# True
isinstance(v, SupportsAbs)
# True
complex(v)
# (3+4j)
abs(v)
# 5.0
Vector2d.fromcomplex(3+4j)
# Vector2d(3.0, 4.0)
```

For runtime type checking, that is fine, but for better static coverage and error
reporting with a type checker, the `__abs__()`, `__complex__()` and `fromcomplex`
methods should get type hints:

<!-- nocheck -->
```python
def __abs__(self) -> float:
    return math.hypot(self.x, self.y)

def __complex__(self) -> complex:
    return complex(self.x, self.y)

@classmethod
def fromcomplex(cls, datum: SupportsComplex) -> Vector2d:
    c = complex(datum)
    return cls(c.real, c.imag)
```

The `float` return annotation on `__abs__()` is needed, otherwise Mypy infers `Any`, and
doesn't check the body of the method.  Even without the annotation, Mypy is able to infer
that `__complex__()` returns a `complex`; the annotation prevents a warning, depending on
your configuration.  In `fromcomplex`, `SupportsComplex` ensures the `datum` is
convertible.  The explicit conversion `complex(datum)` is necessary, because the
`SupportsComplex` type does not declare `.real` and `.imag` attributes, used in the next
line.  For example, `Vector2d` doesn't have those attributes, but implements
`__complex__()`.

> **Note**
>
> Can the return type of `fromcomplex` really be written as `Vector2d`, inside the body of
> class `Vector2d` itself?  In Python 3.14 and later, yes: annotations are evaluated lazily
> ([**PEP 649**](https://peps.python.org/pep-0649/) and
> [**PEP 749**](https://peps.python.org/pep-0749/)), so a reference to a class that is not
> fully defined yet is fine.  In older versions you'd write the name as a string,
> `'Vector2d'`, or add `from __future__ import annotations` at the top of the module.  In
> this case, `Self` would also work as the return type.

Next, let's see how to create — and later, extend — a new static protocol.

### Designing a Static Protocol

While studying goose typing, we saw the `Tombola` ABC.  Here we'll see how to define a
similar interface using a static protocol.

The `Tombola` ABC specifies two methods: `pick` and `load`.  We could define a static
protocol with these two methods as well, but the Go community has learned that
single-method protocols make static duck typing more useful and flexible.  The Go standard
library has several interfaces like `Reader`, an interface for I/O that requires just a
`read` method.  After a while, if you realize a more complete protocol is required, you
can combine two or more protocols to define a new one.

Using a container that picks items at random may or may not require reloading the
container, but it certainly needs a method to do the actual pick, so that's the method
we'll choose for the minimal `RandomPicker` protocol:

```python
from typing import Protocol, runtime_checkable, Any

@runtime_checkable
class RandomPicker(Protocol):
    def pick(self) -> Any: ...
```

> **Note**
>
> The `pick` method returns `Any`.  In
> [Implementing a Generic Static Protocol](type-hints-more.md#implementing-a-generic-static-protocol),
> we will see how to make `RandomPicker` a generic type with a parameter to let users of
> the protocol specify the return type of the `pick` method.

And here are some tests using it:

```python
import random
from collections.abc import Iterable
from typing import Any, TYPE_CHECKING

class SimplePicker:  # implements RandomPicker, but does not subclass it
    def __init__(self, items: Iterable) -> None:
        self._items = list(items)
        random.shuffle(self._items)

    def pick(self) -> Any:
        return self._items.pop()

def test_isinstance() -> None:
    popper: RandomPicker = SimplePicker([1])
    assert isinstance(popper, RandomPicker)

def test_item_type() -> None:
    items = [1, 2]
    popper = SimplePicker(items)
    item = popper.pick()
    assert item in items
    if TYPE_CHECKING:
        reveal_type(item)
    assert isinstance(item, int)

test_isinstance()
test_item_type()
```

It's not necessary to import the static protocol to define a class that implements it;
here `RandomPicker` is used only in `test_isinstance`.  `SimplePicker` implements
`RandomPicker` — but it does not subclass it.  This is static duck typing in action.
`Any` is the default return type, so the `pick` annotation is not strictly necessary, but
it does make it more clear that we are implementing the `RandomPicker` protocol.

Don't forget to add `-> None` hints to your tests if you want Mypy to look at them.  The
type hint on the `popper` variable shows that the type checker understands that
`SimplePicker` is consistent-with `RandomPicker`.  `test_isinstance` proves that an
instance of `SimplePicker` is also an instance of `RandomPicker`.  This works because of
the `@runtime_checkable` decorator applied to `RandomPicker`, and because `SimplePicker`
has a `pick` method as required.

`test_item_type` invokes the `pick` method from a `SimplePicker`, verifies that it returns
one of the items given to `SimplePicker`, and then does static and runtime checks on the
returned item.  `reveal_type` is a "magic" function recognized by type checkers; we can
only call it inside `if` blocks protected by
[`typing.TYPE_CHECKING`](https://docs.python.org/3/library/typing.html#typing.TYPE_CHECKING),
which is only `True` in the eyes of a static type checker, but is `False` at runtime.
(Since Python 3.11 there is also a real `typing.reveal_type()` function that prints the
runtime type, so the guard is no longer strictly required.)  Both tests pass, and Mypy
shows the result of the `reveal_type` on the item returned by `pick`:

```console
$ mypy randompick_test.py
randompick_test.py:24: note: Revealed type is "Any"
```

Having created our first protocol, let's study some advice on the matter.

### Best Practices for Protocol Design

After years of experience with static duck typing in Go, it is clear that narrow
protocols are more useful — often such protocols have a single method, rarely more than a
couple of methods.  Martin Fowler wrote a post defining
[role interface](https://martinfowler.com/bliki/RoleInterface.html), a useful idea to keep
in mind when designing protocols.

Also, sometimes you see a protocol defined near the function that uses it — that is,
defined in "client code" instead of being defined in a library.  This makes it easy to
create new types to call that function, which is good for extensibility and testing with
mocks.

The practices of narrow protocols and client-code protocols both avoid unnecessary tight
coupling, in line with the *Interface Segregation Principle*, which we can summarize as
"Clients should not be forced to depend upon interfaces that they do not use."

The typeshed contributing guidelines recommend this naming convention for static
protocols:

* Use plain names for protocols that represent a clear concept (e.g., `Iterator`,
  `Container`).
* Use `SupportsX` for protocols that provide callable methods (e.g., `SupportsInt`,
  `SupportsRead`, `SupportsReadSeek`).
* Use `HasX` for protocols that have readable and/or writable attributes or getter/setter
  methods (e.g., `HasItems`, `HasFileno`).

The Go standard library has another nice naming convention: for single-method protocols,
if the method name is a verb, append "-er" or "-or" to make it a noun.  For example,
instead of `SupportsRead`, have `Reader`.  More examples include `Formatter`, `Animator`
and `Scanner`.

One good reason to create minimalistic protocols is the ability to extend them later, if
needed.  We'll now see that it's not hard to create a derived protocol with an additional
method.

### Extending a Protocol

When practice reveals that a protocol with more methods is useful, instead of adding
methods to the original protocol, it's better to derive a new protocol from it.
Extending a static protocol in Python has a few caveats, as this example shows:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class LoadableRandomPicker(RandomPicker, Protocol):
    def load(self, iterable: Iterable) -> None: ...

isinstance(SimplePicker([1]), LoadableRandomPicker)  # no load method
# False
isinstance(LottoBlower([1]), LoadableRandomPicker)  # has both pick and load
# True
```

If you want the derived protocol to be runtime checkable, you must apply the decorator
again — its behavior is not inherited.  Every protocol must explicitly name
`typing.Protocol` as one of its base classes in addition to the protocol we are
extending; this is different from the way inheritance works in Python (see "Merging and
extending protocols" in PEP 544 for the rationale).  Back to "regular" object-oriented
programming: we only need to declare the method that is new in this derived protocol.
The `pick` method declaration is inherited from `RandomPicker`.

Note how `LottoBlower`, a subclass of the `Tombola` ABC that knows nothing about
`LoadableRandomPicker`, satisfies it anyway: that's structural typing.

To wrap up the chapter, we'll go over numeric ABCs and their possible replacement with
numeric protocols.

### The `numbers` ABCs and Numeric Protocols

As we saw in [The fall of the numeric tower](type-hints-functions.md#the-fall-of-the-numeric-tower),
the ABCs in the `numbers` package of the standard library work fine for runtime type
checking.  If you need to check for an integer, you can use
`isinstance(x, numbers.Integral)` to accept `int`, `bool` (which subclasses `int`) or
other integer types that are provided by external libraries that register their types as
virtual subclasses of the `numbers` ABCs.  For example, NumPy has many integer types, all
registered as `numbers.Integral` — as well as floating-point types registered as
`numbers.Real`, and complex numbers with various bit widths registered as
`numbers.Complex`.

> **Note**
>
> Somewhat surprisingly, `decimal.Decimal` is not registered as a virtual subclass of
> `numbers.Real`.  The reason is that, if you need the precision of `Decimal` in your
> program, then you want to be protected from accidental mixing of decimals with
> floating-point numbers that are less precise.

Sadly, the numeric tower was not designed for static type checking.  The root ABC —
`numbers.Number` — has no methods, so if you declare `x: Number`, a type checker will not
let you do arithmetic or call any methods on `x`.

If the `numbers` ABCs are not supported, what are the options?  A good place to look for
typing solutions is the typeshed project.  The stub file for the `statistics` module
uses definitions like these, written here in modern syntax:

<!-- nocheck -->
```python
type _Number = float | Decimal | Fraction
_NumberT = TypeVar('_NumberT', float, Decimal, Fraction)
```

That approach is correct, but limited.  It does not support numeric types outside of the
standard library, which the `numbers` ABCs do support at runtime — when the numeric types
are registered as virtual subclasses.

The current trend is to recommend the numeric protocols provided by the `typing` module,
which we discussed in [Runtime Checkable Static Protocols](#runtime-checkable-static-protocols).
Unfortunately, at runtime, the numeric protocols may let you down.  The built-ins
`float` and `int`, and also `numpy.float16` and `numpy.uint8`, don't have a
`__complex__()` method, so `isinstance(x, SupportsComplex)` returns `False` for them.
However, in practice, the `complex()` built-in constructor handles instances of all these
types with no errors or warnings:

```python
import numpy as np
from typing import SupportsComplex
sample = [1+0j, np.complex64(1+0j), 1.0, np.float16(1.0), 1, np.uint8(1)]
[isinstance(x, SupportsComplex) for x in sample]
# [True, True, False, False, False, False]
[complex(x) for x in sample]
# [(1+0j), (1+0j), (1+0j), (1+0j), (1+0j), (1+0j)]
```

This shows that `isinstance` checks against `SupportsComplex` suggest that some of those
conversions to `complex` would fail, but they all succeed.  Guido van Rossum pointed out
that the built-in `complex` accepts a single argument of these types (through
`__float__()` and `__index__()`), and that's why those conversions work.

On the other hand, Mypy accepts arguments of all those six types in a call to a
`to_complex()` function defined like this:

<!-- nocheck -->
```python
def to_complex(n: SupportsComplex) -> complex:
    return complex(n)
```

Mypy is "aware" that the built-in `int` and `float` can be converted to `complex`, even
though they don't implement `__complex__()`.  In conclusion, although numeric types
should not be hard to type check, the current situation is this: PEP 484 eschews the
numeric tower and implicitly recommends that type checkers hardcode the subtype
relationships among built-in `complex`, `float` and `int`.  Mypy does that, and it also
pragmatically accepts that `int` and `float` are consistent-with `SupportsComplex`.

> **Tip**
>
> The unexpected results with `isinstance` checks against numeric `Supports*` protocols
> show up mostly in conversions to or from `complex`.  If you don't use complex numbers,
> you can rely on those protocols instead of the `numbers` ABCs.

The main takeaways for this section are:

* The `numbers` ABCs are fine for runtime type checking, but unsuitable for static
  typing.
* The numeric static protocols `SupportsComplex`, `SupportsFloat`, etc. work well for
  static typing, but are unreliable for runtime type checking when complex numbers are
  involved.

## Summary

The typing map is the key to making sense of this chapter.  After a brief introduction to
the four approaches to typing, we contrasted dynamic and static protocols, which
respectively support duck typing and static duck typing.  Both kinds of protocols share
the essential characteristic that a class is never required to explicitly declare
support for any specific protocol.  A class supports a protocol simply by implementing
the necessary methods.

In [Programming Ducks](#programming-ducks), we explored the lengths to which the Python
interpreter goes to make the sequence and iterable dynamic protocols work, including
partial implementations of both.  We then saw how a class can be made to implement a
protocol at runtime through the addition of extra methods via monkey patching.  The duck
typing section ended with hints for defensive programming, including detection of
structural types without explicit `isinstance` or `hasattr` checks using `try`/`except`
and failing fast.

After Alex Martelli's case for goose typing, we saw how to subclass existing ABCs,
surveyed important ABCs in the standard library, and created an ABC from scratch, which
we then implemented by traditional subclassing and by registration.  To close that
section, we saw how the `__subclasshook__()` special method enables ABCs to support
structural typing by recognizing unrelated classes that provide methods fulfilling the
interface defined in the ABC.

In [Static Protocols](#static-protocols), we resumed coverage of static duck typing.  We
saw how the `@runtime_checkable` decorator also leverages `__subclasshook__()` to support
structural typing at runtime — even though the best use of static protocols is with
static type checkers, which can take into account type hints to make structural typing
more reliable.  Next we talked about the design and coding of a static protocol and how
to extend it.  The chapter ended with the sad story of the derelict state of the numeric
tower and a few shortcomings of the proposed alternative: the numeric static protocols
such as `SupportsFloat`.

The main message of this chapter is that we have four complementary ways of programming
with interfaces in modern Python, each with different advantages and drawbacks.  You are
likely to find suitable use cases for each typing scheme in any modern Python codebase of
significant size.  Rejecting any one of these approaches will make your work as a Python
programmer harder than it needs to be.

Having said that, Python achieved widespread popularity while supporting only duck
typing.  Other popular languages such as JavaScript, PHP and Ruby, as well as Lisp,
Smalltalk, Erlang and Clojure — not popular but very influential — are all languages that
had and still have tremendous impact by leveraging the power and simplicity of duck
typing.

> **Note**
>
> Python's static typing followed a "minimum viable product" strategy.  First,
> [**PEP 3107**](https://peps.python.org/pep-3107/) added function annotations in Python
> 3.0 with no semantics at all, to allow experimentation.  Eight years later,
> [**PEP 484**](https://peps.python.org/pep-0484/) added the `typing` module with
> nominal types and generics, but no protocols.  Then came variable annotations
> (PEP 526), generic built-in collections (PEP 585), protocols (PEP 544), `X | Y` unions
> (PEP 604), the type parameter syntax (PEP 695) and lazy annotations (PEP 649), each step
> guided by feedback from real use.  Incremental progress turned out to be safer than a
> big-bang release.

> **See also**
>
> * Glyph Lefkowitz, ["I Want A New Duck: `typing.Protocol` and the future of duck
>   typing"](https://glyph.twistedmatrix.com/2020/07/new-duck.html), a quick look at
>   typing pros and cons and the importance of `typing.Protocol`.
> * The Mypy documentation chapter
>   ["Protocols and structural subtyping"](https://mypy.readthedocs.io/en/stable/protocols.html).
> * Martin Fowler, ["Dynamic Typing"](https://martinfowler.com/bliki/DynamicTyping.html)
>   and ["Role Interface"](https://martinfowler.com/bliki/RoleInterface.html).
> * [**PEP 3119**](https://peps.python.org/pep-3119/) — Introducing Abstract Base Classes
>   gives the rationale for ABCs; [**PEP 3141**](https://peps.python.org/pep-3141/)
>   presents the ABCs of the `numbers` module.
> * The [`abc`](https://docs.python.org/3/library/abc.html) and
>   [`collections.abc`](https://docs.python.org/3/library/collections.abc.html) module
>   documentation.
> * Because each of the fundamental collection ABCs extends `Collection`, which in turn
>   extends multiple ABCs, multiple inheritance is practically inevitable when using
>   ABCs.  Therefore, [Inheritance: For Better or for Worse](inheritance.md) is an
>   important follow-up to this chapter.
