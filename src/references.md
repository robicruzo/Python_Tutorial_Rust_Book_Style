# Object References, Mutability, and Recycling

In *Through the Looking-Glass*, the White Knight tells Alice that the *name* of
his song is called "Haddocks' Eyes", but that the name really *is* "The Aged Aged
Man", and that the song itself is something else again.  That scene sets the
tone of this chapter, whose theme is the distinction between objects and their
names.  A name is not the object; a name is a separate thing.

We start with a metaphor for variables in Python: variables are labels, not
boxes.  If reference variables are old news to you, the analogy may still be
handy when you need to explain aliasing issues to others.  Then we discuss
object identity, value and aliasing.  A surprising trait of tuples is revealed:
they are immutable, but their values may change.  This leads to a discussion of
shallow and deep copies.  References and function parameters come next: the
problem with mutable parameter defaults and the safe handling of mutable
arguments passed by clients of our functions.  The last sections cover garbage
collection, the `del` statement, weak references, and a few tricks Python plays
with immutable objects.

This is a rather dry chapter, but its topics lie at the heart of many subtle bugs
in real Python programs.  It complements the discussion of names and objects in
[A Word About Names and Objects](classes.md#tut-object) and
[Python Scopes and Namespaces](classes.md#tut-scopes).

## Variables Are Not Boxes

The usual "variables as boxes" metaphor actually hinders the understanding of
reference variables in object-oriented languages.  Python variables are like
reference variables in Java; a better metaphor is to think of variables as
labels with names attached to objects.  Here is a simple interaction that the
"variables as boxes" idea cannot explain:

```python
a = [1, 2, 3]  # create a list and bind the variable a to it
b = a          # bind b to the same value that a is referencing
a.append(4)    # modify the list referenced by a
b              # the effect is visible through b
# [1, 2, 3, 4]
```

If you think of `b` as a box that stored a copy of the `[1, 2, 3]` from the `a`
box, this behavior makes no sense.  The `b = a` statement does not copy the
contents of box `a` into box `b`.  It attaches the label `b` to the object that
already has the label `a`.  Think of sticky notes, not boxes.

With reference variables, it makes much more sense to say that the variable is
assigned to an object, and not the other way around: "variable `s` is assigned
to the seesaw", never "the seesaw is assigned to variable `s`".  After all, the
object is created before the assignment.  Because the verb "to assign" is used
in contradictory ways, a useful alternative is "to bind": Python's assignment
statement `x = ...` binds the name `x` to the object created or referenced on the
right-hand side.  And the object must exist before a name can be bound to it, as
this example proves:

```python
class Gizmo:
    def __init__(self):
        print(f'Gizmo id: {id(self)}')

x = Gizmo()
# Gizmo id: 4301489152
y = Gizmo() * 10
# Gizmo id: 4301489432
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# TypeError: unsupported operand type(s) for *: 'Gizmo' and 'int'
'y' in globals()
# False
```

The output `Gizmo id: ...` is a side effect of creating a `Gizmo` instance.
Multiplying a `Gizmo` raises an exception, but the second `Gizmo id` line proves
that a second instance was created before the multiplication was attempted.
The variable `y` was never created, because the exception happened while the
right-hand side of the assignment was being evaluated.

> **Tip**
>
> To understand an assignment in Python, read the right-hand side first: that's
> where the object is created or retrieved.  After that, the variable on the left
> is bound to the object, like a label stuck to it.  Just forget about the boxes.

Because variables are mere labels, nothing prevents an object from having several
labels attached to it.  When that happens, you have *aliasing*.

## Identity, Equality, and Aliases

Lewis Carroll is the pen name of Prof. Charles Lutwidge Dodgson.  Mr. Carroll is
not only equal to Prof. Dodgson; they are one and the same:

```python
charles = {'name': 'Charles L. Dodgson', 'born': 1832}
lewis = charles  # lewis is an alias for charles
lewis is charles
# True
id(charles), id(lewis)  # the is operator and the id function confirm it
# (4300473992, 4300473992)
lewis['balance'] = 950  # adding an item to lewis is the same as adding it to charles
charles
# {'name': 'Charles L. Dodgson', 'born': 1832, 'balance': 950}
```

Now suppose an impostor, let's call him Dr. Alexander Pedachenko, claims he is
Charles L. Dodgson, born in 1832.  His credentials may be the same, but
Dr. Pedachenko is not Prof. Dodgson:

```python
alex = {'name': 'Charles L. Dodgson', 'born': 1832, 'balance': 950}
alex == charles  # the objects compare equal, because of dict.__eq__
# True
alex is not charles  # but they are distinct objects
# True
```

`alex` refers to an object that is a replica of the object bound to `charles`.
The objects compare equal, but they are distinct; `a is not b` is the Pythonic
way of writing a negative identity comparison.

`lewis` and `charles` are aliases: two variables bound to the same object.  `alex`,
on the other hand, is not an alias for `charles`: the two are bound to distinct
objects that happen to have the same value (that's what `==` compares) but
different identities.

The [Objects, values and types](https://docs.python.org/3/reference/datamodel.html#objects-values-and-types)
section of the language reference states that an object's identity never changes
once it has been created; you may think of it as the object's address in memory.
The `is` operator compares the identity of two objects, and the `id()` function
returns an integer representing its identity.

The real meaning of an object's id is implementation dependent.  In CPython,
`id()` returns the memory address of the object, but it may be something else in
another Python interpreter.  The key point is that the id is guaranteed to be a
unique integer label, and it will never change during the life of the object.

In practice you rarely call `id()` while programming.  Identity checks are most
often done with the `is` operator, which compares object ids.  The most frequent
use of `id()` is while debugging, when the `repr()` of two objects look alike but
you need to know whether two references are aliases or point to separate objects.

### Choosing Between `==` and `is`

The `==` operator compares the values of objects (the data they hold), while `is`
compares their identities.  While programming, we usually care more about values
than identities, so `==` appears far more often than `is` in Python code.

However, if you are comparing a variable to a singleton, it makes sense to use
`is`.  By far the most common case is checking whether a variable is bound to
`None`.  This is the recommended way to do it:

<!-- nocheck -->
```python
x is None
```

and the proper way to write its negation is:

<!-- nocheck -->
```python
x is not None
```

*Sentinel objects* are another example of singletons you test with `is`.  Here is
one way to create and test a sentinel:

<!-- nocheck -->
```python
END_OF_DATA = object()
# ... many lines
def traverse(...):
    # ... more lines
    if node is END_OF_DATA:
        return
    # etc.
```

The `is` operator is faster than `==`, because it cannot be overloaded, so Python
does not have to find and invoke special methods to evaluate it: computing `is` is
as simple as comparing two integer ids.  In contrast, `a == b` is syntactic sugar
for `a.__eq__(b)`.  The `__eq__()` method inherited from `object` compares object
ids, so it produces the same result as `is`, but most built-in types override
`__eq__()` with more meaningful implementations that take into account the values
of the object attributes.  Equality may involve a lot of processing, for example
when comparing large collections or deeply nested structures.

> **Warning**
>
> Usually we are more interested in object equality than identity.  Checking for
> `None` is the only common use case for the `is` operator, and most other uses
> are wrong.  If you are not sure, use `==`.  It's usually what you want, and it
> also works with `None`, albeit not as fast.

### The Relative Immutability of Tuples

Tuples, like most Python collections (lists, dicts, sets, etc.), are *containers*:
they hold references to objects.  (Flat sequences like `str`, `bytes` and
`array.array` don't contain references; they hold their contents directly in
contiguous memory.)  If the referenced items are mutable, they may change even if
the tuple itself does not.  In other words, the immutability of tuples really
refers to the physical contents of the tuple data structure (the references it
holds), and does not extend to the referenced objects.

What can never change in a tuple is the identity of the items it contains:

```python
t1 = (1, 2, [30, 40])  # t1 is immutable, but t1[-1] is mutable
t2 = (1, 2, [30, 40])  # a tuple whose items are equal to those of t1
t1 == t2  # distinct objects, but equal, as expected
# True
id(t1[-1])
# 4302515784
t1[-1].append(99)  # modify the t1[-1] list in place
t1
# (1, 2, [30, 40, 99])
id(t1[-1])  # the identity of t1[-1] has not changed, only its value
# 4302515784
t1 == t2  # t1 and t2 are now different
# False
```

This relative immutability of tuples is behind the riddle in
[A `+=` Assignment Puzzler](sequences.md#a--assignment-puzzler).  It is also the
reason why some tuples are unhashable, as explained in
[What Is Hashable](dicts-sets.md#what-is-hashable).

The distinction between equality and identity has further implications when you
need to copy an object.  A copy is an equal object with a different id.  But if an
object contains other objects, should the copy also duplicate the inner objects,
or is it OK to share them?  There's no single answer.

## Copies Are Shallow by Default

The easiest way to copy a list (or most built-in mutable collections) is to use
the built-in constructor for the type itself:

```python
l1 = [3, [55, 44], (7, 8, 9)]
l2 = list(l1)  # list(l1) creates a copy of l1
l2
# [3, [55, 44], (7, 8, 9)]
l2 == l1  # the copies are equal...
# True
l2 is l1  # ...but refer to two different objects
# False
```

For lists and other mutable sequences, the shortcut `l2 = l1[:]` also makes a
copy.  However, using the constructor or `[:]` produces a *shallow copy*: the
outermost container is duplicated, but the copy is filled with references to the
same items held by the original container.  This saves memory and causes no
problems if all the items are immutable.  But if there are mutable items, this may
lead to unpleasant surprises.

The next script creates a shallow copy of a list containing another list and a
tuple, and then makes changes to see how they affect the referenced objects.  (If
you can, paste it into the [Online Python Tutor](https://pythontutor.com) to see it
animated; it is an excellent tool for visualizing how Python works.)

```python
l1 = [3, [66, 55, 44], (7, 8, 9)]
l2 = list(l1)
l1.append(100)
l1[1].remove(55)
print('l1:', l1)
print('l2:', l2)
l2[1] += [33, 22]
l2[2] += (10, 11)
print('l1:', l1)
print('l2:', l2)
```

The output is:

```text
l1: [3, [66, 44], (7, 8, 9), 100]
l2: [3, [66, 44], (7, 8, 9)]
l1: [3, [66, 44, 33, 22], (7, 8, 9), 100]
l2: [3, [66, 44, 33, 22], (7, 8, 9, 10, 11)]
```

Step by step:

1. `l2` is a shallow copy of `l1`.  The two variables refer to distinct lists, but
   the lists share references to the same inner list object `[66, 55, 44]` and
   tuple `(7, 8, 9)`.
2. Appending `100` to `l1` has no effect on `l2`.
3. Removing `55` from the inner list `l1[1]` affects `l2`, because `l2[1]` is bound to
   the same list as `l1[1]`.
4. For a mutable object like the list referred to by `l2[1]`, the operator `+=`
   changes the list in place.  The change is visible at `l1[1]`, which is an alias
   for `l2[1]`.
5. `+=` on a tuple creates a new tuple and rebinds the variable `l2[2]`.  This is
   the same as `l2[2] = l2[2] + (10, 11)`.  Now the tuples in the last position of
   `l1` and `l2` are no longer the same object.

At the end, `l1` and `l2` still share references to the same list object, now
containing `[66, 44, 33, 22]`, but `l2[2] += (10, 11)` created a new tuple with
content `(7, 8, 9, 10, 11)`, unrelated to the tuple `(7, 8, 9)` referenced by
`l1[2]`.  Shallow copies are easy to make, but they may or may not be what you
want.

### Deep and Shallow Copies of Arbitrary Objects

Working with shallow copies is not always a problem, but sometimes you need to
make *deep copies*: duplicates that do not share references of embedded objects.
The [`copy`](https://docs.python.org/3/library/copy.html) module provides the
`deepcopy` and `copy` functions that return deep and shallow copies of arbitrary
objects.

To illustrate them, here is a simple class, `Bus`, representing a school bus that
is loaded with passengers and then picks up or drops off passengers on its route:

```python
class Bus:

    def __init__(self, passengers=None):
        if passengers is None:
            self.passengers = []
        else:
            self.passengers = list(passengers)

    def pick(self, name):
        self.passengers.append(name)

    def drop(self, name):
        self.passengers.remove(name)
```

Now let's create a `Bus` object (`bus1`) and two clones, a shallow copy (`bus2`)
and a deep copy (`bus3`), to see what happens as `bus1` drops off a student:

```python
import copy
bus1 = Bus(['Alice', 'Bill', 'Claire', 'David'])
bus2 = copy.copy(bus1)
bus3 = copy.deepcopy(bus1)
id(bus1), id(bus2), id(bus3)  # three distinct Bus instances
# (4301498296, 4301499416, 4301499752)
bus1.drop('Bill')
bus2.passengers  # after bus1 drops 'Bill', he is also missing from bus2
# ['Alice', 'Claire', 'David']
id(bus1.passengers), id(bus2.passengers), id(bus3.passengers)
# (4302658568, 4302658568, 4302657800)
bus3.passengers
# ['Alice', 'Bill', 'Claire', 'David']
```

Inspecting the `passengers` attributes shows that `bus1` and `bus2` share the same
list object, because `bus2` is a shallow copy of `bus1`.  `bus3` is a deep copy of
`bus1`, so its `passengers` attribute refers to another list.

Making deep copies is not a simple matter in the general case.  Objects may have
cyclic references that would cause a naïve algorithm to enter an infinite loop.
The `deepcopy` function remembers the objects already copied, to handle cyclic
references gracefully:

```python
a = [10, 20]
b = [a, 30]
a.append(b)  # b refers to a, and then is appended to a
a
# [10, 20, [[...], 30]]
from copy import deepcopy
c = deepcopy(a)  # deepcopy still manages to copy a
c
# [10, 20, [[...], 30]]
```

Also, a deep copy may be too deep in some cases.  For example, objects may refer
to external resources or singletons that should not be copied.  You can control
the behavior of both `copy` and `deepcopy` by implementing the `__copy__()` and
`__deepcopy__()` special methods, as described in the `copy` module documentation:

```python
class Session:
    def __init__(self, user, connection):
        self.user = user
        self.connection = connection  # an external resource, never copied
        self.history = []

    def __deepcopy__(self, memo):
        clone = Session(copy.deepcopy(self.user, memo), self.connection)
        clone.history = copy.deepcopy(self.history, memo)
        return clone

conn = object()  # pretend this is a database connection
s1 = Session({'name': 'ana'}, conn)
s2 = copy.deepcopy(s1)
s2.user is s1.user, s2.connection is s1.connection
# (False, True)
```

The `memo` dictionary is how `deepcopy` keeps track of objects already copied;
pass it along when you deep-copy parts of your object.

The sharing of objects through aliases also explains how parameter passing works
in Python, and the problem of using mutable types as parameter defaults.

## Function Parameters as References

The only mode of parameter passing in Python is *call by sharing*.  That is the
same mode used in most object-oriented languages, including JavaScript, Ruby and
Java (for Java reference types; primitive types use call by value).  Call by
sharing means that each formal parameter of the function gets a copy of each
reference in the arguments.  In other words, the parameters inside the function
become aliases of the actual arguments.

The result is that a function may change any mutable object passed as a
parameter, but it cannot change the identity of those objects (it cannot replace
an object with another as far as the caller is concerned).  Here is a simple
function using `+=` on one of its parameters.  As we pass numbers, lists and tuples
to it, the actual arguments are affected in different ways:

```python
def f(a, b):
    a += b
    return a

x = 1
y = 2
f(x, y)
# 3
x, y  # the number x is unchanged
# (1, 2)
a = [1, 2]
b = [3, 4]
f(a, b)
# [1, 2, 3, 4]
a, b  # the list a is changed
# ([1, 2, 3, 4], [3, 4])
t = (10, 20)
u = (30, 40)
f(t, u)
# (10, 20, 30, 40)
t, u  # the tuple t is unchanged
# ((10, 20), (30, 40))
```

> **Note**
>
> A popular way of explaining this is: "parameters are passed by value, but the
> values are references".  That's not wrong, but it causes confusion, because the
> most common modes in older languages are call by value (the function gets a copy
> of the argument) and call by reference (the function gets a pointer to the
> argument).  In Python the function gets a copy of the arguments, but the
> arguments are always references.  So the referenced objects may be changed, if
> they are mutable, but their identity cannot; and because the function gets a
> copy of the reference, rebinding the parameter in the function body has no
> effect outside of the function.

### Mutable Types as Parameter Defaults: Bad Idea

Optional parameters with default values are a great feature of Python function
definitions, allowing interfaces to evolve while remaining backward compatible.
However, you should avoid mutable objects as default values for parameters.  The
tutorial already warned about this in [Default Argument Values](controlflow.md#tut-defaultargs);
here is a closer look.

Let's take the `Bus` class and change its `__init__()` to create `HauntedBus`.  Here
we try to be clever: instead of a default value of `passengers=None`, we use
`passengers=[]`, avoiding the `if` in the previous `__init__()`.  This "cleverness"
gets us into trouble:

```python
class HauntedBus:
    """A bus model haunted by ghost passengers"""

    def __init__(self, passengers=[]):
        self.passengers = passengers

    def pick(self, name):
        self.passengers.append(name)

    def drop(self, name):
        self.passengers.remove(name)
```

When the `passengers` argument is not passed, the parameter is bound to the
default list object, which is initially empty.  The assignment makes
`self.passengers` an alias for `passengers`, which is itself an alias for the
default list.  When `.remove()` and `.append()` are used with `self.passengers`,
we are actually mutating the default list, which is an attribute of the function
object.  Here is the eerie behavior of `HauntedBus`:

```python
bus1 = HauntedBus(['Alice', 'Bill'])  # bus1 starts with a two-passenger list
bus1.passengers
# ['Alice', 'Bill']
bus1.pick('Charlie')
bus1.drop('Alice')
bus1.passengers  # so far, so good: no surprises with bus1
# ['Bill', 'Charlie']
bus2 = HauntedBus()  # bus2 starts empty, so the default list is assigned
bus2.pick('Carrie')
bus2.passengers
# ['Carrie']
bus3 = HauntedBus()  # bus3 also starts empty: again the default list
bus3.passengers  # the default is no longer empty!
# ['Carrie']
bus3.pick('Dave')
bus2.passengers  # now Dave, picked by bus3, appears in bus2
# ['Carrie', 'Dave']
bus2.passengers is bus3.passengers  # they refer to the same list
# True
bus1.passengers  # but bus1.passengers is a distinct list
# ['Bill', 'Charlie']
```

`HauntedBus` instances that don't get an initial passenger list end up sharing the
same passenger list among themselves.  Such bugs may be subtle: when a
`HauntedBus` is instantiated with passengers, it works as expected.  Strange things
happen only when a `HauntedBus` starts empty, because then `self.passengers`
becomes an alias for the default value of the `passengers` parameter.  The problem
is that each default value is evaluated when the function is defined (usually
when the module is loaded), and the default values become attributes of the
function object.  So if a default value is a mutable object and you change it, the
change affects every future call of the function.

After running those lines, you can inspect the `HauntedBus.__init__` object and see
the ghost students haunting its `__defaults__` attribute:

```python
'__defaults__' in dir(HauntedBus.__init__)
# True
HauntedBus.__init__.__defaults__
# (['Carrie', 'Dave'],)
HauntedBus.__init__.__defaults__[0] is bus2.passengers
# True
```

The issue with mutable defaults explains why `None` is commonly used as the default
value for parameters that may receive mutable values.  In `Bus.__init__()`, if
`passengers` is `None`, `self.passengers` is bound to a new empty list; if it is not
`None`, the correct implementation binds a *copy* of that argument to
`self.passengers`.  The next section explains why copying the argument is good
practice.

### Defensive Programming with Mutable Parameters

When you write a function that receives a mutable parameter, you should carefully
consider whether the caller expects the argument passed to be changed.  For
example, if your function receives a `dict` and needs to modify it while
processing it, should this side effect be visible outside of the function or not?
It depends on the context; it's really a matter of aligning the expectations of
the author of the function and those of the caller.

The last bus example shows how a `TwilightBus` breaks expectations by sharing its
passenger list with its clients.  First, see how it works from the perspective of
a client:

<!-- nocheck -->
```python
basketball_team = ['Sue', 'Tina', 'Maya', 'Diana', 'Pat']
bus = TwilightBus(basketball_team)
bus.drop('Tina')
bus.drop('Pat')
basketball_team  # the dropped passengers vanished from the team!
# ['Sue', 'Maya', 'Diana']
```

`TwilightBus` violates the "Principle of least astonishment", a best practice of
interface design.  It surely is astonishing that when the bus drops a student,
their name is removed from the basketball team roster.  Here is the
implementation:

```python
class TwilightBus:
    """A bus model that makes passengers vanish"""

    def __init__(self, passengers=None):
        if passengers is None:
            self.passengers = []
        else:
            self.passengers = passengers

    def pick(self, name):
        self.passengers.append(name)

    def drop(self, name):
        self.passengers.remove(name)

basketball_team = ['Sue', 'Tina', 'Maya', 'Diana', 'Pat']
bus = TwilightBus(basketball_team)
bus.drop('Tina')
bus.drop('Pat')
basketball_team
# ['Sue', 'Maya', 'Diana']
```

Here we are careful to create a new empty list when `passengers` is `None`.
However, the `else` branch makes `self.passengers` an alias for `passengers`,
which is itself an alias for the actual argument passed to `__init__()`
(`basketball_team`).  When `.remove()` and `.append()` are used with
`self.passengers`, we are actually mutating the original list received as an
argument to the constructor.

The bus should keep its own passenger list.  The fix is simple: when the
`passengers` parameter is provided, initialize `self.passengers` with a copy of it,
as `Bus` does:

<!-- nocheck -->
```python
def __init__(self, passengers=None):
    if passengers is None:
        self.passengers = []
    else:
        self.passengers = list(passengers)
```

Now the internal handling of the passenger list does not affect the argument used
to initialize the bus.  As a bonus, this solution is more flexible: the argument
passed to `passengers` may be a tuple or any other iterable, like a `set` or even
database results, because the `list` constructor accepts any iterable.  And since
we create our own list to manage, we ensure that it supports the `.remove()` and
`.append()` operations used by `.pick()` and `.drop()`.

> **Tip**
>
> Unless a method is explicitly intended to mutate an object received as an
> argument, think twice before aliasing the argument object by simply assigning
> it to an instance variable in your class.  If in doubt, make a copy.  Your clients
> will be happier.  Of course, making a copy is not free: there is a cost in CPU and
> memory.  However, an interface that causes subtle bugs is usually a bigger problem
> than one that is a little slower or uses more resources.

## `del` and Garbage Collection

The Data Model chapter of the language reference says that objects are never
explicitly destroyed; however, when they become unreachable they may be
garbage-collected.

The first strange fact about `del` is that it's not a function, it's a statement
(see [The del statement](datastructures.md#tut-del)).  We write `del x` and not
`del(x)`, although the latter also works, but only because the expressions `x` and
`(x)` usually mean the same thing in Python.

The second surprising fact is that `del` deletes *references*, not objects.
Python's garbage collector may discard an object from memory as an indirect
result of `del`, if the deleted variable was the last reference to the object.
Rebinding a variable may also cause the number of references to an object to
reach zero, causing its destruction:

```python
a = [1, 2]  # create object [1, 2] and bind a to it
b = a       # bind b to the same [1, 2] object
del a       # delete reference a
b           # [1, 2] was not affected, because b still points to it
# [1, 2]
b = [3]     # rebinding b removes the last remaining reference to [1, 2]
```

After the last line, the garbage collector can discard the `[1, 2]` object.

> **Warning**
>
> There is a `__del__()` special method, but it does not cause the disposal of the
> instance, and it should not be called by your code.  `__del__()` is invoked by the
> interpreter when the instance is about to be destroyed, to give it a chance to
> release external resources.  You will seldom need to implement `__del__()` in
> your own code, and its proper use is rather tricky.  See the
> [`__del__()` documentation](https://docs.python.org/3/reference/datamodel.html#object.__del__).

In CPython, the primary algorithm for garbage collection is *reference counting*.
Essentially, each object keeps count of how many references point to it.  As soon
as that refcount reaches zero, the object is immediately destroyed: CPython calls
the `__del__()` method on the object (if defined) and then frees the memory
allocated to it.  CPython 2.0 added a generational garbage collection algorithm
to detect groups of objects involved in reference cycles, which may be unreachable
even with outstanding references to them, when all the mutual references are
contained within the group.  Other implementations of Python have more
sophisticated garbage collectors that do not rely on reference counting, which
means `__del__()` may not be called immediately when there are no more references
to the object.

The next example uses [`weakref.finalize`](https://docs.python.org/3/library/weakref.html#weakref.finalize)
to register a callback function to be called when an object is destroyed, so we
can watch the end of an object's life:

```python
import weakref
s1 = {1, 2, 3}
s2 = s1  # s1 and s2 are aliases referring to the same set
def bye():
    print('...like tears in the rain.')

ender = weakref.finalize(s1, bye)  # register the bye callback on the set
ender.alive  # alive is True before the finalize object is called
# True
del s1
ender.alive  # del did not delete the object, just the s1 reference to it
# True
s2 = 'spam'  # rebinding the last reference makes {1, 2, 3} unreachable
# ...like tears in the rain.
ender.alive
# False
```

The `bye` function must not be a bound method of the object about to be destroyed,
or otherwise hold a reference to it.  The point of the example is to make explicit
that `del` does not delete objects; objects may be deleted as a consequence of
being unreachable after `del` is used.

You may wonder why the `{1, 2, 3}` object was destroyed at all.  After all, the
`s1` reference was passed to `finalize`, which must have held on to it to monitor
the object and invoke the callback.  This works because `finalize` holds a *weak
reference* to `{1, 2, 3}`.

> **Note**
>
> Since Python 3.12, some objects such as `None`, `True` and small integers are
> *immortal* in CPython ([**PEP 683**](https://peps.python.org/pep-0683/)): their
> reference counts are never changed, and they are never deallocated.  This is
> another implementation detail you should not depend on, but it explains odd
> values returned by `sys.getrefcount()` for those objects.

## Weak References

The presence of references is what keeps an object alive in memory.  When the
reference count of an object reaches zero, the garbage collector disposes of it.
But sometimes it is useful to have a reference to an object that does not keep it
around longer than necessary.  A common use case is a cache.

Weak references to an object do not increase its reference count.  The object that
is the target of a reference is called the *referent*.  Therefore, we say that a
weak reference does not prevent the referent from being garbage collected.  Weak
references are useful in caching applications because you don't want the cached
objects to be kept alive just because they are referenced by the cache.  The
tutorial introduced them briefly in [Weak References](stdlib2.md#tut-weak-references).

A `weakref.ref` instance can be called to reach its referent.  If the object is
alive, calling the weak reference returns it; otherwise it returns `None`:

<!-- nocheck -->
```python
import weakref
a_set = {0, 1}
wref = weakref.ref(a_set)
wref
# <weakref at 0x100637598; to 'set' at 0x100636748>
wref()
# {0, 1}
a_set = {2, 3, 4}
wref()
# {0, 1}
wref() is None
# False
wref() is None
# True
```

Here a weak reference `wref` is created and inspected.  Invoking `wref()` returns
the referenced object, `{0, 1}`; at the interactive prompt, that result is also
bound to the variable `_`, which keeps it alive.  `a_set` no longer refers to the
`{0, 1}` set, so its reference count is decreased, but the `_` variable still
refers to it, so `wref()` still returns `{0, 1}`.  When the first `wref() is None`
expression is evaluated, `{0, 1}` lives; the result, `False`, is then bound to `_`,
so there are no more strong references to `{0, 1}`.  Now the `{0, 1}` object is
gone, and the last call to `wref()` returns `None`.  (This only behaves this way in
the interactive interpreter, because of the hidden `_` variable.)

The [`weakref`](https://docs.python.org/3/library/weakref.html) module
documentation makes the point that the `weakref.ref` class is actually a low-level
interface intended for advanced uses, and that most programs are better served by
the `weakref` collections and `finalize`.  In other words, consider using
`WeakKeyDictionary`, `WeakValueDictionary`, `WeakSet` and `finalize` (which use weak
references internally) instead of creating and handling your own `weakref.ref`
instances by hand.

### The `WeakValueDictionary` Skit

The class `WeakValueDictionary` implements a mutable mapping where the values are
weak references to objects.  When a referred object is garbage collected elsewhere
in the program, the corresponding key is automatically removed from the
`WeakValueDictionary`.  This is commonly used for caching.

Our demonstration of a `WeakValueDictionary` is inspired by the classic Monty
Python's "Cheese Shop" skit, in which a customer asks for more than 40 kinds of
cheese, including cheddar and mozzarella, but none are in stock.  Here is a
trivial class to represent each kind of cheese:

```python
class Cheese:

    def __init__(self, kind):
        self.kind = kind

    def __repr__(self):
        return f'Cheese({self.kind!r})'
```

Each cheese from a catalog is loaded from a list into a stock implemented as a
`WeakValueDictionary`.  However, all but one disappear from the stock as soon as the
catalog is deleted:

```python
import weakref
stock = weakref.WeakValueDictionary()
catalog = [Cheese('Red Leicester'), Cheese('Tilsit'),
           Cheese('Brie'), Cheese('Parmesan')]

for cheese in catalog:
    stock[cheese.kind] = cheese

sorted(stock.keys())
# ['Brie', 'Parmesan', 'Red Leicester', 'Tilsit']
del catalog
sorted(stock.keys())
# ['Parmesan']
del cheese
sorted(stock.keys())
# []
```

The `stock` maps the name of each cheese to a weak reference to the cheese instance
in the `catalog`.  The stock is complete until the catalog is deleted; then most
cheeses are gone, as expected.  Why not all of them?  A temporary variable may
cause an object to last longer than expected by holding a reference to it.  This
is usually not a problem with local variables, because they are destroyed when the
function returns.  But here `cheese` is a global variable of the `for` loop, and it
will never go away unless explicitly deleted.  After `del cheese`, the Parmesan
goes too.

A counterpart to `WeakValueDictionary` is `WeakKeyDictionary`, in which the keys
are weak references.  A `WeakKeyDictionary` can associate additional data with
objects that are owned by other parts of the program, without adding attributes to
those objects; this is useful for objects that prohibit attribute assignment.  The
`WeakSet` class is "a set class that keeps weak references to its elements; an
element will be discarded when no strong reference to it exists any more."  If you
need to build a class that is aware of every one of its instances, a good solution
is to create a class attribute with a `WeakSet` to hold the references to the
instances.  Otherwise, if a regular `set` were used, the instances would never be
garbage collected, because the class itself would have strong references to them,
and classes live as long as the Python process unless you deliberately delete them.

### Limitations of Weak References

Not every Python object may be the target, or referent, of a weak reference.
Basic `list` and `dict` instances may not be referents, but a plain subclass of
either can solve this problem easily:

```python
class MyList(list):
    """list subclass whose instances may be weakly referenced"""

a_list = MyList(range(10))

# a_list can be the target of a weak reference
wref_to_a_list = weakref.ref(a_list)
wref_to_a_list() is a_list
# True
```

A `set` instance can be a referent, and user-defined types also pose no problem,
which explains why the `Cheese` class was needed in the cheese shop example.  But
`int` and `tuple` instances cannot be targets of weak references, even if
subclasses of those types are created.  Most of these limitations are
implementation details of CPython that may not apply to other Python interpreters.
They are the result of internal optimizations, some of which are discussed in the
next section.

## Tricks Python Plays with Immutables

> **Note**
>
> This optional section discusses some details that are not really important for
> users of Python, and that may not apply to other implementations or even future
> versions of CPython.  Nevertheless, people stumble upon these corner cases and
> then start using the `is` operator incorrectly, so they are worth mentioning.

For a tuple `t`, `t[:]` does not make a copy, but returns a reference to the same
object.  You also get a reference to the same tuple if you write `tuple(t)`.  (This
is documented: `help(tuple)` says "If the argument is a tuple, the return value is
the same object.")

```python
t1 = (1, 2, 3)
t2 = tuple(t1)
t2 is t1  # t1 and t2 are bound to the same object
# True
t3 = t1[:]
t3 is t1  # and so is t3
# True
```

The same behavior can be observed with instances of `str`, `bytes` and `frozenset`.
A `frozenset` is not a sequence, so `fs[:]` does not work, but `fs.copy()` has the
same effect: it cheats and returns a reference to the same object, not a copy at
all.  (That harmless lie keeps `frozenset` compatible with `set`; it makes no
difference to the user whether two identical immutable objects are the same or are
copies.)

<!-- nocheck -->
```python
t1 = (1, 2, 3)
t3 = (1, 2, 3)  # creating a new tuple from scratch
t3 is t1  # equal, but not the same object
# False
s1 = 'ABC'
s2 = 'ABC'  # creating a second str from scratch
s2 is s1  # surprise: they refer to the same str!
# True
```

The sharing of string literals is an optimization technique called *interning*.
CPython uses a similar technique with small integers to avoid unnecessary
duplication of numbers that appear frequently in programs, like 0, 1, -1, etc.
Note that CPython does not intern all strings or integers, and the criteria it uses
are an undocumented implementation detail.  (Whether `t3 is t1` above is `True` or
`False` also depends on how the code is compiled; in a script, the compiler may
reuse a single constant for both literals.)

> **Warning**
>
> Never depend on `str` or `int` interning!  Always use `==` instead of `is` to
> compare strings or integers for equality.  Interning is an optimization for
> internal use of the Python interpreter.

The tricks discussed in this section, including the behavior of
`frozenset.copy()`, are harmless "lies" that save memory and make the interpreter
faster.  Don't worry about them; they should not give you any trouble, because they
only apply to immutable types.

## Summary

Every Python object has an identity, a type and a value.  Only the value of an
object may change over time.  (Strictly speaking, the type can be changed by
assigning a different class to `__class__`, but that is pure evil.)

If two variables refer to immutable objects that have equal values (`a == b` is
`True`), in practice it rarely matters whether they refer to copies or are aliases
of the same object, because the value of an immutable object does not change, with
one exception: immutable collections such as tuples.  If an immutable collection
holds references to mutable items, its value may actually change when the value of
a mutable item changes.  What never changes in an immutable collection are the
identities of the objects within.  `frozenset` does not suffer from this problem
because it can only hold hashable elements, and the value of hashable objects
cannot ever change, by definition.

The fact that variables hold references has many practical consequences:

* Simple assignment does not create copies.
* Augmented assignment with `+=` or `*=` creates new objects if the left-hand
  variable is bound to an immutable object, but may modify a mutable object in
  place.
* Assigning a new value to an existing variable does not change the object
  previously bound to it.  This is called a *rebinding*: the variable is now bound
  to a different object.  If that variable was the last reference to the previous
  object, that object will be garbage collected.
* Function parameters are passed as aliases, which means the function may change
  any mutable object received as an argument.  There is no way to prevent this,
  except making local copies or using immutable objects (for example, passing a
  tuple instead of a list).
* Using mutable objects as default values for function parameters is dangerous,
  because if the parameters are changed in place, the default is changed,
  affecting every future call that relies on it.

In CPython, objects are discarded as soon as the number of references to them
reaches zero.  They may also be discarded if they form groups with cyclic
references but no outside references.  In some situations it is useful to hold a
reference to an object that will not, by itself, keep the object alive; weak
references and the `weakref` collections serve that purpose.

> **Note**
>
> There is no mechanism in Python to directly destroy an object, and that omission
> is a feature: if you could destroy an object at any time, what would happen to
> existing references pointing to it?  Because CPython uses reference counting, a
> line like `open('test.txt', 'wt', encoding='utf-8').write('1, 2, 3')` happens to
> close the file right away.  But other implementations, whose garbage collectors
> don't rely on reference counting, may take longer to destroy the file object.  In
> all cases the best practice is to close files explicitly, and the most reliable way
> is the `with` statement, which guarantees that the file is closed even if
> exceptions are raised:
>
> ```python
> with open('test.txt', 'wt', encoding='utf-8') as fp:
>     fp.write('1, 2, 3')
> ```

> **See also**
>
> * The [Data Model](https://docs.python.org/3/reference/datamodel.html) chapter of
>   the language reference starts with a clear explanation of object identities and
>   values.
> * The [`gc`](https://docs.python.org/3/library/gc.html) module documentation and
>   "Design of CPython's Garbage Collector" in the Python Developer's Guide describe
>   the generational collector in depth.  The Data Model chapter even notes that an
>   implementation may postpone garbage collection or omit it altogether, as long as
>   no reachable objects are collected.
> * [**PEP 442**](https://peps.python.org/pep-0442/) describes the safe finalization
>   of objects with a `__del__()` method.
