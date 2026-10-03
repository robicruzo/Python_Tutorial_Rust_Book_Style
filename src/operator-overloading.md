# Operator Overloading

> There are some things that I kind of feel torn about, like operator overloading.  I
> left out operator overloading as a fairly personal choice because I had seen too many
> people abuse it in C++.
>
> — James Gosling, creator of Java

In Python, you can compute compound interest using a formula written like this:

<!-- nocheck -->
```python
interest = principal * ((1 + rate) ** periods - 1)
```

Operators that appear between operands, like `1 + rate`, are *infix operators*.  In
Python, the infix operators can handle any arbitrary type.  Thus, if you are dealing with
real money, you can make sure that `principal`, `rate` and `periods` are exact numbers —
instances of the Python `decimal.Decimal` class — and that formula will work as written,
producing an exact result.

But in Java, if you switch from `float` to `BigDecimal` to get exact results, you can't
use infix operators anymore, because they only work with the primitive types.  This is
the same formula coded to work with `BigDecimal` numbers in Java:

```text
BigDecimal interest = principal.multiply(BigDecimal.ONE.add(rate)
                        .pow(periods).subtract(BigDecimal.ONE));
```

It's clear that infix operators make formulas more readable.  Operator overloading is
necessary to support infix operator notation with user-defined or extension types, such
as NumPy arrays.  Having operator overloading in a high-level, easy-to-use language was
probably a key reason for the huge success of Python in data science, including
financial and scientific applications.

In [The Python Data Model](data-model.md) we saw some trivial implementations of
operators in a bare-bones `Vector` class.  The `__add__()` and `__mul__()` methods there
were written to show how special methods support operator overloading, but there are
subtle problems in their implementations that we overlooked.  Also, in
[Special Methods for Sequences](sequence-protocol.md) we noted that `Vector.__eq__`
considers `Vector([1, 2]) == (1, 2)` to be `True` — which may or may not make sense.  We
will address these matters in this chapter, as well as:

* how an infix operator method should signal it cannot handle an operand;
* using duck typing or goose typing to deal with operands of various types;
* the special behavior of the rich comparison operators (e.g., `==`, `>`, `<=`);
* the default handling of augmented assignment operators such as `+=`, and how to
  overload them.

## Operator Overloading 101

Operator overloading allows user-defined objects to interoperate with infix operators
such as `+` and `|`, or unary operators like `-` and `~`.  More generally, function
invocation (`()`), attribute access (`.`) and item access/slicing (`[]`) are also
operators in Python, but this chapter covers unary and infix operators.

Operator overloading has a bad name in some circles.  It is a language feature that can
be (and has been) abused, resulting in programmer confusion, bugs and unexpected
performance bottlenecks.  But if used well, it leads to pleasurable APIs and readable
code.  Python strikes a good balance among flexibility, usability and safety by imposing
some limitations:

* We cannot change the meaning of the operators for the built-in types.
* We cannot create new operators, only overload existing ones.
* A few operators can't be overloaded: `is`, `and`, `or`, `not` (but the bitwise `&`,
  `|`, `~` can).

In [Special Methods for Sequences](sequence-protocol.md), we already had one infix
operator in `Vector`: `==`, supported by the `__eq__()` method.  In this chapter, we'll
improve the implementation of `__eq__()` to better handle operands of types other than
`Vector`.  However, the rich comparison operators (`==`, `!=`, `>`, `<`, `>=`, `<=`) are
special cases in operator overloading, so we'll start by overloading four arithmetic
operators in `Vector`: the unary `-` and `+`, followed by the infix `+` and `*`.

> **Note**
>
> The snippets in this chapter show only the methods being discussed.  They are all
> collected in the complete `vector_v8.py` listing in
> [The Complete Listing](#the-complete-listing), followed by the tests that produced the
> outputs shown along the way.

Let's start with the easiest topic: unary operators.

## Unary Operators

The Language Reference section
[Unary arithmetic and bitwise operations](https://docs.python.org/3/reference/expressions.html#unary-arithmetic-and-bitwise-operations)
lists three unary operators, shown here with their associated special methods:

`-`, implemented by `__neg__`
: Arithmetic unary negation.  If `x` is `-2` then `-x == 2`.

`+`, implemented by `__pos__`
: Arithmetic unary plus.  Usually `x == +x`, but there are a few cases when that's not
  true.  See [When `x` and `+x` Are Not Equal](#when-x-and-x-are-not-equal) if you're
  curious.

`~`, implemented by `__invert__`
: Bitwise not, or bitwise inverse of an integer, defined as `~x == -(x+1)`.  If `x` is
  `2` then `~x == -3`.

The [Data model](https://docs.python.org/3/reference/datamodel.html#emulating-numeric-types)
chapter of the Language Reference also lists the `abs()` built-in function as a unary
operator.  The associated special method is `__abs__()`, as we've seen before.

It's easy to support the unary operators.  Simply implement the appropriate special
method, which will take just one argument: `self`.  Use whatever logic makes sense in
your class, but stick to the general rule of operators: always return a new object.  In
other words, do not modify the receiver (`self`), but create and return a new instance of
a suitable type.

In the case of `-` and `+`, the result will probably be an instance of the same class as
`self`.  For unary `+`, if the receiver is immutable you should return `self`; otherwise,
return a copy of `self`.  For `abs()`, the result should be a scalar number.

As for `~`, it's difficult to say what would be a sensible result if you're not dealing
with bits in an integer.  In the pandas data analysis package, the tilde negates boolean
filtering conditions.

Here is the `__abs__()` method we already had, and the newly added `__neg__()` and
`__pos__()` unary operator methods:

<!-- nocheck -->
```python
def __abs__(self):
    return math.hypot(*self)

def __neg__(self):
    return Vector(-x for x in self)  # build a new Vector with every component negated

def __pos__(self):
    return Vector(self)  # build a new Vector with every component of self
```

Recall that `Vector` instances are iterable, and `Vector.__init__` takes an iterable
argument, so the implementations of `__neg__()` and `__pos__()` are short and sweet.

We'll not implement `__invert__()`, so if the user tries `~v` on a `Vector` instance,
Python will raise `TypeError` with a clear message: `bad operand type for unary ~:
'Vector'`.

### When `x` and `+x` Are Not Equal

Everybody expects that `x == +x`, and that is true almost all the time in Python, but
there are two cases in the standard library where `x != +x`.

The first case involves the `decimal.Decimal` class.  You can have `x != +x` if `x` is a
`Decimal` instance created in an arithmetic context and `+x` is then evaluated in a
context with different settings.  For example, `x` is calculated in a context with a
certain precision, but the precision of the context is changed and then `+x` is
evaluated:

```python
import decimal
ctx = decimal.getcontext()  # get a reference to the current global arithmetic context
ctx.prec = 40  # set the precision of the arithmetic context to 40
one_third = decimal.Decimal('1') / decimal.Decimal('3')  # compute 1/3 with that precision
one_third  # there are 40 digits after the decimal point
# Decimal('0.3333333333333333333333333333333333333333')
one_third == +one_third
# True
ctx.prec = 28  # lower precision to 28, the default for Decimal arithmetic
one_third == +one_third
# False
+one_third  # there are 28 digits after the '.' here
# Decimal('0.3333333333333333333333333333')
```

Each occurrence of the expression `+one_third` produces a new `Decimal` instance from the
value of `one_third`, but using the precision of the current arithmetic context.

You can find the second case where `x != +x` in the
[`collections.Counter`](https://docs.python.org/3/library/collections.html#collections.Counter)
documentation.  The `Counter` class implements several arithmetic operators, including
infix `+` to add the tallies from two `Counter` instances.  However, for practical
reasons, `Counter` addition discards from the result any item with a negative or zero
count.  And the prefix `+` is a shortcut for adding an empty `Counter`, therefore it
produces a new `Counter`, preserving only the tallies that are greater than zero:

```python
from collections import Counter
ct = Counter('abracadabra')
ct
# Counter({'a': 5, 'b': 2, 'r': 2, 'c': 1, 'd': 1})
ct['r'] = -3
ct['d'] = 0
ct
# Counter({'a': 5, 'b': 2, 'c': 1, 'd': 0, 'r': -3})
+ct
# Counter({'a': 5, 'b': 2, 'c': 1})
```

Now, back to our regularly scheduled programming.

## Overloading `+` for Vector Addition

The `Vector` class is a sequence type, and the section
[Emulating container types](https://docs.python.org/3/reference/datamodel.html#emulating-container-types)
of the Data Model says that sequences should support the `+` operator for concatenation
and `*` for repetition.  However, here we will implement `+` and `*` as mathematical
vector operations, which are a bit harder but more meaningful for a `Vector` type.

> **Tip**
>
> If users want to concatenate or repeat `Vector` instances, they can convert them to
> tuples or lists, apply the operator, and convert back — thanks to the fact that
> `Vector` is iterable and can be constructed from an iterable:
>
> ```python
> v_concatenated = Vector(list(v1) + list(v2))
> v_repeated = Vector(tuple(v1) * 5)
> ```

Adding two Euclidean vectors results in a new vector in which the components are the
pairwise additions of the components of the operands.  To illustrate:

<!-- nocheck -->
```python
v1 = Vector([3, 4, 5])
v2 = Vector([6, 7, 8])
v1 + v2
# Vector([9.0, 11.0, 13.0])
v1 + v2 == Vector([3 + 6, 4 + 7, 5 + 8])
# True
```

What happens if we try to add two `Vector` instances of different lengths?  We could
raise an error, but considering practical applications (such as information retrieval),
it's better to fill out the shortest `Vector` with zeros.  This is the result we want:

<!-- nocheck -->
```python
v1 = Vector([3, 4, 5, 6])
v3 = Vector([1, 2])
v1 + v3
# Vector([4.0, 6.0, 5.0, 6.0])
```

Given these basic requirements, we can implement `__add__()` like this:

<!-- nocheck -->
```python
# inside the Vector class

def __add__(self, other):
    pairs = itertools.zip_longest(self, other, fillvalue=0.0)
    return Vector(a + b for a, b in pairs)
```

`pairs` is a generator that produces tuples `(a, b)`, where `a` is from `self`, and `b`
is from `other`.  If `self` and `other` have different lengths, `fillvalue` supplies the
missing values for the shortest iterable (see [The Awesome `zip`](sequence-protocol.md#the-awesome-zip)).
A new `Vector` is built from a generator expression, producing one addition for each
`(a, b)` from `pairs`.  Note how `__add__()` returns a new `Vector` instance, and does not
change `self` or `other`.

> **Warning**
>
> Special methods implementing unary or infix operators should never change the value of
> the operands.  Expressions with such operators are expected to produce results by
> creating new objects.  Only augmented assignment operators may change the first operand
> (`self`), as discussed in [Augmented Assignment Operators](#augmented-assignment-operators).

This allows adding `Vector` to a `Vector2d`, and `Vector` to a tuple or to any iterable
that produces numbers:

<!-- nocheck -->
```python
v1 = Vector([3, 4, 5])
v1 + (10, 20, 30)
# Vector([13.0, 24.0, 35.0])
v2d = Vector2d(1, 2)
v1 + v2d
# Vector([4.0, 6.0, 5.0])
```

Both uses of `+` work because `__add__()` uses `zip_longest(...)`, which can consume any
iterable, and the generator expression to build the new `Vector` merely performs `a + b`
with the pairs produced by `zip_longest(...)`, so an iterable producing any number items
will do.  However, if we swap the operands, the mixed-type additions fail:

<!-- nocheck -->
```python
(10, 20, 30) + v1
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# TypeError: can only concatenate tuple (not "Vector") to tuple
v2d + v1
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# TypeError: unsupported operand type(s) for +: 'Vector2d' and 'Vector'
```

To support operations involving objects of different types, Python implements a special
dispatching mechanism for the infix operator special methods.  Given an expression
`a + b`, the interpreter will perform these steps:

1. If `a` has `__add__`, call `a.__add__(b)` and return the result unless it's
   `NotImplemented`.
2. If `a` doesn't have `__add__`, or calling it returns `NotImplemented`, check if `b` has
   `__radd__`, then call `b.__radd__(a)` and return the result unless it's
   `NotImplemented`.
3. If `b` doesn't have `__radd__`, or calling it returns `NotImplemented`, raise
   `TypeError` with an *unsupported operand types* message.

```text
               a + b
                 │
      does a have __add__? ──no──┐
                 │ yes           │
     result = a.__add__(b)       │
                 │               │
   result is NotImplemented? ─no─┼──► return result
                 │ yes           │
                 ▼               ▼
            does b have __radd__? ──no──► raise TypeError
                 │ yes
     result = b.__radd__(a)
                 │
   result is NotImplemented? ──yes──► raise TypeError
                 │ no
                 ▼
           return result
```

(There is one refinement: if the type of `b` is a subclass of the type of `a`, and it
overrides the reflected method, then `b.__radd__(a)` is tried *first*.  That lets
subclasses take control of mixed operations with their base class.)

> **Note**
>
> The `__radd__()` method is called the "reflected" or "reversed" version of
> `__add__()`.  The Data Model chapter uses "reflected", but the
> [`numbers`](https://docs.python.org/3/library/numbers.html#implementing-the-arithmetic-operations)
> module docs mention "forward" and "reverse" methods, and that terminology is clearer,
> because "forward" and "reverse" name each of the directions, while "reflected"
> doesn't have an obvious opposite.

Therefore, to make the mixed-type additions work, we need to implement the
`Vector.__radd__` method, which Python will invoke as a fallback if the left operand
does not implement `__add__()`, or if it does but returns `NotImplemented` to signal that
it doesn't know how to handle the right operand.

> **Warning**
>
> Do not confuse `NotImplemented` with `NotImplementedError`.  The first,
> `NotImplemented`, is a special singleton value that an infix operator special method
> should *return* to tell the interpreter it cannot handle a given operand.  In contrast,
> `NotImplementedError` is an exception that stub methods in abstract classes may *raise*
> to warn that subclasses must implement them.

The simplest implementation of `__radd__()` that works is this:

<!-- nocheck -->
```python
# inside the Vector class

def __add__(self, other):  # no changes to __add__
    pairs = itertools.zip_longest(self, other, fillvalue=0.0)
    return Vector(a + b for a, b in pairs)

def __radd__(self, other):  # __radd__ just delegates to __add__
    return self + other
```

Often, `__radd__()` can be as simple as that: just invoke the proper operator, therefore
delegating to `__add__()` in this case.  This applies to any commutative operator; `+` is
commutative when dealing with numbers or our vectors, but it's not commutative when
concatenating sequences in Python.  If `__radd__()` simply calls `__add__()`, here is
another way to achieve the same effect:

<!-- nocheck -->
```python
def __add__(self, other):
    pairs = itertools.zip_longest(self, other, fillvalue=0.0)
    return Vector(a + b for a, b in pairs)

__radd__ = __add__
```

These methods work with `Vector` objects, or any iterable with numeric items, such as a
`Vector2d`, a `tuple` of integers, or an `array` of floats.  But if provided with a
noniterable object, `__add__()` raises an exception with a message that is not very
helpful:

<!-- nocheck -->
```python
v1 + 1
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
#   File "vector_v6.py", line 328, in __add__
#     pairs = itertools.zip_longest(self, other, fillvalue=0.0)
# TypeError: 'int' object is not iterable
```

Even worse, we get a misleading message if an operand is iterable but its items cannot be
added to the `float` items in the `Vector`:

<!-- nocheck -->
```python
v1 + 'ABC'
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
#   File "vector_v6.py", line 329, in __add__
#     return Vector(a + b for a, b in pairs)
#   File "vector_v6.py", line 243, in __init__
#     self._components = array(self.typecode, components)
#   File "vector_v6.py", line 329, in <genexpr>
#     return Vector(a + b for a, b in pairs)
# TypeError: unsupported operand type(s) for +: 'float' and 'str'
```

We tried to add `Vector` and a `str`, but the message complains about `float` and `str`.

The problems actually go deeper than obscure error messages: if an operator special
method cannot return a valid result because of type incompatibility, it should return
`NotImplemented` and not raise `TypeError`.  By returning `NotImplemented`, you leave the
door open for the implementer of the other operand type to perform the operation when
Python tries the reversed method call.

In the spirit of duck typing, we will refrain from testing the type of the `other`
operand, or the type of its elements.  We'll catch the exceptions and return
`NotImplemented`.  If the interpreter has not yet reversed the operands, it will try that.
If the reverse method call returns `NotImplemented`, then Python will raise `TypeError`
with a standard error message like "unsupported operand type(s) for +: 'Vector' and
'str'".  Here is the final implementation of the special methods for `Vector` addition:

<!-- nocheck -->
```python
def __add__(self, other):
    try:
        pairs = itertools.zip_longest(self, other, fillvalue=0.0)
        return Vector(a + b for a, b in pairs)
    except TypeError:
        return NotImplemented

def __radd__(self, other):
    return self + other
```

Note that `__add__()` now catches a `TypeError` and returns `NotImplemented`.

> **Tip**
>
> If an infix operator method raises an exception, it aborts the operator dispatch
> algorithm.  In the particular case of `TypeError`, it is often better to catch it and
> return `NotImplemented`.  This allows the interpreter to try calling the reversed
> operator method, which may correctly handle the computation with the swapped operands,
> if they are of different types.

At this point, we have safely overloaded the `+` operator by writing `__add__()` and
`__radd__()`.  We will now tackle another infix operator: `*`.

## Overloading `*` for Scalar Multiplication

What does `Vector([1, 2, 3]) * x` mean?  If `x` is a number, that would be a scalar
product, and the result would be a new `Vector` with each component multiplied by `x` —
also known as an elementwise multiplication:

<!-- nocheck -->
```python
v1 = Vector([1, 2, 3])
v1 * 10
# Vector([10.0, 20.0, 30.0])
11 * v1
# Vector([11.0, 22.0, 33.0])
```

> **Note**
>
> Another kind of product involving `Vector` operands would be the dot product of two
> vectors — or matrix multiplication, if you take one vector as a 1 × N matrix and the
> other as an N × 1 matrix.  We will implement that operator in our `Vector` class in
> [Using `@` as an Infix Operator](#using--as-an-infix-operator).

Back to our scalar product, again we start with the simplest `__mul__()` and
`__rmul__()` methods that could possibly work:

<!-- nocheck -->
```python
# inside the Vector class

def __mul__(self, scalar):
    return Vector(n * scalar for n in self)

def __rmul__(self, scalar):
    return self * scalar
```

Those methods do work, except when provided with incompatible operands.  The `scalar`
argument has to be a number that when multiplied by a `float` produces another `float`
(because our `Vector` class uses an array of floats internally).  So a `complex` number
will not do, but the scalar can be an `int`, a `bool` (because `bool` is a subclass of
`int`), or even a `fractions.Fraction` instance.  The next version of `__mul__()` does not
make an explicit type check on `scalar`, but instead converts it into a `float`, and
returns `NotImplemented` if that fails.  That's a clear example of duck typing:

<!-- nocheck -->
```python
def __mul__(self, scalar):
    try:
        factor = float(scalar)
    except (TypeError, ValueError):  # if scalar cannot be converted to float...
        return NotImplemented  # ...we don't know how to handle it
    return Vector(n * factor for n in self)

def __rmul__(self, scalar):
    return self * scalar
```

If `scalar` cannot be converted to `float`, we don't know how to handle it, so we return
`NotImplemented` to let Python try `__rmul__()` on the `scalar` operand.  `float()` raises
`TypeError` for most unsuitable objects, but `ValueError` for strings that don't look like
numbers, such as `'x'`, so we catch both.  `__rmul__()` works fine by just performing
`self * scalar`, delegating to the `__mul__()` method.

> **Warning**
>
> Duck typing has a price here: `float('1.5')` works, so `Vector([1, 2]) * '1.5'` would
> return `Vector([1.5, 3.0])`.  If that's unacceptable in your application, reject `str`
> explicitly, or check against a protocol like `typing.SupportsFloat`
> ([Runtime Checkable Static Protocols](protocols-abcs.md#runtime-checkable-static-protocols)),
> which `str` does not implement.

With that, we can multiply `Vector`s by scalar values of the usual, and not so usual,
numeric types:

<!-- nocheck -->
```python
v1 = Vector([1.0, 2.0, 3.0])
14 * v1
# Vector([14.0, 28.0, 42.0])
v1 * True
# Vector([1.0, 2.0, 3.0])
from fractions import Fraction
v1 * Fraction(1, 3)
# Vector([0.3333333333333333, 0.6666666666666666, 1.0])
```

Now that we can multiply `Vector` by scalars, let's see how to implement `Vector` by
`Vector` products.

> **Note**
>
> An earlier edition of *Fluent Python* used goose typing in `__mul__()`: it checked the
> `scalar` argument with `isinstance(scalar, numbers.Real)`.  The `numbers` ABCs are not
> supported by static type checkers (see
> [The `numbers` ABCs and Numeric Protocols](protocols-abcs.md#the-numbers-abcs-and-numeric-protocols)),
> so duck typing is preferable there.  On the other hand, `__matmul__()` in the next
> section is a good example of goose typing.

## Using `@` as an Infix Operator

The `@` sign is well-known as the prefix of function decorators, but since Python 3.5 it
can also be used as an infix operator.  For years, the dot product was written as
`numpy.dot(a, b)` in NumPy.  The function call notation makes longer formulas harder to
translate from mathematical notation to Python, so the numerical computing community
lobbied for [**PEP 465**](https://peps.python.org/pep-0465/) — A dedicated infix operator
for matrix multiplication.  Today, you can write `a @ b` to compute the dot product of two
NumPy arrays.

The `@` operator is supported by the special methods `__matmul__()`, `__rmatmul__()` and
`__imatmul__()`, named for "matrix multiplication".  These methods are not used anywhere
in the standard library, but are recognized by the interpreter, so the NumPy team — and
the rest of us — can support the `@` operator in user-defined types.

These simple tests show how `@` should work with `Vector` instances:

<!-- nocheck -->
```python
va = Vector([1, 2, 3])
vz = Vector([5, 6, 7])
va @ vz == 38.0  # 1*5 + 2*6 + 3*7
# True
[10, 20, 30] @ vz
# 380.0
va @ 3
# Traceback (most recent call last):
#   ...
# TypeError: unsupported operand type(s) for @: 'Vector' and 'int'
```

Here is the code of the relevant special methods:

<!-- nocheck -->
```python
class Vector:
    # many methods omitted

    def __matmul__(self, other):
        if (isinstance(other, abc.Sized) and  # both operands must implement __len__ and __iter__...
            isinstance(other, abc.Iterable)):
            if len(self) == len(other):  # ...and have the same length to allow...
                return sum(a * b for a, b in zip(self, other))  # ...a beautiful use of sum and zip
            else:
                raise ValueError('@ requires vectors of equal length.')
        else:
            return NotImplemented

    def __rmatmul__(self, other):
        return self @ other
```

> **Tip**
>
> With `zip(self, other, strict=True)` (Python 3.10+), you could replace the inner `if`
> with a `try`/`except ValueError`, since `zip` itself raises `ValueError` when the
> iterables have different lengths.  That is in line with Python's fail-fast philosophy.

This is a good example of goose typing in practice.  If we tested the `other` operand
against `Vector`, we'd deny users the flexibility of using lists or arrays as operands to
`@`.  As long as one operand is a `Vector`, our `@` implementation supports other operands
that are instances of `abc.Sized` and `abc.Iterable`.  Both of these ABCs implement the
`__subclasshook__()`, therefore any object providing `__len__()` and `__iter__()` satisfies
our test — no need to actually subclass those ABCs or even register with them, as
explained in [Structural Typing with ABCs](protocols-abcs.md#structural-typing-with-abcs).
In particular, our `Vector` class does not subclass either `abc.Sized` or `abc.Iterable`,
but it does pass the `isinstance` checks against those ABCs because it has the necessary
methods.

Let's review the arithmetic operators supported by Python, before diving into the special
category of [Rich Comparison Operators](#rich-comparison-operators).

## Wrapping-Up Arithmetic Operators

Implementing `+`, `*` and `@`, we saw the most common patterns for coding infix
operators.  The techniques we described are applicable to all operators listed in this
table (the in-place operators will be covered in
[Augmented Assignment Operators](#augmented-assignment-operators)):

| Operator | Forward | Reverse | In-place | Description |
|---|---|---|---|---|
| `+` | `__add__` | `__radd__` | `__iadd__` | Addition or concatenation |
| `-` | `__sub__` | `__rsub__` | `__isub__` | Subtraction |
| `*` | `__mul__` | `__rmul__` | `__imul__` | Multiplication or repetition |
| `/` | `__truediv__` | `__rtruediv__` | `__itruediv__` | True division |
| `//` | `__floordiv__` | `__rfloordiv__` | `__ifloordiv__` | Floor division |
| `%` | `__mod__` | `__rmod__` | `__imod__` | Modulo |
| `divmod()` | `__divmod__` | `__rdivmod__` | | Returns tuple of floor division quotient and modulo |
| `**`, `pow()` | `__pow__` | `__rpow__` | `__ipow__` | Exponentiation (`pow(a, b, modulo)` calls `a.__pow__(b, modulo)`) |
| `@` | `__matmul__` | `__rmatmul__` | `__imatmul__` | Matrix multiplication |
| `&` | `__and__` | `__rand__` | `__iand__` | Bitwise and |
| `\|` | `__or__` | `__ror__` | `__ior__` | Bitwise or |
| `^` | `__xor__` | `__rxor__` | `__ixor__` | Bitwise xor |
| `<<` | `__lshift__` | `__rlshift__` | `__ilshift__` | Bitwise shift left |
| `>>` | `__rshift__` | `__rrshift__` | `__irshift__` | Bitwise shift right |

The rich comparison operators use a different set of rules.

## Rich Comparison Operators

The handling of the rich comparison operators `==`, `!=`, `>`, `<`, `>=` and `<=` by the
Python interpreter is similar to what we just saw, but differs in two important aspects:

* The same set of methods is used in forward and reverse operator calls.  The rules are
  summarized in the table below.  For example, in the case of `==`, both the forward and
  reverse calls invoke `__eq__()`, only swapping arguments; and a forward call to
  `__gt__()` is followed by a reverse call to `__lt__()` with the arguments swapped.
* In the case of `==` and `!=`, if the reverse method is missing, or returns
  `NotImplemented`, Python compares the object IDs instead of raising `TypeError`.

| Group | Infix operator | Forward method call | Reverse method call | Fallback |
|---|---|---|---|---|
| Equality | `a == b` | `a.__eq__(b)` | `b.__eq__(a)` | Return `id(a) == id(b)` |
| | `a != b` | `a.__ne__(b)` | `b.__ne__(a)` | Return `not (a == b)` |
| Ordering | `a > b` | `a.__gt__(b)` | `b.__lt__(a)` | Raise `TypeError` |
| | `a < b` | `a.__lt__(b)` | `b.__gt__(a)` | Raise `TypeError` |
| | `a >= b` | `a.__ge__(b)` | `b.__le__(a)` | Raise `TypeError` |
| | `a <= b` | `a.__le__(b)` | `b.__ge__(a)` | Raise `TypeError` |

Given these rules, let's review and improve the behavior of the `Vector.__eq__` method,
which was coded as follows in [Special Methods for Sequences](sequence-protocol.md):

<!-- nocheck -->
```python
class Vector:
    # many lines omitted

    def __eq__(self, other):
        return (len(self) == len(other) and
                all(a == b for a, b in zip(self, other)))
```

That method produces these results:

<!-- nocheck -->
```python
va = Vector([1.0, 2.0, 3.0])
vb = Vector(range(1, 4))
va == vb  # two Vector instances with equal numeric components compare equal
# True
vc = Vector([1, 2])
v2d = Vector2d(1, 2)
vc == v2d  # a Vector and a Vector2d are also equal if their components are equal
# True
t3 = (1, 2, 3)
va == t3  # a Vector is also equal to a tuple or any iterable with equal numeric items
# True
```

The last result is probably not desirable.  Do we really want a `Vector` to be considered
equal to a `tuple` containing the same numbers?  There's no hard rule about this; it
depends on the application context.  The Zen of Python says: "In the face of ambiguity,
refuse the temptation to guess."  Excessive liberality in the evaluation of operands may
lead to surprising results, and programmers hate surprises.

Taking a clue from Python itself, we can see that `[1,2] == (1, 2)` is `False`.
Therefore, let's be conservative and do some type checking.  If the second operand is a
`Vector` instance (or an instance of a `Vector` subclass), then use the same logic as the
current `__eq__()`.  Otherwise, return `NotImplemented` and let Python handle that:

<!-- nocheck -->
```python
def __eq__(self, other):
    if isinstance(other, Vector):  # if other is a Vector, compare as before
        return (len(self) == len(other) and
                all(a == b for a, b in zip(self, other)))
    else:
        return NotImplemented  # otherwise, return NotImplemented
```

If you run the same comparisons with the new `Vector.__eq__`, this is what you get:

<!-- nocheck -->
```python
va = Vector([1.0, 2.0, 3.0])
vb = Vector(range(1, 4))
va == vb  # same result as before, as expected
# True
vc = Vector([1, 2])
v2d = Vector2d(1, 2)
vc == v2d  # same result as before, but why? Explanation coming up
# True
t3 = (1, 2, 3)
va == t3  # different result; this is what we wanted. But why does it work?
# False
```

The first result is no news, but the last two were caused by `__eq__()` returning
`NotImplemented`.  Here is what happens in the example with a `Vector` and a `Vector2d`,
`vc == v2d`, step by step:

1. To evaluate `vc == v2d`, Python calls `Vector.__eq__(vc, v2d)`.
2. `Vector.__eq__(vc, v2d)` verifies that `v2d` is not a `Vector` and returns
   `NotImplemented`.
3. Python gets the `NotImplemented` result, so it tries `Vector2d.__eq__(v2d, vc)`.
4. `Vector2d.__eq__(v2d, vc)` turns both operands into tuples and compares them: the
   result is `True` (see `Vector2d.__eq__` in [A Pythonic Object](pythonic-object.md)).

As for the comparison `va == t3`, between `Vector` and `tuple`, the actual steps are:

1. To evaluate `va == t3`, Python calls `Vector.__eq__(va, t3)`.
2. `Vector.__eq__(va, t3)` verifies that `t3` is not a `Vector` and returns
   `NotImplemented`.
3. Python gets the `NotImplemented` result, so it tries `tuple.__eq__(t3, va)`.
4. `tuple.__eq__(t3, va)` has no idea what a `Vector` is, so it returns `NotImplemented`.
5. In the special case of `==`, if the reversed call returns `NotImplemented`, Python
   compares object IDs as a last resort.

We don't need to implement `__ne__()` for `!=` because the fallback behavior of
`__ne__()` inherited from `object` suits us: when `__eq__()` is defined and does not
return `NotImplemented`, `__ne__()` returns that result negated.  In other words, given
the same objects, the results for `!=` are consistent:

<!-- nocheck -->
```python
va != vb
# False
vc != v2d
# False
va != (1, 2, 3)
# True
```

The `__ne__()` inherited from `object` works like the following code — except that the
original is written in C:

<!-- nocheck -->
```python
def __ne__(self, other):
    eq_result = self == other
    if eq_result is NotImplemented:
        return NotImplemented
    else:
        return not eq_result
```

> **Tip**
>
> If you need ordering comparisons too, implement `__eq__()` and one of `__lt__()`,
> `__le__()`, `__gt__()` or `__ge__()`, and decorate the class with
> [`functools.total_ordering`](https://docs.python.org/3/library/functools.html#functools.total_ordering):
> it fills in the remaining comparison methods.  Data classes can generate all of them
> with `@dataclass(order=True)` (see [Data Class Builders](dataclasses.md)).

```python
from functools import total_ordering

@total_ordering
class Version:
    def __init__(self, *parts):
        self.parts = parts

    def __eq__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self.parts == other.parts

    def __lt__(self, other):
        if not isinstance(other, Version):
            return NotImplemented
        return self.parts < other.parts

Version(3, 12) <= Version(3, 15), Version(3, 15) > Version(3, 9, 1)
# (True, True)
```

After covering the essentials of infix operator overloading, let's turn to a different
class of operators: the augmented assignment operators.

## Augmented Assignment Operators

Our `Vector` class already supports the augmented assignment operators `+=` and `*=`.
That's because augmented assignment works with immutable receivers by creating new
instances and rebinding the lefthand variable:

<!-- nocheck -->
```python
v1 = Vector([1, 2, 3])
v1_alias = v1  # create an alias so we can inspect the Vector([1, 2, 3]) object later
id(v1)  # remember the ID of the initial Vector bound to v1
# 4302860128
v1 += Vector([4, 5, 6])  # perform augmented addition
v1  # the expected result...
# Vector([5.0, 7.0, 9.0])
id(v1)  # ...but a new Vector was created
# 4302859904
v1_alias  # inspect v1_alias to confirm the original Vector was not altered
# Vector([1.0, 2.0, 3.0])
v1 *= 11  # perform augmented multiplication
v1  # again, the expected result, but a new Vector was created
# Vector([55.0, 77.0, 99.0])
id(v1)
# 4302858336
```

If a class does not implement the in-place operators listed in the table above, the
augmented assignment operators work as syntactic sugar: `a += b` is evaluated exactly as
`a = a + b`.  That's the expected behavior for immutable types, and if you have
`__add__()`, then `+=` will work with no additional code.

However, if you do implement an in-place operator method such as `__iadd__()`, that
method is called to compute the result of `a += b`.  As the name says, those operators are
expected to change the lefthand operand in place, and not create a new object as the
result.  (This is the same mechanism behind the `list` behavior discussed in
[A `+=` Assignment Puzzler](sequences.md#a--assignment-puzzler).)

> **Warning**
>
> The in-place special methods should never be implemented for immutable types like our
> `Vector` class.  This is fairly obvious, but worth stating anyway.

To show the code of an in-place operator, we will extend the `BingoCage` class from
[Interfaces, Protocols, and ABCs](protocols-abcs.md#subclassing-the-tombola-abc) to
implement `__add__()` and `__iadd__()`.  We'll call the subclass `AddableBingoCage`.  This
is the behavior we want for the `+` operator:

<!-- nocheck -->
```python
vowels = 'AEIOU'
globe = AddableBingoCage(vowels)  # create a globe instance with five items
globe.inspect()
# ('A', 'E', 'I', 'O', 'U')
globe.pick() in vowels  # pop one of the items, and verify it is one of the vowels
# True
len(globe.inspect())  # confirm that the globe is down to four items
# 4
globe2 = AddableBingoCage('XYZ')  # create a second instance, with three items
globe3 = globe + globe2  # create a third instance by adding the previous two
len(globe3.inspect())
# 7
void = globe + [10, 20]  # adding an AddableBingoCage to a list fails
# Traceback (most recent call last):
#   ...
# TypeError: unsupported operand type(s) for +: 'AddableBingoCage' and 'list'
```

Attempting to add an `AddableBingoCage` to a `list` fails with `TypeError`.  That error
message is produced by the Python interpreter when our `__add__()` method returns
`NotImplemented`.  Because an `AddableBingoCage` is mutable, this is how it will work when
we implement `__iadd__()` (continuing from the previous example):

<!-- nocheck -->
```python
globe_orig = globe  # create an alias so we can check the identity of the object later
len(globe.inspect())  # globe has four items here
# 4
globe += globe2  # an AddableBingoCage can receive items from another instance...
len(globe.inspect())
# 7
globe += ['M', 'N']  # ...or from any iterable
len(globe.inspect())
# 9
globe is globe_orig  # throughout this example, globe has always been the same object
# True
globe += 1  # adding a noniterable fails with a proper error message
# Traceback (most recent call last):
#   ...
# TypeError: right operand in += must be 'Tombola' or an iterable
```

Note that the `+=` operator is more liberal than `+` with regard to the second operand.
With `+`, we want both operands to be of the same type (`AddableBingoCage`, in this case),
because if we accepted different types, this might cause confusion as to the type of the
result.  With the `+=`, the situation is clearer: the lefthand object is updated in place,
so there's no doubt about the type of the result.

> **Tip**
>
> This contrasting behavior of `+` and `+=` mirrors the `list` built-in type.  Writing
> `my_list + x`, you can only concatenate one `list` to another `list`, but if you write
> `my_list += x`, you can extend the lefthand `list` with items from any iterable `x` on
> the righthand side.  This is how the `list.extend()` method works: it accepts any
> iterable argument.

Now that we are clear on the desired behavior for `AddableBingoCage`, we can look at its
implementation.  Recall that `BingoCage` is a concrete subclass of the `Tombola` ABC:

<!-- nocheck -->
```python
from tombola import Tombola
from bingo import BingoCage

class AddableBingoCage(BingoCage):  # AddableBingoCage extends BingoCage

    def __add__(self, other):
        if isinstance(other, Tombola):  # __add__ only works with a Tombola as the second operand
            return AddableBingoCage(self.inspect() + other.inspect())
        else:
            return NotImplemented

    def __iadd__(self, other):
        if isinstance(other, Tombola):
            other_iterable = other.inspect()  # retrieve items from other, if it's a Tombola
        else:
            try:
                other_iterable = iter(other)  # otherwise, try to obtain an iterator over other
            except TypeError:  # if that fails, explain what the user should do
                msg = ('right operand in += must be '
                       "'Tombola' or an iterable")
                raise TypeError(msg)
        self.load(other_iterable)  # if we got this far, load other_iterable into self
        return self  # very important: augmented assignment methods must return self
```

In `__iadd__()`, we retrieve items from `other`, if it is an instance of `Tombola`.
Otherwise, we try to obtain an iterator over `other` (the `iter` built-in function is
covered in [Iterators, Generators, and Classic Coroutines](iterators-generators.md); here
we could have used `tuple(other)`, at the cost of building a new tuple when all `.load()`
needs is to iterate over its argument).  If that fails, we raise an exception explaining
what the user should do.  When possible, error messages should explicitly guide the user
to the solution.  If we got this far, we load the `other_iterable` into `self`.

Very important: augmented assignment special methods of mutable objects must return
`self`.  That's what users expect.  We can summarize the whole idea of in-place operators
by contrasting the `return` statements that produce results in `__add__()` and
`__iadd__()`:

`__add__`
: The result is produced by calling the constructor `AddableBingoCage` to build a new
  instance.

`__iadd__`
: The result is produced by returning `self`, after it has been modified.

To wrap up this example, a final observation: by design, no `__radd__()` was coded in
`AddableBingoCage`, because there is no need for it.  The forward method `__add__()` will
only deal with righthand operands of the same type, so if Python is trying to compute
`a + b`, where `a` is an `AddableBingoCage` and `b` is not, we return `NotImplemented` —
maybe the class of `b` can make it work.  But if the expression is `b + a` and `b` is not
an `AddableBingoCage`, and it returns `NotImplemented`, then it's better to let Python
give up and raise `TypeError` because we cannot handle `b`.

> **Tip**
>
> In general, if a forward infix operator method (e.g., `__mul__()`) is designed to work
> only with operands of the same type as `self`, it's useless to implement the
> corresponding reverse method (e.g., `__rmul__()`) because that, by definition, will only
> be invoked when dealing with an operand of a different type.

## The Complete Listing

Here is `vector_v8.py`, consolidating everything implemented since
[Special Methods for Sequences](sequence-protocol.md#formatting) and in this chapter
(the dynamic attribute `__setattr__()` is omitted for brevity):

```python
"""
A multidimensional ``Vector`` class, take 8: operator overloading
"""

from array import array
import reprlib
import math
import functools
import operator
import itertools
from collections import abc

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
        if isinstance(other, Vector):
            return (len(self) == len(other) and
                    all(a == b for a, b in zip(self, other)))
        else:
            return NotImplemented

    def __hash__(self):
        hashes = (hash(x) for x in self)
        return functools.reduce(operator.xor, hashes, 0)

    def __abs__(self):
        return math.hypot(*self)

    def __neg__(self):
        return Vector(-x for x in self)

    def __pos__(self):
        return Vector(self)

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
            coords = itertools.chain([abs(self)], self.angles())
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

    def __add__(self, other):
        try:
            pairs = itertools.zip_longest(self, other, fillvalue=0.0)
            return Vector(a + b for a, b in pairs)
        except TypeError:
            return NotImplemented

    def __radd__(self, other):
        return self + other

    def __mul__(self, scalar):
        try:
            factor = float(scalar)
        except (TypeError, ValueError):
            return NotImplemented
        return Vector(n * factor for n in self)

    def __rmul__(self, scalar):
        return self * scalar

    def __matmul__(self, other):
        if (isinstance(other, abc.Sized) and
            isinstance(other, abc.Iterable)):
            if len(self) == len(other):
                return sum(a * b for a, b in zip(self, other))
            else:
                raise ValueError('@ requires vectors of equal length.')
        else:
            return NotImplemented

    def __rmatmul__(self, other):
        return self @ other
```

And here are tests for the operators covered in this chapter:

```python
v1 = Vector([3, 4, 5])  # unary operators
-v1
# Vector([-3.0, -4.0, -5.0])
+v1
# Vector([3.0, 4.0, 5.0])
~v1
# Traceback (most recent call last):
#   ...
# TypeError: bad operand type for unary ~: 'Vector'
v2 = Vector([6, 7, 8])  # addition
v1 + v2
# Vector([9.0, 11.0, 13.0])
v1 + v2 == Vector([3 + 6, 4 + 7, 5 + 8])
# True
Vector([3, 4, 5, 6]) + Vector([1, 2])  # addition with different lengths
# Vector([4.0, 6.0, 5.0, 6.0])
v1 + (10, 20, 30)  # addition with other iterables, in either order
# Vector([13.0, 24.0, 35.0])
(10, 20, 30) + v1
# Vector([13.0, 24.0, 35.0])
v1 + 1  # addition with incompatible types: standard error messages
# Traceback (most recent call last):
#   ...
# TypeError: unsupported operand type(s) for +: 'Vector' and 'int'
v1 + 'ABC'
# Traceback (most recent call last):
#   ...
# TypeError: unsupported operand type(s) for +: 'Vector' and 'str'
v1 = Vector([1.0, 2.0, 3.0])  # scalar multiplication
14 * v1
# Vector([14.0, 28.0, 42.0])
v1 * True
# Vector([1.0, 2.0, 3.0])
from fractions import Fraction
v1 * Fraction(1, 3)
# Vector([0.3333333333333333, 0.6666666666666666, 1.0])
v1 * 'x'
# Traceback (most recent call last):
#   ...
# TypeError: can't multiply sequence by non-int of type 'Vector'
va = Vector([1, 2, 3])  # dot product with @
vz = Vector([5, 6, 7])
va @ vz == 38.0
# True
[10, 20, 30] @ vz
# 380.0
va @ 3
# Traceback (most recent call last):
#   ...
# TypeError: unsupported operand type(s) for @: 'Vector' and 'int'
vb = Vector(range(1, 4))  # equality
va == vb
# True
va == (1, 2, 3)
# False
va != (1, 2, 3)
# True
v1 = Vector([1, 2, 3])  # augmented assignment creates new objects
v1_alias = v1
v1 += Vector([4, 5, 6])
v1
# Vector([5.0, 7.0, 9.0])
v1_alias
# Vector([1.0, 2.0, 3.0])
v1 *= 11
v1
# Vector([55.0, 77.0, 99.0])
```

Note the error message for `v1 * 'x'`: `Vector.__mul__` returned `NotImplemented`, so
Python tried `str.__rmul__`, and that method's own error message is what we see.

This concludes our exploration of operator overloading in Python.

## Summary

We started this chapter by reviewing some restrictions Python imposes on operator
overloading: no redefining of operators in the built-in types themselves, overloading
limited to existing operators, with a few operators left out (`is`, `and`, `or`, `not`).

We got down to business with the unary operators, implementing `__neg__()` and
`__pos__()`.  Next came the infix operators, starting with `+`, supported by the
`__add__()` method.  We saw that unary and infix operators are supposed to produce results
by creating new objects, and should never change their operands.  To support operations
with other types, we return the `NotImplemented` special value — not an exception —
allowing the interpreter to try again by swapping the operands and calling the reverse
special method for that operator (e.g., `__radd__()`).

Mixing operand types requires detecting operands we can't handle.  In this chapter, we did
this in two ways: in the duck typing way, we just went ahead and tried the operation,
catching a `TypeError` exception if it happened; later, in `__matmul__()`, we did it with
an explicit `isinstance` test.  There are pros and cons to these approaches: duck typing is
more flexible, but explicit type checking is more predictable.

In general, libraries should leverage duck typing — opening the door for objects
regardless of their types, as long as they support the necessary operations.  However,
Python's operator dispatch algorithm may produce misleading error messages or unexpected
results when combined with duck typing.  For this reason, the discipline of type checking
using `isinstance` calls against ABCs is often useful when writing special methods for
operator overloading.  That's goose typing, which we saw in
[Goose Typing](protocols-abcs.md#goose-typing).  Goose typing is a good compromise between
flexibility and safety, because existing or future user-defined types can be declared as
actual or virtual subclasses of an ABC.  In addition, if an ABC implements the
`__subclasshook__()`, then objects pass `isinstance` checks against that ABC by providing
the required methods — no subclassing or registration required.

The next topic we covered was the rich comparison operators.  We implemented `==` with
`__eq__()` and discovered that Python provides a handy implementation of `!=` in the
`__ne__()` inherited from the `object` base class.  The way Python evaluates these
operators along with `>`, `<`, `>=` and `<=` is slightly different, with special logic for
choosing the reverse method, and fallback handling for `==` and `!=`, which never generate
errors because Python compares the object IDs as a last resort.

In the last section, we focused on augmented assignment operators.  We saw that Python
handles them by default as a combination of plain operator followed by assignment, that
is: `a += b` is evaluated exactly as `a = a + b`.  That always creates a new object, so it
works for mutable or immutable types.  For mutable objects, we can implement in-place
special methods such as `__iadd__()` for `+=`, and alter the value of the lefthand
operand.  To show this at work, we left behind the immutable `Vector` class and worked on
implementing a `BingoCage` subclass to support `+=` for adding items to the random pool,
similar to the way the `list` built-in supports `+=` as a shortcut for the
`list.extend()` method.  While doing this, we discussed how `+` tends to be stricter than
`+=` regarding the types it accepts.

> **Note**
>
> If you look closely at the `v1 + 'ABC'` traceback in the first version of `__add__()`,
> you'll see evidence of the lazy evaluation of generator expressions.  The `Vector` call
> gets a generator expression as its `components` argument — no problem at that stage.
> The genexp is passed to the `array` constructor, which tries to iterate over it, causing
> the evaluation of the first item `a + b`.  That's when the `TypeError` occurs, and the
> exception propagates up through the `Vector` constructor call.  If the constructor were
> invoked as `Vector([a + b for a, b in pairs])`, the exception would happen right there,
> because the list comprehension builds a list before the call; the body of
> `Vector.__init__` would not be reached at all.

> **See also**
>
> * Guido van Rossum, ["Why operators are useful"](https://neopythonic.blogspot.com/2019/03/why-operators-are-useful.html),
>   a good defense of operator overloading.
> * Trey Hunner, ["Tuple ordering and deep comparisons in Python"](https://treyhunner.com/2019/03/python-deep-comparisons-and-code-readability/).
> * The [Data model](https://docs.python.org/3/reference/datamodel.html#emulating-numeric-types)
>   chapter of the Language Reference, and
>   ["Implementing the arithmetic operations"](https://docs.python.org/3/library/numbers.html#implementing-the-arithmetic-operations)
>   in the `numbers` module docs.
> * A clever nonarithmetic example of operator overloading is in `pathlib`: `Path`
>   overloads `/` to build filesystem paths, as in `Path('/etc') / 'init.d' / 'reboot'`.
>   The Scapy library uses `/` to stack network protocol layers in packets.
> * Dan Ingalls, "A Simple Technique for Handling Multiple Polymorphism", and Kurt J.
>   Hebel and Ralph Johnson, "Arithmetic and Double Dispatching in Smalltalk-80", for the
>   double-dispatch alternative that Python's forward/reverse algorithm replaces.
