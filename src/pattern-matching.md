# Pattern Matching in Depth

The most visible feature added in Python 3.10 is *structural pattern matching*
with the `match`/`case` statement, proposed in
[**PEP 634**](https://peps.python.org/pep-0634/).  The tutorial introduced it in
[`match` Statements](controlflow.md#tut-match).  This chapter goes deeper: it covers
sequence, mapping and class patterns, OR-patterns, guards, and the capture rules
that trip people up, and it ends with a case study in which pattern matching drives
a small interpreter for a subset of the Scheme language.

On the surface, `match`/`case` may look like the `switch`/`case` statement of C and
its descendants, but that's only half the story.  One key improvement over `switch`
is *destructuring*, a more advanced form of unpacking.  Destructuring is a new word
in the Python vocabulary, but it is commonly used in the documentation of languages
that support pattern matching, like Scala and Elixir.  (A sequence of
`if/elif/elif/.../else` blocks is a fine replacement for `switch/case`, and it doesn't
suffer from the fallthrough and dangling-`else` problems that some languages copied
from C.)

## The Shape of a `match` Statement

A `match` statement has a *subject*, the expression after the `match` keyword, and one
or more `case` clauses.  Each `case` clause has a *pattern* and an optional *guard*
introduced by `if`.  Python tries the patterns in order; the first one that matches
the subject, and whose guard (if any) is true, has its block executed, and then the
`match` statement ends.  If no case matches, nothing happens: there is no error,
which can be a silent failure, so it is often good practice to end with a catch-all
case.

Here is a first example of `match`/`case` handling sequences.  Imagine you are
designing a robot that accepts commands sent as sequences of words and numbers, like
`BEEPER 440 3`.  After splitting into parts and parsing the numbers, you'd have a
message like `['BEEPER', 440, 3]`.  You could use a method like this to handle such
messages:

<!-- nocheck -->
```python
def handle_command(self, message):
    match message:
        case ['BEEPER', frequency, times]:
            self.beep(times, frequency)
        case ['NECK', angle]:
            self.rotate_neck(angle)
        case ['LED', ident, intensity]:
            self.leds[ident].set_brightness(ident, intensity)
        case ['LED', ident, red, green, blue]:
            self.leds[ident].set_color(ident, red, green, blue)
        case _:
            raise InvalidCommand(message)
```

The expression after the `match` keyword is the subject: the data that Python will
try to match against the patterns in each `case` clause.  The first pattern matches
any subject that is a sequence with three items; the first item must be the string
`'BEEPER'`, and the second and third items can be anything, and are bound to the
variables `frequency` and `times`, in that order.  The second pattern matches any
subject with two items, the first being `'NECK'`.  The third matches a subject with
three items starting with `'LED'`; if the number of items does not match, Python
proceeds to the next case, another sequence pattern starting with `'LED'`, now with
five items.  The last is the default case: it matches any subject that did not match
a previous pattern.  The `_` variable is special, as you'll see.

## Kinds of Patterns

Patterns are built from a small number of pieces that can be nested freely:

*Literal patterns*
: numbers, strings, `None`, `True` and `False` match values equal to them (`None`,
  `True` and `False` are compared with `is`).

*Capture patterns*
: a bare name, like `frequency`, matches anything and binds the matched value to that
  name.

*The wildcard `_`*
: matches anything but binds nothing.

*Value patterns*
: a dotted name, like `Color.RED` or `http.HTTPStatus.OK`, matches values equal to the
  value of that name.

*Sequence patterns*
: like `[a, b, *rest]` or `(x, y)`, match sequences item by item.

*Mapping patterns*
: like `{'type': 'book', 'api': 2}`, match mappings by key.

*Class patterns*
: like `Point(x=0)` or `float(lat)`, match instances by type and attributes.

*OR-patterns*
: like `401 | 403 | 404`, match if any alternative matches.

*AS-patterns*
: like `(lat, lon) as coord`, bind the subject of a subpattern to a name.

### Capture Patterns and Value Patterns

The rule that a bare name is a capture pattern is the most common source of
surprise.  This looks like it compares the subject to a constant, but it doesn't:

```python
NOT_FOUND = 404
status = 200
match status:
    case NOT_FOUND:  # DANGER: this binds NOT_FOUND, it doesn't compare!
        print('not found')
# not found
NOT_FOUND
# 200
```

`case NOT_FOUND:` matches any subject, because Python sees `NOT_FOUND` as a capture
variable, which is then bound to the subject, clobbering the global.  (In fact, a
bare capture pattern makes the rest of the cases unreachable, and Python reports a
`SyntaxError` if any cases come after it.)  To compare against a named constant, use a
dotted name: an attribute of a module, a class or an enum.  Enums are ideal for this:

```python
from enum import Enum

class Color(Enum):
    RED = 'red'
    GREEN = 'green'
    BLUE = 'blue'

def describe(color):
    match color:
        case Color.RED:
            return 'I see red!'
        case Color.GREEN | Color.BLUE:
            return 'cool colors'

describe(Color('green'))
# 'cool colors'
```

## Pattern Matching with Sequences

As a first example of destructuring, here is part of the cities report from
[Nested Unpacking](sequences.md#nested-unpacking), rewritten with `match`/`case`:

```python
metro_areas = [
    ('Tokyo', 'JP', 36.933, (35.689722, 139.691667)),
    ('Delhi NCR', 'IN', 21.935, (28.613889, 77.208889)),
    ('Mexico City', 'MX', 20.142, (19.433333, -99.133333)),
    ('New York-Newark', 'US', 20.104, (40.808611, -74.020386)),
    ('São Paulo', 'BR', 19.649, (-23.547778, -46.635833)),
]

def main():
    print(f'{"":15} | {"latitude":>9} | {"longitude":>9}')
    for record in metro_areas:
        match record:
            case [name, _, _, (lat, lon)] if lon <= 0:
                print(f'{name:15} | {lat:9.4f} | {lon:9.4f}')

main()
#                 |  latitude | longitude
# Mexico City     |   19.4333 |  -99.1333
# New York-Newark |   40.8086 |  -74.0204
# São Paulo       |  -23.5478 |  -46.6358
```

The subject of this `match` is `record`, each of the tuples in `metro_areas`.  The
`case` clause has two parts: a pattern and an optional guard with the `if` keyword.

In general, a sequence pattern matches the subject if:

1. the subject is a sequence, and
2. the subject and the pattern have the same number of items, and
3. each corresponding item matches, including nested items.

For example, the pattern `[name, _, _, (lat, lon)]` matches a sequence with four
items, and the last item must be a two-item sequence.

Sequence patterns may be written as tuples or lists or any combination of nested
tuples and lists; it makes no difference which syntax you use, since in a sequence
pattern square brackets and parentheses mean the same thing.  The example uses a list
with a nested 2-tuple just to avoid repeating brackets or parentheses.

A sequence pattern can match instances of most actual or virtual subclasses of
`collections.abc.Sequence`, with the exception of `str`, `bytes` and `bytearray`.

> **Warning**
>
> Instances of `str`, `bytes` and `bytearray` are not handled as sequences in the
> context of `match`/`case`.  A subject of one of those types is treated as an
> "atomic" value, like the integer 987 is treated as one value, not a sequence of
> digits.  Treating those three types as sequences could cause bugs due to unintended
> matches.  If you want to treat an object of those types as a sequence subject,
> convert it in the `match` clause, as with `tuple(phone)` here:
>
> ```python
> def region(phone):
>     match tuple(phone):
>         case ['1', *rest]:  # North America and Caribbean
>             return 'NANP'
>         case ['2', *rest]:  # Africa and some territories
>             return 'Africa'
>         case ['3' | '4', *rest]:  # Europe
>             return 'Europe'
>
> region('251911234567')
> # 'Africa'
> ```

In the standard library, these types are compatible with sequence patterns:

```text
list     memoryview    array.array
tuple    range         collections.deque
```

Unlike unpacking, patterns don't destructure iterables that are not sequences (such as
iterators).

The `_` symbol is special in patterns: it matches any single item in that position,
but it is never bound to the value of the matched item.  Also, `_` is the only variable
that can appear more than once in a pattern.

You can bind any part of a pattern with a variable using the `as` keyword:

<!-- nocheck -->
```python
case [name, _, _, (lat, lon) as coord]:
```

Given the subject `['Shanghai', 'CN', 24.9, (31.1, 121.3)]`, that pattern will match,
and set the following variables:

| Variable | Set value |
|---|---|
| `name` | `'Shanghai'` |
| `lat` | `31.1` |
| `lon` | `121.3` |
| `coord` | `(31.1, 121.3)` |

You can make patterns more specific by adding type information.  For example, the
following pattern matches the same nested sequence structure as the previous one, but
the first item must be an instance of `str`, and both items in the 2-tuple must be
instances of `float`:

<!-- nocheck -->
```python
case [str(name), _, _, (float(lat), float(lon))]:
```

> **Tip**
>
> The expressions `str(name)` and `float(lat)` look like constructor calls, which
> you'd use to convert `name` and `lat` to `str` and `float`.  But in the context of a
> pattern, that syntax performs a runtime type check: the preceding pattern matches a
> four-item sequence in which item 0 must be a `str`, and item 3 must be a pair of
> floats.  Additionally, the `str` in item 0 is bound to the `name` variable, and the
> floats in item 3 are bound to `lat` and `lon`.  So, although `str(name)` borrows the
> syntax of a constructor call, the semantics are completely different in a pattern.
> Class patterns are covered [below](#pattern-matching-class-instances).

On the other hand, if you want to match any subject sequence starting with a `str` and
ending with a nested sequence of two floats, you can write:

<!-- nocheck -->
```python
case [str(name), *_, (float(lat), float(lon))]:
```

The `*_` matches any number of items, without binding them to a variable.  Using
`*extra` instead of `*_` would bind the items to `extra` as a `list` with zero or more
items.

The optional guard clause starting with `if` is evaluated only if the pattern matches,
and it can reference variables bound in the pattern, as in the cities example.  The
block runs only if the pattern matches *and* the guard expression is truthy.

> **Tip**
>
> Destructuring with patterns is so expressive that sometimes a `match` with a single
> `case` can make code simpler.  Guido van Rossum has a collection of `match`/`case`
> examples, including one that he titled "A very deep iterable and type match with
> extraction".

The cities example is not an improvement over the plain `for` loop with unpacking;
it's just a way of contrasting two ways of doing the same thing.  The next example
shows how pattern matching contributes to clear, concise and effective code.

### Pattern Matching Sequences in an Interpreter

Peter Norvig of Stanford University wrote `lis.py`: an interpreter for a subset of the
Scheme dialect of the Lisp programming language in 132 lines of beautiful and readable
Python code.  Its two main functions are `parse` and `evaluate`.  (Norvig named the
latter `eval`; it's renamed here to avoid confusion with Python's `eval` built-in.)
The parser takes Scheme parenthesized expressions and returns Python lists:

<!-- nocheck -->
```python
parse('(gcd 18 45)')
# ['gcd', 18, 45]
parse('''
(define double
    (lambda (n)
        (* n 2)))
''')
# ['define', 'double', ['lambda', ['n'], ['*', 'n', 2]]]
```

The evaluator takes lists like these and executes them.  The first example calls a
`gcd` function with 18 and 45 as arguments; when evaluated, it computes the greatest
common divisor of the arguments: 9.  The second example defines a function named
`double` with a parameter `n`, whose body is the expression `(* n 2)`.  The result of
calling a function in Scheme is the value of the last expression in its body.

Here is Norvig's evaluator with minor changes, abbreviated to show only the sequence
handling, without pattern matching:

<!-- nocheck -->
```python
def evaluate(exp: Expression, env: Environment) -> Any:
    "Evaluate an expression in an environment."
    if isinstance(exp, Symbol):      # variable reference
        return env[exp]
    # ... lines omitted
    elif exp[0] == 'quote':          # (quote exp)
        (_, x) = exp
        return x
    elif exp[0] == 'if':             # (if test conseq alt)
        (_, test, consequence, alternative) = exp
        if evaluate(test, env):
            return evaluate(consequence, env)
        else:
            return evaluate(alternative, env)
    elif exp[0] == 'lambda':         # (lambda (parm…) body…)
        (_, parms, *body) = exp
        return Procedure(parms, body, env)
    elif exp[0] == 'define':
        (_, name, value_exp) = exp
        env[name] = evaluate(value_exp, env)
    # ... more lines omitted
```

Each `elif` clause checks the first item of the list, and then unpacks the list,
ignoring the first item.  The extensive use of unpacking suggests that Norvig is a fan
of pattern matching, but he wrote that code originally for Python 2.  Using
`match`/`case`, we can refactor `evaluate` like this:

<!-- nocheck -->
```python
def evaluate(exp: Expression, env: Environment) -> Any:
    "Evaluate an expression in an environment."
    match exp:
    # ... lines omitted
        case ['quote', x]:
            return x
        case ['if', test, consequence, alternative]:
            if evaluate(test, env):
                return evaluate(consequence, env)
            else:
                return evaluate(alternative, env)
        case ['lambda', [*parms], *body] if body:
            return Procedure(parms, body, env)
        case ['define', Symbol() as name, value_exp]:
            env[name] = evaluate(value_exp, env)
        # ... more lines omitted
        case _:
            raise SyntaxError(lispstr(exp))
```

The first case matches a two-item sequence starting with `'quote'`.  The second matches
a four-item sequence starting with `'if'`.  The third matches a sequence of three or
more items starting with `'lambda'`; the guard ensures that `body` is not empty.  The
fourth matches a three-item sequence starting with `'define'`, followed by an instance
of `Symbol`.  And it is good practice to have a catch-all case: if `exp` doesn't match
any of the patterns, the expression is malformed, so we raise `SyntaxError`.

Norvig deliberately avoided error checking in `lis.py` to keep the code easy to
understand.  With pattern matching, we can add more checks and still keep it readable.
For example, in the `'define'` pattern, the original code does not ensure that `name`
is an instance of `Symbol`; that would require an `if` block, an `isinstance` call, and
more code.  The `match` version is shorter and safer.

#### Alternative patterns for lambda

This is the syntax of `lambda` in Scheme, using the convention that the suffix `…`
means the element may appear zero or more times:

```text
(lambda (parms…) body1 body2…)
```

A simple pattern for the `'lambda'` case would be this:

<!-- nocheck -->
```python
case ['lambda', parms, *body] if body:
```

However, that matches any value in the `parms` position, including the first `'x'` in
this invalid subject: `['lambda', 'x', ['*', 'x', 2]]`.  The nested list after the
`lambda` keyword in Scheme holds the names of the formal parameters for the function,
and it must be a list even if it has only one element.  It may also be an empty list,
if the function takes no parameters, like Python's `random.random()`.  The refactored
`evaluate` makes the `'lambda'` pattern safer using a nested sequence pattern:

<!-- nocheck -->
```python
case ['lambda', [*parms], *body] if body:
    return Procedure(parms, body, env)
```

In a sequence pattern, `*` can appear only once per sequence.  Here we have two
sequences: the outer and the inner.  Adding the characters `[*]` around `parms` made
the pattern look more like the Scheme syntax it handles, and gave us an additional
structural check.

#### Shortcut syntax for function definition

Scheme has an alternative `define` syntax to create a named function without using a
nested `lambda`:

```text
(define (name parm…) body1 body2…)
```

The `define` keyword is followed by a list with the name of the new function and zero
or more parameter names.  After that list comes the function body with one or more
expressions.  Adding these two lines to the `match` takes care of the implementation:

<!-- nocheck -->
```python
case ['define', [Symbol() as name, *parms], *body] if body:
    env[name] = Procedure(parms, body, env)
```

The order between the two `define` cases is irrelevant here, because no subject can
match both patterns: the second element must be a `Symbol` in the original `define`
case, but it must be a sequence starting with a `Symbol` in the shortcut.  Now consider
how much work it would take to add support for this second `define` syntax without the
help of pattern matching.  The `match` statement does a lot more than the `switch` in
C-like languages.

Pattern matching is an example of *declarative programming*: the code describes
"what" you want to match, instead of "how" to match it.  The shape of the code follows
the shape of the data:

| Scheme syntax | Sequence pattern |
|---|---|
| `(quote exp)` | `['quote', exp]` |
| `(if test conseq alt)` | `['if', test, conseq, alt]` |
| `(lambda (parms…) body1 body2…)` | `['lambda', [*parms], *body] if body` |
| `(define name exp)` | `['define', Symbol() as name, exp]` |
| `(define (name parms…) body1 body2…)` | `['define', [Symbol() as name, *parms], *body] if body` |

The full interpreter is covered in the case study at the end of this chapter.

## Pattern Matching with Mappings

Mapping patterns look like `dict` literals, but they match instances of any actual or
virtual subclass of `collections.abc.Mapping`.  Different kinds of patterns can be
combined and nested, which makes pattern matching a powerful tool to process records
structured like nested mappings and sequences, which you often read from JSON APIs and
from databases with semi-structured schemas.  The simple type hints in this
`get_creators` function make it clear that it takes a `dict` and returns a `list`:

```python
def get_creators(record: dict) -> list:
    match record:
        case {'type': 'book', 'api': 2, 'authors': [*names]}:
            return names
        case {'type': 'book', 'api': 1, 'author': name}:
            return [name]
        case {'type': 'book'}:
            raise ValueError(f"Invalid 'book' record: {record!r}")
        case {'type': 'movie', 'director': name}:
            return [name]
        case _:
            raise ValueError(f'Invalid record: {record!r}')

get_creators(dict(api=1, author='Douglas Hofstadter',
                  type='book', title='Gödel, Escher, Bach'))
# ['Douglas Hofstadter']
get_creators({'type': 'movie', 'director': 'Akira Kurosawa'})
# ['Akira Kurosawa']
```

[Pattern Matching with Mappings](dicts-sets.md#pattern-matching-with-mappings) in the
Dictionaries and Sets chapter walks through this function in detail.  The rules to
remember are:

* The order of the keys in mapping patterns is irrelevant.
* Unlike sequence patterns, mapping patterns succeed on *partial* matches: extra keys
  in the subject are ignored.
* To capture the extra key-value pairs as a `dict`, prefix one variable with `**`, as
  in `{'category': 'ice cream', **details}`.  It must be the last item in the pattern,
  and `**_` is forbidden because it would be redundant.
* A match succeeds only if the subject already has the required keys.  The automatic
  handling of missing keys of `defaultdict` and other mappings with `__missing__()` is
  not triggered, because pattern matching always uses the `d.get(key, sentinel)`
  method, where `sentinel` is a special marker value that cannot occur in user data.

## Pattern Matching Class Instances

Class patterns are designed to match class instances by type and, optionally, by
attributes.  The subject of a class pattern can be any class instance, not only
instances of data classes.  There are three variations of class patterns: simple,
keyword and positional.

### Simple Class Patterns

You've already seen simple class patterns used as subpatterns in sequence patterns:

<!-- nocheck -->
```python
case [str(name), _, _, (float(lat), float(lon))]:
```

That pattern matches a four-item sequence where the first item must be an instance of
`str`, and the last item must be a 2-tuple with two instances of `float`.

The syntax for class patterns looks like a constructor invocation.  The following is a
class pattern that matches `float` values without binding a variable (the case body
can refer to `x` directly if needed):

<!-- nocheck -->
```python
match x:
    case float():
        do_something_with(x)
```

But this is likely to be a bug in your code:

<!-- nocheck -->
```python
match x:
    case float:  # DANGER!!!
        do_something_with(x)
```

In the preceding example, `case float:` matches any subject, because Python sees
`float` as a capture variable, which is then bound to the subject.

The simple pattern syntax of `float(x)` is a special case that applies only to nine
blessed built-in types, listed at the end of the "Class Patterns" section of PEP 634:

```text
bytes   dict   float   frozenset   int   list   set   str   tuple
```

For those classes, the variable that looks like a constructor argument, the `x` in
`float(x)`, is bound to the whole subject instance or the part of the subject that
matches a subpattern, as `str(name)` does in the sequence pattern above.  If the class
is not one of those nine blessed built-ins, then the argument-like variables represent
patterns to be matched against attributes of an instance of that class.

### Keyword Class Patterns

To understand keyword class patterns, consider the following `City` class and five
instances:

```python
import typing

class City(typing.NamedTuple):
    continent: str
    name: str
    country: str

cities = [
    City('Asia', 'Tokyo', 'JP'),
    City('Asia', 'Delhi', 'IN'),
    City('North America', 'Mexico City', 'MX'),
    City('North America', 'New York', 'US'),
    City('South America', 'São Paulo', 'BR'),
]
```

Given those definitions, the following function returns a list of Asian cities:

```python
def match_asian_cities():
    results = []
    for city in cities:
        match city:
            case City(continent='Asia'):
                results.append(city)
    return results

match_asian_cities()
# [City(continent='Asia', name='Tokyo', country='JP'), City(continent='Asia', name='Delhi', country='IN')]
```

The pattern `City(continent='Asia')` matches any `City` instance where the `continent`
attribute value is equal to `'Asia'`, regardless of the values of the other attributes.
If you want to collect the value of the `country` attribute, you could write:

```python
def match_asian_countries():
    results = []
    for city in cities:
        match city:
            case City(continent='Asia', country=cc):
                results.append(cc)
    return results

match_asian_countries()
# ['JP', 'IN']
```

The pattern `City(continent='Asia', country=cc)` matches the same Asian cities as
before, but now the `cc` variable is bound to the `country` attribute of the instance.
This also works if the pattern variable is called `country` as well:

<!-- nocheck -->
```python
match city:
    case City(continent='Asia', country=country):
        results.append(country)
```

Keyword class patterns are very readable, and work with any class that has public
instance attributes, but they are somewhat verbose.  Positional class patterns are
more convenient in some cases, but they require explicit support by the class of the
subject.

### Positional Class Patterns

Given the same definitions, the following function returns a list of Asian cities,
using a positional class pattern:

```python
def match_asian_cities_pos():
    results = []
    for city in cities:
        match city:
            case City('Asia'):
                results.append(city)
    return results

def match_asian_countries_pos():
    results = []
    for city in cities:
        match city:
            case City('Asia', _, country):
                results.append(country)
    return results

match_asian_countries_pos()
# ['JP', 'IN']
```

The pattern `City('Asia')` matches any `City` instance where the first attribute value
is `'Asia'`, regardless of the values of the other attributes.  The pattern
`City('Asia', _, country)` matches the same cities, but binds the `country` variable to
the third attribute of the instance.

What do "first" and "third" attribute mean?  What makes `City`, or any class, work with
positional patterns is the presence of a special class attribute named
`__match_args__`, which the class builders in [Data Class Builders](dataclasses.md)
create automatically:

```python
City.__match_args__
# ('continent', 'name', 'country')
```

`__match_args__` declares the names of the attributes in the order they will be used
in positional patterns.  [Supporting Positional Pattern Matching](pythonic-object.md#supporting-positional-pattern-matching)
shows how to define `__match_args__` for a class created without the help of a class
builder.

> **Tip**
>
> You can combine keyword and positional arguments in a pattern.  Some, but not all,
> of the instance attributes available for matching may be listed in
> `__match_args__`.  Therefore, sometimes you may need to use keyword arguments in
> addition to positional arguments in a pattern.

## Using OR-Patterns

A series of patterns separated by `|` is an *OR-pattern*: it succeeds if any of the
subpatterns succeeds.  You'll see this pattern in the interpreter below:

<!-- nocheck -->
```python
case int(x) | float(x):
    return x
```

All subpatterns in an OR-pattern must use the same variables.  This restriction is
necessary to ensure that the variables are available to the guard expression and the
case body, regardless of the subpattern that matched.

> **Warning**
>
> In the context of a `case` clause, the `|` operator has a special meaning.  It does
> not trigger the `__or__()` special method, which handles expressions like `a | b` in
> other contexts, where it is overloaded to perform operations such as set union or
> integer bitwise-or, depending on the operands.

An OR-pattern is not restricted to the top level of a pattern; you can also use `|` in
subpatterns.  For example, to let the interpreter accept the Greek letter λ (lambda)
as well as the `lambda` keyword, we can rewrite the pattern like this:

<!-- nocheck -->
```python
# (λ (a b) (/ (+ a b) 2) )
case ['lambda' | 'λ', [*parms], *body] if body:
    return Procedure(parms, body, env)
```

(The official Unicode name of λ, U+03BB, is `GREEK SMALL LETTER LAMDA`: the character
is named "lamda" without the "b" in the Unicode database.)

## Case Study: Pattern Matching in `lis.py`

This section gives a broader overview of how Norvig's `lis.py` works, explores all the
`case` clauses of `evaluate`, and explains not only the patterns but also what the
interpreter does in each case.  Besides showing more pattern matching, it is worth
studying for three reasons: `lis.py` is a beautiful example of idiomatic Python code;
the simplicity of Scheme is a master class of language design; and learning how an
interpreter works gives you a deeper understanding of Python and programming languages
in general, interpreted or compiled.

### Scheme Syntax

In Scheme there is no distinction between expressions and statements, as there is in
Python.  Also, there are no infix operators.  All expressions use prefix notation like
`(+ x 13)` instead of `x + 13`.  The same prefix notation is used for function calls,
like `(gcd x 13)`, and for special forms, like `(define x 13)`, which we'd write as the
assignment statement `x = 13` in Python.  The notation used by Scheme and most Lisp
dialects is known as *S-expression*.  Here is a simple example in Scheme:

```text
(define (mod m n)
    (- m (* n (quotient m n))))

(define (gcd m n)
    (if (= n 0)
        m
        (gcd n (mod m n))))

(display (gcd 18 45))
```

That shows three Scheme expressions: two function definitions, `mod` and `gcd`, and a
call to `display`, which outputs 9, the result of `(gcd 18 45)`.  Here is the same code
in Python, shorter than an English explanation of the recursive Euclidean algorithm:

```python
def mod(m, n):
    return m - (m // n * n)

def gcd(m, n):
    if n == 0:
        return m
    else:
        return gcd(n, mod(m, n))

print(gcd(18, 45))
# 9
```

In idiomatic Python you'd use the `%` operator instead of reinventing `mod`, and it
would be more efficient to use a `while` loop instead of recursion (or just
`math.gcd`).  But the point is to make the examples as similar as possible.  Scheme has
no iterative control flow commands like `while` or `for`; iteration is done with
recursion, which Scheme makes efficient with *proper tail calls*.  Note that there are
no assignments in the Scheme and Python examples.  Extensive use of recursion and
minimal use of assignment are hallmarks of programming in a functional style.

### Imports and Types

Here is the top of `lis.py`:

```python
import math
import operator as op
from collections import ChainMap
from itertools import chain
from typing import Any, TypeAlias, NoReturn

Symbol: TypeAlias = str
Atom: TypeAlias = float | int | Symbol
Expression: TypeAlias = Atom | list
```

The types defined are:

`Symbol`
: just an alias for `str`.  In `lis.py`, `Symbol` is used for identifiers; there is no
  string data type with operations such as slicing, splitting, etc.

`Atom`
: a simple syntactic element, such as a number or a `Symbol`, as opposed to a
  composite structure made of distinct parts, like a list.

`Expression`
: the building blocks of Scheme programs are expressions made of atoms and lists,
  possibly nested.

(These are written as plain assignments annotated with `TypeAlias` rather than with
the newer `type` statement, because `evaluate` uses `Symbol` in class patterns like
`Symbol(var)`, which requires `Symbol` to be an actual class.)

### The Parser

Norvig's parser is 36 lines of code showcasing the power of Python applied to handling
the simple recursive syntax of S-expressions, without string data, comments, macros
and other features of standard Scheme that make parsing more complicated:

```python
def parse(program: str) -> Expression:
    "Read a Scheme expression from a string."
    return read_from_tokens(tokenize(program))

def tokenize(s: str) -> list[str]:
    "Convert a string into a list of tokens."
    return s.replace('(', ' ( ').replace(')', ' ) ').split()

def read_from_tokens(tokens: list[str]) -> Expression:
    "Read an expression from a sequence of tokens."
    if len(tokens) == 0:
        raise SyntaxError('unexpected EOF while reading')
    token = tokens.pop(0)
    if '(' == token:
        exp = []
        while tokens and tokens[0] != ')':
            exp.append(read_from_tokens(tokens))
        if not tokens:
            raise SyntaxError('unexpected EOF while reading')
        tokens.pop(0)  # discard ')'
        return exp
    elif ')' == token:
        raise SyntaxError('unexpected )')
    else:
        return parse_atom(token)

def parse_atom(token: str) -> Atom:
    "Numbers become numbers; every other token is a symbol."
    try:
        return int(token)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            return Symbol(token)
```

The main function of that group is `parse`, which takes an S-expression as a `str` and
returns an `Expression` object: an `Atom`, or a `list` that may contain more atoms and
nested lists.  Norvig uses a smart trick in `tokenize`: he adds spaces before and after
each parenthesis in the input and then splits it, resulting in a list of tokens with
`'('` and `')'` as separate tokens.  This shortcut works because there is no string
type in the little Scheme of `lis.py`, so every `'('` or `')'` is an expression
delimiter.  The recursive parsing happens in `read_from_tokens`.  Here are some
examples:

```python
parse('1.5')
# 1.5
parse('ni!')
# 'ni!'
parse('(gcd 18 45)')
# ['gcd', 18, 45]
parse('''
(define double
    (lambda (n)
        (* n 2)))
''')
# ['define', 'double', ['lambda', ['n'], ['*', 'n', 2]]]
```

The parsing rules for this subset of Scheme are simple:

1. A token that looks like a number is parsed as a `float` or `int`.
2. Anything else that is not `'('` or `')'` is parsed as a `Symbol`, a `str` to be used
   as an identifier.  This includes source text like `+`, `set!` and `make-counter`,
   which are valid identifiers in Scheme but not in Python.
3. Expressions inside `'('` and `')'` are recursively parsed as lists containing atoms
   or as nested lists that may contain atoms and more nested lists.

Using the terminology of the Python interpreter, the output of `parse` is an *AST*
(Abstract Syntax Tree): a convenient representation of the Scheme program as nested
lists forming a tree-like structure, where the outermost list is the trunk, inner lists
are the branches, and atoms are the leaves.

### Environment with `ChainMap`

The `Environment` class extends [`collections.ChainMap`](dicts-sets.md#collectionschainmap),
adding a `change` method to update a value inside one of the chained dicts, which
`ChainMap` instances hold in a list of mappings: the `self.maps` attribute.  The
`change` method is needed to support the Scheme `(set! …)` form, described later:

```python
class Environment(ChainMap[Symbol, Any]):
    "A ChainMap that allows changing an item in-place."

    def change(self, key: Symbol, value: Any) -> None:
        "Find where key is defined and change the value there."
        for map in self.maps:
            if key in map:
                map[key] = value
                return
        raise KeyError(key)
```

Note that the `change` method only updates existing keys; trying to change a key that
is not found raises `KeyError`.  Here is how `Environment` works:

```python
inner_env = {'a': 2}
outer_env = {'a': 0, 'b': 1}
env = Environment(inner_env, outer_env)
env['a']
# 2
env['a'] = 111
env['c'] = 222
env
# Environment({'a': 111, 'c': 222}, {'a': 0, 'b': 1})
env.change('b', 333)
env
# Environment({'a': 111, 'c': 222}, {'a': 0, 'b': 333})
```

When reading values, `Environment` works as `ChainMap`: keys are searched in the
nested mappings from left to right.  That's why the value of `a` in `outer_env` is
shadowed by the value in `inner_env`.  Assigning with `[]` overwrites or inserts new
items, but always in the first mapping, `inner_env` in this example.
`env.change('b', 333)` seeks the `'b'` key and assigns a new value to it in place, in
`outer_env`.

Next is the `standard_env()` function, which builds and returns an `Environment` loaded
with predefined functions, similar to Python's `__builtins__` module that is always
available:

```python
def standard_env() -> Environment:
    "An environment with some Scheme standard procedures."
    env = Environment()
    env.update(vars(math))   # sin, cos, sqrt, pi, ...
    env.update({
            '+': op.add,
            '-': op.sub,
            '*': op.mul,
            '/': op.truediv,
            'quotient': op.floordiv,
            '>': op.gt,
            '<': op.lt,
            '>=': op.ge,
            '<=': op.le,
            '=': op.eq,
            'abs': abs,
            'append': lambda *args: list(chain(*args)),
            'apply': lambda proc, args: proc(*args),
            'begin': lambda *x: x[-1],
            'car': lambda x: x[0],
            'cdr': lambda x: x[1:],
            'cons': lambda x, y: [x] + y,
            'display': lambda x: print(lispstr(x)),
            'eq?': op.is_,
            'equal?': op.eq,
            'length': len,
            'list': lambda *x: list(x),
            'list?': lambda x: isinstance(x, list),
            'map': lambda *args: list(map(*args)),
            'max': max,
            'min': min,
            'not': op.not_,
            'null?': lambda x: x == [],
            'number?': lambda x: isinstance(x, (int, float)),
            'procedure?': callable,
            'round': round,
            'symbol?': lambda x: isinstance(x, Symbol),
    })
    return env
```

To summarize, the `env` mapping is loaded with all functions from Python's `math`
module; selected operators from Python's `operator` module; simple but powerful
functions built with Python's `lambda`; and Python built-ins renamed, like `callable`
as `procedure?`, or directly mapped, like `round`.

### The REPL

Norvig's REPL (read-eval-print loop) is easy to understand but not user-friendly.  At
the `lis.py>` prompt, you must enter correct and complete expressions; if you forget
to close one parenthesis, `lis.py` crashes:

```python
def repl(prompt: str = 'lis.py> ') -> NoReturn:
    "A prompt-read-eval-print loop."
    global_env = Environment({}, standard_env())
    while True:
        ast = parse(input(prompt))
        val = evaluate(ast, global_env)
        if val is not None:
            print(lispstr(val))

def lispstr(exp: object) -> str:
    "Convert a Python object back into a Lisp-readable string."
    if isinstance(exp, list):
        return '(' + ' '.join(map(lispstr, exp)) + ')'
    else:
        return str(exp)
```

`repl` calls `standard_env()` to provide built-in functions for the global
environment, then enters an infinite loop, reading and parsing each input line,
evaluating it in the global environment, and displaying the result, unless it's `None`.
The `global_env` may be modified by `evaluate`: for example, when a user defines a new
global variable or named function, it is stored in the first mapping of the
environment, the empty `dict` in the `Environment` constructor call.  `lispstr` is the
inverse of `parse`: given a Python object representing an expression, it returns the
Scheme source code for it.  For example, given `['+', 2, 3]`, the result is
`'(+ 2 3)'`.

### The Evaluator

Now we can appreciate the beauty of Norvig's expression evaluator, made a little
prettier with `match`/`case`.  The `evaluate` function takes an `Expression` built by
`parse` and an `Environment`.  Its body is a single `match` statement with an
expression `exp` as the subject.  The `case` patterns express the syntax and semantics
of Scheme with amazing clarity:

```python
KEYWORDS = ['quote', 'if', 'lambda', 'define', 'set!']

def evaluate(exp: Expression, env: Environment) -> Any:
    "Evaluate an expression in an environment."
    match exp:
        case int(x) | float(x):
            return x
        case Symbol(var):
            return env[var]
        case ['quote', x]:
            return x
        case ['if', test, consequence, alternative]:
            if evaluate(test, env):
                return evaluate(consequence, env)
            else:
                return evaluate(alternative, env)
        case ['lambda', [*parms], *body] if body:
            return Procedure(parms, body, env)
        case ['define', Symbol(name), value_exp]:
            env[name] = evaluate(value_exp, env)
        case ['define', [Symbol(name), *parms], *body] if body:
            env[name] = Procedure(parms, body, env)
        case ['set!', Symbol(name), value_exp]:
            env.change(name, evaluate(value_exp, env))
        case [func_exp, *args] if func_exp not in KEYWORDS:
            proc = evaluate(func_exp, env)
            values = [evaluate(arg, env) for arg in args]
            return proc(*values)
        case _:
            raise SyntaxError(lispstr(exp))
```

Let's study each `case` clause and what it does.  The comments show an S-expression
that would match the pattern when parsed into a Python list.  (`evaluate` refers to the
`Procedure` class, defined after this walkthrough; the examples below assume it has
been defined.)

#### Evaluating numbers

<!-- nocheck -->
```python
case int(x) | float(x):
    return x
```

*Subject*: an instance of `int` or `float`.  *Action*: return the value as is.  This
is an OR-pattern; both alternatives bind `x`.

<!-- nocheck -->
```python
evaluate(parse('1.5'), {})
# 1.5
```

#### Evaluating symbols

<!-- nocheck -->
```python
case Symbol(var):
    return env[var]
```

*Subject*: an instance of `Symbol`, that is, a `str` used as an identifier.
*Action*: look up `var` in `env` and return its value.

<!-- nocheck -->
```python
evaluate(parse('+'), standard_env())
# <built-in function add>
evaluate(parse('ni!'), standard_env())
# Traceback (most recent call last):
#     ...
# KeyError: 'ni!'
```

#### `(quote …)`

The `quote` special form treats atoms and lists as data instead of expressions to be
evaluated.

<!-- nocheck -->
```python
# (quote (99 bottles of beer))
case ['quote', x]:
    return x
```

*Subject*: a list starting with the symbol `'quote'`, followed by one expression `x`.
*Action*: return `x` without evaluating it.

<!-- nocheck -->
```python
evaluate(parse('(quote no-such-name)'), standard_env())
# 'no-such-name'
evaluate(parse('(quote (99 bottles of beer))'), standard_env())
# [99, 'bottles', 'of', 'beer']
evaluate(parse('(quote (/ 10 0))'), standard_env())
# ['/', 10, 0]
```

Without `quote`, each expression in those tests would raise an error: `no-such-name`
would be looked up in the environment, raising `KeyError`; `(99 bottles of beer)`
cannot be evaluated because the number 99 is not a `Symbol` naming a special form,
operator or function; and `(/ 10 0)` would raise `ZeroDivisionError`.

> **Note**
>
> Why do languages have reserved keywords?  Although simple, `quote` cannot be
> implemented as a function in Scheme.  Its special power is to prevent the
> interpreter from evaluating `(f 10)` in the expression `(quote (f 10))`: the result is
> simply a list with a `Symbol` and an `int`.  In a function call like `(abs (f 10))`,
> by contrast, the interpreter evaluates `(f 10)` before invoking `abs`.  That's why
> `quote` is a reserved keyword: it must be handled as a special form.  In general,
> reserved keywords are needed to introduce specialized evaluation rules, as in
> `quote` and `lambda`, which don't evaluate any of their subexpressions; to change the
> control flow, as in `if` and function calls; and to manage the environment, as in
> `define` and `set!`.  This is also why Python needs reserved keywords: think of what
> `def`, `if`, `yield`, `import` and `del` do.

#### `(if …)`

<!-- nocheck -->
```python
# (if (< x 0) 0 x)
case ['if', test, consequence, alternative]:
    if evaluate(test, env):
        return evaluate(consequence, env)
    else:
        return evaluate(alternative, env)
```

*Subject*: a list starting with `'if'` followed by three expressions: `test`,
`consequence` and `alternative`.  *Action*: evaluate `test`; if true, evaluate
`consequence` and return its value, otherwise evaluate `alternative` and return its
value.

<!-- nocheck -->
```python
evaluate(parse('(if (= 3 3) 1 0))'), standard_env())
# 1
evaluate(parse('(if (= 3 4) 1 0))'), standard_env())
# 0
```

The `consequence` and `alternative` branches must be single expressions.  If more than
one expression is needed in a branch, you can combine them with `(begin exp1 exp2…)`,
provided as a function in `standard_env`.

#### `(lambda …)`

Scheme's `lambda` form defines anonymous functions.  It doesn't suffer from the
limitations of Python's `lambda`: any function that can be written in Scheme can be
written using the `(lambda …)` syntax.

<!-- nocheck -->
```python
# (lambda (a b) (/ (+ a b) 2))
case ['lambda', [*parms], *body] if body:
    return Procedure(parms, body, env)
```

*Subject*: a list starting with `'lambda'`, followed by a list of zero or more
parameter names and one or more expressions collected in `body` (the guard ensures
that `body` is not empty).  *Action*: create and return a new `Procedure` instance
with the parameter names, the list of expressions as the body, and the current
environment.

<!-- nocheck -->
```python
expr = '(lambda (a b) (* (/ a b) 100))'
f = evaluate(parse(expr), standard_env())
f
# <__main__.Procedure object at 0x...>
f(15, 20)
# 75.0
```

The `Procedure` class implements the concept of a closure: a callable object holding
parameter names, a function body, and a reference to the environment in which the
function is defined.  We'll study its code in a moment.

#### `(define …)`

The `define` keyword is used in two different syntactic forms.  The simplest is:

<!-- nocheck -->
```python
# (define half (/ 1 2))
case ['define', Symbol(name), value_exp]:
    env[name] = evaluate(value_exp, env)
```

*Subject*: a list starting with `'define'`, followed by a `Symbol` and an expression.
*Action*: evaluate the expression and put its value into `env`, using `name` as key.

<!-- nocheck -->
```python
global_env = standard_env()
evaluate(parse('(define answer (* 7 6))'), global_env)
global_env['answer']
# 42
```

We can use that simple `define` form to create variables or to bind names to
anonymous functions, using `(lambda …)` as the `value_exp`.  Standard Scheme provides a
shortcut for defining named functions; that's the second `define` form:

<!-- nocheck -->
```python
# (define (average a b) (/ (+ a b) 2))
case ['define', [Symbol(name), *parms], *body] if body:
    env[name] = Procedure(parms, body, env)
```

*Subject*: a list starting with `'define'`, followed by a list starting with a
`Symbol(name)` followed by zero or more items collected into a list named `parms`, and
then one or more expressions collected in `body`.  *Action*: create a new `Procedure`
with the parameter names, the list of expressions as the body, and the current
environment, and put it into `env`, using `name` as key.  Here we define a function
named `%` that computes a percentage:

<!-- nocheck -->
```python
global_env = standard_env()
percent = '(define (% a b) (* (/ a b) 100))'
evaluate(parse(percent), global_env)
global_env['%']
# <__main__.Procedure object at 0x...>
global_env['%'](170, 200)
# 85.0
```

(The pattern for the second `define` case does not enforce that the items in `parms`
are all `Symbol` instances.  That would require a check before building the
`Procedure`, which is left out to keep the code as easy to follow as Norvig's.)

#### `(set! …)`

The `set!` form changes the value of a previously defined variable.

<!-- nocheck -->
```python
# (set! n (+ n 1))
case ['set!', Symbol(name), value_exp]:
    env.change(name, evaluate(value_exp, env))
```

*Subject*: a list starting with `'set!'`, followed by a `Symbol` and an expression.
*Action*: update the value of `name` in `env` with the result of evaluating the
expression.  The `Environment.change` method traverses the chained environments from
local to global, and updates the first occurrence of `name` with the new value.  If we
were not implementing the `set!` keyword, we could use Python's `ChainMap` as the
`Environment` type everywhere in this interpreter.  (Coding in a functional style can
take you very far without state changes: in *Structure and Interpretation of Computer
Programs*, the best-known Scheme book, `set!` only appears on page 220.)

> **Note**
>
> Python's `nonlocal` and Scheme's `set!` address the same issue.  Declaring
> `nonlocal x` allows `x = 10` to update a previously defined `x` outside of the local
> scope; without it, `x = 10` always creates a local variable (see
> [The `nonlocal` Declaration](decorators.md#the-nonlocal-declaration)).  Similarly,
> `(set! x 10)` updates a previously defined `x` that may be outside of the local
> environment of the function, while `x` in `(define x 10)` is always a local variable.
> Both are needed to update program state held in variables within a closure.  Here is
> the running average from the Decorators chapter, written in the Scheme subset of
> `lis.py`:
>
> ```text
> (define (make-averager)
>     (define count 0)
>     (define total 0)
>     (lambda (new-value)
>         (set! count (+ count 1))
>         (set! total (+ total new-value))
>         (/ total count)
>     )
> )
> (define avg (make-averager))
> (avg 10)
> (avg 11)
> (avg 15)
> ```
>
> `(make-averager)` creates a new closure with the inner function defined by `lambda`,
> and the variables `count` and `total` initialized to 0, and binds the closure to
> `avg`.  The three calls return 10.0, 10.5 and 12.0.

#### Function call

<!-- nocheck -->
```python
# (gcd (* 2 105) 84)
case [func_exp, *args] if func_exp not in KEYWORDS:
    proc = evaluate(func_exp, env)
    values = [evaluate(arg, env) for arg in args]
    return proc(*values)
```

*Subject*: a list with one or more items.  The guard ensures that `func_exp` is not
one of `['quote', 'if', 'define', 'lambda', 'set!']`.  The pattern matches any list with
one or more expressions, binding the first expression to `func_exp` and the rest to
`args` as a list, which may be empty.  *Action*: evaluate `func_exp` to obtain a
function `proc`, evaluate each item in `args` to build a list of argument values, and
call `proc` with the values as separate arguments, returning the result.

<!-- nocheck -->
```python
evaluate(parse('(% (* 12 14) (- 500 100))'), global_env)
# 42.0
```

That example assumes `global_env` has the function named `%` defined above.  The
arguments given to `%` are arithmetic expressions, to emphasize that the arguments are
evaluated before the function is called.  The guard is needed because
`[func_exp, *args]` matches any sequence subject with one or more items; if `func_exp`
is a keyword and the subject did not match any previous case, then it is really a
syntax error.

#### Catch syntax errors

If the subject `exp` does not match any of the previous cases, the catch-all case
raises a `SyntaxError`:

<!-- nocheck -->
```python
case _:
    raise SyntaxError(lispstr(exp))
```

Here is a malformed `(lambda …)` reported as a `SyntaxError`:

<!-- nocheck -->
```python
evaluate(parse('(lambda is not like this)'), standard_env())
# Traceback (most recent call last):
#     ...
# SyntaxError: (lambda is not like this)
```

If the function call case did not have the guard rejecting keywords, the
`(lambda is not like this)` expression would be handled as a function call, which
would raise `KeyError` because `'lambda'` is not part of the environment, just like
`lambda` is not a Python built-in function.

### `Procedure`: A Class Implementing a Closure

The `Procedure` class could very well be named `Closure`, because that's what it
represents: a function definition together with an environment.  The function
definition includes the names of the parameters and the expressions that make up the
body of the function.  The environment is used when the function is called to provide
the values of the *free variables*: variables that appear in the body of the function
but are not parameters, local variables or global variables (see
[Closures](decorators.md#closures)).  Here is how a closure is implemented in
`lis.py`:

```python
class Procedure:
    "A user-defined Scheme procedure."

    def __init__(
        self, parms: list[Symbol], body: list[Expression], env: Environment
    ):
        self.parms = parms
        self.body = body
        self.env = env

    def __call__(self, *args: Expression) -> Any:
        local_env = dict(zip(self.parms, args))
        env = Environment(local_env, self.env)
        for exp in self.body:
            result = evaluate(exp, env)
        return result
```

`__init__()` is called when a function is defined by the `lambda` or `define` forms;
it saves the parameter names, body expressions and environment for later use.
`__call__()` is called by `proc(*values)` in the last line of the function call case.
It builds `local_env`, mapping `self.parms` as local variable names to the given
`args` as values; builds a new combined `env`, putting `local_env` first and then
`self.env`, the environment that was saved when the function was defined; evaluates
each expression in `self.body` in the combined `env`; and returns the result of the
last expression evaluated.

Now the whole interpreter works.  Let's run the `gcd` program and the running average
through it:

```python
def run(source: str) -> Any:
    "Evaluate each expression in source; return the value of the last one."
    global_env = Environment({}, standard_env())
    tokens = tokenize(source)
    while tokens:
        exp = read_from_tokens(tokens)
        result = evaluate(exp, global_env)
    return result

run('''
(define (mod m n)
    (- m (* n (quotient m n))))
(define (gcd m n)
    (if (= n 0)
        m
        (gcd n (mod m n))))
(gcd 18 45)
''')
# 9
run('''
(define (make-averager)
    (define count 0)
    (define total 0)
    (lambda (new-value)
        (set! count (+ count 1))
        (set! total (+ total new-value))
        (/ total count)))
(define avg (make-averager))
(avg 10)
(avg 11)
(avg 15)
''')
# 12.0
run('''
(define (% a b) (* (/ a b) 100))
(% (* 12 14) (- 500 100))
''')
# 42.0
```

The goals of this case study were to share the beauty of Norvig's little interpreter,
to give more insight into how closures work, and to show how `match`/`case` is a great
addition to Python.

## Summary

Pattern matching with `match`/`case` supports destructuring: matching the shape of the
data and extracting parts of it in one step.  Sequence patterns match sequences other
than `str`, `bytes` and `bytearray`, item by item, with `*` to collect excess items;
mapping patterns match any mapping by key and succeed on partial matches; class
patterns match instances by type and attributes, positionally through
`__match_args__` or by keyword.  Patterns can be nested and combined with `|`
(OR-patterns) and `as`, and guards add arbitrary conditions.  Remember that a bare name
is always a capture pattern, never a comparison: use dotted names, like enum members,
to match constants.

As the `lis.py` case study shows, pattern matching is an example of declarative
programming: the shape of the code follows the shape of the data.

> **See also**
>
> * The "Structural Pattern Matching" section of [What's New In Python 3.10](https://docs.python.org/3/whatsnew/3.10.html#pep-634-structural-pattern-matching)
>   is a great introduction in about 1,400 words.
>   [**PEP 636**](https://peps.python.org/pep-0636/) is a longer tutorial, and
>   [**PEP 635**](https://peps.python.org/pep-0635/) gives the motivation and
>   rationale.  [**PEP 634**](https://peps.python.org/pep-0634/) is the
>   specification, and the [match statement](https://docs.python.org/3/reference/compound_stmts.html#the-match-statement)
>   section of the language reference is the authoritative description.
> * Peter Norvig's essay "(How to Write a (Lisp) Interpreter (in Python))" explains
>   `lis.py` in his own words.
