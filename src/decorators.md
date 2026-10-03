# Decorators and Closures

Function decorators let us "mark" functions in the source code to enhance their
behavior in some way.  This is powerful stuff, but mastering it requires
understanding *closures*, which is what we get when functions capture variables
defined outside of their bodies.  (The name "decorator" has drawn complaints for
not matching the Decorator pattern of the *Design Patterns* book;
[**PEP 318**](https://peps.python.org/pep-0318/) suggests that it owes more to its
use in compilers, where a syntax tree is walked and annotated.)

The most obscure reserved keyword in Python is `nonlocal`.  You can have a
profitable life as a Python programmer without ever using it if you adhere to a
strict regimen of class-centered object orientation.  However, if you want to
implement your own function decorators, you must understand closures, and then the
need for `nonlocal` becomes obvious.  Aside from their application in decorators,
closures are also essential for any type of programming using callbacks, and for
coding in a functional style when it makes sense.

The goal of this chapter is to explain exactly how function decorators work, from
the simplest registration decorators to the rather more complicated parameterized
ones.  Before we reach that goal, we need to cover:

* how Python evaluates decorator syntax;
* how Python decides whether a variable is local;
* why closures exist and how they work;
* what problem is solved by `nonlocal`.

With this grounding, we can tackle further topics:

* implementing a well-behaved decorator;
* powerful decorators in the standard library: `@cache`, `@lru_cache` and
  `@singledispatch`;
* implementing a parameterized decorator.

The scope rules discussed here complement
[Python Scopes and Namespaces](classes.md#tut-scopes) in the Classes chapter.

## Decorators 101

A decorator is a callable that takes another function as an argument (the
decorated function).  A decorator may perform some processing with the decorated
function, and returns it or replaces it with another function or callable object.
(Replace "function" with "class" in the previous sentences and you have a brief
description of what a class decorator does; class decorators are covered in
[Class Metaprogramming](class-metaprogramming.md).)

In other words, assuming an existing decorator named `decorate`, this code:

<!-- nocheck -->
```python
@decorate
def target():
    print('running target()')
```

has the same effect as writing this:

<!-- nocheck -->
```python
def target():
    print('running target()')

target = decorate(target)
```

The end result is the same: at the end of either of these snippets, the `target`
name is bound to whatever function is returned by `decorate(target)`, which may be
the function initially named `target`, or may be a different function.  To confirm
that the decorated function is replaced:

```python
def deco(func):
    def inner():
        print('running inner()')
    return inner  # deco returns its inner function object

@deco
def target():  # target is decorated by deco
    print('running target()')

target()  # invoking the decorated target actually runs inner
# running inner()
target  # target is now a reference to inner
# <function deco.<locals>.inner at 0x10063b598>
```

Strictly speaking, decorators are just syntactic sugar.  As we just saw, you can
always simply call a decorator like any regular callable, passing another function.
Sometimes that is actually convenient, especially when doing *metaprogramming*:
changing program behavior at runtime.

Three essential facts make a good summary of decorators:

* A decorator is a function or another callable.
* A decorator may replace the decorated function with a different one.
* Decorators are executed immediately when a module is loaded.

Now let's focus on the third point.

## When Python Executes Decorators

A key feature of decorators is that they run right after the decorated function is
defined.  That is usually at *import time*, that is, when a module is loaded by
Python.  Consider this `registration.py` module:

```python
registry = []

def register(func):
    print(f'running register({func})')
    registry.append(func)
    return func

@register
def f1():
    print('running f1()')

@register
def f2():
    print('running f2()')

def f3():
    print('running f3()')

def main():
    print('running main()')
    print('registry ->', registry)
    f1()
    f2()
    f3()

if __name__ == '__main__':
    main()
```

`registry` will hold references to functions decorated by `@register`.  `register`
takes a function as an argument, displays what function is being decorated, for
demonstration, includes it in `registry`, and returns it: a decorator must return a
function, and here we return the same one received as the argument.  `f1` and `f2`
are decorated by `@register`; `f3` is not.  `main` displays the registry, then calls
`f1()`, `f2()` and `f3()`, and it is only invoked if `registration.py` runs as a
script.  The output of running it as a script looks like this:

```console
$ python3 registration.py
running register(<function f1 at 0x100631bf8>)
running register(<function f2 at 0x100631c80>)
running main()
registry -> [<function f1 at 0x100631bf8>, <function f2 at 0x100631c80>]
running f1()
running f2()
running f3()
```

Note that `register` runs (twice) before any other function in the module.  When
`register` is called, it receives the decorated function object as an argument, for
example `<function f1 at 0x100631bf8>`.  After the module is loaded, the `registry`
list holds references to the two decorated functions, `f1` and `f2`.  These
functions, as well as `f3`, are only executed when explicitly called by `main`.

If `registration.py` is imported (and not run as a script), the output is this:

<!-- nocheck -->
```python
import registration
# running register(<function f1 at 0x10063b1e0>)
# running register(<function f2 at 0x10063b268>)
registration.registry
# [<function f1 at 0x10063b1e0>, <function f2 at 0x10063b268>]
```

The main point is that function decorators are executed as soon as the module is
imported, but the decorated functions only run when they are explicitly invoked.
This highlights the difference between what Pythonistas call *import time* and
*runtime*.

### Registration Decorators

Considering how decorators are commonly employed in real code, `registration.py` is
unusual in two ways:

* The decorator function is defined in the same module as the decorated
  functions.  A real decorator is usually defined in one module and applied to
  functions in other modules.
* The `register` decorator returns the same function passed as an argument.  In
  practice, most decorators define an inner function and return it.

Even though `register` returns the decorated function unchanged, that technique is
not useless.  Similar decorators are used in many Python frameworks to add functions
to some central registry, for example a registry mapping URL patterns to functions
that generate HTTP responses.  Such registration decorators may or may not change the
decorated function.  You'll see a registration decorator applied in
[Decorator-Enhanced Strategy Pattern](function-patterns.md#decorator-enhanced-strategy-pattern).

Most decorators do change the decorated function.  They usually do it by defining
an inner function and returning it to replace the decorated function.  Code that uses
inner functions almost always depends on closures to operate correctly.  To
understand closures, we need to take a step back and review how variable scopes work
in Python.

## Variable Scope Rules

Here we define and test a function that reads two variables: a local variable `a`,
defined as a function parameter, and a variable `b` that is not defined anywhere in
the function:

```python
def f1(a):
    print(a)
    print(b)

f1(3)
# 3
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
#   File "<stdin>", line 3, in f1
# NameError: name 'b' is not defined
```

The error is not surprising.  If we assign a value to a global `b` and then call
`f1`, it works:

```python
b = 6
f1(3)
# 3
# 6
```

Now let's see an example that may surprise you.  The `f2` function below starts with
the same two lines as `f1`, then makes an assignment to `b`.  But it fails at the
second `print`, before the assignment is made:

```python
b = 6
def f2(a):
    print(a)
    print(b)
    b = 9

f2(3)
# 3
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
#   File "<stdin>", line 3, in f2
# UnboundLocalError: cannot access local variable 'b' where it is not associated with a value
```

The output starts with `3`, which proves that the `print(a)` statement was executed.
But the second one, `print(b)`, never runs.  You might expect `6` to be printed,
because there is a global variable `b` and the assignment to the local `b` is made
after `print(b)`.

But the fact is, when Python compiles the body of the function, it decides that `b`
is a local variable because it is assigned within the function.  The generated
bytecode reflects this decision and will try to fetch `b` from the local scope.
Later, when the call `f2(3)` is made, the body of `f2` fetches and prints the value
of the local variable `a`, but when trying to fetch the value of local variable `b`,
it discovers that `b` is unbound.

This is not a bug, but a design choice: Python does not require you to declare
variables, but assumes that a variable assigned in the body of a function is local.
This is much better than the behavior of JavaScript, which does not require variable
declarations either, but if you forget to declare that a variable is local (with
`var`), you may clobber a global variable without knowing it.

If we want the interpreter to treat `b` as a global variable and still assign a new
value to it within the function, we use the `global` declaration:

```python
b = 6
def f3(a):
    global b
    print(a)
    print(b)
    b = 9

f3(3)
# 3
# 6
b
# 9
```

In the preceding examples, we can see two scopes in action:

*The module global scope*
: made of names assigned to values outside of any class or function block.

*The `f3` function local scope*
: made of names assigned to values as parameters, or directly in the body of the
  function.

There is one other scope where variables can come from, which we call *nonlocal*,
and it is fundamental for closures; we'll see it in a bit.

### Comparing Bytecodes

The [`dis`](https://docs.python.org/3/library/dis.html) module provides an easy way to
disassemble the bytecode of Python functions.  Here are the bytecodes for `f1` and
`f2`, as produced by Python 3.13 (the details vary between versions, but the key
instructions are the same):

<!-- nocheck -->
```python
from dis import dis
dis(f1)
#   1           RESUME                   0
#
#   2           LOAD_GLOBAL              1 (print + NULL)
#               LOAD_FAST                0 (a)
#               CALL                     1
#               POP_TOP
#
#   3           LOAD_GLOBAL              1 (print + NULL)
#               LOAD_GLOBAL              2 (b)
#               CALL                     1
#               POP_TOP
#               RETURN_CONST             0 (None)
```

In `f1`, `print` is loaded with `LOAD_GLOBAL`, the local name `a` with
`LOAD_FAST`, and the global name `b` with `LOAD_GLOBAL`.  Contrast that with `f2`:

<!-- nocheck -->
```python
dis(f2)
#   1           RESUME                   0
#
#   2           LOAD_GLOBAL              1 (print + NULL)
#               LOAD_FAST                0 (a)
#               CALL                     1
#               POP_TOP
#
#   3           LOAD_GLOBAL              1 (print + NULL)
#               LOAD_FAST_CHECK          1 (b)
#               CALL                     1
#               POP_TOP
#
#   4           LOAD_CONST               1 (9)
#               STORE_FAST               1 (b)
#               RETURN_CONST             0 (None)
```

Here `b` is loaded as a *local* name (`LOAD_FAST_CHECK`).  This shows that the
compiler considers `b` a local variable, even though the assignment to `b` occurs
later, because the nature of a variable (whether it is local or not) cannot change
within the body of a function.  The CPython virtual machine that runs the bytecode is
a stack machine, so the `LOAD` and `POP` operations refer to the stack; the opcodes are
documented with the `dis` module.

## Closures

Closures are sometimes confused with anonymous functions.  Many people confuse them
because of the parallel history of those features: defining functions inside
functions is not so common or convenient until you have anonymous functions, and
closures only matter when you have nested functions.  So many people learn both
concepts at the same time.

Actually, a *closure* is a function, let's call it `f`, with an extended scope that
encompasses variables referenced in the body of `f` that are not global variables or
local variables of `f`.  Such variables must come from the local scope of an outer
function that encompasses `f`.  It does not matter whether the function is anonymous
or not; what matters is that it can access nonglobal variables that are defined
outside of its body.

This is a challenging concept to grasp, and is better approached through an example.
Consider an `avg` function to compute the mean of an ever-growing series of values;
for example, the average closing price of a commodity over its entire history.  Every
day a new price is added, and the average is computed taking into account all prices
so far.  Starting with a clean slate, this is how `avg` could be used:

<!-- nocheck -->
```python
avg(10)
# 10.0
avg(11)
# 10.5
avg(12)
# 11.0
```

Where does `avg` come from, and where does it keep the history of previous values?
For starters, here is a class-based implementation:

```python
class Averager():

    def __init__(self):
        self.series = []

    def __call__(self, new_value):
        self.series.append(new_value)
        total = sum(self.series)
        return total / len(self.series)
```

The `Averager` class creates instances that are callable:

```python
avg = Averager()
avg(10)
# 10.0
avg(11)
# 10.5
avg(12)
# 11.0
```

Now here is a functional implementation, using the higher-order function
`make_averager`:

```python
def make_averager():
    series = []

    def averager(new_value):
        series.append(new_value)
        total = sum(series)
        return total / len(series)

    return averager
```

When invoked, `make_averager` returns an `averager` function object.  Each time an
`averager` is called, it appends the passed argument to the series, and computes the
current average:

```python
avg = make_averager()
avg(10)
# 10.0
avg(11)
# 10.5
avg(15)
# 12.0
```

Note the similarities of the examples: we call `Averager()` or `make_averager()` to
get a callable object `avg` that will update the historical series and calculate the
current mean.  In the class version, `avg` is an instance of `Averager`; in the
functional version, it is the inner function, `averager`.  Either way, we just call
`avg(n)` to include `n` in the series and get the updated mean.

It's obvious where the `avg` of the `Averager` class keeps the history: the
`self.series` instance attribute.  But where does the `avg` function in the second
example find the `series`?

Note that `series` is a local variable of `make_averager`, because the assignment
`series = []` happens in the body of that function.  But when `avg(10)` is called,
`make_averager` has already returned, and its local scope is long gone.

Within `averager`, `series` is a *free variable*.  This is a technical term meaning a
variable that is not bound in the local scope.  The closure for `averager` extends
the scope of that function to include the binding for the free variable `series`.

Inspecting the returned `averager` object shows how Python keeps the names of local
and free variables in the `__code__` attribute that represents the compiled body of
the function:

```python
avg.__code__.co_varnames
# ('new_value', 'total')
avg.__code__.co_freevars
# ('series',)
```

The value for `series` is kept in the `__closure__` attribute of the returned
function `avg`.  Each item in `avg.__closure__` corresponds to a name in
`avg.__code__.co_freevars`.  These items are *cells*, and they have an attribute
called `cell_contents` where the actual value can be found:

```python
avg.__code__.co_freevars
# ('series',)
avg.__closure__
# (<cell at 0x107a44f78: list object at 0x107a91a48>,)
avg.__closure__[0].cell_contents
# [10, 11, 15]
```

To summarize: a closure is a function that retains the bindings of the free
variables that exist when the function is defined, so that they can be used later
when the function is invoked and the defining scope is no longer available.

Note that the only situation in which a function may need to deal with external
variables that are nonglobal is when it is nested in another function and those
variables are part of the local scope of the outer function.

## The `nonlocal` Declaration

Our previous implementation of `make_averager` was not efficient: it stored all the
values in the historical series and computed their `sum` every time `averager` was
called.  A better implementation would only store the total and the number of items
so far, and compute the mean from these two numbers.  Here is a broken
implementation, just to make a point.  Can you see where it breaks?

```python
def make_averager():
    count = 0
    total = 0

    def averager(new_value):
        count += 1
        total += new_value
        return total / count

    return averager

avg = make_averager()
avg(10)
# Traceback (most recent call last):
#   ...
# UnboundLocalError: cannot access local variable 'count' where it is not associated with a value
```

The problem is that the statement `count += 1` actually means the same as
`count = count + 1`, when `count` is a number or any immutable type.  So we are
actually assigning to `count` in the body of `averager`, and that makes it a local
variable.  The same problem affects the `total` variable.

We did not have this problem in the previous version, because we never assigned to
the `series` name; we only called `series.append` and invoked `sum` and `len` on it.
So we took advantage of the fact that lists are mutable.  But with immutable types
like numbers, strings, tuples, etc., all you can do is read, never update.  If you try
to rebind them, as in `count = count + 1`, then you are implicitly creating a local
variable `count`.  It is no longer a free variable, and therefore it is not saved in
the closure.

To work around this, the `nonlocal` keyword was introduced in Python 3.  It lets you
declare a variable as a free variable even when it is assigned within the function.
If a new value is assigned to a `nonlocal` variable, the binding stored in the closure
is changed.  A correct implementation of our newest `make_averager` looks like this:

```python
def make_averager():
    count = 0
    total = 0

    def averager(new_value):
        nonlocal count, total
        count += 1
        total += new_value
        return total / count

    return averager

avg = make_averager()
avg(10)
# 10.0
avg(11)
# 10.5
avg(12)
# 11.0
```

### Variable Lookup Logic

When a function is defined, the Python bytecode compiler determines how to fetch a
variable `x` that appears in it, based on these rules:

* If there is a `global x` declaration, `x` comes from and is assigned to the `x`
  global variable of the module.  (Python has no program-wide global scope, only
  module global scopes.)
* If there is a `nonlocal x` declaration, `x` comes from and is assigned to the `x`
  local variable of the nearest surrounding function where `x` is defined.
* If `x` is a parameter or is assigned a value in the function body, then `x` is a
  local variable.
* If `x` is referenced but is not assigned and is not a parameter:
  * `x` will be looked up in the local scopes of the surrounding function bodies
    (nonlocal scopes);
  * if not found in surrounding scopes, it will be read from the module global
    scope;
  * if not found in the global scope, it will be read from
    `__builtins__.__dict__`.

Now that we have Python closures covered, we can effectively implement decorators
with nested functions.

## Implementing a Simple Decorator

Here is a decorator that clocks every invocation of the decorated function and
displays the elapsed time, the arguments passed, and the result of the call:

```python
import time

def clock(func):
    def clocked(*args):
        t0 = time.perf_counter()
        result = func(*args)
        elapsed = time.perf_counter() - t0
        name = func.__name__
        arg_str = ', '.join(repr(arg) for arg in args)
        print(f'[{elapsed:0.8f}s] {name}({arg_str}) -> {result!r}')
        return result
    return clocked
```

We define the inner function `clocked` to accept any number of positional
arguments.  The line `result = func(*args)` only works because the closure for
`clocked` encompasses the `func` free variable.  Finally, `clock` returns the inner
function to replace the decorated function.  Here is the decorator in use:

<!-- nocheck -->
```python
import time
from clockdeco0 import clock

@clock
def snooze(seconds):
    time.sleep(seconds)

@clock
def factorial(n):
    return 1 if n < 2 else n*factorial(n-1)

if __name__ == '__main__':
    print('*' * 40, 'Calling snooze(.123)')
    snooze(.123)
    print('*' * 40, 'Calling factorial(6)')
    print('6! =', factorial(6))
```

The output of running that script looks like this:

```console
$ python3 clockdeco_demo.py
**************************************** Calling snooze(.123)
[0.12363791s] snooze(0.123) -> None
**************************************** Calling factorial(6)
[0.00000095s] factorial(1) -> 1
[0.00002408s] factorial(2) -> 2
[0.00003934s] factorial(3) -> 6
[0.00005221s] factorial(4) -> 24
[0.00006390s] factorial(5) -> 120
[0.00008297s] factorial(6) -> 720
6! = 720
```

### How It Works

Remember that this code:

<!-- nocheck -->
```python
@clock
def factorial(n):
    return 1 if n < 2 else n*factorial(n-1)
```

actually does this:

<!-- nocheck -->
```python
def factorial(n):
    return 1 if n < 2 else n*factorial(n-1)

factorial = clock(factorial)
```

So, in both cases, `clock` gets the `factorial` function as its `func` argument.  It
then creates and returns the `clocked` function, which the interpreter assigns to
`factorial` (behind the scenes, in the first case).  In fact, if you import the
`clockdeco_demo` module and check the `__name__` of `factorial`, this is what you get:

<!-- nocheck -->
```python
import clockdeco_demo
clockdeco_demo.factorial.__name__
# 'clocked'
```

So `factorial` now actually holds a reference to the `clocked` function.  From now on,
each time `factorial(n)` is called, `clocked(n)` gets executed.  In essence, `clocked`
does the following:

1. records the initial time `t0`;
2. calls the original `factorial` function, saving the result;
3. computes the elapsed time;
4. formats and displays the collected data;
5. returns the result saved in step 2.

This is the typical behavior of a decorator: it replaces the decorated function with
a new function that accepts the same arguments and (usually) returns whatever the
decorated function was supposed to return, while also doing some extra processing.

> **Tip**
>
> In *Design Patterns* by Gamma et al., the short description of the Decorator
> pattern starts with: "Attach additional responsibilities to an object
> dynamically."  Function decorators fit that description.  But at the
> implementation level, Python decorators bear little resemblance to the classic
> Decorator described there.  In the pattern, an instance of a concrete decorator
> wraps an instance of a concrete component, conforming to its interface so that its
> presence is transparent to clients.  In Python, the decorator function plays the
> role of a concrete Decorator subclass, and the inner function it returns is a
> decorator instance: it wraps the decorated function (the component), accepts the
> same arguments, forwards calls, and may do extra work before or after.
> Transparency lets you stack decorators.  But in general, the Decorator pattern
> itself is best implemented with classes.

The `clock` decorator has a few shortcomings: it does not support keyword arguments,
and it masks the `__name__` and `__doc__` of the decorated function.  This version
uses the [`functools.wraps`](https://docs.python.org/3/library/functools.html#functools.wraps)
decorator to copy the relevant attributes from `func` to `clocked`, and handles
keyword arguments correctly:

```python
import time
import functools

def clock(func):
    @functools.wraps(func)
    def clocked(*args, **kwargs):
        t0 = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - t0
        name = func.__name__
        arg_lst = [repr(arg) for arg in args]
        arg_lst.extend(f'{k}={v!r}' for k, v in kwargs.items())
        arg_str = ', '.join(arg_lst)
        print(f'[{elapsed:0.8f}s] {name}({arg_str}) -> {result!r}')
        return result
    return clocked

@clock
def factorial(n):
    """returns n!"""
    return 1 if n < 2 else n*factorial(n-1)

factorial.__name__, factorial.__doc__
# ('factorial', 'returns n!')
```

`functools.wraps` also sets a `__wrapped__` attribute on the wrapper, referring to the
original function, which tools like `inspect.signature()` use to report the right
signature.  It is just one of the ready-to-use decorators in the standard library.

## Decorators in the Standard Library

Python has three built-in functions that are designed to decorate methods:
`property`, `classmethod` and `staticmethod`.  `property` is covered in
[Using a Property for Attribute Validation](dynamic-attributes.md#using-a-property-for-attribute-validation),
and the others in [`classmethod` Versus `staticmethod`](pythonic-object.md#classmethod-versus-staticmethod).

You just saw another important decorator: `functools.wraps`, a helper for building
well-behaved decorators.  Some of the most interesting decorators in the standard
library are `cache`, `lru_cache` and `singledispatch`, all from the `functools`
module.

### Memoization with `functools.cache`

The [`functools.cache`](https://docs.python.org/3/library/functools.html#functools.cache)
decorator implements *memoization*: an optimization technique that works by saving
the results of previous invocations of an expensive function, avoiding repeat
computations on previously used arguments.  (That's not a typo: memoization is a
computer science term vaguely related to "memorization", but not the same.)

A good demonstration is to apply `@cache` to the painfully slow recursive function
that generates the *n*th number in the Fibonacci sequence:

<!-- nocheck -->
```python
from clockdeco import clock

@clock
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 2) + fibonacci(n - 1)

if __name__ == '__main__':
    print(fibonacci(6))
```

Here is the result of running it.  Except for the last line, all output is generated
by the `clock` decorator:

```console
$ python3 fibo_demo.py
[0.00000042s] fibonacci(0) -> 0
[0.00000049s] fibonacci(1) -> 1
[0.00006115s] fibonacci(2) -> 1
[0.00000031s] fibonacci(1) -> 1
[0.00000035s] fibonacci(0) -> 0
[0.00000030s] fibonacci(1) -> 1
[0.00001084s] fibonacci(2) -> 1
[0.00002074s] fibonacci(3) -> 2
[0.00009189s] fibonacci(4) -> 3
[0.00000029s] fibonacci(1) -> 1
[0.00000027s] fibonacci(0) -> 0
[0.00000029s] fibonacci(1) -> 1
[0.00000959s] fibonacci(2) -> 1
[0.00001905s] fibonacci(3) -> 2
[0.00000026s] fibonacci(0) -> 0
[0.00000029s] fibonacci(1) -> 1
[0.00000997s] fibonacci(2) -> 1
[0.00000028s] fibonacci(1) -> 1
[0.00000030s] fibonacci(0) -> 0
[0.00000031s] fibonacci(1) -> 1
[0.00001019s] fibonacci(2) -> 1
[0.00001967s] fibonacci(3) -> 2
[0.00003876s] fibonacci(4) -> 3
[0.00006670s] fibonacci(5) -> 5
[0.00016852s] fibonacci(6) -> 8
8
```

The waste is obvious: `fibonacci(1)` is called eight times, `fibonacci(2)` five
times, etc.  But adding just two lines to use `cache`, performance is much improved:

<!-- nocheck -->
```python
import functools

from clockdeco import clock

@functools.cache
@clock
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 2) + fibonacci(n - 1)

if __name__ == '__main__':
    print(fibonacci(6))
```

This is an example of *stacked decorators*: `@cache` is applied to the function
returned by `@clock`.

> **Note**
>
> To make sense of stacked decorators, recall that the `@` is syntax sugar for
> applying the decorator function to the function below it.  If there's more than
> one decorator, they behave like nested function calls.  This:
>
> ```python
> @alpha
> @beta
> def my_fn():
>     ...
> ```
>
> is the same as this:
>
> ```python
> my_fn = alpha(beta(my_fn))
> ```
>
> In other words, the `beta` decorator is applied first, and the function it returns
> is then passed to `alpha`.

Using `cache`, the `fibonacci` function is called only once for each value of `n`:

```console
$ python3 fibo_demo_lru.py
[0.00000043s] fibonacci(0) -> 0
[0.00000054s] fibonacci(1) -> 1
[0.00006179s] fibonacci(2) -> 1
[0.00000070s] fibonacci(3) -> 2
[0.00007366s] fibonacci(4) -> 3
[0.00000057s] fibonacci(5) -> 5
[0.00008479s] fibonacci(6) -> 8
8
```

In another test, to compute `fibonacci(30)`, the cached version made the 31 calls
needed in a fraction of a millisecond, while the uncached version took many seconds,
because it called `fibonacci(1)` 832,040 times, in a total of 2,692,537 calls.

All the arguments taken by the decorated function must be hashable, because the
underlying cache uses a `dict` to store the results, and the keys are made from the
positional and keyword arguments used in the calls.  Besides making silly recursive
algorithms viable, `@cache` really shines in applications that need to fetch
information from remote APIs.

```python
import functools

@functools.cache
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 2) + fibonacci(n - 1)

fibonacci(100)
# 354224848179261915075
fibonacci.cache_info()
# CacheInfo(hits=98, misses=101, maxsize=None, currsize=101)
```

> **Warning**
>
> `functools.cache` can consume all available memory if there is a very large number
> of cache entries.  It is more suitable for short-lived command-line scripts.  In
> long-running processes, use `functools.lru_cache` with a suitable `maxsize`
> parameter, as explained next.

### Using `lru_cache`

The `functools.cache` decorator is actually a simple wrapper around the older
[`functools.lru_cache`](https://docs.python.org/3/library/functools.html#functools.lru_cache)
function, which is more flexible.  The main advantage of `@lru_cache` is that its
memory usage is bounded by the `maxsize` parameter, which has a rather conservative
default value of 128, meaning the cache holds at most 128 entries at any time.  The
acronym LRU stands for *Least Recently Used*: older entries that have not been read
for a while are discarded to make room for new ones.

`lru_cache` can be applied in two ways.  The simplest:

<!-- nocheck -->
```python
@lru_cache
def costly_function(a, b):
    ...
```

The other way is to invoke it as a function, with `()`:

<!-- nocheck -->
```python
@lru_cache()
def costly_function(a, b):
    ...
```

In both cases, the default parameters are used.  These are:

`maxsize=128`
: Sets the maximum number of entries to be stored.  After the cache is full, the
  least recently used entry is discarded to make room for each new entry.  For
  optimal performance, `maxsize` should be a power of 2.  If you pass
  `maxsize=None`, the LRU logic is disabled, so the cache works faster but entries
  are never discarded, which may consume too much memory.  That's what
  `@functools.cache` does.

`typed=False`
: Determines whether the results of different argument types are stored
  separately.  For example, in the default setting, `float` and integer arguments
  that are considered equal are stored only once, so there would be a single entry
  for the calls `f(1)` and `f(1.0)`.  If `typed=True`, those arguments would produce
  different entries, possibly storing distinct results.

Here is `@lru_cache` with nondefault parameters:

<!-- nocheck -->
```python
@lru_cache(maxsize=2**20, typed=True)
def costly_function(a, b):
    ...
```

A related decorator, [`functools.cached_property`](https://docs.python.org/3/library/functools.html#functools.cached_property),
caches the result of a method on the instance; it is discussed in
[Dynamic Attributes and Properties](dynamic-attributes.md#step-5-caching-properties-with-functools).

### Single Dispatch Generic Functions

Imagine we are creating a tool to debug web applications.  We want to generate HTML
displays for different types of Python objects.  We could start with a function like
this:

```python
import html

def htmlize(obj):
    content = html.escape(repr(obj))
    return f'<pre>{content}</pre>'
```

That will work for any Python type, but now we want to extend it to generate custom
displays for some types:

`str`
: replace embedded newline characters with `'<br/>\n'` and use `<p>` tags instead
  of `<pre>`.

`int`
: show the number in decimal and hexadecimal (with a special case for `bool`).

`list`
: output an HTML list, formatting each item according to its type.

`float` and `Decimal`
: output the value as usual, but also in the form of a fraction (why not?).

The behavior we want is this:

<!-- nocheck -->
```python
htmlize({1, 2, 3})
# '<pre>{1, 2, 3}</pre>'
htmlize(abs)
# '<pre>&lt;built-in function abs&gt;</pre>'
htmlize('Heimlich & Co.\n- a game')
# '<p>Heimlich &amp; Co.<br/>\n- a game</p>'
htmlize(42)
# '<pre>42 (0x2a)</pre>'
print(htmlize(['alpha', 66, {3, 2, 1}]))
# <ul>
# <li><p>alpha</p></li>
# <li><pre>66 (0x42)</pre></li>
# <li><pre>{1, 2, 3}</pre></li>
# </ul>
htmlize(True)
# '<pre>True</pre>'
htmlize(fractions.Fraction(2, 3))
# '<pre>2/3</pre>'
htmlize(2/3)
# '<pre>0.6666666666666666 (2/3)</pre>'
htmlize(decimal.Decimal('0.02380952'))
# '<pre>0.02380952 (1/42)</pre>'
```

The original function handles arguments of any type that doesn't match the other
implementations.  `str` objects are also HTML-escaped but wrapped in `<p></p>`, with
`<br/>` line breaks inserted before each `'\n'`.  An `int` is shown in decimal and
hexadecimal, inside `<pre></pre>`.  Each list item is formatted according to its type,
and the whole sequence is rendered as an HTML list.  Although `bool` is an `int`
subtype, it gets special treatment.  A `Fraction` is shown as a fraction, and `float`
and `Decimal` with an approximate fractional equivalent.

#### Function `singledispatch`

Because we don't have Java-style method overloading in Python, we can't simply create
variations of `htmlize` with different signatures for each data type we want to
handle differently.  A possible solution in Python would be to turn `htmlize` into a
dispatch function, with a chain of `if/elif/...` or `match/case/...` calling
specialized functions like `htmlize_str`, `htmlize_int`, etc.  This is not extensible
by users of our module, and is unwieldy: over time, the `htmlize` dispatcher would
become too big, and the coupling between it and the specialized functions would be
very tight.

The [`functools.singledispatch`](https://docs.python.org/3/library/functools.html#functools.singledispatch)
decorator allows different modules to contribute to the overall solution, and lets
you easily provide specialized functions even for types that belong to third-party
packages that you can't edit.  If you decorate a plain function with
`@singledispatch`, it becomes the entry point for a *generic function*: a group of
functions to perform the same operation in different ways, depending on the type of
the first argument.  This is what is meant by the term *single dispatch*.  If more
arguments were used to select the specific functions, we'd have *multiple dispatch*.
Here is how:

```python
from functools import singledispatch
from collections import abc
import fractions
import decimal
import html
import numbers

@singledispatch
def htmlize(obj: object) -> str:
    content = html.escape(repr(obj))
    return f'<pre>{content}</pre>'

@htmlize.register
def _(text: str) -> str:
    content = html.escape(text).replace('\n', '<br/>\n')
    return f'<p>{content}</p>'

@htmlize.register
def _(seq: abc.Sequence) -> str:
    inner = '</li>\n<li>'.join(htmlize(item) for item in seq)
    return '<ul>\n<li>' + inner + '</li>\n</ul>'

@htmlize.register
def _(n: numbers.Integral) -> str:
    return f'<pre>{n} (0x{n:x})</pre>'

@htmlize.register
def _(n: bool) -> str:
    return f'<pre>{n}</pre>'

@htmlize.register(fractions.Fraction)
def _(x) -> str:
    frac = fractions.Fraction(x)
    return f'<pre>{frac.numerator}/{frac.denominator}</pre>'

@htmlize.register(decimal.Decimal)
@htmlize.register(float)
def _(x) -> str:
    frac = fractions.Fraction(x).limit_denominator()
    return f'<pre>{x} ({frac.numerator}/{frac.denominator})</pre>'

htmlize(42), htmlize(True), htmlize(2/3)
# ('<pre>42 (0x2a)</pre>', '<pre>True</pre>', '<pre>0.6666666666666666 (2/3)</pre>')
```

Some things to note:

* `@singledispatch` marks the base function that handles the `object` type.
* Each specialized function is decorated with `@«base».register`.
* The type of the first argument given at runtime determines when a particular
  function definition will be used.  The name of the specialized functions is
  irrelevant; `_` is a good choice to make this clear.
* For each additional type to get special treatment, register a new function with a
  matching type hint in the first parameter.
* The `numbers` ABCs are useful with `singledispatch`.
* `bool` is a subtype-of `numbers.Integral`, but the `singledispatch` logic seeks the
  implementation with the most specific matching type, regardless of the order in
  which they appear in the code.
* If you don't want to, or cannot, add type hints to the decorated function, you can
  pass a type to the `@«base».register` decorator.
* The `@«base».register` decorator returns the undecorated function, so it's
  possible to stack them to register two or more types on the same implementation.
  (Since Python 3.11 you can also register a union type, as in
  `def _(x: float | decimal.Decimal)`.)

When possible, register the specialized functions to handle ABCs such as
`numbers.Integral` and `abc.MutableSequence`, instead of concrete implementations like
`int` and `list`.  This allows your code to support a greater variety of compatible
types.  For example, a Python extension can provide alternatives to the `int` type
with fixed bit lengths as subclasses of `numbers.Integral` (NumPy does this).

> **Tip**
>
> Using ABCs or `typing.Protocol` with `@singledispatch` allows your code to support
> existing or future classes that are actual or virtual subclasses of those ABCs, or
> that implement those protocols.  ABCs and virtual subclasses are the subject of
> [Interfaces, Protocols, and ABCs](protocols-abcs.md).

A notable quality of the `singledispatch` mechanism is that you can register
specialized functions anywhere in the system, in any module.  If you later add a
module with a new user-defined type, you can easily provide a new custom function to
handle that type.  And you can write custom functions for classes that you did not
write and can't change.  [**PEP 443**](https://peps.python.org/pep-0443/) is a good
reference, though it doesn't mention type hints, which were added later; the
`functools` documentation has up-to-date coverage.  For methods, use
[`functools.singledispatchmethod`](https://docs.python.org/3/library/functools.html#functools.singledispatchmethod),
which dispatches on the type of the first argument after `self`.

> **Warning**
>
> `@singledispatch` is not designed to bring Java-style method overloading to Python.
> A single class with many overloaded variations of a method is better than a single
> function with a lengthy stretch of `if/elif/elif/elif` blocks.  But both solutions
> are flawed, because they concentrate too much responsibility in a single code unit,
> the class or the function.  The advantage of `@singledispatch` is supporting modular
> extension: each module can register a specialized function for each type it
> supports.  In a realistic use case, you would not have all the implementations of a
> generic function in the same module.

We've seen some decorators that take arguments, for example `@lru_cache()` and
`htmlize.register(float)`.  The next section shows how to build decorators that
accept parameters.

## Parameterized Decorators

When parsing a decorator in source code, Python takes the decorated function and
passes it as the first argument to the decorator function.  So how do you make a
decorator accept other arguments?  The answer is: make a *decorator factory* that
takes those arguments and returns a decorator, which is then applied to the function
to be decorated.  Confusing?  Sure.  Let's start with an example based on the
simplest decorator we've seen, `register`:

```python
registry = []

def register(func):
    print(f'running register({func})')
    registry.append(func)
    return func

@register
def f1():
    print('running f1()')

print('running main()')
print('registry ->', registry)
f1()
```

### A Parameterized Registration Decorator

To make it easy to enable or disable the registration performed by `register`, we'll
make it accept an optional `active` parameter which, if `False`, skips registering
the decorated function.  Conceptually, the new `register` function is not a decorator
but a decorator factory.  When called, it returns the actual decorator that will be
applied to the target function:

```python
registry = set()

def register(active=True):
    def decorate(func):
        print('running register'
              f'(active={active})->decorate({func})')
        if active:
            registry.add(func)
        else:
            registry.discard(func)

        return func
    return decorate

@register(active=False)
def f1():
    print('running f1()')

@register()
def f2():
    print('running f2()')

def f3():
    print('running f3()')
```

`registry` is now a `set`, so adding and removing functions is faster.  `register`
takes an optional keyword argument.  The `decorate` inner function is the actual
decorator; note how it takes a function as an argument.  It registers `func` only if
the `active` argument (retrieved from the closure) is `True`; if not active and
`func in registry`, it removes it.  Because `decorate` is a decorator, it must return
a function, and `register`, our decorator factory, returns `decorate`.

The `@register` factory must be invoked as a function, with the desired parameters.
If no parameters are passed, `register` must still be called as a function,
`@register()`, to return the actual decorator, `decorate`.  The main point is that
`register()` returns `decorate`, which is then applied to the decorated function.

If that code is in a `registration_param.py` module and we import it, this is what we
get:

<!-- nocheck -->
```python
import registration_param
# running register(active=False)->decorate(<function f1 at 0x10063c1e0>)
# running register(active=True)->decorate(<function f2 at 0x10063c268>)
registration_param.registry
# {<function f2 at 0x10063c268>}
```

Only the `f2` function appears in the registry; `f1` does not appear because
`active=False` was passed to the `register` decorator factory, so the `decorate`
applied to `f1` did not add it to the registry.

If, instead of using the `@` syntax, we used `register` as a regular function, the
syntax needed to decorate a function `f` would be `register()(f)` to add `f` to the
registry, or `register(active=False)(f)` to not add it (or remove it):

<!-- nocheck -->
```python
from registration_param import *
# running register(active=False)->decorate(<function f1 at 0x10073c1e0>)
# running register(active=True)->decorate(<function f2 at 0x10073c268>)
registry  # when the module is imported, f2 is in the registry
# {<function f2 at 0x10073c268>}
register()(f3)  # register() returns decorate, which is then applied to f3
# running register(active=True)->decorate(<function f3 at 0x10073c158>)
# <function f3 at 0x10073c158>
registry  # the previous line added f3 to the registry
# {<function f3 at 0x10073c158>, <function f2 at 0x10073c268>}
register(active=False)(f2)  # this call removes f2 from the registry
# running register(active=False)->decorate(<function f2 at 0x10073c268>)
# <function f2 at 0x10073c268>
registry  # only f3 remains
# {<function f3 at 0x10073c158>}
```

The workings of parameterized decorators are fairly involved, and the one we've just
discussed is simpler than most.  Parameterized decorators usually replace the
decorated function, and their construction requires yet another level of nesting.

### The Parameterized Clock Decorator

Let's revisit the `clock` decorator, adding a feature: users may pass a format string
to control the output of the clocked function report.  (For simplicity, this is based
on the initial `clock` implementation, not the improved one that uses
`@functools.wraps`, which would add yet another function layer.)

```python
import time

DEFAULT_FMT = '[{elapsed:0.8f}s] {name}({args}) -> {result}'

def clock(fmt=DEFAULT_FMT):
    def decorate(func):
        def clocked(*_args):
            t0 = time.perf_counter()
            _result = func(*_args)
            elapsed = time.perf_counter() - t0
            name = func.__name__
            args = ', '.join(repr(arg) for arg in _args)
            result = repr(_result)
            print(fmt.format(**locals()))
            return _result
        return clocked
    return decorate

if __name__ == '__main__':

    @clock()
    def snooze(seconds):
        time.sleep(seconds)

    for i in range(3):
        snooze(.123)
```

`clock` is our parameterized decorator factory, `decorate` is the actual decorator,
and `clocked` wraps the decorated function.  `_result` is the actual result of the
decorated function, and `_args` holds the actual arguments of `clocked`, while `args`
is the `str` used for display and `result` is the `str` representation of `_result`,
also for display.  Using `**locals()` lets any local variable of `clocked` be
referenced in `fmt`.  (Linters may complain about unused variables, since they tend to
ignore uses of `locals()`; you could spell out each variable instead, as in
`fmt.format(elapsed=elapsed, name=name, args=args, result=result)`.)  `clocked`
replaces the decorated function, so it returns whatever that function returns;
`decorate` returns `clocked`, and `clock` returns `decorate`.  In the self test,
`clock()` is called without arguments, so the decorator applied uses the default
format.  If you run the module from the shell, this is what you get:

```console
$ python3 clockdeco_param.py
[0.12412500s] snooze(0.123) -> None
[0.12411904s] snooze(0.123) -> None
[0.12410498s] snooze(0.123) -> None
```

To exercise the new functionality, here are two other modules using
`clockdeco_param`, and the outputs they generate:

<!-- nocheck -->
```python
import time
from clockdeco_param import clock

@clock('{name}: {elapsed}s')
def snooze(seconds):
    time.sleep(seconds)

for i in range(3):
    snooze(.123)
```

```console
$ python3 clockdeco_param_demo1.py
snooze: 0.12414693832397461s
snooze: 0.1241159439086914s
snooze: 0.12412118911743164s
```

<!-- nocheck -->
```python
import time
from clockdeco_param import clock

@clock('{name}({args}) dt={elapsed:0.3f}s')
def snooze(seconds):
    time.sleep(seconds)

for i in range(3):
    snooze(.123)
```

```console
$ python3 clockdeco_param_demo2.py
snooze(0.123) dt=0.124s
snooze(0.123) dt=0.124s
snooze(0.123) dt=0.124s
```

> **Tip**
>
> Many experienced Pythonistas argue that nontrivial decorators are best coded as
> classes implementing `__call__()`, rather than as nested functions.  Functions are
> easier for explaining the basic idea, but for industrial-strength techniques when
> building decorators see Graham Dumpleton's blog posts and his
> [wrapt](https://pypi.org/project/wrapt/) package.

### A Class-Based Clock Decorator

As a final example, here is a parameterized clock decorator implemented as a class
with `__call__()`.  Contrast it with the function-based version.  Which one do you
prefer?

```python
import time

DEFAULT_FMT = '[{elapsed:0.8f}s] {name}({args}) -> {result}'

class clock:

    def __init__(self, fmt=DEFAULT_FMT):
        self.fmt = fmt

    def __call__(self, func):
        def clocked(*_args):
            t0 = time.perf_counter()
            _result = func(*_args)
            elapsed = time.perf_counter() - t0
            name = func.__name__
            args = ', '.join(repr(arg) for arg in _args)
            result = repr(_result)
            print(self.fmt.format(**locals()))
            return _result
        return clocked

@clock('{name}({args}) -> {result}')
def add(a, b):
    return a + b

add(2, 3)
# add(2, 3) -> 5
# 5
```

Instead of a `clock` outer function, the `clock` class is our parameterized
decorator factory.  It is named with a lowercase `c` to make clear that this
implementation is a drop-in replacement for the function-based one.  The argument
passed in `clock(my_format)` is assigned to the `fmt` parameter; the class constructor
returns an instance of `clock`, with `my_format` stored in `self.fmt`.  `__call__()`
makes the `clock` instance callable: when invoked, the instance replaces the decorated
function with `clocked`, which wraps the decorated function.

That ends our exploration of function decorators.  Class decorators are covered in
[Class Metaprogramming](class-metaprogramming.md).

## Summary

We covered some difficult terrain in this chapter, and definitely entered the realm of
metaprogramming.  We started with a simple `@register` decorator without an inner
function, and finished with a parameterized `@clock()` involving two levels of nested
functions.

Registration decorators, though simple in essence, have real applications in Python
frameworks.  We will apply the registration idea in one implementation of the
Strategy design pattern in [Design Patterns with First-Class Functions](function-patterns.md).

Understanding how decorators actually work required covering the difference between
import time and runtime, then diving into variable scoping, closures, and the
`nonlocal` declaration.  Mastering closures and `nonlocal` is valuable not only to
build decorators, but also to write event-oriented programs for GUIs or asynchronous
I/O with callbacks, and to adopt a functional style when it makes sense.

Parameterized decorators almost always involve at least two nested functions, maybe
more if you want to use `@functools.wraps` to produce a decorator that provides better
support for more advanced techniques, such as stacked decorators.  For more
sophisticated decorators, a class-based implementation may be easier to read and
maintain.  As examples of decorators in the standard library, we visited the powerful
`@cache`, `@lru_cache` and `@singledispatch` from the `functools` module.

> **Note**
>
> Why do closures matter so much?  The designer of any language with first-class
> functions faces this issue: a function is defined in one scope but may be invoked
> in others, so how should its free variables be evaluated?  The simplest answer is
> *dynamic scope*: look up free variables in the environment where the function is
> *invoked*.  But then, to use a function with free variables, you'd have to know its
> internals and set up the right environment, and an unrelated assignment like
> `series = [1]` could silently break `avg`.  Most modern languages use *lexical
> scope* instead: free variables are evaluated in the environment where the function
> is *defined*.  Lexical scope makes source code easier to read, but it requires
> closures.  Lisp started with dynamic scope (Emacs Lisp still uses it by default);
> Scheme, in 1975, popularized lexical scope.  Python lambdas did not provide closures
> until Python 2.2.

> **See also**
>
> * Graham Dumpleton's blog series starting with "How you implemented your Python
>   decorator is wrong" explains techniques for well-behaved decorators that support
>   introspection and behave correctly when applied to methods and when used as
>   descriptors.
> * Chapter 9, "Metaprogramming", of the *Python Cookbook*, 3rd ed., by David Beazley
>   and Brian K. Jones, has several recipes, from elementary decorators to a decorator
>   that can be used with or without arguments, like `@clock` or `@clock()`.
> * [**PEP 3104**](https://peps.python.org/pep-3104/) describes the introduction of
>   `nonlocal` and compares how other dynamic languages solve the same problem.
>   [**PEP 227**](https://peps.python.org/pep-0227/) documents the introduction of
>   lexical scoping in Python 2.1 and 2.2.
> * Item 26 of Brett Slatkin's *Effective Python*, 2nd ed., recommends always using
>   `functools.wraps` when defining function decorators.
