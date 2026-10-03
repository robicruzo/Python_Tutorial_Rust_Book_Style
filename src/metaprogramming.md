# Metaprogramming

*Metaprogramming* is writing code that manipulates code: classes that build attributes on
the fly, objects that control how attributes of other objects are read and written, and
functions or classes that create or modify classes.  Python makes these techniques
unusually accessible, which is both a blessing and a temptation.

The chapters in this part build on each other:

* [Dynamic Attributes and Properties](dynamic-attributes.md) covers the simplest ways to
  compute attributes on demand: the `@property` decorator and the `__getattr__` special
  method, along with `functools.cached_property`, property factories, and an overview of
  the built-in functions and special methods for attribute handling.
* [Attribute Descriptors](descriptors.md) explains the protocol behind properties,
  methods, `classmethod` and `staticmethod`: descriptors.  You'll learn the difference
  between overriding and nonoverriding descriptors, and why methods are descriptors.
* [Class Metaprogramming](class-metaprogramming.md) is about creating and customizing
  classes at runtime: `type` as a class factory, `__init_subclass__`, class decorators,
  what happens at import time, and metaclasses — including when *not* to use them.

> **Warning**
>
> Metaprogramming is a powerful tool for library and framework authors.  In application
> code, it is rarely the simplest solution.  As Tim Peters wrote: "Metaclasses are deeper
> magic than 99% of users should ever worry about.  If you wonder whether you need them,
> you don't."  The same applies, to a lesser degree, to the other techniques in this part.
> Learn them to understand how the frameworks you use work, and reach for them only when
> plainer code would be clearly worse.
