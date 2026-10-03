# Data Class Builders

Python offers a few ways to build a simple class that is just a collection of
fields, with little or no extra functionality.  That pattern is known as a
*data class*, and [`dataclasses`](https://docs.python.org/3/library/dataclasses.html)
is one of the packages that supports it.  This chapter covers three class
builders you can use as shortcuts to write data classes:

[`collections.namedtuple`](https://docs.python.org/3/library/collections.html#collections.namedtuple)
: the simplest way, available since Python 2.6.

[`typing.NamedTuple`](https://docs.python.org/3/library/typing.html#typing.NamedTuple)
: an alternative that requires type hints on the fields, with class syntax
  available since Python 3.6.

[`@dataclasses.dataclass`](https://docs.python.org/3/library/dataclasses.html#dataclasses.dataclass)
: a class decorator that allows more customization than the previous
  alternatives, adding lots of options and potential complexity; available since
  Python 3.7.

After covering those builders, we discuss why "Data Class" is also the name of a
*code smell*: a pattern that may be a symptom of poor object-oriented design.
The chapter ends with pattern matching on class instances.  It assumes you have
read [Classes](classes.md), especially [A First Look at Classes](classes.md#tut-firstclasses).

> **Note**
>
> [`typing.TypedDict`](https://docs.python.org/3/library/typing.html#typing.TypedDict)
> may look like another data class builder.  It uses similar syntax and is
> documented right after `typing.NamedTuple`.  However, `TypedDict` does not
> build concrete classes that you can instantiate.  It is just syntax to write
> type hints for function parameters and variables that accept mappings used as
> records, with keys as field names.  It is covered in
> [More About Type Hints](type-hints-more.md#typeddict).

## Overview of Data Class Builders

Consider a simple class to represent a geographic coordinate pair:

```python
class Coordinate:

    def __init__(self, lat, lon):
        self.lat = lat
        self.lon = lon
```

That `Coordinate` class does the job of holding latitude and longitude
attributes.  But writing the `__init__()` boilerplate gets old fast, especially
if your class has more than a couple of attributes: each of them is mentioned
three times!  And that boilerplate doesn't buy you basic features you'd expect
from a Python object:

```python
moscow = Coordinate(55.76, 37.62)
moscow  # the __repr__ inherited from object is not very helpful
# <__main__.Coordinate object at 0x107142f10>
location = Coordinate(55.76, 37.62)
location == moscow  # meaningless ==: object.__eq__ compares object ids
# False
(location.lat, location.lon) == (moscow.lat, moscow.lon)
# True
```

Comparing two coordinates requires an explicit comparison of each attribute.
The data class builders covered in this chapter provide the necessary
`__init__()`, `__repr__()` and `__eq__()` methods automatically, as well as other
useful features.

> **Note**
>
> None of these class builders depends on inheritance to do its work.  Both
> `collections.namedtuple` and `typing.NamedTuple` build classes that are `tuple`
> subclasses.  `@dataclass` is a class decorator that does not affect the class
> hierarchy in any way.  Each of them uses different metaprogramming techniques
> to inject methods and data attributes into the class under construction.

Here is a `Coordinate` class built with `namedtuple`, a factory function that
builds a subclass of `tuple` with the name and fields you specify:

```python
from collections import namedtuple
Coordinate = namedtuple('Coordinate', 'lat lon')
issubclass(Coordinate, tuple)
# True
moscow = Coordinate(55.756, 37.617)
moscow  # useful __repr__
# Coordinate(lat=55.756, lon=37.617)
moscow == Coordinate(lat=55.756, lon=37.617)  # meaningful __eq__
# True
```

The newer `typing.NamedTuple` provides the same functionality, adding a type
annotation to each field:

```python
import typing
Coordinate = typing.NamedTuple('Coordinate',
    [('lat', float), ('lon', float)])
issubclass(Coordinate, tuple)
# True
typing.get_type_hints(Coordinate)
# {'lat': <class 'float'>, 'lon': <class 'float'>}
```

> **Tip**
>
> A typed named tuple can also be constructed with the fields given as keyword
> arguments, like this: `Coordinate = typing.NamedTuple('Coordinate', lat=float,
> lon=float)`.  This is more readable, and also lets you provide the mapping of
> fields and types as `**fields_and_types`.  (Recent versions of Python deprecate
> this keyword-argument form in favor of the class syntax below.)

`typing.NamedTuple` can also be used in a `class` statement, with type
annotations written as described in [**PEP 526**](https://peps.python.org/pep-0526/).
This is much more readable, and makes it easy to override methods or add new
ones.  Here is the same `Coordinate` class, with a pair of `float` attributes and a
custom `__str__()` that displays a coordinate formatted like `55.8°N, 37.6°E`:

```python
from typing import NamedTuple

class Coordinate(NamedTuple):
    lat: float
    lon: float

    def __str__(self):
        ns = 'N' if self.lat >= 0 else 'S'
        we = 'E' if self.lon >= 0 else 'W'
        return f'{abs(self.lat):.1f}°{ns}, {abs(self.lon):.1f}°{we}'

print(Coordinate(55.756, 37.617))
# 55.8°N, 37.6°E
```

> **Warning**
>
> Although `NamedTuple` appears in the `class` statement as a superclass, it
> actually is not one.  `typing.NamedTuple` uses the advanced functionality of a
> metaclass (see [Class Metaprogramming](class-metaprogramming.md)) to customize
> the creation of the user's class.  Check this out:
>
> ```python
> issubclass(Coordinate, typing.NamedTuple)
> # False
> issubclass(Coordinate, tuple)
> # True
> ```

In the `__init__()` method generated by `typing.NamedTuple`, the fields appear as
parameters in the same order they appear in the `class` statement.

Like `typing.NamedTuple`, the `dataclass` decorator supports the PEP 526 syntax to
declare instance attributes.  The decorator reads the variable annotations and
automatically generates methods for your class.  For comparison, here is the
equivalent `Coordinate` class written with the help of `@dataclass`:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Coordinate:
    lat: float
    lon: float

    def __str__(self):
        ns = 'N' if self.lat >= 0 else 'S'
        we = 'E' if self.lon >= 0 else 'W'
        return f'{abs(self.lat):.1f}°{ns}, {abs(self.lon):.1f}°{we}'
```

The bodies of the last two classes are identical; the difference is in the
`class` statement itself.  The `@dataclass` decorator does not depend on
inheritance or a metaclass, so it should not interfere with your own use of
these mechanisms.  (Class decorators are covered in
[Class Metaprogramming](class-metaprogramming.md).)  This `Coordinate` class is a
subclass of `object`.

### Main Features

The different data class builders have a lot in common, as this table shows
(`x` stands for an instance of a data class of that kind):

| | `namedtuple` | `NamedTuple` | `dataclass` |
|---|---|---|---|
| mutable instances | NO | NO | YES |
| `class` statement syntax | NO | YES | YES |
| construct `dict` | `x._asdict()` | `x._asdict()` | `dataclasses.asdict(x)` |
| get field names | `x._fields` | `x._fields` | `[f.name for f in dataclasses.fields(x)]` |
| get defaults | `x._field_defaults` | `x._field_defaults` | `[f.default for f in dataclasses.fields(x)]` |
| get field types | N/A | `x.__annotations__` | `x.__annotations__` |
| new instance with changes | `x._replace(...)` | `x._replace(...)` | `dataclasses.replace(x, ...)` |
| new class at runtime | `namedtuple(...)` | `NamedTuple(...)` | `dataclasses.make_dataclass(...)` |

> **Warning**
>
> The classes built by `typing.NamedTuple` and `@dataclass` have an
> `__annotations__` attribute holding the type hints for the fields.  However,
> reading `__annotations__` directly is not recommended.  The best practice is to
> call [`annotationlib.get_annotations()`](https://docs.python.org/3/library/annotationlib.html)
> (Python 3.14+), `inspect.get_annotations()` (Python 3.10+), or
> `typing.get_type_hints()`, because those functions provide extra services, like
> resolving forward references in type hints.  More on this in
> [Problems with Annotations at Runtime](type-hints-more.md#problems-with-annotations-at-runtime).

*Mutable instances*
: A key difference between these class builders is that `collections.namedtuple`
  and `typing.NamedTuple` build `tuple` subclasses, so their instances are
  immutable.  By default, `@dataclass` produces mutable classes.  But the
  decorator accepts a keyword argument `frozen`, as shown above.  With
  `frozen=True`, the class raises an exception if you try to assign a value to a
  field after the instance is initialized.

*Class statement syntax*
: Only `typing.NamedTuple` and `dataclass` support the regular `class` statement
  syntax, making it easier to add methods and docstrings to the class you are
  creating.

*Construct dict*
: Both named tuple variants provide an instance method (`._asdict`) to construct a
  `dict` object from the fields of an instance.  The `dataclasses` module provides
  a function to do it: `dataclasses.asdict`.

*Get field names and default values*
: All three class builders let you get the field names and any default values
  configured for them.  In named tuple classes, that metadata is in the
  `._fields` and `._field_defaults` class attributes.  You can get the same
  metadata from a `dataclass`-decorated class using the `fields` function from
  the `dataclasses` module.  It returns a tuple of `Field` objects that have
  several attributes, including `name` and `default`.

*Get field types*
: Classes defined with the help of `typing.NamedTuple` and `@dataclass` have a
  mapping of field names to types, as explained in the warning above.

*New instance with changes*
: Given a named tuple instance `x`, the call `x._replace(**kwargs)` returns a new
  instance with some attribute values replaced according to the keyword
  arguments given.  The module-level function `dataclasses.replace(x, **kwargs)`
  does the same for an instance of a `dataclass`-decorated class.  (Since
  Python 3.13, the generic [`copy.replace()`](https://docs.python.org/3/library/copy.html#copy.replace)
  function works with both.)

*New class at runtime*
: Although the `class` statement syntax is more readable, it is hardcoded.  A
  framework may need to build data classes on the fly, at runtime.  For that, you
  can use the function call syntax of `collections.namedtuple`, which is likewise
  supported by `typing.NamedTuple`.  The `dataclasses` module provides a
  `make_dataclass` function for the same purpose.

```python
import dataclasses
Point = dataclasses.make_dataclass('Point', [('x', float), ('y', float, 0.0)])
p = Point(1.5)
p
# Point(x=1.5, y=0.0)
dataclasses.asdict(p)
# {'x': 1.5, 'y': 0.0}
dataclasses.replace(p, y=2)
# Point(x=1.5, y=2)
```

Now let's focus on each builder in turn, starting with the simplest.

## Classic Named Tuples

The `collections.namedtuple` function is a factory that builds subclasses of
`tuple` enhanced with field names, a class name and an informative
`__repr__()`.  Classes built with `namedtuple` can be used anywhere tuples are
needed, and in fact many functions of the standard library that used to return
tuples now return named tuples for convenience, without affecting user code at
all.

> **Tip**
>
> Each instance of a class built by `namedtuple` takes exactly the same amount of
> memory as a tuple, because the field names are stored in the class.

Here is a named tuple to hold information about a city:

```python
from collections import namedtuple
City = namedtuple('City', 'name country population coordinates')
tokyo = City('Tokyo', 'JP', 36.933, (35.689722, 139.691667))
tokyo
# City(name='Tokyo', country='JP', population=36.933, coordinates=(35.689722,
# 139.691667))
tokyo.population
# 36.933
tokyo.coordinates
# (35.689722, 139.691667)
tokyo[1]
# 'JP'
```

Two parameters are required to create a named tuple: a class name and a list of
field names, which can be given as an iterable of strings or as a single
space-delimited string.  Field values must be passed as separate positional
arguments to the constructor (in contrast, the `tuple` constructor takes a single
iterable).  You can access the fields by name or by position.

As a `tuple` subclass, `City` inherits useful methods such as `__eq__()` and the
special methods for comparison operators, including `__lt__()`, which allows
sorting lists of `City` instances.

A named tuple offers a few attributes and methods in addition to those inherited
from `tuple`.  The most useful are the `_fields` class attribute, the class
method `_make(iterable)`, and the `_asdict()` instance method:

```python
City = namedtuple('City', 'name country population location')
City._fields  # a tuple with the field names of the class
# ('name', 'country', 'population', 'location')
Coordinate = namedtuple('Coordinate', 'lat lon')
delhi_data = ('Delhi NCR', 'IN', 21.935, Coordinate(28.613889, 77.208889))
delhi = City._make(delhi_data)  # City(*delhi_data) would do the same
delhi._asdict()  # a dict built from the named tuple instance
# {'name': 'Delhi NCR', 'country': 'IN', 'population': 21.935,
#  'location': Coordinate(lat=28.613889, lon=77.208889)}
import json
json.dumps(delhi._asdict())  # useful to serialize the data in JSON format
# '{"name": "Delhi NCR", "country": "IN", "population": 21.935, "location": [28.613889, 77.208889]}'
```

> **Note**
>
> The `_asdict` method returned an `OrderedDict` until Python 3.7.  Since Python
> 3.8 it returns a simple `dict`, which is fine now that we can rely on key
> insertion order.  If you must have an `OrderedDict`, build one from the result:
> `OrderedDict(x._asdict())`.

`namedtuple` also accepts the `defaults` keyword-only argument, providing an
iterable of *N* default values for each of the *N* rightmost fields of the class.
Here is a `Coordinate` named tuple with a default value for a `reference` field:

```python
Coordinate = namedtuple('Coordinate', 'lat lon reference', defaults=['WGS84'])
Coordinate(0, 0)
# Coordinate(lat=0, lon=0, reference='WGS84')
Coordinate._field_defaults
# {'reference': 'WGS84'}
```

### Hacking a `namedtuple` to Inject a Method

It is easier to write methods with the class syntax supported by
`typing.NamedTuple` and `@dataclass`.  You can also add methods to a
`namedtuple`, but it's a hack.  Recall how the `Card` class was built in
[The Python Data Model](data-model.md):

<!-- nocheck -->
```python
Card = collections.namedtuple('Card', ['rank', 'suit'])
```

Later in that chapter we wrote a `spades_high` function for sorting.  It would be
nice if that logic were encapsulated in a method of `Card`, but adding it without
a `class` statement requires a quick hack: define the function and then assign it
to a class attribute:

```python
import collections
Card = collections.namedtuple('Card', ['rank', 'suit'])
ranks = [str(n) for n in range(2, 11)] + list('JQKA')

Card.suit_values = dict(spades=3, hearts=2, diamonds=1, clubs=0)
def spades_high(card):
    rank_value = ranks.index(card.rank)
    suit_value = card.suit_values[card.suit]
    return rank_value * len(card.suit_values) + suit_value

Card.overall_rank = spades_high
lowest_card = Card('2', 'clubs')
highest_card = Card('A', 'spades')
lowest_card.overall_rank()
# 0
highest_card.overall_rank()
# 51
```

We attach a class attribute with values for each suit, then attach the function
to the `Card` class as a method named `overall_rank`.  `spades_high` will become a
method; its first argument doesn't need to be named `self`, but it will get the
receiver anyway when called as a method.  It works!

For readability and future maintenance, it is much better to write methods
inside a `class` statement, but it is good to know this hack is possible.  It is
also not common practice in Python, partly because it doesn't work with any
built-in type (`str`, `list` and so on), which many consider a blessing.

## Typed Named Tuples

The `Coordinate` class with a default field can be written using
`typing.NamedTuple`:

```python
from typing import NamedTuple

class Coordinate(NamedTuple):
    lat: float
    lon: float
    reference: str = 'WGS84'
```

Every instance field must be annotated with a type, and the `reference` field is
annotated with a type and a default value.  Classes built by `typing.NamedTuple`
don't have any methods beyond those that `collections.namedtuple` also generates,
plus those inherited from `tuple`.  The only difference is the presence of the
`__annotations__` class attribute, which Python ignores at runtime.

Given that the main feature of `typing.NamedTuple` is type annotations, let's
take a brief look at them before continuing.

## Type Hints 101

Type hints, also known as type annotations, are ways to declare the expected type
of function arguments, return values, variables and attributes.  The first thing
you need to know about them is that they are not enforced at all by the Python
bytecode compiler and interpreter.

> **Note**
>
> This is a very brief introduction to type hints, just enough to make sense of the
> syntax and meaning of the annotations used in `typing.NamedTuple` and
> `@dataclass` declarations.  Type hints for function signatures are covered in
> [Type Hints in Functions](type-hints-functions.md), and more advanced
> annotations in [More About Type Hints](type-hints-more.md).

### No Runtime Effect

Think of Python type hints as "documentation that can be verified by IDEs and
type checkers".  That's because they have no impact on the runtime behavior of
Python programs:

```python
import typing
class Coordinate(typing.NamedTuple):
    lat: float
    lon: float

trash = Coordinate('Ni!', None)
print(trash)  # no type checking at runtime!
# Coordinate(lat='Ni!', lon=None)
```

If you put that code in a module, it will run and display a meaningless
`Coordinate`, with no error or warning:

```console
$ python3 nocheck_demo.py
Coordinate(lat='Ni!', lon=None)
```

Type hints are intended primarily to support third-party type checkers, like
[Mypy](https://mypy-lang.org/) or the type checker built into an IDE.  These are
*static analysis* tools: they check Python source code "at rest", not running
code.  To see the effect of type hints, you must run one of those tools on your
code, like a linter.  For instance, here is what Mypy has to say about the
previous example:

```console
$ mypy nocheck_demo.py
nocheck_demo.py:8: error: Argument 1 to "Coordinate" has
incompatible type "str"; expected "float"
nocheck_demo.py:8: error: Argument 2 to "Coordinate" has
incompatible type "None"; expected "float"
```

Given the definition of `Coordinate`, Mypy knows that both arguments to create an
instance must be of type `float`, but the assignment to `trash` uses a `str` and
`None`.  (In the context of type hints, `None` is not the `NoneType` singleton but
an alias for `NoneType` itself.  That's strange when you think about it, but it
appeals to intuition and makes return annotations easier to read in the common
case of functions that return `None`.)

### Variable Annotation Syntax

Both `typing.NamedTuple` and `@dataclass` use the syntax of variable annotations
defined in PEP 526.  The basic syntax is:

<!-- nocheck -->
```python
var_name: some_type
```

The "Acceptable type hints" section of [**PEP 484**](https://peps.python.org/pep-0484/)
explains what types are acceptable, but in the context of defining a data class,
these are the most useful:

* a concrete class, for example `str` or `FrenchDeck`;
* a parameterized collection type, like `list[int]`, `tuple[str, float]`, etc.;
* an optional type, like `str | None` (or `typing.Optional[str]`), to declare a
  field that can be a `str` or `None`.

You can also initialize the variable with a value.  In a `typing.NamedTuple` or
`@dataclass` declaration, that value becomes the default for the attribute if the
corresponding argument is omitted in the constructor call:

<!-- nocheck -->
```python
var_name: some_type = a_value
```

### The Meaning of Variable Annotations

Type hints have no effect at runtime, but when a module is loaded Python does
record them, so that `typing.NamedTuple` and `@dataclass` can use them to enhance
the class.  Let's start with a plain class, to see later what extra features are
added by the class builders:

```python
class DemoPlainClass:
    a: int
    b: float = 1.1
    c = 'spam'
```

Here `a` becomes an annotation, but is otherwise discarded: no attribute named `a`
is created in the class.  `b` is saved as an annotation, and also becomes a class
attribute with value `1.1`.  `c` is just a plain old class attribute, not an
annotation.  We can verify that by reading the annotations of `DemoPlainClass` and
then trying to get its attributes:

```python
import inspect
inspect.get_annotations(DemoPlainClass)
# {'a': <class 'int'>, 'b': <class 'float'>}
DemoPlainClass.a
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# AttributeError: type object 'DemoPlainClass' has no attribute 'a'
DemoPlainClass.b
# 1.1
DemoPlainClass.c
# 'spam'
```

The annotations are recorded by the interpreter even in a plain class.  The `a`
survives only as an annotation; it doesn't become a class attribute because no
value is bound to it.  (Python has no concept of "undefined", unlike JavaScript.)
The `b` and `c` are stored as class attributes because they are bound to values.

None of those three attributes will be in a new instance of `DemoPlainClass`.  If
you create an object `o = DemoPlainClass()`, `o.a` raises `AttributeError`, while
`o.b` and `o.c` retrieve the class attributes with values `1.1` and `'spam'`;
that's just normal Python object behavior.

#### Inspecting a `typing.NamedTuple`

Now let's examine a class built with `typing.NamedTuple`, using the same
attributes and annotations:

```python
import typing

class DemoNTClass(typing.NamedTuple):
    a: int
    b: float = 1.1
    c = 'spam'
```

Here `a` becomes an annotation and also an instance attribute; `b` is another
annotation, and also becomes an instance attribute with default value `1.1`; `c`
is just a plain old class attribute, with no annotation referring to it.
Inspecting the class:

```python
inspect.get_annotations(DemoNTClass)
# {'a': <class 'int'>, 'b': <class 'float'>}
DemoNTClass.a
# _tuplegetter(0, 'Alias for field number 0')
DemoNTClass.b
# _tuplegetter(1, 'Alias for field number 1')
DemoNTClass.c
# 'spam'
```

We have the same annotations for `a` and `b`, but `typing.NamedTuple` creates `a`
and `b` class attributes.  Those attributes are *descriptors*, an advanced feature
covered in [Attribute Descriptors](descriptors.md).  For now, think of them as
similar to property getters: methods that don't require the explicit call
operator `()` to retrieve an instance attribute.  In practice, this means `a` and
`b` work as read-only instance attributes, which makes sense when you recall that
`DemoNTClass` instances are just fancy tuples, and tuples are immutable.
`DemoNTClass` also gets a custom docstring:

```python
DemoNTClass.__doc__
# 'DemoNTClass(a, b)'
```

Let's inspect an instance:

```python
nt = DemoNTClass(8)
nt.a
# 8
nt.b
# 1.1
nt.c
# 'spam'
```

To construct `nt`, we need to give at least the `a` argument; the constructor also
takes a `b` argument, but it has a default value of `1.1`, so it's optional.  The
`nt` object has the `a` and `b` attributes as expected; it doesn't have a `c`
attribute, but Python retrieves it from the class, as usual.  If you try to assign
values to `nt.a`, `nt.b`, `nt.c`, or even `nt.z`, you'll get `AttributeError`
exceptions with subtly different error messages.  Try that and reflect on the
messages.

#### Inspecting a Class Decorated with `dataclass`

Now the same class decorated with `@dataclass`:

```python
from dataclasses import dataclass

@dataclass
class DemoDataClass:
    a: int
    b: float = 1.1
    c = 'spam'
```

`a` becomes an annotation and also an instance attribute; `b` is another
annotation, and also becomes an instance attribute with a default value `1.1`;
`c` is just a plain old class attribute.  Let's check out the annotations, the
docstring, and the `a`, `b`, `c` attributes on `DemoDataClass`:

```python
inspect.get_annotations(DemoDataClass)
# {'a': <class 'int'>, 'b': <class 'float'>}
DemoDataClass.__doc__
# 'DemoDataClass(a: int, b: float = 1.1)'
DemoDataClass.a
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# AttributeError: type object 'DemoDataClass' has no attribute 'a'
DemoDataClass.b
# 1.1
DemoDataClass.c
# 'spam'
```

The annotations and docstring are not surprising.  However, there is no attribute
named `a` in `DemoDataClass`, in contrast with `DemoNTClass`, which has a
descriptor to get `a` from the instances as a read-only attribute.  That's because
the `a` attribute will only exist in instances of `DemoDataClass`.  It will be a
public attribute that you can get and set, unless the class is frozen.  But `b`
and `c` exist as class attributes, with `b` holding the default value for the `b`
instance attribute, while `c` is just a class attribute that will not be bound to
the instances.  Now let's see a `DemoDataClass` instance:

```python
dc = DemoDataClass(9)
dc.a
# 9
dc.b
# 1.1
dc.c
# 'spam'
```

Again, `a` and `b` are instance attributes, and `c` is a class attribute we get
through the instance.  As mentioned, `DemoDataClass` instances are mutable, and no
type checking is done at runtime:

```python
dc.a = 10
dc.b = 'oops'
```

We can do even sillier assignments:

```python
dc.c = 'whatever'
dc.z = 'secret stash'
```

Now the `dc` instance has a `c` attribute, but that does not change the `c` class
attribute.  And we can add a new `z` attribute.  This is normal Python behavior:
regular instances can have their own attributes that don't appear in the class.
(Setting attributes after `__init__()` does defeat the key-sharing memory
optimization described in
[Practical Consequences of How `dict` Works](dicts-sets.md#practical-consequences-of-how-dict-works).)

## More About `@dataclass`

So far we've only seen simple uses of `@dataclass`.  The decorator accepts several
keyword arguments.  These are the most commonly used, in the order of its
signature, `@dataclass(*, init=True, repr=True, eq=True, order=False,
unsafe_hash=False, frozen=False, ...)`:

| Option | Meaning | Default | Notes |
|---|---|---|---|
| `init` | generate `__init__` | `True` | ignored if `__init__` is implemented by the user |
| `repr` | generate `__repr__` | `True` | ignored if `__repr__` is implemented by the user |
| `eq` | generate `__eq__` | `True` | ignored if `__eq__` is implemented by the user |
| `order` | generate `__lt__`, `__le__`, `__gt__`, `__ge__` | `False` | if `True`, raises exceptions if `eq=False`, or if any of the comparison methods that would be generated are defined or inherited |
| `unsafe_hash` | generate `__hash__` | `False` | complex semantics and several caveats; see the `dataclass` documentation |
| `frozen` | make instances "immutable" | `False` | instances will be reasonably safe from accidental change, but not really immutable |
| `match_args` | generate `__match_args__` | `True` | used by positional class patterns (Python 3.10+) |
| `kw_only` | make all fields keyword-only | `False` | Python 3.10+ |
| `slots` | generate `__slots__` | `False` | Python 3.10+; see [Saving Memory with `__slots__`](pythonic-object.md#saving-memory-with-__slots__) |

The `*` in the first position of the signature means the parameters are
keyword-only.  `@dataclass` emulates immutability by generating `__setattr__()`
and `__delattr__()` methods, which raise `dataclasses.FrozenInstanceError`, a
subclass of `AttributeError`, when you attempt to set or delete a field.

The defaults are the most useful settings for common use cases.  The options you
are most likely to change from the defaults are:

`frozen=True`
: protects against accidental changes to the class instances.

`order=True`
: allows sorting of instances of the data class.

Given the dynamic nature of Python objects, it's not too hard for a nosy
programmer to get around the protection afforded by `frozen=True`.  But the
necessary tricks should be easy to spot in a code review.

If the `eq` and `frozen` arguments are both `True`, `@dataclass` produces a suitable
`__hash__()` method, so the instances are hashable.  The generated `__hash__()`
uses data from all fields that are not individually excluded using a field option
you'll see shortly.  If `frozen=False` (the default), `@dataclass` sets `__hash__` to
`None`, signaling that the instances are unhashable, and therefore overriding
`__hash__()` from any superclass.

[**PEP 557**](https://peps.python.org/pep-0557/) says of `unsafe_hash` that, although
not recommended, you can force data classes to create a `__hash__()` method with
`unsafe_hash=True`.  This might be the case if your class is logically immutable
but can nonetheless be mutated.  It is a specialized use case and should be
considered carefully.

Further customization of the generated data class can be done at the field level.

### Field Options

You've already seen the most basic field option: providing (or not) a default
value with the type hint.  The instance fields you declare become parameters in
the generated `__init__()`.  Python does not allow parameters without defaults
after parameters with defaults, so after you declare a field with a default value,
all remaining fields must also have default values.

Mutable default values are a common source of bugs for beginners.  In function
definitions, a mutable default value is easily corrupted when one invocation of
the function mutates the default, changing the behavior of later invocations
(the tutorial warns about this in [Default Argument Values](controlflow.md#tut-defaultargs),
and [Mutable Types as Parameter Defaults: Bad Idea](references.md#mutable-types-as-parameter-defaults-bad-idea)
explores it further).  Class attributes are often used as default values for
instance attributes, including in data classes, and `@dataclass` uses the default
values in the type hints to generate parameters with defaults for `__init__()`.  To
prevent bugs, `@dataclass` rejects this class definition:

<!-- nocheck -->
```python
@dataclass
class ClubMember:
    name: str
    guests: list = []
```

If you load a module with that `ClubMember` class, this is what you get:

```console
$ python3 club_wrong.py
Traceback (most recent call last):
  File "club_wrong.py", line 4, in <module>
    class ClubMember:
  ...several lines omitted...
ValueError: mutable default <class 'list'> for field guests is not allowed:
use default_factory
```

The `ValueError` message explains the problem and suggests a solution: use
`default_factory`.  Here is how to correct `ClubMember`:

```python
from dataclasses import dataclass, field

@dataclass
class ClubMember:
    name: str
    guests: list = field(default_factory=list)
```

In the `guests` field, instead of a literal list, the default value is set by
calling the `dataclasses.field` function with `default_factory=list`.  The
`default_factory` parameter lets you provide a function, class, or any other
callable, which is invoked with zero arguments to build a default value each time
an instance of the data class is created.  This way, each instance of
`ClubMember` has its own list, instead of all instances sharing the same list from
the class, which is rarely what you want and is often a bug.

> **Warning**
>
> It's good that `@dataclass` rejects class definitions with a `list` default
> value in a field.  However, be aware that this is a partial solution: it only
> applies to unhashable defaults such as `list`, `dict` and `set`.  Other mutable
> values used as defaults will not be flagged by `@dataclass`.  It's up to you to
> understand the problem and remember to use a default factory to set mutable
> default values.

The `dataclasses` documentation defines a `list` field with more precise syntax:

```python
from dataclasses import dataclass, field

@dataclass
class ClubMember:
    name: str
    guests: list[str] = field(default_factory=list)
```

`list[str]` means "a list of `str`".  It is a *parameterized generic type*: since
Python 3.9 the `list` built-in accepts that bracket notation to specify the type
of the list items.  (Before that, you had to import `List` from `typing` and write
`List[str]`.)  Generics are covered in [Type Hints in Functions](type-hints-functions.md).
Both definitions are correct, and Mypy accepts both.  The difference is that
`guests: list` means `guests` can be a list of objects of any kind, while
`guests: list[str]` says that every item must be a `str`.  This lets the type
checker find (some) bugs in code that puts invalid items in the list, or that
reads items from it.

`default_factory` is probably the most common option of the `field` function,
but there are several others:

| Option | Meaning | Default |
|---|---|---|
| `default` | default value for the field | `MISSING` (a sentinel indicating that the option was not provided, so that `None` can be an actual default) |
| `default_factory` | 0-parameter function used to produce a default | `MISSING` |
| `init` | include the field in the parameters of `__init__` | `True` |
| `repr` | include the field in `__repr__` | `True` |
| `compare` | use the field in comparison methods `__eq__`, `__lt__`, etc. | `True` |
| `hash` | include the field in the `__hash__` calculation | `None` (the field is used in `__hash__` only if `compare=True`) |
| `metadata` | mapping with user-defined data; ignored by `@dataclass` | `None` |
| `kw_only` | make the field keyword-only (Python 3.10+) | `MISSING` (use the class-level setting) |

The `default` option exists because the `field` call takes the place of the
default value in the field annotation.  If you want to create an `athlete` field
with a default value of `False`, and also omit that field from `__repr__()`, you'd
write this:

```python
@dataclass
class ClubMember:
    name: str
    guests: list = field(default_factory=list)
    athlete: bool = field(default=False, repr=False)

ClubMember('Mary', athlete=True)
# ClubMember(name='Mary', guests=[])
```

### Post-init Processing

The `__init__()` generated by `@dataclass` only takes the arguments passed and
assigns them, or their default values if missing, to the instance fields.  But you
may need to do more than that to initialize the instance.  If that's the case, you
can provide a `__post_init__()` method.  When that method exists, `@dataclass`
adds code to the generated `__init__()` to call `__post_init__()` as the last step.
Common use cases for `__post_init__()` are validation and computing field values
based on other fields.

We'll look at a simple example that does both.  First, the expected behavior of a
`ClubMember` subclass named `HackerClubMember`.  `HackerClubMember` objects accept
an optional `handle` argument; if `handle` is omitted, it is set to the first part
of the member's name; and members must have unique handles:

<!-- nocheck -->
```python
anna = HackerClubMember('Anna Ravenscroft', handle='AnnaRaven')
anna
# HackerClubMember(name='Anna Ravenscroft', guests=[], handle='AnnaRaven')
leo = HackerClubMember('Leo Rochael')
leo
# HackerClubMember(name='Leo Rochael', guests=[], handle='Leo')
leo2 = HackerClubMember('Leo DaVinci')
# Traceback (most recent call last):
#   ...
# ValueError: handle 'Leo' already exists.
leo2 = HackerClubMember('Leo DaVinci', handle='Neo')
leo2
# HackerClubMember(name='Leo DaVinci', guests=[], handle='Neo')
```

Note that we must provide `handle` as a keyword argument, because
`HackerClubMember` inherits `name` and `guests` from `ClubMember` and adds the
`handle` field after them.  The generated docstring shows the order of the fields
in the constructor call:

<!-- nocheck -->
```python
HackerClubMember.__doc__
# "HackerClubMember(name: str, guests: list = <factory>, handle: str = '')"
```

Here, `<factory>` is a short way of saying that some callable will produce the
default value for `guests` (in our case, the factory is the `list` class).  The
"Inheritance" section of the `dataclasses` documentation explains how the order of
the fields is computed when there are several levels of inheritance.

> **Note**
>
> [Inheritance: For Better or for Worse](inheritance.md) discusses misusing
> inheritance, particularly when the superclasses are not abstract.  Creating a
> hierarchy of data classes is usually a bad idea, but it serves well here to keep
> the example short, focusing on the `handle` field and the `__post_init__()`
> validation.

Here is the implementation:

```python
from dataclasses import dataclass, field

@dataclass
class ClubMember:
    name: str
    guests: list = field(default_factory=list)

@dataclass
class HackerClubMember(ClubMember):
    all_handles = set()
    handle: str = ''

    def __post_init__(self):
        cls = self.__class__
        if self.handle == '':
            self.handle = self.name.split()[0]
        if self.handle in cls.all_handles:
            msg = f'handle {self.handle!r} already exists.'
            raise ValueError(msg)
        cls.all_handles.add(self.handle)

leo = HackerClubMember('Leo Rochael')
leo
# HackerClubMember(name='Leo Rochael', guests=[], handle='Leo')
leo2 = HackerClubMember('Leo DaVinci')
# Traceback (most recent call last):
#   ...
# ValueError: handle 'Leo' already exists.
```

`HackerClubMember` extends `ClubMember`.  `all_handles` is a class attribute.
`handle` is an instance field of type `str` with an empty string as its default
value, which makes it optional.  `__post_init__()` gets the class of the instance;
if `self.handle` is the empty string, sets it to the first part of `name`; if
`self.handle` is in `cls.all_handles`, raises `ValueError`; and otherwise adds the
new handle to `cls.all_handles`.

This works as intended, but it does not satisfy a static type checker.  Next,
we'll see why, and how to fix it.

### Typed Class Attributes

If we type check that code with Mypy, we are reprimanded:

```console
$ mypy hackerclub.py
hackerclub.py:37: error: Need type annotation for "all_handles"
(hint: "all_handles: Set[<type>] = ...")
Found 1 error in 1 file (checked 1 source file)
```

The hint is not helpful in the context of `@dataclass`: if we add a type hint like
`set[...]` to `all_handles`, `@dataclass` will find that annotation and make
`all_handles` an *instance* field, as we saw in the `DemoDataClass` inspection.
The workaround defined in PEP 526 is to use a pseudotype named
[`typing.ClassVar`](https://docs.python.org/3/library/typing.html#typing.ClassVar),
which uses the generics `[]` notation to set the type of the variable and also
declare it a class attribute.  To make the type checker and `@dataclass` happy,
this is how `all_handles` should be declared:

<!-- nocheck -->
```python
all_handles: ClassVar[set[str]] = set()
```

That type hint says: `all_handles` is a class attribute of type set-of-str, with an
empty set as its default value.  To write it, you must import `ClassVar` from the
`typing` module.

The `@dataclass` decorator doesn't care about the types in the annotations, except
in two cases, and this is one of them: if the type is `ClassVar`, an instance field
will not be generated for that attribute.  The other case is when declaring
*init-only variables*.

### Initialization Variables That Are Not Fields

Sometimes you need to pass arguments to `__init__()` that are not instance fields.
The `dataclasses` documentation calls them init-only variables.  To declare an
argument like that, the `dataclasses` module provides the pseudotype `InitVar`,
which uses the same syntax as `typing.ClassVar`.  The example in the documentation
is a data class that has a field initialized from a database, where the database
object must be passed to the constructor:

<!-- nocheck -->
```python
@dataclass
class C:
    i: int
    j: int | None = None
    database: InitVar[DatabaseType | None] = None

    def __post_init__(self, database):
        if self.j is None and database is not None:
            self.j = database.lookup('j')

c = C(10, database=my_database)
```

`InitVar` prevents `@dataclass` from treating `database` as a regular field.  It
will not be set as an instance attribute, and `dataclasses.fields` will not list
it.  However, `database` will be one of the arguments that the generated
`__init__()` accepts, and it will also be passed to `__post_init__()`.  If you write
that method, you must add a corresponding parameter to its signature, as shown
above.

### `@dataclass` Example: Dublin Core Resource Record

Classes built with `@dataclass` often have more fields than the short examples so
far.  The Dublin Core Schema is a small set of vocabulary terms that can be used to
describe digital resources (video, images, web pages, etc.), as well as physical
resources such as books or CDs, and objects like artworks.  The standard defines
15 optional fields; the `Resource` class below uses 8 of them:

```python
from dataclasses import dataclass, field, fields
from enum import Enum, auto
import datetime

class ResourceType(Enum):
    BOOK = auto()
    EBOOK = auto()
    VIDEO = auto()

@dataclass
class Resource:
    """Media resource description."""
    identifier: str
    title: str = '<untitled>'
    creators: list[str] = field(default_factory=list)
    date: datetime.date | None = None
    type: ResourceType = ResourceType.BOOK
    description: str = ''
    language: str = ''
    subjects: list[str] = field(default_factory=list)
```

The [`Enum`](https://docs.python.org/3/library/enum.html) provides type-safe values
for the `Resource.type` field.  `identifier` is the only required field.  `title` is
the first field with a default, which forces all the fields below it to provide
defaults.  The value of `date` can be a `datetime.date` instance, or `None`.  The
`type` field defaults to `ResourceType.BOOK`.

> **Warning**
>
> Note that we annotate the `date` field with `datetime.date`, after
> `import datetime`.  If we had written `from datetime import date` and then
> `date: date | None = None`, the annotation would be resolved in the class
> namespace, where the name `date` is bound to the default value `None`, so it
> would mean `None | None`, which raises `TypeError`.  When a field has the same name as
> a type, refer to the type through its module.

Here is a `Resource` record:

```python
description = 'Improving the design of existing code'
book = Resource('978-0-13-475759-9', 'Refactoring, 2nd Edition',
    ['Martin Fowler', 'Kent Beck'], datetime.date(2018, 11, 19),
    ResourceType.BOOK, description, 'EN',
    ['computer programming', 'OOP'])
book
# Resource(identifier='978-0-13-475759-9', title='Refactoring, 2nd Edition',
# creators=['Martin Fowler', 'Kent Beck'], date=datetime.date(2018, 11, 19),
# type=<ResourceType.BOOK: 1>, description='Improving the design of existing code',
# language='EN', subjects=['computer programming', 'OOP'])
```

The `__repr__()` generated by `@dataclass` is OK, but we can make it more readable,
with one field per line.  This `__repr__()` uses `dataclasses.fields` to get the
names of the data class fields:

```python
def __repr__(self):
    cls = self.__class__
    cls_name = cls.__name__
    indent = ' ' * 4
    res = [f'{cls_name}(']
    for f in fields(cls):
        value = getattr(self, f.name)
        res.append(f'{indent}{f.name} = {value!r},')
    res.append(')')
    return '\n'.join(res)

Resource.__repr__ = __repr__  # normally you'd define it inside the class
print(repr(book))
# Resource(
#     identifier = '978-0-13-475759-9',
#     title = 'Refactoring, 2nd Edition',
#     creators = ['Martin Fowler', 'Kent Beck'],
#     date = datetime.date(2018, 11, 19),
#     type = <ResourceType.BOOK: 1>,
#     description = 'Improving the design of existing code',
#     language = 'EN',
#     subjects = ['computer programming', 'OOP'],
# )
```

It starts the `res` list with the class name and an open parenthesis; for each
field `f` in the class, gets the named attribute from the instance and appends an
indented line with the name of the field and `repr(value)` (that's what `!r` does);
then appends the closing parenthesis and builds a multiline string from `res`.

## Data Class as a Code Smell

Whether you implement a data class by writing all the code yourself or with one of
the class builders described in this chapter, be aware that it may signal a problem
in your design.

In *Refactoring: Improving the Design of Existing Code*, Martin Fowler and Kent
Beck present a catalog of "code smells": patterns in code that may indicate the
need for refactoring.  Their entry titled "Data Class" describes classes that have
fields, getting and setting methods for fields, and nothing else: dumb data
holders, often manipulated in far too much detail by other classes.

A *code smell*, as Fowler explains it, is a surface indication that usually
corresponds to a deeper problem in the system.  Two points are worth noting.
First, a smell is quick to spot: you notice it just by looking at the code.
Second, smells don't always indicate a problem; they are prompts to look deeper.
Data classes are a good example: when you see one, ask yourself what behavior
should live in that class, and then start moving that behavior into it.

The main idea of object-oriented programming is to place behavior and data
together in the same code unit: a class.  If a class is widely used but has no
significant behavior of its own, it's possible that code dealing with its
instances is scattered (and even duplicated) in methods and functions throughout
the system, a recipe for maintenance headaches.  That's why the refactorings for a
data class involve bringing responsibilities back into it.

Taking that into account, there are a couple of common scenarios where it does make
sense to have a data class with little or no behavior.

### Data Class as Scaffolding

In this scenario, the data class is an initial, simplistic implementation of a
class to jump-start a new project or module.  With time, the class should get its
own methods, instead of relying on methods of other classes to operate on its
instances.  Scaffolding is temporary; eventually your custom class may become fully
independent from the builder you used to start it.  (Python is also used for quick
problem solving and experimentation, and then it's OK to leave the scaffolding in
place.)

### Data Class as Intermediate Representation

A data class can be useful to build records about to be exported to JSON or some
other interchange format, or to hold data that was just imported, crossing some
system boundary.  Python's data class builders all provide a method or function to
convert an instance to a plain `dict`, and you can always invoke the constructor with
a `dict` used as keyword arguments expanded with `**`.  Such a `dict` is very close
to a JSON record.

In this scenario, the data class instances should be handled as immutable objects:
even if the fields are mutable, you should not change them while they are in this
intermediate form.  If you do, you're losing the key benefit of having data and
behavior close together.  When importing or exporting requires changing values, you
should implement your own builder methods instead of using the given "as dict"
methods or standard constructors.

## Data Classes and Pattern Matching

Classes built with these three builders automatically get a `__match_args__` class
attribute, which makes them work with *positional* class patterns in `match`
statements:

```python
import typing

class City(typing.NamedTuple):
    continent: str
    name: str
    country: str

City.__match_args__
# ('continent', 'name', 'country')

def describe(city):
    match city:
        case City('Asia', _, country):
            return f'an Asian city in {country}'
        case City(continent='North America', name=name):
            return f'{name}, in North America'
        case _:
            return 'somewhere else'

describe(City('Asia', 'Tokyo', 'JP'))
# 'an Asian city in JP'
describe(City('North America', 'Mexico City', 'MX'))
# 'Mexico City, in North America'
```

Class patterns of all kinds are explained in
[Pattern Matching in Depth](pattern-matching.md#pattern-matching-class-instances).

## Summary

The main topic of this chapter was the data class builders
`collections.namedtuple`, `typing.NamedTuple` and `dataclasses.dataclass`.  Each
generates data classes from descriptions provided as arguments to a factory
function or, in the case of the latter two, from `class` statements with type
hints.  Both named tuple variants produce `tuple` subclasses, adding only the
ability to access fields by name and a `_fields` class attribute listing the field
names as a tuple of strings.

We compared the main features of the three builders side by side, including how to
extract instance data as a `dict`, how to get the names and default values of
fields, and how to make a new instance from an existing one.

That prompted our first look at type hints, particularly those used to annotate
attributes in a `class` statement.  Probably the most surprising aspect of type
hints is that they have no effect at all at runtime: Python remains a dynamic
language, and external tools like Mypy are needed to use typing information to
detect errors via static analysis.  We studied the effect of annotations in a plain
class and in classes built by `typing.NamedTuple` and `@dataclass`.

Next we covered the most commonly used features of `@dataclass` and the
`default_factory` option of `dataclasses.field`, along with the special pseudotype
hints `typing.ClassVar` and `dataclasses.InitVar`.  An example based on the Dublin
Core Schema showed how to use `dataclasses.fields` to iterate over the attributes of
an instance in a custom `__repr__()`.

Then we warned against abuse of data classes defeating a basic principle of
object-oriented programming: data and the functions that touch it should be
together in the same class.  Classes with no logic may be a sign of misplaced logic.

> **See also**
>
> * The documentation of [`dataclasses`](https://docs.python.org/3/library/dataclasses.html)
>   is very good and has quite a few small examples.  [**PEP 557**](https://peps.python.org/pep-0557/)
>   has a few informative sections that were not copied into it, including "Why
>   not just use namedtuple?" and the "Rationale" section, which notes that data
>   classes are not appropriate when API compatibility with tuples or dicts is
>   required, or when type or value validation or conversion is required.
> * For more features, including validation, see the
>   [attrs](https://www.attrs.org/) project, which appeared years before
>   `dataclasses` and influenced it, including the important design decision of
>   using a class decorator instead of a base class or a metaclass.
> * Martin Fowler's *Refactoring*, 2nd ed., is the best source on data class as a
>   code smell.
