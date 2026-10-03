# Asynchronous Programming

> The problem with normal approaches to asynchronous programming is that they're
> all-or-nothing propositions.  You rewrite all your code so none of it blocks or you're
> just wasting your time.
>
> — Alvaro Videla and Jason J. W. Williams, *RabbitMQ in Action*

This chapter addresses three major topics that are closely related:

* Python's `async def`, `await`, `async with` and `async for` constructs;
* objects supporting those constructs: native coroutines and asynchronous variants of
  context managers, iterables, generators and comprehensions;
* [`asyncio`](https://docs.python.org/3/library/asyncio.html) and other asynchronous
  libraries.

This chapter builds on the ideas of iterables and generators
([Iterators, Generators, and Classic Coroutines](iterators-generators.md), in particular
[Classic Coroutines](iterators-generators.md#classic-coroutines)), context managers
([Context Managers and `else` Blocks](context-managers.md)), and general concepts of
concurrent programming ([Concurrency Models in Python](concurrency-models.md)).

We'll study concurrent HTTP clients similar to the ones we saw in
[Concurrent Executors](executors.md), rewritten with native coroutines and asynchronous
context managers, using the same HTTPX library as before, but now through its asynchronous
API.  We'll also see how to avoid blocking the event loop by delegating slow operations to a
thread or process executor.

After the HTTP client examples, we'll see two simple asynchronous server-side applications,
one of them using the FastAPI framework.  Then we'll cover other language constructs
enabled by the `async`/`await` keywords: asynchronous generator functions, asynchronous
comprehensions and asynchronous generator expressions.  To emphasize the fact that those
language features are not tied to `asyncio`, we'll see one example rewritten to use Curio —
the elegant and innovative asynchronous framework invented by David Beazley — and then
`asyncio.TaskGroup`, which brought Curio's and Trio's ideas of structured concurrency to
the standard library.  To wrap up the chapter, there's a brief section on the advantages and
pitfalls of asynchronous programming.

That's a lot of ground to cover.  We only have space for basic examples, but they will
illustrate the most important features of each idea.

> **Tip**
>
> The `asyncio` documentation separates the few functions useful to application developers
> (the "high-level APIs") from the low-level API for creators of packages like web
> frameworks and database drivers.  Start with the high-level part.  For book-length
> coverage of `asyncio`, read *Using Asyncio in Python* by Caleb Hattingh (O'Reilly).

> **Note**
>
> Many examples in this chapter talk to DNS or HTTP servers on the network.  Those are
> shown as listings with sample output.  Wherever a concept can be demonstrated without a
> network, there is also a self-contained version that simulates network latency with
> `asyncio.sleep`, so you can run it as is.

## A Few Definitions

At the start of [Classic Coroutines](iterators-generators.md#classic-coroutines), we saw
that Python offers more than one kind of coroutine:

**Native coroutine**
: A coroutine function defined with `async def`.  You can delegate from a native coroutine
  to another native coroutine using the `await` keyword, similar to how classic coroutines
  use `yield from`.  The `async def` statement always defines a native coroutine, even if
  the `await` keyword is not used in its body.  The `await` keyword cannot be used outside
  of a native coroutine (with one exception: the asynchronous console, explained in
  [Experimenting with Python's async console](#experimenting-with-pythons-async-console)).

**Classic coroutine**
: A generator function that consumes data sent to it via `my_coro.send(data)` calls, and
  reads that data by using `yield` in an expression.  Classic coroutines can delegate to
  other classic coroutines using `yield from`.  Classic coroutines cannot be driven by
  `await`, and are no longer supported by `asyncio`.

**Generator-based coroutine**
: A generator function decorated with `@types.coroutine`.  That decorator makes the
  generator compatible with the `await` keyword.  It is not supported by `asyncio`, but is
  used in low-level code in the Curio and Trio asynchronous frameworks.  (The
  `@asyncio.coroutine` decorator was removed in Python 3.11.)

In this chapter, we focus on native coroutines as well as asynchronous generators:

**Asynchronous generator**
: A generator function defined with `async def` and using `yield` in its body.  It returns
  an asynchronous generator object that provides `__anext__`, a coroutine method to
  retrieve the next item.

## An `asyncio` Example: Probing Domains

Imagine you are about to start a new blog on Python, and you plan to register a domain
using a Python keyword and the `.DEV` suffix — for example: AWAIT.DEV.  Here is a script
using `asyncio` to check several domains concurrently.  This is the output it produces:

```console
$ python3 blogdom.py
  with.dev
+ elif.dev
+ def.dev
  from.dev
  else.dev
  or.dev
  if.dev
  del.dev
+ as.dev
  none.dev
  pass.dev
  true.dev
+ in.dev
+ for.dev
+ is.dev
+ and.dev
+ try.dev
+ not.dev
```

Note that the domains appear unordered.  If you run the script, you'll see them displayed
one after the other, with varying delays.  The `+` sign indicates your machine was able to
resolve the domain via DNS.  Otherwise, the domain did not resolve and may be available.

In `blogdom.py`, the DNS probing is done via native coroutine objects.  Because the
asynchronous operations are interleaved, the time needed to check the 18 domains is much
less than checking them sequentially.  In fact, the total time is practically the same as
the time for the single slowest DNS response, instead of the sum of the times of all
responses.  Here is the code:

<!-- nocheck -->
```python
#!/usr/bin/env python3
import asyncio
import socket
from keyword import kwlist

MAX_KEYWORD_LEN = 4  # shorter is better for domain names

async def probe(domain: str) -> tuple[str, bool]:  # returns the domain and whether it resolved
    loop = asyncio.get_running_loop()  # get a reference to the asyncio event loop
    try:
        await loop.getaddrinfo(domain, None)  # we don't need the result, only success/failure
    except socket.gaierror:
        return (domain, False)
    return (domain, True)

async def main() -> None:  # main must be a coroutine, so that we can use await in it
    names = (kw for kw in kwlist if len(kw) <= MAX_KEYWORD_LEN)
    domains = (f'{name}.dev'.lower() for name in names)
    coros = [probe(domain) for domain in domains]  # a list of coroutine objects
    for coro in asyncio.as_completed(coros):  # yields awaitables in the order they complete
        domain, found = await coro  # won't block: the coroutine is done
        mark = '+' if found else ' '
        print(f'{mark} {domain}')

if __name__ == '__main__':
    asyncio.run(main())  # start the event loop; return only when it exits
```

`probe` returns a tuple with the domain name and a boolean; `True` means the domain
resolved.  Returning the domain name will make it easier to display the results.  We get a
reference to the `asyncio` event loop, so we can use it next.  The `loop.getaddrinfo(...)`
coroutine method returns a five-part tuple of parameters to connect to the given address
using a socket.  In this example, we don't need the result.  If we got it, the domain
resolves; otherwise, it doesn't.

`main` must be a coroutine, so that we can use `await` in it.  It builds a list of coroutine
objects by invoking the `probe` coroutine with each `domain` argument.
`asyncio.as_completed` produces awaitables that return the results of the coroutines passed
to it in the order they are completed — not the order they were submitted.  It's similar to
`futures.as_completed`, which we saw in [Concurrent Executors](executors.md).  At that
point, we know the coroutine is done because that's how `as_completed` works.  Therefore,
the `await` expression will not block, but we need it to get the result from `coro`.  If
`coro` raised an unhandled exception, it would be re-raised here.

`asyncio.run` starts the event loop and returns only when the event loop exits.  This is a
common pattern for scripts that use `asyncio`: implement `main` as a coroutine, and drive it
with `asyncio.run` inside the `if __name__ == '__main__':` block.

> **Tip**
>
> Use `asyncio.get_running_loop()` inside coroutines, as shown in `probe`.  If there's no
> running loop, it raises `RuntimeError`.  The older `asyncio.get_event_loop()` used to
> create a loop if necessary; that behavior was deprecated, and since Python 3.14 it raises
> `RuntimeError` when there is no current event loop.

Here is a version of the same idea that runs without a network: `probe` pretends to take a
different amount of time for each domain.

```python
import asyncio

DELAYS = {'if.dev': .3, 'or.dev': .1, 'in.dev': .2, 'def.dev': .05}

async def probe(domain: str) -> tuple[str, bool]:
    await asyncio.sleep(DELAYS[domain])  # stands in for a DNS query
    return (domain, domain != 'or.dev')

async def main() -> None:
    coros = [probe(domain) for domain in DELAYS]
    for coro in asyncio.as_completed(coros):
        domain, found = await coro
        mark = '+' if found else ' '
        print(f'{mark} {domain}')

asyncio.run(main())
# + def.dev
#   or.dev
# + in.dev
# + if.dev
```

### Guido's Trick to Read Asynchronous Code

There are a lot of new concepts to grasp in `asyncio`, but the overall logic of
`blogdom.py` is easy to follow if you employ a trick suggested by Guido van Rossum himself:
squint and pretend the `async` and `await` keywords are not there.  If you do that, you'll
realize that coroutines read like plain old sequential functions.

For example, imagine that the body of this coroutine:

<!-- nocheck -->
```python
async def probe(domain: str) -> tuple[str, bool]:
    loop = asyncio.get_running_loop()
    try:
        await loop.getaddrinfo(domain, None)
    except socket.gaierror:
        return (domain, False)
    return (domain, True)
```

works like the following function, except that it magically never blocks:

<!-- nocheck -->
```python
def probe(domain: str) -> tuple[str, bool]:  # no async
    loop = asyncio.get_running_loop()
    try:
        loop.getaddrinfo(domain, None)  # no await
    except socket.gaierror:
        return (domain, False)
    return (domain, True)
```

Using the syntax `await loop.getaddrinfo(...)` avoids blocking because `await` suspends the
current coroutine object.  For example, during the execution of the `probe('if.dev')`
coroutine, a new coroutine object is created by `getaddrinfo('if.dev', None)`.  Awaiting it
starts the low-level `addrinfo` query and yields control back to the event loop, not to the
`probe('if.dev')` coroutine, which is suspended.  The event loop can then drive other
pending coroutine objects, such as `probe('or.dev')`.

When the event loop gets a response for the `getaddrinfo('if.dev', None)` query, that
specific coroutine object resumes and returns control back to the `probe('if.dev')` — which
was suspended at `await` — and can now handle a possible exception and return the result
tuple.

So far, we've only seen `asyncio.as_completed` and `await` applied to coroutines.  But they
handle any *awaitable* object.  That concept is explained next.

## New Concept: Awaitable

The `for` keyword works with iterables.  The `await` keyword works with awaitables.  As an
end user of `asyncio`, these are the awaitables you will see on a daily basis:

* a native coroutine object, which you get by calling a native coroutine function;
* an `asyncio.Task`, which you usually get by passing a coroutine object to
  `asyncio.create_task()`.

However, end-user code does not always need to `await` on a `Task`.  We use
`asyncio.create_task(one_coro())` to schedule `one_coro` for concurrent execution, without
waiting for its return.  That's what we did with the `spinner` coroutine in
[Spinner with Coroutines](concurrency-models.md#spinner-with-coroutines).

> **Warning**
>
> The event loop keeps only a *weak* reference to tasks.  A task that nobody references may
> be garbage collected before it's done.  If you create "fire-and-forget" tasks, keep a
> reference to them — for example, in a set, removing each task when it finishes with
> `task.add_done_callback(tasks.discard)` — or, better, use a `TaskGroup`, as shown in
> [Structured Concurrency with `TaskGroup`](#structured-concurrency-with-taskgroup).

In contrast, we use `await other_coro()` to run `other_coro` right now and wait for its
completion because we need its result before we can proceed.  In the spinner example, the
`supervisor` coroutine did `res = await slow()` to execute `slow` and get its result.

When implementing asynchronous libraries or contributing to `asyncio` itself, you may also
deal with these lower-level awaitables:

* an object with an `__await__` method that returns an iterator; for example, an
  `asyncio.Future` instance (`asyncio.Task` is a subclass of `asyncio.Future`);
* objects written in other languages using the Python/C API with a
  `tp_as_async.am_await` function, returning an iterator (similar to `__await__`).

> **Note**
>
> [**PEP 492**](https://peps.python.org/pep-0492/) states that the `await` expression "uses
> the `yield from` implementation with an extra step of validating its argument" and
> "`await` only accepts an awaitable".

Here is a minimal awaitable class, just to show the protocol at work (never write one of
these in application code):

```python
import asyncio

class Ready:
    def __init__(self, value):
        self.value = value

    def __await__(self):  # must return an iterator
        yield from asyncio.sleep(0).__await__()  # give the event loop a chance to run
        return self.value

async def main():
    return await Ready(42)

asyncio.run(main())
# 42
```

Now let's study the `asyncio` version of a script that downloads a fixed set of flag images.

## Downloading with `asyncio` and HTTPX

The `flags_asyncio.py` script downloads a fixed set of 20 flags from fluentpython.com.  We
first mentioned it in [Concurrent Web Downloads](executors.md#concurrent-web-downloads), but
now we'll study it in detail, applying the concepts we just saw.  `asyncio` supports TCP and
UDP directly, but there are no asynchronous HTTP client or server packages in the standard
library, so we use HTTPX in all the HTTP client examples.

We'll explore `flags_asyncio.py` from the bottom up — that is, looking first at the
functions that set up the action.  To make the code easier to read, `flags_asyncio.py` has no
error handling.  As we introduce `async`/`await`, it's useful to focus on the "happy path"
initially, to understand how regular functions and coroutines are arranged in a program.

<!-- nocheck -->
```python
def download_many(cc_list: list[str]) -> int:  # a plain function, to be passed to main
    return asyncio.run(supervisor(cc_list))  # run the event loop until supervisor returns

async def supervisor(cc_list: list[str]) -> int:
    async with AsyncClient() as client:  # an asynchronous context manager
        to_do = [download_one(client, cc)
                 for cc in sorted(cc_list)]  # a list of coroutine objects
        res = await asyncio.gather(*to_do)  # wait for all of them; results in submission order

    return len(res)

if __name__ == '__main__':
    main(download_many)
```

`download_many` needs to be a plain function — not a coroutine — so it can be passed to and
called by the `main` function from the `flags.py` module.  It executes the event loop driving
the `supervisor(cc_list)` coroutine object until it returns.  This will block while the event
loop runs.  The result of this line is whatever `supervisor` returns.

Asynchronous HTTP client operations in `httpx` are methods of `AsyncClient`, which is also an
asynchronous context manager: a context manager with asynchronous setup and teardown methods
(more about this in [Asynchronous Context Managers](#asynchronous-context-managers)).  We build
a list of coroutine objects by calling the `download_one` coroutine once for each flag to be
retrieved, then wait for the `asyncio.gather` coroutine, which accepts one or more awaitable
arguments and waits for all of them to complete, returning a list of results for the given
awaitables in the order they were submitted.  `supervisor` returns the length of the list
returned by `asyncio.gather`.

Now let's review the top of `flags_asyncio.py`, with the coroutines in the order they are
started by the event loop:

<!-- nocheck -->
```python
import asyncio

from httpx import AsyncClient  # httpx must be installed: it's not in the standard library

from flags import BASE_URL, save_flag, main  # reuse code from flags.py

async def download_one(client: AsyncClient, cc: str):  # must be a coroutine to await get_flag
    image = await get_flag(client, cc)
    save_flag(image, f'{cc}.gif')
    print(cc, end=' ', flush=True)
    return cc

async def get_flag(client: AsyncClient, cc: str) -> bytes:  # needs the AsyncClient
    url = f'{BASE_URL}/{cc}/{cc}.gif'.lower()
    resp = await client.get(url, timeout=6.1,
                                  follow_redirects=True)  # network I/O is a coroutine method
    return resp.read()
```

`download_one` must be a native coroutine, so it can `await` on `get_flag` — which does the
HTTP request.  Then it displays the code of the downloaded flag, and saves the image.
`get_flag` needs to receive the `AsyncClient` to make the request.  The `get` method of an
`httpx.AsyncClient` instance is a coroutine, so network I/O operations are driven
asynchronously by the `asyncio` event loop.

> **Note**
>
> For better performance, the `save_flag` call inside `download_one` should be asynchronous,
> to avoid blocking the event loop.  However, `asyncio` does not provide an asynchronous
> filesystem API — as Node.js does.  [Using `asyncio.as_completed` and a Thread](#using-asyncioas_completed-and-a-thread)
> will show how to delegate `save_flag` to a thread.

Your code delegates to the `httpx` coroutines explicitly through `await` or implicitly through
the special methods of the asynchronous context managers, such as `AsyncClient`.

### The Secret of Native Coroutines: Humble Generators

A key difference between the classic coroutine examples we saw in
[Classic Coroutines](iterators-generators.md#classic-coroutines) and `flags_asyncio.py` is
that there are no visible `.send()` calls or `yield` expressions in the latter.  Your code
sits between the `asyncio` library and the asynchronous libraries you are using, such as
HTTPX: a user's function starts the event loop, scheduling an initial coroutine with
`asyncio.run`.  Each user's coroutine drives the next with an `await` expression, forming a
channel that enables communication between a library like HTTPX and the event loop.

Under the hood, the `asyncio` event loop makes the `.send` calls that drive your coroutines,
and your coroutines `await` on other coroutines, including library coroutines.  As
mentioned, `await` borrows most of its implementation from `yield from`, which also makes
`.send` calls to drive coroutines.

The `await` chain eventually reaches a low-level awaitable, which returns a generator that
the event loop can drive in response to events such as timers or network I/O.  The low-level
awaitables and generators at the end of these `await` chains are implemented deep into the
libraries, are not part of their APIs, and may be Python/C extensions.

Using functions like `asyncio.gather` and `asyncio.create_task`, you can start multiple
concurrent `await` channels, enabling concurrent execution of multiple I/O operations driven
by a single event loop, in a single thread.

You can see the generator machinery by driving a coroutine by hand, as the event loop does:

```python
import types

@types.coroutine
def suspend():  # a generator-based coroutine: the bottom of an await chain
    received = yield 'suspended'  # this value goes all the way up to whoever calls send()
    return received

async def middle():
    return await suspend()

async def top():
    return await middle()

coro = top()
coro.send(None)  # start it: runs until the yield deep in suspend()
# 'suspended'
try:
    coro.send('data from the "event loop"')  # resume; the value travels down the chain
except StopIteration as exc:  # the coroutine returned: the value is wrapped in StopIteration
    print(exc.value)

# data from the "event loop"
```

### The All-or-Nothing Problem

Note that `flags_asyncio.py` could not reuse the `get_flag` function from `flags.py`.  It had
to be rewritten as a coroutine to use the asynchronous API of HTTPX.  For peak performance
with `asyncio`, we must replace every function that does I/O with an asynchronous version
that is activated with `await` or `asyncio.create_task`, so that control is given back to
the event loop while the function waits for I/O.  If you can't rewrite a blocking function
as a coroutine, you should run it in a separate thread or process, as we'll see in
[Delegating Tasks to Executors](#delegating-tasks-to-executors).

That's why the epigraph for this chapter includes this advice: "You rewrite all your code so
none of it blocks or you're just wasting your time."

For the same reason, `flags_asyncio.py` could not reuse the `download_one` function from
`flags_threadpool.py` either.  It drives `get_flag` with `await`, so `download_one` must also
be a coroutine.  For each request, a `download_one` coroutine object is created in
`supervisor`, and they are all driven by the `asyncio.gather` coroutine.

Now let's study the `async with` statement that appeared in `supervisor`.

## Asynchronous Context Managers

In [Context Managers and `with` Blocks](context-managers.md#context-managers-and-with-blocks),
we saw how an object can be used to run code before and after the body of a `with` block, if
its class provides the `__enter__` and `__exit__` methods.  Now, consider this example, from
the documentation of the asyncpg asyncio-compatible PostgreSQL driver:

<!-- nocheck -->
```python
tr = connection.transaction()
await tr.start()
try:
    await connection.execute("INSERT INTO mytable VALUES (1, 2, 3)")
except:
    await tr.rollback()
    raise
else:
    await tr.commit()
```

A database transaction is a natural fit for the context manager protocol: the transaction has
to be started, data is changed with `connection.execute`, and then a rollback or commit must
happen, depending on the outcome of the changes.

In an asynchronous driver like asyncpg, the setup and wrap-up need to be coroutines so that
other operations can happen concurrently.  However, the implementation of the classic `with`
statement doesn't support coroutines doing the work of `__enter__` or `__exit__`.  That's why
PEP 492 introduced the `async with` statement, which works with *asynchronous context
managers*: objects implementing the `__aenter__` and `__aexit__` methods as coroutines.
With `async with`, that example can be written like this other snippet from the asyncpg
documentation:

<!-- nocheck -->
```python
async with connection.transaction():
    await connection.execute("INSERT INTO mytable VALUES (1, 2, 3)")
```

In the `asyncpg.Transaction` class, the `__aenter__` coroutine method does
`await self.start()`, and the `__aexit__` coroutine awaits on private `__rollback` or
`__commit` coroutine methods, depending on whether an exception occurred or not.  Using
coroutines to implement `Transaction` as an asynchronous context manager allows asyncpg to
handle many transactions concurrently.

Here is a toy asynchronous context manager, to see the protocol at work:

```python
import asyncio

class Connection:
    async def __aenter__(self):
        await asyncio.sleep(.01)  # pretend to connect over the network
        print('connected')
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await asyncio.sleep(.01)  # pretend to say goodbye politely
        print('disconnected')

async def main():
    async with Connection() as conn:
        print('using', type(conn).__name__)

asyncio.run(main())
# connected
# using Connection
# disconnected
```

Back to `flags_asyncio.py`, the `AsyncClient` class of `httpx` is an asynchronous context
manager, so it can use awaitables in its `__aenter__` and `__aexit__` special coroutine
methods.

> **Tip**
>
> [Asynchronous generators as context managers](#asynchronous-generators-as-context-managers)
> shows how to use Python's `contextlib` to create an asynchronous context manager without
> having to write a class.  That explanation comes later in this chapter because of a
> prerequisite topic: [Asynchronous Generator Functions](#asynchronous-generator-functions).

We'll now enhance the `asyncio` flag download example with a progress bar, which will lead
us to explore a bit more of the `asyncio` API.

## Enhancing the asyncio Downloader

Recall from [Downloads with Progress Display and Error Handling](executors.md#downloads-with-progress-display-and-error-handling)
that the `flags2` set of examples share the same command-line interface, and they display a
progress bar while the downloads are happening.  They also include error handling.  For
instance, here is an attempt to get 100 flags (`-al 100`) from the `ERROR` server, using 100
concurrent requests (`-m 100`).  The 48 errors in the result are either HTTP 418 or time-out
errors — the expected (mis)behavior of the test server:

```console
$ python3 flags2_asyncio.py -s ERROR -al 100 -m 100
ERROR site: http://localhost:8002/flags
Searching for 100 flags: from AD to LK
100 concurrent connections will be used.
100%|█████████████████████████████████████████| 100/100 [00:03<00:00, 30.48it/s]
--------------------
 52 flags downloaded.
 48 errors.
Elapsed time: 3.31s
```

> **Warning**
>
> Even if the overall download time is not much different between the threaded and
> `asyncio` HTTP clients, `asyncio` can send requests faster, so it's more likely that the
> server will suspect a DoS attack.  To really exercise these concurrent clients at full
> throttle, please use local HTTP servers for testing, as explained in
> [Setting Up Test Servers](executors.md#setting-up-test-servers).

Now let's see how `flags2_asyncio.py` is implemented.

### Using `asyncio.as_completed` and a Thread

In `flags_asyncio.py`, we passed several coroutines to `asyncio.gather`, which returns a list
with results of the coroutines in the order they were submitted.  This means that
`asyncio.gather` can only return when all the awaitables are done.  However, to update a
progress bar, we need to get results as they are done.  Fortunately, there is an `asyncio`
equivalent of the `as_completed` generator function we used in the thread pool example with
the progress bar.  Here is the top of the `flags2_asyncio.py` script, where the `get_flag`
and `download_one` coroutines are defined:

<!-- nocheck -->
```python
import asyncio
from collections import Counter
from http import HTTPStatus
from pathlib import Path

import httpx
import tqdm  # type: ignore

from flags2_common import main, DownloadStatus, save_flag

# low concurrency default to avoid errors from remote site,
# such as 503 - Service Temporarily Unavailable
DEFAULT_CONCUR_REQ = 5
MAX_CONCUR_REQ = 1000

async def get_flag(client: httpx.AsyncClient,  # requires the client parameter
                   base_url: str,
                   cc: str) -> bytes:
    url = f'{base_url}/{cc}/{cc}.gif'.lower()
    resp = await client.get(url, timeout=3.1, follow_redirects=True)  # a coroutine: await it
    resp.raise_for_status()
    return resp.content

async def download_one(client: httpx.AsyncClient,
                       cc: str,
                       base_url: str,
                       semaphore: asyncio.Semaphore,
                       verbose: bool) -> DownloadStatus:
    try:
        async with semaphore:  # only this coroutine is suspended if the counter is zero
            image = await get_flag(client, base_url, cc)
    except httpx.HTTPStatusError as exc:  # same error handling logic as before
        res = exc.response
        if res.status_code == HTTPStatus.NOT_FOUND:
            status = DownloadStatus.NOT_FOUND
            msg = f'not found: {res.url}'
        else:
            raise
    else:
        await asyncio.to_thread(save_flag, image, f'{cc}.gif')  # file I/O in a thread
        status = DownloadStatus.OK
        msg = 'OK'
    if verbose and msg:
        print(cc, msg)
    return status
```

`get_flag` is very similar to the sequential version, but it requires the `client`
parameter, and `.get` is an `AsyncClient` method that is a coroutine, so we need to `await`
it.  In `download_one`, we use the semaphore as an asynchronous context manager so that the
program as a whole is not blocked; only this coroutine is suspended when the semaphore
counter is zero.  More about this in [Python's Semaphores](#pythons-semaphores).  The error
handling logic is the same as in the sequential `download_one`.

Saving the image is an I/O operation.  To avoid blocking the event loop, we run `save_flag`
in a thread.  All network I/O is done with coroutines in `asyncio`, but not file I/O.
However, file I/O is also "blocking" — in the sense that reading/writing files takes
thousands of times longer than reading/writing to RAM.  If you're using Network-Attached
Storage, it may even involve network I/O under the covers.  The
[`asyncio.to_thread`](https://docs.python.org/3/library/asyncio-task.html#asyncio.to_thread)
coroutine makes it easy to delegate file I/O to a thread pool provided by `asyncio`.

```python
import asyncio
import threading
import time

def blocking_io(label):  # a plain function that blocks, like reading a big file
    time.sleep(.1)
    return f'{label} done in {threading.current_thread().name.split("_")[0]}'

async def main():
    results = await asyncio.gather(  # both run concurrently in worker threads
        asyncio.to_thread(blocking_io, 'A'),
        asyncio.to_thread(blocking_io, 'B'),
    )
    print(results)

asyncio.run(main())
# ['A done in asyncio', 'B done in asyncio']
```

But first, let's finish our study of the HTTP client code.

### Throttling Requests with a Semaphore

Network clients like the ones we are studying should be *throttled* (i.e., limited) to avoid
pounding the server with too many concurrent requests.  A *semaphore* is a synchronization
primitive, more flexible than a lock.  A semaphore can be held by multiple coroutines, with a
configurable maximum number.  This makes it ideal to throttle the number of active
concurrent coroutines.

In `flags2_threadpool.py`, the throttling was done by instantiating the `ThreadPoolExecutor`
with the required `max_workers` argument set to `concur_req` in the `download_many` function.
In `flags2_asyncio.py`, an `asyncio.Semaphore` is created by the `supervisor` function and
passed as the `semaphore` argument to `download_one`.

#### Python's Semaphores

Computer scientist Edsger W. Dijkstra invented the semaphore in the early 1960s.  It's a
simple idea, but it's so flexible that most other synchronization objects — such as locks
and barriers — can be built on top of semaphores.  There are three `Semaphore` classes in
Python's standard library: one in `threading`, another in `multiprocessing`, and a third one
in `asyncio`.  Here we'll describe the latter.

An `asyncio.Semaphore` has an internal counter that is decremented whenever we `await` on the
`.acquire()` coroutine method, and incremented when we call the `.release()` method — which
is not a coroutine because it never blocks.  The initial value of the counter is set when the
`Semaphore` is instantiated:

<!-- nocheck -->
```python
semaphore = asyncio.Semaphore(concur_req)
```

Awaiting on `.acquire()` causes no delay when the counter is greater than zero, but if the
counter is zero, `.acquire()` suspends the awaiting coroutine until some other coroutine
calls `.release()` on the same `Semaphore`, thus incrementing the counter.  Instead of using
those methods directly, it's safer to use the semaphore as an asynchronous context manager,
as in `download_one`:

<!-- nocheck -->
```python
async with semaphore:
    image = await get_flag(client, base_url, cc)
```

The `Semaphore.__aenter__` coroutine method awaits for `.acquire()`, and its `__aexit__`
coroutine method calls `.release()`.  That snippet guarantees that no more than `concur_req`
instances of `get_flag` coroutines will be active at any time.  Here is the effect, measured:

```python
import asyncio

async def worker(n, semaphore, active, peak):
    async with semaphore:
        active.append(n)
        peak[0] = max(peak[0], len(active))
        await asyncio.sleep(.01)  # pretend to make a request
        active.remove(n)

async def main():
    semaphore = asyncio.Semaphore(3)
    active, peak = [], [0]
    await asyncio.gather(*(worker(n, semaphore, active, peak) for n in range(10)))
    return peak[0]

asyncio.run(main())  # never more than 3 workers inside the async with block
# 3
```

Each of the `Semaphore` classes in the standard library has a `BoundedSemaphore` subclass
that enforces an additional constraint: the internal counter can never become larger than
the initial value when there are more `.release()` than `.acquire()` operations.

Now let's take a look at the rest of the script:

<!-- nocheck -->
```python
async def supervisor(cc_list: list[str],
                     base_url: str,
                     verbose: bool,
                     concur_req: int) -> Counter[DownloadStatus]:  # same arguments as download_many
    counter: Counter[DownloadStatus] = Counter()
    semaphore = asyncio.Semaphore(concur_req)  # no more than concur_req active coroutines
    async with httpx.AsyncClient() as client:
        to_do = [download_one(client, cc, base_url, semaphore, verbose)
                 for cc in sorted(cc_list)]  # one coroutine object per download
        to_do_iter = asyncio.as_completed(to_do)  # coroutines come out as they're done
        if not verbose:
            to_do_iter = tqdm.tqdm(to_do_iter, total=len(cc_list))  # wrap to show progress
        error: httpx.HTTPError | None = None  # holds an exception beyond the try/except
        for coro in to_do_iter:  # similar to the loop in flags2_threadpool.py
            try:
                status = await coro  # will not block: as_completed only produces done ones
            except httpx.HTTPStatusError as exc:
                error_msg = 'HTTP error {resp.status_code} - {resp.reason_phrase}'
                error_msg = error_msg.format(resp=exc.response)
                error = exc  # exc is unbound after the except clause, so keep it
            except httpx.RequestError as exc:
                error_msg = f'{exc} {type(exc)}'.strip()
                error = exc
            except KeyboardInterrupt:
                break

            if error:
                status = DownloadStatus.ERROR  # if there was an error, set the status
                if verbose:
                    url = str(error.request.url)  # extract the URL from the exception...
                    cc = Path(url).stem.upper()  # ...and the country code from the URL
                    print(f'{cc} error: {error_msg}')
            counter[status] += 1

    return counter

def download_many(cc_list: list[str],
                  base_url: str,
                  verbose: bool,
                  concur_req: int) -> Counter[DownloadStatus]:
    coro = supervisor(cc_list, base_url, verbose, concur_req)
    counts = asyncio.run(coro)  # drive supervisor and collect its result

    return counts

if __name__ == '__main__':
    main(download_many, DEFAULT_CONCUR_REQ, MAX_CONCUR_REQ)
```

`supervisor` takes the same arguments as the `download_many` function, but it cannot be
invoked directly from `main` because it's a coroutine and not a plain function like
`download_many`.  The value of `concur_req` is computed by the `main` function from
`flags2_common.py`, based on command-line options and constants set in each example.  The
call to `as_completed` is not placed directly in the `for` loop because it may need to be
wrapped with the `tqdm` iterator for the progress bar, depending on the user's choice for
verbosity.

We declare and initialize `error` with `None`; this variable will be used to hold an
exception beyond the `try`/`except` statement, if one is raised.  That assignment is
necessary because the `exc` variable scope is limited to its `except` clause.

In that code, we could not use the mapping of futures to country codes we saw in
`flags2_threadpool.py`, because the awaitables produced by iterating over
`asyncio.as_completed` with a plain `for` loop are not the same objects we pass into the
`as_completed` call.  That's why the country code is extracted from the exception, kept in
the `error` variable to retrieve outside of the `try`/`except` statement.

> **Tip**
>
> Since Python 3.13, `asyncio.as_completed` is also an *asynchronous* iterator, and
> iterating over it with `async for` yields the original tasks or futures you passed in.
> So if you wrap your coroutines in tasks first, you can use the same idiom as with
> `concurrent.futures`: a `dict` mapping each task to extra data.
>
> ```python
> to_do_map = {asyncio.create_task(download_one(...)): cc for cc in cc_list}
> async for task in asyncio.as_completed(to_do_map):
>     cc = to_do_map[task]
>     ...
> ```

> **Note**
>
> Python is not a block-scoped language: statements such as loops and `try`/`except` don't
> create a local scope in the blocks they manage.  But if an `except` clause binds an
> exception to a variable, like the `exc` variables we just saw, that binding only exists
> within the block inside that particular `except` clause — the name is deleted when the
> clause ends.

This wraps up the discussion of an `asyncio` example functionally equivalent to the
`flags2_threadpool.py` we saw earlier.

The next example demonstrates the simple pattern of executing one asynchronous task after
another using coroutines.  This deserves our attention because anyone with previous
experience with JavaScript knows that running one asynchronous function after the other was
the reason for the nested coding pattern known as *pyramid of doom*.  The `await` keyword
makes that curse go away.

### Making Multiple Requests for Each Download

Suppose you want to save each country flag with the name of the country and the country
code, instead of just the country code.  Now you need to make two HTTP requests per flag:
one to get the flag image itself, the other to get the `metadata.json` file in the same
directory as the image — that's where the name of the country is recorded.

Coordinating multiple requests in the same task is easy in the threaded script: just make
one request then the other, blocking the thread twice, and keeping both pieces of data
(country code and name) in local variables, ready to use when saving the files.  If you
needed to do the same in an asynchronous script with callbacks, you needed nested functions
so that the country code and name were available in their closures until you could save the
file, because each callback runs in a different local scope.  The `await` keyword provides
relief from that, allowing you to drive the asynchronous requests one after the other,
sharing the local scope of the driving coroutine.

> **Tip**
>
> If you are doing asynchronous application programming in modern Python with lots of
> callbacks, you are probably applying old patterns that don't make sense in modern Python.
> That is justified if you are writing a library that interfaces with legacy or low-level
> code that does not support coroutines.

The third variation of the `asyncio` flag downloading script adds a `get_country`
coroutine, which fetches the `metadata.json` file for the country code and gets the name of
the country from it, and changes `download_one` to use `await` to delegate to `get_flag` and
the new `get_country` coroutine:

<!-- nocheck -->
```python
async def get_country(client: httpx.AsyncClient,
                      base_url: str,
                      cc: str) -> str:  # returns the country name, if all goes well
    url = f'{base_url}/{cc}/metadata.json'.lower()
    resp = await client.get(url, timeout=3.1, follow_redirects=True)
    resp.raise_for_status()
    metadata = resp.json()  # a Python dict built from the JSON contents of the response
    return metadata['country']

async def download_one(client: httpx.AsyncClient,
                       cc: str,
                       base_url: str,
                       semaphore: asyncio.Semaphore,
                       verbose: bool) -> DownloadStatus:
    try:
        async with semaphore:  # hold the semaphore to await for get_flag...
            image = await get_flag(client, base_url, cc)
        async with semaphore:  # ...and again for get_country
            country = await get_country(client, base_url, cc)
    except httpx.HTTPStatusError as exc:
        res = exc.response
        if res.status_code == HTTPStatus.NOT_FOUND:
            status = DownloadStatus.NOT_FOUND
            msg = f'not found: {res.url}'
        else:
            raise
    else:
        filename = country.replace(' ', '_')  # no spaces in filenames
        await asyncio.to_thread(save_flag, image, f'{filename}.gif')
        status = DownloadStatus.OK
        msg = 'OK'
    if verbose and msg:
        print(cc, msg)
    return status
```

Much better than nested callbacks!  The calls to `get_flag` and `get_country` are in separate
`with` blocks controlled by the semaphore because it's good practice to hold semaphores and
locks for the shortest possible time.

We could schedule both `get_flag` and `get_country` in parallel using `asyncio.gather`, but
if `get_flag` raises an exception, there is no image to save, so it's pointless to run
`get_country`.  But there are cases where it makes sense to use `asyncio.gather` to hit
several APIs at the same time instead of waiting for one response before making the next
request.

One challenge is to know when you have to use `await` and when you can't use it.  The answer
in principle is easy: you `await` coroutines and other awaitables, such as `asyncio.Task`
instances.  But some APIs are tricky, mixing coroutines and plain functions in seemingly
arbitrary ways, like the `StreamWriter` class we'll use in
[An `asyncio` TCP Server](#an-asyncio-tcp-server).

## Delegating Tasks to Executors

One important advantage of Node.js over Python for asynchronous programming is the Node.js
standard library, which provides async APIs for all I/O — not just for network I/O.  In
Python, if you're not careful, file I/O can seriously degrade the performance of asynchronous
applications, because reading and writing to storage in the main thread blocks the event
loop.  In the `download_one` coroutine, we used this line to save the downloaded image to
disk:

<!-- nocheck -->
```python
await asyncio.to_thread(save_flag, image, f'{cc}.gif')
```

`asyncio.to_thread` is a convenience built on a lower-level method of the event loop,
`run_in_executor`, which is what you'd use in older code:

<!-- nocheck -->
```python
loop = asyncio.get_running_loop()  # get a reference to the event loop
await loop.run_in_executor(None, save_flag,  # None selects the default ThreadPoolExecutor
                           image, f'{cc}.gif')
```

The first argument is the executor to use; passing `None` selects the default
`ThreadPoolExecutor` that is always available in the `asyncio` event loop.  You can pass
positional arguments to the function to run, but if you need to pass keyword arguments, then
you need to resort to `functools.partial`, as described in the `run_in_executor`
documentation.  The newer `asyncio.to_thread` function is easier to use and more flexible, as
it also accepts keyword arguments.

The implementation of `asyncio` itself uses `run_in_executor` under the hood in a few places.
For example, the `loop.getaddrinfo(...)` coroutine we saw in `blogdom.py` is implemented by
calling the `getaddrinfo` function from the `socket` module — which is a blocking function
that may take seconds to return, as it depends on DNS resolution.

A common pattern in asynchronous APIs is to wrap blocking calls that are implementation
details in coroutines using `run_in_executor` internally.  That way, you provide a
consistent interface of coroutines to be driven with `await`, and hide the threads you need
to use for pragmatic reasons.  The Motor asynchronous driver for MongoDB, for example, has an
API compatible with `async`/`await` that was really a façade around a threaded core that talks
to the database server: its lead developer found that a thread pool was more performant in
the particular use case of a database driver — despite the myth that asynchronous approaches
are always faster than threads for network I/O.

The main reason to pass an explicit `Executor` to `loop.run_in_executor` is to employ a
`ProcessPoolExecutor` if the function to execute is CPU intensive, so that it runs in a
different Python process, avoiding contention for the GIL.  Because of the high start-up
cost, it would be better to start the `ProcessPoolExecutor` in the `supervisor`, and pass it
to the coroutines that need to use it.

> **Warning**
>
> Caleb Hattingh, the author of *Using Asyncio in Python*, warns: "Using `run_in_executor`
> can produce hard-to-debug problems since cancellation doesn't work the way one might
> expect.  Coroutines that use executors give merely the pretense of cancellation: the
> underlying thread (if it's a `ThreadPoolExecutor`) has no cancellation mechanism.  For
> example, a long-lived thread that is created inside a `run_in_executor` call may prevent
> your asyncio program from shutting down cleanly: `asyncio.run` will wait for the executor
> to fully shut down before returning, and it will wait forever if the executor jobs don't
> stop somehow on their own.  My greybeard inclination is to want that function to be named
> `run_in_executor_uncancellable`."  The same applies to `asyncio.to_thread`.

We'll now go from client scripts to writing servers with `asyncio`.

## Writing asyncio Servers

The classic toy example of a TCP server is an echo server.  We'll build slightly more
interesting toys: server-side Unicode character search utilities, first using HTTP with
FastAPI, then using plain TCP with `asyncio` only.  These servers let users query for Unicode
characters based on words in their standard names from the `unicodedata` module we discussed
in [The Unicode Database](unicode.md#the-unicode-database).

The Unicode search logic in these examples is in the `InvertedIndex` class in the
`charindex.py` module of the *Fluent Python* code repository.  There's nothing concurrent in
that small module, so here is just a brief overview.

#### Meet the inverted index

An *inverted index* usually maps words to documents in which they occur.  In the mojifinder
examples, each "document" is one Unicode character.  The `charindex.InvertedIndex` class
indexes each word that appears in each character name in the Unicode database, and creates an
inverted index stored in a `defaultdict`.  For example, to index character U+0037 — DIGIT
SEVEN — the `InvertedIndex` initializer appends the character `'7'` to the entries under the
keys `'DIGIT'` and `'SEVEN'`.  The `InvertedIndex.search` method breaks the query into words,
and returns the intersection of the entries for each word.  That's the beautiful idea behind
an inverted index: a fundamental building block in information retrieval — the theory behind
search engines.  Here is a tiny version:

```python
import sys
import unicodedata
from collections import defaultdict

class InvertedIndex:
    def __init__(self, start=32, stop=sys.maxunicode + 1):
        self.entries = defaultdict(set)
        for char in (chr(i) for i in range(start, stop)):
            name = unicodedata.name(char, '')
            for word in name.split():
                self.entries[word].add(char)

    def search(self, query):
        words = query.upper().split()
        if not words:
            return set()
        return set.intersection(*(self.entries.get(w, set()) for w in words))

index = InvertedIndex(0x1F600, 0x1F650)  # just the emoticons block, to keep it fast
sorted(index.search('cat face'))
# ['😸', '😹', '😺', '😻', '😼', '😽', '😾', '😿', '🙀']
```

### A FastAPI Web Service

The next example — `web_mojifinder.py` — uses [FastAPI](https://fastapi.tiangolo.com/): one
of the Python ASGI web frameworks mentioned in
[WSGI Application Servers](concurrency-models.md#wsgi-application-servers).  Its frontend is a
super simple SPA (Single Page Application): after the initial HTML download, the UI is updated
by client-side JavaScript communicating with the server.

FastAPI is designed to implement backends for SPA and mobile apps, which mostly consist of web
API end points returning JSON responses instead of server-rendered HTML.  FastAPI leverages
decorators, type hints and code introspection to eliminate a lot of the boilerplate code for
web APIs, and also automatically publishes interactive OpenAPI — a.k.a. Swagger —
documentation for the APIs we create.

To run `web_mojifinder.py`, you need to install two packages and their dependencies: FastAPI
and uvicorn (or another ASGI server, such as Hypercorn).  This is the command to run it with
uvicorn in development mode:

```console
$ uvicorn web_mojifinder:app --reload
```

The parameters are `web_mojifinder:app` — the package name, a colon, and the name of the ASGI
application defined in it (`app` is the conventional name) — and `--reload`, which makes
uvicorn monitor changes to application source files and automatically reload them.  Here is
the source code:

<!-- nocheck -->
```python
from pathlib import Path
from unicodedata import name

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from charindex import InvertedIndex

STATIC_PATH = Path(__file__).parent.absolute() / 'static'  # pathlib's overloaded / operator

app = FastAPI(  # defines the ASGI app; the parameters are metadata for the docs
    title='Mojifinder Web',
    description='Search for Unicode characters by name.',
)

class CharName(BaseModel):  # a pydantic schema for a JSON response with char and name fields
    char: str
    name: str

def init(app):  # build the index and load the static HTML form, attaching both to app.state
    app.state.index = InvertedIndex()
    app.state.form = (STATIC_PATH / 'form.html').read_text()

init(app)  # run init when this module is loaded by the ASGI server

@app.get('/search', response_model=list[CharName])  # describes the response format
async def search(q: str):  # parameters not in the route path come from the query string
    chars = sorted(app.state.index.search(q))
    return ({'char': c, 'name': name(c)} for c in chars)  # dicts compatible with the model

@app.get('/', response_class=HTMLResponse, include_in_schema=False)
def form():  # regular functions can also produce responses
    return app.state.form

# no main function: the module is loaded and driven by the ASGI server
```

FastAPI assumes that any parameters that appear in the function or coroutine signature that
are not in the route path will be passed in the HTTP query string, e.g., `/search?q=cat`.
Since `q` has no default, FastAPI will return a 422 (Unprocessable Entity) status if `q` is
missing from the query string.  Returning an iterable of dicts compatible with the
`response_model` schema allows FastAPI to build the JSON response according to the
`response_model` in the `@app.get` decorator.

This module has no direct calls to `asyncio`.  FastAPI is built on the Starlette ASGI
toolkit, which in turn uses `asyncio`.  Also note that the body of `search` doesn't use
`await`, `async with` or `async for`, therefore it could be a plain function.  It's defined as
a coroutine just to show that FastAPI knows how to handle it.  In a real app, most endpoints
will query databases or hit other remote servers, so it is a critical advantage of FastAPI —
and ASGI frameworks in general — to support coroutines that can take advantage of
asynchronous libraries for network I/O.

> **Tip**
>
> The `init` and `form` functions to load and serve the static HTML form are a hack to make
> the example short and easy to run.  The recommended best practice is to have a
> proxy/load-balancer in front of the ASGI server to handle all static assets, and also use a
> CDN (Content Delivery Network) when possible.

There are no return type hints in `search` and `form`.  Instead, FastAPI relies on the
`response_model=` keyword argument in the route decorators.  The "Response Model" page in the
FastAPI documentation explains: "The response model is declared in this parameter instead of
as a function return type annotation, because the path function may not actually return that
response model but rather return a dict, database object or some other model, and then use the
`response_model` to perform the field limiting and serialization."

### An `asyncio` TCP Server

The `tcp_mojifinder.py` program uses plain TCP to communicate with a client like Telnet or
Netcat, so it can be written using `asyncio` without external dependencies — and without
reinventing HTTP.  The user types a query at a `?>` prompt, and the server responds with one
line per character found: the code point, the character and its name.  Let's start with the
`supervisor` coroutine and the `main` function that drives the program:

<!-- nocheck -->
```python
async def supervisor(index: InvertedIndex, host: str, port: int) -> None:
    server = await asyncio.start_server(  # quickly gets a started asyncio.Server
        functools.partial(finder, index),  # the callback to run for each client connection
        host, port)

    addr = server.sockets[0].getsockname()  # address and port of the first socket
    print(f'Serving on {addr}. Hit CTRL-C to stop.')
    await server.serve_forever()  # suspend supervisor here, while the server runs

def main(host: str = '127.0.0.1', port_arg: str = '2323'):
    port = int(port_arg)
    print('Building index.')
    index = InvertedIndex()  # build the inverted index
    try:
        asyncio.run(supervisor(index, host, port))  # start the event loop running supervisor
    except KeyboardInterrupt:  # avoid a distracting traceback on Ctrl-C
        print('\nServer shut down.')

if __name__ == '__main__':
    main(*sys.argv[1:])
```

This `await` quickly gets an instance of `asyncio.Server`, a TCP socket server.  By default,
`start_server` creates and starts the server, so it's ready to receive connections.  The first
argument to `start_server` is `client_connected_cb`, a callback to run when a new client
connection starts.  The callback can be a function or a coroutine, but it must accept exactly
two arguments: an `asyncio.StreamReader` and an `asyncio.StreamWriter`.  However, our `finder`
coroutine also needs to get an `index`, so we use `functools.partial` to bind that parameter
and obtain a callable that takes the reader and writer.  Adapting user functions to callback
APIs is the most common use case for `functools.partial` (see
[Freezing Arguments with `functools.partial`](first-class-functions.md#freezing-arguments-with-functoolspartial)).

Although `start_server` already started the server as a concurrent task, we need to `await` on
the `serve_forever` method so that `supervisor` is suspended there.  Without this line,
`supervisor` would return immediately, ending the loop started with
`asyncio.run(supervisor(...))`, and exiting the program.

You may find it easier to understand how control flows in `tcp_mojifinder.py` if you study the
output it generates on the server console:

```console
$ python3 tcp_mojifinder.py
Building index.
Serving on ('127.0.0.1', 2323). Hit Ctrl-C to stop.
 From ('127.0.0.1', 58192): 'cat face'
   To ('127.0.0.1', 58192): 10 results.
 From ('127.0.0.1', 58192): 'fire'
   To ('127.0.0.1', 58192): 11 results.
 From ('127.0.0.1', 58192): '\x00'
Close ('127.0.0.1', 58192).
^C
Server shut down.
$
```

`Building index.` is output by `main`; there's a short delay while the index is built.
`Serving on...` is output by `supervisor`.  Each `From`/`To` pair is one iteration of a
`while` loop in `finder`.  The TCP/IP stack assigned port 58192 to the Telnet client.  If you
connect several clients to the server, you'll see their various ports in the output.  The
`'\x00'` query came from hitting Ctrl-C on the client terminal; the `while` loop in `finder`
exits, and `finder` displays the `Close` message.  Meanwhile the server is still running,
ready to service another client.  Hitting Ctrl-C on the server terminal cancels
`server.serve_forever`, ending `supervisor` and the event loop.

After `main` builds the index and starts the event loop, `supervisor` quickly displays the
`Serving on...` message and is suspended at the `await server.serve_forever()` line.  At that
point, control flows into the event loop and stays there, occasionally coming back to the
`finder` coroutine, which yields control back to the event loop whenever it needs to wait for
the network to send or receive data.  While the event loop is alive, a new instance of the
`finder` coroutine will be started for each client that connects to the server.  In this way,
many clients can be handled concurrently by this simple server.

Now let's see the top of `tcp_mojifinder.py`, with the `finder` coroutine:

<!-- nocheck -->
```python
import asyncio
import functools
import sys

from charindex import InvertedIndex, format_results  # format_results: text-based UI display

CRLF = b'\r\n'
PROMPT = b'?> '

async def finder(index: InvertedIndex,  # wrapped with functools.partial in supervisor
                 reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter) -> None:
    client = writer.get_extra_info('peername')  # the remote client address
    while True:  # a dialog that lasts until a control character is received
        writer.write(PROMPT)  # can't await! write is a plain method
        await writer.drain()  # must await! drain is a coroutine that flushes the buffer
        data = await reader.readline()  # a coroutine that returns bytes
        if not data:  # no bytes: the client closed the connection
            break
        try:
            query = data.decode().strip()  # decode the bytes to str, using UTF-8
        except UnicodeDecodeError:  # control bytes, e.g. from Ctrl-C in Telnet
            query = '\x00'
        print(f' From {client}: {query!r}')  # log the query to the server console
        if query:
            if ord(query[:1]) < 32:  # exit the loop on a control or null character
                break
            results = await search(query, index, writer)  # do the actual search
            print(f'   To {client}: {results} results.')

    writer.close()  # close the StreamWriter...
    await writer.wait_closed()  # ...and wait for it to close
    print(f'Close {client}.')
```

The `StreamWriter.write` method is not a coroutine, just a plain function; that line sends the
`?>` prompt.  `StreamWriter.drain` flushes the writer buffer; it is a coroutine, so it must be
driven with `await`.  `StreamReader.readline` is a coroutine that returns `bytes`.  A
`UnicodeDecodeError` may happen when the user hits Ctrl-C and the Telnet client sends control
bytes; if that happens, we replace the query with a null character, for simplicity.

The last piece of this example is the `search` coroutine:

<!-- nocheck -->
```python
async def search(query: str,  # a coroutine because it writes to a StreamWriter and drains it
                 index: InvertedIndex,
                 writer: asyncio.StreamWriter) -> int:
    chars = index.search(query)  # query the inverted index
    lines = (line.encode() + CRLF for line  # UTF-8 encoded lines, e.g. b'U+0039\t9\tDIGIT NINE\r\n'
                in format_results(chars))
    writer.writelines(lines)  # surprisingly, writer.writelines is not a coroutine...
    await writer.drain()  # ...but writer.drain() is. Don't forget the await!
    status_line = f'{"─" * 66} {len(chars)} found'  # build a status line, then send it
    writer.write(status_line.encode() + CRLF)
    await writer.drain()
    return len(chars)
```

Note that all network I/O in `tcp_mojifinder.py` is in bytes; we need to decode the bytes
received from the network, and encode strings before sending them out.

> **Warning**
>
> Some of the I/O methods are coroutines and must be driven with `await`, while others are
> simple functions.  For example, `StreamWriter.write` is a plain function, because it writes
> to a buffer.  On the other hand, `StreamWriter.drain` — which flushes the buffer and performs
> the network I/O — is a coroutine, as is `StreamReader.readline` — but not
> `StreamWriter.writelines`!  The `asyncio` API docs clearly label coroutines as such.

Here is a complete, self-contained server and client exchange using the same Streams API —
the server and the client run in the same event loop, talking over a real TCP socket on
`localhost`:

```python
import asyncio

async def handle(reader, writer):  # the server side: upper-case each line received
    while data := await reader.readline():
        writer.write(data.upper())
        await writer.drain()
    writer.close()
    await writer.wait_closed()

async def main():
    server = await asyncio.start_server(handle, '127.0.0.1', 0)  # port 0: any free port
    port = server.sockets[0].getsockname()[1]
    async with server:
        reader, writer = await asyncio.open_connection('127.0.0.1', port)  # the client side
        for word in ['async', 'await']:
            writer.write(word.encode() + b'\n')
            await writer.drain()
            print((await reader.readline()).decode().strip())
        writer.close()
        await writer.wait_closed()

asyncio.run(main())
# ASYNC
# AWAIT
```

The `tcp_mojifinder.py` code leverages the high-level `asyncio` Streams API that provides a
ready-to-use server so you only need to implement a handler function, which can be a plain
callback or a coroutine.  There is also a lower-level Transports and Protocols API, inspired
by the transport and protocols abstractions in the Twisted framework.  Refer to the `asyncio`
documentation for more information, including TCP and UDP echo servers and clients
implemented with that lower-level API.

Our next topic is `async for` and the objects that make it work.

## Asynchronous Iteration and Asynchronous Iterables

We saw in [Asynchronous Context Managers](#asynchronous-context-managers) how `async with`
works with objects implementing the `__aenter__` and `__aexit__` methods returning awaitables
— usually in the form of coroutine objects.

Similarly, `async for` works with *asynchronous iterables*: objects that implement
`__aiter__`.  However, `__aiter__` must be a regular method — not a coroutine method — and it
must return an *asynchronous iterator*.  An asynchronous iterator provides an `__anext__`
coroutine method that returns an awaitable — often a coroutine object.  They are also expected
to implement `__aiter__`, which usually returns `self`.  This mirrors the important
distinction of iterables and iterators we discussed in
[Don't Make the Iterable an Iterator for Itself](iterators-generators.md#dont-make-the-iterable-an-iterator-for-itself).

The aiopg asynchronous PostgreSQL driver documentation has an example that illustrates the use
of `async for` to iterate over the rows of a database cursor:

<!-- nocheck -->
```python
async def go():
    pool = await aiopg.create_pool(dsn)
    async with pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT 1")
            ret = []
            async for row in cur:
                ret.append(row)
            assert ret == [(1,)]
```

In this example the query will return a single row, but in a realistic scenario you may have
thousands of rows in response to a `SELECT` query.  For large responses, the cursor will not be
loaded with all the rows in a single batch.  Therefore it is important that
`async for row in cur:` does not block the event loop while the cursor may be waiting for
additional rows.  By implementing the cursor as an asynchronous iterator, aiopg may yield to
the event loop at each `__anext__` call, and resume later when more rows arrive from
PostgreSQL.

Here is a hand-written asynchronous iterator, for comparison with what comes next:

```python
import asyncio

class Ticker:  # an asynchronous iterator: __aiter__ returns self, __anext__ is a coroutine
    def __init__(self, count):
        self.count = count

    def __aiter__(self):  # a plain method
        return self

    async def __anext__(self):  # a coroutine
        if self.count == 0:
            raise StopAsyncIteration  # the asynchronous counterpart of StopIteration
        await asyncio.sleep(.01)  # pretend to wait for data to arrive
        self.count -= 1
        return self.count

async def main():
    return [n async for n in Ticker(3)]

asyncio.run(main())
# [2, 1, 0]
```

### Asynchronous Generator Functions

You can implement an asynchronous iterator by writing a class with `__anext__` and
`__aiter__`, but there is a simpler way: write a function declared with `async def` and use
`yield` in its body.  This parallels how generator functions simplify the classic Iterator
pattern.

Let's study a simple example using `async for` and implementing an asynchronous generator.
We saw `blogdom.py`, a script that probed domain names.  Now suppose we find other uses for the
`probe` coroutine we defined there, and decide to put it into a new module — `domainlib.py` —
together with a new `multi_probe` asynchronous generator that takes a list of domain names and
yields results as they are probed.  We'll look at the implementation of `domainlib.py` soon,
but first let's see how it is used with Python's asynchronous console.

#### Experimenting with Python's async console

You can run the interpreter with the `-m asyncio` command-line option to get an "async REPL":
a Python console that imports `asyncio`, provides a running event loop, and accepts `await`,
`async for` and `async with` at the top-level prompt — which otherwise are syntax errors when
used outside of native coroutines:

```console
$ python -m asyncio
asyncio REPL 3.15.0 ...
Use "await" directly instead of "asyncio.run()".
Type "help", "copyright", "credits" or "license" for more information.
>>> import asyncio
>>>
```

Note how the header says you can use `await` instead of `asyncio.run()` — to drive coroutines
and other awaitables.  Also: the `import asyncio` line was not typed by the user.  The
`asyncio` module is automatically imported and that line makes that fact clear.  Now let's
import `domainlib.py` and play with its two coroutines, `probe` and `multi_probe`:

```pycon
>>> await asyncio.sleep(3, 'Rise and shine!')
'Rise and shine!'
>>> from domainlib import *
>>> await probe('python.org')
Result(domain='python.org', found=True)
>>> names = 'python.org rust-lang.org golang.org no-lang.invalid'.split()
>>> async for result in multi_probe(names):
...      print(*result, sep='\t')
...
golang.org      True
no-lang.invalid False
python.org      True
rust-lang.org   True
```

First, a simple `await` to see the asynchronous console in action: `asyncio.sleep()` takes an
optional second argument that is returned when you `await` it.  Then we drive the `probe`
coroutine; the `domainlib` version of `probe` returns a `Result` named tuple.  We make a list
of domains.  The `.invalid` top-level domain is reserved for testing: DNS queries for such
domains always get an NXDOMAIN response from DNS servers, meaning "that domain does not exist"
(see RFC 6761).  Finally, we iterate with `async for` over the `multi_probe` asynchronous
generator to display the results.  Note that the results are not in the order the domains
were given to `multi_probe`.  They appear as each DNS response comes back.

That shows that `multi_probe` is an asynchronous generator because it is compatible with
`async for`.  Here are a few more experiments:

```pycon
>>> probe('python.org')
<coroutine object probe at 0x10e313740>
>>> multi_probe(names)
<async_generator object multi_probe at 0x10e246b80>
>>> for r in multi_probe(names):
...    print(r)
...
Traceback (most recent call last):
   ...
TypeError: 'async_generator' object is not iterable
```

Calling a native coroutine gives you a coroutine object.  Calling an asynchronous generator
gives you an `async_generator` object.  We can't use a regular `for` loop with asynchronous
generators because they implement `__aiter__` instead of `__iter__`.

Asynchronous generators are driven by `async for`, which can be a block statement, and it also
appears in asynchronous comprehensions, which we'll cover soon.

#### Implementing an asynchronous generator

Now let's study the code for `domainlib.py`, with the `multi_probe` asynchronous generator:

<!-- nocheck -->
```python
import asyncio
import socket
from collections.abc import Iterable, AsyncIterator
from typing import NamedTuple

class Result(NamedTuple):  # makes the result from probe easier to read and debug
    domain: str
    found: bool

async def probe(domain: str, loop: asyncio.AbstractEventLoop | None = None) -> Result:
    if loop is None:  # optional loop argument, to avoid repeated get_running_loop calls
        loop = asyncio.get_running_loop()
    try:
        await loop.getaddrinfo(domain, None)
    except socket.gaierror:
        return Result(domain, False)
    return Result(domain, True)

async def multi_probe(domains: Iterable[str]) -> AsyncIterator[Result]:  # an async generator
    loop = asyncio.get_running_loop()
    coros = [probe(domain, loop) for domain in domains]  # a list of probe coroutine objects
    for coro in asyncio.as_completed(coros):  # not async for: as_completed is a classic generator
        result = await coro  # await on the coroutine object to retrieve the result
        yield result  # this line makes multi_probe an asynchronous generator
```

`probe` now gets an optional `loop` argument, to avoid repeated calls to `get_running_loop`
when this coroutine is driven by `multi_probe`.  An asynchronous generator function produces
an asynchronous generator object, which can be annotated as `AsyncIterator[SomeType]`.  The
`for` loop could be more concise:

<!-- nocheck -->
```python
    for coro in asyncio.as_completed(coros):
        yield await coro
```

Python parses that as `yield (await coro)`, so it works.  Here is a version you can run
anywhere, with simulated DNS latency:

```python
import asyncio
from collections.abc import Iterable, AsyncIterator
from typing import NamedTuple

class Result(NamedTuple):
    domain: str
    found: bool

DELAYS = {'python.org': .03, 'rust-lang.org': .04, 'golang.org': .01, 'no-lang.invalid': .02}

async def probe(domain: str) -> Result:
    await asyncio.sleep(DELAYS[domain])  # stands in for a DNS query
    return Result(domain, not domain.endswith('.invalid'))

async def multi_probe(domains: Iterable[str]) -> AsyncIterator[Result]:
    coros = [probe(domain) for domain in domains]
    for coro in asyncio.as_completed(coros):
        yield await coro

names = 'python.org rust-lang.org golang.org no-lang.invalid'.split()

async def main():
    async for result in multi_probe(names):
        print(*result, sep='\t')

asyncio.run(main())
# golang.org	True
# no-lang.invalid	False
# python.org	True
# rust-lang.org	True
```

Given `domainlib.py`, we can demonstrate the use of the `multi_probe` asynchronous generator
in `domaincheck.py`: a script that takes a domain suffix and searches for domains made from
short Python keywords.  Here is a sample output:

```console
$ ./domaincheck.py net
FOUND           NOT FOUND
=====           =========
in.net
del.net
true.net
for.net
is.net
                none.net
try.net
                from.net
and.net
or.net
else.net
with.net
if.net
as.net
                elif.net
                pass.net
                not.net
                def.net
```

Thanks to `domainlib`, the code for `domaincheck.py` is straightforward:

<!-- nocheck -->
```python
#!/usr/bin/env python3
import asyncio
import sys
from keyword import kwlist

from domainlib import multi_probe

async def main(tld: str) -> None:
    tld = tld.strip('.')
    names = (kw for kw in kwlist if len(kw) <= 4)  # keywords with length up to 4
    domains = (f'{name}.{tld}'.lower() for name in names)  # domain names with the given TLD
    print('FOUND\t\tNOT FOUND')  # a header for the tabular output
    print('=====\t\t=========')
    async for domain, found in multi_probe(domains):  # asynchronously iterate
        indent = '' if found else '\t\t'  # put the result in the proper column
        print(f'{indent}{domain}')

if __name__ == '__main__':
    if len(sys.argv) == 2:
        asyncio.run(main(sys.argv[1]))  # run main with the command-line argument
    else:
        print('Please provide a TLD.', f'Example: {sys.argv[0]} COM.BR')
```

Generators have one extra use unrelated to iteration: they can be made into context managers.
This also applies to asynchronous generators.

#### Asynchronous generators as context managers

Writing our own asynchronous context managers is not a frequent programming task, but if you
need to write one, consider using the
[`@asynccontextmanager`](https://docs.python.org/3/library/contextlib.html#contextlib.asynccontextmanager)
decorator from the `contextlib` module.  That's very similar to the `@contextmanager` decorator
we studied in [Using `@contextmanager`](context-managers.md#using-contextmanager).  An
interesting example combining `@asynccontextmanager` with `loop.run_in_executor` appears in
Caleb Hattingh's book *Using Asyncio in Python*:

<!-- nocheck -->
```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def web_page(url):  # the decorated function must be an asynchronous generator
    loop = asyncio.get_running_loop()
    data = await loop.run_in_executor(  # download_webpage blocks: run it in a thread
        None, download_webpage, url)
    yield data  # lines before this become __aenter__; data is bound to the as target
    await loop.run_in_executor(None, update_stats, url)  # lines after become __aexit__

async with web_page('google.com') as data:  # use web_page with async with
    process(data)
```

Suppose `download_webpage` is a blocking function using the `requests` library; we run it in a
separate thread to avoid blocking the event loop.  All lines before the `yield` expression will
become the `__aenter__` coroutine method of the asynchronous context manager built by the
decorator.  The value of `data` will be bound to the `data` variable after the `as` clause in
the `async with` statement.  Lines after the `yield` will become the `__aexit__` coroutine
method.  Here, another blocking call is delegated to the thread executor.  And here is a
runnable sketch of the same shape:

```python
import asyncio
from contextlib import asynccontextmanager

@asynccontextmanager
async def session(name):
    await asyncio.sleep(.01)  # pretend to open a connection
    print(f'open {name}')
    try:
        yield name.upper()
    finally:
        await asyncio.sleep(.01)  # pretend to close it
        print(f'close {name}')

async def main():
    async with session('db') as s:
        print('using', s)

asyncio.run(main())
# open db
# using DB
# close db
```

Now let's wrap up our coverage of asynchronous generator functions by contrasting them with
native coroutines.

#### Asynchronous generators versus native coroutines

Here are some key similarities and differences between a native coroutine and an asynchronous
generator function:

* Both are declared with `async def`.
* An asynchronous generator always has a `yield` expression in its body — that's what makes it
  a generator.  A native coroutine never contains `yield`.
* A native coroutine may `return` some value other than `None`.  An asynchronous generator can
  only use empty `return` statements.
* Native coroutines are awaitable: they can be driven by `await` expressions or passed to one
  of the many `asyncio` functions that take awaitable arguments, such as `create_task`.
  Asynchronous generators are not awaitable.  They are asynchronous iterables, driven by
  `async for` or by asynchronous comprehensions.

Time to talk about asynchronous comprehensions.

### Async Comprehensions and Async Generator Expressions

[**PEP 530**](https://peps.python.org/pep-0530/) — Asynchronous Comprehensions introduced the
use of `async for` and `await` in the syntax of comprehensions and generator expressions.  The
only construct defined by PEP 530 that can appear outside an `async def` body is an
asynchronous generator expression.

#### Defining and using an asynchronous generator expression

Given the `multi_probe` asynchronous generator, we could write another asynchronous generator
returning only the names of the domains found.  Here is how, continuing with the runnable
`multi_probe` defined above:

```python
gen_found = (name async for name, found in multi_probe(names) if found)
gen_found  # an async_generator object, like those returned by multi_probe
# <async_generator object <genexpr> at 0x10a8f9700>

async def main():
    async for name in gen_found:  # driven by async for, inside a coroutine
        print(name)

asyncio.run(main())
# golang.org
# python.org
# rust-lang.org
```

The use of `async for` makes this an asynchronous generator expression.  It can be defined
anywhere in a Python module.  The asynchronous generator expression builds an
`async_generator` object — exactly the same type of object returned by an asynchronous
generator function like `multi_probe`.  The asynchronous generator object is driven by the
`async for` statement, which in turn can only appear inside an `async def` body or in the
magic asynchronous console.

To summarize: an asynchronous generator expression can be defined anywhere in your program,
but it can only be consumed inside a native coroutine or asynchronous generator function.
The remaining constructs introduced by PEP 530 can only be defined and used inside native
coroutines or asynchronous generator functions.

#### Asynchronous comprehensions

Yury Selivanov — the author of PEP 530 — justifies the need for asynchronous comprehensions
with three short code snippets.  We can all agree that we should be able to rewrite this code:

<!-- nocheck -->
```python
result = []
async for i in aiter():
    if i % 2:
        result.append(i)
```

like this:

<!-- nocheck -->
```python
result = [i async for i in aiter() if i % 2]
```

In addition, given a native coroutine `fun`, we should be able to write this:

<!-- nocheck -->
```python
result = [await fun() for fun in funcs]
```

> **Tip**
>
> Using `await` in a list comprehension is similar to using `asyncio.gather` — except that the
> comprehension awaits each coroutine in turn, while `gather` runs them concurrently.
> `gather` also gives you more control over exception handling, thanks to its optional
> `return_exceptions` argument.

Here are both, running with the simulated `probe`:

```python
async def main():
    sorted_names = sorted(names)
    coros = [probe(name) for name in sorted_names]
    print(await asyncio.gather(*coros))  # concurrent
    print([await probe(name) for name in sorted_names])  # one after the other

asyncio.run(main())
# [Result(domain='golang.org', found=True), Result(domain='no-lang.invalid', found=False), Result(domain='python.org', found=True), Result(domain='rust-lang.org', found=True)]
# [Result(domain='golang.org', found=True), Result(domain='no-lang.invalid', found=False), Result(domain='python.org', found=True), Result(domain='rust-lang.org', found=True)]
```

The list of names is sorted to show that the results come out in the order they were
submitted, in both cases.

PEP 530 allows the use of `async for` and `await` in list comprehensions as well as in `dict`
and `set` comprehensions.  We can use the `await` keyword in the expression before the `for`
or `async for` clause, and also in the expression after the `if` clause:

```python
async def main():
    print({name: found async for name, found in multi_probe(names)})
    print(sorted({name for name in names if (await probe(name)).found}))

asyncio.run(main())
# {'golang.org': True, 'no-lang.invalid': False, 'python.org': True, 'rust-lang.org': True}
# ['golang.org', 'python.org', 'rust-lang.org']
```

Note the extra parentheses around the `await` expression in the set comprehension, due to the
higher precedence of the `.` (dot) operator.  Again, all of these comprehensions can only
appear inside an `async def` body or in the enchanted asynchronous console.

Now let's talk about a very important feature of the `async` statements, `async` expressions,
and the objects they create.  Those constructs are often used with `asyncio` but, they are
actually library independent.

## async Beyond asyncio: Curio

Python's `async`/`await` language constructs are not tied to any specific event loop or
library.  (That's in contrast with JavaScript, where `async`/`await` is hardwired to the
built-in event loop and runtime environment.)  Thanks to the extensible API provided by
special methods, anyone sufficiently motivated can write their own asynchronous runtime
environment and framework to drive native coroutines, asynchronous generators, etc.

That's what David Beazley did in his [Curio](https://github.com/dabeaz/curio) project.  He was
interested in rethinking how these new language features could be used in a framework built
from scratch.  Recall that `asyncio` was released in Python 3.4, and it used `yield from`
instead of `await`, so its API could not leverage asynchronous context managers, asynchronous
iterators, and everything else that the `async`/`await` keywords made possible.  As a result,
Curio has a cleaner API and a simpler implementation, compared to `asyncio`.  Here is
`blogdom.py` rewritten to use Curio:

<!-- nocheck -->
```python
#!/usr/bin/env python3
from curio import run, TaskGroup
import curio.socket as socket
from keyword import kwlist

MAX_KEYWORD_LEN = 4

async def probe(domain: str) -> tuple[str, bool]:  # no need to get the event loop, because...
    try:
        await socket.getaddrinfo(domain, None)  # ...getaddrinfo is a top-level function
    except socket.gaierror:
        return (domain, False)
    return (domain, True)

async def main() -> None:
    names = (kw for kw in kwlist if len(kw) <= MAX_KEYWORD_LEN)
    domains = (f'{name}.dev'.lower() for name in names)
    async with TaskGroup() as group:  # monitor and control several coroutines
        for domain in domains:
            await group.spawn(probe, domain)  # start a coroutine, managed by the group
        async for task in group:  # yields Task instances as each is completed
            domain, found = task.result
            mark = '+' if found else ' '
            print(f'{mark} {domain}')

if __name__ == '__main__':
    run(main())
```

`probe` doesn't need to get the event loop, because `getaddrinfo` is a top-level function of
`curio.socket`, not a method of a `loop` object — as it is in `asyncio`.  A `TaskGroup` is a
core concept in Curio, to monitor and control several coroutines, and to make sure they are all
executed and cleaned up.  `TaskGroup.spawn` is how you start a coroutine, managed by a specific
`TaskGroup` instance.  The coroutine is wrapped by a `Task`.  Iterating with `async for` over a
`TaskGroup` yields `Task` instances as each is completed.  And `run(main())` is the sensible way
to start an asynchronous program that Curio pioneered — `asyncio.run` came later.

Task groups support *structured concurrency*: a form of concurrent programming that constrains
all the activity of a group of asynchronous tasks to a single entry and exit point.  This is
analogous to structured programming, which eschewed the `GOTO` command and introduced block
statements to limit the entry and exit points of loops and subroutines.  When used as an
asynchronous context manager, a `TaskGroup` ensures that all tasks spawned inside are completed
or cancelled, and any exceptions raised, upon exiting the enclosed block.

Another important feature of Curio is better support for programming with coroutines and
threads in the same codebase — a necessity in most nontrivial asynchronous programs.  The
design of Curio has been influential.  The [Trio](https://trio.readthedocs.io/) framework
started by Nathaniel J. Smith was heavily inspired by Curio, and calls its task groups
"nurseries".  Curio and Trio also prompted Python contributors to improve the usability of the
`asyncio` API.  For example, in its earliest releases, `asyncio` users very often had to get
and pass around a `loop` object; in recent versions of Python, direct access to the loop is
rarely needed.

### Structured Concurrency with `TaskGroup`

The ideas of Curio and Trio arrived in the standard library in Python 3.11.
[**PEP 654**](https://peps.python.org/pep-0654/) — Exception Groups and `except*` said that
"implementing a better task spawning API in asyncio, inspired by Trio nurseries, was the main
motivation for this PEP", and that API is
[`asyncio.TaskGroup`](https://docs.python.org/3/library/asyncio-task.html#task-groups):

```python
import asyncio

async def probe(domain: str) -> tuple[str, bool]:
    await asyncio.sleep(DELAYS[domain])
    return (domain, not domain.endswith('.invalid'))

async def main() -> None:
    async with asyncio.TaskGroup() as tg:  # the block waits for all tasks to finish
        tasks = [tg.create_task(probe(domain)) for domain in names]
    for task in tasks:  # all tasks are done here
        domain, found = task.result()
        print('+' if found else ' ', domain)

asyncio.run(main())
# + python.org
# + rust-lang.org
# + golang.org
#   no-lang.invalid
```

Compared to `asyncio.gather`, a `TaskGroup` has much better failure semantics.  If any task
raises an exception, the group cancels all the other tasks, waits for them, and then raises an
`ExceptionGroup` collecting the errors, which you can handle with `except*` (see
[Raising and Handling Multiple Unrelated Exceptions](errors.md#tut-exception-groups)):

```python
async def fails():
    await asyncio.sleep(.01)
    raise ValueError('boom')

async def slow():
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        print('slow was cancelled')  # the group cancels the other tasks
        raise

async def main():
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(fails())
            tg.create_task(slow())
    except* ValueError as eg:
        print('caught', repr(eg.exceptions[0]))

asyncio.run(main())
# slow was cancelled
# caught ValueError('boom')
```

> **Tip**
>
> Prefer `asyncio.TaskGroup` to `asyncio.gather` and bare `create_task` calls in new code.
> Combine it with `asyncio.timeout()` (also new in Python 3.11), an asynchronous context
> manager that cancels the block if it takes too long:
>
> ```python
> async with asyncio.timeout(10):  # raises TimeoutError after 10 seconds
>     async with asyncio.TaskGroup() as tg:
>         ...
> ```

Type annotations for asynchronous types are our next topic.

## Type Hinting Asynchronous Objects

The return type of a native coroutine describes what you get when you `await` on that
coroutine, which is the type of the object that appears in the `return` statements in the body
of the native coroutine function.  (This differs from the annotations of classic coroutines, as
discussed in [Generic Type Hints for Classic Coroutines](iterators-generators.md#generic-type-hints-for-classic-coroutines).)
This chapter provided many examples of annotated native coroutines, including `probe`:

<!-- nocheck -->
```python
async def probe(domain: str) -> tuple[str, bool]:
    try:
        await socket.getaddrinfo(domain, None)
    except socket.gaierror:
        return (domain, False)
    return (domain, True)
```

If you need to annotate a parameter that takes a coroutine object, then the generic type is
`collections.abc.Coroutine[YieldType, SendType, ReturnType]`.  That type, and the following
types are used to annotate asynchronous objects (all from `collections.abc`, except the
context manager, which is in `contextlib`; the corresponding names in `typing` are deprecated
aliases):

<!-- nocheck -->
```python
class Coroutine(Awaitable[V_co], Generic[T_co, T_contra, V_co]): ...
class AsyncIterable(Generic[T_co]): ...
class AsyncIterator(AsyncIterable[T_co]): ...
class AsyncGenerator(AsyncIterator[T_co], Generic[T_co, T_contra]): ...
class Awaitable(Generic[T_co]): ...
class AbstractAsyncContextManager(Generic[T_co]): ...  # in contextlib
```

There are three aspects of those generic types worth highlighting.

First: they are all covariant on the first type parameter, which is the type of the items
yielded from these objects.  Recall rule #1 of
[Variance rules of thumb](type-hints-more.md#variance-rules-of-thumb): if a formal type
parameter defines a type for data that comes out of the object, it can be covariant.

Second: `AsyncGenerator` and `Coroutine` are contravariant on the second to last parameter.
That's the type of the argument of the low-level `.send()` method that the event loop calls to
drive asynchronous generators and coroutines.  As such, it is an "input" type.  Therefore, it
can be contravariant, per variance rule of thumb #2: if a formal type parameter defines a type
for data that goes into the object after its initial construction, it can be contravariant.

Third: `AsyncGenerator` has no return type, in contrast with `collections.abc.Generator`.
Returning a value by raising `StopIteration(value)` was one of the hacks that enabled generators
to operate as coroutines and support `yield from`, as we saw in
[Classic Coroutines](iterators-generators.md#classic-coroutines).  There is no such overlap
among the asynchronous objects: `AsyncGenerator` objects don't return values, and are completely
separate from native coroutine objects, which are annotated with `Coroutine`.

Finally, let's briefly discuss the advantages and challenges of asynchronous programming.

## How Async Works and How It Doesn't

The sections closing this chapter discuss high-level ideas around asynchronous programming,
regardless of the language or library you are using.  Let's begin by explaining the #1 reason
why asynchronous programming is appealing, followed by a popular myth, and how to deal with it.

### Running Circles Around Blocking Calls

Ryan Dahl, the inventor of Node.js, introduces the philosophy of his project by saying "We're
doing I/O completely wrong."  He defines a *blocking function* as one that does file or network
I/O, and argues that we can't treat them as we treat nonblocking functions.  To explain why, he
presents numbers like those in the second column of this table:

| Device | CPU cycles | Proportional "human" scale |
|---|---:|---:|
| L1 cache | 3 | 3 seconds |
| L2 cache | 14 | 14 seconds |
| RAM | 250 | 250 seconds |
| disk | 41,000,000 | 1.3 years |
| network | 240,000,000 | 7.6 years |

To make sense of that table, bear in mind that modern CPUs with GHz clocks run billions of
cycles per second.  Let's say that a CPU runs exactly 1 billion cycles per second.  That CPU can
make more than 333 million L1 cache reads in 1 second, or 4 (four!) network reads in the same
time.  The third column puts those numbers in perspective by multiplying the second column by a
constant factor.  So, in an alternate universe, if one read from L1 cache took 3 seconds, then a
network read would take 7.6 years!

That explains why a disciplined approach to asynchronous programming can lead to
high-performance servers.  The challenge is achieving that discipline.  The first step is to
recognize that "I/O bound system" is a fantasy.

### The Myth of I/O-Bound Systems

A commonly repeated meme is that asynchronous programming is good for "I/O bound systems".
There are no "I/O-bound systems".  You may have I/O-bound *functions*.  Perhaps the vast
majority of the functions in your system are I/O bound; i.e., they spend more time waiting for
I/O than crunching data.  While waiting, they cede control to the event loop, which can then
drive some other pending task.  But inevitably, any nontrivial system will have some parts that
are CPU bound.  Even trivial systems reveal that, under stress.

A famous example: when Yury Selivanov released uvloop, "a fast, drop-in replacement of the
built-in asyncio event loop", in 2016, his benchmarks of a simple HTTP echo server — the
archetypal "I/O-bound system" — showed that the bottleneck was not the event loop at all, but
the HTTP header parser, written in Python.  Whenever a function written in Python was parsing
headers, the event loop was blocked.  He had to write `httptools`, a binding to a C parser,
before the faster event loop could make a difference.

Given that any nontrivial system will have CPU-bound functions, dealing with them is the key to
success in asynchronous programming.

### Avoiding CPU-Bound Traps

If you're using Python at scale, you should have some automated tests designed specifically to
detect performance regressions as soon as they appear.  This is critically important with
asynchronous code, but also relevant to threaded Python code — because of the GIL.  If you wait
until the slowdown starts bothering the development team, it's too late.  The fix will probably
require some major makeover.  Here are some options for when you identify a CPU-hogging
bottleneck:

* Delegate the task to a Python process pool.
* Delegate the task to an external task queue.
* Rewrite the relevant code in Cython, C, Rust, or some other language that compiles to machine
  code and interfaces with the Python/C API, preferably releasing the GIL.
* Decide that you can afford the performance hit and do nothing — but record the decision to
  make it easier to revert to it later.

The external task queue should be chosen and integrated as soon as possible at the start of the
project, so that nobody in the team hesitates to use it when needed.  The last option — do
nothing — falls in the category of technical debt.

> **Tip**
>
> `asyncio` has a *debug mode* (`python -X dev`, or `asyncio.run(main(), debug=True)`) that
> logs coroutines that were never awaited, and callbacks that take more than 100ms — a cheap
> way to spot code that blocks the event loop.  See
> [Developing with asyncio](https://docs.python.org/3/library/asyncio-dev.html).

## Summary

> The problem with normal approaches to asynchronous programming is that they're
> all-or-nothing propositions.  You rewrite all your code so none of it blocks or you're just
> wasting your time.
>
> — Alvaro Videla and Jason J. W. Williams, *RabbitMQ in Action*

That epigraph is apt for two reasons.  At a high level, it reminds us to avoid blocking the
event loop by delegating slow tasks to a different processing unit, from a simple thread all
the way to a distributed task queue.  At a lower level, it is also a warning: once you write
your first `async def`, your program is inevitably going to have more and more `async def`,
`await`, `async with` and `async for`.  And using non-asynchronous libraries suddenly becomes a
challenge.

After the simple spinner examples in [Concurrency Models in Python](concurrency-models.md), here
our main focus was asynchronous programming with native coroutines, starting with the
`blogdom.py` DNS probing example, followed by the concept of awaitables.  While reading the
source code of `flags_asyncio.py`, we found the first example of an asynchronous context
manager.

The more advanced variations of the flag downloading program introduced two powerful functions:
the `asyncio.as_completed` generator and the `asyncio.to_thread` coroutine (and the
`loop.run_in_executor` method underneath it).  We also saw the concept and application of a
semaphore to limit the number of concurrent downloads — as expected from well-behaved HTTP
clients.

Server-side asynchronous programming was presented through the mojifinder examples: a FastAPI
web service and `tcp_mojifinder.py` — the latter using just `asyncio` and the TCP protocol.

Asynchronous iteration and asynchronous iterables were the next major topic, with sections on
`async for`, Python's async console, asynchronous generators, asynchronous generator
expressions and asynchronous comprehensions.

The last examples in the chapter were `blogdom.py` rewritten with the Curio framework, to
demonstrate how Python's asynchronous features are not tied to the `asyncio` package, and
`asyncio.TaskGroup`, the standard library's version of structured concurrency.

Finally, the sections under [How Async Works and How It Doesn't](#how-async-works-and-how-it-doesnt)
discussed the main appeal of asynchronous programming, the misconception of "I/O-bound
systems", and dealing with the inevitable CPU-bound parts of your program.

> **See also**
>
> * The [`asyncio`](https://docs.python.org/3/library/asyncio.html) documentation, in
>   particular [Developing with asyncio](https://docs.python.org/3/library/asyncio-dev.html),
>   which documents debug mode and common mistakes.
> * Caleb Hattingh, *Using Asyncio in Python* (O'Reilly).
> * David Beazley's PyOhio 2016 keynote "Fear and Awaiting in Async", a live-coded
>   introduction to how the asynchronous objects in this chapter work, without any framework.
> * Nathaniel J. Smith, "Some thoughts on asynchronous API design in a post-async/await world"
>   and "Notes on structured concurrency, or: Go statement considered harmful".
> * Łukasz Langa's video series "Learn Python's AsyncIO", and his PyCon 2020 talk
>   "AsyncIO + Music".
> * Lynn Root, "Advanced asyncio: Solving Real-world Production Problems", EuroPython 2019.
> * Bob Nystrom, "What Color Is Your Function?", on the incompatible execution models of plain
>   functions versus async functions in JavaScript, Python, C# and other languages.
