# Dynamic Attributes and Properties

> The crucial importance of properties is that their existence makes it perfectly safe and
> indeed advisable for you to expose public data attributes as part of your class's public
> interface.
>
> — Martelli, Ravenscroft and Holden, *Python in a Nutshell*

Data attributes and methods are collectively known as *attributes* in Python.  A method is
an attribute that is callable.  *Dynamic attributes* present the same interface as data
attributes — i.e., `obj.attr` — but are computed on demand.  This follows Bertrand Meyer's
*Uniform Access Principle*:

> All services offered by a module should be available through a uniform notation, which
> does not betray whether they are implemented through storage or through computation.

There are several ways to implement dynamic attributes in Python.  This chapter covers the
simplest ways: the `@property` decorator and the `__getattr__` special method.

A user-defined class implementing `__getattr__` can implement a variation of dynamic
attributes we can call *virtual attributes*: attributes that are not explicitly declared
anywhere in the source code of the class, and are not present in the instance `__dict__`,
but may be retrieved elsewhere or computed on the fly whenever a user tries to read a
nonexistent attribute like `obj.no_such_attr`.

Coding dynamic and virtual attributes is the kind of metaprogramming that framework authors
do.  However, in Python the basic techniques are straightforward, so we can use them in
everyday data wrangling tasks.  That's how we'll start this chapter.

## Data Wrangling with Dynamic Attributes

In the next few examples, we'll leverage dynamic attributes to work with a JSON dataset
published by O'Reilly for the OSCON 2014 conference.  The full dataset has 895 records (a
copy, `osconfeed.json`, is in the *Fluent Python* example code repository).  To keep the
examples here self-contained, we'll use a small sample with the same structure:

```python
SAMPLE_JSON = """
{ "Schedule":
  { "conferences": [{"serial": 115 }],
    "events": [
      { "serial": 34505,
        "name": "Why Schools Don't Use Open Source to Teach Programming",
        "event_type": "40-minute conference session",
        "time_start": "2014-07-23 11:30:00",
        "time_stop": "2014-07-23 12:10:00",
        "venue_serial": 1462,
        "speakers": [157509],
        "categories": ["Education"] },
      { "serial": 33950,
        "name": "There *Will* Be Bugs",
        "event_type": "40-minute conference session",
        "time_start": "2014-07-23 14:30:00",
        "time_stop": "2014-07-23 15:10:00",
        "venue_serial": 1449,
        "speakers": [3471, 5199],
        "categories": ["Python"] }
    ],
    "speakers": [
      { "serial": 157509, "name": "Robert Lefkowitz",
        "twitter": "sharewaveteam", "position": "CTO" },
      { "serial": 3471, "name": "Anna Martelli Ravenscroft",
        "twitter": "annaraven" },
      { "serial": 5199, "name": "Alex Martelli",
        "twitter": "aleaxit" }
    ],
    "venues": [
      { "serial": 1462, "name": "F151", "category": "Conference Venues" },
      { "serial": 1449, "name": "Portland 251", "category": "Conference Venues" }
    ]
  }
}
"""
```

The entire dataset is a single JSON object with the key `"Schedule"`, and its value is
another mapping with four keys: `"conferences"`, `"events"`, `"speakers"` and `"venues"`.
Each of those four keys maps to a list of records.  In the full dataset, the `"events"`,
`"speakers"` and `"venues"` lists have dozens or hundreds of records, while `"conferences"`
has only one record.  Every record has a `"serial"` field, which is a unique identifier for
the record within the list.  Let's explore it in the console:

```python
import json
feed = json.loads(SAMPLE_JSON)  # a dict holding nested dicts and lists, strings and ints
sorted(feed['Schedule'].keys())  # the four record collections inside "Schedule"
# ['conferences', 'events', 'speakers', 'venues']
for key, value in sorted(feed['Schedule'].items()):
    print(f'{len(value):3} {key}')

#   1 conferences
#   2 events
#   3 speakers
#   2 venues
feed['Schedule']['speakers'][-1]['name']  # navigate the nested dicts and lists
# 'Alex Martelli'
feed['Schedule']['speakers'][-1]['serial']
# 5199
feed['Schedule']['events'][1]['name']
# 'There *Will* Be Bugs'
feed['Schedule']['events'][1]['speakers']  # a list of speaker serial numbers
# [3471, 5199]
```

### Exploring JSON-Like Data with Dynamic Attributes

That is simple enough, but the syntax `feed['Schedule']['events'][1]['name']` is
cumbersome.  In JavaScript, you can get the same value by writing
`feed.Schedule.events[1].name`.  It's easy to implement a `dict`-like class that does the
same in Python — there are plenty of implementations on the web.  `FrozenJSON` is simpler
than most because it supports reading only: it's just for exploring the data.
`FrozenJSON` is also recursive, dealing automatically with nested mappings and lists:

```python
from collections import abc

class FrozenJSON:
    """A read-only façade for navigating a JSON-like object
       using attribute notation
    """

    def __init__(self, mapping):
        self.__data = dict(mapping)  # a dict from the argument; private attribute

    def __getattr__(self, name):  # called only when there's no attribute with that name
        try:
            return getattr(self.__data, name)  # e.g. keys, items: attributes of the dict
        except AttributeError:
            return FrozenJSON.build(self.__data[name])  # otherwise, fetch the item and build

    def __dir__(self):  # supports dir() and auto-completion in consoles
        return self.__data.keys()

    @classmethod
    def build(cls, obj):  # an alternate constructor
        if isinstance(obj, abc.Mapping):  # if obj is a mapping, build a FrozenJSON
            return cls(obj)
        elif isinstance(obj, abc.MutableSequence):  # if it's a list, build a list recursively
            return [cls.build(item) for item in obj]
        else:  # otherwise, return the item as it is
            return obj
```

We build a `dict` from the `mapping` argument.  This ensures we get a mapping or something
that can be converted to one.  The double-underscore prefix on `__data` makes it a private
attribute (see [Private Variables](classes.md#tut-private)).  `__getattr__` is called only
when there's no attribute with that name.  If `name` matches an attribute of the instance
`__data` dict, we return that.  This is how calls like `feed.keys()` are handled: the
`keys` method is an attribute of the `__data` dict.  Otherwise, we fetch the item with the
key `name` from `self.__data`, and return the result of calling `FrozenJSON.build()` on
that.

Implementing `__dir__` supports the `dir()` built-in, which in turn supports
auto-completion in the standard Python console as well as IPython, Jupyter Notebook, etc.
This simple code will enable recursive auto-completion based on the keys in `self.__data`,
because `__getattr__` builds `FrozenJSON` instances on the fly — useful for interactive
exploration of the data.

`build` is an alternate constructor, a common use for the `@classmethod` decorator.  If
`obj` is a mapping, it builds a `FrozenJSON` with it.  This is an example of goose typing
(see [Goose Typing](protocols-abcs.md#goose-typing)).  If it is a `MutableSequence`, it must
be a list (the only collection types in JSON data are `dict` and `list`), so we build a list
by passing each item in `obj` recursively to `.build()`.  If it's not a `dict` or a `list`,
we return the item as it is.  Here it is in action:

```python
raw_feed = json.loads(SAMPLE_JSON)
feed = FrozenJSON(raw_feed)  # build a FrozenJSON from nested dicts and lists
len(feed.Schedule.speakers)  # traverse nested dicts using attribute notation
# 3
feed.keys()  # methods of the underlying dicts can also be accessed
# dict_keys(['Schedule'])
sorted(feed.Schedule.keys())
# ['conferences', 'events', 'speakers', 'venues']
for key, value in sorted(feed.Schedule.items()):
    print(f'{len(value):3} {key}')

#   1 conferences
#   2 events
#   3 speakers
#   2 venues
feed.Schedule.speakers[-1].name  # a list remains a list, but its items are FrozenJSON
# 'Alex Martelli'
talk = feed.Schedule.events[1]
type(talk)  # item 1 in the events list was a JSON object; now it's a FrozenJSON
# <class '__main__.FrozenJSON'>
talk.name
# 'There *Will* Be Bugs'
talk.speakers
# [3471, 5199]
talk.flavor  # reading a missing attribute raises KeyError, not AttributeError
# Traceback (most recent call last):
#   ...
# KeyError: 'flavor'
```

The keystone of the `FrozenJSON` class is the `__getattr__` method, which we already used in
the `Vector` example in [Dynamic Attribute Access](sequence-protocol.md#dynamic-attribute-access),
to retrieve `Vector` components by letter: `v.x`, `v.y`, `v.z`, etc.  It's essential to
recall that the `__getattr__` special method is only invoked by the interpreter when the
usual process fails to retrieve an attribute (i.e., when the named attribute cannot be found
in the instance, nor in the class or in its superclasses).

The last line of that example exposes a minor issue: trying to read a missing attribute
should raise `AttributeError`, and not `KeyError` as shown.  Implementing the error handling
to do that makes the `__getattr__` method twice as long, distracting from the most important
logic.  Given that users know that a `FrozenJSON` is built from mappings and lists, the
`KeyError` is not too confusing — but handling it is a good exercise.

A `FrozenJSON` instance has the `__data` private instance attribute stored under the name
`_FrozenJSON__data`.  Attempts to retrieve attributes by other names will trigger
`__getattr__`.  This method will first look if the `self.__data` dict has an attribute (not
a key!) by that name; this allows `FrozenJSON` instances to handle `dict` methods such as
`items`, by delegating to `self.__data.items()`.  If `self.__data` doesn't have an attribute
with the given name, `__getattr__` uses `name` as a key to retrieve an item from
`self.__data`, and passes that item to `FrozenJSON.build`.  This allows navigating through
nested structures in the JSON data, as each nested mapping is converted to another
`FrozenJSON` instance by the `build` class method.

Note that `FrozenJSON` does not transform or cache the original dataset.  As we traverse the
data, `__getattr__` creates `FrozenJSON` instances again and again.  That's OK for a dataset
of this size, and for a script that will only be used to explore or convert the data.

Any script that generates or emulates dynamic attribute names from arbitrary sources must
deal with one issue: the keys in the original data may not be suitable attribute names.  The
next section addresses this.

### The Invalid Attribute Name Problem

The `FrozenJSON` code doesn't handle attribute names that are Python keywords.  For example,
if you build an object like this:

```python
student = FrozenJSON({'name': 'Jim Bo', 'class': 1982})
```

You won't be able to read `student.class` because `class` is a reserved keyword in Python:

```text
>>> student.class
  File "<stdin>", line 1
    student.class
            ^^^^^
SyntaxError: invalid syntax
```

You can always do this, of course:

```python
getattr(student, 'class')
# 1982
```

But the idea of `FrozenJSON` is to provide convenient access to the data, so a better
solution is checking whether a key in the mapping given to `FrozenJSON.__init__` is a
keyword, and if so, append an `_` to it, so the attribute can be read like `student.class_`.
This can be achieved by replacing the one-liner `__init__` with this version:

<!-- nocheck -->
```python
def __init__(self, mapping):
    self.__data = {}
    for key, value in mapping.items():
        if keyword.iskeyword(key):  # needs import keyword
            key += '_'
        self.__data[key] = value
```

The [`keyword.iskeyword(...)`](https://docs.python.org/3/library/keyword.html#keyword.iskeyword)
function is exactly what we need; to use it, the `keyword` module must be imported.

A similar problem may arise if a key in a JSON record is not a valid Python identifier, like
`'2be'`: `x.2be` is a `SyntaxError`.  Such problematic keys are easy to detect because the
`str` class provides the `s.isidentifier()` method, which tells you whether `s` is a valid
Python identifier according to the language grammar.  But turning a key that is not a valid
identifier into a valid attribute name is not trivial.  One solution would be to implement
`__getitem__` to allow attribute access using notation like `x['2be']`.  For the sake of
simplicity, we will not worry about this issue.

After giving some thought to the dynamic attribute names, let's turn to another essential
feature of `FrozenJSON`: the logic of the `build` class method.  `FrozenJSON.build` is used
by `__getattr__` to return a different type of object depending on the value of the
attribute being accessed: nested structures are converted to `FrozenJSON` instances or lists
of `FrozenJSON` instances.  Instead of a class method, the same logic could be implemented as
the `__new__` special method, as we'll see next.

### Flexible Object Creation with `__new__`

We often refer to `__init__` as the constructor method, but that's because we adopted jargon
from other languages.  In Python, `__init__` gets `self` as the first argument, therefore the
object already exists when `__init__` is called by the interpreter.  Also, `__init__` cannot
return anything.  So it's really an initializer, not a constructor.

When a class is called to create an instance, the special method that Python calls on that
class to construct an instance is `__new__`.  It's a class method, but gets special
treatment, so the `@classmethod` decorator is not applied to it.  Python takes the instance
returned by `__new__` and then passes it as the first argument `self` of `__init__`.  We
rarely need to code `__new__`, because the implementation inherited from `object` suffices
for the vast majority of use cases.

If necessary, the `__new__` method can also return an instance of a different class.  When
that happens, the interpreter does not call `__init__`.  In other words, Python's logic for
building an object is similar to this pseudocode:

<!-- nocheck -->
```python
# pseudocode for object construction
def make(the_class, some_arg):
    new_object = the_class.__new__(some_arg)
    if isinstance(new_object, the_class):
        the_class.__init__(new_object, some_arg)
    return new_object

# the following statements are roughly equivalent
x = Foo('bar')
x = make(Foo, 'bar')
```

Here is a variation of `FrozenJSON` where the logic of the former `build` class method was
moved to `__new__`:

```python
from collections import abc
import keyword

class FrozenJSON:
    """A read-only façade for navigating a JSON-like object
       using attribute notation
    """

    def __new__(cls, arg):  # gets the class itself, then the same arguments as __init__
        if isinstance(arg, abc.Mapping):
            return super().__new__(cls)  # default: delegate to object.__new__
        elif isinstance(arg, abc.MutableSequence):  # the rest is as in the old build method
            return [cls(item) for item in arg]
        else:
            return arg

    def __init__(self, mapping):
        self.__data = {}
        for key, value in mapping.items():
            if keyword.iskeyword(key):
                key += '_'
            self.__data[key] = value

    def __getattr__(self, name):
        try:
            return getattr(self.__data, name)
        except AttributeError:
            return FrozenJSON(self.__data[name])  # just call the class: Python calls __new__

    def __dir__(self):
        return self.__data.keys()

student = FrozenJSON({'name': 'Jim Bo', 'class': 1982})
student.class_  # keywords get a trailing underscore
# 1982
FrozenJSON([1, {'a': 2}])  # __new__ can return objects that are not FrozenJSON
# [1, <__main__.FrozenJSON object at 0x...>]
FrozenJSON(json.loads(SAMPLE_JSON)).Schedule.venues[1].name
# 'Portland 251'
```

As a class method, the first argument `__new__` gets is the class itself, and the remaining
arguments are the same that `__init__` gets, except for `self`.  The default behavior is to
delegate to the `__new__` of a superclass.  In this case, we are calling `__new__` from the
`object` base class, passing `FrozenJSON` as the only argument.  The remaining lines of
`__new__` are exactly as in the old `build` method.  Where `FrozenJSON.build` was called
before, now we just call the `FrozenJSON` class, which Python handles by calling
`FrozenJSON.__new__`.

The `__new__` method gets the class as the first argument because, usually, the created
object will be an instance of that class.  So, in `FrozenJSON.__new__`, when the expression
`super().__new__(cls)` effectively calls `object.__new__(FrozenJSON)`, the instance built by
the `object` class is actually an instance of `FrozenJSON`.  The `__class__` attribute of the
new instance will hold a reference to `FrozenJSON`, even though the actual construction is
performed by `object.__new__`, implemented in C, in the guts of the interpreter.

The OSCON JSON dataset is structured in a way that is not helpful for interactive
exploration.  For example, the event titled `'There *Will* Be Bugs'` has two speakers, 3471
and 5199.  Finding the names of the speakers is awkward, because those are serial numbers and
the `Schedule.speakers` list is not indexed by them.  To get each speaker, we must iterate
over that list until we find a record with a matching serial number.  Our next task is
restructuring the data to prepare for automatic retrieval of linked records.

## Computed Properties

We first saw the `@property` decorator in [A Pythonic Object](pythonic-object.md#a-hashable-vector2d),
where we used two properties in `Vector2d` just to make the `x` and `y` attributes read-only.
Here we will see properties that compute values, leading to a discussion of how to cache such
values.

The records in the `'events'` list of the OSCON JSON data contain integer serial numbers
pointing to records in the `'speakers'` and `'venues'` lists.  We will implement an `Event`
class with `venue` and `speakers` properties to return the linked data automatically — in
other words, "dereferencing" the serial number.  Given an `Event` instance, this is the
desired behavior:

<!-- nocheck -->
```python
event  # given an Event instance...
# <Event 'There *Will* Be Bugs'>
event.venue  # ...reading event.venue returns a Record object instead of a serial number
# <Record serial=1449>
event.venue.name  # now it's easy to get the name of the venue
# 'Portland 251'
for spkr in event.speakers:  # event.speakers returns a list of Record instances
    print(f'{spkr.serial}: {spkr.name}')

# 3471: Anna Martelli Ravenscroft
# 5199: Alex Martelli
```

As usual, we will build the code step-by-step, starting with the `Record` class and a
function to read the JSON data and return a `dict` with `Record` instances.

### Step 1: Data-Driven Attribute Creation

Here is `schedule_v1.py`.  (The original reads a JSON file; this version reads our sample
string, so the examples run anywhere.)

```python
import json

class Record:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)  # build attributes from keyword arguments

    def __repr__(self):
        return f'<{self.__class__.__name__} serial={self.serial!r}>'

def load(source=SAMPLE_JSON):
    records = {}  # load will return a dict of Record instances
    raw_data = json.loads(source)  # native Python objects: lists, dicts, strings, numbers
    for collection, raw_records in raw_data['Schedule'].items():  # the four top-level lists
        record_type = collection.removesuffix('s')  # e.g. speakers -> speaker
        for raw_record in raw_records:
            key = f'{record_type}.{raw_record["serial"]}'  # e.g. 'speaker.3471'
            records[key] = Record(**raw_record)  # store a Record under that key
    return records

records = load()  # a dict with the JSON data
speaker = records['speaker.3471']  # keys are built from the record type and serial number
speaker  # speaker is an instance of Record
# <Record serial=3471>
speaker.name, speaker.twitter  # fields from the JSON are Record instance attributes
# ('Anna Martelli Ravenscroft', 'annaraven')
```

`load` iterates over the four top-level lists named `'conferences'`, `'events'`,
`'speakers'` and `'venues'`.  `record_type` is the list name without the trailing `s`, so
`speakers` becomes `speaker`, using the `str.removesuffix` method (Python 3.9+,
[**PEP 616**](https://peps.python.org/pep-0616/)).  It builds keys in the format
`'speaker.3471'`, and creates a `Record` instance saved in `records` with that key.

The `Record.__init__` method illustrates an old Python hack.  Recall that the `__dict__` of
an object is where its attributes are kept — unless `__slots__` is declared in the class, as
we saw in [Saving Memory with `__slots__`](pythonic-object.md#saving-memory-with-__slots__).
So, updating an instance `__dict__` with a mapping is a quick way to create a bunch of
attributes in that instance.

> **Note**
>
> Depending on the application, the `Record` class may need to deal with keys that are not
> valid attribute names, as we saw in [The Invalid Attribute Name Problem](#the-invalid-attribute-name-problem).
> Dealing with that issue would distract from the key idea of this example, and is not a
> problem in the dataset we are reading.

The definition of `Record` is so simple that you may be wondering why we did not use it
before, instead of the more complicated `FrozenJSON`.  There are two reasons.  First,
`FrozenJSON` works by recursively converting the nested mappings and lists; `Record` doesn't
need that because our converted dataset doesn't have mappings nested in mappings or lists.
The records contain only strings, integers, lists of strings, and lists of integers.  Second
reason: `FrozenJSON` provides access to the embedded `__data` dict attributes — which we used
to invoke methods like `.keys()` — and now we don't need that functionality either.

> **Tip**
>
> The Python standard library provides classes similar to `Record`, where each instance has
> an arbitrary set of attributes built from keyword arguments given to `__init__`:
> [`types.SimpleNamespace`](https://docs.python.org/3/library/types.html#types.SimpleNamespace),
> `argparse.Namespace` and `multiprocessing.managers.Namespace`.  The simpler `Record` class
> here highlights the essential idea: `__init__` updating the instance `__dict__`.

```python
from types import SimpleNamespace
ns = SimpleNamespace(serial=3471, name='Anna Martelli Ravenscroft')
ns
# namespace(serial=3471, name='Anna Martelli Ravenscroft')
ns.name
# 'Anna Martelli Ravenscroft'
```

After reorganizing the schedule dataset, we can enhance the `Record` class to automatically
retrieve venue and speaker records referenced in an event record.  We'll use properties to
do that in the next examples.

### Step 2: Property to Retrieve a Linked Record

The goal of this next version is: given an event record, reading its `venue` property will
return a `Record`.  This is similar to what the Django ORM does when you access a
`ForeignKey` field: instead of the key, you get the linked model object.  We start with an
enhanced `Record` class:

```python
import inspect
import json

class Record:

    __index = None  # will hold a reference to the dict returned by load

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __repr__(self):
        return f'<{self.__class__.__name__} serial={self.serial!r}>'

    @staticmethod
    def fetch(key):  # a staticmethod: not influenced by the instance or class it's called on
        if Record.__index is None:  # populate the Record.__index, if needed
            Record.__index = load()
        return Record.__index[key]  # use it to retrieve the record with the given key
```

`inspect` will be used in `load`, listed next.  The `__index` private class attribute will
eventually hold a reference to the `dict` returned by `load`.  `fetch` is a `staticmethod` to
make it explicit that its effect is not influenced by the instance or class on which it is
called.  This is one example where the use of `staticmethod` makes sense.  The `fetch`
method always acts on the `Record.__index` class attribute, even if invoked from a subclass,
like `Event.fetch()` — which we'll soon explore.  It would be misleading to code it as a class
method because the `cls` first argument would not be used.

Now we get to the use of a property in the `Event` class:

```python
class Event(Record):  # Event extends Record

    def __repr__(self):
        try:
            return f'<{self.__class__.__name__} {self.name!r}>'  # use name, if available
        except AttributeError:
            return super().__repr__()

    @property
    def venue(self):
        key = f'venue.{self.venue_serial}'
        return self.__class__.fetch(key)  # fetch is inherited from Record
```

If the instance has a `name` attribute, it is used to produce a custom representation.
Otherwise, we delegate to the `__repr__` from `Record`.  The `venue` property builds a `key`
from the `venue_serial` attribute, and passes it to the `fetch` method, inherited from
`Record`.

The second line of the `venue` method returns `self.__class__.fetch(key)`.  Why not simply
call `self.fetch(key)`?  The simpler form works with the specific OSCON dataset because there
is no event record with a `'fetch'` key.  But, if an event record had a key named `'fetch'`,
then within that specific `Event` instance, the reference `self.fetch` would retrieve the
value of that field, instead of the `fetch` method that `Event` inherits from `Record`.  This
is a subtle bug, and it could easily sneak through testing because it depends on the
dataset.

> **Warning**
>
> When creating instance attribute names from data, there is always the risk of bugs due to
> shadowing of class attributes — such as methods — or data loss through accidental
> overwriting of existing instance attributes.  These problems may explain why Python dicts
> are not like JavaScript objects in the first place.

If the `Record` class behaved more like a mapping, implementing a dynamic `__getitem__`
instead of a dynamic `__getattr__`, there would be no risk of bugs from overwriting or
shadowing.  A custom mapping is probably the Pythonic way to implement `Record`.  But if we
took that road, we'd not be studying the tricks and traps of dynamic attribute programming.

The final piece of this example is the revised `load` function:

```python
def load(source=SAMPLE_JSON):
    records = {}
    raw_data = json.loads(source)
    for collection, raw_records in raw_data['Schedule'].items():
        record_type = collection.removesuffix('s')  # no changes so far
        cls_name = record_type.capitalize()  # e.g. 'event' becomes 'Event'
        cls = globals().get(cls_name, Record)  # get an object by that name, or Record
        if inspect.isclass(cls) and issubclass(cls, Record):  # if it's a Record subclass...
            factory = cls  # ...use it as the factory
        else:
            factory = Record  # otherwise, use Record
        for raw_record in raw_records:  # the same loop as before, except that...
            key = f'{record_type}.{raw_record["serial"]}'
            records[key] = factory(**raw_record)  # ...the record is built by factory
    return records

event = Record.fetch('event.33950')  # fetch gets a Record or an Event from the dataset
event  # event is an instance of the Event class
# <Event 'There *Will* Be Bugs'>
event.venue  # accessing event.venue returns a Record instance
# <Record serial=1449>
event.venue.name
# 'Portland 251'
event.venue_serial  # the Event instance also has a venue_serial attribute
# 1449
```

We capitalize the `record_type` to get a possible class name; e.g., `'event'` becomes
`'Event'`.  Then we get an object by that name from the module global scope, or the `Record`
class if there's no such object.  If the object just retrieved is a class, and is a subclass
of `Record`, we bind the `factory` name to it.  This means `factory` may be any subclass of
`Record`, depending on the `record_type`.  The object stored in `records` is constructed by
`factory`.

Note that the only `record_type` that has a custom class is `Event`, but if classes named
`Speaker` or `Venue` are coded, `load` will automatically use those classes when building and
saving records, instead of the default `Record` class.

We'll now apply the same idea to a new `speakers` property in the `Event` class.

### Step 3: Property Overriding an Existing Attribute

The name of the `venue` property does not match a field name in records of the `"events"`
collection.  Its data comes from a `venue_serial` field name.  In contrast, each record in
the `events` collection has a `speakers` field with a list of serial numbers.  We want to
expose that information as a `speakers` property in `Event` instances, which returns a list
of `Record` instances.  This name clash requires some special attention:

<!-- nocheck -->
```python
@property
def speakers(self):
    spkr_serials = self.__dict__['speakers']  # read from __dict__ to avoid recursion
    fetch = self.__class__.fetch
    return [fetch(f'speaker.{key}')
            for key in spkr_serials]  # all records matching the serial numbers
```

The data we want is in a `speakers` attribute, but we must retrieve it directly from the
instance `__dict__` to avoid a recursive call to the `speakers` property.  Inside the
`speakers` method, trying to read `self.speakers` will invoke the property itself, quickly
raising a `RecursionError`.  However, if we read the same data via
`self.__dict__['speakers']`, Python's usual algorithm for retrieving attributes is bypassed,
the property is not called, and the recursion is avoided.  For this reason, reading or
writing data directly to an object's `__dict__` is a common Python metaprogramming trick.

> **Warning**
>
> The interpreter evaluates `obj.my_attr` by first looking at the class of `obj`.  If the
> class has a property with the `my_attr` name, that property shadows an instance attribute
> by the same name.  Examples in [Properties Override Instance Attributes](#properties-override-instance-attributes)
> will demonstrate this, and [Attribute Descriptors](descriptors.md) will reveal that a
> property is implemented as a descriptor — a more powerful and general abstraction.

Here it is, added to `Event`:

```python
class Event(Record):

    def __repr__(self):
        try:
            return f'<{self.__class__.__name__} {self.name!r}>'
        except AttributeError:
            return super().__repr__()

    @property
    def venue(self):
        key = f'venue.{self.venue_serial}'
        return self.__class__.fetch(key)

    @property
    def speakers(self):
        spkr_serials = self.__dict__['speakers']
        fetch = self.__class__.fetch
        return [fetch(f'speaker.{key}')
                for key in spkr_serials]

Record._Record__index = None  # reset the index, so load() uses the new Event class
event = Record.fetch('event.33950')
for spkr in event.speakers:
    print(f'{spkr.serial}: {spkr.name}')

# 3471: Anna Martelli Ravenscroft
# 5199: Alex Martelli
```

(The line resetting `Record._Record__index` — the mangled name of the private `__index`
attribute — is needed only because we redefined `Event` in the same session.)

The list comprehension in `speakers` may look expensive.  Not really, because events in the
OSCON dataset have few speakers, so coding anything more complicated would be premature
optimization.  However, caching a property is a common need — and there are caveats.  So
let's see how to do that in the next examples.

### Step 4: Bespoke Property Cache

Caching properties is a common need because there is an expectation that an expression like
`event.venue` should be inexpensive.  Some form of caching could become necessary if the
`Record.fetch` method behind the `Event` properties needed to query a database or a web API.
A straightforward handmade cache looks like this:

<!-- nocheck -->
```python
@property
def speakers(self):
    if not hasattr(self, '__speaker_objs'):  # if there is no cache attribute, compute it
        spkr_serials = self.__dict__['speakers']
        fetch = self.__class__.fetch
        self.__speaker_objs = [fetch(f'speaker.{key}')
                for key in spkr_serials]
    return self.__speaker_objs
```

> **Warning**
>
> That code has a subtle bug: `hasattr(self, '__speaker_objs')` uses the literal string
> `'__speaker_objs'`, but the assignment `self.__speaker_objs = ...` inside the class stores
> the attribute under the mangled name `_Event__speaker_objs`, so the check always fails and
> the "cache" is recomputed on every access.  Name mangling applies to identifiers in the
> source code, not to strings.

Creating an attribute after the instance is initialized also works against the key-sharing
dictionary optimization of [**PEP 412**](https://peps.python.org/pep-0412/), which lets
instances of the same class share the storage of their attribute names, provided they all
create the same attributes in `__init__`.  A similar hand-rolled solution that plays well
with key sharing requires coding an `__init__` for the `Event` class, to create the necessary
`__speaker_objs` initialized to `None`, and then checking for that in the `speakers` method:

<!-- nocheck -->
```python
class Event(Record):

    def __init__(self, **kwargs):
        self.__speaker_objs = None
        super().__init__(**kwargs)

    # 15 lines omitted...

    @property
    def speakers(self):
        if self.__speaker_objs is None:
            spkr_serials = self.__dict__['speakers']
            fetch = self.__class__.fetch
            self.__speaker_objs = [fetch(f'speaker.{key}')
                    for key in spkr_serials]
        return self.__speaker_objs
```

These illustrate simple caching techniques that are fairly common in legacy Python codebases.
However, in multithreaded programs, handmade caches like those introduce race conditions: if
two threads are reading a property that was not previously cached, both may compute the value,
and one may read a value that another thread is still building.  The standard library offers
ready-made caching decorators, with their own caveats, explained next.

### Step 5: Caching Properties with `functools`

The `functools` module provides three decorators for caching.  We saw `@cache` and
`@lru_cache` in [Memoization with `functools.cache`](decorators.md#memoization-with-functoolscache).
The third one is
[`@cached_property`](https://docs.python.org/3/library/functools.html#functools.cached_property).

The `functools.cached_property` decorator caches the result of the method in an instance
attribute with the same name.  For example, here the value computed by the `venue` method is
stored in a `venue` attribute in `self`.  After that, when client code tries to read `venue`,
the newly created `venue` instance attribute is used instead of the method:

<!-- nocheck -->
```python
@cached_property
def venue(self):
    key = f'venue.{self.venue_serial}'
    return self.__class__.fetch(key)
```

In [Step 3](#step-3-property-overriding-an-existing-attribute), we saw that a property shadows
an instance attribute by the same name.  If that is true, how can `@cached_property` work?  If
the property overrides the instance attribute, the `venue` attribute will be ignored and the
`venue` method will always be called, computing the `key` and running `fetch` every time!

The answer is a bit sad: `cached_property` is a misnomer.  The `@cached_property` decorator
does not create a full-fledged property, it creates a *nonoverriding descriptor*.  A
descriptor is an object that manages the access to an attribute in another class.  We will
dive into descriptors in [Attribute Descriptors](descriptors.md).  The `property` decorator
is a high-level API to create an *overriding descriptor*.

For now, let us set aside the underlying implementation and focus on the differences between
`cached_property` and `property` from a user's point of view.  Raymond Hettinger explains them
very well in the Python docs:

> The mechanics of `cached_property()` are somewhat different from `property()`.  A regular
> property blocks attribute writes unless a setter is defined.  In contrast, a
> `cached_property` allows writes.
>
> The `cached_property` decorator only runs on lookups and only when an attribute of the same
> name doesn't exist.  When it does run, the `cached_property` writes to the attribute with
> the same name.  Subsequent attribute reads and writes take precedence over the
> `cached_property` method and it works like a normal attribute.
>
> The cached value can be cleared by deleting the attribute.  This allows the
> `cached_property` method to run again.

```python
from functools import cached_property

class Circle:
    def __init__(self, radius):
        self.radius = radius

    @cached_property
    def area(self):
        print('computing area...')
        return 3.14159 * self.radius ** 2

c = Circle(2)
c.area  # the first read runs the method...
# computing area...
# 12.56636
c.area  # ...and stores the result in c.__dict__['area']
# 12.56636
vars(c)
# {'radius': 2, 'area': 12.56636}
del c.area  # deleting the attribute clears the cache
c.radius = 1
c.area
# computing area...
# 3.14159
```

Back to our `Event` class: the specific behavior of `@cached_property` makes it unsuitable to
decorate `speakers`, because that method relies on an existing attribute also named
`speakers`, containing the serial numbers of the event speakers.

> **Warning**
>
> `@cached_property` has some important limitations:
>
> * It cannot be used as a drop-in replacement to `@property` if the decorated method already
>   depends on an instance attribute with the same name.
> * It cannot be used in a class that defines `__slots__` (it needs an instance `__dict__`).
> * It defeats the key-sharing optimization of the instance `__dict__`, because it creates an
>   instance attribute after `__init__`.
> * It is not synchronized: since Python 3.12 it no longer holds a lock (the old lock was per
>   property, not per instance, which caused contention), so in multithreaded code the method
>   may run more than once for the same instance.  That's harmless if the method is idempotent.

The `@cached_property` documentation recommends an alternative solution that we can use with
`speakers`: stacking `@property` and `@cache` decorators:

<!-- nocheck -->
```python
@property  # the order is important: @property goes on top...
@cache  # ...of @cache
def speakers(self):
    spkr_serials = self.__dict__['speakers']
    fetch = self.__class__.fetch
    return [fetch(f'speaker.{key}')
            for key in spkr_serials]
```

Recall from [Memoization with `functools.cache`](decorators.md#memoization-with-functoolscache) the meaning of that syntax.
The top three lines are similar to `speakers = property(cache(speakers))`.  The `@cache` is
applied to `speakers`, returning a new function.  That function then is decorated by
`@property`, which replaces it with a newly constructed property.

> **Warning**
>
> `@cache` on a method stores `self` as part of the cache key, in a cache that belongs to the
> class.  That keeps every instance alive as long as the class exists — a memory leak for
> classes with many short-lived instances — and requires instances to be hashable.  It's fine
> for our `Event` records, which live as long as the program, but keep the trade-off in mind.

This wraps up our discussion of read-only properties and caching decorators, exploring the
OSCON dataset.  In the next section, we start a new series of examples creating read/write
properties.

## Using a Property for Attribute Validation

Besides computing attribute values, properties are also used to enforce business rules by
changing a public attribute into an attribute protected by a getter and setter without
affecting client code.  Let's work through an extended example.

### LineItem Take #1: Class for an Item in an Order

Imagine an app for a store that sells organic food in bulk, where customers can order nuts,
dried fruit or cereals by weight.  In that system, each order would hold a sequence of line
items, and each line item could be represented by an instance of a class like this:

```python
class LineItem:

    def __init__(self, description, weight, price):
        self.description = description
        self.weight = weight
        self.price = price

    def subtotal(self):
        return self.weight * self.price
```

That's nice and simple.  Perhaps too simple:

```python
raisins = LineItem('Golden raisins', 10, 6.95)
raisins.subtotal()
# 69.5
raisins.weight = -20  # garbage in...
raisins.subtotal()  # garbage out...
# -139.0
```

This is a toy example, but not as fanciful as you may think.  Here is a story from the early
days of Amazon.com: "We found that customers could order a negative quantity of books!  And we
would credit their credit card with the price and, I assume, wait around for them to ship the
books," said Jeff Bezos.

How do we fix this?  We could change the interface of `LineItem` to use a getter and a setter
for the `weight` attribute.  That would be the Java way, and it's not wrong.  On the other
hand, it's natural to be able to set the `weight` of an item by just assigning to it; and
perhaps the system is in production with other parts already accessing `item.weight`
directly.  In this case, the Python way would be to replace the data attribute with a
property.

### LineItem Take #2: A Validating Property

Implementing a property will allow us to use a getter and a setter, but the interface of
`LineItem` will not change (i.e., setting the `weight` of a `LineItem` will still be written
as `raisins.weight = 12`):

```python
class LineItem:

    def __init__(self, description, weight, price):
        self.description = description
        self.weight = weight  # the property setter is already in use here
        self.price = price

    def subtotal(self):
        return self.weight * self.price

    @property  # @property decorates the getter method
    def weight(self):  # all methods implementing a property share the public name
        return self.__weight  # the actual value is stored in a private attribute

    @weight.setter  # the getter's .setter attribute ties the getter and setter together
    def weight(self, value):
        if value > 0:
            self.__weight = value  # if the value is greater than zero, set it
        else:
            raise ValueError('value must be > 0')  # otherwise, raise ValueError
```

The property setter is already in use in `__init__`, making sure that no instances with
negative weight can be created.  `@property` decorates the getter method.  All the methods
that implement a property share the name of the public attribute: `weight`.  The actual value
is stored in a private attribute `__weight`.  The decorated getter has a `.setter` attribute,
which is also a decorator; this ties the getter and setter together.  Note how a `LineItem`
with an invalid weight cannot be created now:

```python
walnuts = LineItem('walnuts', 0, 10.00)
# Traceback (most recent call last):
#     ...
# ValueError: value must be > 0
```

Now we have protected `weight` from users providing negative values.  Although buyers usually
can't set the price of an item, a clerical error or a bug may create a `LineItem` with a
negative `price`.  To prevent that, we could also turn `price` into a property, but this would
entail some repetition in our code.

Remember the Paul Graham quote from [Iterators, Generators, and Classic Coroutines](iterators-generators.md):
"When I see patterns in my programs, I consider it a sign of trouble."  The cure for
repetition is abstraction.  There are two ways to abstract away property definitions: using a
property factory or a descriptor class.  The descriptor class approach is more flexible, and
we'll devote [Attribute Descriptors](descriptors.md) to a full discussion of it.  Properties
are in fact implemented as descriptor classes themselves.  But here we will continue our
exploration of properties by implementing a property factory as a function.  But before we
can implement a property factory, we need to have a deeper understanding of properties.

## A Proper Look at Properties

Although often used as a decorator, the `property` built-in is actually a class.  In Python,
functions and classes are often interchangeable, because both are callable and there is no
`new` operator for object instantiation, so invoking a constructor is no different from
invoking a factory function.  And both can be used as decorators, as long as they return a
new callable that is a suitable replacement of the decorated callable.  This is the full
signature of the [`property`](https://docs.python.org/3/library/functions.html#property)
constructor:

<!-- nocheck -->
```python
property(fget=None, fset=None, fdel=None, doc=None)
```

All arguments are optional, and if a function is not provided for one of them, the
corresponding operation is not allowed by the resulting property object.

The `property` type was added in Python 2.2, but the `@` decorator syntax appeared only in
Python 2.4, so for a few years, properties were defined by passing the accessor functions as
the first two arguments.  Here is the "classic" syntax for defining properties without
decorators:

```python
class LineItem:

    def __init__(self, description, weight, price):
        self.description = description
        self.weight = weight
        self.price = price

    def subtotal(self):
        return self.weight * self.price

    def get_weight(self):  # a plain getter
        return self.__weight

    def set_weight(self, value):  # a plain setter
        if value > 0:
            self.__weight = value
        else:
            raise ValueError('value must be > 0')

    weight = property(get_weight, set_weight)  # build the property, assign to a class attribute
```

The classic form is better than the decorator syntax in some situations; the code of the
property factory we'll discuss shortly is one example.  On the other hand, in a class body
with many methods, the decorators make it explicit which are the getters and setters, without
depending on the convention of using `get` and `set` prefixes in their names.

The presence of a property in a class affects how attributes in instances of that class can be
found in a way that may be surprising at first.  The next section explains.

### Properties Override Instance Attributes

Properties are always class attributes, but they actually manage attribute access in the
instances of the class.  In [Overriding Class Attributes](pythonic-object.md#overriding-class-attributes)
we saw that when an instance and its class both have a data attribute by the same name, the
instance attribute overrides, or shadows, the class attribute — at least when read through
that instance:

```python
class Class:  # two class attributes: the data attribute and the prop property
    data = 'the class data attr'
    @property
    def prop(self):
        return 'the prop value'

obj = Class()
vars(obj)  # vars returns the __dict__ of obj: it has no instance attributes
# {}
obj.data  # reading obj.data retrieves the value of Class.data
# 'the class data attr'
obj.data = 'bar'  # writing to obj.data creates an instance attribute
vars(obj)
# {'data': 'bar'}
obj.data  # now the instance data shadows the class data
# 'bar'
Class.data  # the Class.data attribute is intact
# 'the class data attr'
```

Now, let's try to override the `prop` attribute on the `obj` instance:

```python
Class.prop  # reading prop from Class retrieves the property object itself
# <property object at 0x...>
obj.prop  # reading obj.prop executes the property getter
# 'the prop value'
obj.prop = 'foo'  # trying to set an instance prop attribute fails
# Traceback (most recent call last):
#   ...
# AttributeError: property 'prop' of 'Class' object has no setter
obj.__dict__['prop'] = 'foo'  # putting 'prop' directly in obj.__dict__ works
vars(obj)  # obj now has two instance attributes: data and prop
# {'data': 'bar', 'prop': 'foo'}
obj.prop  # but reading obj.prop still runs the getter: the property is not shadowed
# 'the prop value'
Class.prop = 'baz'  # overwriting Class.prop destroys the property object
obj.prop  # now obj.prop retrieves the instance attribute
# 'foo'
```

As a final demonstration, we'll add a new property to `Class`, and see it overriding an
instance attribute:

```python
obj.data  # obj.data retrieves the instance data attribute
# 'bar'
Class.data  # Class.data retrieves the class data attribute
# 'the class data attr'
Class.data = property(lambda self: 'the "data" prop value')  # a new property
obj.data  # obj.data is now shadowed by the Class.data property
# 'the "data" prop value'
del Class.data  # delete the property
obj.data  # obj.data now reads the instance data attribute again
# 'bar'
```

The main point of this section is that an expression like `obj.data` does not start the
search for `data` in `obj`.  The search actually starts at `obj.__class__`, and only if there
is no property named `data` in the class, Python looks in the `obj` instance itself.  This
applies to *overriding descriptors* in general, of which properties are just one example.
Further treatment of descriptors must wait for [Attribute Descriptors](descriptors.md).

Now back to properties.  Every Python code unit — modules, functions, classes, methods — can
have a docstring.  The next topic is how to attach documentation to properties.

### Property Documentation

When tools such as the console `help()` function or IDEs need to display the documentation of
a property, they extract the information from the `__doc__` attribute of the property.  If
used with the classic call syntax, `property` can get the documentation string as the `doc`
argument:

<!-- nocheck -->
```python
weight = property(get_weight, set_weight, doc='weight in kilograms')
```

The docstring of the getter method — the one with the `@property` decorator itself — is used
as the documentation of the property as a whole:

```python
class Foo:

    @property
    def bar(self):
        """The bar attribute"""
        return self.__dict__['bar']

    @bar.setter
    def bar(self, value):
        self.__dict__['bar'] = value

Foo.bar.__doc__  # this is what help(Foo.bar) and help(Foo) display
# 'The bar attribute'
```

Now that we have these property essentials covered, let's go back to the issue of protecting
both the `weight` and `price` attributes of `LineItem` so they only accept values greater than
zero — but without implementing two nearly identical pairs of getters/setters by hand.

## Coding a Property Factory

We'll create a factory to create `quantity` properties — so named because the managed
attributes represent quantities that can't be negative or zero in the application.  Here is
the implementation of the `quantity` property factory (adapted from "Recipe 9.21. Avoiding
Repetitive Property Methods" in *Python Cookbook*, 3rd ed., by Beazley and Jones):

```python
def quantity(storage_name):  # storage_name determines where the data is stored

    def qty_getter(instance):  # instance refers to the LineItem where the value is stored
        return instance.__dict__[storage_name]  # bypass the property to avoid recursion

    def qty_setter(instance, value):
        if value > 0:
            instance.__dict__[storage_name] = value  # store directly in the instance __dict__
        else:
            raise ValueError('value must be > 0')

    return property(qty_getter, qty_setter)  # build a custom property object and return it
```

And here is the clean look of the `LineItem` class using two instances of `quantity`
properties: one for managing the `weight` attribute, the other for `price`:

```python
class LineItem:
    weight = quantity('weight')  # use the factory to define the weight property
    price = quantity('price')  # this second call builds another custom property, price

    def __init__(self, description, weight, price):
        self.description = description
        self.weight = weight  # the property is already active here, rejecting weight <= 0
        self.price = price

    def subtotal(self):
        return self.weight * self.price  # the properties retrieve the values stored
```

Recall that properties are class attributes.  When building each `quantity` property, we need
to pass the name of the `LineItem` attribute that will be managed by that specific property.
Having to type the word `weight` twice in `weight = quantity('weight')` is unfortunate.  But
avoiding that repetition is complicated because the property has no way of knowing which class
attribute name will be bound to it.  Remember: the righthand side of an assignment is
evaluated first, so when `quantity()` is invoked, the `weight` class attribute doesn't even
exist.

> **Note**
>
> Improving the `quantity` property so that the user doesn't need to retype the attribute name
> is a nontrivial metaprogramming problem.  We'll solve that problem in
> [Attribute Descriptors](descriptors.md), with the `__set_name__` special method.

The bits of the factory that deserve careful study revolve around the `storage_name`
variable.  When you code each property in the traditional way, the name of the attribute where
you will store a value is hardcoded in the getter and setter methods.  But here, the
`qty_getter` and `qty_setter` functions are generic, and they depend on the `storage_name`
variable to know where to get/set the managed attribute in the instance `__dict__`.  Each time
the `quantity` factory is called to build a property, the `storage_name` must be set to a
unique value.  The functions `qty_getter` and `qty_setter` will be wrapped by the `property`
object created in the last line of the factory function.  Later, when called to perform their
duties, these functions will read the `storage_name` from their closures (see
[Closures](decorators.md#closures)) to determine where to retrieve/store the managed attribute
values.

Here we create and inspect a `LineItem` instance, exposing the storage attributes:

```python
nutmeg = LineItem('Moluccan nutmeg', 8, 13.95)
nutmeg.weight, nutmeg.price  # read through the properties shadowing the instance attributes
# (8, 13.95)
nutmeg.__dict__  # the actual instance attributes used to store the values
# {'description': 'Moluccan nutmeg', 'weight': 8, 'price': 13.95}
nutmeg.price = -1
# Traceback (most recent call last):
#   ...
# ValueError: value must be > 0
```

Note how the properties built by our factory leverage the behavior described in
[Properties Override Instance Attributes](#properties-override-instance-attributes): the
`weight` property overrides the `weight` instance attribute so that every reference to
`self.weight` or `nutmeg.weight` is handled by the property functions, and the only way to
bypass the property logic is to access the instance `__dict__` directly.

The factory may be a bit tricky, but it's concise: it's identical in length to the decorated
getter/setter pair defining just the `weight` property in Take #2.  The `LineItem` definition
looks much better without the noise of the getter/setters.  In a real system, that same kind
of validation may appear in many fields, across several classes, and the `quantity` factory
would be placed in a utility module to be used over and over again.  Eventually that simple
factory could be refactored into a more extensible descriptor class, with specialized
subclasses performing different validations.  We'll do that in
[Attribute Descriptors](descriptors.md).

Now let us wrap up the discussion of properties with the issue of attribute deletion.

## Handling Attribute Deletion

We can use the `del` statement to delete not only variables, but also attributes:

```python
class Demo:
    pass

d = Demo()
d.color = 'green'
d.color
# 'green'
del d.color
d.color
# Traceback (most recent call last):
#   File "<stdin>", line 1, in <module>
# AttributeError: 'Demo' object has no attribute 'color'
```

In practice, deleting attributes is not something we do every day in Python, and the
requirement to handle it with a property is even more unusual.  But it is supported, and here
is a silly example to demonstrate it.  In a property definition, the
`@my_property.deleter` decorator wraps the method in charge of deleting the attribute managed
by the property.  This example is inspired by the scene with the Black Knight from *Monty
Python and the Holy Grail*:

```python
class BlackKnight:

    def __init__(self):
        self.phrases = [
            ('an arm', "'Tis but a scratch."),
            ('another arm', "It's just a flesh wound."),
            ('a leg', "I'm invincible!"),
            ('another leg', "All right, we'll call it a draw.")
        ]

    @property
    def member(self):
        print('next member is:')
        return self.phrases[0][0]

    @member.deleter
    def member(self):
        member, text = self.phrases.pop(0)
        print(f'BLACK KNIGHT (loses {member}) -- {text}')

knight = BlackKnight()
knight.member
# next member is:
# 'an arm'
del knight.member
# BLACK KNIGHT (loses an arm) -- 'Tis but a scratch.
del knight.member
# BLACK KNIGHT (loses another arm) -- It's just a flesh wound.
del knight.member
# BLACK KNIGHT (loses a leg) -- I'm invincible!
del knight.member
# BLACK KNIGHT (loses another leg) -- All right, we'll call it a draw.
```

Using the classic call syntax instead of decorators, the `fdel` argument configures the deleter
function.  For example, the `member` property would be coded like this in the body of the
`BlackKnight` class: `member = property(member_getter, fdel=member_deleter)`.

If you are not using a property, attribute deletion can also be handled by implementing the
lower-level `__delattr__` special method, presented in
[Special Methods for Attribute Handling](#special-methods-for-attribute-handling).

Properties are a powerful feature, but sometimes simpler or lower-level alternatives are
preferable.  In the final section of this chapter, we'll review some of the core APIs that
Python offers for dynamic attribute programming.

## Essential Attributes and Functions for Attribute Handling

Throughout this chapter, and even before in this book, we've used some of the built-in
functions and special methods Python provides for dealing with dynamic attributes.  This
section gives an overview of them in one place, because their documentation is scattered in
the official docs.

### Special Attributes that Affect Attribute Handling

The behavior of many of the functions and special methods listed in the following sections
depend on three special attributes:

`__class__`
: A reference to the object's class (i.e., `obj.__class__` is the same as `type(obj)`).
  Python looks for special methods such as `__getattr__` only in an object's class, and not in
  the instances themselves.

`__dict__`
: A mapping that stores the writable attributes of an object or class.  An object that has a
  `__dict__` can have arbitrary new attributes set at any time.  If a class has a `__slots__`
  attribute, then its instances may not have a `__dict__`.

`__slots__`
: An attribute that may be defined in a class to save memory.  `__slots__` is a tuple of
  strings naming the allowed attributes.  (It can be coded as a list, but it's better to be
  explicit and always use a tuple, because changing the list after the class body is processed
  has no effect.)  If the `'__dict__'` name is not in `__slots__`, then the instances of that
  class will not have a `__dict__` of their own, and only the attributes listed in `__slots__`
  will be allowed in those instances.  Recall
  [Saving Memory with `__slots__`](pythonic-object.md#saving-memory-with-__slots__) for more.

### Built-In Functions for Attribute Handling

These five built-in functions perform object attribute reading, writing and introspection:

`dir([object])`
: Lists most attributes of the object.  The official docs say `dir` is intended for
  interactive use so it does not provide a comprehensive list of attributes, but an
  "interesting" set of names.  `dir` can inspect objects implemented with or without a
  `__dict__`.  The `__dict__` attribute itself is not listed by `dir`, but the `__dict__` keys
  are listed.  Several special attributes of classes, such as `__mro__`, `__bases__` and
  `__name__`, are not listed by `dir` either.  You can customize the output of `dir` by
  implementing the `__dir__` special method, as we saw in `FrozenJSON`.  If the optional
  `object` argument is not given, `dir` lists the names in the current scope.

`getattr(object, name[, default])`
: Gets the attribute identified by the `name` string from the `object`.  The main use case is
  to retrieve attributes (or methods) whose names we don't know beforehand.  This may fetch an
  attribute from the object's class or from a superclass.  If no such attribute exists,
  `getattr` raises `AttributeError` or returns the `default` value, if given.  One great
  example of using `getattr` is in the `Cmd.onecmd` method in the `cmd` package of the
  standard library, where it is used to get and execute a user-defined command.

`hasattr(object, name)`
: Returns `True` if the named attribute exists in the `object`, or can be somehow fetched
  through it (by inheritance, for example).  The documentation explains: "This is implemented
  by calling `getattr(object, name)` and seeing whether it raises an `AttributeError` or not."

`setattr(object, name, value)`
: Assigns the `value` to the named attribute of `object`, if the `object` allows it.  This may
  create a new attribute or overwrite an existing one.

`vars([object])`
: Returns the `__dict__` of `object`; `vars` can't deal with instances of classes that define
  `__slots__` and don't have a `__dict__` (contrast with `dir`, which handles such instances).
  Without an argument, `vars()` does the same as `locals()`: returns a `dict` representing the
  local scope.

```python
class Cmd:
    def do_greet(self, name):
        return f'Hello, {name}!'

    def onecmd(self, line):  # dispatch on a name read at runtime, like cmd.Cmd.onecmd
        command, _, arg = line.partition(' ')
        method = getattr(self, f'do_{command}', None)
        if method is None:
            return f'*** Unknown syntax: {line}'
        return method(arg)

c = Cmd()
c.onecmd('greet world')
# 'Hello, world!'
c.onecmd('fly away')
# '*** Unknown syntax: fly away'
hasattr(c, 'do_greet'), hasattr(c, 'do_fly')
# (True, False)
setattr(c, 'mood', 'cheerful')
vars(c)
# {'mood': 'cheerful'}
```

### Special Methods for Attribute Handling

When implemented in a user-defined class, the special methods listed here handle attribute
retrieval, setting, deletion and listing.  Attribute access using either dot notation or the
built-in functions `getattr`, `hasattr` and `setattr` triggers the appropriate special methods
listed here.  Reading and writing attributes directly in the instance `__dict__` does not
trigger these special methods — and that's the usual way to bypass them if needed.

The [Special method lookup](https://docs.python.org/3/reference/datamodel.html#special-method-lookup)
section of the Data Model warns: "For custom classes, implicit invocations of special methods
are only guaranteed to work correctly if defined on an object's type, not in the object's
instance dictionary."  In other words, assume that the special methods will be retrieved on
the class itself, even when the target of the action is an instance.  For this reason, special
methods are not shadowed by instance attributes with the same name.

In the following descriptions, assume there is a class named `Class`, `obj` is an instance of
`Class`, and `attr` is an attribute of `obj`.  For every one of these special methods, it
doesn't matter if the attribute access is done using dot notation or one of the built-in
functions listed above.  For example, both `obj.attr` and `getattr(obj, 'attr', 42)` trigger
`Class.__getattribute__(obj, 'attr')`.

`__delattr__(self, name)`
: Always called when there is an attempt to delete an attribute using the `del` statement;
  e.g., `del obj.attr` triggers `Class.__delattr__(obj, 'attr')`.  If `attr` is a property, its
  deleter method is never called if the class implements `__delattr__`.

`__dir__(self)`
: Called when `dir` is invoked on the object, to provide a listing of attributes; e.g.,
  `dir(obj)` triggers `Class.__dir__(obj)`.  Also used by tab-completion in all modern Python
  consoles.

`__getattr__(self, name)`
: Called only when an attempt to retrieve the named attribute fails, after the `obj`, `Class`
  and its superclasses are searched.  The expressions `obj.no_such_attr`,
  `getattr(obj, 'no_such_attr')` and `hasattr(obj, 'no_such_attr')` may trigger
  `Class.__getattr__(obj, 'no_such_attr')`, but only if an attribute by that name cannot be
  found in `obj` or in `Class` and its superclasses.

`__getattribute__(self, name)`
: Always called when there is an attempt to retrieve the named attribute directly from Python
  code (the interpreter may bypass this in some cases, for example, to get the `__repr__`
  method).  Dot notation and the `getattr` and `hasattr` built-ins trigger this method.
  `__getattr__` is only invoked after `__getattribute__`, and only when `__getattribute__`
  raises `AttributeError`.  To retrieve attributes of the instance `obj` without triggering an
  infinite recursion, implementations of `__getattribute__` should use
  `super().__getattribute__(name)`.

`__setattr__(self, name, value)`
: Always called when there is an attempt to set the named attribute.  Dot notation and the
  `setattr` built-in trigger this method; e.g., both `obj.attr = 42` and
  `setattr(obj, 'attr', 42)` trigger `Class.__setattr__(obj, 'attr', 42)`.

> **Warning**
>
> In practice, because they are unconditionally called and affect practically every attribute
> access, the `__getattribute__` and `__setattr__` special methods are harder to use correctly
> than `__getattr__`, which only handles nonexisting attribute names.  Using properties or
> descriptors is less error prone than defining these special methods.

Here is a class that logs every attribute access, to see the order of calls:

```python
class Traced:
    def __init__(self):
        self.x = 1  # goes through __setattr__

    def __getattribute__(self, name):
        print(f'__getattribute__({name!r})')
        return super().__getattribute__(name)

    def __getattr__(self, name):
        print(f'__getattr__({name!r})')
        return f'<virtual {name}>'

    def __setattr__(self, name, value):
        print(f'__setattr__({name!r}, {value!r})')
        super().__setattr__(name, value)

t = Traced()
# __setattr__('x', 1)
t.x  # found: only __getattribute__ runs
# __getattribute__('x')
# 1
t.y  # not found: __getattribute__ raises AttributeError, then __getattr__ runs
# __getattribute__('y')
# __getattr__('y')
# '<virtual y>'
```

This concludes our dive into properties, special methods, and other techniques for coding
dynamic attributes.

## Summary

We started our coverage of dynamic attributes by showing practical examples of simple classes
to make it easier to deal with a JSON dataset.  The first example was the `FrozenJSON` class
that converted nested dicts and lists into nested `FrozenJSON` instances and lists of them.
The `FrozenJSON` code demonstrated the use of the `__getattr__` special method to convert data
structures on the fly, whenever their attributes were read.  The last version of `FrozenJSON`
showcased the use of the `__new__` constructor method to transform a class into a flexible
factory of objects, not limited to instances of itself.

We then converted the JSON dataset to a `dict` storing instances of a `Record` class.  The
first rendition of `Record` was a few lines long and introduced the "bunch" idiom: using
`self.__dict__.update(**kwargs)` to build arbitrary attributes from keyword arguments passed to
`__init__`.  The second iteration added the `Event` class, implementing automatic retrieval of
linked records through properties.  Computed property values sometimes require caching, and we
covered a few ways of doing that.  After realizing that `@functools.cached_property` is not
always applicable, we learned about an alternative: combining `@property` on top of
`@functools.cache`, in that order.

Coverage of properties continued with the `LineItem` class, where a property was deployed to
protect a `weight` attribute from negative or zero values that make no business sense.  After a
deeper look at property syntax and semantics, we created a property factory to enforce the same
validation on `weight` and `price`, without coding multiple getters and setters.  The property
factory leveraged subtle concepts — such as closures, and instance attribute overriding by
properties — to provide an elegant generic solution using the same number of lines as a single
hand-coded property definition.

Finally, we had a brief look at handling attribute deletion with properties, followed by an
overview of the key special attributes, built-in functions and special methods that support
attribute metaprogramming in the core Python language.

> **Note**
>
> Python's approach to the Uniform Access Principle lets us start simple, coding data members
> as public attributes, because we know they can always be wrapped by properties (or
> descriptors) later, without changing client code.  That's why Alex Martelli calls Java-style
> accessors "goofy idioms": `someInstance.widgetCounter += 1` reads much better than
> `someInstance.setWidgetCounter(someInstance.getWidgetCounter() + 1)`.  The trade-off is that
> users of an API can't tell whether reading `product.price` is cheap or expensive — a general
> problem with abstractions, which make it hard to reason about the runtime cost of an
> expression.

> **See also**
>
> * [Customizing attribute access](https://docs.python.org/3/reference/datamodel.html#customizing-attribute-access)
>   and [Special method lookup](https://docs.python.org/3/reference/datamodel.html#special-method-lookup)
>   in the Language Reference; the [Built-in Functions](https://docs.python.org/3/library/functions.html)
>   chapter for `getattr`, `setattr`, `property`, etc.
> * *Python Cookbook*, 3rd ed., by David Beazley and Brian K. Jones: "Recipe 8.8. Extending a
>   Property in a Subclass", "Recipe 8.15. Delegating Attribute Access" and "Recipe 9.21.
>   Avoiding Repetitive Property Methods".
> * *Python in a Nutshell* by Alex Martelli, Anna Ravenscroft, Steve Holden and Paul McGuire
>   (O'Reilly), for a rigorous description of the semantics of Python classes.
> * Bertrand Meyer, *Object-Oriented Software Construction*, 2nd ed. (Pearson), where the
>   Uniform Access Principle is defined.
