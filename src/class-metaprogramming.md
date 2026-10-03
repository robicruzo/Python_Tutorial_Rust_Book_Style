# Class Metaprogramming

> Everyone knows that debugging is twice as hard as writing a program in the first place.
> So if you're as clever as you can be when you write it, how will you ever debug it?
>
> — Brian W. Kernighan and P. J. Plauger, *The Elements of Programming Style*

Class metaprogramming is the art of creating or customizing classes at runtime.  Classes are
first-class objects in Python, so a function can be used to create a new class at any time,
without using the `class` keyword.  Class decorators are also functions, but designed to
inspect, change, and even replace the decorated class with another class.  Finally,
metaclasses are the most advanced tool for class metaprogramming: they let you create whole
new categories of classes with special traits, such as the abstract base classes we've
already seen.

Metaclasses are powerful, but hard to justify and even harder to get right.  Class decorators
solve many of the same problems and are easier to understand.  Furthermore, Python 3.6
implemented [**PEP 487**](https://peps.python.org/pep-0487/) — Simpler customization of class
creation, providing special methods supporting tasks that previously required metaclasses or
class decorators.

This chapter presents the class metaprogramming techniques in ascending order of complexity.

> **Warning**
>
> This is an exciting topic, and it's easy to get carried away.  For the sake of readability
> and maintainability, you should probably avoid the techniques described in this chapter in
> application code.  On the other hand, these are the tools of the trade if you want to write
> the next great Python framework.

We'll get started by reviewing attributes and methods defined in the Python Data Model for all
classes.

## Classes as Objects

Like most program entities in Python, classes are also objects.  Every class has a number of
attributes defined in the Python Data Model, documented in
[Special Attributes](https://docs.python.org/3/reference/datamodel.html#special-attributes).
Three of those attributes appeared several times already: `__class__`, `__name__` and
`__mro__`.  Other class standard attributes are:

`cls.__bases__`
: The tuple of base classes of the class.

`cls.__qualname__`
: The qualified name of a class or function, which is a dotted path from the global scope of
  the module to the class definition.  This is relevant when the class is defined inside
  another class.  For example, in a Django model class such as `Ox`, there is an inner class
  called `Meta`.  The `__qualname__` of `Meta` is `Ox.Meta`, but its `__name__` is just
  `Meta`.  The specification for this attribute is
  [**PEP 3155**](https://peps.python.org/pep-3155/).

`cls.__subclasses__()`
: This method returns a list of the immediate subclasses of the class.  The implementation
  uses weak references to avoid circular references between the superclass and its
  subclasses — which hold a strong reference to the superclasses in their `__bases__`
  attribute.  The method lists subclasses currently in memory.  Subclasses in modules not yet
  imported will not appear in the result.

`cls.mro()`
: The interpreter calls this method when building a class to obtain the tuple of superclasses
  stored in the `__mro__` attribute of the class.  A metaclass can override this method to
  customize the method resolution order of the class under construction.

```python
class Ox:
    class Meta:
        pass

Ox.Meta.__name__, Ox.Meta.__qualname__
# ('Meta', 'Ox.Meta')
class Bovine(Ox): pass
class Bison(Bovine): pass
Ox.__subclasses__()  # only the immediate subclasses
# [<class '__main__.Bovine'>]
Bison.__bases__
# (<class '__main__.Bovine'>,)
Bison.mro()
# [<class '__main__.Bison'>, <class '__main__.Bovine'>, <class '__main__.Ox'>, <class 'object'>]
'__mro__' in dir(Bison)  # none of these attributes are listed by dir()
# False
```

Now, if a class is an object, what is the class of a class?

## `type`: The Built-In Class Factory

We usually think of `type` as a function that returns the class of an object, because that's
what `type(my_object)` does: it returns `my_object.__class__`.  However, `type` is a class that
creates a new class when invoked with three arguments.  Consider this simple class:

<!-- nocheck -->
```python
class MyClass(MySuperClass, MyMixin):
    x = 42

    def x2(self):
        return self.x * 2
```

Using the `type` constructor, you can create `MyClass` at runtime with this code:

<!-- nocheck -->
```python
MyClass = type('MyClass',
               (MySuperClass, MyMixin),
               {'x': 42, 'x2': lambda self: self.x * 2},
          )
```

That `type` call is functionally equivalent to the previous `class MyClass…` block statement.
When Python reads a `class` statement, it calls `type` to build the class object with these
parameters:

`name`
: The identifier that appears after the `class` keyword, e.g., `MyClass`.

`bases`
: The tuple of superclasses given in parentheses after the class identifier, or `(object,)`
  if superclasses are not mentioned in the `class` statement.

`dict`
: A mapping of attribute names to values.  Callables become methods, as we saw in
  [Methods Are Descriptors](descriptors.md#methods-are-descriptors).  Other values become
  class attributes.

```python
MyClass = type('MyClass', (), {'x': 42, 'x2': lambda self: self.x * 2})
MyClass().x2()
# 84
MyClass.__mro__
# (<class '__main__.MyClass'>, <class 'object'>)
```

> **Note**
>
> The `type` constructor accepts optional keyword arguments, which are ignored by `type`
> itself, but are passed untouched into `__init_subclass__`, which must consume them.  We'll
> study that special method — including those keyword arguments — in
> [Introducing `__init_subclass__`](#introducing-__init_subclass__).

The `type` class is a *metaclass*: a class that builds classes.  In other words, instances of
the `type` class are classes.  The standard library provides a few other metaclasses, but
`type` is the default:

```python
type(7)
# <class 'int'>
type(int)
# <class 'type'>
type(OSError)
# <class 'type'>
class Whatever:
    pass

type(Whatever)
# <class 'type'>
```

We'll build custom metaclasses in [Metaclasses 101](#metaclasses-101).  Next, we'll use the
`type` built-in to make a function that builds classes.

## A Class Factory Function

The standard library has a class factory function that appears several times in this book:
`collections.namedtuple`.  In [Data Class Builders](dataclasses.md) we also saw
`typing.NamedTuple` and `@dataclass`.  All of these class builders leverage techniques covered
in this chapter.

We'll start with a super simple factory for classes of mutable objects — the simplest possible
replacement for `@dataclass`.  Suppose we're writing a pet shop application and we want to
store data for dogs as simple records.  But we don't want to write boilerplate like this:

```python
class Dog:
    def __init__(self, name, weight, owner):
        self.name = name
        self.weight = weight
        self.owner = owner
```

Boring… each field name appears three times, and that boilerplate doesn't even buy us a nice
`repr`:

```python
rex = Dog('Rex', 30, 'Bob')
rex
# <__main__.Dog object at 0x...>
```

Taking a hint from `collections.namedtuple`, let's create a `record_factory` that creates
simple classes like `Dog` on the fly.  Here is the code (`record_factory.py`):

```python
from typing import Any
from collections.abc import Iterable, Iterator

type FieldNames = str | Iterable[str]  # names as a single string or an iterable of strings

def record_factory(cls_name: str, field_names: FieldNames) -> type[tuple]:

    slots = parse_identifiers(field_names)  # this will be the __slots__ of the new class

    def __init__(self, *args, **kwargs) -> None:  # will become __init__ in the new class
        attrs = dict(zip(self.__slots__, args))
        attrs.update(kwargs)
        for name, value in attrs.items():
            setattr(self, name, value)

    def __iter__(self) -> Iterator[Any]:  # yield the values in the order of __slots__
        for name in self.__slots__:
            yield getattr(self, name)

    def __repr__(self):  # the nice repr, iterating over __slots__ and self
        values = ', '.join(f'{name}={value!r}'
            for name, value in zip(self.__slots__, self))
        cls_name = self.__class__.__name__
        return f'{cls_name}({values})'

    cls_attrs = dict(  # assemble a dictionary of class attributes
        __slots__=slots,
        __init__=__init__,
        __iter__=__iter__,
        __repr__=__repr__,
    )

    return type(cls_name, (object,), cls_attrs)  # build and return the new class

def parse_identifiers(names: FieldNames) -> tuple[str, ...]:
    if isinstance(names, str):
        names = names.replace(',', ' ').split()  # names separated by spaces or commas
    if not all(s.isidentifier() for s in names):
        raise ValueError('names must all be valid identifiers')
    return tuple(names)
```

And here it is in use:

```python
Dog = record_factory('Dog', 'name weight owner')  # called like namedtuple
rex = Dog('Rex', 30, 'Bob')
rex  # nice repr
# Dog(name='Rex', weight=30, owner='Bob')
name, weight, _ = rex  # instances are iterable, so they can be unpacked...
name, weight
# ('Rex', 30)
"{2}'s dog weighs {1}kg".format(*rex)  # ...or passed to functions like format
# "Bob's dog weighs 30kg"
rex.weight = 32  # a record instance is mutable
rex
# Dog(name='Rex', weight=32, owner='Bob')
Dog.__mro__  # the new class inherits from object: no relationship to the factory
# (<class '__main__.Dog'>, <class 'object'>)
```

This is the first time we've seen `type` in a type hint.  If the annotation was just
`-> type`, that would mean that `record_factory` returns a class — and it would be correct.
But the annotation `-> type[tuple]` is more precise: it says the returned class will be a
subclass of `tuple`.  (Strictly speaking, our records are not tuples, they just behave like
them by being iterable; the hint expresses the intent, and a type checker can't verify a class
built by `type()` anyway.)  The `type FieldNames = ...` line uses the type alias statement of
Python 3.12 ([**PEP 695**](https://peps.python.org/pep-0695/)).

The last line of `record_factory` builds a class named by the value of `cls_name`, with
`object` as its single immediate base class, and with a namespace loaded with `__slots__`,
`__init__`, `__iter__` and `__repr__`, of which the last three are instance methods.

We could have named the `__slots__` class attribute anything else, but then we'd have to
implement `__setattr__` to validate the names of attributes being assigned, because for our
record-like classes we want the set of attributes to be always the same and in the same
order.  However, recall that the main feature of `__slots__` is saving memory when you are
dealing with millions of instances, and using `__slots__` has some drawbacks, discussed in
[Saving Memory with `__slots__`](pythonic-object.md#saving-memory-with-__slots__).

> **Warning**
>
> Instances of classes created by `record_factory` are not serializable — that is, they can't
> be exported with the `dump` function from the `pickle` module, because `pickle` can't find
> the class by its name in a module.  Solving this problem is beyond the scope of this
> example, which aims to show the `type` class in action in a simple use case.  For the full
> solution, study the source code for `collections.namedtuple`; search for the word
> "pickling" (hint: it sets `__module__` on the new class).

Now let's see how to emulate more modern class builders like `typing.NamedTuple`, which takes
a user-defined class written as a `class` statement, and automatically enhances it with more
functionality.

## Introducing `__init_subclass__`

Both `__init_subclass__` and `__set_name__` were proposed in PEP 487.  We saw the
`__set_name__` special method for descriptors for the first time in
[LineItem Take #4](descriptors.md#lineitem-take-4-automatic-naming-of-storage-attributes).
Now let's study `__init_subclass__`.

`__init_subclass__` is called on a class whenever a subclass of it is defined.  The simplest
classic use is a registry of subclasses — handy for plugins.  Note how keyword arguments in
the `class` statement are passed to `__init_subclass__`:

```python
class Plugin:
    registry: dict[str, type] = {}

    def __init_subclass__(cls, /, name=None, **kwargs):
        super().__init_subclass__(**kwargs)  # play nice with cooperative multiple inheritance
        cls.registry[name or cls.__name__.lower()] = cls

class CsvExporter(Plugin, name='csv'):  # keyword argument for __init_subclass__
    pass

class JsonExporter(Plugin):
    pass

Plugin.registry
# {'csv': <class '__main__.CsvExporter'>, 'jsonexporter': <class '__main__.JsonExporter'>}
```

In [Data Class Builders](dataclasses.md), we saw that `typing.NamedTuple` and `@dataclass` let
programmers use the `class` statement to specify attributes for a new class, which is then
enhanced by the class builder with the automatic addition of essential methods like
`__init__`, `__repr__`, `__eq__`, etc.  Both of these class builders read type hints in the
user's `class` statement to enhance the class.  Those type hints also allow static type
checkers to validate code that sets or gets those attributes.  However, `NamedTuple` and
`@dataclass` do not take advantage of the type hints for attribute validation at runtime.  The
`Checked` class in the next example does.

> **Note**
>
> It is not possible to support every conceivable static type hint for runtime type checking,
> which is probably why `typing.NamedTuple` and `@dataclass` don't even try it.  However, some
> types that are also concrete classes can be used with `Checked`.  This includes simple types
> often used for field contents, such as `str`, `int`, `float` and `bool`, as well as lists of
> those types.

Here is how we'll use `Checked` to build a `Movie` class:

<!-- nocheck -->
```python
class Movie(Checked):  # Movie inherits from Checked, defined later
    title: str  # each attribute is annotated with a constructor
    year: int
    box_office: float

movie = Movie(title='The Godfather', year=1972, box_office=137)  # keyword arguments only
movie.title
# 'The Godfather'
movie  # in return, you get a nice __repr__
# Movie(title='The Godfather', year=1972, box_office=137.0)
```

The constructors used as the attribute type hints may be any callable that takes zero or one
argument and returns a value suitable for the intended field type, or rejects the argument by
raising `TypeError` or `ValueError`.  Using built-in types for the annotations means the values
must be acceptable by the constructor of the type.  For `int`, this means any `x` such that
`int(x)` returns an `int`.  For `str`, anything goes at runtime, because `str(x)` works with
any `x` in Python.

When called with no arguments, the constructor should return a default value of its type.
This is standard behavior for Python's built-in constructors:

```python
int(), float(), bool(), str(), list(), dict(), set()
# (0, 0.0, False, '', [], {}, set())
```

In a `Checked` subclass like `Movie`, missing parameters create instances with default values
returned by the field constructors.  The constructors are also used for validation during
instantiation and when an attribute is set directly on an instance.  (This solution avoids
using `None` as a default.  Avoiding null values is a good idea where it's easy: in Go,
variables and struct fields are initialized with a "zero value" of their type, much like
this.)

Now let's look at the implementation of `checkedlib.py`.  The first class is the `Field`
descriptor:

```python
from collections.abc import Callable
from typing import Any, NoReturn, get_type_hints

class Field:
    def __init__(self, name: str, constructor: Callable) -> None:  # minimal Callable hint
        if not callable(constructor) or constructor is type(None):  # runtime check
            raise TypeError(f'{name!r} type hint must be callable')
        self.name = name
        self.constructor = constructor

    def __set__(self, instance: Any, value: Any) -> None:
        if value is ...:  # Checked.__init__ uses ... to mean "no value given"
            value = self.constructor()
        else:
            try:
                value = self.constructor(value)  # call the constructor with the value
            except (TypeError, ValueError) as e:  # rephrase errors helpfully
                type_name = self.constructor.__name__
                msg = f'{value!r} is not compatible with {self.name}:{type_name}'
                raise TypeError(msg) from e
        instance.__dict__[self.name] = value
```

Since Python 3.9, the `Callable` type for annotations is the ABC in `collections.abc`, and not
the deprecated `typing.Callable`.  For runtime checking, we use the `callable` built-in.  The
test against `type(None)` is necessary because Python reads `None` in a type as `NoneType`,
the class of `None` (therefore callable), but a useless constructor that only returns `None`.

If `Checked.__init__` sets the value as `...` (the `Ellipsis` built-in object), we call the
constructor with no arguments.  Otherwise, we call the constructor with the given value.  We
need to catch `TypeError` and `ValueError` because built-in constructors may raise either of
them, depending on the argument.  For example, `float(None)` raises `TypeError`, but
`float('A')` raises `ValueError`.  On the other hand, `float('8')` raises no error and returns
`8.0` — a feature, not a bug, of this toy example.

> **Tip**
>
> We saw the handy `__set_name__` special method for descriptors in the previous chapter.  We
> don't need it in the `Field` class because the descriptors are not instantiated in client
> source code; the user declares types that are constructors.  Instead, the `Field`
> descriptor instances are created at runtime by the `Checked.__init_subclass__` method, which
> passes the name explicitly.  Note that `__set_name__` is called only by `type.__new__`, so
> it is *not* called for descriptors assigned with `setattr` after the class is built.

Now let's focus on the `Checked` class.  Here are its most important methods:

<!-- nocheck -->
```python
class Checked:
    @classmethod
    def _fields(cls) -> dict[str, type]:  # hides the call to typing.get_type_hints
        return get_type_hints(cls)

    def __init_subclass__(subclass) -> None:  # gets the new subclass as first argument
        super().__init_subclass__()  # not strictly necessary, but plays nice
        for name, constructor in subclass._fields().items():  # for each field and constructor...
            setattr(subclass, name, Field(name, constructor))  # ...install a Field descriptor

    def __init__(self, **kwargs: Any) -> None:
        for name in self._fields():  # for each name in the class fields...
            value = kwargs.pop(name, ...)  # ...get the value or ... (the Ellipsis sentinel)
            setattr(self, name, value)  # this triggers Checked.__setattr__
        if kwargs:  # remaining items don't match any declared field
            self.__flag_unknown_attrs(*kwargs)
```

`_fields` hides the call to
[`typing.get_type_hints`](https://docs.python.org/3/library/typing.html#typing.get_type_hints)
from the rest of the class; review [Reading Type Hints at Runtime](type-hints-more.md) for the
subtleties of reading annotations, including the lazy annotations of Python 3.14.  Using
`...` as the default of `kwargs.pop` allows us to distinguish between arguments given the value
`None` from arguments that were not given.  The `*kwargs` with a single asterisk passes the
keys of `kwargs` as a sequence of arguments.

#### `__init_subclass__` is not a typical class method

The `@classmethod` decorator is never used with `__init_subclass__`, but that doesn't mean
much, because the `__new__` special method behaves as a class method even without
`@classmethod`.  The first argument that Python passes to `__init_subclass__` is a class.
However, it is never the class where `__init_subclass__` is implemented: it is a newly defined
subclass of that class.  That's unlike `__new__` and every other class method.  Therefore,
`__init_subclass__` is not a class method in the usual sense, and it can be misleading to name
the first argument `cls` — that's why it's named `subclass` above.  The documentation names
the argument `cls` but explains: "…called whenever the containing class is subclassed.  `cls`
is then the new subclass."

Now let's see the remaining methods of the `Checked` class.  Note that `_fields` and `_asdict`
are prefixed with `_` for the same reason the `collections.namedtuple` API does: to reduce the
chance of name clashes with user-defined field names.  Here is the complete class:

```python
class Checked:
    @classmethod
    def _fields(cls) -> dict[str, type]:
        return get_type_hints(cls)

    def __init_subclass__(subclass) -> None:
        super().__init_subclass__()
        for name, constructor in subclass._fields().items():
            setattr(subclass, name, Field(name, constructor))

    def __init__(self, **kwargs: Any) -> None:
        for name in self._fields():
            value = kwargs.pop(name, ...)
            setattr(self, name, value)
        if kwargs:
            self.__flag_unknown_attrs(*kwargs)

    def __setattr__(self, name: str, value: Any) -> None:  # intercept all attribute setting
        if name in self._fields():  # known name: fetch the descriptor...
            cls = self.__class__
            descriptor = getattr(cls, name)
            descriptor.__set__(self, value)  # ...and call its __set__ explicitly
        else:  # unknown name: raise
            self.__flag_unknown_attrs(name)

    def __flag_unknown_attrs(self, *names: str) -> NoReturn:  # a rare use of NoReturn
        plural = 's' if len(names) > 1 else ''
        extra = ', '.join(f'{name!r}' for name in names)
        cls_name = repr(self.__class__.__name__)
        raise AttributeError(f'{cls_name} object has no attribute{plural} {extra}')

    def _asdict(self) -> dict[str, Any]:  # follows the namedtuple._asdict convention
        return {
            name: getattr(self, name)
            for name, attr in self.__class__.__dict__.items()
            if isinstance(attr, Field)
        }

    def __repr__(self) -> str:  # the main reason for having _asdict
        kwargs = ', '.join(
            f'{key}={value!r}' for key, value in self._asdict().items()
        )
        return f'{self.__class__.__name__}({kwargs})'
```

Usually we don't need to call the descriptor `__set__` explicitly.  It was necessary in this
case because `__setattr__` intercepts all attempts to set an attribute on the instance,
including in the presence of an overriding descriptor such as `Field`.  Let's try it:

```python
class Movie(Checked):
    title: str
    year: int
    box_office: float

movie = Movie(title='The Godfather', year=1972, box_office=137)
movie.title
# 'The Godfather'
movie
# Movie(title='The Godfather', year=1972, box_office=137.0)
Movie(title='Life of Brian')  # missing fields get default values from the constructors
# Movie(title='Life of Brian', year=0, box_office=0.0)
blockbuster = Movie(title='Avatar', year=2009, box_office='billions')
# Traceback (most recent call last):
#   ...
# TypeError: 'billions' is not compatible with box_office:float
movie.year = 'MCMLXXII'
# Traceback (most recent call last):
#   ...
# TypeError: 'MCMLXXII' is not compatible with year:int
movie.director = 'Francis Ford Coppola'
# Traceback (most recent call last):
#   ...
# AttributeError: 'Movie' object has no attribute 'director'
movie._asdict()
# {'title': 'The Godfather', 'year': 1972, 'box_office': 137.0}
```

> **Note**
>
> **`Checked` subclasses and static type checking.**  In a *.py* source file with a `movie`
> instance of `Movie`, a type checker flags `movie.year = 'MCMLXXII'` as a type error.
> However, it can't detect type errors in a constructor call like
> `Movie(title='Avatar', year='MMIX')`, because `Movie` inherits `Checked.__init__`, and the
> signature of that method must accept any keyword arguments to support arbitrary
> user-defined classes.  The fix is
> [`typing.dataclass_transform`](https://docs.python.org/3/library/typing.html#typing.dataclass_transform)
> ([**PEP 681**](https://peps.python.org/pep-0681/), Python 3.11): decorating `Checked` with
> `@dataclass_transform(kw_only_default=True)` tells type checkers that subclasses get a
> synthesized, dataclass-like `__init__` based on their annotations.  The same decorator works
> on class decorators and metaclasses.  On the other hand, if you declare a `Checked` subclass
> field with the type hint `list[float]`, a type checker can flag assignments of lists with
> incompatible contents, but `Checked` will ignore the type parameter and treat that the same
> as `list`.

The `Checked` example illustrates how to handle overriding descriptors when implementing
`__setattr__` to block arbitrary attribute setting after instantiation.  It is debatable
whether implementing `__setattr__` is worthwhile in this example.  Without it, setting
`movie.director = 'Greta Gerwig'` would succeed, but the `director` attribute would not be
checked in any way, and would not appear in the `__repr__` nor would it be included in the
`dict` returned by `_asdict`.

In `record_factory.py` we solved this issue using the `__slots__` class attribute.  However,
this simpler solution is not viable in this case, as explained next.

### Why `__init_subclass__` Cannot Configure `__slots__`

The `__slots__` attribute is only effective if it is one of the entries in the class namespace
passed to `type.__new__`.  Adding `__slots__` to an existing class has no effect.  Python
invokes `__init_subclass__` only after the class is built — by then it's too late to configure
`__slots__`.  A class decorator can't configure `__slots__` either, because it is applied even
later than `__init_subclass__`.  We'll explore these timing issues in
[What Happens When: Import Time Versus Runtime](#what-happens-when-import-time-versus-runtime).

```python
class Late:
    pass

Late.__slots__ = ('x',)  # too late: the class already has instance dicts
obj = Late()
obj.anything = 1  # no error: __slots__ was ignored
vars(obj)
# {'anything': 1}
```

To configure `__slots__` at runtime, your own code must build the class namespace passed as
the last argument of `type.__new__`.  To do that, you can write a class factory function, like
`record_factory.py`, or you can take the nuclear option and implement a metaclass.  We will see
how to dynamically configure `__slots__` in [Metaclasses 101](#metaclasses-101).  (The
`@dataclass(slots=True)` option of Python 3.10 works around the limitation in a third way: the
decorator builds and returns a *new* class with `__slots__`, instead of the decorated one.)

Before PEP 487 simplified the customization of class creation with `__init_subclass__` in
Python 3.6, similar functionality had to be implemented using a class decorator.  That's the
focus of the next section.

## Enhancing Classes with a Class Decorator

A class decorator is a callable that behaves similarly to a function decorator: it gets the
decorated class as an argument, and should return a class to replace the decorated class.
Class decorators often return the decorated class itself, after injecting more methods in it
via attribute assignment.

Probably the most common reason to choose a class decorator over the simpler
`__init_subclass__` is to avoid interfering with other class features, such as inheritance and
metaclasses.  (This rationale appears in the abstract of
[**PEP 557**](https://peps.python.org/pep-0557/) — Data Classes, to explain why it was
implemented as a class decorator.)

In this section, we'll study `checkeddeco.py`, which provides the same service as
`checkedlib.py`, but using a class decorator.  The only difference in usage is the way the
`Movie` class is declared: it is decorated with `@checked` instead of subclassing `Checked`.
Otherwise, the external behavior is the same, including the type validation and default value
assignments.

The imports and `Field` class are the same as in `checkedlib.py`.  There is no other class,
only functions in `checkeddeco.py`.  The logic previously implemented in `__init_subclass__`
is now part of the `checked` function — the class decorator:

```python
def checked(cls: type) -> type:  # takes a class and returns a class
    for name, constructor in _fields(cls).items():  # _fields is defined below
        setattr(cls, name, Field(name, constructor))  # what __init_subclass__ did

    cls._fields = classmethod(_fields)  # type: ignore

    instance_methods = (  # module-level functions that will become instance methods
        __init__,
        __repr__,
        __setattr__,
        _asdict,
        __flag_unknown_attrs,
    )
    for method in instance_methods:  # add each of them to cls
        setattr(cls, method.__name__, method)

    return cls  # fulfill the essential contract of a class decorator
```

The `# type: ignore` comment is needed because type checkers complain that `type` has no
`_fields` attribute.  Every top-level function in `checkeddeco.py` is prefixed with an
underscore, except the `checked` decorator.  This naming convention makes sense for a couple of
reasons:

* `checked` is part of the public interface of the `checkeddeco.py` module, but the other
  functions are not.
* The functions will be injected in the decorated class, and the leading `_` reduces the
  chance of naming conflicts with user-defined attributes and methods of the decorated class.

The rest of `checkeddeco.py` follows.  Those module-level functions have the same code as the
corresponding methods of the `Checked` class.  Note that the `_fields` function does double
duty: it is used as a regular function in the first line of the `checked` decorator, and it
will also be injected as a class method of the decorated class.

```python
def _fields(cls: type) -> dict[str, type]:
    return get_type_hints(cls)

def __init__(self: Any, **kwargs: Any) -> None:
    for name in self._fields():
        value = kwargs.pop(name, ...)
        setattr(self, name, value)
    if kwargs:
        self.__flag_unknown_attrs(*kwargs)

def __setattr__(self: Any, name: str, value: Any) -> None:
    if name in self._fields():
        cls = self.__class__
        descriptor = getattr(cls, name)
        descriptor.__set__(self, value)
    else:
        self.__flag_unknown_attrs(name)

def __flag_unknown_attrs(self: Any, *names: str) -> NoReturn:
    plural = 's' if len(names) > 1 else ''
    extra = ', '.join(f'{name!r}' for name in names)
    cls_name = repr(self.__class__.__name__)
    raise AttributeError(f'{cls_name} has no attribute{plural} {extra}')

def _asdict(self: Any) -> dict[str, Any]:
    return {
        name: getattr(self, name)
        for name, attr in self.__class__.__dict__.items()
        if isinstance(attr, Field)
    }

def __repr__(self: Any) -> str:
    kwargs = ', '.join(
        f'{key}={value!r}' for key, value in self._asdict().items()
    )
    return f'{self.__class__.__name__}({kwargs})'
```

> **Warning**
>
> There is a subtle trap in that listing.  Inside a class body, `self.__flag_unknown_attrs`
> would be mangled to `self._Checked__flag_unknown_attrs`.  At module level there is no class,
> so no mangling happens, and the function is installed under its plain name
> `__flag_unknown_attrs` — which is exactly the name the module-level functions look up.  It
> works, but only because *all* the code involved lives outside any class body.

Now the decorator in action:

```python
@checked
class Movie:
    title: str
    year: int
    box_office: float

movie = Movie(title='The Godfather', year=1972, box_office=137)
movie
# Movie(title='The Godfather', year=1972, box_office=137.0)
Movie(title='Life of Brian')
# Movie(title='Life of Brian', year=0, box_office=0.0)
Movie.__mro__  # no special base class
# (<class '__main__.Movie'>, <class 'object'>)
```

The `checkeddeco.py` module implements a simple but usable class decorator.  Python's
`@dataclass` does a lot more.  It supports many configuration options, adds more methods to the
decorated class, handles or warns about conflicts with user-defined methods in the decorated
class, and even traverses the `__mro__` to collect user-defined attributes declared in the
superclasses of the decorated class.  The source code of the `dataclasses` module is more than
1,500 lines long.  Another — much simpler — example of a class decorator in the standard
library is `functools.total_ordering`, which generates special methods for object comparison
(see [Operator Overloading](operator-overloading.md)).

For metaprogramming classes, we must be aware of when the Python interpreter evaluates each
block of code during the construction of a class.  This is covered next.

## What Happens When: Import Time Versus Runtime

Python programmers talk about "import time" versus "runtime", but the terms are not strictly
defined and there is a gray area between them.  At import time, the interpreter:

1. Parses the source code of a *.py* module in one pass from top to bottom.  This is when a
   `SyntaxError` may occur.
2. Compiles the bytecode to be executed.
3. Executes the top-level code of the compiled module.

If there is an up-to-date *.pyc* file available in the local `__pycache__`, parsing and
compiling are skipped because the bytecode is ready to run (see
[“Compiled” Python files](modules.md)).

Although parsing and compiling are definitely "import time" activities, other things may happen
at that time, because almost every statement in Python is executable in the sense that they can
potentially run user code and may change the state of the user program.  In particular, the
`import` statement is not merely a declaration — unlike in Java — but it actually runs all the
top-level code of a module when it is imported for the first time in the process.  Further
imports of the same module will use a cache, and then the only effect will be binding the
imported objects to names in the client module.  That top-level code may do anything,
including actions typical of "runtime", such as writing to a log or connecting to a database.
That's why the border between "import time" and "runtime" is fuzzy: the `import` statement
can trigger all sorts of "runtime" behavior.  Conversely, "import time" can also happen deep
inside runtime, because the `import` statement and the `__import__()` built-in can be used
inside any regular function.

This is all rather abstract and subtle, so let's do some experiments to see what happens when.

### Evaluation Time Experiments

Consider an *evaldemo.py* script that uses a class decorator, a descriptor, and a class builder
based on `__init_subclass__`, all defined in a *builderlib.py* module.  The modules have several
`print` calls to show what happens under the covers.  Otherwise, they don't perform anything
useful.  The goal of these experiments is to observe the order in which these `print` calls
happen.

> **Warning**
>
> Applying a class decorator and a class builder with `__init_subclass__` together in a single
> class is likely a sign of overengineering or desperation.  This unusual combination is useful
> in these experiments to show the timing of the changes that a class decorator and
> `__init_subclass__` can apply to a class.

Here is *builderlib.py*.  Lines printed by it are prefixed with `@`:

<!-- nocheck -->
```python
print('@ builderlib module start')

class Builder:  # a class builder to implement...
    print('@ Builder body')

    def __init_subclass__(cls):  # ...an __init_subclass__ method
        print(f'@ Builder.__init_subclass__({cls!r})')

        def inner_0(self):  # a function to be added to the subclass below
            print(f'@ SuperA.__init_subclass__:inner_0({self!r})')

        cls.method_a = inner_0

    def __init__(self):
        super().__init__()
        print(f'@ Builder.__init__({self!r})')


def deco(cls):  # a class decorator
    print(f'@ deco({cls!r})')

    def inner_1(self):  # function to be added to the decorated class
        print(f'@ deco:inner_1({self!r})')

    cls.method_b = inner_1
    return cls  # return the class received as an argument

class Descriptor:  # a descriptor class to demonstrate when...
    print('@ Descriptor body')

    def __init__(self):  # ...a descriptor instance is created, and when...
        print(f'@ Descriptor.__init__({self!r})')

    def __set_name__(self, owner, name):  # ...__set_name__ is invoked
        args = (self, owner, name)
        print(f'@ Descriptor.__set_name__{args!r}')

    def __set__(self, instance, value):  # only displays its arguments
        args = (self, instance, value)
        print(f'@ Descriptor.__set__{args!r}')

    def __repr__(self):
        return '<Descriptor instance>'

print('@ builderlib module end')
```

If you import *builderlib.py* in the Python console, this is what you get:

```pycon
>>> import builderlib
@ builderlib module start
@ Builder body
@ Descriptor body
@ builderlib module end
```

Now let's turn to *evaldemo.py*, which will trigger special methods in *builderlib.py*.  Its
own lines are prefixed with `#`:

<!-- nocheck -->
```python
#!/usr/bin/env python3

from builderlib import Builder, deco, Descriptor

print('# evaldemo module start')

@deco  # apply a decorator
class Klass(Builder):  # subclass Builder to trigger its __init_subclass__
    print('# Klass body')

    attr = Descriptor()  # instantiate the descriptor

    def __init__(self):
        super().__init__()
        print(f'# Klass.__init__({self!r})')

    def __repr__(self):
        return '<Klass instance>'


def main():  # only called if the module is run as the main program
    obj = Klass()
    obj.method_a()
    obj.method_b()
    obj.attr = 999

if __name__ == '__main__':
    main()

print('# evaldemo module end')
```

If you open a fresh console and import *evaldemo.py*, this is the output:

```pycon
>>> import evaldemo
@ builderlib module start
@ Builder body
@ Descriptor body
@ builderlib module end
# evaldemo module start
# Klass body
@ Descriptor.__init__(<Descriptor instance>)
@ Descriptor.__set_name__(<Descriptor instance>, <class 'evaldemo.Klass'>, 'attr')
@ Builder.__init_subclass__(<class 'evaldemo.Klass'>)
@ deco(<class 'evaldemo.Klass'>)
# evaldemo module end
```

1. The top four lines are the result of `from builderlib import…`.  They will not appear if
   *builderlib.py* was already loaded in the same session.
2. `# Klass body` signals that Python started reading the body of `Klass`.  At this point, the
   class object does not exist yet.
3. The descriptor instance is created and bound to `attr` in the namespace that Python will
   pass to the default class object constructor: `type.__new__`.
4. At this point, Python's built-in `type.__new__` has created the `Klass` object and calls
   `__set_name__` on each descriptor instance of descriptor classes that provide that method,
   passing `Klass` as the `owner` argument.
5. `type.__new__` then calls `__init_subclass__` on the superclass of `Klass`, passing `Klass`
   as the single argument.
6. When `type.__new__` returns the class object, Python applies the decorator.  In this
   example, the class returned by `deco` is bound to `Klass` in the module namespace.

The implementation of `type.__new__` is written in C.  The behavior just described is
documented in the
[Creating the class object](https://docs.python.org/3/reference/datamodel.html#creating-the-class-object)
section of the Data Model reference.

Note that the `main()` function of *evaldemo.py* was not executed in the console session,
therefore no instance of `Klass` was created.  All the action we saw was triggered by "import
time" operations: importing `builderlib` and defining `Klass`.  If you run *evaldemo.py* as a
script, you will see the same output with extra lines right before the end.  The extra lines
are the result of running `main()`:

```console
$ ./evaldemo.py
[... 9 lines omitted ...]
@ deco(<class '__main__.Klass'>)
@ Builder.__init__(<Klass instance>)
# Klass.__init__(<Klass instance>)
@ SuperA.__init_subclass__:inner_0(<Klass instance>)
@ deco:inner_1(<Klass instance>)
@ Descriptor.__set__(<Descriptor instance>, <Klass instance>, 999)
# evaldemo module end
```

`@ Builder.__init__` is triggered by `super().__init__()` in `Klass.__init__`; the next two
lines by `obj.method_a()` and `obj.method_b()` in `main` — `method_a` was injected by
`Builder.__init_subclass__`, `method_b` by `deco`; and the `Descriptor.__set__` line by
`obj.attr = 999`.

A base class with `__init_subclass__` and a class decorator are powerful tools, but they are
limited to working with a class already built by `type.__new__` under the covers.  In the rare
occasions when you need to adjust the arguments passed to `type.__new__`, you need a metaclass.
That's the final destination of this chapter.

## Metaclasses 101

> [Metaclasses] are deeper magic than 99% of users should ever worry about.  If you wonder
> whether you need them, you don't (the people who actually need them know with certainty that
> they need them, and don't need an explanation about why).
>
> — Tim Peters, inventor of the Timsort algorithm and prolific Python contributor

A metaclass is a class factory.  In contrast with `record_factory`, a metaclass is written as a
class.  In other words, a metaclass is a class whose instances are classes — a mill producing
other mills.

Consider the Python object model: classes are objects, therefore each class must be an instance
of some other class.  By default, Python classes are instances of `type`.  In other words,
`type` is the metaclass for most built-in and user-defined classes:

```python
str.__class__
# <class 'type'>
Movie.__class__
# <class 'type'>
type.__class__  # to avoid infinite regress, the class of type is type
# <class 'type'>
```

Note that we are not saying that `str` or `Movie` are subclasses of `type`.  What we are saying
is that `str` and `Movie` are instances of `type`.  They all are subclasses of `object`:

```text
   subclass-of view (__mro__)            instance-of view (__class__)

          object                                  type
         /  |   \                               /  |  \  \
      str  type  Movie                     str object type Movie
```

> **Note**
>
> The classes `object` and `type` have a unique relationship: `object` is an instance of
> `type`, and `type` is a subclass of `object`.  This relationship is "magic": it cannot be
> expressed in Python because either class would have to exist before the other could be
> defined.  The fact that `type` is an instance of itself is also magical.

The next snippet shows that the class of `collections.abc.Iterable` is `abc.ABCMeta`.  Note
that `Iterable` is an abstract class, but `ABCMeta` is a concrete class — after all, `Iterable`
is an instance of `ABCMeta`:

```python
from collections.abc import Iterable
Iterable.__class__
# <class 'abc.ABCMeta'>
import abc
from abc import ABCMeta
ABCMeta.__class__
# <class 'type'>
ABCMeta.__mro__  # a metaclass is a subclass of type
# (<class 'abc.ABCMeta'>, <class 'type'>, <class 'object'>)
```

Ultimately, the class of `ABCMeta` is also `type`.  Every class is an instance of `type`,
directly or indirectly, but only metaclasses are also subclasses of `type`.  That's the most
important relationship to understand metaclasses: a metaclass, such as `ABCMeta`, inherits from
`type` the power to construct classes.  A metaclass can customize its instances by implementing
special methods, as the next sections demonstrate.

### How a Metaclass Customizes a Class

To use a metaclass, it's critical to understand how `__new__` works on any class.  This was
discussed in
[Flexible Object Creation with `__new__`](dynamic-attributes.md#flexible-object-creation-with-__new__).
The same mechanics happen at a "meta" level when a metaclass is about to create a new instance,
which is a class.  Consider this declaration:

<!-- nocheck -->
```python
class Klass(SuperKlass, metaclass=MetaKlass):
    x = 42
    def __init__(self, y):
        self.y = y
```

To process that `class` statement, Python calls `MetaKlass.__new__` with these arguments:

`meta_cls`
: The metaclass itself (`MetaKlass`), because `__new__` works as class method.

`cls_name`
: The string `Klass`.

`bases`
: The single-element tuple `(SuperKlass,)`, with more elements in the case of multiple
  inheritance.

`cls_dict`
: A mapping like `{'x': 42, '__init__': <function __init__ at 0x...>}`.

When you implement `MetaKlass.__new__`, you can inspect and change those arguments before
passing them to `super().__new__`, which will eventually call `type.__new__` to create the new
class object.

After `super().__new__` returns, you can also apply further processing to the newly created
class before returning it to Python.  Python then calls `SuperKlass.__init_subclass__`, passing
the class you created, and then applies a class decorator to it, if one is present.  Finally,
Python binds the class object to its name in the surrounding namespace — usually the global
namespace of a module, if the `class` statement was a top-level statement.

The most common processing made in a metaclass `__new__` is to add or replace items in the
`cls_dict` — the mapping that represents the namespace of the class under construction.  For
instance, before calling `super().__new__`, you can inject methods in the class under
construction by adding functions to `cls_dict`.  However, note that adding methods can also be
done after the class is built, which is why we were able to do it using `__init_subclass__` or
a class decorator.

One attribute that you must add to the `cls_dict` before `type.__new__` runs is `__slots__`, as
discussed in [Why `__init_subclass__` Cannot Configure `__slots__`](#why-__init_subclass__-cannot-configure-__slots__).
The `__new__` method of a metaclass is the ideal place to configure `__slots__`.  The next
section shows how to do that.

### A Nice Metaclass Example

The `MetaBunch` metaclass presented here is a variation of the last example in Chapter 4 of
*Python in a Nutshell*, 3rd ed., by Alex Martelli, Anna Ravenscroft and Steve Holden.  It
first appeared in a message posted by Martelli to comp.lang.python on July 7, 2002, with the
subject line "a nice metaclass example", and his code for Python 2.2 still runs after a single
change: in Python 3, the metaclass is given with the `metaclass` keyword argument in the class
declaration, instead of a `__metaclass__` class attribute.

```python
class MetaBunch(type):  # to create a new metaclass, inherit from type
    def __new__(meta_cls, cls_name, bases, cls_dict):  # meta_cls: the class is a metaclass

        defaults = {}  # attribute names and their default values

        def __init__(self, **kwargs):  # this will be injected into the new class
            for name, default in defaults.items():  # set each attribute from kwargs or default
                setattr(self, name, kwargs.pop(name, default))
            if kwargs:  # leftovers: no slots left to place them; fail fast
                extra = ', '.join(kwargs)
                raise AttributeError(f'No slots left for: {extra!r}')

        def __repr__(self):  # looks like a constructor call, omitting default values
            rep = ', '.join(f'{name}={value!r}'
                            for name, default in defaults.items()
                            if (value := getattr(self, name)) != default)
            return f'{cls_name}({rep})'

        new_dict = dict(__slots__=[], __init__=__init__, __repr__=__repr__)  # new namespace

        for name, value in cls_dict.items():  # iterate over the user's class namespace
            if name.startswith('__') and name.endswith('__'):  # dunder: copy it, unless...
                if name in new_dict:  # ...it would overwrite __init__ or __repr__
                    raise AttributeError(f"Can't set {name!r} in {cls_name!r}")
                new_dict[name] = value
            else:  # not a dunder: append to __slots__ and save the default
                new_dict['__slots__'].append(name)
                defaults[name] = value
        return super().__new__(meta_cls, cls_name, bases, new_dict)  # build the new class

class Bunch(metaclass=MetaBunch):  # a base class, so users don't need to see MetaBunch
    pass
```

`__new__` works as a class method, but the class is a metaclass, so we name the first argument
`meta_cls` (`mcs` is a common alternative).  The remaining three arguments are the same as the
three-argument signature for calling `type()` directly to create a class.  The check for dunder
names prevents users from overwriting `__init__`, `__repr__`, while still copying other
attributes set by Python, such as `__qualname__` and `__module__`.

Here is what the `Bunch` base class provides:

```python
class Point(Bunch):
    x = 0.0
    y = 0.0
    color = 'gray'

Point(x=1.2, y=3, color='green')
# Point(x=1.2, y=3, color='green')
p = Point()
p.x, p.y, p.color
# (0.0, 0.0, 'gray')
p
# Point()
```

Remember that `Checked` assigns names to the `Field` descriptors in subclasses based on class
variable type hints, which do not actually become attributes on the class since they don't have
values.  `Bunch` subclasses, on the other hand, use actual class attributes with values, which
then become the default values of the instance attributes.  The generated `__repr__` omits the
arguments for attributes that are equal to the defaults.

`MetaBunch` — the metaclass of `Bunch` — generates `__slots__` for the new class from the class
attributes declared in the user's class.  This blocks the instantiation and later assignment of
undeclared attributes:

```python
Point(x=1, y=2, z=3)
# Traceback (most recent call last):
#   ...
# AttributeError: No slots left for: 'z'
p = Point(x=21)
p.y = 42
p
# Point(x=21, y=42)
p.flavor = 'banana'
# Traceback (most recent call last):
#   ...
# AttributeError: 'Point' object has no attribute 'flavor' and no __dict__ for setting new attributes
```

(That last error message comes from Python 3.13; older versions stop after `'flavor'`.)
`MetaBunch` works because it is able to configure `__slots__` before calling `super().__new__`
to build the final class.  As usual when metaprogramming, understanding the sequence of actions
is key.  Let's do another evaluation time experiment, now with a metaclass.

### Metaclass Evaluation Time Experiment

This is a variation of the previous experiment, adding a metaclass to the mix.  The
*builderlib.py* module is the same as before, but the main script is now *evaldemo_meta.py*,
which is *evaldemo.py* with three changes: it imports `MetaKlass` from *metalib.py*, declares
the class as `class Klass(Builder, metaclass=MetaKlass):`, and `main()` also calls
`obj.method_c()`, a method injected by `MetaKlass.__new__`.

> **Warning**
>
> In the interest of science, *evaldemo_meta.py* defies all reason and applies three different
> metaprogramming techniques together on `Klass`: a decorator, a base class using
> `__init_subclass__`, and a custom metaclass.  If you do this in production code, please
> don't.  Again, the goal is to observe the order in which the three techniques interfere in
> the class construction process.

Here is *metalib.py*.  Its lines are prefixed with `%`:

```python
print('% metalib module start')

import collections

class NosyDict(collections.UserDict):  # displays each key and value as they are set
    def __setitem__(self, key, value):
        args = (self, key, value)
        print(f'% NosyDict.__setitem__{args!r}')
        super().__setitem__(key, value)

    def __repr__(self):
        return '<NosyDict instance>'

class MetaKlass(type):
    print('% MetaKlass body')

    @classmethod  # the class under construction does not exist yet
    def __prepare__(meta_cls, cls_name, bases):  # get a mapping for the class namespace
        args = (meta_cls, cls_name, bases)
        print(f'% MetaKlass.__prepare__{args!r}')
        return NosyDict()  # use a NosyDict as the namespace

    def __new__(meta_cls, cls_name, bases, cls_dict):  # cls_dict: the NosyDict
        args = (meta_cls, cls_name, bases, cls_dict)
        print(f'% MetaKlass.__new__{args!r}')
        def inner_2(self):
            print(f'% MetaKlass.__new__:inner_2({self!r})')

        cls = super().__new__(meta_cls, cls_name, bases, cls_dict.data)  # needs a real dict

        cls.method_c = inner_2  # inject a method in the newly created class

        return cls  # __new__ must return the new class

    def __repr__(cls):  # customizes the repr() of class objects
        cls_name = cls.__name__
        return f"<class {cls_name!r} built by MetaKlass>"

print('% metalib module end')
```

Importing *metalib.py* in the Python console is not very exciting:

```pycon
>>> import metalib
% metalib module start
% MetaKlass body
% metalib module end
```

The main attraction of *metalib.py* is the metaclass.  It implements the `__prepare__` special
method, a class method that Python only invokes on metaclasses.  The `__prepare__` method
provides the earliest opportunity to influence the process of creating a new class: Python
calls it to obtain a mapping to hold the namespace of the class under construction.
`type.__new__` requires a real `dict` as the last argument, so we give it the `data` attribute
of `NosyDict`, inherited from `UserDict`.

> **Tip**
>
> When coding a metaclass, it's useful to adopt this naming convention for special method
> arguments: use `cls` instead of `self` for instance methods, because the instance is a
> class; and use `meta_cls` instead of `cls` for class methods, because the class is a
> metaclass.  Recall that `__new__` behaves as a class method even without the `@classmethod`
> decorator.

The main use case for `__prepare__` before Python 3.6 was to provide an `OrderedDict` to hold
the attributes of the class under construction, so that the metaclass `__new__` could process
those attributes in the order in which they appear in the source code of the user's class
definition.  Now that `dict` preserves the insertion order, `__prepare__` is rarely needed.
You will see a creative use for it in
[A Metaclass Hack with `__prepare__`](#a-metaclass-hack-with-__prepare__).

Lots of things happen if you import *evaldemo_meta.py* (output from Python 3.13, with
addresses elided and long lines wrapped):

```pycon
>>> import evaldemo_meta
@ builderlib module start
@ Builder body
@ Descriptor body
@ builderlib module end
% metalib module start
% MetaKlass body
% metalib module end
# evaldemo_meta module start
% MetaKlass.__prepare__(<class 'metalib.MetaKlass'>, 'Klass',
                        (<class 'builderlib.Builder'>,))
% NosyDict.__setitem__(<NosyDict instance>, '__module__', 'evaldemo_meta')
% NosyDict.__setitem__(<NosyDict instance>, '__qualname__', 'Klass')
% NosyDict.__setitem__(<NosyDict instance>, '__firstlineno__', 8)
# Klass body
@ Descriptor.__init__(<Descriptor instance>)
% NosyDict.__setitem__(<NosyDict instance>, 'attr', <Descriptor instance>)
% NosyDict.__setitem__(<NosyDict instance>, '__init__',
                       <function Klass.__init__ at …>)
% NosyDict.__setitem__(<NosyDict instance>, '__repr__',
                       <function Klass.__repr__ at …>)
% NosyDict.__setitem__(<NosyDict instance>, '__static_attributes__', ())
% NosyDict.__setitem__(<NosyDict instance>, '__classcell__', <cell at …: empty>)
% MetaKlass.__new__(<class 'metalib.MetaKlass'>, 'Klass',
                    (<class 'builderlib.Builder'>,), <NosyDict instance>)
@ Descriptor.__set_name__(<Descriptor instance>,
                          <class 'Klass' built by MetaKlass>, 'attr')
@ Builder.__init_subclass__(<class 'Klass' built by MetaKlass>)
@ deco(<class 'Klass' built by MetaKlass>)
# evaldemo_meta module end
```

1. Python invokes `__prepare__` to start processing a `class` statement.
2. Before running the class body, Python adds the `__module__` and `__qualname__` entries to the
   namespace of the class under construction — and, since Python 3.13, `__firstlineno__`.
3. The descriptor instance is created and bound to `attr` in the class namespace, then
   `__init__` and `__repr__` methods are defined and added.  At the end of the body, Python 3.13
   also stores `__static_attributes__`: a tuple of the names assigned as `self.<name>` in the
   methods — empty here, because `Klass` assigns no instance attributes.  `__classcell__` is an
   implementation detail that makes `super()` with no arguments work.
4. Once Python finishes processing the class body, it calls `MetaKlass.__new__`.
5. `__set_name__`, `__init_subclass__` and the decorator are invoked in this order, after the
   `__new__` method of the metaclass returns the newly constructed class.

If you run *evaldemo_meta.py* as a script, `main()` is called, and a few more things happen:

```console
$ ./evaldemo_meta.py
[... 23 lines omitted ...]
@ deco(<class 'Klass' built by MetaKlass>)
@ Builder.__init__(<Klass instance>)
# Klass.__init__(<Klass instance>)
@ SuperA.__init_subclass__:inner_0(<Klass instance>)
@ deco:inner_1(<Klass instance>)
% MetaKlass.__new__:inner_2(<Klass instance>)
@ Descriptor.__set__(<Descriptor instance>, <Klass instance>, 999)
# evaldemo_meta module end
```

The `% MetaKlass.__new__:inner_2` line is triggered by `obj.method_c()` in `main`.

Let's now go back to the idea of the `Checked` class with the `Field` descriptors implementing
runtime type validation, and see how it can be done with a metaclass.

## A Metaclass Solution for Checked

We don't want to encourage premature optimization and overengineering, so here is a
make-believe scenario to justify rewriting `checkedlib.py` with `__slots__`, which requires the
application of a metaclass.  Feel free to skip it.

> **Note**
>
> **A bit of storytelling.**  Our `checkedlib.py` using `__init_subclass__` is a company-wide
> success, and our production servers have millions of instances of `Checked` subclasses in
> memory at any one time.  Profiling a proof-of-concept, we discover that using `__slots__`
> will reduce the cloud hosting bill for two reasons: lower memory usage, as `Checked`
> instances don't need their own `__dict__`; and higher performance, by removing
> `__setattr__`, which was created just to block unexpected attributes, but is triggered at
> instantiation and for all attribute setting before `Field.__set__` is called to do its job.

The new `checkedlib.py` is a drop-in replacement for the previous one.  The complexity is
abstracted away from the user: the only visible part of the library is the `Checked` base
class.  A `Movie` class using it is an instance of `CheckedMeta`, and a subclass of `Checked`.
Also, the `title`, `year` and `box_office` class attributes of `Movie` are three separate
instances of `Field`.  Each `Movie` instance has its own `_title`, `_year` and `_box_office`
slots, to store the values of the corresponding fields.

The `Field` descriptor class is now a bit different.  In the previous examples, each `Field`
descriptor instance stored its value in the managed instance using an attribute of the same
name.  This made it unnecessary for `Field` to provide a `__get__` method.  However, when a
class like `Movie` uses `__slots__`, it cannot have class attributes and instance attributes
with the same name.  Each descriptor instance is a class attribute, and now we need separate
per-instance storage attributes.  The code uses the descriptor name prefixed with a single
`_`.  Therefore `Field` instances have separate `name` and `storage_name` attributes, and we
implement `Field.__get__`:

```python
class Field:
    def __init__(self, name: str, constructor: Callable) -> None:
        if not callable(constructor) or constructor is type(None):
            raise TypeError(f'{name!r} type hint must be callable')
        self.name = name
        self.storage_name = '_' + name  # compute storage_name from name
        self.constructor = constructor

    def __get__(self, instance, owner=None):
        if instance is None:  # read from the managed class itself: return the descriptor
            return self
        return getattr(instance, self.storage_name)  # the value in the storage slot

    def __set__(self, instance: Any, value: Any) -> None:
        if value is ...:
            value = self.constructor()
        else:
            try:
                value = self.constructor(value)
            except (TypeError, ValueError) as e:
                type_name = self.constructor.__name__
                msg = f'{value!r} is not compatible with {self.name}:{type_name}'
                raise TypeError(msg) from e
        setattr(instance, self.storage_name, value)  # set or update the slot
```

Here is the metaclass that drives this example.  There's one modern wrinkle: to get the type
hints in prior examples, we used `typing.get_type_hints`, but that requires an existing class.
At this point, the class we are configuring does not exist yet, so we need to read the
annotations from the `cls_dict` — the namespace of the class under construction.  Through
Python 3.13, that namespace has an `__annotations__` dict.  Since Python 3.14, annotations are
evaluated lazily ([**PEP 649**](https://peps.python.org/pep-0649/) and
[**PEP 749**](https://peps.python.org/pep-0749/)): the namespace holds an annotate function
instead, which we can call using the new
[`annotationlib`](https://docs.python.org/3/library/annotationlib.html) module.  A helper
function handles both cases:

```python
def namespace_annotations(cls_dict) -> dict[str, Any]:
    if '__annotations__' in cls_dict:  # Python <= 3.13, or `from __future__ import annotations`
        return cls_dict['__annotations__']
    try:
        import annotationlib  # Python >= 3.14
    except ImportError:
        return {}
    annotate = annotationlib.get_annotate_from_class_namespace(cls_dict)
    if annotate is None:
        return {}
    return annotationlib.call_annotate_function(annotate, annotationlib.Format.FORWARDREF)

class CheckedMeta(type):

    def __new__(meta_cls, cls_name, bases, cls_dict):  # the only method in CheckedMeta
        if '__slots__' not in cls_dict:  # only enhance classes that don't declare __slots__
            slots = []
            type_hints = namespace_annotations(cls_dict)  # read from the namespace
            for name, constructor in type_hints.items():  # for each annotated attribute...
                field = Field(name, constructor)  # ...build a Field...
                cls_dict[name] = field  # ...put it in the namespace...
                slots.append(field.storage_name)  # ...and collect its storage name

            cls_dict['__slots__'] = slots  # populate __slots__ before the class exists

        return super().__new__(
                meta_cls, cls_name, bases, cls_dict)
```

If `__slots__` is already present, `CheckedMeta` assumes it is the `Checked` base class and not
a user-defined subclass, and builds the class as is.  The last part of the new `checkedlib.py`
is the `Checked` base class that users of this library will subclass.  It is the same as the
`__init_subclass__` version, with three changes:

1. Added an empty `__slots__` to signal to `CheckedMeta.__new__` that this class doesn't
   require special processing.
2. Removed `__init_subclass__`.  Its job is now done by `CheckedMeta.__new__`.
3. Removed `__setattr__`.  It became redundant because adding `__slots__` to the user-defined
   class prevents setting undeclared attributes.

```python
class Checked(metaclass=CheckedMeta):
    __slots__ = ()  # skip CheckedMeta.__new__ processing

    @classmethod
    def _fields(cls) -> dict[str, type]:
        return get_type_hints(cls)

    def __init__(self, **kwargs: Any) -> None:
        for name in self._fields():
            value = kwargs.pop(name, ...)
            setattr(self, name, value)
        if kwargs:
            self.__flag_unknown_attrs(*kwargs)

    def __flag_unknown_attrs(self, *names: str) -> NoReturn:
        plural = 's' if len(names) > 1 else ''
        extra = ', '.join(f'{name!r}' for name in names)
        cls_name = repr(self.__class__.__name__)
        raise AttributeError(f'{cls_name} object has no attribute{plural} {extra}')

    def _asdict(self) -> dict[str, Any]:
        return {
            name: getattr(self, name)
            for name, attr in self.__class__.__dict__.items()
            if isinstance(attr, Field)
        }

    def __repr__(self) -> str:
        kwargs = ', '.join(
            f'{key}={value!r}' for key, value in self._asdict().items()
        )
        return f'{self.__class__.__name__}({kwargs})'

class Movie(Checked):
    title: str
    year: int
    box_office: float

movie = Movie(title='The Godfather', year=1972, box_office=137)
movie
# Movie(title='The Godfather', year=1972, box_office=137.0)
Movie.__slots__  # configured by the metaclass
# ['_title', '_year', '_box_office']
hasattr(movie, '__dict__')  # no per-instance dict: memory saved
# False
type(Movie)
# <class '__main__.CheckedMeta'>
movie.director = 'Francis Ford Coppola'  # blocked by __slots__, no __setattr__ needed
# Traceback (most recent call last):
#   ...
# AttributeError: 'Movie' object has no attribute 'director' and no __dict__ for setting new attributes
```

That concise `Movie` class definition leverages three instances of the `Field` validating
descriptor, a `__slots__` configuration, five methods inherited from `Checked`, and a metaclass
to put it all together.  This concludes the third rendering of a class builder with validated
descriptors.  The next section covers some general issues related to metaclasses.

## Metaclasses in the Real World

Metaclasses are powerful, but tricky.  Before deciding to implement a metaclass, consider the
following points.

### Modern Features Simplify or Replace Metaclasses

Over time, several common use cases of metaclasses were made redundant by new language
features:

Class decorators
: Simpler to understand than metaclasses, and less likely to cause conflicts with base classes
  and metaclasses.

`__set_name__`
: Avoids the need for custom metaclass logic to automatically set the name of a descriptor.

`__init_subclass__`
: Provides a way to customize class creation that is transparent to the end user and even
  simpler than a decorator — but may introduce conflicts in a complex class hierarchy.

Built-in `dict` preserving key insertion order
: Eliminated the #1 reason to use `__prepare__`: to provide an `OrderedDict` to store the
  namespace of the class under construction.  Python only calls `__prepare__` on metaclasses,
  so if you needed to process the class namespace in the order it appears in the source code,
  you had to use a metaclass before Python 3.6.

`__class_getitem__`
: Added in Python 3.7 ([**PEP 560**](https://peps.python.org/pep-0560/)) so that classes can
  support subscription like `list[int]` without a metaclass implementing `__getitem__`.

Every actively maintained version of CPython supports all the features just listed.  Keep
advocating these features: there is too much unnecessary complexity in our profession, and
metaclasses are a gateway to complexity.

### Metaclasses Are Stable Language Features

Metaclasses were introduced in Python 2.2 in 2002, together with so-called "new-style
classes", descriptors and properties.  It is remarkable that the `MetaBunch` example, first
posted by Alex Martelli in July 2002, still works today — the only change being the way to
specify the metaclass to use, which in Python 3 is done with the syntax
`class Bunch(metaclass=MetaBunch):`.

None of the additions mentioned in the previous section broke existing code using
metaclasses.  But legacy code using metaclasses can often be simplified by leveraging those
features.

### A Class Can Only Have One Metaclass

If your class declaration involves two or more metaclasses, you will see this puzzling error
message:

```python
class PersistentMeta(type):
    pass

class Record(abc.ABC, metaclass=PersistentMeta):
    pass
# Traceback (most recent call last):
#   ...
# TypeError: metaclass conflict: the metaclass of a derived class must be a (non-strict) subclass of the metaclasses of all its bases
```

This may happen even without multiple inheritance, as that example shows.  We saw that
`abc.ABC` is an instance of the `abc.ABCMeta` metaclass.  If that `PersistentMeta` metaclass is
not itself a subclass of `abc.ABCMeta`, you get a metaclass conflict.  There are two ways of
dealing with that error:

* Find some other way of doing what you need to do, while avoiding at least one of the
  metaclasses involved.
* Write your own `PersistentABCMeta` metaclass as a subclass of both `abc.ABCMeta` and
  `PersistentMeta`, using multiple inheritance, and use that as the only metaclass for
  `Record`:

```python
class PersistentABCMeta(abc.ABCMeta, PersistentMeta):
    pass

class Record(abc.ABC, metaclass=PersistentABCMeta):
    pass

type(Record).__mro__
# (<class '__main__.PersistentABCMeta'>, <class 'abc.ABCMeta'>, <class '__main__.PersistentMeta'>, <class 'type'>, <class 'object'>)
```

> **Warning**
>
> One can imagine the solution of the metaclass with two base metaclasses implemented to meet
> a deadline.  But metaclass programming always takes longer than anticipated, which makes
> this approach risky before a hard deadline.  Even in the absence of known bugs, consider this
> approach as technical debt simply because it is hard to understand and maintain.

### Metaclasses Should Be Implementation Details

Besides `type`, there are only a handful of metaclasses in the entire standard library.  The
better known metaclasses are probably `abc.ABCMeta`, `typing.NamedTupleMeta` and
`enum.EnumType` (formerly `EnumMeta`).  None of them are intended to appear explicitly in user
code.  We may consider them implementation details.

Although you can do some really wacky metaprogramming with metaclasses, it's best to heed the
principle of least astonishment so that most users can indeed regard metaclasses as
implementation details.  In recent years, some metaclasses in the Python standard library were
replaced by other mechanisms, without breaking the public API of their packages.  The simplest
way to future-proof such APIs is to offer a regular class that users subclass to access the
functionality provided by the metaclass, as we've done in our examples.

To wrap up our coverage of class metaprogramming, here is a small but very cool metaclass
example.

## A Metaclass Hack with `__prepare__`

The simplest and most interesting metaclass idea that Luciano Ramalho found while updating
*Fluent Python* came from João S. O. Bueno — better known as JS in the Brazilian Python
community.  One application of his idea is to create a class that autogenerates numeric
constants:

<!-- nocheck -->
```python
class Flavor(AutoConst):
    banana
    coconut
    vanilla

Flavor.vanilla
# 2
Flavor.banana, Flavor.coconut
# (0, 1)
```

Yes, that code works as shown!  Here is the user-friendly `AutoConst` base class and the
metaclass behind it, implemented in `autoconst.py`:

<!-- nocheck -->
```python
class AutoConstMeta(type):
    def __prepare__(name, bases, **kwargs):
        return WilyDict()

class AutoConst(metaclass=AutoConstMeta):
    pass
```

That's it.  Clearly the trick is in `WilyDict`.  When Python processes the namespace of the
user's class and reads `banana`, it looks up that name in the mapping provided by
`__prepare__`: an instance of `WilyDict`.  `WilyDict` implements `__missing__`, covered in
[The `__missing__` Method](dicts-sets.md#the-__missing__-method).  The `WilyDict` instance
initially has no `'banana'` key, so the `__missing__` method is triggered.  It makes an item on
the fly with the key `'banana'` and the value `0`, returning that value.  Python is happy with
that, then tries to retrieve `'coconut'`.  `WilyDict` promptly adds that entry with the value
`1`, returning it.  The same happens with `'vanilla'`, which is then mapped to `2`.

We've seen `__prepare__` and `__missing__` before.  The real innovation is how JS put them
together.  Here is the source code for `WilyDict`, also from `autoconst.py`:

```python
class WilyDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__next_value = 0

    def __missing__(self, key):
        if key.startswith('__') and key.endswith('__'):
            raise KeyError(key)
        self[key] = value = self.__next_value
        self.__next_value += 1
        return value

class AutoConstMeta(type):
    def __prepare__(name, bases, **kwargs):
        return WilyDict()

class AutoConst(metaclass=AutoConstMeta):
    pass

class Flavor(AutoConst):
    banana
    coconut
    vanilla

Flavor.vanilla
# 2
Flavor.banana, Flavor.coconut
# (0, 1)
```

While experimenting, Ramalho found that Python looked up `__name__` in the namespace of the
class under construction, causing `WilyDict` to add a `__name__` entry, and increment
`__next_value`.  That's the reason for the `if` statement in `__missing__`, raising `KeyError`
for keys that look like dunder attributes.

Here are some ideas for extending JS's ingenious hack:

* Make it possible to retrieve the constant name if you have the value.  For example,
  `Flavor[2]` could return `'vanilla'`.  You can do this by implementing `__getitem__` in
  `AutoConstMeta`, or `__class_getitem__` in `AutoConst` itself.
* Support iteration over the class, by implementing `__iter__` on the metaclass, yielding the
  constants as `(name, value)` pairs.
* Implement a new `Enum` variant.  This would be a major undertaking, because the `enum`
  package is full of tricks, including the `EnumType` metaclass with hundreds of lines of code
  and a nontrivial `__prepare__` method.

Here are the first two ideas, implemented on the metaclass.  Special methods on a metaclass
apply to its instances — which are classes — so this is how to make a class itself
subscriptable and iterable, like `Enum` subclasses:

```python
class AutoConstMeta2(AutoConstMeta):
    def __getitem__(cls, value):  # Flavor2[2] -> 'vanilla'
        for name, val in cls:
            if val == value:
                return name
        raise KeyError(value)

    def __iter__(cls):  # iterate over (name, value) pairs
        for name, value in vars(cls).items():
            if not (name.startswith('__') and name.endswith('__')):
                yield name, value

class AutoConst2(metaclass=AutoConstMeta2):
    pass

class Flavor2(AutoConst2):
    banana
    coconut
    vanilla

Flavor2[2]
# 'vanilla'
list(Flavor2)
# [('banana', 0), ('coconut', 1), ('vanilla', 2)]
```

> **Note**
>
> The `__class_getitem__` special method was added to support generic types, as part of PEP 560
> and [**PEP 585**](https://peps.python.org/pep-0585/).  Thanks to `__class_getitem__`, Python's
> core developers did not have to write a new metaclass for the built-in types to implement
> `__getitem__` so that we could write generic type hints like `list[int]`.  This is a narrow
> feature, but representative of a wider use case for metaclasses: implementing operators and
> other special methods to work at the class level, such as making the class itself iterable,
> just like `Enum` subclasses.

## Wrapping Up

Metaclasses, as well as class decorators and `__init_subclass__`, are useful for:

* Subclass registration
* Subclass structural validation
* Applying decorators to many methods at once
* Object serialization
* Object-relational mapping
* Object-based persistence
* Implementing special methods at the class level
* Implementing class features found in other languages, such as traits and aspect-oriented
  programming

Class metaprogramming can also help with performance issues in some cases, by performing tasks
at import time that otherwise would execute repeatedly at runtime.

To wrap up, let's recall Alex Martelli's final advice from his essay "Waterfowl and ABCs"
(see [Interfaces, Protocols, and ABCs](protocols-abcs.md)):

> And, don't define custom ABCs (or metaclasses) in production code… if you feel the urge to do
> so, I'd bet it's likely to be a case of "all problems look like a nail"-syndrome for somebody
> who just got a shiny new hammer — you (and future maintainers of your code) will be much
> happier sticking with straightforward and simple code, eschewing such depths.

Martelli's advice applies not only to ABCs and metaclasses, but also to class hierarchies,
operator overloading, function decorators, descriptors, class decorators, and class builders
using `__init_subclass__`.  Those powerful tools exist primarily to support library and
framework development.  Applications naturally should use those tools, as provided by the
Python standard library or external packages.  But implementing them in application code is
often premature abstraction.

> Good frameworks are extracted, not invented.
>
> — David Heinemeier Hansson, creator of Ruby on Rails

## Summary

This chapter started with an overview of attributes found in class objects, such as
`__qualname__` and the `__subclasses__()` method.  Next, we saw how the `type` built-in can be
used to construct classes at runtime.

The `__init_subclass__` special method was introduced, with the first iteration of a `Checked`
base class designed to replace attribute type hints in user-defined subclasses with `Field`
instances that apply constructors to enforce the type of those attributes at runtime.  The same
idea was implemented with a `@checked` class decorator that adds features to user-defined
classes, similar to what `__init_subclass__` allows.  We saw that neither `__init_subclass__`
nor a class decorator can dynamically configure `__slots__`, because they operate only after a
class is created.

The concepts of "import time" and "runtime" were clarified with experiments showing the order
in which Python code is executed when modules, descriptors, class decorators and
`__init_subclass__` are involved.

Our coverage of metaclasses began with an overall explanation of `type` as a metaclass, and how
user-defined metaclasses can implement `__new__` to customize the classes they build.  We then
saw our first custom metaclass, the classic `MetaBunch` example using `__slots__`.  Next,
another evaluation time experiment demonstrated how the `__prepare__` and `__new__` methods of a
metaclass are invoked earlier than `__init_subclass__` and class decorators, providing
opportunities for deeper class customization.  The third iteration of a `Checked` class builder
with `Field` descriptors and custom `__slots__` configuration was presented — including how to
read annotations from a class namespace under the lazy annotations of Python 3.14 — followed by
some general considerations about metaclass usage in practice.

Finally, we saw the `AutoConst` hack invented by João S. O. Bueno, based on the cunning idea of
a metaclass with `__prepare__` returning a mapping that implements `__missing__`.  In less than
20 lines of code, `autoconst.py` showcases the power of combining Python metaprogramming
techniques.

> **Note**
>
> Properties let us start our programs simply, exposing attributes as public, knowing a public
> attribute can become a property at any time without much pain.  The descriptor idea goes way
> beyond that, providing a framework for abstracting away repetitive accessor logic — so
> effective that essential Python constructs use it behind the scenes.  Combined with functions
> as first-class objects, descriptors unify functions and methods: a function's `__get__`
> produces a method object on the fly by binding the instance to the `self` argument.  And with
> classes as first-class objects, a beginner-friendly language provides powerful abstractions
> such as class builders, class decorators and full-fledged, user-defined metaclasses — without
> complicating its suitability for casual programming.  The convenience and success of
> frameworks such as Django and SQLAlchemy owe much to these features.

> **See also**
>
> * [Customizing class creation](https://docs.python.org/3/reference/datamodel.html#customizing-class-creation)
>   in the Data Model chapter, which covers `__init_subclass__` and metaclasses; the
>   [`type`](https://docs.python.org/3/library/functions.html#type) documentation; and
>   [`types.new_class`](https://docs.python.org/3/library/types.html#types.new_class) and
>   `types.prepare_class`, which simplify dynamic class creation with metaclasses.
> * [**PEP 3129**](https://peps.python.org/pep-3129/) — Class Decorators, and
>   [**PEP 3115**](https://peps.python.org/pep-3115/) — Metaclasses in Python 3000, which
>   introduced `__prepare__`.
> * Caleb Hattingh's [autoslot](https://github.com/cjrh/autoslot) package: a metaclass that
>   creates `__slots__` automatically by inspecting the bytecode of `__init__` — only 74 lines,
>   and an excellent example to study.
> * Guido van Rossum's 2003 paper "Unifying types and classes in Python 2.2", which still
>   applies to modern Python, and Brett Slatkin's *Effective Python*, 2nd ed., with several
>   up-to-date examples of class building techniques.
> * [**PEP 638**](https://peps.python.org/pep-0638/) — Syntactic Macros, a draft proposal for
>   the ultimate metaprogramming feature, as offered by Lisp, Elixir and Rust.
