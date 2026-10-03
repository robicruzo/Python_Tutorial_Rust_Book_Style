<a id="tutorial-index"></a>

# The Python Tutorial

> **Tip**
> 
> This tutorial is designed for
> *programmers* that are new to the Python language,
> **not** *beginners* who are new to programming.

Python is an easy to learn, powerful programming language. It has efficient
high-level data structures and a simple but effective approach to
object-oriented programming. Python’s elegant syntax and dynamic typing,
together with its interpreted nature, make it an ideal language for scripting
and rapid application development in many areas on most platforms.

The Python interpreter and the extensive standard library are freely available
in source or binary form for all major platforms from the Python website,
[https://www.python.org/](https://www.python.org/), and may be freely distributed. The same site also
contains distributions of and pointers to many free third party Python modules,
programs and tools, and additional documentation.

The Python interpreter is easily extended with new functions and data types
implemented in C or C++ (or other languages callable from C). Python is also
suitable as an extension language for customizable applications.

This tutorial introduces the reader informally to the basic concepts and
features of the Python language and system. Be aware that it expects you to
have a basic understanding of programming in general. It helps to have a Python
interpreter handy for hands-on experience, but all examples are self-contained,
so the tutorial can be read off-line as well.

For a description of standard objects and modules, see [Built-in Functions](https://docs.python.org/3/library/functions.html) and
[The Python Standard Library](https://docs.python.org/3/library/index.html).  [The Python Language Reference](https://docs.python.org/3/reference/index.html) gives a more formal definition of
the language.  To write extensions in C or C++, read [Extending and Embedding the Python Interpreter](https://docs.python.org/3/extending/index.html) and
[Python/C API Reference Manual](https://docs.python.org/3/c-api/index.html). There are also several books covering Python in depth.

This tutorial does not attempt to be comprehensive and cover every single
feature, or even every commonly used feature. Instead, it introduces many of
Python’s most noteworthy features, and will give you a good idea of the
language’s flavor and style. After reading it, you will be able to read and
write Python modules and programs, and you will be ready to learn more about the
various Python library modules described in [The Python Standard Library](https://docs.python.org/3/library/index.html).

The [Glossary](https://docs.python.org/3/glossary.html) is also worth going through.

## About This Edition

This edition presents the official tutorial in the style of the Rust book, expanded with
explanations, concepts and examples adapted from *Fluent Python*, 2nd edition, by Luciano
Ramalho (O'Reilly), and updated for Python 3.12 and later.  The original tutorial chapters
are kept as they are, with new chapters nested under the tutorial chapter they build upon:

* Under **An Informal Introduction to Python**: Unicode text and bytes.
* Under **More Control Flow Tools**: pattern matching, functions as objects, type hints in
  functions, decorators and closures, and design patterns with functions.
* Under **Data Structures**: sequences, dictionaries and sets, and object references.
* Under **Errors and Exceptions**: context managers and `else` blocks.
* Under **Classes**: the data model, data classes, Pythonic objects, sequence protocols,
  interfaces and ABCs, inheritance, more type hints, operator overloading, and iterators and
  generators.
* Two new parts, [Concurrency](concurrency.md) and [Metaprogramming](metaprogramming.md),
  cover threads, processes, `asyncio`, properties, descriptors and metaclasses.

The new chapters assume you have read the tutorial chapter above them, and are best read in
order.  Every runnable example shows its output in comments, so you can paste the code into
the interpreter and compare the results.
