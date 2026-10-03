# Inheritance: For Better or for Worse

> [...] we needed a better theory about inheritance entirely (and still do).  For
> example, inheritance and instancing (which is a kind of inheritance) muddles both
> pragmatics (such as factoring code to save space) and semantics (used for way too many
> tasks such as: specialization, generalization, speciation, etc.).
>
> — Alan Kay, "The Early History of Smalltalk"

This chapter is about inheritance and subclassing.  It assumes the basic understanding
of these concepts given in [Inheritance](classes.md#tut-inheritance) and
[Multiple Inheritance](classes.md#tut-multiple), and focuses on four characteristics of
Python:

* the `super()` function;
* the pitfalls of subclassing from built-in types;
* multiple inheritance and method resolution order;
* mixin classes.

*Multiple inheritance* is the ability of a class to have more than one base class.  C++
supports it; Java and C# don't.  Many consider multiple inheritance more trouble than
it's worth; it was deliberately left out of Java after its perceived abuse in early C++
codebases.

There is also a significant backlash against overuse of inheritance in general — not
only multiple inheritance — because superclasses and subclasses are tightly coupled.
Tight coupling means that changes to one part of the program may have unexpected and
far-reaching effects in other parts, making systems brittle and hard to understand.
However, we have to maintain existing systems designed with complex class hierarchies,
or use frameworks that force us to use inheritance — even multiple inheritance
sometimes.  This chapter illustrates practical uses of multiple inheritance with the
standard library, the Django web framework and the Tkinter GUI toolkit, and gives some
guidance on how to cope with single or multiple inheritance when you must use it.

## The `super()` Function

Consistent use of the [`super()`](https://docs.python.org/3/library/functions.html#super)
built-in function is essential for maintainable object-oriented Python programs.

When a subclass overrides a method of a superclass, the overriding method usually needs
to call the corresponding method of the superclass.  Here's the recommended way to do
it, from an example in the `collections` module documentation (with an improved
docstring):

```python
from collections import OrderedDict

class LastUpdatedOrderedDict(OrderedDict):
    """Store items in the order they were last updated"""

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        self.move_to_end(key)

d = LastUpdatedOrderedDict(a=1, b=2, c=3)
d['a'] = 10
list(d)
# ['b', 'c', 'a']
```

To do its job, `LastUpdatedOrderedDict` overrides `__setitem__()` to:

1. use `super().__setitem__` to call that method on the superclass, to let it insert or
   update the key/value pair;
2. call `self.move_to_end` to ensure the updated key is in the last position.

Invoking an overridden `__init__()` method is particularly important to allow
superclasses to do their part in initializing the instance.

> **Tip**
>
> If you learned object-oriented programming in Java, you may recall that a Java
> constructor method automatically calls the no-argument constructor of the superclass.
> Python doesn't do this.  You must get used to writing this pattern:
>
> ```python
> def __init__(self, a, b) :
>     super().__init__(a, b)
>     ...  # more initialization code
> ```

You may have seen code that doesn't use `super()`, but instead calls the method directly
on the superclass, like this:

```python
class NotRecommended(OrderedDict):
    """This is a counter example!"""

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        self.move_to_end(key)
```

This alternative works in this particular case, but is not recommended for two reasons.
First, it hardcodes the base class.  The name `OrderedDict` appears in the `class`
statement and also inside `__setitem__()`.  If in the future someone changes the `class`
statement to change the base class or add another one, they may forget to update the
body of `__setitem__()`, introducing a bug.

The second reason is that `super` implements logic to handle class hierarchies with
multiple inheritance.  We'll come back to that in
[Multiple Inheritance and Method Resolution Order](#multiple-inheritance-and-method-resolution-order).
To conclude this refresher about `super`, it is useful to review how it had to be called
in Python 2, because the old signature with two arguments is revealing:

```python
class LastUpdatedOrderedDict(OrderedDict):
    """This code works in Python 2 and Python 3"""

    def __setitem__(self, key, value):
        super(LastUpdatedOrderedDict, self).__setitem__(key, value)
        self.move_to_end(key)
```

Both arguments of `super` are now optional.  The Python 3 bytecode compiler automatically
provides them by inspecting the surrounding context when `super()` is invoked in a
method.  The arguments are:

`type`
: The start of the search path for the superclass implementing the desired method.  By
  default, it is the class that owns the method where the `super()` call appears.

`object_or_type`
: The object (for instance method calls) or class (for class method calls) to be the
  receiver of the method call.  By default, it is `self` if the `super()` call happens in
  an instance method.

Whether you or the compiler provides those arguments, the `super()` call returns a
dynamic proxy object that finds a method (such as `__setitem__` in the example) in a
superclass of the `type` parameter, and binds it to the `object_or_type`, so that we
don't need to pass the receiver (`self`) explicitly when invoking the method.

You can still explicitly provide the first and second arguments to `super()`, but they
are needed only in special cases, such as skipping over part of the MRO for testing or
debugging, or for working around undesired behavior in a superclass.

Now let's discuss the caveats when subclassing built-in types.

## Subclassing Built-In Types Is Tricky

It was not possible to subclass built-in types such as `list` or `dict` in the earliest
versions of Python.  Since Python 2.2, it's possible, but there is a major caveat: the
code of the built-ins (written in C) usually does not call methods overridden by
user-defined classes.  A good short description of the problem is in the PyPy
documentation, in the "Differences between PyPy and CPython" section, "Subclasses of
built-in types":

> Officially, CPython has no rule at all for when exactly overridden method of subclasses
> of built-in types get implicitly called or not.  As an approximation, these methods are
> never called by other built-in methods of the same object.  For example, an overridden
> `__getitem__()` in a subclass of `dict` will not be called by e.g. the built-in `get()`
> method.

This example illustrates the problem:

```python
class DoppelDict(dict):
    def __setitem__(self, key, value):
        super().__setitem__(key, [value] * 2)  # duplicate values when storing

dd = DoppelDict(one=1)  # __init__ inherited from dict ignores our __setitem__
dd
# {'one': 1}
dd['two'] = 2  # the [] operator calls our __setitem__ and works as expected
dd
# {'one': 1, 'two': [2, 2]}
dd.update(three=3)  # the update method from dict does not use our __setitem__ either
dd
# {'one': 1, 'two': [2, 2], 'three': 3}
```

`DoppelDict.__setitem__` duplicates values when storing (for no good reason, just to
have a visible effect).  It works by delegating to the superclass.  The `__init__()`
method inherited from `dict` clearly ignored that `__setitem__()` was overridden: the
value of `'one'` is not duplicated.  The `[]` operator calls our `__setitem__()` and works
as expected: `'two'` maps to the duplicated value `[2, 2]`.  The `update` method from
`dict` does not use our version of `__setitem__()` either: the value of `'three'` was not
duplicated.

This built-in behavior is a violation of a basic rule of object-oriented programming:
the search for methods should always start from the class of the receiver (`self`), even
when the call happens inside a method implemented in a superclass.  This is what is
called "late binding", which Alan Kay — of Smalltalk fame — considers a key feature of
object-oriented programming: in any call of the form `x.method()`, the exact method to
be called must be determined at runtime, based on the class of the receiver `x`.  (C++
has the notion of virtual and nonvirtual methods; every method you can write in Python
is late bound like a virtual method, but built-in objects written in C seem to have
nonvirtual methods by default, at least in CPython.)  This sad state of affairs
contributes to the issues we saw in
[Inconsistent Usage of `__missing__` in the Standard Library](dicts-sets.md#inconsistent-usage-of-__missing__-in-the-standard-library).

The problem is not limited to calls within an instance — whether `self.get()` calls
`self.__getitem__()` — but also happens with overridden methods of other classes that
should be called by the built-in methods.  This example is adapted from the PyPy
documentation:

```python
class AnswerDict(dict):
    def __getitem__(self, key):  # always returns 42, no matter what the key
        return 42

ad = AnswerDict(a='foo')
ad['a']
# 42
d = {}
d.update(ad)  # d is a plain dict, which we update with ad
d['a']  # dict.update ignored our AnswerDict.__getitem__
# 'foo'
d
# {'a': 'foo'}
```

> **Warning**
>
> Subclassing built-in types like `dict` or `list` or `str` directly is error-prone
> because the built-in methods mostly ignore user-defined overrides.  Instead of
> subclassing the built-ins, derive your classes from the `collections` module using
> [`UserDict`](https://docs.python.org/3/library/collections.html#collections.UserDict),
> `UserList` and `UserString`, which are designed to be easily extended.

If you subclass `collections.UserDict` instead of `dict`, both issues are fixed:

```python
import collections

class DoppelDict2(collections.UserDict):
    def __setitem__(self, key, value):
        super().__setitem__(key, [value] * 2)

dd = DoppelDict2(one=1)
dd
# {'one': [1, 1]}
dd['two'] = 2
dd
# {'one': [1, 1], 'two': [2, 2]}
dd.update(three=3)
dd
# {'one': [1, 1], 'two': [2, 2], 'three': [3, 3]}

class AnswerDict2(collections.UserDict):
    def __getitem__(self, key):
        return 42

ad = AnswerDict2(a='foo')
ad['a']
# 42
d = {}
d.update(ad)
d['a']
# 42
d
# {'a': 42}
```

As an experiment to measure the extra work required to subclass a built-in, the author
of *Fluent Python* rewrote the `StrKeyDict` class from
[Dictionaries and Sets](dicts-sets.md) to subclass `dict` instead of `UserDict`.  To make
it pass the same suite of tests, he had to implement `__init__()`, `get` and `update`,
because the versions inherited from `dict` refused to cooperate with the overridden
`__missing__()`, `__contains__()` and `__setitem__()`.  The `UserDict` subclass had 16
lines, while the experimental `dict` subclass ended up with 33 lines.

To be clear: this section covered an issue that applies only to method delegation within
the C language code of the built-in types, and only affects classes derived directly from
those types.  If you subclass a base class coded in Python, such as `UserDict` or
`MutableMapping`, you will not be troubled by this.  (In this regard PyPy behaves more
"correctly" than CPython, at the expense of introducing a minor incompatibility.)

Now let's focus on an issue that arises with multiple inheritance: if a class has two
superclasses, how does Python decide which attribute to use when we call `super().attr`,
but both superclasses have an attribute with that name?

## Multiple Inheritance and Method Resolution Order

Any language implementing multiple inheritance needs to deal with potential naming
conflicts when superclasses implement a method by the same name.  This is called the
"diamond problem", because of the shape of the class graph:

```text
        Root
       /    \
      A      B
       \    /
        Leaf
```

Here is code for classes `Leaf`, `A`, `B` and `Root` that form that graph:

```python
class Root:  # Root provides ping, pong and __repr__ to make the output easier to read
    def ping(self):
        print(f'{self}.ping() in Root')

    def pong(self):
        print(f'{self}.pong() in Root')

    def __repr__(self):
        cls_name = type(self).__name__
        return f'<instance of {cls_name}>'

class A(Root):  # the ping and pong methods in class A both call super()
    def ping(self):
        print(f'{self}.ping() in A')
        super().ping()

    def pong(self):
        print(f'{self}.pong() in A')
        super().pong()

class B(Root):  # only the ping method in class B calls super()
    def ping(self):
        print(f'{self}.ping() in B')
        super().ping()

    def pong(self):
        print(f'{self}.pong() in B')

class Leaf(A, B):  # Leaf implements only ping, and it calls super()
    def ping(self):
        print(f'{self}.ping() in Leaf')
        super().ping()
```

Now let's see the effect of calling the `ping` and `pong` methods on an instance of
`Leaf`:

```python
leaf1 = Leaf()
leaf1.ping()
# <instance of Leaf>.ping() in Leaf
# <instance of Leaf>.ping() in A
# <instance of Leaf>.ping() in B
# <instance of Leaf>.ping() in Root
leaf1.pong()
# <instance of Leaf>.pong() in A
# <instance of Leaf>.pong() in B
```

Calling `leaf1.ping()` activates the `ping` methods in `Leaf`, `A`, `B` and `Root`,
because the `ping` methods in the first three classes call `super().ping()`.  Calling
`leaf1.pong()` activates `pong` in `A` via inheritance, which then calls
`super().pong()`, activating `B.pong`.

The activation sequences are determined by two factors:

* the method resolution order of the `Leaf` class;
* the use of `super()` in each method.

Every class has an attribute called `__mro__` holding a tuple of references to the
superclasses in method resolution order, from the current class all the way to the
`object` class.  For the `Leaf` class, this is the `__mro__`:

```python
Leaf.__mro__
# (<class '__main__.Leaf'>, <class '__main__.A'>, <class '__main__.B'>,
#  <class '__main__.Root'>, <class 'object'>)
```

> **Note**
>
> Looking at the diagram, you may think the MRO describes a breadth-first search, but
> that's just a coincidence for that particular class hierarchy.  The MRO is computed by
> a published algorithm called C3.  Its use in Python is detailed in Michele Simionato's
> ["The Python 2.3 Method Resolution Order"](https://docs.python.org/3/howto/mro.html),
> now part of the Python HOWTOs.  It's a challenging read, but Simionato writes: "unless
> you make strong use of multiple inheritance and you have non-trivial hierarchies, you
> don't need to understand the C3 algorithm, and you can easily skip this paper."
> (Classes also have a `.mro()` method, but that's an advanced feature of metaclass
> programming; the content of `__mro__` is what matters during normal usage.)

The MRO only determines the activation order, but whether a particular method will be
activated in each of the classes depends on whether each implementation calls `super()`
or not.

Consider the experiment with the `pong` method.  The `Leaf` class does not override it,
therefore calling `leaf1.pong()` activates the implementation in the next class of
`Leaf.__mro__`: the `A` class.  Method `A.pong` calls `super().pong()`.  The `B` class is
next in the MRO, therefore `B.pong` is activated.  But that method doesn't call
`super().pong()`, so the activation sequence ends here.

The MRO takes into account not only the inheritance graph but also the order in which
superclasses are listed in a subclass declaration.  In other words, if the `Leaf` class
was declared as `Leaf(B, A)`, then class `B` would appear before `A` in `Leaf.__mro__`.
This would affect the activation order of the `ping` methods, and would also cause
`leaf1.pong()` to activate `B.pong` via inheritance, but `A.pong` and `Root.pong` would
never run, because `B.pong` doesn't call `super()`.

When a method calls `super()`, it is a *cooperative method*.  Cooperative methods enable
*cooperative multiple inheritance*.  These terms are intentional: in order to work,
multiple inheritance in Python requires the active cooperation of the methods involved.
In the `B` class, `ping` cooperates, but `pong` does not.

> **Warning**
>
> A noncooperative method can be the cause of subtle bugs.  Many coders reading the
> example above may expect that when method `A.pong` calls `super().pong()`, that will
> ultimately activate `Root.pong`.  But if `B.pong` is activated before, it drops the
> ball.  That's why it is recommended that every method `m` of a nonroot class should
> call `super().m()`.

Cooperative methods must have compatible signatures, because you never know whether
`A.ping` will be called before or after `B.ping`.  The activation sequence depends on the
order of `A` and `B` in the declaration of each subclass that inherits from both.

Python is a dynamic language, so the interaction of `super()` with the MRO is also
dynamic.  Here is a surprising result of this dynamic behavior:

```python
class U():  # U is unrelated to A or Root
    def ping(self):
        print(f'{self}.ping() in U')
        super().ping()  # what does super().ping() do? It depends. Read on.

class LeafUA(U, A):  # LeafUA subclasses U and A in this order
    def ping(self):
        print(f'{self}.ping() in LeafUA')
        super().ping()
```

If you create an instance of `U` and try to call `ping`, you get an error:

```python
u = U()
u.ping()
# Traceback (most recent call last):
#   ...
# AttributeError: 'super' object has no attribute 'ping'
```

The `'super'` object returned by `super()` has no attribute `'ping'` because the MRO of
`U` has two classes: `U` and `object`, and the latter has no attribute named `'ping'`.
(The first line of output, `<__main__.U object at 0x...>.ping() in U`, is printed before
the error.)  However, the `U.ping` method is not completely hopeless.  Check this out:

```python
leaf2 = LeafUA()
leaf2.ping()
# <instance of LeafUA>.ping() in LeafUA
# <instance of LeafUA>.ping() in U
# <instance of LeafUA>.ping() in A
# <instance of LeafUA>.ping() in Root
LeafUA.__mro__
# (<class '__main__.LeafUA'>, <class '__main__.U'>,
#  <class '__main__.A'>, <class '__main__.Root'>, <class 'object'>)
```

The `super().ping()` call in `LeafUA` activates `U.ping`, which cooperates by calling
`super().ping()` too, activating `A.ping`, and eventually `Root.ping`.

Note the base classes of `LeafUA` are `(U, A)` in that order.  If instead the bases were
`(A, U)`, then `leaf2.ping()` would never reach `U.ping`, because the `super().ping()` in
`A.ping` would activate `Root.ping`, and that method does not call `super()`.

In a real program, a class like `U` could be a *mixin class*: a class intended to be used
together with other classes in multiple inheritance, to provide additional
functionality.  We'll study that shortly, in [Mixin Classes](#mixin-classes).

To wrap up this discussion of the MRO, here is part of the complex multiple inheritance
graph of the Tkinter GUI toolkit from the standard library, listed with the help of a
`print_mro` convenience function:

<!-- nocheck -->
```python
def print_mro(cls):
    print(', '.join(c.__name__ for c in cls.__mro__))

import tkinter
print_mro(tkinter.Text)
# Text, Widget, BaseWidget, Misc, Pack, Place, Grid, XView, YView, object
```

The `Text` class implements a full-featured, multiline editable text widget.  It provides
rich functionality in itself, but also inherits many methods from other classes.  Now
let's talk about mixins.

## Mixin Classes

A mixin class is designed to be subclassed together with at least one other class in a
multiple inheritance arrangement.  A mixin is not supposed to be the only base class of
a concrete class, because it does not provide all the functionality for a concrete
object, but only adds or customizes the behavior of child or sibling classes.

> **Note**
>
> Mixin classes are a convention with no explicit language support in Python and C++.
> Ruby allows the explicit definition and use of modules that work as mixins —
> collections of methods that may be included to add functionality to a class.  C#, PHP
> and Rust implement *traits*, which are also an explicit form of mixin.

Let's see a simple but handy example of a mixin class.

### Case-Insensitive Mappings

`UpperCaseMixin` is a class designed to provide case-insensitive access to mappings with
string keys, by uppercasing those keys when they are added or looked up:

```python
import collections

def _upper(key):
    try:
        return key.upper()
    except AttributeError:
        return key

class UpperCaseMixin:
    def __setitem__(self, key, item):
        super().__setitem__(_upper(key), item)

    def __getitem__(self, key):
        return super().__getitem__(_upper(key))

    def get(self, key, default=None):
        return super().get(_upper(key), default)

    def __contains__(self, key):
        return super().__contains__(_upper(key))
```

The helper function `_upper` takes a key of any type, and tries to return `key.upper()`;
if that fails, it returns the key unchanged.  The mixin implements four essential
methods of mappings, always calling `super()`, with the key uppercased, if possible.

Since every method of `UpperCaseMixin` calls `super()`, this mixin depends on a sibling
class that implements or inherits methods with the same signature.  To make its
contribution, a mixin usually needs to appear before other classes in the MRO of a
subclass that uses it.  In practice, that means mixins must appear first in the tuple of
base classes in a class declaration.  Here are two examples:

```python
class UpperDict(UpperCaseMixin, collections.UserDict):
    pass

class UpperCounter(UpperCaseMixin, collections.Counter):
    """Specialized 'Counter' that uppercases string keys"""
```

`UpperDict` needs no implementation of its own, but `UpperCaseMixin` must be the first
base class, otherwise the methods from `UserDict` would be called instead.
`UpperCaseMixin` also works with `Counter`.  Instead of `pass`, it's better to provide a
docstring to satisfy the need for a body in the `class` statement syntax.  Here are some
tests for `UpperDict`:

```python
d = UpperDict([('a', 'letter A'), (2, 'digit two')])
list(d.keys())
# ['A', 2]
d['b'] = 'letter B'
'b' in d
# True
d['a'], d.get('B')
# ('letter A', 'letter B')
list(d.keys())
# ['A', 2, 'B']
```

And a quick demonstration of `UpperCounter`:

```python
c = UpperCounter('BaNanA')
c.most_common()
# [('A', 3), ('N', 2), ('B', 1)]
```

`UpperDict` and `UpperCounter` seem almost magical, but making `UpperCaseMixin` work with
them required carefully studying the code of `UserDict` and `Counter`.

For example, a first version of `UpperCaseMixin` without the `get` method worked with
`UserDict` but not with `Counter`.  The `UserDict` class inherits `get` from
`collections.abc.Mapping`, and that `get` calls `__getitem__()`, which the mixin
implemented.  But keys were not uppercased when an `UpperCounter` was loaded upon
`__init__()`.  That happened because `Counter.__init__` uses `Counter.update`, which in
turn relies on the `get` method inherited from `dict`.  However, the `get` method in the
`dict` class does not call `__getitem__()`.  This is the heart of the issue discussed in
[Subclassing Built-In Types Is Tricky](#subclassing-built-in-types-is-tricky).  It is
also a stark reminder of the brittle and puzzling nature of programs leveraging
inheritance, even at a small scale.

The next section covers several examples of multiple inheritance, often featuring mixin
classes.

## Multiple Inheritance in the Real World

In the *Design Patterns* book, almost all the code is in C++, but the only example of
multiple inheritance is the Adapter pattern.  In Python, multiple inheritance is not the
norm either, but there are important examples.

### ABCs Are Mixins Too

In the standard library, the most visible use of multiple inheritance is the
`collections.abc` package.  That is not controversial: after all, even Java supports
multiple inheritance of interfaces, and ABCs are interface declarations that may
optionally provide concrete method implementations.

Python's official documentation of `collections.abc` uses the term *mixin method* for the
concrete methods implemented in many of the collection ABCs.  The ABCs that provide
mixin methods play two roles: they are interface definitions and also mixin classes.  For
example, the implementation of `collections.UserDict` relies on several of the mixin
methods provided by `collections.abc.MutableMapping`.

### `ThreadingMixIn` and `ForkingMixIn`

The [`http.server`](https://docs.python.org/3/library/http.server.html) package provides
`HTTPServer` and `ThreadingHTTPServer` classes.  The latter's documentation says:

> This class is identical to `HTTPServer` but uses threads to handle requests by using
> the `ThreadingMixIn`.  This is useful to handle web browsers pre-opening sockets, on
> which `HTTPServer` would wait indefinitely.

This is the complete source code for the `ThreadingHTTPServer` class:

<!-- nocheck -->
```python
class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True
```

The source code of `socketserver.ThreadingMixIn` is short.  Here is a summary of its
implementation:

<!-- nocheck -->
```python
class ThreadingMixIn:
    """Mixin class to handle each request in a new thread."""

    # 8 lines omitted

    def process_request_thread(self, request, client_address):
        ... # 6 lines omitted

    def process_request(self, request, client_address):
        ... # 8 lines omitted

    def server_close(self):
        super().server_close()
        self._threads.join()
```

`process_request_thread` does not call `super()` because it is a new method, not an
override; its implementation calls three instance methods that `HTTPServer` provides or
inherits.  `process_request` overrides the method that `HTTPServer` inherits from
`socketserver.BaseServer`, starting a thread and delegating the actual work to
`process_request_thread` running in that thread.  It does not call `super()`.
`server_close` calls `super().server_close()` to stop taking requests, then waits for the
threads started by `process_request` to finish their jobs.

The `ThreadingMixIn` appears in the
[`socketserver`](https://docs.python.org/3/library/socketserver.html) module
documentation next to `ForkingMixIn`.  The latter is designed to support concurrent
servers based on `os.fork()`, an API for launching a child process, available in
POSIX-compliant Unix-like systems.

### Django Generic Views Mixins

> **Note**
>
> You don't need to know Django to follow this section.  It uses a small part of the
> framework as a practical example of multiple inheritance, assuming only some experience
> with server-side web development in any language or framework.

In Django, a *view* is a callable object that takes a `request` argument — an object
representing an HTTP request — and returns an object representing an HTTP response.  The
responses can be as simple as a redirect, with no content body, or as complex as a
catalog page in an online store, rendered from an HTML template and listing multiple
items with buttons for buying, and links to detail pages.

Originally, Django provided a set of functions, called *generic views*, that implemented
some common use cases.  For example, many sites need to show search results that include
information from numerous items, with the listing spanning multiple pages, and for each
item a link to a page with detailed information about it.  In Django, a list view and a
detail view are designed to work together to solve this problem.  However, the original
generic views were functions, so they were not extensible: if you needed to do something
similar but not exactly like a generic list view, you'd have to start from scratch.

The concept of class-based views was introduced in Django 1.3, along with a set of
generic view classes organized as base classes, mixins and ready-to-use concrete
classes.  The base classes and mixins are in the `base` module of the
`django.views.generic` package.  At the top of the hierarchy there are two classes that
take care of very distinct responsibilities: `View` and `TemplateResponseMixin`.

`View` is the base class of all views (it could be an ABC), and it provides core
functionality like the `dispatch` method, which delegates to "handler" methods like
`get`, `head`, `post`, etc., implemented by concrete subclasses to handle the different
HTTP verbs.  The `RedirectView` class inherits only from `View`, and implements `get`,
`head`, `post`, etc.

Concrete subclasses of `View` are supposed to implement the handler methods, so why
aren't those methods part of the `View` interface?  The reason: subclasses are free to
implement just the handlers they want to support.  A `TemplateView` is used only to
display content, so it only implements `get`.  If an HTTP `POST` request is sent to a
`TemplateView`, the inherited `View.dispatch` method checks that there is no `post`
handler, and produces an HTTP 405 Method Not Allowed response.  (This is a dynamic
variation of the Template Method pattern: `dispatch` checks at runtime if a concrete
handler is available for the specific request.)

The `TemplateResponseMixin` provides functionality that is of interest only to views
that need to use a template.  A `RedirectView`, for example, has no content body, so it
has no need of a template and it does not inherit from this mixin.
`TemplateResponseMixin` provides behaviors to `TemplateView` and other
template-rendering views, such as `ListView`, `DetailView`, etc.

For Django users, the most important of these classes is `ListView`, which is an
*aggregate class*, with no code at all (its body is just a docstring).  When
instantiated, a `ListView` has an `object_list` instance attribute through which the
template can iterate to show the page contents, usually the result of a database query
returning multiple objects.  All the functionality related to generating this iterable
of objects comes from the `MultipleObjectMixin`.  That mixin also provides the complex
pagination logic — to display part of the results in one page and links to more pages.

Suppose you want to create a view that will not render a template, but will produce a
list of objects in JSON format.  That's why the `BaseListView` exists.  It provides an
easy-to-use extension point that brings together `View` and `MultipleObjectMixin`
functionality, without the overhead of the template machinery.

The Django class-based views API is a better example of multiple inheritance than
Tkinter.  In particular, it is easy to make sense of its mixin classes: each has a
well-defined purpose, and they are all named with the `...Mixin` suffix.  (The
[Classy Class-Based Views](https://ccbv.co.uk/) website is a great resource to study
them.)

Class-based views were not universally embraced by Django users.  Many use them in a
limited way, as opaque boxes, but when it's necessary to create something new, a lot of
Django coders continue writing monolithic view functions that take care of all those
responsibilities, instead of trying to reuse the base views and mixins.  It does take
some time to learn how to leverage class-based views, but they eliminate a lot of
boilerplate code, make it easier to reuse solutions, and even improve team communication
— for example, by defining standard names for templates, and for the variables passed to
template contexts.  Class-based views are Django views "on rails".

### Multiple Inheritance in Tkinter

An extreme example of multiple inheritance in Python's standard library is the Tkinter
GUI toolkit.  Tkinter is decades old, and it is not an example of current best practices.
But it shows how multiple inheritance was used when coders did not appreciate its
drawbacks, and it will serve as a counterexample when we cover some good practices in the
next section.  Consider these classes:

* `Toplevel`: the class of a top-level window in a Tkinter application;
* `Widget`: the superclass of every visible object that can be placed on a window;
* `Button`: a plain button widget;
* `Entry`: a single-line editable text field;
* `Text`: a multiline editable text field.

Here are the MROs of those classes, displayed by the `print_mro` function:

<!-- nocheck -->
```python
import tkinter
print_mro(tkinter.Toplevel)
# Toplevel, BaseWidget, Misc, Wm, object
print_mro(tkinter.Widget)
# Widget, BaseWidget, Misc, Pack, Place, Grid, object
print_mro(tkinter.Button)
# Button, Widget, BaseWidget, Misc, Pack, Place, Grid, object
print_mro(tkinter.Entry)
# Entry, Widget, BaseWidget, Misc, Pack, Place, Grid, XView, object
print_mro(tkinter.Text)
# Text, Widget, BaseWidget, Misc, Pack, Place, Grid, XView, YView, object
```

> **Note**
>
> By current standards, the class hierarchy of Tkinter is very deep.  Few parts of the
> Python standard library have more than three or four levels of concrete classes, and
> the same can be said of the Java class library.  However, some of the deepest
> hierarchies in the Java class library are precisely in the packages related to GUI
> programming: `java.awt` and `javax.swing`.  GUI toolkits are where inheritance is most
> useful.

Note how these classes relate to others:

* `Toplevel` is the only graphical class that does not inherit from `Widget`, because it
  is the top-level window and does not behave like a widget; for example, it cannot be
  attached to a window or frame.  `Toplevel` inherits from `Wm`, which provides direct
  access functions of the host window manager, like setting the window title and
  configuring its borders.
* `Widget` inherits directly from `BaseWidget` and from `Pack`, `Place` and `Grid`.  These
  last three classes are *geometry managers*: they are responsible for arranging widgets
  inside a window or frame.  Each encapsulates a different layout strategy and widget
  placement API.
* `Button`, like most widgets, descends only from `Widget`, but indirectly from `Misc`,
  which provides dozens of methods to every widget.
* `Entry` subclasses `Widget` and `XView`, which supports horizontal scrolling.
* `Text` subclasses `Widget`, `XView` and `YView` for vertical scrolling.

We'll now discuss some good practices of multiple inheritance and see whether Tkinter
goes along with them.

## Coping with Inheritance

What Alan Kay wrote in the epigraph remains true: there's still no general theory about
inheritance that can guide practicing programmers.  What we have are rules of thumb,
design patterns, "best practices", clever acronyms, taboos, etc.  Some of these provide
useful guidelines, but none of them are universally accepted or always applicable.

It's easy to create incomprehensible and brittle designs using inheritance, even without
multiple inheritance.  Because we don't have a comprehensive theory, here are a few tips
to avoid spaghetti class graphs.

### Favor Object Composition over Class Inheritance

The title of this subsection is the second principle of object-oriented design from the
*Design Patterns* book, and is the best advice available here.  Once you get comfortable
with inheritance, it's too easy to overuse it.  Placing objects in a neat hierarchy
appeals to our sense of order; programmers do it just for fun.

Favoring composition leads to more flexible designs.  For example, in the case of the
`tkinter.Widget` class, instead of inheriting the methods from all geometry managers,
widget instances could hold a reference to a geometry manager, and invoke its methods.
After all, a `Widget` should not "be" a geometry manager, but could use the services of
one via delegation.  Then you could add a new geometry manager without touching the
widget class hierarchy and without worrying about name clashes.  Even with single
inheritance, this principle enhances flexibility, because subclassing is a form of tight
coupling, and tall inheritance trees tend to be brittle.

Here is the difference in miniature.  Instead of making a stack *be* a list (and inherit
`insert`, `sort`, `__setitem__()` and dozens of other methods that a stack should not
have), make it *have* a list:

```python
class Stack:
    def __init__(self, items=()):
        self._items = list(items)  # composition: a Stack has a list

    def push(self, item):
        self._items.append(item)  # delegation

    def pop(self):
        return self._items.pop()

    def __len__(self):
        return len(self._items)

s = Stack([1, 2])
s.push(3)
s.pop(), len(s)
# (3, 2)
```

Composition and delegation can replace the use of mixins to make behaviors available to
different classes, but cannot replace the use of interface inheritance to define a
hierarchy of types.

### Understand Why Inheritance Is Used in Each Case

When dealing with multiple inheritance, it's useful to keep straight the reasons why
subclassing is done in each particular case.  The main reasons are:

* *Inheritance of interface* creates a subtype, implying an "is-a" relationship.  This is
  best done with ABCs.
* *Inheritance of implementation* avoids code duplication by reuse.  Mixins can help with
  this.

In practice, both uses are often simultaneous, but whenever you can make the intent
clear, do it.  Inheritance for code reuse is an implementation detail, and it can often be
replaced by composition and delegation.  On the other hand, interface inheritance is the
backbone of a framework.  Interface inheritance should use only ABCs as base classes, if
possible.

### Make Interfaces Explicit with ABCs

In modern Python, if a class is intended to define an interface, it should be an explicit
ABC or a `typing.Protocol` subclass (see [Interfaces, Protocols, and ABCs](protocols-abcs.md)).
An ABC should subclass only `abc.ABC` or other ABCs.  Multiple inheritance of ABCs is not
problematic.

### Use Explicit Mixins for Code Reuse

If a class is designed to provide method implementations for reuse by multiple unrelated
subclasses, without implying an "is-a" relationship, it should be an explicit mixin
class.  Conceptually, a mixin does not define a new type; it merely bundles methods for
reuse.  A mixin should never be instantiated, and concrete classes should not inherit
only from a mixin.  Each mixin should provide a single specific behavior, implementing
few and very closely related methods.  Mixins should avoid keeping any internal state;
i.e., a mixin class should not have instance attributes.

There is no formal way in Python to state that a class is a mixin, so it is highly
recommended that they are named with a `Mixin` suffix.

### Provide Aggregate Classes to Users

> A class that is constructed primarily by inheriting from mixins and does not add its
> own structure or behavior is called an *aggregate class*.
>
> — Booch et al., *Object-Oriented Analysis and Design with Applications*

If some combination of ABCs or mixins is particularly useful to client code, provide a
class that brings them together in a sensible way.  For example, here is the complete
source code for the Django `ListView` class:

<!-- nocheck -->
```python
class ListView(MultipleObjectTemplateResponseMixin, BaseListView):
    """
    Render some list of objects, set by `self.model` or `self.queryset`.
    `self.queryset` can actually be any iterable of items, not just a queryset.
    """
```

The body of `ListView` is empty, but the class provides a useful service: it brings
together a mixin and a base class that should be used together.

Another example is `tkinter.Widget`, which has four base classes and no methods or
attributes of its own — just a docstring.  Thanks to the `Widget` aggregate class, we can
create a new widget with the required mixins, without having to figure out in which order
they should be declared to work as intended.  Note that aggregate classes don't have to
be completely empty, but they often are.

### Subclass Only Classes Designed for Subclassing

> **Warning**
>
> Subclassing any complex class and overriding its methods is error-prone because the
> superclass methods may ignore the subclass overrides in unexpected ways.  As much as
> possible, avoid overriding methods, or at least restrain yourself to subclassing
> classes which are designed to be easily extended, and only in the ways in which they
> were designed to be extended.

That's great advice, but how do we know whether or how a class was designed to be
extended?

The first answer is documentation (sometimes in the form of docstrings or even comments
in code).  For example, Python's `socketserver` package is described as "a framework for
network servers".  Its `BaseServer` class is designed for subclassing, as the name
suggests.  More importantly, the documentation and the docstring in the source code of
the class explicitly note which of its methods are intended to be overridden by
subclasses.

A second answer comes from the `typing` module.
[**PEP 591**](https://peps.python.org/pep-0591/) introduced a
[`@final`](https://docs.python.org/3/library/typing.html#typing.final) decorator that can
be applied to classes or individual methods, so that IDEs or type checkers can report
misguided attempts to subclass those classes or override those methods (PEP 591 also
introduces a `Final` annotation for variables or attributes that should not be reassigned
or overridden).  The converse is
[`@override`](https://docs.python.org/3/library/typing.html#typing.override)
([**PEP 698**](https://peps.python.org/pep-0698/), Python 3.12), which marks a method as
*intended* to override a superclass method, so the type checker can complain if the
superclass method is renamed or removed and the "override" silently becomes a brand-new
method:

```python
from typing import final, override

class Base:
    @final
    def must_not_override(self) -> None: ...

    def hook(self) -> None: ...

class Derived(Base):
    @override
    def hook(self) -> None:  # OK: Base.hook exists
        ...
```

Like other type hints, these decorators have no effect at runtime (apart from setting a
`__final__` or `__override__` attribute on the decorated object).

### Avoid Subclassing from Concrete Classes

Subclassing concrete classes is more dangerous than subclassing ABCs and mixins, because
instances of concrete classes usually have internal state that can easily be corrupted
when you override methods that depend on that state.  Even if your methods cooperate by
calling `super()`, and the internal state is held in private attributes using the `__x`
syntax (see [Private Variables](classes.md#tut-private)), there are still countless ways a
method override can introduce bugs.

Scott Meyers' *More Effective C++* says: "all non-leaf classes should be abstract."  In
other words, only abstract classes should be subclassed.  If you must use subclassing for
code reuse, then the code intended for reuse should be in mixin methods of ABCs or in
explicitly named mixin classes.

We will now analyze Tkinter from the point of view of these recommendations.

### Tkinter: The Good, the Bad, and the Ugly

Most advice in the previous section is not followed by Tkinter, with the notable
exception of [Provide Aggregate Classes to Users](#provide-aggregate-classes-to-users).
Even then, it's not a great example, because composition would probably work better for
integrating the geometry managers into `Widget`, as discussed in
[Favor Object Composition over Class Inheritance](#favor-object-composition-over-class-inheritance).

Keep in mind that Tkinter has been part of the standard library since Python 1.1 was
released in 1994.  Tkinter is a layer on top of the excellent Tk GUI toolkit of the Tcl
language.  The Tcl/Tk combo is not originally object-oriented, so the Tk API is basically
a vast catalog of functions.  However, the toolkit is object-oriented in its design, if
not in its original Tcl implementation.

The docstring of `tkinter.Widget` starts with the words "Internal class."  This suggests
that `Widget` should probably be an ABC.  Although `Widget` has no methods of its own, it
does define an interface.  Its message is: "You can count on every Tkinter widget
providing basic widget methods (`__init__`, `destroy` and dozens of Tk API functions), in
addition to the methods of all three geometry managers."  This is not a great interface
definition (it's just too broad), but it is an interface, and `Widget` "defines" it as the
union of the interfaces of its superclasses.

The `Tk` class, which encapsulates the GUI application logic, inherits from `Wm` and
`Misc`, neither of which are abstract or mixin (`Wm` is not a proper mixin because
`Toplevel` subclasses only from it).  The name of the `Misc` class is — by itself — a very
strong code smell.  `Misc` has more than 100 methods, and all widgets inherit from it.
Why is it necessary that every single widget has methods for clipboard handling, text
selection, timer management and the like?  You can't really paste into a button or
select text from a scrollbar.  `Misc` should be split into several specialized mixin
classes, and not all widgets should inherit from every one of those mixins.

To be fair, as a Tkinter user, you don't need to know or use multiple inheritance at all.
It's an implementation detail hidden behind the widget classes that you will instantiate
or subclass in your own code.  But you will suffer the consequences of excessive multiple
inheritance when you type `dir(tkinter.Button)` and try to find the method you need among
the more than 200 attributes listed.  And you'll need to face the complexity if you decide
to implement a new Tk widget.

> **Tip**
>
> Despite the problems, Tkinter is stable, flexible, and provides a modern look-and-feel
> if you use the `tkinter.ttk` package and its themed widgets.  Also, some of the original
> widgets, like `Canvas` and `Text`, are incredibly powerful.  You can turn a `Canvas`
> object into a simple drag-and-drop drawing application in a matter of hours.  Tkinter
> and Tcl/Tk are definitely worth a look if you are interested in GUI programming.

This concludes our tour through the labyrinth of inheritance.

## Summary

This chapter started with a review of the `super()` function in the context of single
inheritance.  We then discussed the problem with subclassing built-in types: their native
methods implemented in C do not call overridden methods in subclasses, except in very few
special cases.  That's why, when we need a custom `list`, `dict` or `str` type, it's
easier to subclass `UserList`, `UserDict` or `UserString` — all defined in the
`collections` module, which actually wrap the corresponding built-in types and delegate
operations to them: three examples of favoring composition over inheritance in the
standard library.  If the desired behavior is very different from what the built-ins
offer, it may be easier to subclass the appropriate ABC from `collections.abc` and write
your own implementation.

The rest of the chapter was devoted to the double-edged sword of multiple inheritance.
First we saw how the method resolution order, encoded in the `__mro__` class attribute,
addresses the problem of potential naming conflicts in inherited methods.  We also saw
how the `super()` built-in behaves, sometimes unexpectedly, in hierarchies with multiple
inheritance.  The behavior of `super()` is designed to support mixin classes, which we
then studied through the simple example of the `UpperCaseMixin` for case-insensitive
mappings.

We saw how multiple inheritance and mixin methods are used in Python's ABCs, as well as
in the `socketserver` threading and forking mixins.  More complex uses of multiple
inheritance were exemplified by Django's class-based views and the Tkinter GUI toolkit.
Although Tkinter is not an example of modern best practices, it is an example of overly
complex class hierarchies we may find in legacy systems.  To close the chapter, we went
through seven recommendations to cope with inheritance, and applied some of that advice
in a commentary of the Tkinter class hierarchy.

Rejecting inheritance — even single inheritance — is a modern trend.  One of the most
successful languages created in the 21st century is Go.  It doesn't have a construct
called "class", but you can build types that are structs of encapsulated fields and you
can attach methods to those structs.  Go allows the definition of interfaces that are
checked by the compiler using structural typing, a.k.a. static duck typing — very similar
to what we now have with protocol types in Python.  Go has special syntax for building
types and interfaces by composition, but it does not support inheritance — not even among
interfaces.

So perhaps the best advice about inheritance is: avoid it if you can.  But often, we
don't have a choice: the frameworks we use impose their own design choices.

> **Note**
>
> The vast majority of programmers write applications, not frameworks.  When we write
> applications, we normally don't need to code class hierarchies.  At most, we write
> classes that subclass from ABCs or other classes provided by the framework.  It's very
> rare that we need to write a class that will act as the superclass of another: the
> classes we code are almost always leaf classes.  If, while working as an application
> developer, you find yourself building multilevel class hierarchies, it's likely that you
> are reinventing the wheel (look for a library), using a badly designed framework (look
> for an alternative), or overengineering (remember the KISS principle).

> **See also**
>
> * Hynek Schlawack, ["Subclassing in Python Redux"](https://hynek.me/articles/python-subclassing-redux/):
>   "When it comes to reading clarity, properly-done composition is superior to
>   inheritance … Don't forget that more often than not, a function is all you need."
> * Raymond Hettinger, ["Python's super() considered super!"](https://rhettinger.wordpress.com/2011/05/26/super-considered-super/),
>   which explains the workings of `super` and multiple inheritance from a positive
>   perspective.
> * Guido van Rossum, ["Unifying types and classes in Python 2.2"](https://www.python.org/download/releases/2.2.3/descrintro/),
>   where subclassing built-ins, `super`, descriptors and metaclasses were all introduced.
> * Michele Simionato, ["The Python 2.3 Method Resolution Order"](https://docs.python.org/3/howto/mro.html).
> * Brandon Rhodes, ["The Composition Over Inheritance Principle"](https://python-patterns.guide/gang-of-four/composition-over-inheritance/),
>   part of his *Python Design Patterns* guide.
> * Chapter 8 of the *Python Cookbook*, 3rd ed., by David Beazley and Brian K. Jones,
>   starting from "Calling a Method on a Parent Class".
