# Concurrent Executors

> The people bashing threads are typically system programmers which have in mind use
> cases that the typical application programmer will never encounter in her life.  [...]
> In 99% of the use cases an application programmer is likely to run into, the simple
> pattern of spawning a bunch of independent threads and collecting the results in a
> queue is everything one needs to know.
>
> — Michele Simionato, Python deep thinker

This chapter focuses on the `concurrent.futures.Executor` classes that encapsulate the
pattern of "spawning a bunch of independent threads and collecting the results in a
queue", described by Michele Simionato.  The concurrent executors make this pattern
almost trivial to use, not only with threads but also with processes — useful for
compute-intensive tasks.

Here we also introduce the concept of *futures* — objects representing the asynchronous
execution of an operation, similar to JavaScript promises.  This primitive idea is the
foundation not only of `concurrent.futures` but also of the `asyncio` package, the subject
of [Asynchronous Programming](asyncio.md).

## Concurrent Web Downloads

Concurrency is essential for efficient network I/O: instead of idly waiting for remote
machines, the application should do something else until a response comes back.

To demonstrate with code, here are three simple programs to download images of 20 country
flags from the web.  The first one, `flags.py`, runs sequentially: it only requests the
next image when the previous one is downloaded and saved locally.  The other two scripts
make concurrent downloads: they request several images practically at the same time, and
save them as they arrive.  The `flags_threadpool.py` script uses the `concurrent.futures`
package, while `flags_asyncio.py` uses `asyncio`.  Here are three typical runs of each
script, downloading images from fluentpython.com, which is behind a CDN:

```console
$ python3 flags.py
BD BR CD CN DE EG ET FR ID IN IR JP MX NG PH PK RU TR US VN
20 flags downloaded in 7.26s
$ python3 flags.py
BD BR CD CN DE EG ET FR ID IN IR JP MX NG PH PK RU TR US VN
20 flags downloaded in 7.20s
$ python3 flags.py
BD BR CD CN DE EG ET FR ID IN IR JP MX NG PH PK RU TR US VN
20 flags downloaded in 7.09s
$ python3 flags_threadpool.py
DE BD CN JP ID EG NG BR RU CD IR MX US PH FR PK VN IN ET TR
20 flags downloaded in 1.37s
$ python3 flags_threadpool.py
EG BR FR IN BD JP DE RU PK PH CD MX ID US NG TR CN VN ET IR
20 flags downloaded in 1.60s
$ python3 flags_threadpool.py
BD DE EG CN ID RU IN VN ET MX FR CD NG US JP TR PK BR IR PH
20 flags downloaded in 1.22s
$ python3 flags_asyncio.py
BD BR IN ID TR DE CN US IR PK PH FR RU NG VN ET MX EG JP CD
20 flags downloaded in 1.36s
$ python3 flags_asyncio.py
RU CN BR IN FR BD TR EG VN IR PH CD ET ID NG DE JP PK MX US
20 flags downloaded in 1.27s
$ python3 flags_asyncio.py
RU IN ID DE BR VN PK MX US IR ET EG NG BD FR CN JP PH CD TR
20 flags downloaded in 1.42s
```

The output for each run starts with the country codes of the flags as they are downloaded,
and ends with a message stating the elapsed time.  It took `flags.py` an average 7.18s to
download 20 images.  The average for `flags_threadpool.py` was 1.40s; for
`flags_asyncio.py`, 1.35s.  Note the order of the country codes: the downloads happened in a
different order every time with the concurrent scripts.

The difference in performance between the concurrent scripts is not significant, but they
are both more than five times faster than the sequential script — and this is just for the
small task of downloading 20 files of a few kilobytes each.  If you scale the task to
hundreds of downloads, the concurrent scripts can outpace the sequential code by a factor of
20 or more.

> **Warning**
>
> While testing concurrent HTTP clients against public web servers, you may inadvertently
> launch a denial-of-service (DoS) attack, or be suspected of doing so.  In this case it's
> OK because those scripts are hardcoded to make only 20 requests.  For anything bigger,
> run a local test server, as explained in [Setting Up Test Servers](#setting-up-test-servers).

Now let's study the implementations of two of the scripts: `flags.py` and
`flags_threadpool.py`.  The third script, `flags_asyncio.py`, is explained in
[Asynchronous Programming](asyncio.md), but showing all three together makes two points:

1. Regardless of the concurrency constructs you use — threads or coroutines — you'll see
   vastly improved throughput over sequential code in network I/O operations, if you code
   it properly.
2. For HTTP clients that can control how many requests they make, there is no significant
   difference in performance between threads and coroutines.  (For servers that may be hit
   by many clients, there is a difference: coroutines scale better because they use much
   less memory than threads, and also reduce the cost of context switching.)

### A Sequential Download Script

Here is the implementation of `flags.py`.  It's not very interesting, but we'll reuse most
of its code and settings to implement the concurrent scripts, so it deserves some
attention.  For clarity, there is no error handling in it.  We will deal with exceptions
later, but here the focus is on the basic structure of the code, to make it easier to
contrast this script with the concurrent ones.

<!-- nocheck -->
```python
import time
from pathlib import Path
from typing import Callable

import httpx  # not part of the standard library: by convention, imported after a blank line

POP20_CC = ('CN IN US ID BR PK NG BD RU JP '  # the 20 most populous countries
            'MX PH VN ET EG DE IR TR CD FR').split()

BASE_URL = 'https://www.fluentpython.com/data/flags'  # the directory with the flag images
DEST_DIR = Path('downloaded')  # local directory where the images are saved

def save_flag(img: bytes, filename: str) -> None:  # save the img bytes to filename
    (DEST_DIR / filename).write_bytes(img)

def get_flag(cc: str) -> bytes:  # given a country code, download the image
    url = f'{BASE_URL}/{cc}/{cc}.gif'.lower()
    resp = httpx.get(url, timeout=6.1,  # always add a sensible timeout to network operations
                     follow_redirects=True)  # by default, HTTPX does not follow redirects
    resp.raise_for_status()  # raise an exception if the HTTP status is not 2XX
    return resp.content

def download_many(cc_list: list[str]) -> int:  # the key function to compare
    for cc in sorted(cc_list):  # alphabetical order, to see that it's preserved
        image = get_flag(cc)
        save_flag(image, f'{cc}.gif')
        print(cc, end=' ', flush=True)  # show progress, one code at a time on the same line
    return len(cc_list)

def main(downloader: Callable[[list[str]], int]) -> None:  # called with the download function
    DEST_DIR.mkdir(exist_ok=True)  # create DEST_DIR if needed
    t0 = time.perf_counter()  # record and report the elapsed time
    count = downloader(POP20_CC)
    elapsed = time.perf_counter() - t0
    print(f'\n{count} downloads in {elapsed:.2f}s')

if __name__ == '__main__':
    main(download_many)
```

We import the [HTTPX](https://www.python-httpx.org/) library.  It's not part of the
standard library, so by convention the import goes after the standard library modules and
a blank line.  `POP20_CC` lists the ISO 3166 country codes for the 20 most populous
countries in order of decreasing population.  `get_flag`, given a country code, builds the
URL and downloads the image, returning the binary contents of the response.  It's good
practice to add a sensible timeout to network operations, to avoid blocking for several
minutes for no good reason.  `raise_for_status` raises an exception if the HTTP status is
not in the 2XX range — highly recommended to avoid silent failures.

`download_many` is the key function to compare with the concurrent implementations.  It
loops over the list of country codes in alphabetical order, to make it easy to see that the
ordering is preserved in the output.  It displays one country code at a time in the same
line so we can see progress as each download happens.  The `end=' '` argument replaces the
usual line break at the end of each line printed with a space character, so all country
codes are displayed progressively in the same line.  The `flush=True` argument is needed
because, by default, Python output is line buffered, meaning that Python only displays
printed characters after a line break.

`main` must be called with the function that will make the downloads; that way, we can use
`main` as a library function with other implementations of `download_many` in the
threadpool and asyncio examples.

> **Tip**
>
> HTTPX is inspired by the Pythonic `requests` package, but is built on a more modern
> foundation.  Crucially, HTTPX provides synchronous and asynchronous APIs, so we can use
> it in all HTTP client examples in this chapter and the next.  Python's standard library
> provides the `urllib.request` module, but its API is synchronous only, and is not user
> friendly.

There's really nothing new to `flags.py`.  It serves as a baseline for comparing the other
scripts, and is used as a library to avoid redundant code when implementing them.  Now
let's see a reimplementation using `concurrent.futures`.

### Downloading with `concurrent.futures`

The main features of the
[`concurrent.futures`](https://docs.python.org/3/library/concurrent.futures.html) package
are the `ThreadPoolExecutor` and `ProcessPoolExecutor` classes, which implement an API to
submit callables for execution in different threads or processes, respectively.  The
classes transparently manage a pool of worker threads or processes, and queues to
distribute jobs and collect results.  But the interface is very high-level, and we don't
need to know about any of those details for a simple use case like our flag downloads.

Here is the easiest way to implement the downloads concurrently, using the
`ThreadPoolExecutor.map` method:

<!-- nocheck -->
```python
from concurrent import futures

from flags import save_flag, get_flag, main  # reuse some functions from the flags module

def download_one(cc: str):  # download a single image: this is what each worker executes
    image = get_flag(cc)
    save_flag(image, f'{cc}.gif')
    print(cc, end=' ', flush=True)
    return cc

def download_many(cc_list: list[str]) -> int:
    with futures.ThreadPoolExecutor() as executor:  # __exit__ waits for all threads
        res = executor.map(download_one, sorted(cc_list))  # call download_one concurrently

    return len(list(res))  # any exception raised in a thread is re-raised here

if __name__ == '__main__':
    main(download_many)  # pass the concurrent version of download_many
```

We instantiate the `ThreadPoolExecutor` as a context manager; the `executor.__exit__`
method will call `executor.shutdown(wait=True)`, which will block until all threads are
done.  The `map` method is similar to the `map` built-in, except that the `download_one`
function will be called concurrently from multiple threads; it returns a generator that you
can iterate to retrieve the value returned by each function call — in this case, each call
to `download_one` will return a country code.  We return the number of results obtained.
If any of the threaded calls raises an exception, that exception is raised here when the
implicit `next()` call inside the `list` constructor tries to retrieve the corresponding
return value from the iterator returned by `executor.map`.

Note that the `download_one` function is essentially the body of the `for` loop in the
sequential `download_many` function.  This is a common refactoring when writing concurrent
code: turning the body of a sequential `for` loop into a function to be called
concurrently.

> **Tip**
>
> The script is very short because it reuses most functions from the sequential `flags.py`
> script.  One of the best features of `concurrent.futures` is to make it simple to add
> concurrent execution on top of legacy sequential code.

The `ThreadPoolExecutor` constructor takes several arguments not shown, but the first and
most important one is `max_workers`, setting the maximum number of worker threads to be
executed.  When `max_workers` is `None` (the default), `ThreadPoolExecutor` decides its
value using the following expression:

<!-- nocheck -->
```python
max_workers = min(32, (os.process_cpu_count() or 1) + 4)
```

(Before Python 3.13 it used `os.cpu_count()`.)  The rationale is explained in the
`ThreadPoolExecutor` documentation: "This default value preserves at least 5 workers for
I/O bound tasks.  It utilizes at most 32 CPU cores for CPU bound tasks which release the
GIL.  And it avoids using very large resources implicitly on many-core machines."
`ThreadPoolExecutor` also reuses idle worker threads before starting `max_workers` worker
threads.  To conclude: the computed default for `max_workers` is sensible, and
`ThreadPoolExecutor` avoids starting new workers unnecessarily.

The library is called `concurrent.futures`, yet there are no futures to be seen in that
example, so you may be wondering where they are.  The next section explains.

### Where Are the Futures?

Futures are core components of `concurrent.futures` and of `asyncio`, but as users of these
libraries we sometimes don't see them.  The script above depends on futures behind the
scenes, but the code does not touch them directly.  This section is an overview of futures,
with an example that shows them in action.

There are two classes named `Future` in the standard library: `concurrent.futures.Future`
and `asyncio.Future`.  They serve the same purpose: an instance of either `Future` class
represents a deferred computation that may or may not have completed.  This is somewhat
similar to the `Deferred` class in Twisted, the `Future` class in Tornado, and `Promise` in
modern JavaScript.

Futures encapsulate pending operations so that we can put them in queues, check whether
they are done, and retrieve results (or exceptions) when they become available.

An important thing to know about futures is that you and I should not create them: they are
meant to be instantiated exclusively by the concurrency framework, be it
`concurrent.futures` or `asyncio`.  Here is why: a `Future` represents something that will
eventually run, therefore it must be scheduled to run, and that's the job of the framework.
In particular, `concurrent.futures.Future` instances are created only as the result of
submitting a callable for execution with a `concurrent.futures.Executor` subclass.  For
example, the `Executor.submit()` method takes a callable, schedules it to run, and returns
a `Future`.

Application code is not supposed to change the state of a future: the concurrency framework
changes the state of a future when the computation it represents is done, and we can't
control when that happens.

Both types of `Future` have a `.done()` method that is nonblocking and returns a Boolean
that tells you whether the callable wrapped by that future has executed or not.  However,
instead of repeatedly asking whether a future is done, client code usually asks to be
notified.  That's why both `Future` classes have an `.add_done_callback()` method: you give
it a callable, and the callable will be invoked with the future as the single argument when
the future is done.  Be aware that the callback callable will run in the same worker thread
or process that ran the function wrapped in the future.

There is also a `.result()` method, which works the same in both classes when the future
is done: it returns the result of the callable, or re-raises whatever exception might have
been thrown when the callable was executed.  However, when the future is not done, the
behavior of the `result` method is very different between the two flavors of `Future`.  In
a `concurrent.futures.Future` instance, invoking `f.result()` will block the caller's
thread until the result is ready.  An optional `timeout` argument can be passed, and if the
future is not done in the specified time, the `result` method raises `TimeoutError`.  The
`asyncio.Future.result` method does not support timeout, and `await` is the preferred way
to get the result of futures in `asyncio` — but `await` doesn't work with
`concurrent.futures.Future` instances.

```python
from concurrent import futures

with futures.ThreadPoolExecutor() as executor:
    ok = executor.submit(pow, 2, 10)  # submit schedules a callable, returning a Future
    bad = executor.submit(divmod, 1, 0)

ok.result()  # the with block waited for both futures to finish
# 1024
ok.done(), bad.done()
# (True, True)
bad.exception()
# ZeroDivisionError('integer division or modulo by zero')
bad.result()  # result() re-raises the exception from the callable
# Traceback (most recent call last):
#   ...
# ZeroDivisionError: integer division or modulo by zero
```

Several functions in both libraries return futures; others use them in their implementation
in a way that is transparent to the user.  An example of the latter is the `Executor.map`
we saw earlier: it returns an iterator in which `__next__` calls the `result` method of each
future, so we get the results of the futures, and not the futures themselves.

To get a practical look at futures, we can rewrite the threadpool script to use the
[`concurrent.futures.as_completed`](https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.as_completed)
function, which takes an iterable of futures and returns an iterator that yields futures as
they are done.

Using `futures.as_completed` requires changes to the `download_many` function only.  The
higher-level `executor.map` call is replaced by two `for` loops: one to create and schedule
the futures, the other to retrieve their results.  While we are at it, we'll add a few
`print` calls to display each future before and after it's done:

<!-- nocheck -->
```python
def download_many(cc_list: list[str]) -> int:
    cc_list = cc_list[:5]  # for this demonstration, use only five countries
    with futures.ThreadPoolExecutor(max_workers=3) as executor:  # to see pending futures
        to_do: list[futures.Future] = []
        for cc in sorted(cc_list):  # alphabetically: results will arrive out of order
            future = executor.submit(download_one, cc)  # schedule; returns a pending future
            to_do.append(future)  # store each future so we can use as_completed later
            print(f'Scheduled for {cc}: {future}')

        for count, future in enumerate(futures.as_completed(to_do), 1):  # yields done futures
            res: str = future.result()  # get the result of this future
            print(f'{future} result: {res!r}')

    return count
```

We use only the top five most populous countries and set `max_workers` to 3 so we can see
pending futures in the output.  `executor.submit` schedules the callable to be executed,
and returns a future representing this pending operation.  `as_completed` yields futures as
they are completed.  Note that the `future.result()` call will never block in this example
because the future is coming out of `as_completed`.  Here is the output of one run:

```console
$ python3 flags_threadpool_futures.py
Scheduled for BR: <Future at 0x100791518 state=running>
Scheduled for CN: <Future at 0x100791710 state=running>
Scheduled for ID: <Future at 0x100791a90 state=running>
Scheduled for IN: <Future at 0x101807080 state=pending>
Scheduled for US: <Future at 0x101807128 state=pending>
CN <Future at 0x100791710 state=finished returned str> result: 'CN'
BR ID <Future at 0x100791518 state=finished returned str> result: 'BR'
<Future at 0x100791a90 state=finished returned str> result: 'ID'
IN <Future at 0x101807080 state=finished returned str> result: 'IN'
US <Future at 0x101807128 state=finished returned str> result: 'US'

5 downloads in 0.70s
```

The futures are scheduled in alphabetical order; the `repr()` of a future shows its state:
the first three are `running`, because there are three worker threads.  The last two
futures are `pending`, waiting for worker threads.  The first `CN` in the result lines is
the output of `download_one` in a worker thread; the rest of the line is the output of
`download_many`.  In the next line, two threads output codes before `download_many` in the
main thread can display the result of the first thread.

> **Tip**
>
> Experiment with `flags_threadpool_futures.py`.  If you run it several times, you'll see
> the order of the results varying.  Increasing `max_workers` to 5 will increase the
> variation in the order of the results.  Decreasing it to 1 will make this script run
> sequentially, and the order of the results will always be the order of the `submit`
> calls.

You can run the same experiment without a network: replace `download_one` with a function
that sleeps for a different time for each country code, and the futures behave the same
way.

Now let's take a brief look at a simple way to work around the GIL for CPU-bound jobs using
`concurrent.futures`.

## Launching Processes with `concurrent.futures`

The `concurrent.futures` documentation page is subtitled "Launching parallel tasks".  The
package enables parallel computation on multicore machines because it supports
distributing work among multiple Python processes using the `ProcessPoolExecutor` class.

Both `ProcessPoolExecutor` and `ThreadPoolExecutor` implement the `Executor` interface, so
it's easy to switch from a thread-based to a process-based solution using
`concurrent.futures`.  There is no advantage in using a `ProcessPoolExecutor` for the flags
download example or any I/O-bound job.  It's easy to verify this; just change
`futures.ThreadPoolExecutor()` to `futures.ProcessPoolExecutor()` in `download_many`.

The constructor for `ProcessPoolExecutor` also has a `max_workers` parameter, which defaults
to `None`.  In that case, the executor limits the number of workers to the number returned
by `os.process_cpu_count()`.  Processes use more memory and take longer to start than
threads, so the real value of `ProcessPoolExecutor` is in CPU-intensive jobs.  Let's go back
to the primality test example of [A Homegrown Process Pool](concurrency-models.md#a-homegrown-process-pool),
rewriting it with `concurrent.futures`.

### Multicore Prime Checker Redux

In [Code for the multicore prime checker](concurrency-models.md#code-for-the-multicore-prime-checker)
we studied `procs.py`, a script that checked the primality of some large numbers using
`multiprocessing`.  Here we solve the same problem in the `proc_pool.py` program using a
`ProcessPoolExecutor`.  `procs.py` has 43 nonblank lines of code, and `proc_pool.py` has 31
— 28% shorter:

<!-- nocheck -->
```python
import sys
from concurrent import futures  # no need to import multiprocessing, SimpleQueue, etc.
from time import perf_counter
from typing import NamedTuple

from primes import is_prime, NUMBERS

class PrimeResult(NamedTuple):  # the same as in procs.py, but no queues or worker function
    n: int
    flag: bool
    elapsed: float

def check(n: int) -> PrimeResult:
    t0 = perf_counter()
    res = is_prime(n)
    return PrimeResult(n, res, perf_counter() - t0)

def main() -> None:
    if len(sys.argv) < 2:
        workers = None  # let the ProcessPoolExecutor decide
    else:
        workers = int(sys.argv[1])

    executor = futures.ProcessPoolExecutor(workers)  # built before the with, to display...
    actual_workers = executor._max_workers  # type: ignore  # ...the actual number of workers

    print(f'Checking {len(NUMBERS)} numbers with {actual_workers} processes:')

    t0 = perf_counter()

    numbers = sorted(NUMBERS, reverse=True)  # descending order, to expose a difference
    with executor:  # use the executor as a context manager
        for n, prime, elapsed in executor.map(check, numbers):  # results in argument order
            label = 'P' if prime else ' '
            print(f'{n:16}  {label} {elapsed:9.6f}s')

    time = perf_counter() - t0
    print(f'Total time: {time:.2f}s')

if __name__ == '__main__':
    main()
```

Instead of deciding ourselves how many workers to use if no command-line argument was
given, we set `workers` to `None` and let the `ProcessPoolExecutor` decide.  We build the
`ProcessPoolExecutor` before the `with` block so that we can display the actual number of
workers in the next line.  `_max_workers` is an undocumented instance attribute of a
`ProcessPoolExecutor`; Mypy correctly complains when we access it, so the `type: ignore`
comment silences it.  We sort the numbers to be checked in descending order.  This will
expose a difference in the behavior of `proc_pool.py` when compared with `procs.py`.  The
`executor.map` call returns the `PrimeResult` instances returned by `check` in the same
order as the `numbers` arguments.

If you run it, you'll see the results appearing in strict descending order:

```console
$ ./proc_pool.py
Checking 20 numbers with 12 processes:
9999999999999999     0.000024s
9999999999999917  P  9.500677s
7777777777777777     0.000022s
7777777777777753  P  8.976933s
7777777536340681     8.896149s
6666667141414921     8.537621s
6666666666666719  P  8.548641s
6666666666666666     0.000002s
5555555555555555     0.000017s
5555555555555503  P  8.214086s
5555553133149889     8.067247s
4444444488888889     7.546234s
4444444444444444     0.000002s
4444444444444423  P  7.622370s
3333335652092209     6.724649s
3333333333333333     0.000018s
3333333333333301  P  6.655039s
 299593572317531  P  2.072723s
 142702110479723  P  1.461840s
               2  P  0.000001s
Total time: 9.65s
```

The first line appears very quickly; the second line takes more than 9.5s to show up; all
the remaining lines appear almost immediately.  In contrast, the ordering of the output of
`procs.py` is heavily influenced by the difficulty in checking whether each number is a
prime.  For example, `procs.py` shows the result for 7777777777777777 near the top, because
it has a low divisor, 7, so `is_prime` quickly determines it's not a prime.  In contrast,
7777777536340681 is 88191709<sup>2</sup>, so `is_prime` will take much longer to determine
that it's a composite number, and even longer to find out that 7777777777777753 is prime —
therefore both of these numbers appear near the end of the output of `procs.py`.

Here is why `proc_pool.py` behaves in that way:

* As mentioned before, `executor.map(check, numbers)` returns the results in the same order
  as the `numbers` are given.
* By default, `proc_pool.py` uses as many workers as there are CPUs — it's what
  `ProcessPoolExecutor` does when `max_workers` is `None`.  That's 12 processes in that
  laptop.
* Because we are submitting `numbers` in descending order, the first is 9999999999999999;
  with 9 as a divisor, it returns quickly.
* The second number is 9999999999999917, the largest prime in the sample.  This will take
  longer than all the others to check.
* Meanwhile, the remaining 11 processes will be checking other numbers, which are either
  primes or composites with large factors, or composites with very small factors.
* When the worker in charge of 9999999999999917 finally determines that's a prime, all the
  other processes have completed their last jobs, so the results appear immediately after.

> **Note**
>
> Although the progress of `proc_pool.py` is not as visible as that of `procs.py`, the
> overall execution time is practically the same, for the same number of workers and CPU
> cores.

> **Tip**
>
> Python 3.14 added a third executor, `concurrent.futures.InterpreterPoolExecutor`, which
> runs each worker in its own isolated interpreter within the same process
> ([**PEP 734**](https://peps.python.org/pep-0734/)).  Each interpreter has its own GIL, so
> CPU-bound work runs in parallel as with processes, with lower startup costs.  As with
> processes, data passed to and from workers must be serialized, and some extension
> modules don't yet support multiple interpreters.

Understanding how concurrent programs behave is not straightforward, so here's a second
experiment that may help you visualize the operation of `Executor.map`.

## Experimenting with `Executor.map`

Let's investigate `Executor.map`, now using a `ThreadPoolExecutor` with three workers
running five callables that output timestamped messages:

```python
from time import sleep, strftime
from concurrent import futures

def display(*args):  # print the arguments, preceded by a timestamp [HH:MM:SS]
    print(strftime('[%H:%M:%S]'), end=' ')
    print(*args)

def loiter(n):  # display a message, sleep for n seconds, display another message
    msg = '{}loiter({}): doing nothing for {}s...'
    display(msg.format('\t'*n, n, n))
    sleep(n)
    msg = '{}loiter({}): done.'
    display(msg.format('\t'*n, n))
    return n * 10  # return n * 10 so we can see how to collect results

def main():
    display('Script starting.')
    executor = futures.ThreadPoolExecutor(max_workers=3)  # three threads
    results = executor.map(loiter, range(5))  # submit five tasks; this does not block
    display('results:', results)  # results is a generator
    display('Waiting for individual results:')
    for i, result in enumerate(results):  # next(results) blocks until each result is ready
        display(f'result {i}: {result}')
```

`display` simply prints whatever arguments it gets, preceded by a timestamp in the format
`[HH:MM:SS]`.  `loiter` does nothing except display a message when it starts, sleep for `n`
seconds, then display a message when it ends; tabs are used to indent the messages
according to the value of `n`.  `loiter` returns `n * 10` so we can see how to collect
results.

`main` creates a `ThreadPoolExecutor` with three threads and submits five tasks to the
executor.  Since there are only three threads, only three of those tasks will start
immediately: the calls `loiter(0)`, `loiter(1)` and `loiter(2)`; this is a nonblocking
call.  We immediately display the results of invoking `executor.map`: it's a generator, as
the output shows.  The `enumerate` call in the `for` loop will implicitly invoke
`next(results)`, which in turn will invoke `_f.result()` on the (internal) `_f` future
representing the first call, `loiter(0)`.  The `result` method will block until the future
is done, therefore each iteration in this loop will have to wait for the next result to be
ready.

Here is a sample run (the exact sequencing of events that happen nearly at the same time
may vary):

```console
$ python3 demo_executor_map.py
[15:56:50] Script starting.
[15:56:50] loiter(0): doing nothing for 0s...
[15:56:50] loiter(0): done.
[15:56:50]      loiter(1): doing nothing for 1s...
[15:56:50]              loiter(2): doing nothing for 2s...
[15:56:50] results: <generator object Executor.map.<locals>.result_iterator at 0x106517168>
[15:56:50]                      loiter(3): doing nothing for 3s...
[15:56:50] Waiting for individual results:
[15:56:50] result 0: 0
[15:56:51]      loiter(1): done.
[15:56:51]                              loiter(4): doing nothing for 4s...
[15:56:51] result 1: 10
[15:56:52]              loiter(2): done.
[15:56:52] result 2: 20
[15:56:53]                      loiter(3): done.
[15:56:53] result 3: 30
[15:56:55]                              loiter(4): done.
[15:56:55] result 4: 40
```

This run started at 15:56:50.  The first thread executes `loiter(0)`, so it will sleep for
0s and return even before the second thread has a chance to start, but your mileage may
vary.  `loiter(1)` and `loiter(2)` start immediately (because the thread pool has three
workers, it can run three functions concurrently).  The results returned by `executor.map`
is a generator; nothing so far would block, regardless of the number of tasks and the
`max_workers` setting.  Because `loiter(0)` is done, the first worker is now available to
start the fourth thread for `loiter(3)`.

The loop is where execution may block, depending on the parameters given to the `loiter`
calls: the `__next__` method of the `results` generator must wait until the first future is
complete.  In this case, it won't block because the call to `loiter(0)` finished before
this loop started.  Note that everything up to this point happened within the same second:
15:56:50.  `loiter(1)` is done one second later, at 15:56:51.  The thread is freed to start
`loiter(4)`.  The result of `loiter(1)` is shown: `10`.  Now the `for` loop will block
waiting for the result of `loiter(2)`.  The pattern repeats: `loiter(2)` is done, its result
is shown; same with `loiter(3)`.  There is a 2s delay until `loiter(4)` is done, because it
started at 15:56:51 and did nothing for 4s.

> **Note**
>
> `Executor.map` submits all the tasks right away, which can use a lot of memory if the
> input iterable is very large or infinite.  Since Python 3.14, the `buffersize` argument
> limits how many tasks are submitted ahead of the results being consumed.

The `Executor.map` function is easy to use, but often it's preferable to get the results as
they are ready, regardless of the order they were submitted.  To do that, we need a
combination of the `Executor.submit` method and the `futures.as_completed` function, as we
saw in [Where Are the Futures?](#where-are-the-futures).  We'll come back to this technique
in [Using `futures.as_completed`](#using-futuresas_completed).

> **Tip**
>
> The combination of `executor.submit` and `futures.as_completed` is more flexible than
> `executor.map` because you can submit different callables and arguments, while
> `executor.map` is designed to run the same callable on the different arguments.  In
> addition, the set of futures you pass to `futures.as_completed` may come from more than
> one executor — perhaps some were created by a `ThreadPoolExecutor` instance, while others
> are from a `ProcessPoolExecutor`.

In the next section, we will resume the flag download examples with new requirements that
will force us to iterate over the results of `futures.as_completed` instead of using
`executor.map`.

## Downloads with Progress Display and Error Handling

As mentioned, the scripts in [Concurrent Web Downloads](#concurrent-web-downloads) have no
error handling to make them easier to read and to contrast the structure of the three
approaches: sequential, threaded and asynchronous.  In order to test the handling of a
variety of error conditions, *Fluent Python* includes the `flags2` examples (in the
`20-executors/getflags/` directory of the fluentpython/example-code-2e repository):

`flags2_common.py`
: Common functions and settings used by all `flags2` examples, including a `main` function,
  which takes care of command-line parsing, timing and reporting results.  That is support
  code, not directly relevant to the subject of this chapter, so it's not listed here.

`flags2_sequential.py`
: A sequential HTTP client with proper error handling and progress bar display.  Its
  `download_one` function is also used by `flags2_threadpool.py`.

`flags2_threadpool.py`
: Concurrent HTTP client based on `futures.ThreadPoolExecutor` to demonstrate error
  handling and integration of the progress bar.

`flags2_asyncio.py`
: Same functionality as the previous example, but implemented with `asyncio` and `httpx`.
  This is covered in [Enhancing the asyncio Downloader](asyncio.md#enhancing-the-asyncio-downloader).

The most visible feature of the `flags2` examples is that they have an animated, text-mode
progress bar implemented with the [tqdm](https://pypi.org/project/tqdm/) package.  If you
type the following code in the Python console after installing the `tqdm` package, you'll
see an animated progress bar where the comment is:

<!-- nocheck -->
```python
import time
from tqdm import tqdm
for i in tqdm(range(1000)):
    time.sleep(.01)

# -> progress bar will appear here <-
```

Besides the neat effect, the `tqdm` function is also interesting conceptually: it consumes
any iterable and produces an iterator which, while it's consumed, displays the progress bar
and estimates the remaining time to complete all iterations.  To compute that estimate,
`tqdm` needs to get an iterable that has a `len`, or additionally receive the `total=`
argument with the expected number of items.  Integrating `tqdm` with our `flags2` examples
provides an opportunity to look deeper into how the concurrent scripts actually work, by
forcing us to use the `futures.as_completed` and the `asyncio.as_completed` functions so
that `tqdm` can display progress as each future is completed.

The other feature of the `flags2` examples is a command-line interface.  All three scripts
accept the same options:

```console
$ python3 flags2_threadpool.py -h
usage: flags2_threadpool.py [-h] [-a] [-e] [-l N] [-m CONCURRENT] [-s LABEL]
                            [-v]
                            [CC ...]

Download flags for country codes. Default: top 20 countries by population.

positional arguments:
  CC                    country code or 1st letter (eg. B for BA...BZ)

options:
  -h, --help            show this help message and exit
  -a, --all             get all available flags (AD to ZW)
  -e, --every           get flags for every possible code (AA...ZZ)
  -l N, --limit N       limit to N first codes
  -m CONCURRENT, --max_req CONCURRENT
                        maximum concurrent requests (default=30)
  -s LABEL, --server LABEL
                        Server to hit; one of DELAY, ERROR, LOCAL, REMOTE
                        (default=LOCAL)
  -v, --verbose         output detailed progress info
```

All arguments are optional.  But the `-s/--server` is essential for testing: it lets you
choose which HTTP server and port will be used in the test.  Pass one of these
case-insensitive labels to determine where the script will look for the flags:

`LOCAL`
: Use `http://localhost:8000/flags`; this is the default.  You should configure a local
  HTTP server to answer at port 8000.

`REMOTE`
: Use `http://fluentpython.com/data/flags`; that is a public website, hosted on a shared
  server.  Please do not pound it with too many concurrent requests.

`DELAY`
: Use `http://localhost:8001/flags`; a server delaying HTTP responses should be listening
  to port 8001.

`ERROR`
: Use `http://localhost:8002/flags`; a server returning some HTTP errors should be
  listening on port 8002.

### Setting Up Test Servers

You can set up the test servers using only Python, with no external libraries (the
`README.adoc` in the same directory of the example code repository has the details):

`python3 -m http.server`
: The `LOCAL` server on port 8000, serving the files in the current directory.  (Since
  Python 3.7, `http.server` uses the multithreaded `ThreadingHTTPServer`, which is good for
  experimenting with concurrent clients.)

`python3 slow_server.py`
: The `DELAY` server on port 8001, which adds a random delay of 0.5s to 5s before each
  response.

`python3 slow_server.py 8002 --error-rate .25`
: The `ERROR` server on port 8002, which in addition to the random delay, has a 25% chance
  of returning a "418 I'm a teapot" error response.

By default, each `flags2*.py` script will fetch the flags of the 20 most populous countries
from the `LOCAL` server using a default number of concurrent connections, which varies from
script to script:

```console
$ python3 flags2_sequential.py
LOCAL site: http://localhost:8000/flags
Searching for 20 flags: from BD to VN
1 concurrent connection will be used.
--------------------
20 flags downloaded.
Elapsed time: 0.10s
```

You can select which flags will be downloaded in several ways.  This shows how to download
all flags with country codes starting with the letters A, B or C, from the `DELAY` server:

```console
$ python3 flags2_threadpool.py -s DELAY a b c
DELAY site: http://localhost:8001/flags
Searching for 78 flags: from AA to CZ
30 concurrent connections will be used.
--------------------
43 flags downloaded.
35 not found.
Elapsed time: 1.72s
```

Regardless of how the country codes are selected, the number of flags to fetch can be
limited with the `-l/--limit` option.  This runs exactly 100 requests against the `ERROR`
server, combining the `-a` option to get all flags with `-l 100`, using 100 concurrent
requests:

```console
$ python3 flags2_asyncio.py -s ERROR -al 100 -m 100
ERROR site: http://localhost:8002/flags
Searching for 100 flags: from AD to LK
100 concurrent connections will be used.
--------------------
73 flags downloaded.
27 errors.
Elapsed time: 0.64s
```

That's the user interface of the `flags2` examples.  Let's see how they are implemented.

### Error Handling in the `flags2` Examples

The common strategy in all three examples to deal with HTTP errors is that 404 errors (not
found) are handled by the function in charge of downloading a single file
(`download_one`).  Any other exception propagates to be handled by the `download_many`
function or the `supervisor` coroutine — in the `asyncio` example.

Once more, we'll start by studying the sequential code, which is easier to follow — and
mostly reused by the thread pool script.  Here are the functions that perform the actual
downloads in the `flags2_sequential.py` and `flags2_threadpool.py` scripts:

<!-- nocheck -->
```python
from collections import Counter
from http import HTTPStatus

import httpx
import tqdm  # type: ignore  # tqdm has no type hints: tell Mypy to skip it

from flags2_common import main, save_flag, DownloadStatus  # DownloadStatus is an Enum

DEFAULT_CONCUR_REQ = 1
MAX_CONCUR_REQ = 1

def get_flag(base_url: str, cc: str) -> bytes:
    url = f'{base_url}/{cc}/{cc}.gif'.lower()
    resp = httpx.get(url, timeout=3.1, follow_redirects=True)
    resp.raise_for_status()  # raises HTTPStatusError if the status is not in range(200, 300)
    return resp.content

def download_one(cc: str, base_url: str, verbose: bool = False) -> DownloadStatus:
    try:
        image = get_flag(base_url, cc)
    except httpx.HTTPStatusError as exc:  # handle HTTP code 404 specifically...
        res = exc.response
        if res.status_code == HTTPStatus.NOT_FOUND:
            status = DownloadStatus.NOT_FOUND  # ...by setting the status to NOT_FOUND
            msg = f'not found: {res.url}'
        else:
            raise  # any other HTTPStatusError is re-raised to propagate to the caller
    else:
        save_flag(image, f'{cc}.gif')
        status = DownloadStatus.OK
        msg = 'OK'

    if verbose:  # in verbose mode, display the country code and status message
        print(cc, msg)

    return status
```

Note the `try`/`except`/`else` structure, as recommended in
[Do This, Then That](context-managers.md#do-this-then-that-else-blocks-beyond-if): the
`try` block only contains the call that may raise the expected exception.  Here is the
sequential version of the `download_many` function.  This code is straightforward, but
it's worth studying to contrast with the concurrent versions coming up.  Focus on how it
reports progress, handles errors and tallies downloads:

<!-- nocheck -->
```python
def download_many(cc_list: list[str],
                  base_url: str,
                  verbose: bool,
                  _unused_concur_req: int) -> Counter[DownloadStatus]:
    counter: Counter[DownloadStatus] = Counter()  # tally the outcomes: OK, NOT_FOUND, ERROR
    cc_iter = sorted(cc_list)  # the country codes, ordered alphabetically
    if not verbose:
        cc_iter = tqdm.tqdm(cc_iter)  # an iterator that also animates the progress bar
    for cc in cc_iter:
        try:
            status = download_one(cc, base_url, verbose)  # successive calls to download_one
        except httpx.HTTPStatusError as exc:  # HTTP status errors not handled by download_one
            error_msg = 'HTTP error {resp.status_code} - {resp.reason_phrase}'
            error_msg = error_msg.format(resp=exc.response)
        except httpx.RequestError as exc:  # other network-related exceptions
            error_msg = f'{exc} {type(exc)}'.strip()
        except KeyboardInterrupt:  # exit the loop if the user hits Ctrl-C
            break
        else:  # if no exception escaped download_one, clear the error message
            error_msg = ''

        if error_msg:
            status = DownloadStatus.ERROR  # if there was an error, set the status accordingly
        counter[status] += 1  # increment the counter for that status
        if verbose and error_msg:  # in verbose mode, display the error message, if any
            print(f'{cc} error: {error_msg}')

    return counter  # main displays the numbers in the final report
```

Any exception other than those handled here will abort the script, because the
`flags2_common.main` function that calls `download_many` has no `try`/`except`.  We'll now
study the refactored thread pool example, `flags2_threadpool.py`.

### Using `futures.as_completed`

In order to integrate the `tqdm` progress bar and handle errors on each request, the
`flags2_threadpool.py` script uses `futures.ThreadPoolExecutor` with the
`futures.as_completed` function we've already seen.  Here is the full listing of
`flags2_threadpool.py`.  Only the `download_many` function is implemented; the other
functions are reused from `flags2_common.py` and `flags2_sequential.py`:

<!-- nocheck -->
```python
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx
import tqdm  # type: ignore

from flags2_common import main, DownloadStatus
from flags2_sequential import download_one  # reuse download_one from flags2_sequential

DEFAULT_CONCUR_REQ = 30  # default maximum number of concurrent requests (size of the pool)
MAX_CONCUR_REQ = 1000  # a safety cap, to avoid launching too many threads

def download_many(cc_list: list[str],
                  base_url: str,
                  verbose: bool,
                  concur_req: int) -> Counter[DownloadStatus]:
    counter: Counter[DownloadStatus] = Counter()
    with ThreadPoolExecutor(max_workers=concur_req) as executor:
        to_do_map = {}  # maps each Future to the respective country code, for error reports
        for cc in sorted(cc_list):
            future = executor.submit(download_one, cc,
                                     base_url, verbose)  # schedule one call; get a Future
            to_do_map[future] = cc  # store the future and the country code in the dict
        done_iter = as_completed(to_do_map)  # an iterator that yields futures as they're done
        if not verbose:
            done_iter = tqdm.tqdm(done_iter, total=len(cc_list))  # no len: give tqdm the total
        for future in done_iter:  # iterate over the futures as they are completed
            try:
                status = future.result()  # returns the value or raises the exception
            except httpx.HTTPStatusError as exc:  # the rest is the same as the sequential...
                error_msg = 'HTTP error {resp.status_code} - {resp.reason_phrase}'
                error_msg = error_msg.format(resp=exc.response)
            except httpx.RequestError as exc:
                error_msg = f'{exc} {type(exc)}'.strip()
            except KeyboardInterrupt:
                break
            else:
                error_msg = ''

            if error_msg:
                status = DownloadStatus.ERROR
            counter[status] += 1
            if verbose and error_msg:
                cc = to_do_map[future]  # ...except this: get the country code for the future
                print(f'{cc} error: {error_msg}')

    return counter

if __name__ == '__main__':
    main(download_many, DEFAULT_CONCUR_REQ, MAX_CONCUR_REQ)
```

If the `-m/--max_req` command-line option is not given, `DEFAULT_CONCUR_REQ` will be the
maximum number of concurrent requests, implemented as the size of the thread pool; the
actual number may be smaller if the number of flags to download is smaller.
`MAX_CONCUR_REQ` caps the maximum number of concurrent requests regardless of the number of
flags to download or the `-m/--max_req` command-line option.  It's a safety precaution to
avoid launching too many threads with their significant memory overhead.

We create the `executor` with `max_workers` set to `concur_req`, computed by the `main`
function as the smaller of: `MAX_CONCUR_REQ`, the length of `cc_list`, or the value of the
`-m/--max_req` command-line option.  This avoids creating more threads than necessary.  The
order of the results will depend on the timing of the HTTP responses more than anything, but
if the size of the thread pool is much smaller than `len(cc_list)`, you may notice the
downloads batched alphabetically.

Each call to `executor.submit` schedules the execution of one callable and returns a
`Future` instance.  The first argument is the callable, the rest are the arguments it will
receive.  `futures.as_completed` returns an iterator that yields futures as each task is
done.  If not in verbose mode, we wrap the result of `as_completed` with the `tqdm`
function to display the progress bar; because `done_iter` has no `len`, we must tell `tqdm`
what is the expected number of items as the `total=` argument, so `tqdm` can estimate the
work remaining.

Calling the `result` method on a future either returns the value returned by the callable,
or raises whatever exception was caught when the callable was executed.  This method may
block waiting for a resolution, but not in this example because `as_completed` only returns
futures that are done.  To provide context for the error message, we retrieve the country
code from the `to_do_map` using the current future as key.  This was not necessary in the
sequential version because we were iterating over the list of country codes, so we knew the
current `cc`; here we are iterating over the futures.

> **Tip**
>
> That example uses an idiom that is very useful with `futures.as_completed`: building a
> `dict` to map each future to other data that may be useful when the future is completed.
> Here the `to_do_map` maps each future to the country code assigned to it.  This makes it
> easy to do follow-up processing with the result of the futures, despite the fact that they
> are produced out of order.

Here is the idiom in a self-contained form, with `time.sleep` standing in for network
latency:

```python
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

def fake_download(cc: str) -> int:
    delay = {'BR': .3, 'CN': .1, 'IN': .2}[cc]
    time.sleep(delay)
    if cc == 'IN':
        raise ConnectionError('network is down')
    return len(cc) * 1000  # pretend this is the number of bytes downloaded

results = {}
errors = {}
with ThreadPoolExecutor(max_workers=3) as executor:
    to_do_map = {executor.submit(fake_download, cc): cc for cc in ['BR', 'CN', 'IN']}
    for future in as_completed(to_do_map):
        cc = to_do_map[future]  # which country does this future belong to?
        try:
            results[cc] = future.result()
        except ConnectionError as exc:
            errors[cc] = str(exc)

sorted(results.items()), errors
# ([('BR', 2000), ('CN', 2000)], {'IN': 'network is down'})
```

Python threads are well suited for I/O-intensive applications, and the `concurrent.futures`
package makes it relatively simple to use for certain use cases.  With
`ProcessPoolExecutor`, you can also solve CPU-intensive problems on multiple cores — if the
computations are "embarrassingly parallel".  This concludes our basic introduction to
`concurrent.futures`.

## Summary

We started the chapter by comparing two concurrent HTTP clients with a sequential one,
demonstrating that the concurrent solutions show significant performance gains over the
sequential script.

After studying the first example based on `concurrent.futures`, we took a closer look at
future objects, either instances of `concurrent.futures.Future` or `asyncio.Future`,
emphasizing what these classes have in common (their differences will be emphasized in
[Asynchronous Programming](asyncio.md)).  We saw how to create futures by calling
`Executor.submit`, and iterate over completed futures with
`concurrent.futures.as_completed`.

We then discussed the use of multiple processes with the
`concurrent.futures.ProcessPoolExecutor` class, to go around the GIL and use multiple CPU
cores to simplify the multicore prime checker we first saw in
[Concurrency Models in Python](concurrency-models.md).

In the following section, we saw how the `concurrent.futures.ThreadPoolExecutor` works with
a didactic example, launching tasks that did nothing for a few seconds, except for
displaying their status with a timestamp.

Next we went back to the flag downloading examples.  Enhancing them with a progress bar and
proper error handling prompted further exploration of the `futures.as_completed` generator
function, showing a common pattern: storing futures in a `dict` to link further information
to them when submitting, so that we can use that information when the future comes out of
the `as_completed` iterator.

> **Note**
>
> "Concurrency: one of the most difficult topics in computer science (usually best
> avoided)," as David Beazley put it.  That is not a contradiction of the Simionato quote at
> the start of this chapter: `concurrent.futures` is interesting precisely because it treats
> threads, processes and queues as infrastructure at your service, not something you have
> to deal with directly.  It's designed with simple jobs in mind, the so-called
> embarrassingly parallel problems.  But that's a large slice of the concurrency problems we
> face when writing applications — as opposed to operating systems or database servers.

> **See also**
>
> * The [`concurrent.futures`](https://docs.python.org/3/library/concurrent.futures.html)
>   documentation, and [**PEP 3148**](https://peps.python.org/pep-3148/) — futures - execute
>   computations asynchronously, whose author, Brian Quinlan, wrote that the library was
>   "heavily influenced by the Java `java.util.concurrent` package".
> * Brian Quinlan's talk "The Future Is Soon!" at PyCon Australia 2010.
> * The references on threads and processes at the end of
>   [Concurrency Models in Python](concurrency-models.md#summary) also cover
>   `concurrent.futures`.
