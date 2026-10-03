# Context Managers and `else` Blocks

> Context managers may end up being almost as important as the subroutine itself.
> We've only scratched the surface with them. [...] Basic has a `with` statement, there
> are `with` statements in lots of languages.  But they don't do the same thing, they
> all do something very shallow, they save you from repeated dotted [attribute] lookups,
> they don't do setup and tear down.  Just because it's the same name don't think it's
> the same thing.  The `with` statement is a very big deal.
>
> — Raymond Hettinger, PyCon US 2013 keynote

This chapter is about control flow features that are not so common in other languages,
and for this reason tend to be overlooked or underused in Python.  They are:

* the `with` statement and the context manager protocol;
* the `else` clause in `for`, `while` and `try` statements.

The `with` statement sets up a temporary context and reliably tears it down, under the
control of a context manager object.  This prevents errors and reduces boilerplate code,
making APIs at the same time safer and easier to use.  Python programmers are finding lots
of uses for `with` blocks beyond automatic file closing, which you saw in
[Predefined Clean-up Actions](errors.md#tut-cleanup-with) and
[Reading and Writing Files](inputoutput.md#tut-files).

The `else` clause is not a big deal, but it does help convey intention when properly used
together with `for`, `while` and `try`.

> **Note**
>
> In *Fluent Python*, this chapter also covers `match`/`case` through a case study of
> Peter Norvig's `lis.py` Scheme interpreter.  In this book, that case study lives with
> the rest of pattern matching, in
> [Case Study: Pattern Matching in `lis.py`](pattern-matching.md#case-study-pattern-matching-in-lispy).

Let's start with the powerful `with` statement.

## Context Managers and `with` Blocks

Context manager objects exist to control a `with` statement, just like iterators exist to
control a `for` statement.

The `with` statement was designed to simplify some common uses of `try`/`finally`, which
guarantees that some operation is performed after a block of code, even if the block is
terminated by `return`, an exception, or a `sys.exit()` call.  The code in the `finally`
clause usually releases a critical resource or restores some previous state that was
temporarily changed.

The Python community keeps finding new, creative uses for context managers.  Some examples
from the standard library are:

* managing transactions in the `sqlite3` module — see
  [How to use the connection context manager](https://docs.python.org/3/library/sqlite3.html#sqlite3-connection-context-manager);
* safely handling locks, conditions and semaphores — as described in the
  [`threading`](https://docs.python.org/3/library/threading.html#using-locks-conditions-and-semaphores-in-the-with-statement)
  module documentation;
* setting up custom environments for arithmetic operations with `Decimal` objects — see
  the [`decimal.localcontext`](https://docs.python.org/3/library/decimal.html#decimal.localcontext)
  documentation;
* patching objects for testing — see the
  [`unittest.mock.patch`](https://docs.python.org/3/library/unittest.mock.html#patch)
  function.

The context manager interface consists of the `__enter__()` and `__exit__()` methods.  At
the top of the `with`, Python calls the `__enter__()` method of the context manager
object.  When the `with` block completes or terminates for any reason, Python calls
`__exit__()` on the context manager object.

The most common example is making sure a file object is closed.  Here is a detailed
demonstration of using `with` to close a file:

<!-- nocheck -->
```python
with open('mirror.py') as fp:  # fp is bound to the file, because its __enter__ returns self
    src = fp.read(60)  # read 60 Unicode characters from fp

len(src)
# 60
fp  # the fp variable is still available: with blocks don't define a new scope
# <_io.TextIOWrapper name='mirror.py' mode='r' encoding='utf-8'>
fp.closed, fp.encoding  # we can read the attributes of the fp object
# (True, 'utf-8')
fp.read(60)  # but we can't read more text from fp: __exit__ closed the file
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# ValueError: I/O operation on closed file.
```

`fp` is bound to the opened text file because the file's `__enter__()` method returns
`self`.  The `fp` variable is still available after the block — `with` blocks don't
define a new scope, as functions do.  We can read the attributes of the `fp` object.  But
we can't read more text from `fp` because at the end of the `with` block, the
`TextIOWrapper.__exit__` method was called, and it closed the file.  (The encoding shown
is `'utf-8'` because, since Python 3.15, UTF-8 is the default encoding for files opened
in text mode; see [**PEP 686**](https://peps.python.org/pep-0686/).)

The first comment in that example makes a subtle but crucial point: the context manager
object is the result of evaluating the expression after `with`, but the value bound to the
target variable (in the `as` clause) is the result returned by the `__enter__()` method of
the context manager object.

It just happens that the `open()` function returns an instance of `TextIOWrapper`, and its
`__enter__()` method returns `self`.  But in a different class, the `__enter__()` method
may also return some other object instead of the context manager instance.

When control flow exits the `with` block in any way, the `__exit__()` method is invoked on
the context manager object, not on whatever was returned by `__enter__()`.

The `as` clause of the `with` statement is optional.  In the case of `open`, we always need
it to get a reference to the file, so that we can call methods on it.  But some context
managers return `None` because they have no useful object to give back to the user.

Here is a perfectly frivolous context manager designed to highlight the distinction
between the context manager and the object returned by its `__enter__()` method:

```python
import sys

class LookingGlass:

    def __enter__(self):  # Python invokes __enter__ with no arguments besides self
        self.original_write = sys.stdout.write  # hold the original method, to restore later
        sys.stdout.write = self.reverse_write  # monkey-patch sys.stdout.write
        return 'JABBERWOCKY'  # return a string just so we have something in the target variable

    def reverse_write(self, text):  # our replacement reverses the text argument
        self.original_write(text[::-1])

    def __exit__(self, exc_type, exc_value, traceback):  # all None if all went well
        sys.stdout.write = self.original_write  # restore the original method
        if exc_type is ZeroDivisionError:  # if the exception is a ZeroDivisionError...
            print('Please DO NOT divide by zero!')
            return True  # ...tell the interpreter that the exception was handled
```

`__enter__()` holds the original `sys.stdout.write` method, so we can restore it later,
then monkey-patches `sys.stdout.write`, replacing it with our own method, and returns the
`'JABBERWOCKY'` string just so we have something to put in the target variable `what`.
Our replacement to `sys.stdout.write` reverses the `text` argument and calls the original
implementation.  Python calls `__exit__()` with `None, None, None` if all went well; if an
exception is raised, the three arguments get the exception data, as described after this
example.  `__exit__()` restores the original method to `sys.stdout.write`.  If the
exception is not `None` and its type is `ZeroDivisionError`, it prints a message and
returns `True` to tell the interpreter that the exception was handled.

If `__exit__()` returns `None` or any falsy value, any exception raised in the `with` block
will be propagated.  Here is `LookingGlass` in action:

```python
with LookingGlass() as what:  # Python calls __enter__; the result is bound to what
    print('Alice, Kitty and Snowdrop')  # the output of each print comes out reversed
    print(what)

# pordwonS dna yttiK ,ecilA
# YKCOWREBBAJ
what  # the with block is over; what holds the value returned by __enter__
# 'JABBERWOCKY'
print('Back to normal.')  # program output is no longer reversed
# Back to normal.
```

The `ZeroDivisionError` handling also works as designed:

```python
with LookingGlass():
    print('Humpty Dumpty')
    x = 1/0  # an exception: __exit__ restores stdout, prints a message, and returns True
    # the next line is never reached
    print('END')

# ytpmuD ytpmuH
# Please DO NOT divide by zero!
```

> **Tip**
>
> When real applications take over standard output, they often want to replace
> `sys.stdout` with another file-like object for a while, then switch back to the
> original.  The [`contextlib.redirect_stdout`](https://docs.python.org/3/library/contextlib.html#contextlib.redirect_stdout)
> context manager does exactly that: just pass it the file-like object that will stand in
> for `sys.stdout`.

The interpreter calls the `__enter__()` method with no arguments — beyond the implicit
`self`.  The three arguments passed to `__exit__()` are:

`exc_type`
: The exception class (e.g., `ZeroDivisionError`).

`exc_value`
: The exception instance.  Sometimes, parameters passed to the exception constructor —
  such as the error message — can be found in `exc_value.args`.

`traceback`
: A traceback object.

(Those three values are what `sys.exc_info()` returns inside a `finally` block, which makes
sense, considering that the `with` statement is meant to replace most uses of
`try`/`finally`.)

For a detailed look at how a context manager works, here `LookingGlass` is used outside of
a `with` block, so we can manually call its `__enter__()` and `__exit__()` methods:

```python
manager = LookingGlass()  # instantiate and inspect the manager instance
manager
# <__main__.LookingGlass object at 0x...>
monster = manager.__enter__()  # call __enter__ and store the result in monster
monster == 'JABBERWOCKY'  # True appears reversed: stdout goes through reverse_write
# eurT
monster
# 'YKCOWREBBAJ'
manager
# >... ta tcejbo ssalGgnikooL.__niam__<
manager.__exit__(None, None, None)  # restore the previous stdout.write
monster
# 'JABBERWOCKY'
```

> **Note**
>
> Since Python 3.10, you can wrap several context managers in parentheses, spread over
> multiple lines:
>
> ```python
> with (
>     CtxManager1() as example1,
>     CtxManager2() as example2,
>     CtxManager3() as example3,
> ):
>     ...
> ```
>
> Before 3.10, we had to write that as nested `with` blocks, or use backslashes.

The standard library includes the `contextlib` package with handy functions, classes and
decorators for building, combining and using context managers.

### The `contextlib` Utilities

Before rolling your own context manager classes, take a look at
[`contextlib`](https://docs.python.org/3/library/contextlib.html) — "Utilities for
`with`-statement contexts" in the Python documentation.  Maybe what you are about to build
already exists, or there is a class or some callable that will make your job easier.

Besides the `redirect_stdout` context manager mentioned earlier, `redirect_stderr` does the
same, but for output directed to `stderr`.  The `contextlib` package also includes:

`closing`
: A function to build context managers out of objects that provide a `close()` method but
  don't implement the `__enter__`/`__exit__` interface.

`suppress`
: A context manager to temporarily ignore exceptions given as arguments.

`nullcontext`
: A context manager that does nothing, to simplify conditional logic around objects that
  may not implement a suitable context manager.  It serves as a stand-in when conditional
  code before the `with` block may or may not provide a context manager for the `with`
  statement.

`chdir`
: A context manager that changes the current working directory, and restores the previous
  one on exit (Python 3.11+).

The `contextlib` module also provides classes and a decorator that are more widely
applicable than the utilities just mentioned:

`@contextmanager`
: A decorator that lets you build a context manager from a simple generator function,
  instead of creating a class and implementing the interface.  See
  [Using `@contextmanager`](#using-contextmanager).

`AbstractContextManager`
: An ABC that formalizes the context manager interface, and makes it a bit easier to create
  context manager classes by subclassing.

`ContextDecorator`
: A base class for defining class-based context managers that can also be used as function
  decorators, running the entire function within a managed context.

`ExitStack`
: A context manager that lets you enter a variable number of context managers.  When the
  `with` block ends, `ExitStack` calls the stacked context managers' `__exit__()` methods
  in LIFO order (last entered, first exited).  Use this class when you don't know
  beforehand how many context managers you need to enter in your `with` block; for
  example, when opening all files from an arbitrary list of files at the same time.

There are also `AbstractAsyncContextManager`, `@asynccontextmanager`, `aclosing` and
`AsyncExitStack`.  They are similar to the equivalent utilities without the `async` part of
the name, but designed for use with the `async with` statement, covered in
[Asynchronous Programming](asyncio.md).

Here are a few of these utilities at work:

```python
import contextlib
import io

with contextlib.suppress(KeyError):  # ignore a KeyError raised in the block
    {}['missing']
    print('not reached')

buf = io.StringIO()
with contextlib.redirect_stdout(buf):  # temporarily send print output to buf
    print('captured!')

buf.getvalue()
# 'captured!\n'

def maybe_lock(lock=None):
    return lock if lock is not None else contextlib.nullcontext()

with maybe_lock():  # no lock given: nullcontext does nothing
    print('working without a lock')

# working without a lock
with contextlib.ExitStack() as stack:
    for name in 'ABC':
        stack.callback(print, 'cleaning up', name)  # register cleanup callbacks
    print('inside the with block')

# inside the with block
# cleaning up C
# cleaning up B
# cleaning up A
```

The most widely used of these utilities is the `@contextmanager` decorator, so it deserves
more attention.  That decorator is also interesting because it shows a use for the `yield`
statement unrelated to iteration.

### Using `@contextmanager`

The `@contextmanager` decorator is an elegant and practical tool that brings together three
distinctive Python features: a function decorator, a generator, and the `with` statement.

Using `@contextmanager` reduces the boilerplate of creating a context manager: instead of
writing a whole class with `__enter__`/`__exit__` methods, you just implement a generator
with a single `yield` that should produce whatever you want the `__enter__()` method to
return.

In a generator decorated with `@contextmanager`, `yield` splits the body of the function in
two parts: everything before the `yield` will be executed at the beginning of the `with`
block when the interpreter calls `__enter__()`; the code after `yield` will run when
`__exit__()` is called at the end of the block.  Here the `LookingGlass` class is replaced
with a generator function:

```python
import contextlib
import sys

@contextlib.contextmanager  # apply the contextmanager decorator
def looking_glass():
    original_write = sys.stdout.write  # preserve the original sys.stdout.write method

    def reverse_write(text):  # reverse_write can call original_write: it's in the closure
        original_write(text[::-1])

    sys.stdout.write = reverse_write  # replace sys.stdout.write with reverse_write
    yield 'JABBERWOCKY'  # the value bound to the as target; the generator pauses here
    sys.stdout.write = original_write  # when control exits the with block, execution resumes here
```

Here is the `looking_glass` function in operation:

```python
with looking_glass() as what:  # the only difference: the name of the context manager
    print('Alice, Kitty and Snowdrop')
    print(what)

# pordwonS dna yttiK ,ecilA
# YKCOWREBBAJ
what
# 'JABBERWOCKY'
print('back to normal')
# back to normal
```

The `contextlib.contextmanager` decorator wraps the function in a class that implements the
`__enter__()` and `__exit__()` methods (the actual class is named
`_GeneratorContextManager`; read its source code in `Lib/contextlib.py` if you want to see
exactly how it works).  The `__enter__()` method of that class:

1. calls the generator function to get a generator object — let's call it `gen`;
2. calls `next(gen)` to drive it to the `yield` keyword;
3. returns the value yielded by `next(gen)`, to allow the user to bind it to a variable in
   the `with`/`as` form.

When the `with` block terminates, the `__exit__()` method:

1. checks whether an exception was passed as `exc_type`; if so, `gen.throw(exception)` is
   invoked, causing the exception to be raised in the `yield` line inside the generator
   function body;
2. otherwise, `next(gen)` is called, resuming the execution of the generator function body
   after the `yield`.

That `looking_glass` has a flaw: if an exception is raised in the body of the `with` block,
the Python interpreter will catch it and raise it again in the `yield` expression inside
`looking_glass`.  But there is no error handling there, so the `looking_glass` generator
will terminate without ever restoring the original `sys.stdout.write` method, leaving the
system in an invalid state.  This version adds special handling of the `ZeroDivisionError`
exception, making it functionally equivalent to the class-based `LookingGlass`:

```python
import contextlib
import sys

@contextlib.contextmanager
def looking_glass():
    original_write = sys.stdout.write

    def reverse_write(text):
        original_write(text[::-1])

    sys.stdout.write = reverse_write
    msg = ''  # a variable for a possible error message
    try:
        yield 'JABBERWOCKY'
    except ZeroDivisionError:  # handle ZeroDivisionError by setting an error message
        msg = 'Please DO NOT divide by zero!'
    finally:
        sys.stdout.write = original_write  # undo monkey-patching of sys.stdout.write
        if msg:
            print(msg)  # display the error message, if it was set

with looking_glass():
    print('Humpty Dumpty')
    x = 1/0
    print('END')

# ytpmuD ytpmuH
# Please DO NOT divide by zero!
```

Recall that the `__exit__()` method tells the interpreter that it has handled the exception
by returning a truthy value; in that case, the interpreter suppresses the exception.  On the
other hand, if `__exit__()` does not explicitly return a value, the interpreter gets the
usual `None`, and propagates the exception.  With `@contextmanager`, the default behavior is
inverted: the `__exit__()` method provided by the decorator assumes any exception sent into
the generator is handled and should be suppressed — unless the generator re-raises it, or
lets it propagate by not catching it.

> **Tip**
>
> Having a `try`/`finally` (or a `with` block) around the `yield` is an unavoidable price of
> using `@contextmanager`, because you never know what the users of your context manager
> are going to do inside the `with` block.

A little-known feature of `@contextmanager` is that the generators decorated with it can
also be used as decorators themselves.  That happens because `@contextmanager` is
implemented with the `contextlib.ContextDecorator` class.  Here is the `looking_glass`
context manager used as a decorator:

```python
@looking_glass()
def verse():
    print('The time has come')

verse()  # looking_glass does its job before and after the body of verse runs
# emoc sah emit ehT
print('back to normal')  # this confirms that the original sys.stdout.write was restored
# back to normal
```

Contrast that with the previous examples, where `looking_glass` is used as a context
manager.

Here is a practical example, to time a block of code:

```python
import time
from contextlib import contextmanager

@contextmanager
def timer(label):
    t0 = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - t0
        print(f'{label}: {elapsed:.3f}s')

with timer('sum of squares'):
    total = sum(n * n for n in range(1_000_000))

# sum of squares: 0.051s
```

An interesting real-life example of `@contextmanager` outside of the standard library is
Martijn Pieters' [in-place file rewriting using a context manager](https://www.zopatista.com/python/2013/11/26/inplace-file-rewriting/).
It's used like this:

<!-- nocheck -->
```python
import csv

with inplace(csvfilename, 'r', newline='') as (infh, outfh):
    reader = csv.reader(infh)
    writer = csv.writer(outfh)

    for row in reader:
        row += ['new', 'columns']
        writer.writerow(row)
```

The `inplace` function is a context manager that gives you two handles — `infh` and
`outfh` in the example — to the same file, allowing your code to read and write to it at
the same time.  It's easier to use than the standard library's `fileinput.input` function
(which also provides a context manager, by the way).  If you study its source code, find
the `yield` keyword: everything before it deals with setting up the context, which entails
creating a backup file, then opening and yielding references to the readable and writable
file handles that will be returned by the `__enter__()` call.  The `__exit__()` processing
after the `yield` closes the file handles and restores the file from the backup if
something went wrong.

This concludes our overview of the `with` statement and context managers.  Let's turn to
the unusual places where an `else` clause may appear in Python.

## Do This, Then That: `else` Blocks Beyond `if`

This is no secret, but it is an underappreciated language feature: the `else` clause can be
used not only in `if` statements but also in `for`, `while` and `try` statements.  (The
tutorial introduced the `for` case in
[`break` and `continue` Statements, and `else` Clauses on Loops](controlflow.md#tut-for-else).)

The semantics of `for`/`else`, `while`/`else` and `try`/`else` are closely related, but
very different from `if`/`else`.  Here are the rules:

`for`
: The `else` block will run only if and when the `for` loop runs to completion (i.e., not
  if the `for` is aborted with a `break`).

`while`
: The `else` block will run only if and when the `while` loop exits because the condition
  became falsy (i.e., not if the `while` is aborted with a `break`).

`try`
: The `else` block will run only if no exception is raised in the `try` block.  The
  official docs also state: "Exceptions in the `else` clause are not handled by the
  preceding `except` clauses."

In all cases, the `else` clause is also skipped if an exception or a `return`, `break` or
`continue` statement causes control to jump out of the main block of the compound
statement.

> **Note**
>
> `else` is arguably a poor choice for the keyword in all cases except `if`.  It implies an
> excluding alternative, like, "Run this loop, otherwise do that", but the semantics for
> `else` in loops is the opposite: "Run this loop, then do that".  This suggests `then` as
> a better keyword — which would also make sense in the `try` context: "Try this, then do
> that".  However, adding a new keyword is a breaking change to the language — not an easy
> decision to make.

Using `else` with these statements often makes the code easier to read and saves the
trouble of setting up control flags or coding extra `if` statements.  The use of `else` in
loops generally follows the pattern of this snippet:

```python
from dataclasses import dataclass

@dataclass
class IceCream:
    flavor: str

my_list = [IceCream('vanilla'), IceCream('chocolate')]

for item in my_list:
    if item.flavor == 'banana':
        break
else:
    print('No banana flavor found!')  # often a raise ValueError(...) in real code

# No banana flavor found!
```

In the case of `try`/`except` blocks, `else` may seem redundant at first.  After all, the
`after_call()` in the following snippet will run only if the `dangerous_call()` does not
raise an exception, correct?

<!-- nocheck -->
```python
try:
    dangerous_call()
    after_call()
except OSError:
    log('OSError...')
```

However, doing so puts the `after_call()` inside the `try` block for no good reason.  For
clarity and correctness, the body of a `try` block should only have the statements that may
generate the expected exceptions.  This is better:

<!-- nocheck -->
```python
try:
    dangerous_call()
except OSError:
    log('OSError...')
else:
    after_call()
```

Now it's clear that the `try` block is guarding against possible errors in
`dangerous_call()` and not in `after_call()`.  It's also explicit that `after_call()` will
only execute if no exceptions are raised in the `try` block.

In Python, `try`/`except` is commonly used for control flow, and not just for error
handling.  There's even an acronym/slogan for that documented in the official
[Python glossary](https://docs.python.org/3/glossary.html#term-EAFP):

> **EAFP**
>
> Easier to ask for forgiveness than permission.  This common Python coding style assumes
> the existence of valid keys or attributes and catches exceptions if the assumption
> proves false.  This clean and fast style is characterized by the presence of many `try`
> and `except` statements.  The technique contrasts with the LBYL style common to many
> other languages such as C.

The glossary then defines LBYL:

> **LBYL**
>
> Look before you leap.  This coding style explicitly tests for pre-conditions before
> making calls or lookups.  This style contrasts with the EAFP approach and is
> characterized by the presence of many `if` statements.  In a multi-threaded environment,
> the LBYL approach can risk introducing a race condition between "the looking" and "the
> leaping".  For example, the code, `if key in mapping: return mapping[key]` can fail if
> another thread removes `key` from `mapping` after the test, but before the lookup.  This
> issue can be solved with locks or by using the EAFP approach.

Here are the two styles side by side:

```python
mapping = {'a': 1}

# LBYL
if 'b' in mapping:
    value = mapping['b']
else:
    value = 0

# EAFP
try:
    value = mapping['b']
except KeyError:
    value = 0
else:
    print('found it')  # only runs when no exception was raised

value
# 0
```

Given the EAFP style, it makes even more sense to know and use `else` blocks well in
`try`/`except` statements.

> **Note**
>
> When the `match` statement was discussed, some people thought it should also have an
> `else` clause.  In the end it was decided that it wasn't needed because `case _:` does
> the same job.

## Summary

This chapter started with context managers and the meaning of the `with` statement, quickly
moving beyond its common use to automatically close opened files.  We implemented a custom
context manager: the `LookingGlass` class with the `__enter__`/`__exit__` methods, and saw
how to handle exceptions in the `__exit__()` method.  A key point that Raymond Hettinger
made in his PyCon US 2013 keynote is that `with` is not just for resource management; it's a
tool for factoring out common setup and teardown code, or any pair of operations that need
to be done before and after another procedure.

We reviewed functions in the `contextlib` standard library module.  One of them, the
`@contextmanager` decorator, makes it possible to implement a context manager using a simple
generator with one `yield` — a leaner solution than coding a class with at least two
methods.  We reimplemented the `LookingGlass` as a `looking_glass` generator function, and
discussed how to do exception handling when using `@contextmanager`.

Finally, we looked at the `else` clause in `for`, `while` and `try` statements, and at the
EAFP and LBYL coding styles.

> **Note**
>
> In his keynote, Hettinger said subroutines are the most important invention in the
> history of computer languages.  If you have sequences of operations like `A;B;C` and
> `P;B;Q`, you can factor out `B` in a subroutine.  It's like factoring out the filling in
> a sandwich: using tuna with different breads.  But what if you want to factor out the
> *bread*, to make sandwiches with wheat bread, using a different filling each time?
> That's what the `with` statement offers.  It's the complement of the subroutine.

> **See also**
>
> * [Compound statements](https://docs.python.org/3/reference/compound_stmts.html) in the
>   Language Reference says pretty much everything there is to say about `else` clauses in
>   `if`, `for`, `while` and `try` statements.
> * [Context Manager Types](https://docs.python.org/3/library/stdtypes.html#typecontextmanager)
>   in the Library Reference, and
>   [With Statement Context Managers](https://docs.python.org/3/reference/datamodel.html#context-managers)
>   in the Language Reference.  Context managers were introduced in
>   [**PEP 343**](https://peps.python.org/pep-0343/) — The "with" Statement.
> * Nikolaus Rath, "On the Beauty of Python's ExitStack", which compares `ExitStack` to the
>   `defer` statement in Go.
> * Recipes 8.3 and 9.22 of *Python Cookbook*, 3rd ed., by Beazley and Jones, including a
>   context manager for transactional changes to a list: within the `with` block, a working
>   copy is changed, and it replaces the original only if the block completes without an
>   exception.
