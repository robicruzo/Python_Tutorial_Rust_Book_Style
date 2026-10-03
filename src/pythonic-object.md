# A Pythonic Object

For a library or framework to be Pythonic, as Martijn Faassen put it, is to make
it as easy and natural as possible for a Python programmer to pick up how to
perform a task.  Thanks to the Python Data Model, your user-defined types can
behave as naturally as the built-in types.  And this can be accomplished without
inheritance, in the spirit of duck typing: you just implement the methods needed
for your objects to behave as expected.

In previous chapters we studied the behavior of many built-in objects.  We will
now build user-defined classes that behave as real Python objects.  Your
application classes probably don't need, and should not implement, as many special
methods as the examples in this chapter.  But if you are writing a library or a
framework, the programmers who will use your classes may expect them to behave like
the classes that Python provides.  Fulfilling that expectation is one way of being
"Pythonic".

This chapter starts where [The Python Data Model](data-model.md) ended, by showing
how to implement several special methods that are commonly seen in Python objects of
many different types.  We will see how to:

* support the built-in functions that convert objects to other types (`repr()`,
  `bytes()`, `complex()`, etc.);
* implement an alternative constructor as a class method;
* extend the format mini-language used by f-strings, the `format()` built-in and
  the `str.format()` method;
* provide read-only access to attributes;
* make an object hashable for use in sets and as `dict` keys;
* save memory with the use of `__slots__`.

We'll do all that as we develop `Vector2d`, a simple two-dimensional Euclidean
vector type.  This code will be the foundation of an *N*-dimensional vector class in
[Special Methods for Sequences](sequence-protocol.md).  Along the way, we'll pause
to discuss two conceptual topics: how and when to use the `@classmethod` and
`@staticmethod` decorators, and private and protected attributes in Python.  The
chapter assumes you have read [Classes](classes.md).

## Object Representations

Every object-oriented language has at least one standard way of getting a string
representation from any object.  Python has two:

`repr()`
: returns a string representing the object as the developer wants to see it.  It's
  what you get when the interactive interpreter or a debugger shows an object.

`str()`
: returns a string representing the object as the user wants to see it.  It's what
  you get when you `print()` an object.

The special methods `__repr__()` and `__str__()` support `repr()` and `str()`, as
you saw in [The Python Data Model](data-model.md#string-representation).

There are two additional special methods to support alternative representations of
objects: `__bytes__()` and `__format__()`.  The `__bytes__()` method is analogous to
`__str__()`: it's called by `bytes()` to get the object represented as a byte
sequence.  `__format__()` is used by f-strings, by the built-in function `format()`,
and by the `str.format()` method.  They call `obj.__format__(format_spec)` to get
string displays of objects using special formatting codes.

> **Note**
>
> `__repr__()`, `__str__()` and `__format__()` must always return Unicode strings
> (type `str`).  Only `__bytes__()` is supposed to return a byte sequence (type
> `bytes`).

## Vector Class Redux

To demonstrate the many methods used to generate object representations, we'll use a
`Vector2d` class similar to the `Vector` of the Data Model chapter.  Here is the
basic behavior we expect from a `Vector2d` instance:

<!-- nocheck -->
```python
v1 = Vector2d(3, 4)
print(v1.x, v1.y)
# 3.0 4.0
x, y = v1
x, y
# (3.0, 4.0)
v1
# Vector2d(3.0, 4.0)
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
bool(v1), bool(Vector2d(0, 0))
# (True, False)
```

Going through those lines:

* The components of a `Vector2d` can be accessed directly as attributes (no getter
  method calls).
* A `Vector2d` can be unpacked to a tuple of variables.
* The `repr` of a `Vector2d` emulates the source code for constructing the instance.
* Using `eval` here shows that the `repr` of a `Vector2d` is a faithful
  representation of its constructor call.  (To clone an instance, `copy.copy` is
  safer and faster; `eval` is used just to make a point.)
* `Vector2d` supports comparison with `==`; this is useful for testing.
* `print` calls `str`, which for `Vector2d` produces an ordered pair display.
* `bytes` uses the `__bytes__()` method to produce a binary representation.
* `abs` uses the `__abs__()` method to return the magnitude of the `Vector2d`.
* `bool` uses the `__bool__()` method to return `False` for a `Vector2d` of zero
  magnitude, or `True` otherwise.

Here is `vector2d_v0.py`, an implementation of that behavior.  It's based on the
`Vector` of the Data Model chapter, without the methods for `+` and `*`, which come
later in [Operator Overloading](operator-overloading.md), but with `==`, since it's
useful for testing.  At this point, every method is a special method:

```python
from array import array
import math

class Vector2d:
    typecode = 'd'

    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def __iter__(self):
        return (i for i in (self.x, self.y))

    def __repr__(self):
        class_name = type(self).__name__
        return '{}({!r}, {!r})'.format(class_name, *self)

    def __str__(self):
        return str(tuple(self))

    def __bytes__(self):
        return (bytes([ord(self.typecode)]) +
                bytes(array(self.typecode, self)))

    def __eq__(self, other):
        return tuple(self) == tuple(other)

    def __abs__(self):
        return math.hypot(self.x, self.y)

    def __bool__(self):
        return bool(abs(self))
```

Point by point:

* `typecode` is a class attribute we'll use when converting `Vector2d` instances
  to and from `bytes`.
* Converting `x` and `y` to `float` in `__init__()` catches errors early, which is
  helpful in case `Vector2d` is called with unsuitable arguments.
* `__iter__()` makes a `Vector2d` iterable; this is what makes unpacking work (as in
  `x, y = my_vector`).  We implement it simply by using a generator expression to
  yield the components one after the other.  (It could also be written as
  `yield self.x; yield self.y`; see [Iterators, Generators, and Classic
  Coroutines](iterators-generators.md).)
* `__repr__()` builds a string by interpolating the components with `{!r}` to get
  their `repr`; because `Vector2d` is iterable, `*self` feeds the `x` and `y`
  components to `format`.
* From an iterable `Vector2d`, it's easy to build a `tuple` for display as an ordered
  pair in `__str__()`.
* To generate `bytes`, we convert the typecode to `bytes` and concatenate the bytes
  converted from an `array` built by iterating over the instance.
* To quickly compare all components, `__eq__()` builds tuples out of the operands.
  This works for operands that are instances of `Vector2d`, but has issues; see the
  warning below.
* The magnitude is the length of the hypotenuse of the right triangle formed by the
  `x` and `y` components.
* `__bool__()` uses `abs(self)` to compute the magnitude, then converts it to
  `bool`, so `0.0` becomes `False`, and nonzero is `True`.

> **Warning**
>
> `__eq__()` works for `Vector2d` operands but also returns `True` when comparing
> `Vector2d` instances to other iterables holding the same numeric values (e.g.,
> `Vector2d(3, 4) == [3, 4]`).  This may be considered a feature or a bug.  The
> discussion continues in [Operator Overloading](operator-overloading.md).

We have a fairly complete set of basic methods, but we still need a way to rebuild a
`Vector2d` from the binary representation produced by `bytes()`.

## An Alternative Constructor

Since we can export a `Vector2d` as bytes, naturally we need a method that imports a
`Vector2d` from a binary sequence.  Looking at the standard library for inspiration,
we find that `array.array` has a class method named `.frombytes` that suits our
purpose; you saw it in [Arrays](sequences.md#arrays).  We adopt its name and use its
functionality in a class method for `Vector2d`:

<!-- nocheck -->
```python
@classmethod
def frombytes(cls, octets):
    typecode = chr(octets[0])
    memv = memoryview(octets[1:]).cast(typecode)
    return cls(*memv)
```

The `classmethod` decorator modifies a method so it can be called directly on a
class.  There's no `self` argument; instead, the class itself is passed as the first
argument, conventionally named `cls`.  The method reads the typecode from the first
byte, creates a `memoryview` from the `octets` binary sequence and uses the typecode
to cast it (see [Memory Views](sequences.md#memory-views)), and unpacks the
`memoryview` resulting from the cast into the pair of arguments needed for the
constructor.

### `classmethod` Versus `staticmethod`

The `classmethod` decorator is a Python-specific feature, and so is `staticmethod`.
Anyone who has learned object-oriented programming in Java may wonder why Python has
both of these decorators and not just one of them.

Let's start with `classmethod`.  Its use above is typical: it defines a method that
operates on the class and not on instances.  `classmethod` changes the way the method
is called, so it receives the class itself as the first argument, instead of an
instance.  Its most common use is for alternative constructors, like `frombytes`.
Note how the last line of `frombytes` actually uses the `cls` argument by invoking it
to build a new instance: `cls(*memv)`.  That way, subclasses get instances of the
subclass, not of `Vector2d`.

In contrast, the `staticmethod` decorator changes a method so that it receives no
special first argument.  In essence, a static method is just like a plain function
that happens to live in a class body, instead of being defined at the module level.
This contrasts the two:

```python
class Demo:
    @classmethod
    def klassmeth(*args):
        return args  # klassmeth just returns all positional arguments
    @staticmethod
    def statmeth(*args):
        return args  # statmeth does the same

Demo.klassmeth()  # no matter how you invoke it, it receives the class first
# (<class '__main__.Demo'>,)
Demo.klassmeth('spam')
# (<class '__main__.Demo'>, 'spam')
Demo.statmeth()  # behaves just like a plain old function
# ()
Demo.statmeth('spam')
# ('spam',)
```

> **Tip**
>
> The `classmethod` decorator is clearly useful, but good use cases for
> `staticmethod` are rare.  Maybe the function is closely related to the class even
> if it never touches it, so you want to place it nearby in the code.  Even then,
> defining the function right before or after the class in the same module is close
> enough most of the time.  Opinions differ on this, so decide for yourself.

Now let's go back to object representation and see how to support formatted output.

## Formatted Displays

F-strings, the `format()` built-in function and the `str.format()` method delegate the
actual formatting to each type by calling its `.__format__(format_spec)` method.  The
`format_spec` is a formatting specifier, which is either:

* the second argument in `format(my_obj, format_spec)`, or
* whatever appears after the colon in a replacement field delimited with `{}` inside
  an f-string or the `fmt` in `fmt.str.format()`.

For example:

```python
brl = 1 / 4.82  # BRL to USD currency conversion rate
brl
# 0.20746887966804978
format(brl, '0.4f')  # the formatting specifier is '0.4f'
# '0.2075'
'1 BRL = {rate:0.2f} USD'.format(rate=brl)  # the specifier is '0.2f'
# '1 BRL = 0.21 USD'
f'1 USD = {1 / brl:0.2f} BRL'  # again '0.2f'; the 1 / brl expression is not part of it
# '1 USD = 4.82 BRL'
```

In the second example, the `rate` part of the replacement field is not part of the
formatting specifier; it determines which keyword argument of `.format()` goes into
that replacement field.  That makes an important point: a format string such as
`'{0.mass:5.3e}'` actually uses two separate notations.  The `'0.mass'` to the left of
the colon is the `field_name` part of the replacement field syntax, and it can be an
arbitrary expression in an f-string.  The `'5.3e'` after the colon is the formatting
specifier.  The notation used in the formatting specifier is called the
[Format Specification Mini-Language](https://docs.python.org/3/library/string.html#formatspec).

> **Tip**
>
> If f-strings, `format()` and `str.format()` are new to you, it's best to study the
> `format()` built-in function first, which uses just the Format Specification
> Mini-Language.  After you get the gist of that, read
> [Formatted string literals](https://docs.python.org/3/reference/lexical_analysis.html#f-strings)
> and [Format String Syntax](https://docs.python.org/3/library/string.html#formatstrings)
> to learn about the `{:}` replacement field notation (including the `!s`, `!r` and
> `!a` conversion flags).  The tutorial covers the basics in
> [Fancier Output Formatting](inputoutput.md#tut-formatting).  F-strings don't make
> `str.format()` obsolete: most of the time f-strings solve the problem, but sometimes
> it's better to specify the formatting string elsewhere, not where it will be
> rendered.

A few built-in types have their own presentation codes in the Format Specification
Mini-Language.  For example, among several other codes, the `int` type supports `b`
and `x` for base 2 and base 16 output, while `float` implements `f` for a fixed-point
display and `%` for a percentage display:

```python
format(42, 'b')
# '101010'
format(2 / 3, '.1%')
# '66.7%'
```

The Format Specification Mini-Language is extensible because each class gets to
interpret the `format_spec` argument as it likes.  For instance, the classes in the
`datetime` module use the same format codes as the `strftime()` functions in their
`__format__()` methods:

```python
from datetime import datetime
now = datetime(2026, 10, 3, 18, 49, 5)
format(now, '%H:%M:%S')
# '18:49:05'
"It's now {:%I:%M %p}".format(now)
# "It's now 06:49 PM"
```

If a class has no `__format__()`, the method inherited from `object` returns
`str(my_object)`.  Because `Vector2d` has a `__str__()`, this works:

```python
v1 = Vector2d(3, 4)
format(v1)
# '(3.0, 4.0)'
```

However, if you pass a format specifier, `object.__format__()` raises `TypeError`:

```python
format(v1, '.3f')
# Traceback (most recent call last):
#   ...
# TypeError: unsupported format string passed to Vector2d.__format__
```

We will fix that by implementing our own format mini-language.  The first step is to
assume the format specifier provided by the user is intended to format each `float`
component of the vector.  This is the result we want:

<!-- nocheck -->
```python
v1 = Vector2d(3, 4)
format(v1)
# '(3.0, 4.0)'
format(v1, '.2f')
# '(3.00, 4.00)'
format(v1, '.3e')
# '(3.000e+00, 4.000e+00)'
```

Here is a `__format__()` method that produces those displays:

<!-- nocheck -->
```python
# inside the Vector2d class

def __format__(self, fmt_spec=''):
    components = (format(c, fmt_spec) for c in self)
    return '({}, {})'.format(*components)
```

It uses the `format` built-in to apply the `fmt_spec` to each vector component,
building an iterable of formatted strings, and plugs the formatted strings into the
formula `'(x, y)'`.

Now let's add a custom formatting code to our mini-language: if the format specifier
ends with a `'p'`, we'll display the vector in polar coordinates: `<r, θ>`, where `r`
is the magnitude and θ (theta) is the angle in radians.  The rest of the format
specifier (whatever comes before the `'p'`) will be used as before.

> **Tip**
>
> When choosing the letter for a custom format code, avoid overlapping with codes used
> by other types.  In the Format Specification Mini-Language, integers use the codes
> `'bcdoxXn'`, floats use `'eEfFgGn%'`, and strings use `'s'`.  So `'p'` is a good
> choice for polar coordinates.  Because each class interprets these codes
> independently, reusing a code letter in a custom format for a new type is not an
> error, but may be confusing to users.

To generate polar coordinates, we already have `__abs__()` for the magnitude, and we
can write a simple `angle` method using the `math.atan2()` function:

<!-- nocheck -->
```python
# inside the Vector2d class

def angle(self):
    return math.atan2(self.y, self.x)
```

With that, we can enhance `__format__()` to produce polar coordinates:

<!-- nocheck -->
```python
def __format__(self, fmt_spec=''):
    if fmt_spec.endswith('p'):
        fmt_spec = fmt_spec[:-1]
        coords = (abs(self), self.angle())
        outer_fmt = '<{}, {}>'
    else:
        coords = self
        outer_fmt = '({}, {})'
    components = (format(c, fmt_spec) for c in coords)
    return outer_fmt.format(*components)
```

If the format ends with `'p'`, we use polar coordinates: we remove the `'p'` suffix
from `fmt_spec`, build a tuple of polar coordinates `(magnitude, angle)`, and
configure the outer format with angle brackets.  Otherwise, we use the `x, y`
components of `self` for rectangular coordinates, with parentheses.  Then we generate
an iterable with the components as formatted strings and plug them into the outer
format.  The results look like this:

<!-- nocheck -->
```python
format(Vector2d(1, 1), 'p')
# '<1.4142135623730951, 0.7853981633974483>'
format(Vector2d(1, 1), '.3ep')
# '<1.414e+00, 7.854e-01>'
format(Vector2d(1, 1), '0.5fp')
# '<1.41421, 0.78540>'
```

As this section shows, it's not hard to extend the Format Specification Mini-Language
to support user-defined types.  Now let's move to a subject that's not just about
appearances: we will make `Vector2d` hashable, so we can build sets of vectors, or use
them as `dict` keys.

## A Hashable `Vector2d`

As defined so far, our `Vector2d` instances are unhashable, so we can't put them in a
`set`:

```python
v1 = Vector2d(3, 4)
hash(v1)
# Traceback (most recent call last):
#   ...
# TypeError: unhashable type: 'Vector2d'
set([v1])
# Traceback (most recent call last):
#   ...
# TypeError: unhashable type: 'Vector2d'
```

(Defining `__eq__()` without `__hash__()` sets `__hash__` to `None`, which is why the
instances are unhashable.)  To make a `Vector2d` hashable, we must implement
`__hash__()` (`__eq__()` is also required, and we already have it).  We also need to
make vector instances immutable, as explained in
[What Is Hashable](dicts-sets.md#what-is-hashable).  Right now, anyone can do
`v1.x = 7`, and there is nothing in the code to suggest that changing a `Vector2d` is
forbidden.  This is the behavior we want:

<!-- nocheck -->
```python
v1.x, v1.y
# (3.0, 4.0)
v1.x = 7
# Traceback (most recent call last):
#   ...
# AttributeError: property 'x' of 'Vector2d' object has no setter
```

We'll do that by making the `x` and `y` components read-only properties:

<!-- nocheck -->
```python
class Vector2d:
    typecode = 'd'

    def __init__(self, x, y):
        self.__x = float(x)
        self.__y = float(y)

    @property
    def x(self):
        return self.__x

    @property
    def y(self):
        return self.__y

    def __iter__(self):
        return (i for i in (self.x, self.y))

    # remaining methods: same as previous Vector2d
```

We use exactly two leading underscores (with zero or one trailing underscore) to make
an attribute private; more on that [below](#private-and-protected-attributes-in-python).
The `@property` decorator marks the getter method of a property, which is named after
the public property it exposes: `x`, which just returns `self.__x`.  The same formula
is repeated for the `y` property.  Every method that just reads the `x`, `y`
components can stay as it was, reading the public properties via `self.x` and
`self.y` instead of the private attributes.

> **Note**
>
> `Vector2d.x` and `Vector2d.y` are examples of read-only properties.  Read/write
> properties are covered in [Dynamic Attributes and Properties](dynamic-attributes.md),
> where we dive deeper into `@property`.

Now that our vectors are reasonably safe from accidental mutation, we can implement
`__hash__()`.  It should return an `int` and ideally take into account the hashes of
the object attributes that are also used in `__eq__()`, because objects that compare
equal should have the same hash.  The documentation of `__hash__()` suggests computing
the hash of a tuple with the components, so that's what we do:

<!-- nocheck -->
```python
# inside class Vector2d:

def __hash__(self):
    return hash((self.x, self.y))
```

With the addition of `__hash__()`, we now have hashable vectors:

<!-- nocheck -->
```python
v1 = Vector2d(3, 4)
v2 = Vector2d(3.1, 4.2)
hash(v1), hash(v2)
# (1079245023883434373, 1994163070182233067)
{v1, v2}
# {Vector2d(3.1, 4.2), Vector2d(3.0, 4.0)}
```

> **Tip**
>
> It's not strictly necessary to implement properties or otherwise protect the
> instance attributes to create a hashable type.  Implementing `__hash__()` and
> `__eq__()` correctly is all it takes.  But the value of a hashable object is never
> supposed to change, so this was a good excuse to talk about read-only properties.

If you are creating a type that has a sensible scalar numeric value, you may also
implement the `__int__()` and `__float__()` methods, invoked by the `int()` and
`float()` constructors, which are used for type coercion in some contexts.  There is
also a `__complex__()` method to support the `complex()` built-in constructor.
Perhaps `Vector2d` should provide `__complex__()`; that's left as an exercise for you.

## Supporting Positional Pattern Matching

So far, `Vector2d` instances are compatible with keyword class patterns (see
[Keyword Class Patterns](pattern-matching.md#keyword-class-patterns)).  All of these
keyword patterns work as expected:

<!-- nocheck -->
```python
def keyword_pattern_demo(v: Vector2d) -> None:
    match v:
        case Vector2d(x=0, y=0):
            print(f'{v!r} is null')
        case Vector2d(x=0):
            print(f'{v!r} is vertical')
        case Vector2d(y=0):
            print(f'{v!r} is horizontal')
        case Vector2d(x=x, y=y) if x==y:
            print(f'{v!r} is diagonal')
        case _:
            print(f'{v!r} is awesome')
```

However, if you try to use a positional pattern like this:

<!-- nocheck -->
```python
case Vector2d(_, 0):
    print(f'{v!r} is horizontal')
```

you get:

```text
TypeError: Vector2d() accepts 0 positional sub-patterns (1 given)
```

To make `Vector2d` work with positional patterns, we need to add a class attribute
named `__match_args__`, listing the instance attributes in the order they will be used
for positional pattern matching:

<!-- nocheck -->
```python
class Vector2d:
    __match_args__ = ('x', 'y')

    # etc...
```

Now we can save a few keystrokes when writing patterns to match `Vector2d` subjects:

<!-- nocheck -->
```python
def positional_pattern_demo(v: Vector2d) -> None:
    match v:
        case Vector2d(0, 0):
            print(f'{v!r} is null')
        case Vector2d(0):
            print(f'{v!r} is vertical')
        case Vector2d(_, 0):
            print(f'{v!r} is horizontal')
        case Vector2d(x, y) if x==y:
            print(f'{v!r} is diagonal')
        case _:
            print(f'{v!r} is awesome')
```

The `__match_args__` class attribute does not need to include all public instance
attributes.  In particular, if the class `__init__()` has required and optional
arguments that are assigned to instance attributes, it may be reasonable to name the
required arguments in `__match_args__`, but not the optional ones.

## Complete Listing of `Vector2d`, Version 3

We have been working on `Vector2d` for a while, showing just snippets, so here is a
consolidated listing of `vector2d_v3.py`:

```python
"""
A two-dimensional vector class
"""

from array import array
import math

class Vector2d:
    __match_args__ = ('x', 'y')

    typecode = 'd'

    def __init__(self, x, y):
        self.__x = float(x)
        self.__y = float(y)

    @property
    def x(self):
        return self.__x

    @property
    def y(self):
        return self.__y

    def __iter__(self):
        return (i for i in (self.x, self.y))

    def __repr__(self):
        class_name = type(self).__name__
        return '{}({!r}, {!r})'.format(class_name, *self)

    def __str__(self):
        return str(tuple(self))

    def __bytes__(self):
        return (bytes([ord(self.typecode)]) +
                bytes(array(self.typecode, self)))

    def __eq__(self, other):
        return tuple(self) == tuple(other)

    def __hash__(self):
        return hash((self.x, self.y))

    def __abs__(self):
        return math.hypot(self.x, self.y)

    def __bool__(self):
        return bool(abs(self))

    def angle(self):
        return math.atan2(self.y, self.x)

    def __format__(self, fmt_spec=''):
        if fmt_spec.endswith('p'):
            fmt_spec = fmt_spec[:-1]
            coords = (abs(self), self.angle())
            outer_fmt = '<{}, {}>'
        else:
            coords = self
            outer_fmt = '({}, {})'
        components = (format(c, fmt_spec) for c in coords)
        return outer_fmt.format(*components)

    @classmethod
    def frombytes(cls, octets):
        typecode = chr(octets[0])
        memv = memoryview(octets[1:]).cast(typecode)
        return cls(*memv)
```

And here are the tests used while developing it, which exercise everything shown in
this chapter so far:

```python
v1 = Vector2d(3, 4)
print(v1.x, v1.y)
# 3.0 4.0
x, y = v1
x, y
# (3.0, 4.0)
v1
# Vector2d(3.0, 4.0)
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
bool(v1), bool(Vector2d(0, 0))
# (True, False)
v1_clone = Vector2d.frombytes(bytes(v1))  # test of the .frombytes() class method
v1_clone
# Vector2d(3.0, 4.0)
v1 == v1_clone
# True
format(v1)  # tests of format() with Cartesian coordinates
# '(3.0, 4.0)'
format(v1, '.2f')
# '(3.00, 4.00)'
format(v1, '.3e')
# '(3.000e+00, 4.000e+00)'
Vector2d(0, 0).angle()  # tests of the angle method
# 0.0
Vector2d(1, 0).angle()
# 0.0
epsilon = 10**-8
abs(Vector2d(0, 1).angle() - math.pi/2) < epsilon
# True
abs(Vector2d(1, 1).angle() - math.pi/4) < epsilon
# True
format(Vector2d(1, 1), 'p')  # tests of format() with polar coordinates
# '<1.4142135623730951, 0.7853981633974483>'
format(Vector2d(1, 1), '.3ep')
# '<1.414e+00, 7.854e-01>'
format(Vector2d(1, 1), '0.5fp')
# '<1.41421, 0.78540>'
v1.x, v1.y  # tests of x and y read-only properties
# (3.0, 4.0)
v1.x = 123
# Traceback (most recent call last):
#   ...
# AttributeError: property 'x' of 'Vector2d' object has no setter
v1 = Vector2d(3, 4)  # tests of hashing
v2 = Vector2d(3.1, 4.2)
len({v1, v2})
# 2
```

To recap, in this and the previous sections we saw some essential special methods
that you may want to implement to have a full-fledged object.

> **Warning**
>
> You should only implement these special methods if your application needs them.
> End users don't care if the objects that make up the application are "Pythonic" or
> not.  On the other hand, if your classes are part of a library for other Python
> programmers to use, you can't really guess what they will do with your objects, and
> they may expect more of the "Pythonic" behaviors we are describing.  `Vector2d` is a
> didactic example with a laundry list of special methods related to object
> representation, not a template for every user-defined class.

Let's take a break from `Vector2d` to discuss the design and drawbacks of the private
attribute mechanism in Python: the double-underscore prefix in `self.__x`.

## Private and "Protected" Attributes in Python

In Python, there is no way to create private variables like there is with the
`private` modifier in Java.  What we have in Python is a simple mechanism to prevent
accidental overwriting of a "private" attribute in a subclass.  (The tutorial touches
on this in [Private Variables](classes.md#tut-private).)

Consider this scenario: someone wrote a class named `Dog` that uses a `mood` instance
attribute internally, without exposing it.  You need to subclass `Dog` as `Beagle`.
If you create your own `mood` instance attribute without being aware of the name
clash, you will clobber the `mood` attribute used by the methods inherited from `Dog`.
This would be a pain to debug.

To prevent this, if you name an instance attribute in the form `__mood` (two leading
underscores and zero or at most one trailing underscore), Python stores the name in
the instance `__dict__` prefixed with a leading underscore and the class name, so in
the `Dog` class, `__mood` becomes `_Dog__mood`, and in `Beagle` it's `_Beagle__mood`.
This language feature goes by the lovely name of *name mangling*:

```python
v1 = Vector2d(3, 4)
v1.__dict__
# {'_Vector2d__x': 3.0, '_Vector2d__y': 4.0}
v1._Vector2d__x
# 3.0
```

Name mangling is about safety, not security: it's designed to prevent accidental
access and not malicious prying, much like a hinged cover over a switch prevents
accidents, not sabotage.  Anyone who knows how private names are mangled can read the
private attribute directly, as the last line shows; that's actually useful for
debugging and serialization.  They can also directly assign a value to a private
component of a `Vector2d` by writing `v1._Vector2d__x = 7`.  But if you are doing that
in production code, you can't complain if something blows up.

The name mangling functionality is not loved by all Pythonistas, and neither is the
skewed look of names written as `self.__x`.  Some prefer to avoid this syntax and use
just one underscore prefix to "protect" attributes by convention (e.g., `self._x`).
Critics of the automatic double-underscore mangling suggest that concerns about
accidental attribute clobbering should be addressed by naming conventions; Ian
Bicking, creator of pip and virtualenv, recommended never using two leading
underscores, and spelling out the mangling explicitly when name clashes are a concern
(e.g., `_MyThing_blahblah`), which is just as effective but transparent.

The single underscore prefix has no special meaning to the Python interpreter when
used in attribute names, but it's a very strong convention among Python programmers
that you should not access such attributes from outside the class.  It's easy to
respect the privacy of an object that marks its attributes with a single `_`, just as
it's easy to respect the convention that variables in `ALL_CAPS` should be treated as
constants.  (In modules, a single `_` in front of a top-level name does have an
effect: `from mymod import *` does not import names with a `_` prefix.  You can still
write `from mymod import _privatefunc`; see [More on Modules](modules.md#tut-moremodules).)

Attributes with a single `_` prefix are called "protected" in some corners of the
Python documentation.  The practice of "protecting" attributes by convention with the
form `self._x` is widespread, but calling that a "protected" attribute is not so
common.  Some even call that a "private" attribute.

To conclude: the `Vector2d` components are "private" and our `Vector2d` instances are
"immutable", with scare quotes, because there is no way to make them really private
and immutable.  (In practice, the `private` and `protected` modifiers of Java also
provide protection against accidents only: Java's reflection API can read a private
field unless the program runs under a strict security manager, which is rare.  So
relax and enjoy the power Python gives you, and use it responsibly.)

Now back to `Vector2d`.  The next section covers a special attribute (not a method)
that affects the internal storage of an object, with potentially huge impact on the use
of memory but little effect on its public interface: `__slots__`.

## Saving Memory with `__slots__`

By default, Python stores the attributes of each instance in a `dict` named
`__dict__`.  As you saw in
[Practical Consequences of How `dict` Works](dicts-sets.md#practical-consequences-of-how-dict-works),
a `dict` has a significant memory overhead, even with the optimizations mentioned
there.  But if you define a class attribute named `__slots__` holding a sequence of
attribute names, Python uses an alternative storage model for the instance attributes:
the attributes named in `__slots__` are stored in a hidden array of references that
uses less memory than a `dict`.  Let's see how that works through simple examples:

```python
class Pixel:
    __slots__ = ('x', 'y')

p = Pixel()
p.__dict__  # first effect: instances of Pixel have no __dict__
# Traceback (most recent call last):
#   ...
# AttributeError: 'Pixel' object has no attribute '__dict__'
p.x = 10  # set the p.x and p.y attributes normally
p.y = 20
p.color = 'red'  # second effect: attributes not listed in __slots__ can't be set
# Traceback (most recent call last):
#   ...
# AttributeError: 'Pixel' object has no attribute 'color' and no __dict__ for setting new attributes
```

`__slots__` must be present when the class is created; adding or changing it later has
no effect.  The attribute names may be in a tuple or list, but a tuple makes it clear
there's no point in changing it.  We create an instance of `Pixel` because the effects
of `__slots__` are seen on the instances: they have no `__dict__`, and trying to set
an attribute not listed in `__slots__` raises `AttributeError`.

So far, so good.  Now let's create a subclass of `Pixel` to see the counterintuitive
side of `__slots__`:

```python
class OpenPixel(Pixel):  # OpenPixel declares no attributes of its own
    pass

op = OpenPixel()
op.__dict__  # surprise: instances of OpenPixel have a __dict__
# {}
op.x = 8  # if you set attribute x, named in the __slots__ of Pixel...
op.__dict__  # ...it is not stored in the instance __dict__...
# {}
op.x  # ...but in the hidden array of references in the instance
# 8
op.color = 'green'  # an attribute not named in __slots__...
op.__dict__  # ...is stored in the instance __dict__
# {'color': 'green'}
```

So the effect of `__slots__` is only partially inherited by a subclass.  To make sure
that instances of a subclass have no `__dict__`, you must declare `__slots__` again
in the subclass.  If you declare `__slots__ = ()` (an empty tuple), then the instances
of the subclass will have no `__dict__` and will only accept the attributes named in
the `__slots__` of the base class.  If you want a subclass to have additional
attributes, name them in `__slots__`:

```python
class ColorPixel(Pixel):
   __slots__ = ('color',)

cp = ColorPixel()
cp.__dict__  # ColorPixel instances have no __dict__
# Traceback (most recent call last):
#   ...
# AttributeError: 'ColorPixel' object has no attribute '__dict__'
cp.x = 2
cp.color = 'blue'
cp.flavor = 'banana'
# Traceback (most recent call last):
#   ...
# AttributeError: 'ColorPixel' object has no attribute 'flavor' and no __dict__ for setting new attributes
```

Essentially, the `__slots__` of the superclasses are added to the `__slots__` of the
current class.  Don't forget that single-item tuples must have a trailing comma.  You
can set the attributes declared in the `__slots__` of this class and its
superclasses, but no others.

It's possible to "save memory and eat it too": if you add the `'__dict__'` name to the
`__slots__` list, your instances will keep the attributes named in `__slots__` in the
per-instance array of references, but will also support dynamically created
attributes, which are stored in the usual `__dict__`.  This is necessary if you want
to use the `@cached_property` decorator (covered in
[Caching Properties with `functools`](dynamic-attributes.md#step-5-caching-properties-with-functools)).
Of course, having `'__dict__'` in `__slots__` may entirely defeat its purpose,
depending on the number of static and dynamic attributes in each instance and how they
are used.  Careless optimization is worse than premature optimization: you add
complexity but may not get any benefit.

Another special per-instance attribute that you may want to keep is `__weakref__`,
necessary for an object to support weak references (see
[Weak References](references.md#weak-references)).  That attribute exists by default
in instances of user-defined classes.  However, if the class defines `__slots__`, and
you need the instances to be targets of weak references, then you need to include
`'__weakref__'` among the attributes named in `__slots__`.

### Simple Measure of `__slots__` Savings

Here is `Vector2d` with `__slots__`; the `__slots__` attribute is the only addition:

<!-- nocheck -->
```python
class Vector2d:
    __match_args__ = ('x', 'y')
    __slots__ = ('__x', '__y')

    typecode = 'd'
    # methods are the same as previous version
```

`__match_args__` lists the public attribute names for positional pattern matching.  In
contrast, `__slots__` lists the names of the instance attributes, which in this case
are private attributes.  (Private names in `__slots__` are mangled just like private
attributes.)

To measure the memory savings, you can use the
[`tracemalloc`](https://docs.python.org/3/library/tracemalloc.html) module.  This
function measures the memory allocated while building a list of instances of a class:

```python
import tracemalloc

class Pt:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class SlotPt:
    __slots__ = ('x', 'y')
    def __init__(self, x, y):
        self.x = x
        self.y = y

def measure(cls, n=100_000):
    tracemalloc.start()
    objs = [cls(float(i), float(i)) for i in range(n)]
    current, _ = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return current

measure(Pt), measure(SlotPt)
# (14404192, 10398528)
```

Those numbers include the float objects and the list itself, so the difference, about
40 bytes per instance on CPython 3.13, is the saving from `__slots__`.  In older Python
versions the difference was much larger: in an experiment with Python 3.9 building 10
million `Vector2d` instances, the process used about 1.55 GiB with instance `__dict__`
and 551 MiB with `__slots__`, and the `__slots__` version was also faster.  Recent
CPython versions store instance attributes more compactly by default, so measure before
you decide.

> **Tip**
>
> If you are handling millions of objects with numeric data, you should really be using
> NumPy arrays (see [NumPy](sequences.md#numpy)), which are not only memory efficient but
> have highly optimized functions for numeric processing, many of which operate on the
> entire array at once.  `Vector2d` is designed just to provide context when discussing
> special methods.

### Summarizing the Issues with `__slots__`

The `__slots__` class attribute may provide significant memory savings if properly
used, but there are a few caveats:

* You must remember to redeclare `__slots__` in each subclass to prevent their
  instances from having `__dict__`.
* Instances will only be able to have the attributes listed in `__slots__`, unless
  you include `'__dict__'` in `__slots__` (but doing so may negate the memory savings).
* Classes using `__slots__` cannot use the `@cached_property` decorator, unless they
  explicitly name `'__dict__'` in `__slots__`.
* Instances cannot be targets of weak references, unless you add `'__weakref__'` in
  `__slots__`.

(The `@dataclass` decorator can generate `__slots__` for you with `slots=True`; see
[More About `@dataclass`](dataclasses.md#more-about-dataclass).)

## Overriding Class Attributes

A distinctive feature of Python is how class attributes can be used as default values
for instance attributes.  In `Vector2d` there is the `typecode` class attribute.  It's
used twice in the `__bytes__()` method, but we read it as `self.typecode` by design.
Because `Vector2d` instances are created without a `typecode` attribute of their own,
`self.typecode` gets the `Vector2d.typecode` class attribute by default.

But if you write to an instance attribute that does not exist, you create a new
instance attribute, for example a `typecode` instance attribute, and the class
attribute by the same name is untouched.  However, from then on, whenever the code
handling that instance reads `self.typecode`, the instance `typecode` is retrieved,
effectively shadowing the class attribute by the same name.  This opens the
possibility of customizing an individual instance with a different `typecode`.

The default `Vector2d.typecode` is `'d'`, meaning each vector component is represented
as an 8-byte double-precision float when exporting to `bytes`.  If we set the
`typecode` of a `Vector2d` instance to `'f'` prior to exporting, each component is
exported as a 4-byte single-precision float.  (Since we are adding a custom instance
attribute, this uses the `Vector2d` implementation without `__slots__`.)

```python
v1 = Vector2d(1.1, 2.2)
dumpd = bytes(v1)
dumpd
# b'd\x9a\x99\x99\x99\x99\x99\xf1?\x9a\x99\x99\x99\x99\x99\x01@'
len(dumpd)  # the default bytes representation is 17 bytes long
# 17
v1.typecode = 'f'  # set typecode to 'f' in the v1 instance
dumpf = bytes(v1)
dumpf
# b'f\xcd\xcc\x8c?\xcd\xcc\x0c@'
len(dumpf)  # now the bytes dump is 9 bytes long
# 9
Vector2d.typecode  # unchanged; only the v1 instance uses typecode 'f'
# 'd'
```

Now it should be clear why the `bytes` export of a `Vector2d` is prefixed by the
`typecode`: we wanted to support different export formats.

If you want to change a class attribute, you must set it on the class directly, not
through an instance.  You could change the default `typecode` for all instances (that
don't have their own `typecode`) with `Vector2d.typecode = 'f'`.  However, there is an
idiomatic Python way of achieving a more permanent effect, and being more explicit
about the change.  Because class attributes are public, they are inherited by
subclasses, so it's common practice to subclass just to customize a class data
attribute.  The Django class-based views use this technique extensively:

```python
class ShortVector2d(Vector2d):  # a subclass just to overwrite typecode
    typecode = 'f'

sv = ShortVector2d(1/11, 1/27)
sv
# ShortVector2d(0.09090909090909091, 0.037037037037037035)
len(bytes(sv))  # the exported bytes are 9 long, not 17 as before
# 9
```

This example also explains why the `class_name` in `Vector2d.__repr__()` is not
hardcoded, but read from `type(self).__name__`:

<!-- nocheck -->
```python
# inside class Vector2d:

def __repr__(self):
    class_name = type(self).__name__
    return '{}({!r}, {!r})'.format(class_name, *self)
```

If `class_name` were hardcoded, subclasses of `Vector2d` like `ShortVector2d` would
have to overwrite `__repr__()` just to change the `class_name`.  By reading the name
from the type of the instance, `__repr__()` is safer to inherit.

This ends our coverage of building a simple class that leverages the data model to play
well with the rest of Python: offering different object representations, providing a
custom formatting code, exposing read-only attributes, and supporting `hash()` to
integrate with sets and mappings.

## Summary

The aim of this chapter was to demonstrate the use of special methods and conventions in
the construction of a well-behaved Pythonic class.

Is `vector2d_v3.py` more Pythonic than `vector2d_v0.py`?  The final `Vector2d`
certainly exhibits more Python features.  But whether the first or the last
implementation is suitable depends on the context where it would be used.  The Zen of
Python says: "Simple is better than complex."  An object should be as simple as the
requirements dictate, and not a parade of language features.  If the code is for an
application, it should focus on what is needed to support the end users, not more.  If
the code is for a library for other programmers to use, then it's reasonable to
implement special methods supporting behaviors that Pythonistas expect.  For example,
`__eq__()` may not be necessary to support a business requirement, but it makes the
class easier to test.

The examples in this chapter demonstrated several of the special methods from the
overview in [The Python Data Model](data-model.md#overview-of-special-methods):

* string/bytes representation methods: `__repr__`, `__str__`, `__format__` and
  `__bytes__`;
* methods for reducing an object to a number: `__abs__`, `__bool__` and `__hash__`;
* the `__eq__` operator, to support testing and hashing (along with `__hash__`).

While supporting conversion to bytes, we also implemented an alternative constructor,
`Vector2d.frombytes()`, which provided the context for discussing the decorators
`@classmethod` (very handy) and `@staticmethod` (not so useful; module-level functions
are simpler).  The `frombytes` method was inspired by its namesake in the `array.array`
class.

We saw that the Format Specification Mini-Language is extensible by implementing a
`__format__()` method that parses a `format_spec` provided to the
`format(obj, format_spec)` built-in or within replacement fields `'{:«format_spec»}'`
in f-strings or strings used with `str.format()`.

To make `Vector2d` instances hashable, we made them immutable, at least preventing
accidental changes by making the `x` and `y` attributes private and exposing them as
read-only properties.  We then implemented `__hash__()` by hashing a tuple of the
instance attributes.

We then discussed the memory savings and the caveats of declaring a `__slots__`
attribute.  Because using `__slots__` has side effects, it really makes sense only when
handling a very large number of instances, think millions of instances, not just
thousands.

The last topic was the overriding of a class attribute accessed via the instances (as
in `self.typecode`), first by creating an instance attribute, and then by subclassing
and overwriting at the class level.

Throughout the chapter, design choices in the examples were informed by studying the
interfaces of standard Python objects.  If this chapter can be summarized in one
sentence, it is this: to build Pythonic objects, observe how real Python objects behave.

> **Note**
>
> In the first versions of `Vector2d`, the `x` and `y` attributes were public, as are
> all Python instance and class attributes by default.  When we needed to avoid
> accidental updates, we implemented properties, but nothing changed elsewhere in the
> code or in the public interface of `Vector2d`: users still write `my_vector.x` and
> `my_vector.y`.  This shows that you can always start your classes in the simplest
> possible way, with public attributes, because when (or if) you later need more control
> with getters and setters, you can implement them through properties without changing
> any code that already uses those attributes.  That is the opposite of the Java
> practice of writing getters and setters up front, because Java has no properties.
> Besides, writing `my_object.set_foo(my_object.get_foo() + 1)` instead of
> `my_object.foo += 1` is goofy.

> **See also**
>
> * [Basic customization](https://docs.python.org/3/reference/datamodel.html#basic-customization)
>   in the Data Model chapter of the language reference documents most of the methods
>   used in this chapter.
> * Chapter 8, "Classes and Objects", of the *Python Cookbook*, 3rd ed., has several
>   solutions related to this chapter.
> * The [attrs](https://www.attrs.org/) package and the data class builders from
>   [Data Class Builders](dataclasses.md) generate several of these special methods for
>   you.  Knowing how to write them yourself is still essential to understand what
>   those packages do, to decide whether you need them, and to override the methods they
>   generate when necessary.
> * This chapter covered every special method related to object representation except
>   `__index__` (covered in [Special Methods for Sequences](sequence-protocol.md#a-slice-aware-__getitem__))
>   and `__fspath__` (see [**PEP 519**](https://peps.python.org/pep-0519/)).
