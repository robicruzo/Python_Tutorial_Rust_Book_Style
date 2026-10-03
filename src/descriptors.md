# Attribute Descriptors

> Learning about descriptors not only provides access to a larger toolset, it creates a
> deeper understanding of how Python works and an appreciation for the elegance of its
> design.
>
> — Raymond Hettinger, [Descriptor HowTo Guide](https://docs.python.org/3/howto/descriptor.html)

Descriptors are a way of reusing the same access logic in multiple attributes.  For example,
field types in ORMs, such as the Django ORM and SQLAlchemy, are descriptors, managing the
flow of data from the fields in a database record to Python object attributes and vice
versa.

A descriptor is a class that implements a dynamic protocol consisting of the `__get__`,
`__set__` and `__delete__` methods.  The `property` class implements the full descriptor
protocol.  As usual with dynamic protocols, partial implementations are OK.  In fact, most
descriptors we see in real code implement only `__get__` and `__set__`, and many implement
only one of these methods.

Descriptors are a distinguishing feature of Python, deployed not only at the application
level but also in the language infrastructure.  User-defined functions are descriptors.
We'll see how the descriptor protocol allows methods to operate as bound or unbound methods,
depending on how they are called.

In this chapter we'll refactor the bulk food example we first saw in
[Using a Property for Attribute Validation](dynamic-attributes.md#using-a-property-for-attribute-validation),
replacing properties with descriptors.  This will make it easier to reuse the attribute
validation logic across different classes.  We'll tackle the concepts of overriding and
nonoverriding descriptors, and realize that Python functions are descriptors.  Finally we'll
see some tips about implementing descriptors.

## Descriptor Example: Attribute Validation

As we saw in [Coding a Property Factory](dynamic-attributes.md#coding-a-property-factory), a
property factory is a way to avoid repetitive coding of getters and setters by applying
functional programming patterns.  A property factory is a higher-order function that creates
a parameterized set of accessor functions and builds a custom property instance from them,
with closures to hold settings like the `storage_name`.  The object-oriented way of solving
the same problem is a descriptor class.

We'll continue the series of `LineItem` examples where we left off, by refactoring the
`quantity` property factory into a `Quantity` descriptor class.  This will make it easier to
use.

### LineItem Take #3: A Simple Descriptor

As we said in the introduction, a class implementing a `__get__`, a `__set__` or a
`__delete__` method is a descriptor.  You use a descriptor by declaring instances of it as
class attributes of another class.

We'll create a `Quantity` descriptor, and the `LineItem` class will use two instances of
`Quantity`: one for managing the `weight` attribute, the other for `price`.  Note that there
are really two distinct attributes named `weight`: one is a class attribute of `LineItem`
(the descriptor instance), the other is an instance attribute that will exist in each
`LineItem` object (where the value is stored).  This also applies to `price`.

```text
             LineItem (class)                      a LineItem instance
  +-------------------------------------+     +---------------------------+
  | weight = <Quantity object>  --------+---->| __dict__['weight'] = 8    |
  | price  = <Quantity object>  --------+---->| __dict__['price']  = 13.95|
  | __init__(), subtotal()              |     | __dict__['description']   |
  +-------------------------------------+     +---------------------------+
        descriptor instances                       storage attributes
        (class attributes)                         (instance attributes)
```

#### Terms to understand descriptors

Implementing and using descriptors involves several components, and it is useful to be
precise when naming those components.  These terms will be used throughout this chapter.
They will be easier to understand once you see the code, but they are listed up front so you
can refer back to them when needed.

Descriptor class
: A class implementing the descriptor protocol.  That's `Quantity` in the diagram.

Managed class
: The class where the descriptor instances are declared as class attributes.  `LineItem` is
  the managed class.

Descriptor instance
: Each instance of a descriptor class, declared as a class attribute of the managed class.

Managed instance
: One instance of the managed class.  In this example, `LineItem` instances are the managed
  instances.

Storage attribute
: An attribute of the managed instance that holds the value of a managed attribute for that
  particular instance.  The `LineItem` instance attributes `weight` and `price` are the
  storage attributes.  They are distinct from the descriptor instances, which are always
  class attributes.

Managed attribute
: A public attribute in the managed class that is handled by a descriptor instance, with
  values stored in storage attributes.  In other words, a descriptor instance and a storage
  attribute provide the infrastructure for a managed attribute.

It's important to realize that `Quantity` instances are class attributes of `LineItem`.  In
Luciano Ramalho's "Mills & Gizmos Notation", classes are *mills* — complicated machines that
produce *gizmos*, the instances.  The `Quantity` mill produces two gizmos which are attached
to the `LineItem` mill: `weight` and `price`.  The `LineItem` mill produces many gizmos of its
own, each with its own `weight` and `price` values.  Each descriptor gizmo has a magnifying
glass to `__get__` values and a claw to `__set__` values in the `LineItem` gizmos.

Enough doodling for now.  Here is the code: the `Quantity` descriptor class (`bulkfood_v3.py`):

```python
class Quantity:  # descriptor is a protocol-based feature; no subclassing needed

    def __init__(self, storage_name):
        self.storage_name = storage_name  # name of the storage attribute

    def __set__(self, instance, value):  # called on assignment to the managed attribute
        if value > 0:
            instance.__dict__[self.storage_name] = value  # store directly in the instance
        else:
            msg = f'{self.storage_name} must be > 0'
            raise ValueError(msg)

    def __get__(self, instance, owner):  # needed: storage_name may differ from the attr name
        return instance.__dict__[self.storage_name]
```

Each `Quantity` instance will have a `storage_name` attribute: that's the name of the storage
attribute to hold the value in the managed instances.  `__set__` is called when there is an
attempt to assign to the managed attribute.  Here, `self` is the descriptor instance (i.e.,
`LineItem.weight` or `LineItem.price`), `instance` is the managed instance (a `LineItem`
instance), and `value` is the value being assigned.  We must store the attribute value
directly into `__dict__`; calling `setattr(instance, self.storage_name)` would trigger the
`__set__` method again, leading to infinite recursion.

We need to implement `__get__` because the name of the managed attribute may not be the same
as the `storage_name`.  A user could write something like this:

<!-- nocheck -->
```python
class House:
    rooms = Quantity('number_of_rooms')
```

In the `House` class, the managed attribute is `rooms`, but the storage attribute is
`number_of_rooms`.  Given a `House` instance named `chaos_manor`, reading and writing
`chaos_manor.rooms` goes through the `Quantity` descriptor instance attached to `rooms`, but
reading and writing `chaos_manor.number_of_rooms` bypasses the descriptor.

Note that `__get__` receives three arguments: `self`, `instance` and `owner`.  The `owner`
argument is a reference to the managed class (e.g., `LineItem`), and it's useful if you want
the descriptor to support retrieving a class attribute — perhaps to emulate Python's default
behavior of retrieving a class attribute when the name is not found in the instance.

If a managed attribute, such as `weight`, is retrieved via the class like `LineItem.weight`,
the descriptor `__get__` method receives `None` as the value for the `instance` argument.  To
support introspection and other metaprogramming tricks by the user, it's a good practice to
make `__get__` return the descriptor instance when the managed attribute is accessed through
the class.  To do that, we'd code `__get__` like this:

<!-- nocheck -->
```python
def __get__(self, instance, owner):
    if instance is None:
        return self
    else:
        return instance.__dict__[self.storage_name]
```

Here is the `LineItem` class using `Quantity`:

```python
class LineItem:
    weight = Quantity('weight')  # the first descriptor instance manages weight
    price = Quantity('price')  # the second manages price

    def __init__(self, description, weight, price):  # the rest is as simple as Take #1
        self.description = description
        self.weight = weight
        self.price = price

    def subtotal(self):
        return self.weight * self.price
```

The code works as intended, preventing the sale of truffles for \$0:

```python
truffle = LineItem('White truffle', 100, 0)
# Traceback (most recent call last):
#     ...
# ValueError: price must be > 0
```

> **Warning**
>
> When coding descriptor `__get__` and `__set__` methods, keep in mind what the `self` and
> `instance` arguments mean: `self` is the descriptor instance, and `instance` is the managed
> instance.  Descriptors managing instance attributes should store values in the managed
> instances.  That's why Python provides the `instance` argument to the descriptor methods.

It may be tempting, but wrong, to store the value of each managed attribute in the descriptor
instance itself.  In other words, in the `__set__` method, instead of coding
`instance.__dict__[self.storage_name] = value`, the tempting but bad alternative would be
`self.__dict__[self.storage_name] = value`.  To understand why this would be wrong, think
about the meaning of the first two arguments to `__set__`.  Here, `self` is the descriptor
instance, which is actually a class attribute of the managed class.  You may have thousands of
`LineItem` instances in memory at one time, but you'll only have two instances of the
descriptors: the class attributes `LineItem.weight` and `LineItem.price`.  So anything you
store in the descriptor instances themselves is actually part of a `LineItem` class attribute,
and therefore is shared among all `LineItem` instances:

```python
class BadQuantity:
    def __set__(self, instance, value):
        self.value = value  # WRONG: stored in the descriptor, shared by all instances

    def __get__(self, instance, owner):
        return self.value

class Item:
    weight = BadQuantity()

a, b = Item(), Item()
a.weight = 10
b.weight = 20
a.weight  # oops: b clobbered a's weight
# 20
```

> **Tip**
>
> If you really need per-instance storage outside the instance — say, because the managed
> class uses `__slots__` without a `__dict__` — keep a
> [`weakref.WeakKeyDictionary`](https://docs.python.org/3/library/weakref.html#weakref.WeakKeyDictionary)
> in the descriptor, keyed by managed instance, so the descriptor doesn't keep the instances
> alive.

A drawback of this version is the need to repeat the names of the attributes when the
descriptors are instantiated in the managed class body.  It would be nice if the `LineItem`
class could be declared like this:

<!-- nocheck -->
```python
class LineItem:
    weight = Quantity()
    price = Quantity()

    # remaining methods as before
```

As it stands, Take #3 requires naming each `Quantity` explicitly, which is not only
inconvenient but dangerous.  If a programmer copying and pasting code forgets to edit both
names and writes something like `price = Quantity('weight')`, the program will misbehave
badly, clobbering the value of `weight` whenever the `price` is set.

The problem is that — as we saw in [Object References, Mutability, and Recycling](references.md)
— the righthand side of an assignment is executed before the variable exists.  The expression
`Quantity()` is evaluated to create a descriptor instance, and there is no way the code in the
`Quantity` class can guess the name of the variable to which the descriptor will be bound
(e.g., `weight` or `price`).  Thankfully, the descriptor protocol supports the aptly named
`__set_name__` special method.  We'll see how to use it next.

### LineItem Take #4: Automatic Naming of Storage Attributes

To avoid retyping the attribute name in the descriptor instances, we'll implement
`__set_name__` to set the `storage_name` of each `Quantity` instance.  The `__set_name__`
special method was added to the descriptor protocol in Python 3.6
([**PEP 487**](https://peps.python.org/pep-0487/)).  The interpreter calls `__set_name__` on
each descriptor it finds in a class body — if the descriptor implements it.  (More precisely,
`__set_name__` is called by `type.__new__`, the constructor of objects representing classes;
see [Class Metaprogramming](class-metaprogramming.md).)

In `bulkfood_v4.py`, the `Quantity` descriptor class doesn't need an `__init__`.  Instead,
`__set_name__` saves the name of the storage attribute:

```python
class Quantity:

    def __set_name__(self, owner, name):  # owner: managed class; name: attribute name
        self.storage_name = name  # this is what __init__ did in Take #3

    def __set__(self, instance, value):  # exactly the same as in Take #3
        if value > 0:
            instance.__dict__[self.storage_name] = value
        else:
            msg = f'{self.storage_name} must be > 0'
            raise ValueError(msg)

    # no __get__ needed

class LineItem:
    weight = Quantity()  # no need to pass the managed attribute name any more
    price = Quantity()

    def __init__(self, description, weight, price):
        self.description = description
        self.weight = weight
        self.price = price

    def subtotal(self):
        return self.weight * self.price

nutmeg = LineItem('Moluccan nutmeg', 8, 13.95)
nutmeg.weight, nutmeg.price
# (8, 13.95)
LineItem.weight.storage_name
# 'weight'
nutmeg.weight = 0
# Traceback (most recent call last):
#     ...
# ValueError: weight must be > 0
```

In `__set_name__`, `self` is the descriptor instance (not the managed instance), `owner` is
the managed class, and `name` is the name of the attribute of `owner` to which this descriptor
instance was assigned in the class body of `owner`.

Implementing `__get__` is not necessary because the name of the storage attribute matches the
name of the managed attribute.  The expression `product.price` gets the `price` attribute
directly from the `LineItem` instance.  (Notice that `LineItem.weight` returned the descriptor
instance itself: with no `__get__`, Python returns the class attribute as is.)

Looking at this example, you may think that's a lot of code just for managing a couple of
attributes, but it's important to realize that the descriptor logic is now abstracted into a
separate code unit: the `Quantity` class.  Usually we do not define a descriptor in the same
module where it's used, but in a separate utility module designed to be used across the
application — even in many applications, if you are developing a library or framework.  With
this in mind, this better represents the typical usage of a descriptor:

<!-- nocheck -->
```python
import model_v4c as model  # import the module where Quantity is implemented


class LineItem:
    weight = model.Quantity()  # put model.Quantity to use
    price = model.Quantity()

    def __init__(self, description, weight, price):
        self.description = description
        self.weight = weight
        self.price = price

    def subtotal(self):
        return self.weight * self.price
```

Django users will notice that this looks a lot like a model definition.  It's no coincidence:
Django model fields are descriptors.

Because descriptors are implemented as classes, we can leverage inheritance to reuse some of
the code we have for new descriptors.  That's what we'll do in the following section.

### LineItem Take #5: A New Descriptor Type

The imaginary organic food store hits a snag: somehow a line item instance was created with a
blank description, and the order could not be fulfilled.  To prevent that, we'll create a new
descriptor, `NonBlank`.  As we design `NonBlank`, we realize it will be very much like the
`Quantity` descriptor, except for the validation logic.

This prompts a refactoring, producing `Validated`, an abstract class that overrides the
`__set__` method, calling a `validate` method that must be implemented by subclasses.  We'll
then rewrite `Quantity`, and implement `NonBlank` by inheriting from `Validated` and just
coding the `validate` methods.

The relationship among `Validated`, `Quantity` and `NonBlank` is an application of the
*template method* as described in the *Design Patterns* classic:

> A template method defines an algorithm in terms of abstract operations that subclasses
> override to provide concrete behavior.

Here, `Validated.__set__` is the template method and `self.validate` is the abstract
operation (`model_v5.py`):

```python
import abc

class Validated(abc.ABC):

    def __set_name__(self, owner, name):
        self.storage_name = name

    def __set__(self, instance, value):
        value = self.validate(self.storage_name, value)  # delegate validation...
        instance.__dict__[self.storage_name] = value  # ...then store the returned value

    @abc.abstractmethod
    def validate(self, name, value):  # the abstract operation
        """return validated value or raise ValueError"""
```

Alex Martelli prefers to call this design pattern *Self-Delegation*, and it's a more
descriptive name: the first line of `__set__` self-delegates to `validate`.  The concrete
`Validated` subclasses in this example are `Quantity` and `NonBlank`:

```python
class Quantity(Validated):
    """a number greater than zero"""

    def validate(self, name, value):  # implementation of the abstract operation
        if value <= 0:
            raise ValueError(f'{name} must be > 0')
        return value

class NonBlank(Validated):
    """a string with at least one non-space character"""

    def validate(self, name, value):
        value = value.strip()
        if not value:  # nothing left after stripping blanks: reject
            raise ValueError(f'{name} cannot be blank')
        return value  # returning the value lets validate clean it up
```

Requiring the concrete `validate` methods to return the validated value gives them an
opportunity to clean up, convert, or normalize the data received.  In this case, `value` is
returned without leading or trailing blanks.

Users of `model_v5.py` don't need to know all these details.  What matters is that they get
to use `Quantity` and `NonBlank` to automate the validation of instance attributes.  Here is
the latest `LineItem` class (`bulkfood_v5.py`):

```python
class LineItem:
    description = NonBlank()  # put NonBlank to use; the rest is unchanged
    weight = Quantity()
    price = Quantity()

    def __init__(self, description, weight, price):
        self.description = description
        self.weight = weight
        self.price = price

    def subtotal(self):
        return self.weight * self.price

raisins = LineItem('  Golden raisins ', 10, 6.95)
raisins.description  # NonBlank cleaned up the value
# 'Golden raisins'
raisins.subtotal()
# 69.5
LineItem('   ', 1, 1)
# Traceback (most recent call last):
#     ...
# ValueError: description cannot be blank
```

The `LineItem` examples we've seen in this chapter demonstrate a typical use of descriptors to
manage data attributes.  Descriptors like `Quantity` are called overriding descriptors because
their `__set__` method overrides (i.e., intercepts and overrules) the setting of an instance
attribute by the same name in the managed instance.  However, there are also nonoverriding
descriptors.  We'll explore this distinction in detail in the next section.

## Overriding Versus Nonoverriding Descriptors

Recall that there is an important asymmetry in the way Python handles attributes.  Reading an
attribute through an instance normally returns the attribute defined in the instance, but if
there is no such attribute in the instance, a class attribute will be retrieved.  On the other
hand, assigning to an attribute in an instance normally creates the attribute in the instance,
without affecting the class at all.

This asymmetry also affects descriptors, in effect creating two broad categories of
descriptors, depending on whether the `__set__` method is implemented.  If `__set__` is
present, the class is an overriding descriptor; otherwise, it is a nonoverriding descriptor.
These terms will make sense as we study descriptor behaviors in the next examples.

Observing the different descriptor categories requires a few classes, so we'll use the code
in `descriptorkinds.py` as our test bed for the following sections.  Every `__get__` and
`__set__` method calls `print_args` so their invocations are displayed in a readable way.
Understanding `print_args` and the auxiliary functions `cls_name` and `display` is not
important, so don't get distracted by them.

```python
### auxiliary functions for display only ###

def cls_name(obj_or_cls):
    cls = type(obj_or_cls)
    if cls is type:
        cls = obj_or_cls
    return cls.__name__.split('.')[-1]

def display(obj):
    cls = type(obj)
    if cls is type:
        return f'<class {obj.__name__}>'
    elif cls in [type(None), int]:
        return repr(obj)
    else:
        return f'<{cls_name(obj)} object>'

def print_args(name, *args):
    pseudo_args = ', '.join(display(x) for x in args)
    print(f'-> {cls_name(args[0])}.__{name}__({pseudo_args})')

### essential classes for this example ###

class Overriding:  # an overriding descriptor class with __get__ and __set__
    """a.k.a. data descriptor or enforced descriptor"""

    def __get__(self, instance, owner):
        print_args('get', self, instance, owner)

    def __set__(self, instance, value):
        print_args('set', self, instance, value)

class OverridingNoGet:  # an overriding descriptor without a __get__ method
    """an overriding descriptor without ``__get__``"""

    def __set__(self, instance, value):
        print_args('set', self, instance, value)

class NonOverriding:  # no __set__ method here, so this is a nonoverriding descriptor
    """a.k.a. non-data or shadowable descriptor"""

    def __get__(self, instance, owner):
        print_args('get', self, instance, owner)

class Managed:  # the managed class, using one instance of each descriptor class
    over = Overriding()
    over_no_get = OverridingNoGet()
    non_over = NonOverriding()

    def spam(self):  # here for comparison, because methods are also descriptors
        print(f'-> Managed.spam({display(self)})')
```

In the following sections, we will examine the behavior of attribute reads and writes on the
`Managed` class, and one instance of it, going through each of the different descriptors
defined.

### Overriding Descriptors

A descriptor that implements the `__set__` method is an overriding descriptor, because
although it is a class attribute, a descriptor implementing `__set__` will override attempts
to assign to instance attributes.  This is how Take #4 was implemented.  Properties are also
overriding descriptors: if you don't provide a setter function, the default `__set__` from the
`property` class will raise `AttributeError` to signal that the attribute is read-only.  Here
are experiments with an overriding descriptor:

```python
obj = Managed()  # create a Managed object for testing
obj.over  # triggers __get__, passing the managed instance obj as the second argument
# -> Overriding.__get__(<Overriding object>, <Managed object>, <class Managed>)
Managed.over  # via the class: __get__ gets None as the instance argument
# -> Overriding.__get__(<Overriding object>, None, <class Managed>)
obj.over = 7  # assigning triggers __set__, passing 7 as the last argument
# -> Overriding.__set__(<Overriding object>, <Managed object>, 7)
obj.over  # reading still invokes the descriptor __get__
# -> Overriding.__get__(<Overriding object>, <Managed object>, <class Managed>)
obj.__dict__['over'] = 8  # bypass the descriptor, setting a value directly in __dict__
vars(obj)  # the value is in obj.__dict__, under the over key...
# {'over': 8}
obj.over  # ...but the Managed.over descriptor still overrides reads
# -> Overriding.__get__(<Overriding object>, <Managed object>, <class Managed>)
```

> **Note**
>
> Python contributors and authors use different terms when discussing these concepts.
> "Overriding descriptor" comes from the book *Python in a Nutshell*.  The official Python
> documentation uses "data descriptor", but "overriding descriptor" highlights the special
> behavior.  Overriding descriptors are also called "enforced descriptors".  Synonyms for
> nonoverriding descriptors include "nondata descriptors" or "shadowable descriptors".

### Overriding Descriptor Without `__get__`

Properties and other overriding descriptors, such as Django model fields, implement both
`__set__` and `__get__`, but it's also possible to implement only `__set__`, as we saw in Take
#4.  In this case, only writing is handled by the descriptor.  Reading the descriptor through
an instance will return the descriptor object itself because there is no `__get__` to handle
that access.  If a namesake instance attribute is created with a new value via direct access
to the instance `__dict__`, the `__set__` method will still override further attempts to set
that attribute, but reading that attribute will simply return the new value from the instance,
instead of returning the descriptor object.  In other words, the instance attribute will
shadow the descriptor, but only when reading:

```python
obj.over_no_get  # no __get__: reading retrieves the descriptor instance from the class
# <__main__.OverridingNoGet object at 0x...>
Managed.over_no_get  # the same thing happens via the managed class
# <__main__.OverridingNoGet object at 0x...>
obj.over_no_get = 7  # setting invokes the __set__ descriptor method
# -> OverridingNoGet.__set__(<OverridingNoGet object>, <Managed object>, 7)
obj.over_no_get  # our __set__ doesn't store anything, so we get the descriptor again
# <__main__.OverridingNoGet object at 0x...>
obj.__dict__['over_no_get'] = 9  # set an instance attribute through __dict__
obj.over_no_get  # now the instance attribute shadows the descriptor, for reading
# 9
obj.over_no_get = 7  # assignment still goes through the descriptor __set__
# -> OverridingNoGet.__set__(<OverridingNoGet object>, <Managed object>, 7)
obj.over_no_get  # but reading is shadowed while the namesake instance attribute exists
# 9
```

### Nonoverriding Descriptor

A descriptor that does not implement `__set__` is a nonoverriding descriptor.  Setting an
instance attribute with the same name will shadow the descriptor, rendering it ineffective for
handling that attribute in that specific instance.  Methods and `@functools.cached_property`
are implemented as nonoverriding descriptors.  Here is the operation of a nonoverriding
descriptor:

```python
obj = Managed()
obj.non_over  # triggers __get__, passing obj as the second argument
# -> NonOverriding.__get__(<NonOverriding object>, <Managed object>, <class Managed>)
obj.non_over = 7  # no __set__ to interfere with this assignment
obj.non_over  # the instance attribute shadows the namesake descriptor
# 7
Managed.non_over  # the descriptor is still there, and catches access via the class
# -> NonOverriding.__get__(<NonOverriding object>, None, <class Managed>)
del obj.non_over  # if the instance attribute is deleted...
obj.non_over  # ...reading hits the descriptor __get__ again
# -> NonOverriding.__get__(<NonOverriding object>, <Managed object>, <class Managed>)
```

In the previous examples, we saw several assignments to an instance attribute with the same
name as a descriptor, and different results according to the presence of a `__set__` method in
the descriptor.

The setting of attributes in the class cannot be controlled by descriptors attached to the
same class.  In particular, this means that the descriptor attributes themselves can be
clobbered by assigning to the class, as the next section explains.

### Overwriting a Descriptor in the Class

Regardless of whether a descriptor is overriding or not, it can be overwritten by assignment
to the class.  This is a monkey-patching technique, but here the descriptors are replaced by
integers, which would effectively break any class that depended on the descriptors for proper
operation:

```python
class Managed2:  # a fresh copy, so we don't break Managed for later examples
    over = Overriding()
    over_no_get = OverridingNoGet()
    non_over = NonOverriding()

obj = Managed2()  # create a new instance for later testing
Managed2.over = 1  # overwrite the descriptor attributes in the class
Managed2.over_no_get = 2
Managed2.non_over = 3
obj.over, obj.over_no_get, obj.non_over  # the descriptors are really gone
# (1, 2, 3)
```

This reveals another asymmetry regarding reading and writing attributes: although the reading
of a class attribute can be controlled by a descriptor with `__get__` attached to the managed
class, the writing of a class attribute cannot be handled by a descriptor with `__set__`
attached to the same class.

> **Tip**
>
> In order to control the setting of attributes in a class, you have to attach descriptors to
> the class of the class — in other words, the metaclass.  By default, the metaclass of
> user-defined classes is `type`, and you cannot add attributes to `type`.  But in
> [Class Metaprogramming](class-metaprogramming.md), we'll create our own metaclasses.

### The Attribute Lookup Algorithm

We can now summarize what `obj.attr` does for an ordinary object.  The work is done by
`object.__getattribute__` (classes use `type.__getattribute__`, which is similar but also
calls `__get__` for descriptors found in the class itself):

1. Search `type(obj).__mro__` for `attr`.  If found, and it's an **overriding** (data)
   descriptor — it has `__set__` or `__delete__` — return `descriptor.__get__(obj, type(obj))`.
2. Otherwise, if `attr` is in `obj.__dict__`, return that value.
3. Otherwise, if step 1 found a **nonoverriding** descriptor, return the result of its
   `__get__`; if it found a plain class attribute, return it.
4. Otherwise, raise `AttributeError` — which makes Python try `__getattr__`, if the class has
   one.

Assignment is simpler: `obj.attr = value` calls `__set__` if an overriding descriptor named
`attr` is found in the class's MRO; otherwise it stores the value in `obj.__dict__`.  Here is
a pure-Python emulation of `property` along the lines of the one in the
[Descriptor HowTo Guide](https://docs.python.org/3/howto/descriptor.html#properties), showing
that there's nothing magical about it:

```python
class Property:
    "Emulate PyProperty_Type() in Objects/descrobject.c"

    def __init__(self, fget=None, fset=None, fdel=None, doc=None):
        self.fget = fget
        self.fset = fset
        self.fdel = fdel
        if doc is None and fget is not None:
            doc = fget.__doc__
        self.__doc__ = doc

    def __set_name__(self, owner, name):
        self.__name__ = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        if self.fget is None:
            raise AttributeError(f'property {self.__name__!r} has no getter')
        return self.fget(obj)

    def __set__(self, obj, value):  # always present: Property is an overriding descriptor
        if self.fset is None:
            raise AttributeError(f'property {self.__name__!r} has no setter')
        self.fset(obj, value)

    def __delete__(self, obj):
        if self.fdel is None:
            raise AttributeError(f'property {self.__name__!r} has no deleter')
        self.fdel(obj)

    def getter(self, fget):
        return type(self)(fget, self.fset, self.fdel, self.__doc__)

    def setter(self, fset):
        return type(self)(self.fget, fset, self.fdel, self.__doc__)

    def deleter(self, fdel):
        return type(self)(self.fget, self.fset, fdel, self.__doc__)

class Celsius:
    def __init__(self, degrees):
        self.degrees = degrees

    @Property
    def fahrenheit(self):
        """temperature in degrees Fahrenheit"""
        return self.degrees * 9 / 5 + 32

c = Celsius(100)
c.fahrenheit
# 212.0
Celsius.fahrenheit.__doc__
# 'temperature in degrees Fahrenheit'
c.fahrenheit = 0
# Traceback (most recent call last):
#     ...
# AttributeError: property 'fahrenheit' has no setter
```

Let's now focus on how descriptors are used to implement methods in Python.

## Methods Are Descriptors

A function within a class becomes a bound method when invoked on an instance because all
user-defined functions have a `__get__` method, therefore they operate as descriptors when
attached to a class.  Here we read the `spam` method from the `Managed` class introduced
earlier:

```python
obj = Managed()
obj.spam  # reading from obj.spam retrieves a bound method object
# <bound method Managed.spam of <__main__.Managed object at 0x...>>
Managed.spam  # but reading from Managed.spam retrieves a function
# <function Managed.spam at 0x...>
obj.spam = 7  # assigning to obj.spam shadows the class attribute
obj.spam
# 7
```

Functions do not implement `__set__`, therefore they are nonoverriding descriptors, as the
last line shows.

The other key takeaway is that `obj.spam` and `Managed.spam` retrieve different objects.  As
usual with descriptors, the `__get__` of a function returns a reference to itself when the
access happens through the managed class.  But when the access goes through an instance, the
`__get__` of the function returns a bound method object: a callable that wraps the function
and binds the managed instance (e.g., `obj`) to the first argument of the function (i.e.,
`self`), like the `functools.partial` function does (as seen in
[Freezing Arguments with `functools.partial`](first-class-functions.md#freezing-arguments-with-functoolspartial)).
For a deeper understanding of this mechanism, consider this `Text` class, derived from
`UserString` (`method_is_descriptor.py`):

```python
import collections

class Text(collections.UserString):

    def __repr__(self):
        return 'Text({!r})'.format(self.data)

    def reverse(self):
        return self[::-1]
```

Now let's investigate the `Text.reverse` method:

```python
word = Text('forward')
word  # the repr looks like a constructor call that would make an equal instance
# Text('forward')
word.reverse()  # the reverse method returns the text spelled backward
# Text('drawrof')
Text.reverse(Text('backward'))  # a method called on the class works as a function
# Text('drawkcab')
type(Text.reverse), type(word.reverse)  # note the different types
# (<class 'function'>, <class 'method'>)
list(map(Text.reverse, ['repaid', (10, 20, 30), Text('stressed')]))  # works on any sequence
# ['diaper', (30, 20, 10), Text('desserts')]
Text.reverse.__get__(word)  # calling __get__ with an instance retrieves a bound method
# <bound method Text.reverse of Text('forward')>
Text.reverse.__get__(None, Text)  # with None as the instance: the function itself
# <function Text.reverse at 0x...>
word.reverse  # word.reverse actually invokes Text.reverse.__get__(word)
# <bound method Text.reverse of Text('forward')>
word.reverse.__self__  # the bound method holds a reference to the instance...
# Text('forward')
word.reverse.__func__ is Text.reverse  # ...and to the original function
# True
```

`Text.reverse` operates as a function, even working with objects that are not instances of
`Text`.  Any function is a nonoverriding descriptor.  Calling its `__get__` with an instance
retrieves a method bound to that instance; calling it with `None` as the instance argument
retrieves the function itself.  The bound method object has a `__self__` attribute holding a
reference to the instance on which the method was called, and a `__func__` attribute that is a
reference to the original function attached to the managed class.

The bound method object also has a `__call__` method, which handles the actual invocation.
This method calls the original function referenced in `__func__`, passing the `__self__`
attribute of the method as the first argument.  That's how the implicit binding of the
conventional `self` argument works.  We can do the same by hand with
[`types.MethodType`](https://docs.python.org/3/library/types.html#types.MethodType):

```python
import types

def shout(self):
    return self.data.upper() + '!'

bound = types.MethodType(shout, word)  # what function.__get__(word) builds
bound
# <bound method shout of Text('forward')>
bound()
# 'FORWARD!'
```

The way functions are turned into bound methods is a prime example of how descriptors are used
as infrastructure in the language.  The `classmethod` and `staticmethod` built-ins are
descriptors too: `classmethod.__get__` binds the *class* (the `owner` argument) instead of the
instance, and `staticmethod.__get__` returns the underlying function without binding anything:

```python
class Demo:
    @classmethod
    def klassmeth(cls, *args):
        return cls, args

    @staticmethod
    def statmeth(*args):
        return args

d = Demo()
d.klassmeth(1)  # the class is bound, even when accessed through an instance
# (<class '__main__.Demo'>, (1,))
Demo.__dict__['klassmeth'].__get__(None, Demo)  # what Demo.klassmeth does under the hood
# <bound method Demo.klassmeth of <class '__main__.Demo'>>
Demo.__dict__['statmeth'].__get__(d, Demo)  # nothing bound: the plain function
# <function Demo.statmeth at 0x...>
```

> **Note**
>
> Python 3.9 allowed `classmethod` to wrap other descriptors such as `property`, to create
> "class properties".  The feature turned out to be subtly broken; it was deprecated in 3.11
> and removed in 3.13.  If you need a computed class attribute, use a descriptor whose
> `__get__` uses the `owner` argument, or a property on a metaclass.

Since a decorator implemented as a class with `__call__` is not a function, it doesn't get
`__get__` for free, and therefore won't bind `self` when used on a method — unless you
implement `__get__` yourself.  This is a well-known pitfall:

```python
import functools

class counted:
    def __init__(self, func):
        functools.update_wrapper(self, func)
        self.func = func
        self.calls = 0

    def __call__(self, *args, **kwargs):
        self.calls += 1
        return self.func(*args, **kwargs)

    def __get__(self, instance, owner):  # without this, self would not be bound
        if instance is None:
            return self
        return types.MethodType(self, instance)

class Greeter:
    @counted
    def hello(self, name):
        return f'Hello, {name}!'

g = Greeter()
g.hello('Ana')
# 'Hello, Ana!'
Greeter.hello.calls
# 1
```

Delete `__get__` from `counted` and `g.hello('Ana')` fails with
`TypeError: Greeter.hello() missing 1 required positional argument: 'name'`, because the
instance `g` is never passed to the function.

After this deep dive into how descriptors and methods work, let's go through some practical
advice about their use.

## Descriptor Usage Tips

The following list addresses some practical consequences of the descriptor characteristics
just described:

Use `property` to keep it simple
: The `property` built-in creates overriding descriptors implementing `__set__` and `__get__`
  even if you do not define a setter method (a `__delete__` method is provided too).  The
  default `__set__` of a property raises `AttributeError: property 'x' of 'C' object has no
  setter`, so a property is the easiest way to create a read-only attribute, avoiding the
  issue described next.

Read-only descriptors require `__set__`
: If you use a descriptor class to implement a read-only attribute, you must remember to code
  both `__get__` and `__set__`, otherwise setting a namesake attribute on an instance will
  shadow the descriptor.  The `__set__` method of a read-only attribute should just raise
  `AttributeError` with a suitable message.

Validation descriptors can work with `__set__` only
: In a descriptor designed only for validation, the `__set__` method should check the `value`
  argument it gets, and if valid, set it directly in the instance `__dict__` using the
  descriptor instance name as key.  That way, reading the attribute with the same name from
  the instance will be as fast as possible, because it will not require a `__get__`.  See the
  code for Take #4.

Caching can be done efficiently with `__get__` only
: If you code just the `__get__` method, you have a nonoverriding descriptor.  These are
  useful to make some expensive computation and then cache the result by setting an attribute
  by the same name on the instance.  The namesake instance attribute will shadow the
  descriptor, so subsequent access to that attribute will fetch it directly from the instance
  `__dict__` and not trigger the descriptor `__get__` anymore.  The
  `@functools.cached_property` decorator actually produces a nonoverriding descriptor.
  (Recall that creating instance attributes after `__init__` defeats the key-sharing memory
  optimization discussed in [Dictionaries and Sets](dicts-sets.md).)

Nonspecial methods can be shadowed by instance attributes
: Because functions and methods only implement `__get__`, they are nonoverriding descriptors.
  A simple assignment like `my_obj.the_method = 7` means that further access to `the_method`
  through that instance will retrieve the number 7 — without affecting the class or other
  instances.  However, this issue does not interfere with special methods.  The interpreter
  only looks for special methods in the class itself; in other words, `repr(x)` is executed as
  `x.__class__.__repr__(x)`, so a `__repr__` attribute defined in `x` has no effect on
  `repr(x)`.  For the same reason, the existence of an attribute named `__getattr__` in an
  instance will not subvert the usual attribute access algorithm.

Here is a minimal caching descriptor, implementing only `__get__`:

```python
class lazy:
    """compute once per instance, then get out of the way"""

    def __init__(self, func):
        self.func = func

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        value = self.func(instance)
        instance.__dict__[self.name] = value  # the instance attribute will shadow us
        return value

class Report:
    @lazy
    def data(self):
        print('crunching numbers...')
        return [1, 2, 3]

r = Report()
r.data
# crunching numbers...
# [1, 2, 3]
r.data  # served from r.__dict__: the descriptor is not called again
# [1, 2, 3]
```

The fact that nonspecial methods can be overridden so easily in instances may sound fragile
and error prone, but in practice this rarely bites.  On the other hand, if you are doing a lot
of dynamic attribute creation, where the attribute names come from data you don't control (as
we did in [Dynamic Attributes and Properties](dynamic-attributes.md)), then you should be aware
of this and perhaps implement some filtering or escaping of the dynamic attribute names to
preserve your sanity.

> **Note**
>
> The `FrozenJSON` class in the previous chapter is safe from instance attributes shadowing
> methods because its only methods are special methods and the `build` class method.  Class
> methods are safe as long as they are always accessed through the class, as with
> `FrozenJSON.build` — later replaced by `__new__`.  The `Record` and `Event` classes are also
> safe: they implement only special methods, static methods, and properties.  Properties are
> overriding descriptors, so they are not shadowed by instance attributes.

To close this chapter, we'll cover two features we saw with properties that we have not
addressed in the context of descriptors: documentation and handling attempts to delete a
managed attribute.

## Descriptor Docstring and Overriding Deletion

The docstring of a descriptor class is used to document every instance of the descriptor in
the managed class.  For example, `help(LineItem.weight)` with the `Quantity` descriptor from
Take #5 shows the docstring of the `Quantity` class:

```python
LineItem.weight.__doc__
# 'a number greater than zero'
```

(`LineItem.weight` returns the `Quantity` instance because `Validated` doesn't implement
`__get__`; a `__get__` that returns `self` when `instance is None` gives the same result.)
That is somewhat unsatisfactory.  In the case of `LineItem`, it would
be good to add, for example, the information that `weight` must be in kilograms.  That would
be trivial with properties, because each property handles a specific managed attribute.  But
with descriptors, the same `Quantity` descriptor class is used for `weight` and `price`.  One
simple solution is to accept an optional `doc` argument and assign it to `self.__doc__` in the
descriptor's `__init__`: an instance attribute named `__doc__` takes precedence over the class
docstring when reading `LineItem.weight.__doc__` (although `help()` may still show the class
docstring, since it documents the object's type).

The second detail we discussed with properties, but have not addressed with descriptors, is
handling attempts to delete a managed attribute.  That can be done by implementing a
`__delete__` method alongside or instead of the usual `__get__` and/or `__set__` in the
descriptor class.  Real-world usage is rare, but here is a silly example:

```python
class Undeletable:
    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__[self.name]

    def __set__(self, instance, value):
        instance.__dict__[self.name] = value

    def __delete__(self, instance):
        raise AttributeError(f'{self.name!r} is here to stay')

class Monument:
    name = Undeletable()

m = Monument()
m.name = 'Colossus of Rhodes'
del m.name
# Traceback (most recent call last):
#     ...
# AttributeError: 'name' is here to stay
```

Note that a descriptor implementing only `__delete__` (without `__set__`) is still an
overriding descriptor: the data model considers any object with `__set__` *or* `__delete__` a
data descriptor.

## Type Hints for Descriptors

Static type checkers understand descriptors: the type of `obj.attr` is the return type of
`__get__` when called with an instance, and the accepted types for assignment come from the
`value` parameter of `__set__`.  Use `typing.overload` to distinguish access through the class
(`instance` is `None`) from access through an instance, and make the descriptor generic to
reuse it for different value types:

```python
from typing import Any, Callable, overload, Self

class Validated[T]:
    def __init__(self, check: Callable[[T], bool], message: str) -> None:
        self.check = check
        self.message = message

    def __set_name__(self, owner: type, name: str) -> None:
        self.name = name

    @overload
    def __get__(self, instance: None, owner: type) -> Self: ...
    @overload
    def __get__(self, instance: object, owner: type) -> T: ...
    def __get__(self, instance: object | None, owner: type) -> Self | T:
        if instance is None:
            return self
        return instance.__dict__[self.name]

    def __set__(self, instance: object, value: T) -> None:
        if not self.check(value):
            raise ValueError(f'{self.name} {self.message}')
        instance.__dict__[self.name] = value

class Product:
    name: Validated[str] = Validated(str.strip, 'cannot be blank')
    price: Validated[float] = Validated(lambda v: v > 0, 'must be > 0')

    def __init__(self, name: str, price: float) -> None:
        self.name = name
        self.price = price

p = Product('Kona coffee', 30.5)
p.name, p.price  # a type checker infers (str, float)
# ('Kona coffee', 30.5)
Product('Mystery box', -1)
# Traceback (most recent call last):
#     ...
# ValueError: price must be > 0
```

> **Tip**
>
> Descriptors work with [data classes](dataclasses.md), too: a field annotated as a descriptor
> type and assigned a descriptor instance as the default value gets the descriptor's
> `__set__` called by the generated `__init__`.  The data class machinery calls the
> descriptor's `__get__(None, cls)` to find the default value, so such a descriptor should
> return the default — or raise `AttributeError` if there is none — when accessed through the
> class.  See "Descriptor-typed fields" in the
> [`dataclasses` documentation](https://docs.python.org/3/library/dataclasses.html#descriptor-typed-fields).

## Summary

The first example of this chapter was a continuation of the `LineItem` examples from the
previous chapter.  In Take #3, we replaced properties with descriptors.  We saw that a
descriptor is a class that provides instances that are deployed as attributes in the managed
class.  Discussing this mechanism required special terminology, introducing terms such as
*managed instance* and *storage attribute*.

In Take #4 we removed the requirement that `Quantity` descriptors were declared with an
explicit `storage_name`, which was redundant and error prone.  The solution was to implement
the `__set_name__` special method in `Quantity`, to save the name of the managed attribute as
`self.storage_name`.  Take #5 showed how to subclass an abstract descriptor class to share code
while building specialized descriptors with some common functionality.

We then looked at the different behaviors of descriptors providing or omitting the `__set__`
method, making the crucial distinction between overriding and nonoverriding descriptors, a.k.a.
data and nondata descriptors.  Through detailed testing we uncovered when descriptors are in
control and when they are shadowed, bypassed, or overwritten, and summarized the attribute
lookup algorithm.

Following that, we studied a particular category of nonoverriding descriptors: methods.
Console experiments revealed how a function attached to a class becomes a method when accessed
through an instance, by leveraging the descriptor protocol — and why a class-based decorator
must implement `__get__` to decorate methods.  To conclude the chapter, we presented practical
tips, a brief look at how to document descriptors and handle deletion, and how to type hint
descriptors.

> **Note**
>
> **The design of `self`.**  The requirement to explicitly declare `self` as a first argument
> in methods is a controversial design decision in Python.  It's an example of "worse is
> better", a design philosophy described by Richard P. Gabriel, whose first priority is
> simplicity — especially of implementation.  The implementation of methods as descriptors
> wrapping plain functions is simple, even elegant, at the expense of the user interface: a
> method signature like `def zfill(self, width):` doesn't visually match the invocation
> `label.zfill(8)`.  Guido van Rossum explained his reasons in "Adding Support for User-Defined
> Classes", a post on his blog *The History of Python*.  Anyone unhappy about the explicit
> `self` can feel a lot better by considering the baffling semantics of the implicit `this` in
> JavaScript.

> **See also**
>
> * Raymond Hettinger's [Descriptor HowTo Guide](https://docs.python.org/3/howto/descriptor.html),
>   part of the HowTo collection in the official documentation, and
>   [Implementing Descriptors](https://docs.python.org/3/reference/datamodel.html#implementing-descriptors)
>   in the Data Model chapter.
> * [**PEP 487**](https://peps.python.org/pep-0487/) — Simpler customization of class creation,
>   which introduced `__set_name__` and includes an example of a validating descriptor.  Beware
>   that coverage of descriptors written before 2016 is likely to contain examples that are
>   needlessly complicated today, because `__set_name__` was not supported before Python 3.6.
> * *Python Cookbook*, 3rd ed., by David Beazley and Brian K. Jones: "8.10. Using Lazily
>   Computed Properties", "8.13. Implementing a Data Model or Type System" and "9.9. Defining
>   Decorators As Classes".
> * Alex Martelli's presentation "Python's Object Model", which covers properties and
>   descriptors in depth.
