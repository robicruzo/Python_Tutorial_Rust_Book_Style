# Functions as First-Class Objects

Functions in Python are first-class objects.  Programming language researchers
define a "first-class object" as a program entity that can be:

* created at runtime;
* assigned to a variable or element in a data structure;
* passed as an argument to a function;
* returned as the result of a function.

Integers, strings and dictionaries are other examples of first-class objects in
Python; nothing fancy there.  Having functions as first-class objects is an
essential feature of functional languages such as Clojure, Elixir and Haskell.
However, first-class functions are so useful that they've been adopted by
popular languages like JavaScript, Go and Java, none of which claim to be
"functional languages".  Guido van Rossum himself has said that he never
considered Python to be heavily influenced by functional languages; he made
functions first-class objects, but he was much more familiar with imperative
languages such as C and Algol 68.

This chapter, and the next three, explore the practical applications of treating
functions as objects.  They build on [Defining Functions](controlflow.md#tut-functions)
and [More on Defining Functions](controlflow.md#tut-defining).

> **Note**
>
> The term "first-class functions" is widely used as shorthand for "functions as
> first-class objects".  It's not ideal, because it implies an "elite" among
> functions.  In Python, all functions are first-class.

## Treating a Function Like an Object

The following session shows that Python functions are objects.  Here we create a
function, call it, read its `__doc__` attribute, and check that the function object
itself is an instance of the `function` class:

```python
def factorial(n):
    """returns n!"""
    return 1 if n < 2 else n * factorial(n - 1)

factorial(42)
# 1405006117752879898543142606244511569936384000000000
factorial.__doc__  # __doc__ is one of several attributes of function objects
# 'returns n!'
type(factorial)  # factorial is an instance of the function class
# <class 'function'>
```

At the interactive prompt, we are creating that function at "runtime".  The
`__doc__` attribute is used to generate the help text of an object: in the
interactive interpreter, `help(factorial)` displays a screen built from it (see
[Documentation Strings](controlflow.md#tut-docstrings)).

The next snippet shows the "first-class" nature of a function object.  We can
assign it to a variable `fact` and call it through that name.  We can also pass
`factorial` as an argument to the [`map()`](https://docs.python.org/3/library/functions.html#map)
function.  Calling `map(function, iterable)` returns an iterable where each item is
the result of calling the first argument (a function) on successive elements of
the second argument (an iterable), `range(11)` in this example:

```python
fact = factorial
fact
# <function factorial at 0x...>
fact(5)
# 120
map(factorial, range(11))
# <map object at 0x...>
list(map(factorial, range(11)))
# [1, 1, 2, 6, 24, 120, 720, 5040, 40320, 362880, 3628800]
```

Having first-class functions enables programming in a functional style.  One of
the hallmarks of functional programming is the use of higher-order functions.

## Higher-Order Functions

A function that takes a function as an argument or returns a function as the
result is a *higher-order function*.  One example is `map`.  Another is the
built-in function `sorted`: its optional `key` argument lets you provide a function
to be applied to each item for sorting, as you saw in
[`list.sort` Versus the `sorted` Built-In](sequences.md#listsort-versus-the-sorted-built-in).
For example, to sort a list of words by length, pass the `len` function as the key:

```python
fruits = ['strawberry', 'fig', 'apple', 'cherry', 'raspberry', 'banana']
sorted(fruits, key=len)
# ['fig', 'apple', 'cherry', 'banana', 'raspberry', 'strawberry']
```

Any one-argument function can be used as the key.  For example, to create a rhyme
dictionary it might be useful to sort each word spelled backward.  Note that the
words in the list are not changed at all; only their reversed spelling is used as
the sort criterion, so that the berries appear together:

```python
def reverse(word):
    return word[::-1]

reverse('testing')
# 'gnitset'
sorted(fruits, key=reverse)
# ['banana', 'apple', 'fig', 'raspberry', 'strawberry', 'cherry']
```

In the functional programming paradigm, some of the best-known higher-order
functions are `map`, `filter`, `reduce` and `apply`.  The `apply` function was
removed in Python 3 because it's no longer necessary: if you need to call a
function with a dynamic set of arguments, you can write `fn(*args, **kwargs)`
instead of `apply(fn, args, kwargs)`.  The `map`, `filter` and `reduce`
higher-order functions are still around, but better alternatives are available for
most of their use cases.

### Modern Replacements for `map`, `filter`, and `reduce`

Functional languages commonly offer the `map`, `filter` and `reduce` higher-order
functions (sometimes with different names).  The `map` and `filter` functions are
still built-ins in Python 3, but since the introduction of list comprehensions and
generator expressions, they are not as important.  A listcomp or a genexp does the
job of `map` and `filter` combined, and is more readable:

```python
list(map(factorial, range(6)))  # a list of factorials from 0! to 5!
# [1, 1, 2, 6, 24, 120]
[factorial(n) for n in range(6)]  # same operation, with a list comprehension
# [1, 1, 2, 6, 24, 120]
list(map(factorial, filter(lambda n: n % 2, range(6))))  # factorials of odd numbers
# [1, 6, 120]
[factorial(n) for n in range(6) if n % 2]  # no map, filter or lambda needed
# [1, 6, 120]
```

In Python 3, `map` and `filter` return iterators, so their direct substitute is
now a generator expression.  (In Python 2 they returned lists, so their closest
alternative was a listcomp.)

The `reduce` function was demoted from a built-in to the
[`functools`](https://docs.python.org/3/library/functools.html) module in Python 3.
Its most common use case, summation, is better served by the `sum` built-in.  This
is a big win in readability and performance:

```python
from functools import reduce  # reduce is no longer a built-in
from operator import add  # import add to avoid creating a function just to add two numbers
reduce(add, range(100))  # sum integers up to 99
# 4950
sum(range(100))  # same task, no need to import and call reduce and add
# 4950
```

> **Note**
>
> The common idea of `sum` and `reduce` is to apply some operation to successive
> items in a series, accumulating previous results, thus *reducing* a series of
> values to a single value.

Other reducing built-ins are `all` and `any`:

`all(iterable)`
: returns `True` if there are no falsy elements in the iterable; `all([])`
  returns `True`.

`any(iterable)`
: returns `True` if any element of the iterable is truthy; `any([])` returns
  `False`.

You'll see a meaningful use of `reduce` in
[Special Methods for Sequences](sequence-protocol.md#hashing-and-a-faster-), and the
reducing functions are summarized in
[Iterators, Generators, and Classic Coroutines](iterators-generators.md#iterable-reducing-functions).

To use a higher-order function, it is sometimes convenient to create a small,
one-off function.  That is why anonymous functions exist.

## Anonymous Functions

The `lambda` keyword creates an anonymous function within a Python expression
(see [Lambda Expressions](controlflow.md#tut-lambda)).  However, Python's simple
syntax limits the body of a `lambda` to a pure expression.  In other words, the body
cannot contain other Python statements such as `while`, `try`, etc.  Assignment
with `=` is also a statement, so it cannot occur in a `lambda`.  The assignment
expression syntax using `:=` can be used, but if you need it, your `lambda` is
probably too complicated and hard to read, and it should be refactored into a
regular function using `def`.

The best use of anonymous functions is in the argument list of a higher-order
function.  For example, here is the rhyme index example rewritten with `lambda`,
without defining a `reverse` function:

```python
fruits = ['strawberry', 'fig', 'apple', 'cherry', 'raspberry', 'banana']
sorted(fruits, key=lambda word: word[::-1])
# ['banana', 'apple', 'fig', 'raspberry', 'strawberry', 'cherry']
```

Outside the limited context of arguments to higher-order functions, anonymous
functions are rarely useful in Python.  The syntactic restrictions tend to make
nontrivial lambdas either unreadable or unworkable.  Anonymous functions also have
a drawback in any language: they have no name, which makes stack traces harder to
read.

> **Tip**
>
> If you find a piece of code hard to understand because of a `lambda`, the
> [Functional Programming HOWTO](https://docs.python.org/3/howto/functional.html)
> passes along Fredrik Lundh's refactoring procedure:
>
> 1. Write a comment explaining what the heck that lambda does.
> 2. Study the comment for a while, and think of a name that captures the essence
>    of the comment.
> 3. Convert the lambda to a `def` statement, using that name.
> 4. Remove the comment.

The `lambda` syntax is just syntactic sugar: a `lambda` expression creates a
function object just like the `def` statement.  That is just one of several kinds
of callable objects in Python.

## The Nine Flavors of Callable Objects

The call operator `()` may be applied to other objects besides functions.  To
determine whether an object is callable, use the
[`callable()`](https://docs.python.org/3/library/functions.html#callable) built-in.
The Data Model documentation lists nine callable types:

*User-defined functions*
: created with `def` statements or `lambda` expressions.

*Built-in functions*
: functions implemented in C (in CPython), like `len` or `time.strftime`.

*Built-in methods*
: methods implemented in C, like `dict.get`.

*Methods*
: functions defined in the body of a class.

*Classes*
: when invoked, a class runs its `__new__()` method to create an instance, then
  `__init__()` to initialize it, and finally the instance is returned to the
  caller.  Because there is no `new` operator in Python, calling a class is like
  calling a function.  (Usually calling a class creates an instance of that same
  class, but other behaviors are possible by overriding `__new__()`, as you'll see in
  [Flexible Object Creation with `__new__`](dynamic-attributes.md#flexible-object-creation-with-__new__).)

*Class instances*
: if a class defines a `__call__()` method, its instances may be invoked as
  functions, as the next section shows.

*Generator functions*
: functions or methods that use the `yield` keyword in their body.  When called,
  they return a generator object.

*Native coroutine functions*
: functions or methods defined with `async def`.  When called, they return a
  coroutine object.

*Asynchronous generator functions*
: functions or methods defined with `async def` that have `yield` in their body.
  When called, they return an asynchronous generator for use with `async for`.

Generators, native coroutines and asynchronous generator functions are unlike other
callables in that their return values are never application data, but objects that
require further processing to yield application data or perform useful work.
Generator functions return iterators; they are covered in
[Iterators, Generators, and Classic Coroutines](iterators-generators.md).  Native
coroutine functions and asynchronous generator functions return objects that only
work with the help of an asynchronous programming framework, such as `asyncio`;
they are the subject of [Asynchronous Programming](asyncio.md).

> **Tip**
>
> Given the variety of callable types, the safest way to determine whether an
> object is callable is to use the `callable()` built-in:
>
> ```python
> abs, str, 'Ni!'
> # (<built-in function abs>, <class 'str'>, 'Ni!')
> [callable(obj) for obj in (abs, str, 'Ni!')]
> # [True, True, False]
> ```

## User-Defined Callable Types

Not only are Python functions real objects, but arbitrary Python objects may also be
made to behave like functions.  Implementing a `__call__()` instance method is all
it takes.

The following `BingoCage` class is built from any iterable and stores an internal
list of items, in random order.  Calling the instance pops an item:

```python
import random

class BingoCage:

    def __init__(self, items):
        self._items = list(items)
        random.shuffle(self._items)

    def pick(self):
        try:
            return self._items.pop()
        except IndexError:
            raise LookupError('pick from empty BingoCage')

    def __call__(self):
        return self.pick()
```

`__init__()` accepts any iterable; building a local copy prevents unexpected side
effects on any list passed as an argument (see
[Defensive Programming with Mutable Parameters](references.md#defensive-programming-with-mutable-parameters)),
and `shuffle` is guaranteed to work because `self._items` is a list.  `pick` is the
main method; it raises an exception with a custom message if `self._items` is
empty.  `__call__()` is a shortcut, so that `bingo()` does the same as
`bingo.pick()`.  (Why build a `BingoCage` when we already have `random.choice`?
`choice` may return the same item several times, because the picked item is not
removed from the collection.  Calling a `BingoCage` never returns duplicate results,
as long as it is filled with unique values.)

Here is a simple demo.  Note how a `bingo` instance can be invoked as a function,
and the `callable()` built-in recognizes it as a callable object:

```python
bingo = BingoCage(range(3))
bingo.pick()
# 1
bingo()
# 0
callable(bingo)
# True
```

A class implementing `__call__()` is an easy way to create function-like objects
that have some internal state that must be kept across invocations, like the
remaining items in the `BingoCage`.  Another good use case for `__call__()` is
implementing decorators.  Decorators must be callable, and it is sometimes
convenient to "remember" something between calls of the decorator (for example,
for memoization, caching the results of expensive computations for later use) or
to split a complex implementation into separate methods.

The functional approach to creating functions with internal state is to use
*closures*.  Closures, as well as decorators, are the subject of
[Decorators and Closures](decorators.md).

## From Positional to Keyword-Only Parameters

One of the best features of Python functions is their extremely flexible
parameter-handling mechanism.  Closely related is the use of `*` and `**` to unpack
iterables and mappings into separate arguments when calling a function (see
[Unpacking Argument Lists](controlflow.md#tut-unpacking-arguments)).  To see these
features in action, consider this function, which generates HTML elements.  It
uses a keyword-only argument `class_` to pass "class" attributes, as a workaround
because `class` is a keyword in Python:

```python
def tag(name, *content, class_=None, **attrs):
    """Generate one or more HTML tags"""
    if class_ is not None:
        attrs['class'] = class_
    attr_pairs = (f' {attr}="{value}"' for attr, value
                    in sorted(attrs.items()))
    attr_str = ''.join(attr_pairs)
    if content:
        elements = (f'<{name}{attr_str}>{c}</{name}>'
                    for c in content)
        return '\n'.join(elements)
    else:
        return f'<{name}{attr_str} />'
```

The `tag` function can be invoked in many ways:

```python
tag('br')
# '<br />'
tag('p', 'hello')
# '<p>hello</p>'
print(tag('p', 'hello', 'world'))
# <p>hello</p>
# <p>world</p>
tag('p', 'hello', id=33)
# '<p id="33">hello</p>'
print(tag('p', 'hello', 'world', class_='sidebar'))
# <p class="sidebar">hello</p>
# <p class="sidebar">world</p>
tag(content='testing', name="img")
# '<img content="testing" />'
my_tag = {'name': 'img', 'title': 'Sunset Boulevard',
          'src': 'sunset.jpg', 'class': 'framed'}
tag(**my_tag)
# '<img class="framed" src="sunset.jpg" title="Sunset Boulevard" />'
```

Taking those calls in order:

1. A single positional argument produces an empty tag with that name.
2. Any number of arguments after the first are captured by `*content` as a tuple.
3. Keyword arguments not explicitly named in the `tag` signature are captured by
   `**attrs` as a `dict`.
4. The `class_` parameter can only be passed as a keyword argument.
5. The first positional argument can also be passed as a keyword.
6. Prefixing the `my_tag` dict with `**` passes all its items as separate
   arguments, which are then bound to the named parameters, with the remaining
   ones caught by `**attrs`.  In this case the arguments dict can have a `'class'`
   key, because it is a string, and does not clash with the `class` reserved word.

Keyword-only arguments are a feature of Python 3.  In `tag`, the `class_` parameter
can only be given as a keyword argument; it will never capture unnamed positional
arguments.  To specify keyword-only arguments when defining a function, name them
after the argument prefixed with `*`.  If you don't want to support variable
positional arguments but still want keyword-only arguments, put a `*` by itself in
the signature, like this:

```python
def f(a, *, b):
    return a, b

f(1, b=2)
# (1, 2)
f(1, 2)
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# TypeError: f() takes 1 positional argument but 2 were given
```

Note that keyword-only arguments do not need to have a default value: they can be
mandatory, like `b` in the preceding example.

### Positional-Only Parameters

User-defined function signatures may also specify *positional-only* parameters.
This feature always existed for built-in functions such as `divmod(a, b)`, which can
only be called with positional arguments, not as `divmod(a=10, b=4)`.  To define a
function requiring positional-only parameters, use `/` in the parameter list.  This
example from "What's New In Python 3.8" emulates the `divmod` built-in:

```python
def divmod(a, b, /):
    return (a // b, a % b)

divmod(10, 4)
# (2, 2)
divmod(a=10, b=4)
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# TypeError: divmod() got some positional-only arguments passed as keyword arguments: 'a, b'
del divmod  # restore the built-in
```

All arguments to the left of the `/` are positional-only.  After the `/`, you may
specify other arguments, which work as usual.  For example, to make the `name`
parameter of `tag` positional-only, add a `/` after it:

<!-- nocheck -->
```python
def tag(name, /, *content, class_=None, **attrs):
    ...
```

The tutorial section [Special parameters](controlflow.md#special-parameters)
covers the rules in detail, and [**PEP 570**](https://peps.python.org/pep-0570/)
gives the rationale.

### Introspection of Function Parameters

Function objects have several attributes beyond `__doc__`.  Some of them store
information about the parameters, and frameworks use them to call your functions
with the right arguments.  For example, `__defaults__` holds a tuple with the default
values of positional parameters, `__kwdefaults__` holds the defaults of keyword-only
parameters, and `__code__` refers to a code object with details such as the names of
the parameters and local variables:

```python
tag.__defaults__
tag.__kwdefaults__
# {'class_': None}
tag.__code__.co_varnames[:tag.__code__.co_argcount]
# ('name',)
```

(`tag.__defaults__` is `None`, so the interactive interpreter displays nothing.)
Those low-level attributes are awkward to use.  The
[`inspect`](https://docs.python.org/3/library/inspect.html) module provides a much
better interface, `inspect.signature()`, which returns a `Signature` object with an
ordered mapping of `Parameter` objects:

```python
import inspect
sig = inspect.signature(tag)
str(sig)
# '(name, *content, class_=None, **attrs)'
for name, param in sig.parameters.items():
    print(param.kind, ':', name, '=', param.default)
# POSITIONAL_OR_KEYWORD : name = <class 'inspect._empty'>
# VAR_POSITIONAL : content = <class 'inspect._empty'>
# KEYWORD_ONLY : class_ = None
# VAR_KEYWORD : attrs = <class 'inspect._empty'>
```

`inspect._empty` denotes parameters with no default.  The kind of each parameter is
one of `POSITIONAL_OR_KEYWORD`, `VAR_POSITIONAL` (`*args`), `VAR_KEYWORD`
(`**kwargs`), `KEYWORD_ONLY` and `POSITIONAL_ONLY`.  A `Signature` also has a `bind`
method that takes any number of arguments and binds them to the parameters,
applying the same rules Python uses when calling a function.  A framework can use it
to validate arguments before the actual call:

```python
my_tag = {'name': 'img', 'title': 'Sunset Boulevard',
          'src': 'sunset.jpg', 'class': 'framed'}
bound_args = sig.bind(**my_tag)
bound_args
# <BoundArguments (name='img', attrs={'title': 'Sunset Boulevard', 'src': 'sunset.jpg', 'class': 'framed'})>
for name, value in bound_args.arguments.items():
    print(name, '=', value)
# name = img
# attrs = {'title': 'Sunset Boulevard', 'src': 'sunset.jpg', 'class': 'framed'}
del my_tag['name']
bound_args = sig.bind(**my_tag)
# Traceback (most recent call last):
#   ...
# TypeError: missing a required argument: 'name'
```

This is how frameworks and IDEs can validate code before running it.  Function
annotations, which are also accessible through `Signature` and `Parameter` objects,
are covered in [Type Hints in Functions](type-hints-functions.md) and
[Reading Type Hints at Runtime](type-hints-more.md#reading-type-hints-at-runtime).

## Packages for Functional Programming

Although Guido made it clear that he did not design Python to be a functional
programming language, a functional coding style can be used to good extent,
thanks to first-class functions, pattern matching, and the support of packages like
`operator` and `functools`.

### The `operator` Module

In functional programming it is often convenient to use an arithmetic operator as
a function.  For example, suppose you want to multiply a sequence of numbers to
calculate factorials without using recursion.  To perform summation you can use
`sum`, but there is no equivalent function for multiplication.  (Actually, since
Python 3.8 there is [`math.prod()`](https://docs.python.org/3/library/math.html#math.prod),
but let's pretend there isn't.)  You could use `reduce`, but it requires a function
to multiply two items of the sequence.  Here is how to solve this using `lambda`:

```python
from functools import reduce

def factorial(n):
    return reduce(lambda a, b: a*b, range(1, n+1))
```

The [`operator`](https://docs.python.org/3/library/operator.html) module provides
function equivalents for dozens of operators, so you don't have to write trivial
functions like `lambda a, b: a*b`.  With it, we can rewrite `factorial` as:

```python
from functools import reduce
from operator import mul

def factorial(n):
    return reduce(mul, range(1, n+1))

factorial(5)
# 120
```

Another group of one-trick lambdas that `operator` replaces are functions to pick
items from sequences or read attributes from objects: `itemgetter` and `attrgetter`
are factories that build custom functions to do that.

A common use of `itemgetter` is sorting a list of tuples by the value of one field.
Here the cities are printed sorted by country code (field 1).  Essentially,
`itemgetter(1)` creates a function that, given a collection, returns the item at
index 1.  That's easier to write and read than `lambda fields: fields[1]`, which does
the same thing:

```python
metro_data = [
    ('Tokyo', 'JP', 36.933, (35.689722, 139.691667)),
    ('Delhi NCR', 'IN', 21.935, (28.613889, 77.208889)),
    ('Mexico City', 'MX', 20.142, (19.433333, -99.133333)),
    ('New York-Newark', 'US', 20.104, (40.808611, -74.020386)),
    ('São Paulo', 'BR', 19.649, (-23.547778, -46.635833)),
]

from operator import itemgetter
for city in sorted(metro_data, key=itemgetter(1)):
    print(city)
# ('São Paulo', 'BR', 19.649, (-23.547778, -46.635833))
# ('Delhi NCR', 'IN', 21.935, (28.613889, 77.208889))
# ('Tokyo', 'JP', 36.933, (35.689722, 139.691667))
# ('Mexico City', 'MX', 20.142, (19.433333, -99.133333))
# ('New York-Newark', 'US', 20.104, (40.808611, -74.020386))
```

If you pass several index arguments to `itemgetter`, the function it builds returns
tuples with the extracted values, which is useful for sorting on multiple keys:

```python
cc_name = itemgetter(1, 0)
for city in metro_data:
    print(cc_name(city))
# ('JP', 'Tokyo')
# ('IN', 'Delhi NCR')
# ('MX', 'Mexico City')
# ('US', 'New York-Newark')
# ('BR', 'São Paulo')
```

Because `itemgetter` uses the `[]` operator, it supports not only sequences but also
mappings and any class that implements `__getitem__()`.

A sibling of `itemgetter` is `attrgetter`, which creates functions to extract object
attributes by name.  If you pass `attrgetter` several attribute names as arguments,
it also returns a tuple of values.  In addition, if any argument name contains a `.`
(dot), `attrgetter` navigates through nested objects to retrieve the attribute.  To
show that, we need a nested structure:

```python
from collections import namedtuple
LatLon = namedtuple('LatLon', 'lat lon')
Metropolis = namedtuple('Metropolis', 'name cc pop coord')
metro_areas = [Metropolis(name, cc, pop, LatLon(lat, lon))
    for name, cc, pop, (lat, lon) in metro_data]
metro_areas[0]
# Metropolis(name='Tokyo', cc='JP', pop=36.933, coord=LatLon(lat=35.689722,
# lon=139.691667))
metro_areas[0].coord.lat
# 35.689722
from operator import attrgetter
name_lat = attrgetter('name', 'coord.lat')

for city in sorted(metro_areas, key=attrgetter('coord.lat')):
    print(name_lat(city))
# ('São Paulo', -23.547778)
# ('Mexico City', 19.433333)
# ('Delhi NCR', 28.613889)
# ('Tokyo', 35.689722)
# ('New York-Newark', 40.808611)
```

We use `namedtuple` to define `LatLon` and `Metropolis`, then build the
`metro_areas` list with `Metropolis` instances; note the nested tuple unpacking to
extract `(lat, lon)` and use them to build the `LatLon` for the `coord` attribute.
`name_lat` is an `attrgetter` that retrieves the `name` and the nested `coord.lat`
attribute; another `attrgetter` sorts the list of cities by latitude.

Here is the list of public functions defined in `operator` in Python 3.13 (later
versions add a few more, such as `is_none`):

```python
import operator
[name for name in dir(operator) if not name.startswith('_')]
# ['abs', 'add', 'and_', 'attrgetter', 'call', 'concat', 'contains',
#  'countOf', 'delitem', 'eq', 'floordiv', 'ge', 'getitem', 'gt',
#  'iadd', 'iand', 'iconcat', 'ifloordiv', 'ilshift', 'imatmul',
#  'imod', 'imul', 'index', 'indexOf', 'inv', 'invert', 'ior',
#  'ipow', 'irshift', 'is_', 'is_not', 'isub', 'itemgetter',
#  'itruediv', 'ixor', 'le', 'length_hint', 'lshift', 'lt', 'matmul',
#  'methodcaller', 'mod', 'mul', 'ne', 'neg', 'not_', 'or_', 'pos',
#  'pow', 'rshift', 'setitem', 'sub', 'truediv', 'truth', 'xor']
```

Most of the names are self-evident.  The group of names prefixed with `i` and the
name of another operator, like `iadd` and `iand`, correspond to the augmented
assignment operators, like `+=` and `&=`.  These change their first argument in
place, if it is mutable; if not, the function works like the one without the `i`
prefix: it simply returns the result of the operation.

Of the remaining `operator` functions, `methodcaller` is the last we will cover.  It
is somewhat similar to `attrgetter` and `itemgetter` in that it creates a function on
the fly.  The function it creates calls a method by name on the object given as
argument:

```python
from operator import methodcaller
s = 'The time has come'
upcase = methodcaller('upper')
upcase(s)
# 'THE TIME HAS COME'
hyphenate = methodcaller('replace', ' ', '-')
hyphenate(s)
# 'The-time-has-come'
```

The first test is there just to show `methodcaller` at work, but if you need to use
`str.upper` as a function, you can just call it on the `str` class and pass a string
as an argument:

```python
str.upper(s)
# 'THE TIME HAS COME'
```

The second test shows that `methodcaller` can also do a *partial application* to
freeze some arguments, like the `functools.partial` function does.

### Freezing Arguments with `functools.partial`

The `functools` module provides several higher-order functions.  You saw `reduce`
above.  Another is [`partial`](https://docs.python.org/3/library/functools.html#functools.partial):
given a callable, it produces a new callable with some of the arguments of the
original callable bound to predetermined values.  This is useful to adapt a
function that takes one or more arguments to an interface that requires a callback
with fewer arguments.  A trivial demonstration:

```python
from operator import mul
from functools import partial
triple = partial(mul, 3)  # a new triple function from mul, binding the first argument to 3
triple(7)
# 21
list(map(triple, range(1, 10)))  # mul would not work with map in this example
# [3, 6, 9, 12, 15, 18, 21, 24, 27]
```

A more useful example involves the `unicodedata.normalize` function from
[Normalizing Unicode for Reliable Comparisons](unicode.md#normalizing-unicode-for-reliable-comparisons).
If you work with text from many languages, you may want to apply
`unicodedata.normalize('NFC', s)` to any string `s` before comparing or storing it.
If you do that often, it's handy to have an `nfc` function:

```python
import unicodedata, functools
nfc = functools.partial(unicodedata.normalize, 'NFC')
s1 = 'café'
s2 = 'cafe\u0301'
s1, s2
# ('café', 'café')
s1 == s2
# False
nfc(s1) == nfc(s2)
# True
```

`partial` takes a callable as its first argument, followed by an arbitrary number
of positional and keyword arguments to bind.  Here it is with the `tag` function,
freezing one positional argument and one keyword argument:

```python
from functools import partial
picture = partial(tag, 'img', class_='pic-frame')
picture(src='wumpus.jpeg')
# '<img class="pic-frame" src="wumpus.jpeg" />'
picture
# functools.partial(<function tag at 0x10206d1e0>, 'img', class_='pic-frame')
picture.func
# <function tag at 0x10206d1e0>
picture.args
# ('img',)
picture.keywords
# {'class_': 'pic-frame'}
```

We create the `picture` function from `tag` by fixing the first positional argument
with `'img'` and the `class_` keyword argument with `'pic-frame'`, and `picture`
works as expected.  `partial()` returns a `functools.partial` object, which has
attributes providing access to the original function and the fixed arguments.

The [`functools.partialmethod`](https://docs.python.org/3/library/functools.html#functools.partialmethod)
function does the same job as `partial`, but is designed to work with methods.

The `functools` module also includes higher-order functions designed to be used as
function decorators, such as `cache` and `singledispatch`.  Those are covered in
[Decorators and Closures](decorators.md), which also explains how to implement
custom decorators.

## Summary

This chapter explored the first-class nature of functions in Python.  The main
ideas are that you can assign functions to variables, pass them to other functions,
store them in data structures, and access function attributes, allowing frameworks
and tools to act on that information.

Higher-order functions, a staple of functional programming, are common in Python.
The `sorted`, `min` and `max` built-ins and `functools.partial` are examples of
commonly used higher-order functions.  Using `map`, `filter` and `reduce` is not as
common as it used to be, thanks to list comprehensions (and similar constructs like
generator expressions) and the addition of reducing built-ins like `sum`, `all` and
`any`.

Callables come in nine different flavors, from the simple functions created with
`lambda` to instances of classes implementing `__call__()`.  Generators and
coroutines are also callable, although their behavior is very different from other
callables.  All callables can be detected by the `callable()` built-in.  Callables
offer rich syntax for declaring formal parameters, including keyword-only
parameters, positional-only parameters, and annotations, and `inspect.signature()`
lets you introspect them.

Lastly, we covered some functions from the `operator` module and
`functools.partial`, which facilitate functional programming by minimizing the need
for the functionally challenged `lambda` syntax.

> **See also**
>
> * [The standard type hierarchy](https://docs.python.org/3/reference/datamodel.html#the-standard-type-hierarchy)
>   in the language reference presents the nine callable types, along with all the
>   other built-in types.
> * A. M. Kuchling's [Functional Programming HOWTO](https://docs.python.org/3/howto/functional.html)
>   is a great introduction to functional programming in Python, with a focus on
>   iterators and generators.
> * [**PEP 3102**](https://peps.python.org/pep-3102/) explains the rationale and use
>   cases for keyword-only arguments.
> * Chapter 7 of the *Python Cookbook*, 3rd ed., by David Beazley and Brian K. Jones,
>   covers much of the same ground with a different approach.
> * Is Python a functional language?  Not by design.  Python borrows a few good ideas
>   from functional languages: first-class functions, `map`, `filter` and `reduce`
>   (which motivated the addition of `lambda`), and list comprehensions, borrowed
>   from Haskell, which in turn reduced the need for `map`, `filter` and `lambda`.
>   Python's statement-oriented syntax limits `lambda`, and the language deliberately
>   lacks tail-call elimination; Guido's blog post "Tail Recursion Elimination"
>   explains why, with usability arguments first.
