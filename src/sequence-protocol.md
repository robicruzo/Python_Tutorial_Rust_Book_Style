# Special Methods for Sequences

"Don't check whether it *is*-a duck: check whether it *quacks*-like-a duck,
*walks*-like-a duck, etc., etc., depending on exactly what subset of duck-like
behavior you need," Alex Martelli wrote on comp.lang.python in July 2000.  That
attitude is the heart of this chapter.

Here we create a class to represent a multidimensional `Vector`, a significant step
up from the two-dimensional `Vector2d` of [A Pythonic Object](pythonic-object.md).
`Vector` will behave like a standard Python immutable flat sequence.  Its elements
will be floats, and by the end of this chapter it will support:

* the basic sequence protocol: `__len__()` and `__getitem__()`;
* safe representation of instances with many items;
* proper slicing support, producing new `Vector` instances;
* aggregate hashing, taking into account every contained element value;
* a custom formatting language extension.

We'll also implement dynamic attribute access with `__getattr__()` as a way of
replacing the read-only properties we used in `Vector2d`, although this is not typical
of sequence types.  The code-intensive presentation will be interrupted by a
conceptual discussion of protocols as informal interfaces: how protocols and duck
typing are related, and the practical implications when you create your own types.

## `Vector`: A User-Defined Sequence Type

Our strategy to implement `Vector` will be to use composition, not inheritance.  We'll
store the components in an array of floats, and implement the methods needed for our
`Vector` to behave like an immutable flat sequence.  But before implementing the
sequence methods, let's make sure we have a baseline implementation of `Vector` that
is compatible with our earlier `Vector2d` class, except where such compatibility
would not make sense.

> **Note**
>
> Who needs a vector with 1,000 dimensions?  *N*-dimensional vectors (with large
> values of *N*) are widely used in information retrieval, where documents and text
> queries are represented as vectors, with one dimension per word.  This is called the
> *vector space model*.  In this model, a key relevance metric is the *cosine
> similarity*: the cosine of the angle between the vector representing the query and
> the vector representing the document.  As the angle decreases, the cosine approaches
> the maximum value of 1, and so does the relevance of the document to the query.
> Modern machine learning uses high-dimensional vectors ("embeddings") in the same
> way.  Our `Vector` class is a didactic example; NumPy and SciPy are the tools you
> need for real-world vector math.

## `Vector` Take #1: `Vector2d` Compatible

The first version of `Vector` should be as compatible as possible with `Vector2d`.
However, by design, the `Vector` constructor is not compatible with the `Vector2d`
constructor.  We could make `Vector(3, 4)` and `Vector(3, 4, 5)` work by taking
arbitrary arguments with `*args` in `__init__()`, but the best practice for a sequence
constructor is to take the data as an iterable argument, as all built-in sequence types
do.  Here are some ways of instantiating our new `Vector` objects:

<!-- nocheck -->
```python
Vector([3.1, 4.2])
# Vector([3.1, 4.2])
Vector((3, 4, 5))
# Vector([3.0, 4.0, 5.0])
Vector(range(10))
# Vector([0.0, 1.0, 2.0, 3.0, 4.0, ...])
```

Apart from the new constructor signature, every test done with `Vector2d` (e.g.,
`Vector2d(3, 4)`) should pass and produce the same result with a two-component
`Vector([3, 4])`.

> **Warning**
>
> When a `Vector` has more than six components, the string produced by `repr()` is
> abbreviated with `...`, as seen in the last line above.  This is crucial in any
> collection type that may contain a large number of items, because `repr` is used for
> debugging, and you don't want a single large object to span thousands of lines in
> your console or log.  Use the [`reprlib`](https://docs.python.org/3/library/reprlib.html)
> module to produce limited-length representations, as below.

Here is the first version of `Vector`, building on the code of `Vector2d`:

```python
from array import array
import reprlib
import math

class Vector:
    typecode = 'd'

    def __init__(self, components):
        self._components = array(self.typecode, components)

    def __iter__(self):
        return iter(self._components)

    def __repr__(self):
        components = reprlib.repr(self._components)
        components = components[components.find('['):-1]
        return f'Vector({components})'

    def __str__(self):
        return str(tuple(self))

    def __bytes__(self):
        return (bytes([ord(self.typecode)]) +
                bytes(self._components))

    def __eq__(self, other):
        return tuple(self) == tuple(other)

    def __abs__(self):
        return math.hypot(*self)

    def __bool__(self):
        return bool(abs(self))

    @classmethod
    def frombytes(cls, octets):
        typecode = chr(octets[0])
        memv = memoryview(octets[1:]).cast(typecode)
        return cls(memv)

Vector([3.1, 4.2])
# Vector([3.1, 4.2])
Vector((3, 4, 5))
# Vector([3.0, 4.0, 5.0])
Vector(range(10))
# Vector([0.0, 1.0, 2.0, 3.0, 4.0, ...])
```

The `self._components` instance "protected" attribute holds an `array` with the
`Vector` components.  To allow iteration, `__iter__()` returns an iterator over
`self._components` (the `iter()` function is covered in
[Iterators, Generators, and Classic Coroutines](iterators-generators.md)).
`__repr__()` uses `reprlib.repr()` to get a limited-length representation of
`self._components` (e.g., `array('d', [0.0, 1.0, 2.0, 3.0, 4.0, ...])`), and then
removes the `array('d',` prefix and the trailing `)` before plugging the string into a
`Vector` constructor call.  `__bytes__()` builds a `bytes` object directly from
`self._components`.  `math.hypot` accepts *N*-dimensional points (since Python 3.8;
before that you'd write `math.sqrt(sum(x * x for x in self))`).  The only change
needed in `frombytes` is in the last line: we pass the `memoryview` directly to the
constructor, without unpacking with `*` as before.

The way `reprlib.repr` is used deserves some elaboration.  That function produces
safe representations of large or recursive structures by limiting the length of the
output string and marking the cut with `'...'`.  We want the `repr` of a `Vector` to
look like `Vector([3.0, 4.0, 5.0])` and not `Vector(array('d', [3.0, 4.0, 5.0]))`,
because the fact that there is an `array` inside a `Vector` is an implementation
detail.  Because these constructor calls build identical `Vector` objects, the simpler
syntax using a `list` argument is preferable.

When writing `__repr__()`, we could have produced the simplified components display
with `reprlib.repr(list(self._components))`.  However, that would be wasteful,
copying every item from `self._components` to a list just to use the `list` repr.
Instead, `reprlib.repr` is applied to the array directly, and the characters outside
of the `[]` are chopped off.

> **Tip**
>
> Because of its role in debugging, calling `repr()` on an object should never raise an
> exception.  If something goes wrong inside your implementation of `__repr__()`, you
> must deal with the issue and do your best to produce some serviceable output that
> gives the user a chance of identifying the receiver (`self`).

Note that the `__str__()`, `__eq__()` and `__bool__()` methods are unchanged from
`Vector2d`, and only one character was changed in `frombytes` (a `*` was removed in
the last line).  This is one of the benefits of making the original `Vector2d`
iterable.

We could have subclassed `Vector` from `Vector2d`, but there are two reasons not to.
First, the incompatible constructors make subclassing inadvisable; we could work
around that with some clever parameter handling in `__init__()`, but the second
reason is more important: `Vector` should be a standalone example of a class
implementing the sequence protocol.  That's what we'll do next, after a discussion of
the term *protocol*.

## Protocols and Duck Typing

As early as [The Python Data Model](data-model.md), we saw that you don't need to
inherit from any special class to create a fully functional sequence type in Python;
you just need to implement the methods that fulfill the sequence protocol.  But what
kind of protocol are we talking about?

In the context of object-oriented programming, a *protocol* is an informal interface,
defined only in documentation and not in code.  For example, the sequence protocol in
Python entails just the `__len__()` and `__getitem__()` methods.  Any class `Spam`
that implements those methods with the standard signature and semantics can be used
anywhere a sequence is expected.  Whether `Spam` is a subclass of this or that is
irrelevant; all that matters is that it provides the necessary methods.  We saw that
in the `FrenchDeck` class:

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

`FrenchDeck` takes advantage of many Python facilities because it implements the
sequence protocol, even if that is not declared anywhere in the code.  An experienced
Python programmer will look at it and understand that it is a sequence, even though it
subclasses `object`.  We say it *is* a sequence because it *behaves* like one, and
that is what matters.  This became known as *duck typing*, after Alex Martelli's post
quoted at the beginning of this chapter.

Because protocols are informal and unenforced, you can often get away with
implementing just part of a protocol, if you know the specific context where a class
will be used.  For example, to support iteration, only `__getitem__()` is required;
there is no need to provide `__len__()`.  The Data Model documentation itself
suggests that when implementing a class that emulates a built-in type, the emulation
should only be implemented to the degree that makes sense for the object being
modeled: some sequences may work well with retrieval of individual elements, but
extracting a slice may not make sense.  Not having to write nonsense methods just to
fulfill an overdesigned interface makes it easier to keep things simple.

> **Tip**
>
> With [**PEP 544**](https://peps.python.org/pep-0544/), Python supports *protocol
> classes*: the typing constructs from [Static Protocols](type-hints-functions.md#static-protocols).
> This use of the word protocol has a related but different meaning.  When they need
> to be distinguished, we'll write *static protocol* for the protocols formalized in
> protocol classes, and *dynamic protocol* for the traditional sense.  One key
> difference is that static protocol implementations must provide all methods defined
> in the protocol class.  [Two Kinds of Protocols](protocols-abcs.md#two-kinds-of-protocols)
> has more details.

We'll now implement the sequence protocol in `Vector`, initially without proper
support for slicing, then adding it.

## A Sliceable Sequence

As we saw with `FrenchDeck`, supporting the sequence protocol is really easy if you
can delegate to a sequence attribute in your object, like our `self._components`
array.  These `__len__()` and `__getitem__()` one-liners are a good start:

<!-- nocheck -->
```python
class Vector:
    # many lines omitted
    # ...

    def __len__(self):
        return len(self._components)

    def __getitem__(self, index):
        return self._components[index]
```

With these additions, all of these operations now work:

<!-- nocheck -->
```python
v1 = Vector([3, 4, 5])
len(v1)
# 3
v1[0], v1[-1]
# (3.0, 5.0)
v7 = Vector(range(7))
v7[1:4]
# array('d', [1.0, 2.0, 3.0])
```

As you can see, even slicing is supported, but not very well.  It would be better if a
slice of a `Vector` was also a `Vector` instance and not an `array`.  The old
`FrenchDeck` class has a similar problem: when you slice it, you get a `list`.  In the
case of `Vector`, a lot of functionality is lost when slicing produces plain arrays.

Consider the built-in sequence types: every one of them, when sliced, produces a new
instance of its own type, and not of some other type.  To make `Vector` produce slices
as `Vector` instances, we can't just delegate the slicing to `array`.  We need to
analyze the arguments we get in `__getitem__()` and do the right thing.  So let's see
how Python turns the syntax `my_seq[1:3]` into arguments for `my_seq.__getitem__(...)`.

### How Slicing Works

A demo is worth a thousand words:

```python
class MySeq:
    def __getitem__(self, index):
        return index  # for this demonstration, __getitem__ returns whatever is passed

s = MySeq()
s[1]  # a single index, nothing new
# 1
s[1:4]  # the notation 1:4 becomes slice(1, 4, None)
# slice(1, 4, None)
s[1:4:2]  # start at 1, stop at 4, step by 2
# slice(1, 4, 2)
s[1:4:2, 9]  # surprise: commas inside the [] mean __getitem__ receives a tuple
# (slice(1, 4, 2), 9)
s[1:4:2, 7:9]  # the tuple may even hold several slice objects
# (slice(1, 4, 2), slice(7, 9, None))
```

Now let's take a closer look at `slice` itself:

```python
slice  # slice is a built-in type
# <class 'slice'>
sorted(name for name in dir(slice) if not name.startswith('__'))
# ['indices', 'start', 'step', 'stop']
```

Inspecting a `slice`, we find the data attributes `start`, `stop` and `step`, and an
`indices` method.  That method is very interesting but little known.  Here is what
`help(slice.indices)` reveals:

```text
S.indices(len) -> (start, stop, stride)

Assuming a sequence of length len, calculate the start and stop indices,
and the stride length of the extended slice described by S. Out-of-bounds
indices are clipped in a manner consistent with handling of normal slices.
```

In other words, `indices` exposes the tricky logic that's implemented in the built-in
sequences to gracefully handle missing or negative indices and slices that are longer
than the original sequence.  This method produces "normalized" tuples of nonnegative
`start`, `stop` and `stride` integers tailored to a sequence of the given length.
Here are a couple of examples, considering a sequence of `len == 5`, e.g., `'ABCDE'`:

```python
slice(None, 10, 2).indices(5)  # 'ABCDE'[:10:2] is the same as 'ABCDE'[0:5:2]
# (0, 5, 2)
slice(-3, None, None).indices(5)  # 'ABCDE'[-3:] is the same as 'ABCDE'[2:5:1]
# (2, 5, 1)
```

In our `Vector` code, we won't need `slice.indices()`, because when we get a slice
argument we'll delegate its handling to the `_components` array.  But if you can't
count on the services of an underlying sequence, this method can be a huge time saver.

### A Slice-Aware `__getitem__`

These are the two methods needed to make `Vector` behave as a sequence, with
`__getitem__()` now implemented to handle slicing correctly:

<!-- nocheck -->
```python
def __len__(self):
    return len(self._components)

def __getitem__(self, key):
    if isinstance(key, slice):
        cls = type(self)
        return cls(self._components[key])
    index = operator.index(key)
    return self._components[index]
```

If the `key` argument is a `slice`, we get the class of the instance (i.e., `Vector`)
and invoke it to build another `Vector` instance from a slice of the `_components`
array.  Otherwise, if we can get an index from `key`, we return the specific item from
`_components`.

The [`operator.index()`](https://docs.python.org/3/library/operator.html#operator.index)
function calls the `__index__()` special method.  The function and the special method
were defined in [**PEP 357**](https://peps.python.org/pep-0357/), proposed by Travis
Oliphant to allow any of the numerous types of integers in NumPy to be used as indexes
and slice arguments.  The key difference between `operator.index()` and `int()` is that
the former is intended for this specific purpose.  For example, `int(3.14)` returns
`3`, but `operator.index(3.14)` raises `TypeError`, because a `float` should not be
used as an index.

> **Note**
>
> Excessive use of `isinstance` may be a sign of bad object-oriented design, but
> handling slices in `__getitem__()` is a justified use case.  Using `operator.index`
> instead of an `isinstance` test for integers is more flexible, and it raises
> `TypeError` with a very informative message if we can't get an index from `key`, as
> the last test below shows.

With that code added to the `Vector` class, we have proper slicing behavior:

<!-- nocheck -->
```python
v7 = Vector(range(7))
v7[-1]  # an integer index retrieves just one component value as a float
# 6.0
v7[1:4]  # a slice index creates a new Vector
# Vector([1.0, 2.0, 3.0])
v7[-1:]  # a slice of len == 1 also creates a Vector
# Vector([6.0])
v7[1,2]  # Vector does not support multidimensional indexing
# Traceback (most recent call last):
#   ...
# TypeError: 'tuple' object cannot be interpreted as an integer
```

## Dynamic Attribute Access

In the evolution from `Vector2d` to `Vector`, we lost the ability to access vector
components by name (e.g., `v.x`, `v.y`).  We are now dealing with vectors that may
have a large number of components.  Still, it may be convenient to access the first few
components with shortcut letters such as `x`, `y`, `z` instead of `v[0]`, `v[1]` and
`v[2]`.  Here is the alternative syntax we want to provide for reading the first four
components of a vector:

<!-- nocheck -->
```python
v = Vector(range(10))
v.x
# 0.0
v.y, v.z, v.t
# (1.0, 2.0, 3.0)
```

In `Vector2d`, we provided read-only access to `x` and `y` using the `@property`
decorator.  We could write four properties in `Vector`, but it would be tedious.  The
`__getattr__()` special method provides a better way.

The `__getattr__()` method is invoked by the interpreter when attribute lookup fails.
In simple terms, given the expression `my_obj.x`, Python checks whether the `my_obj`
instance has an attribute named `x`; if not, the search goes to the class
(`my_obj.__class__`), and then up the inheritance graph.  If the `x` attribute is not
found, then the `__getattr__()` method defined in the class of `my_obj` is called with
`self` and the name of the attribute as a string (e.g., `'x'`).  (Attribute lookup is
more complicated than this; the gory details are in
[Dynamic Attributes and Properties](dynamic-attributes.md).  For now, this simplified
explanation will do.)

Here is our `__getattr__()` method.  Essentially, it checks whether the attribute being
sought is one of the letters `xyzt` and, if so, returns the corresponding vector
component:

<!-- nocheck -->
```python
__match_args__ = ('x', 'y', 'z', 't')

def __getattr__(self, name):
    cls = type(self)
    try:
        pos = cls.__match_args__.index(name)
    except ValueError:
        pos = -1
    if 0 <= pos < len(self._components):
        return self._components[pos]
    msg = f'{cls.__name__!r} object has no attribute {name!r}'
    raise AttributeError(msg)
```

We set `__match_args__` to allow positional pattern matching on the dynamic attributes
supported by `__getattr__()`.  (It does double duty: it supports positional patterns in
`case` clauses, and it holds the names of the dynamic attributes supported by special
logic in `__getattr__()` and `__setattr__()`.)  `__getattr__()` gets the `Vector` class
for later use, and tries to get the position of `name` in `__match_args__`;
`.index(name)` raises `ValueError` when `name` is not found, so we set `pos` to `-1`.
(A method like `str.find` would be nicer here, but `tuple` doesn't implement it.)  If
`pos` is within range of the available components, we return the component; otherwise
we raise `AttributeError` with a standard message text.

It's not hard to implement `__getattr__()`, but in this case it's not enough.
Consider this bizarre interaction:

<!-- nocheck -->
```python
v = Vector(range(5))
v
# Vector([0.0, 1.0, 2.0, 3.0, 4.0])
v.x  # access element v[0] as v.x
# 0.0
v.x = 10  # assign a new value to v.x; this should raise an exception
v.x  # reading v.x shows the new value, 10
# 10
v  # however, the vector components did not change
# Vector([0.0, 1.0, 2.0, 3.0, 4.0])
```

Can you explain what is happening?  In particular, why does `v.x` return `10` the
second time, if that value is not in the vector components array?  If you don't know
right away, study the explanation of `__getattr__()` given above.  It's a bit subtle,
but a very important foundation to understand a lot of what comes later.

After you've given it some thought, read on.  The inconsistency was introduced because
of the way `__getattr__()` works: Python only calls that method as a fallback, when the
object does not have the named attribute.  However, after we assign `v.x = 10`, the `v`
object now has an `x` attribute, so `__getattr__()` is no longer called to retrieve
`v.x`: the interpreter just returns the value `10` that is bound to `v.x`.  On the other
hand, our implementation of `__getattr__()` pays no attention to instance attributes
other than `self._components`, from where it retrieves the values of the "virtual
attributes" listed in `__match_args__`.

We need to customize the logic for setting attributes in our `Vector` class to avoid
this inconsistency.  Recall that trying to assign to the `.x` or `.y` attributes of a
`Vector2d` raised `AttributeError`.  In `Vector`, we want the same exception with any
attempt at assigning to all single-letter lowercase attribute names, just to avoid
confusion.  To do that, we implement `__setattr__()`:

<!-- nocheck -->
```python
def __setattr__(self, name, value):
    cls = type(self)
    if len(name) == 1:
        if name in cls.__match_args__:
            error = 'readonly attribute {attr_name!r}'
        elif name.islower():
            error = "can't set attributes 'a' to 'z' in {cls_name!r}"
        else:
            error = ''
        if error:
            msg = error.format(cls_name=cls.__name__, attr_name=name)
            raise AttributeError(msg)
    super().__setattr__(name, value)
```

Single-character attribute names get special handling.  If `name` is one of
`__match_args__`, we set a specific error message; if `name` is lowercase, an error
message about all single-letter names; otherwise, a blank error message.  If there is a
nonblank error message, we raise `AttributeError`.  In the default case, we call
`__setattr__()` on the superclass for standard behavior.

> **Tip**
>
> The [`super()`](https://docs.python.org/3/library/functions.html#super) function
> provides a way to access methods of superclasses dynamically, a necessity in a
> dynamic language supporting multiple inheritance like Python.  It's used to delegate
> some task from a method in a subclass to a suitable method in a superclass, as here.
> There is more about `super` in
> [Multiple Inheritance and Method Resolution Order](inheritance.md#multiple-inheritance-and-method-resolution-order).

When choosing the error message to display, it helps to look at the behavior of the
built-in `complex` type, because complex numbers are immutable and have a pair of data
attributes, `real` and `imag`.  Trying to change either raises `AttributeError`, and
trying to set a read-only property, as in `Vector2d`, produces a similar message.  The
messages above are inspired by both, but more explicit about the forbidden attributes.

Note that we are not disallowing setting all attributes, only single-letter lowercase
ones, to avoid confusion with the supported read-only attributes `x`, `y`, `z` and `t`.

> **Warning**
>
> Knowing that declaring `__slots__` at the class level prevents setting new instance
> attributes, it's tempting to use that feature instead of implementing
> `__setattr__()` as we did.  However, because of all the caveats discussed in
> [Summarizing the Issues with `__slots__`](pythonic-object.md#summarizing-the-issues-with-__slots__),
> using `__slots__` just to prevent instance attribute creation is not recommended.
> `__slots__` should be used only to save memory, and only if that is a real issue.

Even without supporting writing to the `Vector` components, here is an important
takeaway from this example: very often when you implement `__getattr__()`, you need to
write `__setattr__()` as well, to avoid inconsistent behavior in your objects.

If we wanted to allow changing components, we could implement `__setitem__()` to
enable `v[0] = 1.1` and/or `__setattr__()` to make `v.x = 1.1` work.  But `Vector` will
remain immutable, because we want to make it hashable in the coming section.

## Hashing and a Faster `==`

Once more we get to implement a `__hash__()` method.  Together with the existing
`__eq__()`, it will make `Vector` instances hashable.

The `__hash__()` of `Vector2d` computed the hash of a tuple built with the two
components, `self.x` and `self.y`.  Now we may be dealing with thousands of components,
so building a tuple may be too costly.  Instead, we will apply the `^` (xor) operator to
the hashes of every component in succession, like this: `v[0] ^ v[1] ^ v[2]`.  That is
what the `functools.reduce` function is for.  `reduce` is not as popular as it used to
be, but computing the hash of all vector components is a good use case for it.

So far we've seen that `functools.reduce()` can be replaced by `sum()`; now let's
properly explain how it works.  The key idea is to *reduce* a series of values to a
single value, as `sum`, `any` and `all` also do.  The first argument to `reduce()` is a
two-argument function, and the second argument is an iterable.  Say we have a
two-argument function `fn` and a list `lst`.  When you call `reduce(fn, lst)`, `fn` is
applied to the first pair of elements, `fn(lst[0], lst[1])`, producing a first result,
`r1`.  Then `fn` is applied to `r1` and the next element, `fn(r1, lst[2])`, producing a
second result, `r2`.  Now `fn(r2, lst[3])` is called to produce `r3`, and so on until
the last element, when a single result, `rN`, is returned.  Here is how you could use
`reduce` to compute 5! (the factorial of 5):

```python
2 * 3 * 4 * 5  # the result we want: 5! == 120
# 120
import functools
functools.reduce(lambda a,b: a*b, range(1, 6))
# 120
```

Back to our hashing problem: here are three ways of computing the aggregate xor of the
integers from 0 to 5, with a `for` loop and with two `reduce` calls:

```python
n = 0
for i in range(1, 6):  # aggregate xor with a for loop and an accumulator variable
    n ^= i

n
# 1
import functools
functools.reduce(lambda a, b: a^b, range(6))  # reduce with an anonymous function
# 1
import operator
functools.reduce(operator.xor, range(6))  # reduce with operator.xor instead of lambda
# 1
```

Of those alternatives, the last one is arguably the best, and the `for` loop comes
second.  What is your preference?  As you saw in
[The `operator` Module](first-class-functions.md#the-operator-module), `operator`
provides the functionality of all Python infix operators in function form, lessening
the need for `lambda`.  To write `Vector.__hash__()` in that style, we need to import
the `functools` and `operator` modules:

<!-- nocheck -->
```python
from array import array
import reprlib
import math
import functools
import operator

class Vector:
    typecode = 'd'

    # many lines omitted in book listing...

    def __eq__(self, other):
        return tuple(self) == tuple(other)

    def __hash__(self):
        hashes = (hash(x) for x in self._components)
        return functools.reduce(operator.xor, hashes, 0)

    # more lines omitted...
```

We import `functools` to use `reduce`, and `operator` to use `xor`.  There's no change
to `__eq__()`; it's listed here because it's good practice to keep `__eq__()` and
`__hash__()` close in source code, since they need to work together.  `__hash__()`
creates a generator expression to lazily compute the hash of each component, and feeds
the hashes to `reduce` with the `xor` function to compute the aggregate hash code; the
third argument, `0`, is the initializer.

> **Warning**
>
> When using `reduce`, it's good practice to provide the third argument,
> `reduce(function, iterable, initializer)`, to prevent this exception:
> `TypeError: reduce() of empty iterable with no initial value` (an excellent message:
> it explains the problem and how to fix it).  The `initializer` is the value returned
> if the sequence is empty, and it is used as the first argument in the reducing loop,
> so it should be the identity value of the operation.  For example, for `+`, `|` and
> `^` the `initializer` should be `0`, but for `*` and `&` it should be `1`.

As implemented, `__hash__()` is a perfect example of a *map-reduce* computation: apply
a function to each item to generate a new series (map), then compute the aggregate
(reduce).  The mapping step produces one hash for each component, and the reduce step
aggregates all hashes with the `xor` operator.  Using `map` instead of a genexp makes
the mapping step even more visible:

<!-- nocheck -->
```python
def __hash__(self):
    hashes = map(hash, self._components)
    return functools.reduce(operator.xor, hashes)
```

(In Python 3, `map` is lazy: it creates an iterator that yields the results on demand,
thus saving memory, just like a generator expression.)

While we are on the topic of reducing functions, we can replace our quick
implementation of `__eq__()` with one that is cheaper in terms of processing and
memory, at least for large vectors.  We have this very concise implementation:

<!-- nocheck -->
```python
def __eq__(self, other):
    return tuple(self) == tuple(other)
```

This works for `Vector2d` and for `Vector`; it even considers `Vector([1, 2])` equal to
`(1, 2)`, which may be a problem, but we'll overlook that for now (it is taken up in
[Operator Overloading 101](operator-overloading.md#operator-overloading-101)).  But for
`Vector` instances that may have thousands of components, it's very inefficient.  It
builds two tuples copying the entire contents of the operands just to use the
`__eq__()` of the `tuple` type.  For `Vector2d` (with only two components), it's a good
shortcut, but not for large multidimensional vectors.  A better way of comparing one
`Vector` to another `Vector` or iterable is this:

<!-- nocheck -->
```python
def __eq__(self, other):
    if len(self) != len(other):
        return False
    for a, b in zip(self, other):
        if a != b:
            return False
    return True
```

If the lengths of the objects are different, they are not equal.  `zip` produces a
generator of tuples made from the items in each iterable argument; the length check is
needed because `zip` stops producing values without warning as soon as one of the
inputs is exhausted.  As soon as two components are different, we exit, returning
`False`; otherwise, the objects are equal.  (The `zip` function is named after the
zipper fastener, because the physical device works by interlocking pairs of teeth taken
from both sides, a good visual analogy for what `zip(left, right)` does.  No relation to
compressed files.)

That version is efficient, but the `all` function can produce the same aggregate
computation as the `for` loop in one line: if all comparisons between corresponding
components in the operands are `True`, the result is `True`; as soon as one comparison
is `False`, `all` returns `False`:

<!-- nocheck -->
```python
def __eq__(self, other):
    return len(self) == len(other) and all(a == b for a, b in zip(self, other))
```

Note that we first check that the operands have equal length, because `zip` will stop
at the shortest operand.  This is the implementation we choose for `__eq__()`.

### The Awesome `zip`

Having a `for` loop that iterates over items without fiddling with index variables is
great and prevents lots of bugs, but it demands some special utility functions.  One of
them is the [`zip`](https://docs.python.org/3/library/functions.html#zip) built-in,
which makes it easy to iterate in parallel over two or more iterables by returning
tuples that you can unpack into variables, one for each item in the parallel inputs:

```python
zip(range(3), 'ABC')  # zip returns an iterator that produces tuples on demand
# <zip object at 0x10063ae48>
list(zip(range(3), 'ABC'))  # build a list just for display
# [(0, 'A'), (1, 'B'), (2, 'C')]
list(zip(range(3), 'ABC', [0.0, 1.1, 2.2, 3.3]))  # zip stops at the shortest iterable
# [(0, 'A', 0.0), (1, 'B', 1.1), (2, 'C', 2.2)]
from itertools import zip_longest
list(zip_longest(range(3), 'ABC', [0.0, 1.1, 2.2, 3.3], fillvalue=-1))
# [(0, 'A', 0.0), (1, 'B', 1.1), (2, 'C', 2.2), (-1, -1, 3.3)]
```

`zip` stops without warning when one of the iterables is exhausted.  The
`itertools.zip_longest` function behaves differently: it uses an optional `fillvalue`
(`None` by default) to complete missing values, so it can generate tuples until the
last iterable is exhausted.

> **Tip**
>
> Silently stopping at the shortest iterable can cause subtle bugs.
> [**PEP 618**](https://peps.python.org/pep-0618/) added an optional `strict` argument
> to `zip` (Python 3.10+): with `strict=True`, `zip` raises `ValueError` if the
> iterables are not all of the same length, in line with Python's fail-fast policy.
>
> ```python
> list(zip('ABC', range(2), strict=True))
> # Traceback (most recent call last):
> #   ...
> # ValueError: zip() argument 2 is shorter than argument 1
> ```

The `zip` function can also be used to transpose a matrix represented as nested
iterables:

```python
a = [(1, 2, 3),
     (4, 5, 6)]
list(zip(*a))
# [(1, 4), (2, 5), (3, 6)]
b = [(1, 2),
     (3, 4),
     (5, 6)]
list(zip(*b))
# [(1, 3, 5), (2, 4, 6)]
```

If you want to grok `zip`, spend some time figuring out how these examples work.  The
`enumerate` built-in is another generator function often used in `for` loops to avoid
direct handling of index variables (see [Looping Techniques](datastructures.md#tut-loopidioms)).
Both, along with several other generator functions in the standard library, are covered
in [Generator Functions in the Standard Library](iterators-generators.md#generator-functions-in-the-standard-library).

## Formatting

The `__format__()` method of `Vector` will resemble that of `Vector2d`, but instead of
providing a custom display in polar coordinates, `Vector` will use spherical
coordinates, also known as "hyperspherical" coordinates, because now we support *n*
dimensions, and spheres are "hyperspheres" in 4D and beyond.  Accordingly, we'll change
the custom format suffix from `'p'` to `'h'`.

> **Tip**
>
> As explained in [Formatted Displays](pythonic-object.md#formatted-displays), when
> extending the Format Specification Mini-Language it's best to avoid reusing format
> codes supported by built-in types.  Our extended mini-language also uses the float
> formatting codes `'eEfFgGn%'` in their original meaning, so we must avoid these.
> Integers use `'bcdoxXn'` and strings use `'s'`.  `'p'` was used for `Vector2d` polar
> coordinates; `'h'` for hyperspherical coordinates is a good choice.

For example, given a `Vector` object in 4D space (`len(v) == 4`), the `'h'` code will
produce a display like `<r, Φ₁, Φ₂, Φ₃>`, where `r` is the magnitude (`abs(v)`), and the
remaining numbers are the angular components Φ₁, Φ₂, Φ₃.  Here are some samples:

<!-- nocheck -->
```python
format(Vector([-1, -1, -1, -1]), 'h')
# '<2.0, 2.0943951023931957, 2.186276035465284, 3.9269908169872414>'
format(Vector([2, 2, 2, 2]), '.3eh')
# '<4.000e+00, 1.047e+00, 9.553e-01, 7.854e-01>'
format(Vector([0, 1, 0, 0]), '0.5fh')
# '<1.00000, 1.57080, 0.00000, 0.00000>'
```

Before we can implement the minor changes required in `__format__()`, we need a pair
of support methods: `angle(n)` to compute one of the angular coordinates (e.g., Φ₁),
and `angles()` to return an iterable of all angular coordinates.  The math is not
explained here; if you're curious, the "n-sphere" entry in Wikipedia has the formulas
used to calculate the spherical coordinates from the Cartesian coordinates.

Here is the full listing of `vector_v5.py`, consolidating everything implemented since
[`Vector` Take #1](#vector-take-1-vector2d-compatible) and introducing custom
formatting:

```python
"""
A multidimensional ``Vector`` class, take 5
"""

from array import array
import reprlib
import math
import functools
import operator
import itertools

class Vector:
    typecode = 'd'

    def __init__(self, components):
        self._components = array(self.typecode, components)

    def __iter__(self):
        return iter(self._components)

    def __repr__(self):
        components = reprlib.repr(self._components)
        components = components[components.find('['):-1]
        return f'Vector({components})'

    def __str__(self):
        return str(tuple(self))

    def __bytes__(self):
        return (bytes([ord(self.typecode)]) +
                bytes(self._components))

    def __eq__(self, other):
        return (len(self) == len(other) and
                all(a == b for a, b in zip(self, other)))

    def __hash__(self):
        hashes = (hash(x) for x in self)
        return functools.reduce(operator.xor, hashes, 0)

    def __abs__(self):
        return math.hypot(*self)

    def __bool__(self):
        return bool(abs(self))

    def __len__(self):
        return len(self._components)

    def __getitem__(self, key):
        if isinstance(key, slice):
            cls = type(self)
            return cls(self._components[key])
        index = operator.index(key)
        return self._components[index]

    __match_args__ = ('x', 'y', 'z', 't')

    def __getattr__(self, name):
        cls = type(self)
        try:
            pos = cls.__match_args__.index(name)
        except ValueError:
            pos = -1
        if 0 <= pos < len(self._components):
            return self._components[pos]
        msg = f'{cls.__name__!r} object has no attribute {name!r}'
        raise AttributeError(msg)

    def __setattr__(self, name, value):
        cls = type(self)
        if len(name) == 1:
            if name in cls.__match_args__:
                error = 'readonly attribute {attr_name!r}'
            elif name.islower():
                error = "can't set attributes 'a' to 'z' in {cls_name!r}"
            else:
                error = ''
            if error:
                msg = error.format(cls_name=cls.__name__, attr_name=name)
                raise AttributeError(msg)
        super().__setattr__(name, value)

    def angle(self, n):
        r = math.hypot(*self[n:])
        a = math.atan2(r, self[n-1])
        if (n == len(self) - 1) and (self[-1] < 0):
            return math.pi * 2 - a
        else:
            return a

    def angles(self):
        return (self.angle(n) for n in range(1, len(self)))

    def __format__(self, fmt_spec=''):
        if fmt_spec.endswith('h'):  # hyperspherical coordinates
            fmt_spec = fmt_spec[:-1]
            coords = itertools.chain([abs(self)],
                                     self.angles())
            outer_fmt = '<{}>'
        else:
            coords = self
            outer_fmt = '({})'
        components = (format(c, fmt_spec) for c in coords)
        return outer_fmt.format(', '.join(components))

    @classmethod
    def frombytes(cls, octets):
        typecode = chr(octets[0])
        memv = memoryview(octets[1:]).cast(typecode)
        return cls(memv)
```

The new parts: we import `itertools` to use the `chain` function in `__format__()`.
`angle(n)` computes one of the angular coordinates, using formulas adapted from the
n-sphere article, and `angles()` creates a generator expression to compute all angular
coordinates on demand.  In `__format__()`, we use `itertools.chain` to produce a genexp
that iterates seamlessly over the magnitude and the angular coordinates, and configure
a spherical coordinate display with angle brackets; otherwise, we configure a
Cartesian coordinate display with parentheses.  Then we create a generator expression
to format each coordinate item on demand, and plug the formatted components, separated
by commas, inside the brackets or parentheses.  (We are making heavy use of generator
expressions in `__format__()`, `angle` and `angles`; generators are explained in detail
in [Iterators, Generators, and Classic Coroutines](iterators-generators.md).)

Here are the tests used while developing `vector_v5.py`:

```python
Vector([3.1, 4.2])  # a Vector is built from an iterable of numbers
# Vector([3.1, 4.2])
Vector((3, 4, 5))
# Vector([3.0, 4.0, 5.0])
Vector(range(10))
# Vector([0.0, 1.0, 2.0, 3.0, 4.0, ...])
v1 = Vector([3, 4])  # tests with two dimensions (same results as Vector2d)
x, y = v1
x, y
# (3.0, 4.0)
v1
# Vector([3.0, 4.0])
v1_clone = eval(repr(v1))
v1 == v1_clone
# True
print(v1)
# (3.0, 4.0)
octets = bytes(v1)
octets
# b'd\x00\x00\x00\x00\x00\x00\x08@\x00\x00\x00\x00\x00\x00\x10@'
abs(v1)
# 5.0
bool(v1), bool(Vector([0, 0]))
# (True, False)
v1_clone = Vector.frombytes(bytes(v1))  # test of the .frombytes() class method
v1_clone
# Vector([3.0, 4.0])
v1 == v1_clone
# True
v1 = Vector([3, 4, 5])  # tests with three dimensions
x, y, z = v1
x, y, z
# (3.0, 4.0, 5.0)
v1
# Vector([3.0, 4.0, 5.0])
print(v1)
# (3.0, 4.0, 5.0)
abs(v1)
# 7.0710678118654755
v7 = Vector(range(7))  # tests with many dimensions
v7
# Vector([0.0, 1.0, 2.0, 3.0, 4.0, ...])
abs(v7)
# 9.539392014169456
v1 = Vector([3, 4, 5])  # tests of sequence behavior
len(v1)
# 3
v1[0], v1[len(v1)-1], v1[-1]
# (3.0, 5.0, 5.0)
v7[-1]  # tests of slicing
# 6.0
v7[1:4]
# Vector([1.0, 2.0, 3.0])
v7[-1:]
# Vector([6.0])
v7[1,2]
# Traceback (most recent call last):
#   ...
# TypeError: 'tuple' object cannot be interpreted as an integer
v7 = Vector(range(10))  # tests of dynamic attribute access
v7.x
# 0.0
v7.y, v7.z, v7.t
# (1.0, 2.0, 3.0)
v7.k  # dynamic attribute lookup failures
# Traceback (most recent call last):
#   ...
# AttributeError: 'Vector' object has no attribute 'k'
v3 = Vector(range(3))
v3.t
# Traceback (most recent call last):
#   ...
# AttributeError: 'Vector' object has no attribute 't'
v3.x = 7  # assignment to single-letter attributes is forbidden
# Traceback (most recent call last):
#   ...
# AttributeError: readonly attribute 'x'
v1 = Vector([3, 4])  # tests of hashing
v3 = Vector([3, 4, 5])
v6 = Vector(range(6))
hash(v1), hash(v3), hash(v6)
# (7, 2, 1)
v1 = Vector([3, 4])  # tests of format() with Cartesian coordinates
format(v1)
# '(3.0, 4.0)'
format(v1, '.2f')
# '(3.00, 4.00)'
format(Vector(range(7)))
# '(0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0)'
format(Vector([1, 1]), 'h')  # tests of format() with spherical coordinates
# '<1.4142135623730951, 0.7853981633974483>'
format(Vector([1, 1, 1]), 'h')
# '<1.7320508075688772, 0.9553166181245093, 0.7853981633974483>'
format(Vector([2, 2, 2]), '.3eh')
# '<3.464e+00, 9.553e-01, 7.854e-01>'
format(Vector([0, 0, 0]), '0.5fh')
# '<0.00000, 0.00000, 0.00000>'
format(Vector([-1, -1, -1, -1]), 'h')
# '<2.0, 2.0943951023931957, 2.186276035465284, 3.9269908169872414>'
format(Vector([2, 2, 2, 2]), '.3eh')
# '<4.000e+00, 1.047e+00, 9.553e-01, 7.854e-01>'
format(Vector([0, 1, 0, 0]), '0.5fh')
# '<1.00000, 1.57080, 0.00000, 0.00000>'
```

(Hash codes of most non-integers vary between 32-bit and 64-bit CPython builds, so
`hash(Vector([3.1, 4.2]))` is `384307168202284039` on a 64-bit build but a different
number on a 32-bit build.)

That concludes our mission for this chapter.  `Vector` will be enhanced with infix
operators in [Operator Overloading](operator-overloading.md), but the goal here was to
explore techniques for writing special methods that are useful in a wide variety of
collection classes.

## Summary

The `Vector` example in this chapter was designed to be compatible with `Vector2d`,
except for the use of a different constructor signature accepting a single iterable
argument, just as the built-in sequence types do.  The fact that `Vector` behaves as a
sequence just by implementing `__getitem__()` and `__len__()` prompted a discussion of
protocols, the informal interfaces used in duck-typed languages.

We then looked at how the `my_seq[a:b:c]` syntax works behind the scenes, by creating a
`slice(a, b, c)` object and handing it to `__getitem__()`.  Armed with this knowledge,
we made `Vector` respond correctly to slicing, by returning new `Vector` instances, just
as a Pythonic sequence is expected to do.

The next step was to provide read-only access to the first few `Vector` components
using notation such as `my_vec.x`, by implementing `__getattr__()`.  Doing that opened
the possibility of tempting the user to assign to those special components by writing
`my_vec.x = 7`, revealing a potential bug.  We fixed it by implementing `__setattr__()`
as well, to forbid assigning values to single-letter attributes.  Very often, when you
write a `__getattr__()` you need to add `__setattr__()` too, to avoid inconsistent
behavior.

Implementing the `__hash__()` function provided the perfect context for using
`functools.reduce`, because we needed to apply the xor operator `^` in succession to the
hashes of all `Vector` components to produce an aggregate hash code for the whole
`Vector`.  After applying `reduce` in `__hash__()`, we used the `all` reducing built-in
to create a more efficient `__eq__()` method.

The last enhancement was to reimplement `__format__()` from `Vector2d`, supporting
spherical coordinates as an alternative to the default Cartesian coordinates.  As in
the previous chapter, we often looked at how standard Python objects behave, to emulate
them and provide a "Pythonic" look and feel to `Vector`.

> **Note**
>
> What is the most Pythonic way to sum the *n*th item of each sublist?  A 2003 thread
> on python-list explored `reduce` with a `lambda`, `reduce(operator.add, ...)`, NumPy
> slicing, and a plain `for` loop with an accumulator, which many found the most
> readable.  Alex Martelli then proposed a `sum()` built-in, which appeared in Python
> 2.3 three months later; with generator expressions, added in Python 2.4, the answer
> became `sum(sub[1] for sub in my_list)`.  It reads like "the sum of a list of items",
> and `sum([])` is simply `0`.  That conversation also helped demote `reduce` from a
> built-in to `functools` in Python 3.  Still, `functools.reduce` has its place, as in
> `Vector.__hash__()`.

> **See also**
>
> * The references in [A Pythonic Object](pythonic-object.md#summary) are all relevant
>   here, since most special methods in `Vector` also appear in `Vector2d`.
> * The powerful `reduce` higher-order function is also known as fold, accumulate,
>   aggregate, compress and inject; Wikipedia's "Fold (higher-order function)" article
>   compares fold-like functions in dozens of languages.
> * [**PEP 357**](https://peps.python.org/pep-0357/) details the need for `__index__`
>   from the perspective of an implementor of a C extension: Travis Oliphant, the
>   primary creator of NumPy.
