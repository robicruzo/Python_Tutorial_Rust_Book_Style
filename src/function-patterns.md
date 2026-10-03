# Design Patterns with First-Class Functions

In software engineering, a *design pattern* is a general recipe for solving a
common design problem.  You don't need to know design patterns to follow this
chapter; the patterns used in the examples are explained as we go.  As Ralph
Johnson, one of the authors of the classic book on the subject, has put it,
conformity to patterns is not a measure of goodness.

The use of design patterns in programming was popularized by the landmark book
*Design Patterns: Elements of Reusable Object-Oriented Software* by Erich Gamma,
Richard Helm, Ralph Johnson and John Vlissides, a.k.a. "the Gang of Four".  The
book is a catalog of 23 patterns consisting of arrangements of classes,
exemplified with code in C++, but assumed to be useful in other object-oriented
languages as well.

Although design patterns are language independent, that does not mean every
pattern applies to every language.  For example,
[Iterators, Generators, and Classic Coroutines](iterators-generators.md) shows that
it doesn't make sense to emulate the recipe of the Iterator pattern in Python,
because the pattern is embedded in the language and ready to use in the form of
generators, which don't need classes to work and require less code than the
classic recipe.  The authors of *Design Patterns* acknowledge in their introduction
that the implementation language determines which patterns are relevant: their
patterns assume Smalltalk/C++-level language features; if they had assumed
procedural languages, they might have included patterns called "Inheritance",
"Encapsulation" and "Polymorphism"; and some of their patterns are supported
directly by less common object-oriented languages.

In his 1996 presentation "Design Patterns in Dynamic Languages", Peter Norvig
states that 16 of the 23 patterns in the original book become either "invisible or
simpler" in a dynamic language.  He was talking about Lisp and Dylan, but many of
the relevant dynamic features are also present in Python.  In particular, in the
context of languages with first-class functions, Norvig suggests rethinking the
classic patterns known as Strategy, Command, Template Method and Visitor.

This chapter shows how, in some cases, functions can do the same work as classes,
with code that is more readable and concise.  We will refactor an implementation of
Strategy using functions as objects, removing a lot of boilerplate code, and
discuss a similar approach to simplifying the Command pattern.  It builds on
[Functions as First-Class Objects](first-class-functions.md) and
[Decorators and Closures](decorators.md).

## Case Study: Refactoring Strategy

Strategy is a good example of a design pattern that can be simpler in Python if you
leverage functions as first-class objects.  First we describe and implement Strategy
using the "classic" structure described in *Design Patterns*.  If you are familiar
with it, you can skip to [Function-Oriented Strategy](#function-oriented-strategy).

### Classic Strategy

*Design Patterns* summarizes the Strategy pattern like this: define a family of
algorithms, encapsulate each one, and make them interchangeable; Strategy lets the
algorithm vary independently from clients that use it.

A clear example of Strategy applied in the e-commerce domain is computing discounts
to orders according to the attributes of the customer or inspection of the ordered
items.  Consider an online store with these discount rules:

* Customers with 1,000 or more fidelity points get a global 5% discount per order.
* A 10% discount is applied to each line item with 20 or more units in the same
  order.
* Orders with at least 10 distinct items get a 7% global discount.

For brevity, let's assume that only one discount may be applied to an order.  The
participants of the Strategy pattern are:

*Context*
: Provides a service by delegating some computation to interchangeable components
  that implement alternative algorithms.  In the e-commerce example, the context is
  an `Order`, which is configured to apply a promotional discount according to one
  of several algorithms.

*Strategy*
: The interface common to the components that implement the different algorithms.
  In our example, this role is played by an abstract class called `Promotion`.

*Concrete strategy*
: One of the concrete subclasses of Strategy.  `FidelityPromo`, `BulkItemPromo` and
  `LargeOrderPromo` are the three concrete strategies implemented.

As described in *Design Patterns*, the concrete strategy is chosen by the client of
the context class.  In our example, before instantiating an order, the system would
somehow select a promotional discount strategy and pass it to the `Order`
constructor.  The selection of the strategy is outside the scope of the pattern.

```python
from abc import ABC, abstractmethod
from collections.abc import Sequence
from decimal import Decimal
from typing import NamedTuple, Optional

class Customer(NamedTuple):
    name: str
    fidelity: int

class LineItem(NamedTuple):
    product: str
    quantity: int
    price: Decimal

    def total(self) -> Decimal:
        return self.price * self.quantity

class Order(NamedTuple):  # the Context
    customer: Customer
    cart: Sequence[LineItem]
    promotion: Optional['Promotion'] = None

    def total(self) -> Decimal:
        totals = (item.total() for item in self.cart)
        return sum(totals, start=Decimal(0))

    def due(self) -> Decimal:
        if self.promotion is None:
            discount = Decimal(0)
        else:
            discount = self.promotion.discount(self)
        return self.total() - discount

    def __repr__(self):
        return f'<Order total: {self.total():.2f} due: {self.due():.2f}>'

class Promotion(ABC):  # the Strategy: an abstract base class
    @abstractmethod
    def discount(self, order: Order) -> Decimal:
        """Return discount as a positive dollar amount"""

class FidelityPromo(Promotion):  # first Concrete Strategy
    """5% discount for customers with 1000 or more fidelity points"""

    def discount(self, order: Order) -> Decimal:
        rate = Decimal('0.05')
        if order.customer.fidelity >= 1000:
            return order.total() * rate
        return Decimal(0)

class BulkItemPromo(Promotion):  # second Concrete Strategy
    """10% discount for each LineItem with 20 or more units"""

    def discount(self, order: Order) -> Decimal:
        discount = Decimal(0)
        for item in order.cart:
            if item.quantity >= 20:
                discount += item.total() * Decimal('0.1')
        return discount

class LargeOrderPromo(Promotion):  # third Concrete Strategy
    """7% discount for orders with 10 or more distinct items"""

    def discount(self, order: Order) -> Decimal:
        distinct_items = {item.product for item in order.cart}
        if len(distinct_items) >= 10:
            return order.total() * Decimal('0.07')
        return Decimal(0)
```

`Promotion` is written as an abstract base class (ABC), to use the
`@abstractmethod` decorator and make the pattern more explicit; ABCs are covered in
[Interfaces, Protocols, and ABCs](protocols-abcs.md).  (The quoted `'Promotion'` in
the type hint of `Order.promotion` is a *forward reference*: `Promotion` is not yet
defined at that point.)  Here is the code in use:

```python
joe = Customer('John Doe', 0)
ann = Customer('Ann Smith', 1100)
cart = (LineItem('banana', 4, Decimal('.5')),
        LineItem('apple', 10, Decimal('1.5')),
        LineItem('watermelon', 5, Decimal(5)))
Order(joe, cart, FidelityPromo())
# <Order total: 42.00 due: 42.00>
Order(ann, cart, FidelityPromo())
# <Order total: 42.00 due: 39.90>
banana_cart = (LineItem('banana', 30, Decimal('.5')),
               LineItem('apple', 10, Decimal('1.5')))
Order(joe, banana_cart, BulkItemPromo())
# <Order total: 30.00 due: 28.50>
long_cart = tuple(LineItem(str(sku), 1, Decimal(1))
                 for sku in range(10))
Order(joe, long_cart, LargeOrderPromo())
# <Order total: 10.00 due: 9.30>
Order(joe, cart, LargeOrderPromo())
# <Order total: 42.00 due: 42.00>
```

There are two customers: `joe` has 0 fidelity points, `ann` has 1,100.  The
`FidelityPromo` gives no discount to `joe`, but `ann` gets 5% because she has at least
1,000 points.  The `banana_cart` has 30 units of the `"banana"` product and 10 apples,
and thanks to the `BulkItemPromo`, `joe` gets a $1.50 discount on the bananas.
`long_cart` has 10 different items at $1.00 each, so `joe` gets a 7% discount on the
whole order because of `LargeOrderPromo`.

This works perfectly well, but the same functionality can be implemented with less
code in Python by using functions as objects.

### Function-Oriented Strategy

Each concrete strategy above is a class with a single method, `discount`.
Furthermore, the strategy instances have no state (no instance attributes).  You
could say they look a lot like plain functions, and you would be right.  Here is a
refactoring that replaces the concrete strategies with simple functions and removes
the `Promotion` abstract class.  Only small adjustments are needed in the `Order`
class:

```python
from collections.abc import Sequence, Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import NamedTuple

class Customer(NamedTuple):
    name: str
    fidelity: int

class LineItem(NamedTuple):
    product: str
    quantity: int
    price: Decimal

    def total(self):
        return self.price * self.quantity

@dataclass(frozen=True)
class Order:  # the Context
    customer: Customer
    cart: Sequence[LineItem]
    promotion: Callable[['Order'], Decimal] | None = None

    def total(self) -> Decimal:
        totals = (item.total() for item in self.cart)
        return sum(totals, start=Decimal(0))

    def due(self) -> Decimal:
        if self.promotion is None:
            discount = Decimal(0)
        else:
            discount = self.promotion(self)
        return self.total() - discount

    def __repr__(self):
        return f'<Order total: {self.total():.2f} due: {self.due():.2f}>'

def fidelity_promo(order: Order) -> Decimal:
    """5% discount for customers with 1000 or more fidelity points"""
    if order.customer.fidelity >= 1000:
        return order.total() * Decimal('0.05')
    return Decimal(0)

def bulk_item_promo(order: Order) -> Decimal:
    """10% discount for each LineItem with 20 or more units"""
    discount = Decimal(0)
    for item in order.cart:
        if item.quantity >= 20:
            discount += item.total() * Decimal('0.1')
    return discount

def large_order_promo(order: Order) -> Decimal:
    """7% discount for orders with 10 or more distinct items"""
    distinct_items = {item.product for item in order.cart}
    if len(distinct_items) >= 10:
        return order.total() * Decimal('0.07')
    return Decimal(0)
```

The type hint of `promotion` says it may be `None`, or a callable that takes an
`Order` argument and returns a `Decimal`.  To compute a discount, `due` calls the
`self.promotion` callable, passing `self` as an argument.  There is no abstract class,
and each strategy is a function.

> **Note**
>
> Why `self.promotion(self)`?  In the `Order` class, `promotion` is not a method.
> It's an instance attribute that happens to be callable.  So the first part of the
> expression, `self.promotion`, retrieves that callable.  To invoke it, we must
> provide an instance of `Order`, which in this case is `self`.  That's why `self`
> appears twice in that expression.  [Methods Are Descriptors](descriptors.md#methods-are-descriptors)
> explains the mechanism that binds methods to instances automatically; it does not
> apply to `promotion` because it is not a method.

The code is shorter than before, and using the new `Order` is also a bit simpler:

```python
joe = Customer('John Doe', 0)
ann = Customer('Ann Smith', 1100)
cart = [LineItem('banana', 4, Decimal('.5')),
        LineItem('apple', 10, Decimal('1.5')),
        LineItem('watermelon', 5, Decimal(5))]
Order(joe, cart, fidelity_promo)
# <Order total: 42.00 due: 42.00>
Order(ann, cart, fidelity_promo)
# <Order total: 42.00 due: 39.90>
banana_cart = [LineItem('banana', 30, Decimal('.5')),
               LineItem('apple', 10, Decimal('1.5'))]
Order(joe, banana_cart, bulk_item_promo)
# <Order total: 30.00 due: 28.50>
long_cart = [LineItem(str(item_code), 1, Decimal(1))
              for item_code in range(10)]
Order(joe, long_cart, large_order_promo)
# <Order total: 10.00 due: 9.30>
Order(joe, cart, large_order_promo)
# <Order total: 42.00 due: 42.00>
```

To apply a discount strategy to an `Order`, just pass the promotion function as an
argument.  There is no need to instantiate a new promotion object with each new
order: the functions are ready to use.

It is interesting to note that *Design Patterns* suggests that "Strategy objects often
make good flyweights", and it defines a flyweight as "a shared object that can be used
in multiple contexts simultaneously".  The sharing is recommended to reduce the cost
of creating a new concrete strategy object when the same strategy is applied over and
over again with every new context, with every new `Order` instance in our example.  So,
to overcome a drawback of the Strategy pattern, its runtime cost, the authors
recommend applying yet another pattern.  Meanwhile, the line count and maintenance
cost of your code are piling up.

A thornier use case, with complex concrete strategies holding internal state, may
require all the pieces of the Strategy and Flyweight patterns combined.  But often
concrete strategies have no internal state; they only deal with data from the
context.  If that is the case, then by all means use plain old functions instead of
coding single-method classes implementing a single-method interface declared in yet
another class.  A function is more lightweight than an instance of a user-defined
class, and there is no need for Flyweight, because each strategy function is created
just once per Python process when it loads the module.  A plain function is also "a
shared object that can be used in multiple contexts simultaneously".

Now that we have implemented the Strategy pattern with functions, other
possibilities emerge.  Suppose you want to create a "metastrategy" that selects the
best available discount for a given `Order`.  The following sections show additional
refactorings that implement this requirement using a variety of approaches that
leverage functions and modules as objects.

### Choosing the Best Strategy: Simple Approach

Given the same customers and shopping carts, here is how the new `best_promo`
function should behave:

<!-- nocheck -->
```python
Order(joe, long_cart, best_promo)
# <Order total: 10.00 due: 9.30>
Order(joe, banana_cart, best_promo)
# <Order total: 30.00 due: 28.50>
Order(ann, cart, best_promo)
# <Order total: 42.00 due: 39.90>
```

`best_promo` selected the `large_order_promo` for customer `joe`'s long cart; for the
banana cart, `joe` got the discount from `bulk_item_promo`; and checking out with a
simple cart, `best_promo` gave loyal customer `ann` the discount for the
`fidelity_promo`.  The implementation of `best_promo` is very simple:

```python
promos = [fidelity_promo, bulk_item_promo, large_order_promo]

def best_promo(order: Order) -> Decimal:
    """Compute the best discount available"""
    return max(promo(order) for promo in promos)

Order(joe, long_cart, best_promo)
# <Order total: 10.00 due: 9.30>
Order(joe, banana_cart, best_promo)
# <Order total: 30.00 due: 28.50>
Order(ann, cart, best_promo)
# <Order total: 42.00 due: 39.90>
```

`promos` is a list of the strategies implemented as functions.  `best_promo` takes an
instance of `Order` as argument, as do the other `*_promo` functions, and uses a
generator expression to apply each of the functions from `promos` to the order,
returning the maximum discount computed.  Once you get used to the idea that functions
are first-class objects, it naturally follows that building data structures holding
functions often makes sense.

Although this works and is easy to read, there is some duplication that could lead
to a subtle bug: to add a new promotion strategy, you need to write the function *and*
remember to add it to the `promos` list, or else the new promotion will work when
explicitly passed as an argument to `Order`, but will not be considered by
`best_promo`.  Read on for a couple of solutions to this issue.

### Finding Strategies in a Module

Modules in Python are also first-class objects, and the standard library provides
several functions to handle them.  The built-in
[`globals()`](https://docs.python.org/3/library/functions.html#globals) returns a
dictionary representing the current global symbol table.  This is always the
dictionary of the current module (inside a function or method, this is the module
where it is defined, not the module from which it is called).

Here is a somewhat hackish way of using `globals` to help `best_promo` automatically
find the other available `*_promo` functions:

<!-- nocheck -->
```python
from decimal import Decimal
from strategy import Order
from strategy import (
    fidelity_promo, bulk_item_promo, large_order_promo
)

promos = [promo for name, promo in globals().items()
                if name.endswith('_promo') and
                   name != 'best_promo'
]

def best_promo(order: Order) -> Decimal:
    """Compute the best discount available"""
    return max(promo(order) for promo in promos)
```

We import the promotion functions so they are available in the global namespace.
(Linters complain that these names are imported but not used; static analysis tools
cannot understand the dynamic nature of Python.)  Then we iterate over each item in
the `dict` returned by `globals()`, selecting only values whose name ends with the
`_promo` suffix, and filtering out `best_promo` itself, to avoid an infinite recursion
when `best_promo` is called.  There are no changes in `best_promo`.

Another way of collecting the available promotions is to create a module and put all
the strategy functions there, except for `best_promo`.  Here the list of strategy
functions is built by introspection of a separate module called `promotions`, with
the help of the [`inspect`](https://docs.python.org/3/library/inspect.html) module,
which provides high-level introspection functions:

<!-- nocheck -->
```python
from decimal import Decimal
import inspect

from strategy import Order
import promotions

promos = [func for _, func in inspect.getmembers(promotions, inspect.isfunction)]

def best_promo(order: Order) -> Decimal:
    """Compute the best discount available"""
    return max(promo(order) for promo in promos)
```

The function `inspect.getmembers` returns the attributes of an object (in this case,
the `promotions` module), optionally filtered by a predicate (a Boolean function).
We use `inspect.isfunction` to get only the functions from the module.

This works regardless of the names given to the functions; all that matters is that
the `promotions` module contains only functions that calculate discounts given orders.
Of course, that is an implicit assumption of the code.  If someone were to create a
function with a different signature in the `promotions` module, then `best_promo`
would break while trying to apply it to an order.  We could add more stringent tests
to filter the functions, by inspecting their arguments for instance.  The point here
is not to offer a complete solution, but to highlight one possible use of module
introspection.

A more explicit alternative to dynamically collecting promotional discount functions
is to use a simple decorator.

## Decorator-Enhanced Strategy Pattern

Recall that the main issue with the simple approach is the repetition of the function
names in their definitions and then in the `promos` list used by `best_promo`.  The
repetition is problematic because someone may add a new promotional strategy function
and forget to add it to the `promos` list, in which case `best_promo` will silently
ignore the new strategy, introducing a subtle bug.  The registration technique covered
in [Registration Decorators](decorators.md#registration-decorators) solves this
problem:

```python
type Promotion = Callable[[Order], Decimal]

promos: list[Promotion] = []

def promotion(promo: Promotion) -> Promotion:
    promos.append(promo)
    return promo

def best_promo(order: Order) -> Decimal:
    """Compute the best discount available"""
    return max(promo(order) for promo in promos)

@promotion
def fidelity(order: Order) -> Decimal:
    """5% discount for customers with 1000 or more fidelity points"""
    if order.customer.fidelity >= 1000:
        return order.total() * Decimal('0.05')
    return Decimal(0)

@promotion
def bulk_item(order: Order) -> Decimal:
    """10% discount for each LineItem with 20 or more units"""
    discount = Decimal(0)
    for item in order.cart:
        if item.quantity >= 20:
            discount += item.total() * Decimal('0.1')
    return discount

@promotion
def large_order(order: Order) -> Decimal:
    """7% discount for orders with 10 or more distinct items"""
    distinct_items = {item.product for item in order.cart}
    if len(distinct_items) >= 10:
        return order.total() * Decimal('0.07')
    return Decimal(0)

[promo.__name__ for promo in promos]
# ['fidelity', 'bulk_item', 'large_order']
Order(ann, cart, best_promo)
# <Order total: 42.00 due: 39.90>
```

The `promos` list is a module global, and starts empty.  `promotion` is a
registration decorator: it returns the `promo` function unchanged, after appending it
to the `promos` list.  No changes are needed to `best_promo`, because it relies on the
`promos` list, and any function decorated by `@promotion` will be added to `promos`.

This solution has several advantages over the others presented before:

* The promotion strategy functions don't have to use special names; there's no need
  for the `_promo` suffix.
* The `@promotion` decorator highlights the purpose of the decorated function, and
  also makes it easy to temporarily disable a promotion: just comment out the
  decorator.
* Promotional discount strategies may be defined in other modules, anywhere in the
  system, as long as the `@promotion` decorator is applied to them.

Next we discuss Command, another design pattern that is sometimes implemented via
single-method classes when plain functions would do.

## The Command Pattern

Command is another design pattern that can be simplified by the use of functions
passed as arguments.  The goal of Command is to decouple an object that invokes an
operation (the *invoker*) from the provider object that implements it (the
*receiver*).  In the example from *Design Patterns*, each invoker is a menu item in a
graphical application, and the receivers are the document being edited or the
application itself.

The idea is to put a `Command` object between the two, implementing an interface with
a single method, `execute`, which calls some method in the receiver to perform the
desired operation.  That way the invoker does not need to know the interface of the
receiver, and different receivers can be adapted through different `Command`
subclasses.  The invoker is configured with a concrete command and calls its `execute`
method to operate it.  A `MacroCommand` may store a sequence of commands; its
`execute()` method calls the same method in each command stored.

*Design Patterns* says that "Commands are an object-oriented replacement for
callbacks."  The question is: do we need an object-oriented replacement for
callbacks?  Sometimes yes, but not always.

Instead of giving the invoker a `Command` instance, we can simply give it a function.
Instead of calling `command.execute()`, the invoker can just call `command()`.  The
`MacroCommand` can be implemented with a class implementing `__call__()`.  Instances of
`MacroCommand` are callables, each holding a list of functions for future invocation:

```python
class MacroCommand:
    """A command that executes a list of commands"""

    def __init__(self, commands):
        self.commands = list(commands)

    def __call__(self):
        for command in self.commands:
            command()

macro = MacroCommand([lambda: print('open'), lambda: print('paste')])
macro()
# open
# paste
```

Building a list from the `commands` argument ensures that it is iterable and keeps a
local copy of the command references in each `MacroCommand` instance.  When an
instance of `MacroCommand` is invoked, each command in `self.commands` is called in
sequence.

More advanced uses of the Command pattern, to support undo, for example, may require
more than a simple callback function.  Even then, Python provides a couple of
alternatives that deserve consideration:

* A callable instance like `MacroCommand` can keep whatever state is necessary, and
  provide extra methods in addition to `__call__()`.
* A closure can be used to hold the internal state of a function between calls.

At a high level, the approach here was similar to the one we applied to Strategy:
replacing with callables the instances of a participant class that implemented a
single-method interface.  After all, every Python callable implements a single-method
interface, and that method is named `__call__`.  (Fun fact: since a function's
`__call__` is itself callable, `turtle.__call__.__call__.__call__()` works just like
`turtle()`.  It's turtles all the way down.)

## Summary

As Peter Norvig pointed out a couple of years after the classic *Design Patterns* book
appeared, "16 of 23 patterns have qualitatively simpler implementation in Lisp or
Dylan than in C++ for at least some uses of each pattern".  Python shares some of the
dynamic features of the Lisp and Dylan languages, in particular first-class functions.

Reflecting on the 20th anniversary of *Design Patterns*, Ralph Johnson stated that one
of the failings of the book is "too much emphasis on patterns as end-points instead
of steps in the design process."  In this chapter we used the Strategy pattern as a
starting point: a working solution that we could simplify using first-class
functions.

In many cases, functions or callable objects provide a more natural way of
implementing callbacks in Python than mimicking the Strategy or Command patterns as
described in *Design Patterns*.  The refactoring of Strategy and the discussion of
Command are examples of a more general insight: sometimes you may encounter a design
pattern or an interface that requires components to implement a single method with a
generic-sounding name such as "execute", "run" or "do_it".  Such patterns or interfaces
can often be implemented with less boilerplate code in Python using functions as
first-class objects.

> **See also**
>
> * "Recipe 8.21. Implementing the Visitor Pattern", in the *Python Cookbook*, 3rd
>   ed., presents an elegant implementation of the Visitor pattern in which a
>   `NodeVisitor` class handles methods as first-class objects.  (Python's
>   `singledispatch`, from [Decorators and Closures](decorators.md), is a limited form
>   of the multimethods that *Design Patterns* suggests as a simpler way to implement
>   Visitor.)
> * Peter Norvig's "Design Patterns in Dynamic Languages" shows how first-class
>   functions and other dynamic features make several of the original patterns
>   simpler or unnecessary.
> * *Design Patterns in Ruby* by Russ Olsen has many insights that also apply to
>   Python, a language semantically close to Ruby.
> * The introduction of the original *Design Patterns* book is worth reading for its
>   design principles, "Program to an interface, not an implementation" and "Favor
>   object composition over class inheritance".
