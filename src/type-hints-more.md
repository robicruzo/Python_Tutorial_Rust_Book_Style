# More About Type Hints

> I learned a painful lesson that for small programs, dynamic typing is great.  For
> large programs you need a more disciplined approach.  And it helps if the language
> gives you that discipline rather than telling you "Well, you can do whatever you
> want".
>
> — Guido van Rossum

This chapter is a sequel to [Type Hints in Functions](type-hints-functions.md), covering
more of Python's gradual type system.  The main topics are:

* overloaded function signatures;
* `typing.TypedDict` for type hinting dicts used as records;
* type casting;
* runtime access to type hints;
* generic types: declaring a generic class; variance (invariant, covariant and
  contravariant types); and generic static protocols.

Throughout this chapter we use the type parameter syntax introduced in Python 3.12 by
[**PEP 695**](https://peps.python.org/pep-0695/) — `class Box[T]: ...` and
`def first[T](xs: list[T]) -> T: ...` — and mention the older `TypeVar` spelling when it
helps to understand existing code.

## Overloaded Signatures

Python functions may accept different combinations of arguments.  The
[`@typing.overload`](https://docs.python.org/3/library/typing.html#typing.overload)
decorator allows annotating those different combinations.  This is particularly
important when the return type of the function depends on the type of two or more
parameters.

Consider the `sum` built-in function.  This is the text of `help(sum)`:

```text
sum(iterable, /, start=0)
    Return the sum of a 'start' value (default: 0) plus an iterable of numbers

    When the iterable is empty, return the start value.
    This function is intended specifically for use with numeric values and may
    reject non-numeric types.
```

The `sum` built-in is written in C, but typeshed has overloaded type hints for it, in
`builtins.pyi`.  In simplified form, they look like this:

<!-- nocheck -->
```python
@overload
def sum[T](iterable: Iterable[T], /) -> T | int: ...
@overload
def sum[T, S](iterable: Iterable[T], /, start: S) -> T | S: ...
```

First let's look at the overall syntax of overloads.  That's all the code about `sum`
you'll find in the stub file (`.pyi`).  The implementation would be in a different file.
The ellipsis (`...`) has no function other than to fulfill the syntactic requirement for
a function body, similar to `pass`.  So `.pyi` files are valid Python files.  The `/`
marks the preceding parameters as positional-only (see
[Annotating Positional-Only and Variadic Parameters](type-hints-functions.md#annotating-positional-only-and-variadic-parameters)):
you can call `sum(my_list)`, but not `sum(iterable=my_list)`.

The type checker tries to match the given arguments with each overloaded signature, in
order.  The call `sum(range(100), 1000)` doesn't match the first overload, because that
signature has only one parameter.  But it matches the second.

You can also use `@overload` in a regular Python module, by writing the overloaded
signatures right before the function's actual signature and implementation.  Here is
how `sum` would appear annotated and implemented in a Python module:

```python
import functools
import operator
from collections.abc import Iterable
from typing import overload

@overload
def sum[T](it: Iterable[T], /) -> T | int: ...
@overload
def sum[T, S](it: Iterable[T], /, start: S) -> T | S: ...
def sum(it, /, start=0):
    return functools.reduce(operator.add, it, start)

sum([1, 2, 3])
# 6
sum([[1], [2]], [])
# [1, 2]
```

The first signature is for the simple case: `sum(my_iterable)`.  The result type may be
`T` — the type of the elements that `my_iterable` yields — or it may be `int` if the
iterable is empty, because the default value of the `start` parameter is `0`.  When
`start` is given, it can be of any type `S`, so the result type is `T | S`.  This is why
we need a second type parameter `S`.  If we reused `T`, then the type of `start` would
have to be the same type as the elements of `Iterable[T]`.  The signature of the actual
function implementation has no type hints.

That's a lot of lines to annotate a one-line function.  Probably overkill.  If you want to
learn about `@overload` by reading code, typeshed has hundreds of examples; the stub file
for Python's built-ins alone has more overloads than any other in the standard library.

> **Tip**
>
> Aiming for 100% of annotated code may lead to type hints that add lots of noise but
> little value.  Refactoring to simplify type hinting can lead to cumbersome APIs.
> Sometimes it's better to be pragmatic and leave a piece of code without type hints.
> Take advantage of gradual typing.

The handy APIs we call Pythonic are often hard to annotate.  In the next section we'll
see an example: six overloads are needed to properly annotate the flexible `max`
built-in function.

### Max Overload

It is difficult to add type hints to functions that leverage the powerful dynamic
features of Python.  A typeshed bug report once revealed that Mypy failed to warn that it
is illegal to pass `None` as one of the arguments to the built-in `max()` function, or to
pass an iterable that at some point yields `None`.  In either case, you get a runtime
exception like this one:

```python
max([1, None])
# Traceback (most recent call last):
#   ...
# TypeError: '>' not supported between instances of 'NoneType' and 'int'
```

The documentation of `max` starts with this sentence: "Return the largest item in an
iterable or the largest of two or more arguments."  That's a very intuitive description.
But if you must annotate a function described in those terms, you have to ask: which is
it?  An iterable or two or more arguments?  The reality is more complicated because `max`
also takes two optional keyword arguments: `key` and `default`.

Here is `max` coded in Python, to make it easier to see the relationship between how it
works and the overloaded annotations (the built-in `max` is in C):

```python
MISSING = object()
EMPTY_MSG = 'max() arg is an empty sequence'

def max(first, *args, key=None, default=MISSING):
    if args:
        series = args
        candidate = first
    else:
        series = iter(first)
        try:
            candidate = next(series)
        except StopIteration:
            if default is not MISSING:
                return default
            raise ValueError(EMPTY_MSG) from None
    if key is None:
        for current in series:
            if candidate < current:
                candidate = current
    else:
        candidate_key = key(candidate)
        for current in series:
            current_key = key(current)
            if candidate_key < current_key:
                candidate = current
                candidate_key = current_key
    return candidate
```

The focus of this example is not the logic of `max`, so we will not spend time with its
implementation, other than explaining `MISSING`.  The `MISSING` constant is a unique
`object` instance used as a *sentinel*.  It is the default value for the `default=`
keyword argument, so that `max` can accept `default=None` and still distinguish between
these two situations:

1. The user did not provide a value for `default=`, so it is `MISSING`, and `max` raises
   `ValueError` if `first` is an empty iterable.
2. The user provided some value for `default=`, including `None`, so `max` returns that
   value if `first` is an empty iterable.

Here are the type hints that fixed the typeshed issue, at the top of the same module:

<!-- nocheck -->
```python
from collections.abc import Callable, Iterable
from typing import Protocol, Any, overload

class SupportsLessThan(Protocol):
    def __lt__(self, other: Any) -> bool: ...

@overload
def max[LT: SupportsLessThan](arg1: LT, arg2: LT, /, *args: LT,
                               key: None = ...) -> LT:
    ...
@overload
def max[T, LT: SupportsLessThan](arg1: T, arg2: T, /, *args: T,
                                  key: Callable[[T], LT]) -> T:
    ...
@overload
def max[LT: SupportsLessThan](iterable: Iterable[LT], /, *,
                               key: None = ...) -> LT:
    ...
@overload
def max[T, LT: SupportsLessThan](iterable: Iterable[T], /, *,
                                  key: Callable[[T], LT]) -> T:
    ...
@overload
def max[LT: SupportsLessThan, DT](iterable: Iterable[LT], /, *,
                                   key: None = ..., default: DT) -> LT | DT:
    ...
@overload
def max[T, LT: SupportsLessThan, DT](iterable: Iterable[T], /, *,
                                      key: Callable[[T], LT],
                                      default: DT) -> T | DT:
    ...
```

The Python implementation of `max` is about the same length as all those typing imports
and declarations.  Thanks to duck typing, that code has no `isinstance` checks, and
provides the same error checking as those type hints — but only at runtime, of course.

A key benefit of `@overload` is declaring the return type as precisely as possible,
according to the types of the arguments given.  We'll see that benefit next by studying
the overloads for `max` in groups of one or two at a time.

**Arguments implementing `SupportsLessThan`, but `key` and `default` not provided.**  In
the first and third overloads, the inputs are either separate arguments of type `LT`
implementing `SupportsLessThan`, or an `Iterable` of such items.  The return type of
`max` is the same as the actual arguments or items, as we saw in
[Bounded type variables](type-hints-functions.md#bounded-type-variables).  Sample calls
that match these overloads:

```python
max(1, 2, -3)
# 2
max(['Go', 'Python', 'Rust'])
# 'Rust'
```

**Argument `key` provided, but no `default`.**  In the second and fourth overloads, the
inputs can be separate items of any type `T` or a single `Iterable[T]`, and `key=` must
be a callable that takes an argument of the same type `T`, and returns a value that
implements `SupportsLessThan`.  The return type of `max` is the same as the actual
arguments:

```python
max(1, 2, -3, key=abs)
# -3
max(['Go', 'Python', 'Rust'], key=len)
# 'Python'
```

**Argument `default` provided, but no `key`.**  In the fifth overload, the input is an
iterable of items of type `LT` implementing `SupportsLessThan`.  The `default=` argument
is the return value when the `Iterable` is empty.  Therefore the return type of `max`
must be a union of type `LT` and the type of the `default` argument:

```python
max([1, 2, -3], default=0)
# 2
max([], default=None)  # returns None, so the console shows nothing
```

**Arguments `key` and `default` provided.**  In the last overload, the inputs are an
`Iterable` of items of any type `T`, a callable that takes an argument of type `T` and
returns a value of type `LT` that implements `SupportsLessThan`, and a default value of
any type `DT`.  The return type of `max` must be a union of type `T` or the type of the
`default` argument:

```python
max([1, 2, -3], key=abs, default=None)
# -3
max([], key=abs, default=None)  # returns None
```

#### Takeaways from overloading `max`

Type hints allow Mypy to flag a call like `max([None, None])` with this error message:

```console
mymax_demo.py:109: error: Value of type variable "LT" of "max"
  cannot be "None"
```

On the other hand, having to write so many lines to support the type checker may
discourage people from writing convenient and flexible functions like `max`.  If you had
to reinvent the `min` function as well, you could refactor and reuse most of the
implementation of `max`, but you'd have to copy and paste all overloaded declarations —
even though they would be identical for `min`, except for the function name.  As
Python developer João S. O. Bueno put it: "Although it is this hard to express the
signature of `max` — it fits in one's mind quite easily.  My understanding is that the
expressiveness of annotation markings is very limited, compared to that of Python."

Now let's study the `TypedDict` typing construct.  It is not as useful as one might
imagine at first, but has its uses.  Experimenting with `TypedDict` demonstrates the
limitations of static typing for handling dynamic structures, such as JSON data.

## `TypedDict`

> **Warning**
>
> It's tempting to use `TypedDict` to protect against errors while handling dynamic data
> structures like JSON API responses.  But the examples here make clear that correct
> handling of JSON must be done at runtime, and not with static type checking.  For
> runtime checking of JSON-like structures using type hints, check out the
> [pydantic](https://pypi.org/project/pydantic/) package on PyPI.

Python dictionaries are sometimes used as records, with the keys used as field names and
field values of different types.  For example, consider a record describing a book in
JSON or Python:

```json
{"isbn": "0134757599",
 "title": "Refactoring, 2e",
 "authors": ["Martin Fowler", "Kent Beck"],
 "pagecount": 478}
```

Before Python 3.8, there was no good way to annotate a record like that, because the
mapping types we saw in [Generic Mappings](type-hints-functions.md#generic-mappings)
limit all values to have the same type.  Here are two lame attempts to annotate a record
like the preceding JSON object:

`dict[str, Any]`
: The values may be of any type.

`dict[str, str | int | list[str]]`
: Hard to read, and doesn't preserve the relationship between field names and their
  respective field types: `title` is supposed to be a `str`, it can't be an `int` or a
  `list[str]`.

[**PEP 589**](https://peps.python.org/pep-0589/) — TypedDict: Type Hints for
Dictionaries with a Fixed Set of Keys addressed that problem.  Here is a simple
`TypedDict`:

```python
from typing import TypedDict

class BookDict(TypedDict):
    isbn: str
    title: str
    authors: list[str]
    pagecount: int
```

At first glance, `typing.TypedDict` may seem like a data class builder, similar to
`typing.NamedTuple` — covered in [Data Class Builders](dataclasses.md).  The syntactic
similarity is misleading.  `TypedDict` is very different.  It exists only for the benefit
of type checkers, and has no runtime effect.  `TypedDict` provides two things:

* class-like syntax to annotate a `dict` with type hints for the value of each "field";
* a constructor that tells the type checker to expect a `dict` with the keys and values as
  specified.

At runtime, a `TypedDict` constructor such as `BookDict` is a placebo: it has the same
effect as calling the `dict` constructor with the same arguments.  The fact that
`BookDict` creates a plain `dict` also means that:

* the "fields" in the pseudoclass definition don't create instance attributes;
* you can't write initializers with default values for the "fields";
* method definitions are not allowed.

Let's explore the behavior of a `BookDict` at runtime:

```python
pp = BookDict(title='Programming Pearls',
              authors='Jon Bentley',  # oops: authors takes a list, but no runtime check
              isbn='0201657880',
              pagecount=256)
pp
# {'title': 'Programming Pearls', 'authors': 'Jon Bentley', 'isbn': '0201657880',
#  'pagecount': 256}
type(pp)  # the result of calling BookDict is a plain dict...
# <class 'dict'>
pp.title  # ...therefore you can't read the data using object.field notation
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# AttributeError: 'dict' object has no attribute 'title'
pp['title']
# 'Programming Pearls'
BookDict.__annotations__  # the type hints are in BookDict.__annotations__, not in pp
# {'isbn': <class 'str'>, 'title': <class 'str'>, 'authors': list[str],
#  'pagecount': <class 'int'>}
```

You can call `BookDict` like a `dict` constructor with keyword arguments, or passing a
`dict` argument — including a `dict` literal.  We forgot that `authors` takes a list,
but gradual typing means no type checking at runtime.

Without a type checker, `TypedDict` is as useful as comments: it may help people read
the code, but that's it.  In contrast, the class builders from
[Data Class Builders](dataclasses.md) are useful even if you don't use a type checker,
because at runtime they generate or enhance a custom class that you can instantiate.

Here is a valid `BookDict`, with some operations on it.  This shows how `TypedDict`
enables Mypy to catch errors:

```python
from typing import TYPE_CHECKING

def demo() -> None:  # remember to add a return type, so Mypy doesn't ignore the function
    book = BookDict(  # a valid BookDict: all keys present, values of the correct types
        isbn='0134757599',
        title='Refactoring, 2e',
        authors=['Martin Fowler', 'Kent Beck'],
        pagecount=478
    )
    authors = book['authors']  # Mypy infers the type from BookDict's 'authors' key
    if TYPE_CHECKING:  # only True when the program is being type checked
        reveal_type(authors)
    authors = 'Bob'  # the last three lines are illegal
    book['weight'] = 4.2
    del book['title']

demo()  # at runtime, nothing complains
```

Type checking that code, we get:

```console
…/typeddict/ $ mypy demo_books.py
demo_books.py:13: note: Revealed type is "builtins.list[builtins.str]"
demo_books.py:14: error: Incompatible types in assignment
                  (expression has type "str", variable has type "list[str]")
demo_books.py:15: error: TypedDict "BookDict" has no key "weight"
demo_books.py:16: error: Key "title" of TypedDict "BookDict" cannot be deleted
Found 3 errors in 1 file (checked 1 source file)
```

The note is the result of `reveal_type(authors)`.  The type of the `authors` variable
was inferred from the type of the `book['authors']` expression that initialized it.  You
can't assign a `str` to a variable of type `list[str]`: type checkers usually don't allow
the type of a variable to change.  You also cannot assign to a key that is not part of
the `BookDict` definition, and cannot delete a key that is part of it.

Now let's see `BookDict` used in function signatures, to type check function calls.
Imagine you need to generate XML from book records, similar to this:

```xml
<BOOK>
  <ISBN>0134757599</ISBN>
  <TITLE>Refactoring, 2e</TITLE>
  <AUTHOR>Martin Fowler</AUTHOR>
  <AUTHOR>Kent Beck</AUTHOR>
  <PAGECOUNT>478</PAGECOUNT>
</BOOK>
```

If you were writing MicroPython code to be embedded in a tiny microcontroller (where
`lxml` and even `xml.etree.ElementTree` don't fit the limited RAM), you might write a
function like this:

```python
AUTHOR_ELEMENT = '<AUTHOR>{}</AUTHOR>'

def to_xml(book: BookDict) -> str:  # the point of the example: BookDict in the signature
    elements: list[str] = []  # collections that start empty often need an annotation
    for key, value in book.items():
        if isinstance(value, list):  # Mypy understands isinstance checks
            elements.extend(
                AUTHOR_ELEMENT.format(n) for n in value)
        else:
            tag = key.upper()
            elements.append(f'<{tag}>{value}</{tag}>')
    xml = '\n\t'.join(elements)
    return f'<BOOK>\n\t{xml}\n</BOOK>'
```

It's often necessary to annotate collections that start empty, otherwise Mypy can't infer
the type of the elements.  Mypy understands `isinstance` checks, and treats `value` as a
`list` in the block they guard.  Using `key == 'authors'` as the condition instead would
make Mypy report an error in the next line — `"object" has no attribute "__iter__"` —
because it infers the type of `value` returned from `book.items()` as `object`, which
doesn't support the `__iter__` method required by the generator expression.

Here is a function that parses a JSON `str` and returns a `BookDict`:

```python
import json

def from_json(data: str) -> BookDict:
    whatever = json.loads(data)  # the return type of json.loads() is Any
    return whatever  # Any is consistent-with every type, including BookDict
```

The second point is very important to keep in mind: Mypy will not flag any problem in
this code, but at runtime the value in `whatever` may not conform to the `BookDict`
structure — in fact, it may not be a `dict` at all!  If you run Mypy with
`--disallow-any-expr`, it will complain about the two lines in the body of `from_json`:

```console
…/typeddict/ $ mypy books_any.py --disallow-any-expr
books_any.py:30: error: Expression has type "Any"
books_any.py:31: error: Expression has type "Any"
Found 2 errors in 1 file (checked 1 source file)
```

We can silence the type error by adding a type hint to the initialization of the
`whatever` variable:

```python
def from_json(data: str) -> BookDict:
    whatever: BookDict = json.loads(data)  # no error: Any immediately assigned to a hinted variable
    return whatever
```

> **Warning**
>
> Don't be lulled into a false sense of type safety by that annotation!  Looking at the
> code at rest, the type checker cannot predict that `json.loads()` will return anything
> that resembles a `BookDict`.  Only runtime validation can guarantee that.

Static type checking is unable to prevent errors with code that is inherently dynamic,
such as `json.loads()`, which builds Python objects of different types at runtime:

```python
NOT_BOOK_JSON = """
    {"title": "Andromeda Strain",
     "flavor": "pistachio",
     "authors": true}
"""
not_book = from_json(NOT_BOOK_JSON)  # this does not produce a valid BookDict
print(not_book)
# {'title': 'Andromeda Strain', 'flavor': 'pistachio', 'authors': True}
print(not_book['flavor'])  # BookDict has no 'flavor' key, but the JSON source does
# pistachio
xml = to_xml(not_book)  # remember the signature: def to_xml(book: BookDict) -> str
print(xml)
# <BOOK>
# 	<TITLE>Andromeda Strain</TITLE>
# 	<FLAVOR>pistachio</FLAVOR>
# 	<AUTHORS>True</AUTHORS>
# </BOOK>
```

A type checker would reveal the type of `not_book` as `BookDict` and of
`not_book['authors']` as `list[str]` — the nominal types, not the runtime contents — and
would flag `not_book['flavor']` because that key does not exist in the nominal type.  But
at runtime, the program outputs nonsense with no errors: `to_xml` takes a `BookDict`
argument, but there is no runtime checking.  Garbage in, garbage out.

If you look at the code for `to_xml` through the lens of duck typing, the argument `book`
must provide an `.items()` method that returns an iterable of tuples like
`(key, value)` where `key` must have an `.upper()` method and `value` can be anything.
The point of this demonstration: when handling data with a dynamic structure, such as
JSON or XML, `TypedDict` is absolutely not a replacement for data validation at runtime.

`TypedDict` has more features.  Keys can be marked as optional with `total=False` on the
class, or individually with
[`NotRequired[...]`](https://docs.python.org/3/library/typing.html#typing.NotRequired)
(and the reverse with `Required[...]`), both added in Python 3.11 by
[**PEP 655**](https://peps.python.org/pep-0655/).  Python 3.13 added
[`ReadOnly[...]`](https://docs.python.org/3/library/typing.html#typing.ReadOnly)
([**PEP 705**](https://peps.python.org/pep-0705/)) for keys that must not be modified.
`TypedDict` also supports a limited form of inheritance, generics, and an alternative
functional declaration syntax.  The required and optional keys are recorded at runtime:

```python
from typing import NotRequired

class MovieDict(TypedDict):
    title: str
    year: NotRequired[int]

sorted(MovieDict.__required_keys__), sorted(MovieDict.__optional_keys__)
# (['title'], ['year'])
```

Finally, `TypedDict` makes it possible to annotate `**kwargs` precisely:
`def f(**kwargs: Unpack[MovieDict])` says that `f` accepts the keyword arguments `title`
and, optionally, `year` ([**PEP 692**](https://peps.python.org/pep-0692/), Python 3.12).

Now let's turn our attention to a function that is best avoided, but sometimes is
unavoidable: `typing.cast`.

## Type Casting

No type system is perfect, and neither are the static type checkers, the type hints in
the typeshed project, or the type hints in the third-party packages that have them.  The
[`typing.cast()`](https://docs.python.org/3/library/typing.html#typing.cast) special
function provides one way to handle type checking malfunctions or incorrect type hints in
code we can't fix.  The Mypy documentation explains: "Casts are used to silence spurious
type checker warnings and give the type checker a little help when it can't quite
understand what is going on."

At runtime, `typing.cast` does absolutely nothing.  This is its implementation:

<!-- nocheck -->
```python
def cast(typ, val):
    """Cast a value to a type.

    This returns the value unchanged.  To the type checker this
    signals that the return value has the designated type, but at
    runtime we intentionally don't check anything (we want this
    to be as fast as possible).
    """
    return val
```

PEP 484 requires type checkers to "blindly believe" the type stated in the `cast`.  The
"Casts" section of PEP 484 gives an example where the type checker needs the guidance of
`cast`:

```python
from typing import cast

def find_first_str(a: list[object]) -> str:
    index = next(i for i, x in enumerate(a) if isinstance(x, str))
    # We only get here if there's at least one string
    return cast(str, a[index])

find_first_str([1, 2.5, 'three', 'four'])
# 'three'
```

The `next()` call on the generator expression will either return the index of a `str`
item or raise `StopIteration`.  Therefore, `find_first_str` will always return a `str`
if no exception is raised, and `str` is the declared return type.  But if the last line
were just `return a[index]`, Mypy would infer the return type as `object` because the `a`
argument is declared as `list[object]`.  So the `cast()` is required to guide Mypy.  (The
use of `enumerate` here is intended to confuse the type checker; a simpler implementation
yielding strings directly is correctly analyzed by Mypy, and needs no `cast()`.)

Another typical use is to correct an outdated type hint for a library.  For example,
while working on an asyncio server, the author of *Fluent Python* wrote
`addr = server.sockets[0].getsockname()`, and Mypy reported
`Value of type "Optional[List[socket]]" is not indexable`, because the type hint for
`Server.sockets` on typeshed was outdated.  Since he couldn't fix typeshed right away, he
added a cast, after reading asyncio source code to find the correct type of the sockets
(the `TransportSocket` class from the undocumented `asyncio.trsock` module):

<!-- nocheck -->
```python
from asyncio.trsock import TransportSocket
from typing import cast

# ... many lines omitted ...

    socket_list = cast(tuple[TransportSocket, ...], server.sockets)
    addr = socket_list[0].getsockname()
```

(He also reported the typeshed issue, and it was quickly fixed.)

> **Warning**
>
> Don't get too comfortable using `cast` to silence Mypy, because Mypy is usually right
> when it reports an error.  If you are using `cast` very often, that's a code smell.
> Your team may be misusing type hints, or you may have low-quality dependencies in your
> codebase.

Despite the downsides, there are valid uses for `cast`.  As Guido van Rossum wrote:
"What's wrong with the occasional `cast()` call or `# type: ignore` comment?"  It is
unwise to completely ban the use of `cast`, especially because the other workarounds are
worse:

* `# type: ignore` is less informative.  (The syntax `# type: ignore[code]` lets you
  specify which error code is being silenced.)
* Using `Any` is contagious: since `Any` is consistent-with all types, abusing it may
  produce cascading effects through type inference, undermining the type checker's
  ability to detect errors in other parts of the code.

Of course, not all typing mishaps can be fixed with `cast`.  Sometimes we need
`# type: ignore`, the occasional `Any`, or even leaving a function without type hints.

> **Tip**
>
> When the reason for a cast is a runtime check the type checker doesn't understand,
> consider writing a *type predicate* function instead.  A function annotated to return
> [`TypeIs[str]`](https://docs.python.org/3/library/typing.html#typing.TypeIs) (Python
> 3.13, [**PEP 742**](https://peps.python.org/pep-0742/)) or `TypeGuard[str]` (Python
> 3.10) tells the checker that, when the function returns `True`, its argument is a
> `str`, which narrows the type inside an `if` block just like `isinstance` does.

Next, let's talk about using annotations at runtime.

## Reading Type Hints at Runtime

Python stores the type hints of functions, classes and modules in attributes named
`__annotations__`.  For instance, consider this annotated `clip` function:

```python
def clip(text: str, max_len: int = 80) -> str:
    """Return text clipped at the last space before or after max_len"""
    text = text.rstrip()
    end = len(text)
    if len(text) > max_len:
        space_before = text.rfind(' ', 0, max_len)
        if space_before >= 0:
            end = space_before
        else:
            space_after = text.find(' ', max_len)
            if space_after >= 0:
                end = space_after
    return text[:end].rstrip()
```

The type hints are stored as a `dict` in the `__annotations__` attribute of the
function:

```python
clip.__annotations__
# {'text': <class 'str'>, 'max_len': <class 'int'>, 'return': <class 'str'>}
```

The `'return'` key maps to the return type hint after the `->` symbol.  Note that the
values in the annotations are the Python classes `str` and `int`, and not the strings
`'str'` and `'int'`: the annotations were *evaluated* by the interpreter.

*When* they are evaluated has changed over the years, and it matters to anyone who reads
annotations at runtime.

### Problems with Annotations at Runtime

Up to Python 3.13, annotations were evaluated eagerly — at import time, when the `def` or
`class` statement runs, just as parameter default values are.  The increased use of type
hints raised two problems with that:

* Importing modules uses more CPU and memory when many type hints are used.
* Referring to types not yet defined requires using strings instead of actual types.

The second problem is the "forward reference" problem: a type hint that needs to refer to
a class defined below in the same module.  A common manifestation doesn't look like a
forward reference at all: a method that returns a new object of the same class.  Since
the class object is not defined until Python completely evaluates the class body, type
hints had to use the name of the class as a string:

```python
class Rectangle:
    def __init__(self, width: float, height: float = 1.0) -> None:
        self.width, self.height = width, height

    def stretch(self, factor: float) -> 'Rectangle':
        return Rectangle(width=self.width * factor)
```

Static type checkers were designed to deal with that from the beginning.  But at runtime,
if you read the return annotation for `stretch`, you get the string `'Rectangle'` instead
of a reference to the actual class.  Now your code needs to figure out what that string
means.  The [`typing.get_type_hints()`](https://docs.python.org/3/library/typing.html#typing.get_type_hints)
function does that, by evaluating such strings in the appropriate namespaces:

```python
Rectangle.stretch.__annotations__
# {'factor': <class 'float'>, 'return': 'Rectangle'}
from typing import get_type_hints
get_type_hints(Rectangle.stretch)
# {'factor': <class 'float'>, 'return': <class '__main__.Rectangle'>}
```

[**PEP 563**](https://peps.python.org/pep-0563/) — Postponed Evaluation of Annotations
tried to solve both problems in Python 3.7.  In any module that starts with
`from __future__ import annotations`, annotations are not evaluated at all; they are
stored as strings, and `get_type_hints()` is needed to turn them back into objects.  The
plan was to make that the default, but the maintainers of libraries that rely on type
hints at runtime, such as pydantic and FastAPI, showed that `get_type_hints()` can't
resolve all strings — for example, names defined inside a function or a class body.  The
Steering Council postponed the change, and eventually chose a different design.

### Lazy Annotations in Python 3.14 and Later

[**PEP 649**](https://peps.python.org/pep-0649/) and
[**PEP 749**](https://peps.python.org/pep-0749/), implemented in Python 3.14, made
annotations *lazy*: the compiler stores the annotation expressions in a hidden function,
and that function runs only when someone asks for `__annotations__`.  So in Python 3.14
and later:

* annotations cost almost nothing at import time if no one reads them;
* forward references just work, without quotes — `def stretch(self, factor: float) ->
  Rectangle:` is fine inside the body of `Rectangle`;
* reading `__annotations__` gives real objects, as before, evaluated on first access.

The new [`annotationlib`](https://docs.python.org/3/library/annotationlib.html) module
lets you choose how annotations are returned, which matters when some name in them is
still undefined:

<!-- nocheck -->
```python
from annotationlib import get_annotations, Format

def f(x: Undefined) -> int: ...

get_annotations(f, format=Format.FORWARDREF)
# {'x': ForwardRef('Undefined', ...), 'return': <class 'int'>}
get_annotations(f, format=Format.STRING)
# {'x': 'Undefined', 'return': 'int'}
get_annotations(f)  # Format.VALUE, the default, evaluates everything
# Traceback (most recent call last):
#   ...
# NameError: name 'Undefined' is not defined
```

`from __future__ import annotations` still works, and still produces strings; it is
expected to be deprecated and eventually removed.

### Dealing with the Problem

Given that the rules have changed across versions, if you need to read annotations at
runtime:

* Avoid reading `__annotations__` directly; instead, use `annotationlib.get_annotations`
  (Python 3.14+), `inspect.get_annotations` (Python 3.10+) or `typing.get_type_hints`.
  See the [Annotations Best Practices](https://docs.python.org/3/howto/annotations.html)
  HOWTO, which is required reading.
* Write a thin wrapper function of your own around one of those functions, and have the
  rest of your codebase call that custom function, so that future changes are localized
  to a single place.

To demonstrate the second point, here are the first lines of the `Checked` class that
we'll study in [Class Metaprogramming](class-metaprogramming.md):

<!-- nocheck -->
```python
class Checked:
    @classmethod
    def _fields(cls) -> dict[str, type]:
        return get_type_hints(cls)
    # ... more lines ...
```

The `Checked._fields` class method protects other parts of the module from depending
directly on `typing.get_type_hints`.  If you want to replace it with
`annotationlib.get_annotations`, the change is limited to `Checked._fields` and does not
affect the rest of your program.

> **Note**
>
> Companies using Python at a very large scale want the benefits of static typing, but
> they don't want to pay the price for the evaluation of the type hints at import time.
> Static checking happens at developer workstations and CI servers, but loading modules
> happens at a much higher frequency in production.  Meanwhile, the creators and users of
> pydantic and FastAPI want type objects available at runtime.  Lazy annotations are the
> compromise that serves both groups.

The remaining sections of this chapter cover generics, starting with how to define a
generic class that can be parameterized by its users.

## Implementing a Generic Class

In [Interfaces, Protocols, and ABCs](protocols-abcs.md#defining-and-using-an-abc) we
defined the `Tombola` ABC: an interface for classes that work like a bingo cage.  The
`LottoBlower` class from the same chapter is a concrete implementation.  Now we'll study a
generic version of `LottoBlower`, used like this:

<!-- nocheck -->
```python
from generic_lotto import LottoBlower

machine = LottoBlower[int](range(1, 11))  # to instantiate a generic class, give it a type

first = machine.pick()  # Mypy will correctly infer that first is an int...
remain = machine.inspect()  # ...and that remain is a tuple of integers
```

In addition, Mypy reports violations of the parameterized type with helpful messages:

<!-- nocheck -->
```python
from generic_lotto import LottoBlower

machine = LottoBlower[int]([1, .2])
## error: List item 1 has incompatible type "float";
##        expected "int"

machine = LottoBlower[int](range(1, 11))

machine.load('ABC')
## error: Argument 1 to "load" of "LottoBlower"
##        has incompatible type "str";
##        expected "Iterable[int]"
## note:  Following member(s) of "str" have conflicts:
## note:      Expected:
## note:          def __iter__(self) -> Iterator[int]
## note:      Got:
## note:          def __iter__(self) -> Iterator[str]
```

Upon instantiation of `LottoBlower[int]`, Mypy flags the `float`.  When calling
`.load('ABC')`, Mypy explains why a `str` won't do: `str.__iter__` returns an
`Iterator[str]`, but `LottoBlower[int]` requires an `Iterator[int]`.  Here is the
implementation:

<!-- nocheck -->
```python
import random
from collections.abc import Iterable

from tombola import Tombola

class LottoBlower[T](Tombola):

    def __init__(self, items: Iterable[T]) -> None:
        self._balls = list[T](items)

    def load(self, items: Iterable[T]) -> None:
        self._balls.extend(items)

    def pick(self) -> T:
        try:
            position = random.randrange(len(self._balls))
        except ValueError:
            raise LookupError('pick from empty LottoBlower')
        return self._balls.pop(position)

    def loaded(self) -> bool:
        return bool(self._balls)

    def inspect(self) -> tuple[T, ...]:
        return tuple(self._balls)
```

The `[T]` after the class name declares `T` as a formal type parameter of
`LottoBlower`.  The `items` argument in `__init__()` is of type `Iterable[T]`, which
becomes `Iterable[int]` when an instance is declared as `LottoBlower[int]`.  The `load`
method is likewise constrained.  The return type of `pick`, `T`, becomes `int` in a
`LottoBlower[int]`.  `loaded` has no type parameter in its signature.  Finally, `T` sets
the type of the items in the tuple returned by `inspect`.

> **Note**
>
> Before Python 3.12, the same class was written by declaring a module-level type
> variable, `T = TypeVar('T')`, and subclassing `Generic[T]` as well:
> `class LottoBlower(Tombola, Generic[T]):`.  That's why generic class declarations in
> older code often use multiple inheritance.  The new syntax creates the `TypeVar` and
> the `Generic` base for you, scoped to the class:
>
> ```python
> class Box[T]:
>     def __init__(self, item: T) -> None:
>         self.item = item
>
> Box.__type_params__
> # (T,)
> Box.__mro__
> # (<class '__main__.Box'>, <class 'typing.Generic'>, <class 'object'>)
> ```

The [User-defined generic types](https://docs.python.org/3/library/typing.html#user-defined-generic-types)
section of the `typing` module documentation is short, presents good examples, and
provides a few more details.

Now that we've seen how to implement a generic class, let's define the terminology to
talk about generics.

### Basic Jargon for Generic Types

Here are a few definitions that are useful when studying generics (the terms are from
Joshua Bloch's *Effective Java*):

**Generic type**
: A type declared with one or more type variables.  Examples: `LottoBlower[T]`,
  `abc.Mapping[KT, VT]`.

**Formal type parameter**
: The type variables that appear in a generic type declaration.  Example: `KT` and `VT` in
  the previous example `abc.Mapping[KT, VT]`.

**Parameterized type**
: A type declared with actual type parameters.  Examples: `LottoBlower[int]`,
  `abc.Mapping[str, float]`.

**Actual type parameter**
: The actual types given as parameters when a parameterized type is declared.  Example:
  the `int` in `LottoBlower[int]`.

The next topic is about how to make generic types more flexible, introducing the concepts
of covariance, contravariance and invariance.

## Variance

> **Note**
>
> Depending on your experience with generics in other languages, this may be the most
> challenging section in this book.  The concept of variance is abstract, and a rigorous
> presentation would look like pages from a math book.  In practice, variance is mostly
> relevant to library authors who want to support new generic container types or provide
> callback-based APIs.  Even then, you can avoid much complexity by supporting only
> invariant containers — which is mostly what we have in the standard library.  So, on a
> first reading, you can skip this whole section or just read the parts about invariant
> types.

We first saw the concept of variance in
[Variance in `Callable` types](type-hints-functions.md#variance-in-callable-types),
applied to parameterized generic `Callable` types.  Here we'll expand the concept to cover
generic collection types, using a "real world" analogy to make this abstract concept more
concrete.

Imagine that a school cafeteria has a rule that only juice dispensers can be installed.
General beverage dispensers are not allowed because they may serve sodas, which are
banned by the school board.

> **Tip**
>
> With the PEP 695 syntax, you never declare variance: type checkers *infer* the variance
> of each type parameter from how the class uses it.  To make the concepts visible, the
> examples below use the older explicit spelling, `TypeVar('T_co', covariant=True)`
> with `Generic[T_co]`, which is still valid and is what you'll find in typeshed and in
> most existing code.  [Variance inference](#variance-inference) explains how the new
> syntax arrives at the same answers.

### An Invariant Dispenser

Let's try to model the cafeteria scenario with a generic `BeverageDispenser` class that
can be parameterized on the type of beverage:

```python
from typing import TypeVar, Generic

class Beverage:  # Beverage, Juice and OrangeJuice form a type hierarchy
    """Any beverage."""

class Juice(Beverage):
    """Any fruit juice."""

class OrangeJuice(Juice):
    """Delicious juice from Brazilian oranges."""

T = TypeVar('T')  # simple TypeVar declaration: invariant by default

class BeverageDispenser(Generic[T]):  # parameterized on the type of beverage
    """A dispenser parameterized on the beverage type."""
    def __init__(self, beverage: T) -> None:
        self.beverage = beverage

    def dispense(self) -> T:
        return self.beverage

def install(dispenser: BeverageDispenser[Juice]) -> None:
    """Install a fruit juice dispenser."""
```

`install` is a module-global function.  Its type hint enforces the rule that only a juice
dispenser is acceptable.  Given those definitions, the following code is legal:

```python
juice_dispenser = BeverageDispenser(Juice())
install(juice_dispenser)
```

However, this is not legal:

<!-- nocheck -->
```python
beverage_dispenser = BeverageDispenser(Beverage())
install(beverage_dispenser)
## mypy: Argument 1 to "install" has
## incompatible type "BeverageDispenser[Beverage]"
##          expected "BeverageDispenser[Juice]"
```

A dispenser that serves any `Beverage` is not acceptable because the cafeteria requires a
dispenser that is specialized for `Juice`.  Somewhat surprisingly, this code is also
illegal:

<!-- nocheck -->
```python
orange_juice_dispenser = BeverageDispenser(OrangeJuice())
install(orange_juice_dispenser)
## mypy: Argument 1 to "install" has
## incompatible type "BeverageDispenser[OrangeJuice]"
##          expected "BeverageDispenser[Juice]"
```

A dispenser specialized for `OrangeJuice` is not allowed either.  Only
`BeverageDispenser[Juice]` will do.  In the typing jargon, we say that
`BeverageDispenser(Generic[T])` is *invariant* when `BeverageDispenser[OrangeJuice]` is
not compatible with `BeverageDispenser[Juice]` — despite the fact that `OrangeJuice` is a
subtype-of `Juice`.

Python mutable collection types — such as `list` and `set` — are invariant.  The
`LottoBlower` class is also invariant.

### A Covariant Dispenser

If we want to be more flexible and model dispensers as a generic class that can accept
some beverage type and also its subtypes, we must make it covariant:

```python
T_co = TypeVar('T_co', covariant=True)  # _co is the conventional suffix on typeshed

class BeverageDispenser(Generic[T_co]):
    def __init__(self, beverage: T_co) -> None:
        self._beverage = beverage

    @property
    def beverage(self) -> T_co:  # read-only: data only comes out
        return self._beverage

    def dispense(self) -> T_co:
        return self._beverage

def install(dispenser: BeverageDispenser[Juice]) -> None:  # same hints as before
    """Install a fruit juice dispenser."""
```

We set `covariant=True` when declaring the type variable, and use `T_co` to parameterize
the `Generic` special class.  Note that `beverage` is now a read-only property: a type
checker will refuse to accept a covariant type parameter in the type of a public mutable
attribute, because assigning to it would let data of the wrong type go in.

The following code works because now both the `Juice` dispenser and the `OrangeJuice`
dispenser are valid in a covariant `BeverageDispenser`:

```python
juice_dispenser = BeverageDispenser(Juice())
install(juice_dispenser)

orange_juice_dispenser = BeverageDispenser(OrangeJuice())
install(orange_juice_dispenser)
```

But a dispenser for an arbitrary `Beverage` is not acceptable:

<!-- nocheck -->
```python
beverage_dispenser = BeverageDispenser(Beverage())
install(beverage_dispenser)
## mypy: Argument 1 to "install" has
## incompatible type "BeverageDispenser[Beverage]"
##          expected "BeverageDispenser[Juice]"
```

That's covariance: the subtype relationship of the parameterized dispensers varies in the
same direction as the subtype relationship of the type parameters.

### A Contravariant Trash Can

Now we'll model the cafeteria rule for deploying a trash can.  Let's assume food and
drinks are served in biodegradable packages, and leftovers as well as single-use utensils
are also biodegradable.  The trash cans must be suitable for biodegradable refuse.  For
the sake of this didactic example, let's make simplifying assumptions to classify trash
in a neat hierarchy:

* `Refuse` is the most general type of trash.  All trash is refuse.
* `Biodegradable` is a specific type of trash that can be decomposed by organisms over
  time.  Some `Refuse` is not `Biodegradable`.
* `Compostable` is a specific type of `Biodegradable` trash that can be efficiently turned
  into organic fertilizer in a compost bin or in a composting facility.  Not all
  `Biodegradable` trash is `Compostable` in our definition.

In order to model the rule for an acceptable trash can in the cafeteria, we need to
introduce the concept of "contravariance":

```python
class Refuse:  # Refuse is the most general type, Compostable the most specific
    """Any refuse."""

class Biodegradable(Refuse):
    """Biodegradable refuse."""

class Compostable(Biodegradable):
    """Compostable refuse."""

T_contra = TypeVar('T_contra', contravariant=True)  # conventional name

class TrashCan(Generic[T_contra]):  # TrashCan is contravariant on the type of refuse
    def put(self, refuse: T_contra) -> None:
        """Store trash until dumped."""

def deploy(trash_can: TrashCan[Biodegradable]):
    """Deploy a trash can for biodegradable refuse."""
```

Given those definitions, these types of trash cans are acceptable:

```python
bio_can: TrashCan[Biodegradable] = TrashCan()
deploy(bio_can)

trash_can: TrashCan[Refuse] = TrashCan()
deploy(trash_can)
```

The more general `TrashCan[Refuse]` is acceptable because it can take any kind of refuse,
including `Biodegradable`.  However, a `TrashCan[Compostable]` will not do, because it
cannot take `Biodegradable`:

<!-- nocheck -->
```python
compost_can: TrashCan[Compostable] = TrashCan()
deploy(compost_can)
## mypy: Argument 1 to "deploy" has
## incompatible type "TrashCan[Compostable]"
##          expected "TrashCan[Biodegradable]"
```

Let's summarize the concepts we just saw.

### Variance Review

Variance is a subtle property.  The following sections recap the concepts of invariant,
covariant and contravariant types, and provide some rules of thumb to reason about them.

#### Invariant types

A generic type `L` is invariant when there is no supertype or subtype relationship
between two parameterized types, regardless of the relationship that may exist between
the actual parameters.  In other words, if `L` is invariant, then `L[A]` is not a
supertype or a subtype of `L[B]`.  They are inconsistent in both ways.

As mentioned, Python's mutable collections are invariant by default.  The `list` type is
a good example: `list[int]` is not consistent-with `list[float]` and vice versa.

In general, if a formal type parameter appears in type hints of method arguments, and the
same parameter appears in method return types, that parameter must be invariant to
ensure type safety when updating and reading from the collection.  For example, here is
part of the type hints for the `list` built-in on typeshed:

<!-- nocheck -->
```python
class list(MutableSequence[_T]):
    @overload
    def __init__(self) -> None: ...
    @overload
    def __init__(self, iterable: Iterable[_T], /) -> None: ...
    # ... lines omitted ...
    def append(self, object: _T, /) -> None: ...
    def extend(self, iterable: Iterable[_T], /) -> None: ...
    def pop(self, index: SupportsIndex = -1, /) -> _T: ...
    # etc...
```

Note that `_T` appears in the arguments of `__init__`, `append` and `extend`, and as the
return type of `pop`.  There is no way to make such a class type safe if it is covariant
or contravariant in `_T`.

#### Covariant types

Consider two types `A` and `B`, where `B` is consistent-with `A`, and neither of them is
`Any`.  Some authors use the `<:` and `:>` symbols to denote type relationships like
this:

`A :> B`
: `A` is a supertype-of or the same as `B`.

`B <: A`
: `B` is a subtype-of or the same as `A`.

Given `A :> B`, a generic type `C` is covariant when `C[A] :> C[B]`.  Note the direction of
the `:>` symbol is the same in both cases where `A` is to the left of `B`.  Covariant
generic types follow the subtype relationship of the actual type parameters.

Immutable containers can be covariant.  For example, `frozenset` is covariant, so,
applying the `:>` notation to parameterized types, we have:

```text
float :> int
frozenset[float] :> frozenset[int]
```

Iterators are another example of covariant generics: they are not read-only collections
like a `frozenset`, but they only produce output.  Any code expecting an
`abc.Iterator[float]` yielding floats can safely use an `abc.Iterator[int]` yielding
integers.  `Callable` types are covariant on the return type for a similar reason.

#### Contravariant types

Given `A :> B`, a generic type `K` is contravariant if `K[A] <: K[B]`.  Contravariant
generic types reverse the subtype relationship of the actual type parameters.  The
`TrashCan` class exemplifies this:

```text
Refuse :> Biodegradable
TrashCan[Refuse] <: TrashCan[Biodegradable]
```

A contravariant container is usually a write-only data structure, also known as a
"sink".  There are no examples of such collections in the standard library, but there are
a few types with contravariant type parameters.

`Callable[[ParamType, ...], ReturnType]` is contravariant on the parameter types, but
covariant on the `ReturnType`.  In addition, `Generator`, `Coroutine` and
`AsyncGenerator` have one contravariant type parameter: the type of the values you can
`send()` into them (see
[Iterators, Generators, and Classic Coroutines](iterators-generators.md) and
[Asynchronous Programming](asyncio.md)).

For the present discussion about variance, the main point is that the contravariant
formal parameter defines the type of the arguments used to invoke or send data to the
object, while different covariant formal parameters define the types of outputs produced
by the object — the yield type or the return type, depending on the object.  We can
derive useful guidelines from these observations of covariant outputs and contravariant
inputs.

#### Variance rules of thumb

Finally, here are a few rules of thumb to reason about when thinking through variance:

1. If a formal type parameter defines a type for data that comes out of the object, it
   can be covariant.
2. If a formal type parameter defines a type for data that goes into the object after its
   initial construction, it can be contravariant.
3. If a formal type parameter defines a type for data that comes out of the object and
   the same parameter defines a type for data that goes into the object, it must be
   invariant.
4. To err on the safe side, make formal type parameters invariant.

`Callable[[ParamType, ...], ReturnType]` demonstrates rules #1 and #2: the `ReturnType` is
covariant, and each `ParamType` is contravariant.  By default, `TypeVar` creates formal
parameters that are invariant, and that's how the mutable collections in the standard
library are annotated.

#### Variance inference

With the PEP 695 syntax, there is no way to write `covariant=True`: type checkers apply
rules much like the ones above automatically.  To infer the variance of `T` in
`class C[T]`, a checker builds two specializations of `C` — one with a supertype and one
with a subtype in place of `T` — and checks which one is assignable to the other,
member by member (ignoring `__init__` and `__new__`).  So:

* `class TrashCan[T]` with only `def put(self, refuse: T) -> None` is inferred
  contravariant;
* `class BeverageDispenser[T]` with a read-only `beverage` property and `dispense()`
  returning `T` is inferred covariant;
* the first, invariant `BeverageDispenser`, with a public mutable `beverage` attribute,
  is inferred invariant — which is correct, since anyone could assign a `Beverage` to
  the attribute of a `BeverageDispenser[Juice]`.

Inferred variance is less error-prone than declared variance, and it's one more reason to
prefer the new syntax.  If you need to declare variance explicitly for some other
reason, `TypeVar` also accepts `infer_variance=True` (Python 3.12+).

> **Note**
>
> Languages like Kotlin and C# declare variance where it makes sense: in the class
> declaration, with `out` and `in` modifiers — `class BeverageDispenser<out T>` is
> covariant, because `T` is an "output" type; `class TrashCan<in T>` is contravariant.
> Those keywords make the rules of thumb easy to recall.  PEP 484 had to put variance on
> `TypeVar`, because it was designed under the self-imposed constraint that type hints
> should not require changes to the interpreter.  PEP 695 lifted that constraint, and
> chose inference rather than new keywords.

Next, let's see how to define generic static protocols, applying the idea of covariance
to a couple of new examples.

## Implementing a Generic Static Protocol

The standard library provides a few generic static protocols.  One of them is
`SupportsAbs`, implemented like this in the `typing` module:

<!-- nocheck -->
```python
@runtime_checkable
class SupportsAbs[T](Protocol):
    """An ABC with one abstract method __abs__ that is covariant in its
        return type."""
    __slots__ = ()

    @abstractmethod
    def __abs__(self) -> T:
        pass
```

`T` appears only as a return type, so it is inferred covariant.  Thanks to
`SupportsAbs`, Mypy recognizes this code as valid:

```python
import math
from typing import NamedTuple, SupportsAbs

class Vector2d(NamedTuple):
    x: float
    y: float

    def __abs__(self) -> float:  # defining __abs__ makes Vector2d consistent-with SupportsAbs
        return math.hypot(self.x, self.y)

def is_unit(v: SupportsAbs[float]) -> bool:  # SupportsAbs[float] lets Mypy accept abs(v)...
    """'True' if the magnitude of 'v' is close to 1."""
    return math.isclose(abs(v), 1.0)  # ...as the first argument for math.isclose

assert issubclass(Vector2d, SupportsAbs)  # valid thanks to @runtime_checkable

v0 = Vector2d(0, 1)
sqrt2 = math.sqrt(2)
v1 = Vector2d(sqrt2 / 2, sqrt2 / 2)
v2 = Vector2d(1, 1)
v3 = complex(.5, math.sqrt(3) / 2)
v4 = 1  # int is also consistent-with SupportsAbs[float]

assert is_unit(v0)
assert is_unit(v1)
assert not is_unit(v2)
assert is_unit(v3)
assert is_unit(v4)

print('OK')
# OK
```

The `int` type is also consistent-with `SupportsAbs`.  According to typeshed,
`int.__abs__` returns an `int`, which is consistent-with the `float` type parameter
declared in the `is_unit` type hint for the `v` argument.

Similarly, we can write a generic version of the `RandomPicker` protocol presented in
[Designing a Static Protocol](protocols-abcs.md#designing-a-static-protocol), which was
defined with a single method `pick` returning `Any`.  Here is a generic `RandomPicker`,
covariant on the return type of `pick`:

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class RandomPicker[T](Protocol):  # T is only used as a return type: inferred covariant
    def pick(self) -> T: ...
```

The generic `RandomPicker` protocol can be covariant because its only formal parameter is
used in a return type.  (With the older syntax, you'd declare
`T_co = TypeVar('T_co', covariant=True)` and write `class RandomPicker(Protocol[T_co]):`.)

With this, we can call it a chapter.

## Summary

The chapter started with a simple example of using `@overload`, followed by a much more
complex example that we studied in detail: the overloaded signatures required to
correctly annotate the `max` built-in function.

The `typing.TypedDict` special construct came next.  It's covered here, and not with
`typing.NamedTuple`, because `TypedDict` is not a class builder; it's merely a way to add
type hints to a variable or argument that requires a `dict` with a specific set of string
keys, and specific types for each key — which happens when we use a `dict` as a record,
often in the context of handling JSON data.  That section was a bit long because using
`TypedDict` can give a false sense of security, and runtime checks and error handling are
really inevitable when trying to make statically structured records out of mappings that
are dynamic in nature.

Next we talked about `typing.cast`, a function designed to let us guide the work of the
type checker.  It's important to carefully consider when to use `cast`, because overusing
it hinders the type checker.

Runtime access to type hints came next.  The key point was to use a function such as
`annotationlib.get_annotations` or `typing.get_type_hints` instead of reading the
`__annotations__` attribute directly, and we saw how lazy annotations in Python 3.14
resolved a long-standing tension between import-time cost and runtime use of type hints.

The final sections were about generics, starting with the `LottoBlower` generic class —
which we later learned is an invariant generic class.  That example was followed by
definitions of four basic terms: generic type, formal type parameter, parameterized type
and actual type parameter.  The major topic of variance was presented next, using
cafeteria beverage dispensers and trash cans as "real life" examples of invariant,
covariant and contravariant generic types, and we saw how the PEP 695 syntax infers
variance.  Lastly, we saw how a generic static protocol is defined, first considering the
`typing.SupportsAbs` protocol, and then applying the same idea to the `RandomPicker`
example, making it more strict than the original protocol.

> **Note**
>
> Python's type system is a huge and rapidly evolving subject.  This chapter is not
> comprehensive; it focuses on topics that are either widely applicable, particularly
> challenging, or conceptually important and therefore likely to be relevant for a long
> time.  Fortunately, Python has a key advantage over Java and C++: an optional type
> system.  We can squelch type checkers and omit type hints when they become too
> cumbersome.

> **See also**
>
> * The [typing specification](https://typing.python.org/en/latest/spec/) and the
>   [typing documentation hub](https://typing.python.org/) consolidate the many typing
>   PEPs into a single reference.
> * The Mypy documentation, especially the
>   ["Generics"](https://mypy.readthedocs.io/en/stable/generics.html) and
>   ["Common issues and solutions"](https://mypy.readthedocs.io/en/stable/common_issues.html)
>   pages.
> * [**PEP 695**](https://peps.python.org/pep-0695/) — Type Parameter Syntax, including
>   the variance inference algorithm.
> * [**PEP 649**](https://peps.python.org/pep-0649/) and
>   [**PEP 749**](https://peps.python.org/pep-0749/) on deferred evaluation of
>   annotations, and the
>   [Annotations Best Practices](https://docs.python.org/3/howto/annotations.html) HOWTO.
> * *Robust Python* by Patrick Viafore (O'Reilly), a book with extensive coverage of
>   Python's static type system.
