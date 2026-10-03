# Concurrency Models in Python

This chapter introduces Python's core packages for concurrent programming —
`threading`, `multiprocessing` and `asyncio` — through simple examples that compare
them.  After a brief conceptual introduction, we'll write the same small program three
ways, use it to understand the real impact of the Global Interpreter Lock, and then
distribute CPU-intensive work over several processes using queues.  The last part of the
chapter is a high-level overview of the tools, libraries and architectures that let
Python applications scale far beyond what the standard library provides.

## The Big Picture

There are many factors that make concurrent programming hard, but the most basic one is
this: starting threads or processes is easy enough, but how do you keep track of them?

When you call a function, the calling code is blocked until the function returns.  So you
know when the function is done, and you can easily get the value it returned.  If the
function raises an exception, the calling code can surround the call site with
`try`/`except` to catch the error.

Those familiar options are not available when you start a thread or process: you don't
automatically know when it's done, and getting back results or errors requires setting up
some communication channel, such as a message queue.

Additionally, starting a thread or a process is not cheap, so you don't want to start one
of them just to perform a single computation and quit.  Often you want to amortize the
startup cost by making each thread or process into a "worker" that enters a loop and
stands by for inputs to work on.  This further complicates communications and introduces
more questions.  How do you make a worker quit when you don't need it anymore?  And how
do you make it quit without interrupting a job partway, leaving half-baked data and
unreleased resources — like open files?  Again the usual answers involve messages and
queues.

A coroutine is cheap to start.  If you start a coroutine using the `await` keyword, it's
easy to get a value returned by it, it can be safely cancelled, and you have a clear site
to catch exceptions.  But coroutines are often started by the asynchronous framework, and
that can make them as hard to monitor as threads or processes.

Finally, Python coroutines and threads are not suitable for CPU-intensive tasks, as we'll
see.  That's why concurrent programming requires learning new concepts and coding
patterns.  Let's first make sure we are on the same page regarding some core concepts.

## A Bit of Jargon

Here are some terms used in this chapter and the next two:

**Concurrency**
: The ability to handle multiple pending tasks, making progress one at a time or in
  parallel (if possible) so that each of them eventually succeeds or fails.  A
  single-core CPU is capable of concurrency if it runs an OS scheduler that interleaves
  the execution of the pending tasks.  Also known as multitasking.

**Parallelism**
: The ability to execute multiple computations at the same time.  This requires a
  multicore CPU, multiple CPUs, a GPU, or multiple computers in a cluster.

**Execution unit**
: General term for objects that execute code concurrently, each with independent state
  and call stack.  Python natively supports three kinds of execution units: processes,
  threads and coroutines.

**Process**
: An instance of a computer program while it is running, using memory and a slice of the
  CPU time.  Modern desktop operating systems routinely manage hundreds of processes
  concurrently, with each process isolated in its own private memory space.  Processes
  communicate via pipes, sockets or memory-mapped files — all of which can only carry raw
  bytes.  Python objects must be serialized (converted) into raw bytes to pass from one
  process to another.  This is costly, and not all Python objects are serializable.  A
  process can spawn subprocesses, each called a child process.  These are also isolated
  from each other and from the parent.  Processes allow *preemptive multitasking*: the OS
  scheduler preempts — i.e., suspends — each running process periodically to allow other
  processes to run.  This means that a frozen process can't freeze the whole system — in
  theory.

**Thread**
: An execution unit within a single process.  When a process starts, it uses a single
  thread: the main thread.  A process can create more threads to operate concurrently by
  calling operating system APIs.  Threads within a process share the same memory space,
  which holds live Python objects.  This allows easy data sharing between threads, but
  can also lead to corrupted data when more than one thread updates the same object
  concurrently.  Like processes, threads also enable preemptive multitasking under the
  supervision of the OS scheduler.  A thread consumes fewer resources than a process doing
  the same job.

**Coroutine**
: A function that can suspend itself and resume later.  In Python, classic coroutines are
  built from generator functions (see [Classic Coroutines](iterators-generators.md#classic-coroutines)),
  and native coroutines are defined with `async def` (see
  [Asynchronous Programming](asyncio.md)).  Python coroutines usually run within a single
  thread under the supervision of an *event loop*, also in the same thread.  Asynchronous
  programming frameworks such as `asyncio`, Curio or Trio provide an event loop and
  supporting libraries for nonblocking, coroutine-based I/O.  Coroutines support
  *cooperative multitasking*: each coroutine must explicitly cede control with the `yield`
  or `await` keyword, so that another may proceed concurrently (but not in parallel).  This
  means that any blocking code in a coroutine blocks the execution of the event loop and
  all other coroutines — in contrast with the preemptive multitasking supported by
  processes and threads.  On the other hand, each coroutine consumes fewer resources than
  a thread or process doing the same job.

**Queue**
: A data structure that lets us put and get items, usually in FIFO order: first in, first
  out.  Queues allow separate execution units to exchange application data and control
  messages, such as error codes and signals to terminate.  The implementation of a queue
  varies according to the underlying concurrency model: the `queue` package in Python's
  standard library provides queue classes to support threads, while the `multiprocessing`
  and `asyncio` packages implement their own queue classes.  The `queue` and `asyncio`
  packages also include queues that are not FIFO: `LifoQueue` and `PriorityQueue`.

**Lock**
: An object that execution units can use to synchronize their actions and avoid
  corrupting data.  While updating a shared data structure, the running code should hold
  an associated lock.  This signals other parts of the program to wait until the lock is
  released before accessing the same data structure.  The simplest type of lock is also
  known as a *mutex* (for mutual exclusion).  The implementation of a lock depends on the
  underlying concurrency model.

**Contention**
: Dispute over a limited asset.  Resource contention happens when multiple execution
  units try to access a shared resource — such as a lock or storage.  There's also CPU
  contention, when compute-intensive processes or threads must wait for the OS scheduler
  to give them a share of the CPU time.

Now let's use some of that jargon to understand concurrency support in Python.

### Processes, Threads, and Python's Infamous GIL

Here is how the concepts we just saw apply to Python programming, in 10 points:

1. Each instance of the Python interpreter is a process.  You can start additional Python
   processes using the `multiprocessing` or `concurrent.futures` libraries.  Python's
   `subprocess` library is designed to launch processes to run external programs,
   regardless of the languages used to write them.
2. The Python interpreter uses a single thread to run the user's program and the memory
   garbage collector.  You can start additional Python threads using the `threading` or
   `concurrent.futures` libraries.
3. Access to object reference counts and other internal interpreter state is controlled by
   a lock, the *Global Interpreter Lock* (GIL).  Only one Python thread can hold the GIL at
   any time.  This means that only one thread can execute Python code at any time,
   regardless of the number of CPU cores.
4. To prevent a Python thread from holding the GIL indefinitely, Python's bytecode
   interpreter pauses the current Python thread every 5ms by default, releasing the GIL.
   (Call `sys.getswitchinterval()` to get the interval; change it with
   `sys.setswitchinterval(s)`.)  The thread can then try to reacquire the GIL, but if
   there are other threads waiting for it, the OS scheduler may pick one of them to
   proceed.
5. When we write Python code, we have no control over the GIL.  But a built-in function or
   an extension written in C — or any language that interfaces at the Python/C API level —
   can release the GIL while running time-consuming tasks.
6. Every Python standard library function that makes a *syscall* (a call to a function of
   the operating system kernel) releases the GIL.  This includes all functions that
   perform disk I/O, network I/O, and `time.sleep()`.  Many CPU-intensive functions in the
   NumPy/SciPy libraries, as well as the compressing/decompressing functions from the
   `zlib` and `bz2` modules, also release the GIL.
7. Extensions that integrate at the Python/C API level can also launch other non-Python
   threads that are not affected by the GIL.  Such GIL-free threads generally cannot
   change Python objects, but they can read from and write to the memory underlying
   objects that support the buffer protocol, such as `bytearray`, `array.array` and NumPy
   arrays.
8. The effect of the GIL on network programming with Python threads is relatively small,
   because the I/O functions release the GIL, and reading or writing to the network always
   implies high latency — compared to reading and writing to memory.  Consequently, each
   individual thread spends a lot of time waiting anyway, so their execution can be
   interleaved without major impact on the overall throughput.  That's why David Beazley
   says: "Python threads are great at doing nothing."
9. Contention over the GIL slows down compute-intensive Python threads.  Sequential,
   single-threaded code is simpler and faster for such tasks.
10. To run CPU-intensive Python code on multiple cores, you must use multiple Python
    processes — or, with the newer options described in the note below, a free-threaded
    build or multiple interpreters.

Here is a good summary from the [`threading`](https://docs.python.org/3/library/threading.html)
module documentation:

> **CPython implementation detail:** In CPython, due to the Global Interpreter Lock, only
> one thread can execute Python code at once (even though certain performance-oriented
> libraries might overcome this limitation).  If you want your application to make better
> use of the computational resources of multi-core machines, you are advised to use
> `multiprocessing` or `concurrent.futures.ProcessPoolExecutor`.  However, threading is
> still an appropriate model if you want to run multiple I/O-bound tasks simultaneously.

That paragraph starts with "CPython implementation detail" because the GIL is not part of
the Python language definition.  The Jython and IronPython implementations don't have a
GIL, though both have lagged far behind CPython.

> **Note**
>
> Since Python 3.13, CPython can be built without the GIL — the *free-threaded* build,
> usually installed as a separate `python3.13t` (or `python3.14t`, etc.) executable.  In
> that build, threads can run Python code on several cores at once, so the CPU-bound
> experiments later in this chapter behave very differently.  Python 3.14 made the
> free-threaded build officially supported, but it is still optional, and the default
> build still has a GIL.  You can check which build you are running:
>
> ```python
> import sysconfig
> sysconfig.get_config_var('Py_GIL_DISABLED')  # 1 in a free-threaded build
> # 0
> ```
>
> Free threading removes the GIL's protection, so code that shares mutable data between
> threads needs locks even more than before.  Everything this chapter says about the
> difficulty of threads and locks applies with full force.

> **Tip**
>
> The GIL does not affect coroutines, because by default they share the same Python
> thread among themselves and with the supervising event loop provided by an asynchronous
> framework.  It is possible to use multiple threads in an asynchronous program, but the
> best practice is that one thread runs the event loop and all coroutines, while
> additional threads carry out specific tasks.  This will be explained in
> [Delegating Tasks to Executors](asyncio.md#delegating-tasks-to-executors).

Enough concepts for now.  Let's see some code.

## A Concurrent Hello World

During a discussion about threads and how to avoid the GIL, Python contributor Michele
Simionato posted an example that is like a concurrent "Hello World": the simplest
program to show how Python can "walk and chew gum".  His program used `multiprocessing`,
but here it's adapted to introduce `threading` and `asyncio` as well.  Let's start with
the `threading` version, which may look familiar if you've studied threads in Java or C.

### Spinner with Threads

The idea of the next few examples is simple: start a function that blocks for 3 seconds
while animating characters in the terminal to let the user know that the program is
"thinking" and not stalled.

The script makes an animated spinner displaying each character in the string `"\|/-"` in
the same screen position.  When the slow computation finishes, the line with the spinner
is cleared and the result is shown: `Answer: 42`.  Running it, you see something like
this, with the last line spinning for 3 seconds before it is replaced by `Answer: 42`:

```console
$ python3 spinner_thread.py
spinner object: <Thread(Thread-1 (spin), initial)>
| thinking!
```

Here are the first two functions of `spinner_thread.py`:

<!-- nocheck -->
```python
import itertools
import time
from threading import Thread, Event

def spin(msg: str, done: Event) -> None:  # this function will run in a separate thread
    for char in itertools.cycle(r'\|/-'):  # an infinite loop: cycle yields chars forever
        status = f'\r{char} {msg}'  # \r moves the cursor back to the start of the line
        print(status, end='', flush=True)
        if done.wait(.1):  # True when the event is set by another thread; False on timeout
            break  # exit the infinite loop
    blanks = ' ' * len(status)
    print(f'\r{blanks}\r', end='')  # clear the status line

def slow() -> int:
    time.sleep(3)  # blocks the main thread, but the GIL is released
    return 42
```

`spin` will run in a separate thread.  The `done` argument is an instance of
[`threading.Event`](https://docs.python.org/3/library/threading.html#event-objects), a
simple object to synchronize threads.  The loop is infinite because `itertools.cycle`
yields one character at a time, cycling through the string forever.  The trick for
text-mode animation is to move the cursor back to the start of the line with the carriage
return ASCII control character (`'\r'`).

The `Event.wait(timeout=None)` method returns `True` when the event is set by another
thread; if the timeout elapses, it returns `False`.  The 0.1s timeout sets the "frame rate"
of the animation to 10 FPS.  If you want the spinner to go faster, use a smaller timeout.
After the loop, we clear the status line by overwriting it with spaces and moving the
cursor back to the beginning.

`slow()` will be called by the main thread.  Imagine this is a slow API call over the
network.  Calling `sleep` blocks the main thread, but the GIL is released so the spinner
thread can proceed.

> **Tip**
>
> The first important insight of this example is that `time.sleep()` blocks the calling
> thread but releases the GIL, allowing other Python threads to run.

The `spin` and `slow` functions will execute concurrently.  The main thread — the only
thread when the program starts — will start a new thread to run `spin` and then call
`slow`.  By design, there is no API for terminating a thread in Python.  You must send it
a message to shut down.

The `threading.Event` class is Python's simplest signalling mechanism to coordinate
threads.  An `Event` instance has an internal boolean flag that starts as `False`.  Calling
`Event.set()` sets the flag to `True`.  While the flag is false, if a thread calls
`Event.wait()`, it is blocked until another thread calls `Event.set()`, at which time
`Event.wait()` returns `True`.  If a timeout in seconds is given to `Event.wait(s)`, this
call returns `False` when the timeout elapses, or returns `True` as soon as `Event.set()` is
called by another thread.

The `supervisor` function uses an `Event` to signal the `spin` function to exit:

<!-- nocheck -->
```python
def supervisor() -> int:  # supervisor will return the result of slow
    done = Event()  # the key to coordinate the main thread and the spinner thread
    spinner = Thread(target=spin, args=('thinking!', done))  # target function and its args
    print(f'spinner object: {spinner}')  # <Thread(Thread-1 (spin), initial)>
    spinner.start()  # start the spinner thread
    result = slow()  # blocks the main thread; meanwhile, the spinner thread runs
    done.set()  # set the Event flag to True: this will terminate the loop inside spin
    spinner.join()  # wait until the spinner thread finishes
    return result

def main() -> None:
    result = supervisor()
    print(f'Answer: {result}')

if __name__ == '__main__':
    main()
```

To create a new `Thread`, provide a function as the `target` keyword argument, and
positional arguments to the target as a tuple passed via `args`.  The repr of the spinner
object is `<Thread(Thread-1 (spin), initial)>`, where `initial` is the state of the thread
— meaning it has not started.  We call `slow`, which blocks the main thread.  Meanwhile,
the secondary thread is running the spinner animation.  When the main thread sets the
`done` event, the spinner thread will eventually notice and exit cleanly.  (The separate
`main` and `supervisor` functions make this example look more like the `asyncio` version
coming up.)

Now let's take a look at a similar example using the `multiprocessing` package.

### Spinner with Processes

The [`multiprocessing`](https://docs.python.org/3/library/multiprocessing.html) package
supports running concurrent tasks in separate Python processes instead of threads.  When
you create a `multiprocessing.Process` instance, a whole new Python interpreter is started
as a child process in the background.  Since each Python process has its own GIL, this
allows your program to use all available CPU cores — but that ultimately depends on the
operating system scheduler.  We'll see practical effects in
[A Homegrown Process Pool](#a-homegrown-process-pool), but for this simple program it
makes no real difference.

The point of this section is to show that the `multiprocessing` API emulates the
`threading` API, making it easy to convert simple programs from threads to processes.
Here are the changed parts of `spinner_proc.py`; everything else is the same as
`spinner_thread.py`:

<!-- nocheck -->
```python
import itertools
import time
from multiprocessing import Process, Event
from multiprocessing import synchronize

def spin(msg: str, done: synchronize.Event) -> None:
    ...  # the rest of spin and slow functions are unchanged

def supervisor() -> int:
    done = Event()
    spinner = Process(target=spin,
                      args=('thinking!', done))
    print(f'spinner object: {spinner}')
    spinner.start()
    result = slow()
    done.set()
    spinner.join()
    return result

# main function is unchanged as well
```

The basic `multiprocessing` API imitates the `threading` API, but type hints expose a
difference: `multiprocessing.Event` is a function (not a class like `threading.Event`)
which returns a `synchronize.Event` instance, forcing us to import
`multiprocessing.synchronize` to write the type hint.  Basic usage of the `Process` class
is similar to `Thread`.  The spinner object is displayed as
`<Process name='Process-1' parent=14868 initial>`, where `14868` is the process ID of the
Python instance running `spinner_proc.py`.

The basic APIs of `threading` and `multiprocessing` are similar, but their implementation
is very different, and `multiprocessing` has a much larger API to handle the added
complexity of multiprocess programming.  For example, one challenge when converting from
threads to processes is how to communicate between processes that are isolated by the
operating system and can't share Python objects.  This means that objects crossing process
boundaries have to be serialized and deserialized, which creates overhead.  In this
example, the only data that crosses the process boundary is the `Event` state, which is
implemented with a low-level OS semaphore in the C code underlying the `multiprocessing`
module.

> **Warning**
>
> How a child process is started depends on the *start method*: `'fork'` copies the parent
> process, `'spawn'` starts a fresh interpreter, and `'forkserver'` forks from a clean
> server process.  The default is `'spawn'` on Windows and macOS, and since Python 3.14,
> `'forkserver'` on Linux and other POSIX platforms (it used to be `'fork'`).  With
> `'spawn'` and `'forkserver'`, the child imports your main module, so code that starts
> processes must be protected by `if __name__ == '__main__':`, as in our examples.  See
> [Contexts and start methods](https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods).

> **Tip**
>
> The [`multiprocessing.shared_memory`](https://docs.python.org/3/library/multiprocessing.shared_memory.html)
> package lets processes share raw bytes and a `ShareableList`, a mutable sequence type
> that can hold a fixed number of items of types `int`, `float`, `bool` and `None`, as well
> as `str` and `bytes` up to 10 MB per item.  It does not support instances of
> user-defined classes.

Now let's see how the same behavior can be achieved with coroutines instead of threads or
processes.

### Spinner with Coroutines

> **Note**
>
> [Asynchronous Programming](asyncio.md) is entirely devoted to asynchronous programming
> with coroutines.  This is just a high-level introduction to contrast this approach with
> the threads and processes concurrency models.  As such, we will overlook many details.

It is the job of OS schedulers to allocate CPU time to drive threads and processes.  In
contrast, coroutines are driven by an application-level event loop that manages a queue of
pending coroutines, drives them one by one, monitors events triggered by I/O operations
initiated by coroutines, and passes control back to the corresponding coroutine when each
event happens.  The event loop and the library coroutines and the user coroutines all
execute in a single thread.  Therefore, any time spent in a coroutine slows down the event
loop — and all other coroutines.

The coroutine version of the spinner program is easier to understand if we start from the
`main` function, then study the `supervisor`:

<!-- nocheck -->
```python
def main() -> None:  # the only regular function in this program; the others are coroutines
    result = asyncio.run(supervisor())  # start the event loop to drive supervisor
    print(f'Answer: {result}')

async def supervisor() -> int:  # native coroutines are defined with async def
    spinner = asyncio.create_task(spin('thinking!'))  # schedule spin, returning a Task
    print(f'spinner object: {spinner}')
    result = await slow()  # await calls slow, blocking supervisor until slow returns
    spinner.cancel()  # raises CancelledError inside the spin coroutine
    return result

if __name__ == '__main__':
    main()
```

`main` is the only regular function defined in this program — the others are coroutines.
The `asyncio.run` function starts the event loop to drive the coroutine that will
eventually set the other coroutines in motion.  The `main` function will stay blocked until
`supervisor` returns.  The return value of `supervisor` will be the return value of
`asyncio.run`.

`asyncio.create_task` schedules the eventual execution of `spin`, immediately returning an
instance of `asyncio.Task`.  The repr of the spinner object looks like
`<Task pending name='Task-2' coro=<spin() running at /path/to/spinner_async.py:11>>`.  The
`await` keyword calls `slow`, blocking `supervisor` until `slow` returns.  The return value
of `slow` will be assigned to `result`.  The `Task.cancel` method raises a `CancelledError`
exception inside the `spin` coroutine, as we'll see next.

This demonstrates the three main ways of running a coroutine:

`asyncio.run(coro())`
: Called from a regular function to drive a coroutine object that usually is the entry
  point for all the asynchronous code in the program, like the `supervisor` in this
  example.  This call blocks until the body of `coro` returns.  The return value of the
  `run()` call is whatever the body of `coro` returns.

`asyncio.create_task(coro())`
: Called from a coroutine to schedule another coroutine to execute eventually.  This call
  does not suspend the current coroutine.  It returns a `Task` instance, an object that
  wraps the coroutine object and provides methods to control and query its state.

`await coro()`
: Called from a coroutine to transfer control to the coroutine object returned by
  `coro()`.  This suspends the current coroutine until the body of `coro` returns.  The
  value of the `await` expression is whatever the body of `coro` returns.

> **Tip**
>
> Remember: invoking a coroutine as `coro()` immediately returns a coroutine object, but
> does not run the body of the `coro` function.  Driving the body of coroutines is the job
> of the event loop.

Now let's study the `spin` and `slow` coroutines:

<!-- nocheck -->
```python
import asyncio
import itertools

async def spin(msg: str) -> None:  # no need for the Event argument
    for char in itertools.cycle(r'\|/-'):
        status = f'\r{char} {msg}'
        print(status, flush=True, end='')
        try:
            await asyncio.sleep(.1)  # pause without blocking other coroutines
        except asyncio.CancelledError:  # raised when cancel is called on the Task
            break
    blanks = ' ' * len(status)
    print(f'\r{blanks}\r', end='')

async def slow() -> int:
    await asyncio.sleep(3)  # also await asyncio.sleep instead of time.sleep
    return 42
```

We don't need the `Event` argument that was used to signal that `slow` had completed its
job in `spinner_thread.py`.  We use `await asyncio.sleep(.1)` instead of `time.sleep(.1)`,
to pause without blocking other coroutines.  `asyncio.CancelledError` is raised when the
`cancel` method is called on the `Task` controlling this coroutine.  Time to exit the loop.
The `slow` coroutine also uses `await asyncio.sleep` instead of `time.sleep`.

#### Experiment: break the spinner for an insight

Here is an experiment that helps to understand how `spinner_async.py` works.  Import the
`time` module, then go to the `slow` coroutine and replace the line
`await asyncio.sleep(3)` with a call to `time.sleep(3)`:

<!-- nocheck -->
```python
async def slow() -> int:
    time.sleep(3)
    return 42
```

Watching the behavior is more memorable than reading about it.  When you run the
experiment, this is what you see:

1. The spinner object is shown, similar to this:
   `<Task pending name='Task-2' coro=<spin() running at /path/to/spinner_async.py:12>>`.
2. The spinner never appears.  The program hangs for 3 seconds.
3. `Answer: 42` is displayed and the program ends.

To understand what is happening, recall that Python code using `asyncio` has only one flow
of execution, unless you've explicitly started additional threads or processes.  That
means only one coroutine executes at any point in time.  Concurrency is achieved by control
passing from one coroutine to another.  Let's focus on what happens in the `supervisor`
and `slow` coroutines during the experiment:

<!-- nocheck -->
```python
async def slow() -> int:
    time.sleep(3)  # blocks for 3 seconds: nothing else can happen in the program
    return 42

async def supervisor() -> int:
    spinner = asyncio.create_task(spin('thinking!'))  # the task is created...
    print(f'spinner object: {spinner}')  # ...and the display shows it is "pending"
    result = await slow()  # the await expression transfers control to slow
    spinner.cancel()  # right after slow returns, the spinner task is cancelled
    return result
```

The spinner task is created, to eventually drive the execution of `spin`, and the display
shows the `Task` is "pending".  The `await` expression transfers control to the `slow`
coroutine.  `time.sleep(3)` blocks for 3 seconds; nothing else can happen in the program,
because the main thread is blocked — and it is the only thread.  The operating system will
continue with other activities.  After 3 seconds, `sleep` unblocks, and `slow` returns.
Right after `slow` returns, the spinner task is cancelled.  The flow of control never
reached the body of the `spin` coroutine.

> **Warning**
>
> Never use `time.sleep(...)` in `asyncio` coroutines unless you want to pause your whole
> program.  If a coroutine needs to spend some time doing nothing, it should
> `await asyncio.sleep(DELAY)`.  This yields control back to the `asyncio` event loop,
> which can drive other pending coroutines.

#### Greenlet and gevent

As we discuss concurrency with coroutines, it's important to mention the
[greenlet](https://pypi.org/project/greenlet/) package, which has been around for many
years and is used at scale.  The package supports cooperative multitasking through
lightweight coroutines — named *greenlets* — that don't require any special syntax such as
`yield` or `await`, therefore are easier to integrate into existing, sequential codebases.
SQLAlchemy uses greenlets internally to implement its asynchronous API compatible with
`asyncio`.

The [gevent](https://pypi.org/project/gevent/) networking library monkey patches Python's
standard `socket` module, making it nonblocking by replacing some of its code with
greenlets.  To a large extent, gevent is transparent to the surrounding code, making it
easier to adapt sequential applications and libraries — such as database drivers — to
perform concurrent network I/O.  Numerous open source projects use gevent, including the
widely deployed Gunicorn — mentioned in [WSGI Application Servers](#wsgi-application-servers).

### Supervisors Side-by-Side

The line count of `spinner_thread.py` and `spinner_async.py` is nearly the same.  The
`supervisor` functions are the heart of these examples.  Let's compare them in detail.
Here is the threaded `supervisor`:

<!-- nocheck -->
```python
def supervisor() -> int:
    done = Event()
    spinner = Thread(target=spin,
                     args=('thinking!', done))
    print('spinner object:', spinner)
    spinner.start()
    result = slow()
    done.set()
    spinner.join()
    return result
```

And here is the asynchronous `supervisor` coroutine:

<!-- nocheck -->
```python
async def supervisor() -> int:
    spinner = asyncio.create_task(spin('thinking!'))
    print('spinner object:', spinner)
    result = await slow()
    spinner.cancel()
    return result
```

Here is a summary of the differences and similarities to note between the two
`supervisor` implementations:

* An `asyncio.Task` is roughly the equivalent of a `threading.Thread`.
* A `Task` drives a coroutine object, and a `Thread` invokes a callable.
* A coroutine yields control explicitly with the `await` keyword.
* You don't instantiate `Task` objects yourself, you get them by passing a coroutine to
  `asyncio.create_task(...)`.
* When `asyncio.create_task(...)` returns a `Task` object, it is already scheduled to run,
  but a `Thread` instance must be explicitly told to run by calling its `start` method.
* In the threaded `supervisor`, `slow` is a plain function and is directly invoked by the
  main thread.  In the asynchronous `supervisor`, `slow` is a coroutine driven by `await`.
* There's no API to terminate a thread from the outside; instead, you must send a signal —
  like setting the `done` `Event` object.  For tasks, there is the `Task.cancel()` instance
  method, which raises `CancelledError` at the `await` expression where the coroutine body
  is currently suspended.
* The `supervisor` coroutine must be started with `asyncio.run` in the `main` function.

One final point related to threads versus coroutines: if you've done any nontrivial
programming with threads, you know how challenging it is to reason about the program
because the scheduler can interrupt a thread at any time.  You must remember to hold locks
to protect the critical sections of your program, to avoid getting interrupted in the
middle of a multistep operation — which could leave data in an invalid state.

With coroutines, your code is protected against interruption by default.  You must
explicitly `await` to let the rest of the program run.  Instead of holding locks to
synchronize the operations of multiple threads, coroutines are "synchronized" by
definition: only one of them is running at any time.  When you want to give up control, you
use `await` to yield control back to the scheduler.  That's why it is possible to safely
cancel a coroutine: by definition, a coroutine can only be cancelled when it's suspended at
an `await` expression, so you can perform cleanup by handling the `CancelledError`
exception.

The `time.sleep()` call blocks but does nothing.  Now we'll experiment with a CPU-intensive
call to get a better understanding of the GIL, as well as the effect of CPU-intensive
functions in asynchronous code.

## The Real Impact of the GIL

In the threading code, you can replace the `time.sleep(3)` call in the `slow` function with
an HTTP client request from your favorite library, and the spinner will keep spinning.
That's because a well-designed network library will release the GIL while waiting for the
network.

You can also replace the `asyncio.sleep(3)` expression in the `slow` coroutine to `await`
for a response from a well-designed asynchronous network library, because such libraries
provide coroutines that yield control back to the event loop while waiting for the
network.  Meanwhile, the spinner will keep spinning.

With CPU-intensive code, the story is different.  Consider the function `is_prime`, which
returns `True` if the argument is a prime number, `False` if it's not.  It's an easy-to-read
primality check, from the `ProcessPoolExecutor` example in the Python docs:

```python
import math

def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False

    root = math.isqrt(n)
    for i in range(3, root + 1, 2):
        if n % i == 0:
            return False
    return True

[n for n in range(30) if is_prime(n)]
# [2, 3, 5, 7, 11, 13, 17, 19, 23, 29]
```

The call `is_prime(5_000_111_000_222_021)` takes a few seconds on a typical laptop.

### Quick Quiz

Given what we've seen so far, take the time to consider the following three-part question.
One part of the answer is tricky.

What would happen to the spinner animation if you made the following changes, assuming
that `n = 5_000_111_000_222_021` — a prime that takes a few seconds to verify?

1. In `spinner_proc.py`, replace `time.sleep(3)` with a call to `is_prime(n)`?
2. In `spinner_thread.py`, replace `time.sleep(3)` with a call to `is_prime(n)`?
3. In `spinner_async.py`, replace `await asyncio.sleep(3)` with a call to `is_prime(n)`?

Before you run the code or read on, try figuring out the answers on your own.  Then, you
may want to copy and modify the `spinner_*.py` examples as suggested.

Now the answers, from easier to hardest.

**1. Answer for `multiprocessing`.**  The spinner is controlled by a child process, so it
continues spinning while the primality test is computed by the parent process.

**2. Answer for `threading`.**  The spinner is controlled by a secondary thread, so it
continues spinning while the primality test is computed by the main thread.

It's easy to get this one wrong by overestimating the impact of the GIL.  In this
particular example, the spinner keeps spinning because Python suspends the running thread
every 5ms (by default), making the GIL available to other pending threads.  Therefore, the
main thread running `is_prime` is interrupted every 5ms, allowing the secondary thread to
wake up and iterate once through the `for` loop, until it calls the `wait` method of the
`done` event, at which time it will release the GIL.  The main thread will then grab the
GIL, and the `is_prime` computation will proceed for another 5ms.

This does not have a visible impact on the running time of this specific example, because
the `spin` function quickly iterates once and releases the GIL as it waits for the `done`
event, so there is not much contention for the GIL.  The main thread running `is_prime`
will have the GIL most of the time.

We got away with a compute-intensive task using threading in this simple experiment
because there are only two threads: one hogging the CPU, and the other waking up only 10
times per second to update the spinner.  But if you have two or more threads vying for a
lot of CPU time, your program will be slower than sequential code.

**3. Answer for `asyncio`.**  If you call `is_prime(5_000_111_000_222_021)` in the `slow`
coroutine of the `spinner_async.py` example, the spinner will never appear.  The effect
would be the same we had when we replaced `await asyncio.sleep(3)` with `time.sleep(3)`:
no spinning at all.  The flow of control will pass from `supervisor` to `slow`, and then to
`is_prime`.  When `is_prime` returns, `slow` returns as well, and `supervisor` resumes,
cancelling the `spinner` task before it is executed even once.  The program appears frozen
for a few seconds, then shows the answer.

### Power Napping with `sleep(0)`

One way to keep the spinner alive is to rewrite `is_prime` as a coroutine, and
periodically call `asyncio.sleep(0)` in an `await` expression to yield control back to the
event loop:

<!-- nocheck -->
```python
async def is_prime(n):
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False

    root = math.isqrt(n)
    for i in range(3, root + 1, 2):
        if n % i == 0:
            return False
        if i % 100_000 == 1:
            await asyncio.sleep(0)  # sleep once every 50,000 iterations (the step is 2)
    return True
```

However, be aware this will slow down `is_prime`, and — more importantly — will still slow
down the event loop and your whole program with it.  When the author of *Fluent Python*
used `await asyncio.sleep(0)` every 100,000 iterations, the spinner was smooth but the
program ran almost 50% longer than the original `is_prime` function by itself with the
same argument.

Using `await asyncio.sleep(0)` should be considered a stopgap measure before you refactor
your asynchronous code to delegate CPU-intensive computations to another process.  We'll
see one way of doing that with `asyncio.loop.run_in_executor` in
[Asynchronous Programming](asyncio.md).  Another option would be a task queue, which we'll
briefly discuss in [Distributed Task Queues](#distributed-task-queues).

So far, we've only experimented with a single call to a CPU-intensive function.  The next
section presents concurrent execution of multiple CPU-intensive calls.

## A Homegrown Process Pool

> **Note**
>
> This section shows the use of multiple processes for CPU-intensive tasks, and the common
> pattern of using queues to distribute tasks and collect results.
> [Concurrent Executors](executors.md) will show a simpler way of distributing tasks to
> processes: a `ProcessPoolExecutor` from the `concurrent.futures` package, which uses
> queues internally.

In this section we'll write programs to compute the primality of a sample of 20 integers,
from 2 to 9,999,999,999,999,999 — i.e., 10<sup>16</sup> – 1, or more than 2<sup>53</sup>.
The sample includes small and large primes, as well as composite numbers with small and
large prime factors.  Here is `primes.py`, with the sample and the `is_prime` function:

```python
import math

NUMBERS = [
    2, 142702110479723, 299593572317531, 3333333333333301,
    3333333333333333, 3333335652092209, 4444444444444423,
    4444444444444444, 4444444488888889, 5555553133149889,
    5555555555555503, 5555555555555555, 6666666666666666,
    6666666666666719, 6666667141414921, 7777777536340681,
    7777777777777753, 7777777777777777, 9999999999999917,
    9999999999999999,
]

def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False

    root = math.isqrt(n)
    for i in range(3, root + 1, 2):
        if n % i == 0:
            return False
    return True
```

The `sequential.py` program provides the performance baseline.  Here is a sample run on
the 6-core laptop used for *Fluent Python*:

```console
$ python3 sequential.py
               2  P  0.000001s
 142702110479723  P  0.568328s
 299593572317531  P  0.796773s
3333333333333301  P  2.648625s
3333333333333333     0.000007s
3333335652092209     2.672323s
4444444444444423  P  3.052667s
4444444444444444     0.000001s
4444444488888889     3.061083s
5555553133149889     3.451833s
5555555555555503  P  3.556867s
5555555555555555     0.000007s
6666666666666666     0.000001s
6666666666666719  P  3.781064s
6666667141414921     3.778166s
7777777536340681     4.120069s
7777777777777753  P  4.141530s
7777777777777777     0.000007s
9999999999999917  P  4.678164s
9999999999999999     0.000007s
Total time: 40.31s
```

The results are shown in three columns: the number to be checked; `P` if it's a prime
number, blank if not; and the elapsed time for checking the primality for that specific
number.  In this example, the total time is approximately the sum of the times for each
check, but it is computed separately:

<!-- nocheck -->
```python
#!/usr/bin/env python3

"""
sequential.py: baseline for comparing sequential, multiprocessing,
and threading code for CPU-intensive work.
"""

from time import perf_counter
from typing import NamedTuple

from primes import is_prime, NUMBERS

class Result(NamedTuple):  # the boolean result of is_prime and the elapsed time
    prime: bool
    elapsed: float

def check(n: int) -> Result:  # check(n) calls is_prime(n) and computes the elapsed time
    t0 = perf_counter()
    prime = is_prime(n)
    return Result(prime, perf_counter() - t0)

def main() -> None:
    print(f'Checking {len(NUMBERS)} numbers sequentially:')
    t0 = perf_counter()
    for n in NUMBERS:  # for each number in the sample, call check and display the result
        prime, elapsed = check(n)
        label = 'P' if prime else ' '
        print(f'{n:16}  {label} {elapsed:9.6f}s')

    elapsed = perf_counter() - t0  # compute and display the total elapsed time
    print(f'Total time: {elapsed:.2f}s')

if __name__ == '__main__':
    main()
```

### Process-Based Solution

The next example, `procs.py`, shows the use of multiple processes to distribute the
primality checks across multiple CPU cores.  These are the times measured with `procs.py`
on the same machine:

```console
$ python3 procs.py
Checking 20 numbers with 12 processes:
               2  P  0.000002s
3333333333333333     0.000021s
4444444444444444     0.000002s
5555555555555555     0.000018s
6666666666666666     0.000002s
 142702110479723  P  1.350982s
7777777777777777     0.000009s
 299593572317531  P  1.981411s
9999999999999999     0.000008s
3333333333333301  P  6.328173s
3333335652092209     6.419249s
4444444488888889     7.051267s
4444444444444423  P  7.122004s
5555553133149889     7.412735s
5555555555555503  P  7.603327s
6666666666666719  P  7.934670s
6666667141414921     8.017599s
7777777536340681     8.339623s
7777777777777753  P  8.388859s
9999999999999917  P  8.117313s
20 checks in 9.58s
```

The last line of the output shows that `procs.py` was 4.2 times faster than
`sequential.py`.

#### Understanding the elapsed times

Note that the elapsed time in the first column is for checking that specific number.  For
example, `is_prime(7777777777777753)` took almost 8.4s to return `True`.  Meanwhile, other
processes were checking other numbers in parallel.

There were 20 numbers to check.  `procs.py` starts a number of worker processes equal to
the number of CPU cores, as determined by `multiprocessing.cpu_count()`.  The total time
in this case is much less than the sum of the elapsed time for the individual checks.
There is some overhead in spinning up processes and in inter-process communication, so
the end result is that the multiprocess version is only about 4.2 times faster than the
sequential.  That's good, but a little disappointing considering the code launches 12
processes to use all cores on that laptop.

> **Note**
>
> `multiprocessing.cpu_count()` returned 12 on that machine, a 6-core Intel i7, because of
> *hyperthreading*, an Intel technology which executes 2 threads per core.  However,
> hyperthreading works better when one of the threads is not working as hard as the other
> thread in the same core — perhaps the first is stalled waiting for data after a cache
> miss, and the other is crunching numbers.  There's no free lunch: that laptop performs
> like a 6-CPU machine for compute-intensive work that doesn't use a lot of memory — like
> that simple primality test.  (Since Python 3.13, `os.process_cpu_count()` reports the
> number of CPUs the *current process* is allowed to use, which may be fewer than
> `os.cpu_count()` in containers.)

#### Code for the multicore prime checker

When we delegate computing to threads or processes, our code does not call the worker
function directly, so we can't simply get a return value.  Instead, the worker is driven
by the thread or process library, and it eventually produces a result that needs to be
stored somewhere.  Coordinating workers and collecting results are common uses of queues
in concurrent programming — and also in distributed systems.  Much of the new code in
`procs.py` has to do with setting up and using queues.  Here is the top of the file:

<!-- nocheck -->
```python
import sys
from time import perf_counter
from typing import NamedTuple
from multiprocessing import Process, SimpleQueue, cpu_count
from multiprocessing import queues

from primes import is_prime, NUMBERS

class PrimeResult(NamedTuple):  # includes the number checked, to simplify reporting
    n: int
    prime: bool
    elapsed: float

type JobQueue = queues.SimpleQueue[int]  # numbers for the worker processes to check
type ResultQueue = queues.SimpleQueue[PrimeResult]  # results for main to collect

def check(n: int) -> PrimeResult:  # similar to sequential.py
    t0 = perf_counter()
    res = is_prime(n)
    return PrimeResult(n, res, perf_counter() - t0)

def worker(jobs: JobQueue, results: ResultQueue) -> None:
    while n := jobs.get():  # 0 is a poison pill: a signal for the worker to finish
        results.put(check(n))  # invoke the primality check and enqueue a PrimeResult
    results.put(PrimeResult(0, False, 0.0))  # let the main loop know this worker is done

def start_jobs(
    procs: int, jobs: JobQueue, results: ResultQueue  # procs: number of worker processes
) -> None:
    for n in NUMBERS:
        jobs.put(n)  # enqueue the numbers to be checked
    for _ in range(procs):
        proc = Process(target=worker, args=(jobs, results))  # a child process per worker
        proc.start()  # start each child process
        jobs.put(0)  # enqueue one 0 for each process, to terminate them
```

Trying to emulate `threading`, `multiprocessing` provides `multiprocessing.SimpleQueue`,
but this is a method bound to a predefined instance of a lower-level `BaseContext` class.
We must call this `SimpleQueue` to build a queue, but we can't use it in type hints.
`multiprocessing.queues` has the `SimpleQueue` class we need for type hints.

`PrimeResult` includes the number checked for primality.  Keeping `n` together with the
other result fields simplifies displaying results later.  `JobQueue` is a type alias for a
`SimpleQueue` that the `main` function will use to send numbers to the processes that will
do the work; `ResultQueue` is a type alias for a second `SimpleQueue` that will collect the
results in `main`.

`worker` gets a queue with the numbers to be checked, and another to put results.  In this
code, the number `0` is used as a *poison pill*: a signal for the worker to finish.  If
`n` is not `0`, the loop proceeds (note the `:=` assignment expression from
[Looping Techniques](datastructures.md#tut-loopidioms)).  `start_jobs` forks a child
process for each worker; each child runs the loop inside its own instance of the `worker`
function, until it fetches a `0` from the `jobs` queue.

> **Note**
>
> The `worker` function follows a common pattern in concurrent programming: looping
> indefinitely while taking items from a queue and processing each with a function that
> does the actual work.  The loop ends when the queue produces a sentinel value, often
> called a "poison pill".
>
> `None` is often used as a sentinel value, but it may be unsuitable if it can occur in the
> data stream.  Calling `object()` is a common way to get a unique value to use as
> sentinel.  However, that does not work across processes because Python objects must be
> serialized for inter-process communication, and when you `pickle.dump` and
> `pickle.load` an instance of `object`, the unpickled instance is distinct from the
> original: it doesn't compare equal.  A good alternative to `None` is the `Ellipsis`
> built-in object (a.k.a. `...`), which survives serialization without losing its
> identity.

```python
import pickle
sentinel = object()
pickle.loads(pickle.dumps(sentinel)) is sentinel
# False
pickle.loads(pickle.dumps(...)) is ...
# True
```

Now let's study the `main` function of `procs.py`:

<!-- nocheck -->
```python
def main() -> None:
    if len(sys.argv) < 2:  # if no argument is given, use the number of CPU cores
        procs = cpu_count()
    else:
        procs = int(sys.argv[1])

    print(f'Checking {len(NUMBERS)} numbers with {procs} processes:')
    t0 = perf_counter()
    jobs: JobQueue = SimpleQueue()  # the queues described above
    results: ResultQueue = SimpleQueue()
    start_jobs(procs, jobs, results)  # start procs processes to consume jobs and post results
    checked = report(procs, results)  # retrieve the results and display them
    elapsed = perf_counter() - t0
    print(f'{checked} checks in {elapsed:.2f}s')  # how many checks and the total time

def report(procs: int, results: ResultQueue) -> int:
    checked = 0
    procs_done = 0
    while procs_done < procs:  # loop until all processes are done
        n, prime, elapsed = results.get()  # .get() blocks until there is an item
        if n == 0:  # if n is zero, then one process exited
            procs_done += 1
        else:
            checked += 1  # otherwise, count the number checked and display the result
            label = 'P' if prime else ' '
            print(f'{n:16}  {label} {elapsed:9.6f}s')
    return checked

if __name__ == '__main__':
    main()
```

Calling `.get()` on a queue blocks until there is an item in the queue.  It's also possible
to make this nonblocking, or set a timeout; see the `SimpleQueue.get` documentation.  The
results will not come back in the same order the jobs were submitted.  That's why we put
`n` in each `PrimeResult` tuple.  Otherwise, there would be no way to know which result
belonged to each number.

If the main process exits before all subprocesses are done, you may see confusing
tracebacks on `FileNotFoundError` exceptions caused by an internal lock in
`multiprocessing`.  Debugging concurrent code is always hard, and debugging
`multiprocessing` is even harder because of all the complexity behind the thread-like
façade.  Fortunately, the `ProcessPoolExecutor` we'll meet in
[Concurrent Executors](executors.md) is easier to use and more robust.

> **Note**
>
> An early version of this example had a *race condition*: a bug that may or may not occur
> depending on the order of actions performed by concurrent execution units.  If "A"
> happens before "B", all is fine; but if "B" happens first, something goes wrong.  That's
> the race.

#### Experimenting with more or fewer processes

You may want to try running `procs.py`, passing arguments to set the number of worker
processes.  For example, `python3 procs.py 2` will launch two worker processes, producing
results almost twice as fast as `sequential.py` — if your machine has at least two cores
and is not too busy running other programs.

Running `procs.py` 12 times with each number of processes from 1 to 20, on that 6-core
laptop, the lowest median time was with 6 processes: 10.39s, against 40.81s with 1
process.  Run times increased after 6 processes due to CPU contention, reaching a local
maximum of 12.51s at 10 processes, and then stayed nearly flat up to 20 processes.

### Thread-Based Nonsolution

A version of `procs.py` using `threading` instead of `multiprocessing` is very similar — as
is usually the case when converting simple examples between these two APIs.  Due to the GIL
and the compute-intensive nature of `is_prime`, the threaded version is slower than the
sequential code, and it gets slower as the number of threads increases, because of CPU
contention and the cost of *context switching*.  To switch to a new thread, the OS needs
to save CPU registers and update the program counter and stack pointer, triggering
expensive side effects like invalidating CPU caches and possibly even swapping memory
pages.

> **Tip**
>
> Run the threaded version on a free-threaded build of Python 3.14 or later and the
> picture changes: the threads can then run `is_prime` on several cores at once, and the
> speedup approaches that of the process-based solution, without the cost of starting
> processes and serializing data.  Single-threaded code runs somewhat slower in the
> free-threaded build, so measure before you switch.

The next two chapters cover more about concurrent programming in Python, using the
high-level `concurrent.futures` library to manage threads and processes, and the `asyncio`
library for asynchronous programming.  The remaining sections in this chapter aim to
answer the question: given the limitations discussed so far, how is Python thriving in a
multicore world?

## Python in the Multicore World

Consider this citation from the widely quoted article
["The Free Lunch Is Over: A Fundamental Turn Toward Concurrency in Software"](http://www.gotw.ca/publications/concurrency-ddj.htm)
by Herb Sutter, from March 2005:

> The major processor manufacturers and architectures, from Intel and AMD to Sparc and
> PowerPC, have run out of room with most of their traditional approaches to boosting CPU
> performance.  Instead of driving clock speeds and straight-line instruction throughput
> ever higher, they are instead turning en masse to hyper-threading and multicore
> architectures.

What Sutter calls the "free lunch" was the trend of software getting faster with no
additional developer effort because CPUs were executing sequential code faster, year after
year.  Since 2004, that is no longer true: clock speeds and execution optimizations reached
a plateau, and now any significant increase in performance must come from leveraging
multiple cores or hyperthreading, advances that only benefit code that is written for
concurrent execution.

Python's story started in the early 1990s, when CPUs were still getting exponentially
faster at sequential code execution.  There was no talk about multicore CPUs except in
supercomputers back then.  At the time, the decision to have a GIL was a no-brainer.  The
GIL makes the interpreter faster when running on a single core, and its implementation
simpler.  The GIL also makes it easier to write simple extensions through the Python/C API.

> **Note**
>
> An extension does not need to deal with the GIL at all.  A function written in C or
> Fortran may be hundreds of times faster than the equivalent in Python.  Therefore the
> added complexity of releasing the GIL to leverage multicore CPUs may not be needed in
> many cases.  So we can thank the GIL for many extensions available for Python — and that
> is certainly one of the key reasons why the language is so popular today.

Despite the GIL, Python is thriving in applications that require concurrent or parallel
execution, thanks to libraries and software architectures that work around the
limitations of CPython.  Let's discuss how Python is used in system administration, data
science, and server-side application development.

### System Administration

Python is widely used to manage large fleets of servers, routers, load balancers and
network-attached storage (NAS).  It's also a leading option in software-defined networking
(SDN) and ethical hacking.  Major cloud service providers support Python through libraries
and tutorials authored by the providers themselves or by their large communities of Python
users.

In this domain, Python scripts automate configuration tasks by issuing commands to be
carried out by the remote machines, so rarely there are CPU-bound operations to be done.
Threads or coroutines are well suited for such jobs.  In particular, the
`concurrent.futures` package we'll see in [Concurrent Executors](executors.md) can be used
to perform the same operations on many remote machines at the same time without a lot of
complexity.  Beyond the standard library, there are popular Python-based projects to
manage server clusters: tools like Ansible and Salt, as well as libraries like Fabric.

### Data Science

Data science — including artificial intelligence — and scientific computing are very well
served by Python.  Applications in these fields are compute-intensive, but Python users
benefit from a vast ecosystem of numeric computing libraries written in C, C++, Fortran,
Cython, Rust, etc. — many of which are able to leverage multicore machines, GPUs and/or
distributed parallel computing in heterogeneous clusters.  Some examples:

**Project Jupyter**
: Two browser-based interfaces — Jupyter Notebook and JupyterLab — that allow users to run
  and document analytics code potentially running across the network on remote machines.
  Both are hybrid Python/JavaScript applications, supporting computing kernels written in
  different languages, all integrated via ZeroMQ — an asynchronous messaging library for
  distributed applications.  The name *Jupyter* comes from Julia, Python and R, the first
  three languages supported by the Notebook.

**PyTorch and TensorFlow**
: The leading deep learning frameworks.  Both are written mostly in C++, and are able to
  leverage multiple cores, GPUs and clusters.  They support other languages as well, but
  Python is their main focus and is used by the majority of their users.

**Dask**
: A parallel computing library that can farm out work to local processes or clusters of
  machines.  Dask offers APIs that closely emulate NumPy, pandas and scikit-learn, and
  includes an interactive dashboard showing the flow of data and computations across the
  processes and machines in near real time.

These are only some examples to illustrate how the data science community is creating
solutions that leverage the best of Python and overcome the limitations of the CPython
runtime.

### Server-Side Web/Mobile Development

Python is widely used in web applications and for the backend APIs supporting mobile
applications.  How is it that Google, YouTube, Dropbox, Instagram, Quora and Reddit —
among others — managed to build Python server-side applications serving hundreds of
millions of users 24x7?  Again, the answer goes way beyond what Python provides "out of
the box".

Before we discuss tools to support Python at scale, here is an admonition from the
Thoughtworks Technology Radar:

> **High performance envy/web scale envy**
>
> We see many teams run into trouble because they have chosen complex tools, frameworks
> or architectures because they "might need to scale".  Companies such as Twitter and
> Netflix need to support extreme loads and so need these architectures, but they also
> have extremely skilled development teams able to handle the complexity.  Most situations
> do not require these kinds of engineering feats; teams should keep their web scale envy
> in check in favor of simpler solutions that still get the job done.

At web scale, the key is an architecture that allows horizontal scaling.  At that point,
all systems are distributed systems, and no single programming language is likely to be
the right choice for every part of the solution.  Martin Kleppmann's *Designing
Data-Intensive Applications* (O'Reilly) is an accessible book on the subject, anchored on
solid research and practical experience.  Typical components of such systems, often
found in Python deployments, include:

* application caches: memcached, Redis, Varnish;
* relational databases: PostgreSQL, MySQL;
* document databases: Apache CouchDB, MongoDB;
* full-text indexes: Elasticsearch, Apache Solr;
* message queues: RabbitMQ, Redis.

There are other industrial-strength open source products in each of those categories.
Major cloud providers also offer their own proprietary alternatives.  For Python
server-side applications, two specific components are often deployed:

* An *application server* to distribute the load among several instances of the Python
  application, handling client requests before they reach the application code.
* A *task queue* built around a message queue, providing a higher-level, easier-to-use API
  to distribute tasks to processes running on other machines.

The next two sections explore these components.

### WSGI Application Servers

WSGI — the Web Server Gateway Interface — is a standard API for a Python framework or
application to receive requests from an HTTP server and send responses to it.  WSGI
application servers manage one or more processes running your application, maximizing the
use of the available CPUs: clients connect to an HTTP server that delivers static files
and routes other requests to the application server, which forks child processes to run
the application code, leveraging multiple CPU cores.

The best-known application servers in Python web projects are mod_wsgi (for users of the
Apache HTTP server), uWSGI, Gunicorn and NGINX Unit.  uWSGI and Gunicorn are often used with
the NGINX HTTP server.  uWSGI offers a lot of extra functionality, including an application
cache, a task queue and cron-like periodic tasks; on the flip side, it is much harder to
configure properly than Gunicorn.

The main point: all of these application servers can potentially use all CPU cores on the
server by forking multiple Python processes to run traditional web apps written in good
old sequential code in Django, Flask, Pyramid, etc.  This explains why it's been possible
to earn a living as a Python web developer without ever studying the `threading`,
`multiprocessing` or `asyncio` modules: the application server handles concurrency
transparently.

> **Note**
>
> WSGI is a synchronous API.  It doesn't support coroutines with `async`/`await` — the most
> efficient way to implement WebSockets or HTTP long polling in Python.  The ASGI
> (Asynchronous Server Gateway Interface) specification is a successor to WSGI, designed
> for asynchronous Python web frameworks such as FastAPI, Starlette, Sanic and aiohttp, as
> well as Django, which has added asynchronous functionality.  ASGI servers include
> Uvicorn, Hypercorn and Daphne.

Now let's turn to another way of bypassing the GIL to achieve higher performance with
server-side Python applications.

### Distributed Task Queues

When the application server delivers a request to one of the Python processes running your
code, your app needs to respond quickly: you want the process to be available to handle the
next request as soon as possible.  However, some requests demand actions that may take
longer — for example, sending email or generating a PDF.  That's the problem that
distributed task queues are designed to solve.

Celery and RQ are the best known open source task queues with Python APIs.  Cloud
providers also offer their own proprietary task queues.  These products wrap a message
queue and offer a high-level API for delegating tasks to workers, possibly running on
different machines.

> **Note**
>
> In the context of task queues, the words *producer* and *consumer* are used instead of
> traditional client/server terminology.  For example, a Django view handler produces job
> requests, which are put in the queue to be consumed by one or more PDF rendering
> processes.

Quoting directly from Celery's FAQ, here are some typical use cases:

> * Running something in the background.  For example, to finish the web request as soon
>   as possible, then update the users page incrementally.  This gives the user the
>   impression of good performance and "snappiness", even though the real work might
>   actually take some time.
> * Running something after the web request has finished.
> * Making sure something is done, by executing it asynchronously and using retries.
> * Scheduling periodic work.

Besides solving these immediate problems, task queues support horizontal scalability.
Producers and consumers are decoupled: a producer doesn't call a consumer, it puts a
request in a queue.  Consumers don't need to know anything about the producers.  Crucially,
you can easily add more workers to consume tasks as demand grows.  That's why Celery and RQ
are called distributed task queues.

Recall that our simple `procs.py` used two queues: one for job requests, the other for
collecting results.  The distributed architecture of Celery and RQ uses a similar pattern.
Both support using the Redis NoSQL database as a message queue and result storage.  Celery
also supports other message queues like RabbitMQ or Amazon SQS, as well as other databases
for result storage.

This wraps up our introduction to concurrency in Python.  The next two chapters will
continue this theme, focusing on the `concurrent.futures` and `asyncio` packages of the
standard library.

## Summary

After a bit of theory, this chapter presented the spinner scripts implemented in each of
Python's three native concurrency programming models:

* threads, with the `threading` package;
* processes, with `multiprocessing`;
* asynchronous coroutines with `asyncio`.

We then explored the real impact of the GIL with an experiment: changing the spinner
examples to compute the primality of a large integer and observe the resulting behavior.
This demonstrated graphically that CPU-intensive functions must be avoided in `asyncio`, as
they block the event loop.  The threaded version of the experiment worked — despite the GIL
— because Python periodically interrupts threads, and the example used only two threads:
one doing compute-intensive work, and the other driving the animation only 10 times per
second.  The `multiprocessing` variant worked around the GIL, starting a new process just
for the animation, while the main process did the primality check.

The next example, computing several primes, highlighted the difference between
`multiprocessing` and `threading`, proving that only processes allow (GIL-enabled) Python
to benefit from multicore CPUs.  Python's GIL makes threads worse than sequential code for
heavy computations.

The GIL dominates discussions about concurrent and parallel computing in Python, but we
should not overestimate its impact.  That was the point of
[Python in the Multicore World](#python-in-the-multicore-world).  For example, the GIL
doesn't affect many use cases of Python in system administration.  On the other hand, the
data science and server-side development communities have worked around the GIL with
industrial-strength solutions tailored to their specific needs.  The last two sections
mentioned two common elements to support Python server-side applications at scale: WSGI
application servers and distributed task queues.

> **Note**
>
> To manage complexity, we need constraints.  Structured programming took away arbitrary
> jumps; object-oriented programming added information hiding; functional programming adds
> immutability.  After we get used to these constraints, we see them as blessings: they
> make reasoning about the code much easier.  Lack of constraints is the main problem with
> the threads-and-locks model of concurrent programming: threads can share access to
> arbitrary, mutable data structures; the scheduler can interrupt a thread at almost any
> point, even in the middle of `a += 1`; and locks are only advisory — nothing prevents
> code that forgot to take a lock from corrupting data.  In contrast, the *actor model*
> used by Erlang and Elixir — where an actor cannot share state, communicates only by
> sending messages that hold copies of data, and handles one message at a time — imposes
> constraints that make concurrency much easier to reason about.

> **See also**
>
> * The [`threading`](https://docs.python.org/3/library/threading.html),
>   [`multiprocessing`](https://docs.python.org/3/library/multiprocessing.html) (including
>   its "Programming guidelines") and
>   [`concurrent.interpreters`](https://docs.python.org/3/library/concurrent.interpreters.html)
>   module documentation.
> * The [Python free-threading guide](https://docs.python.org/3/howto/free-threading-python.html)
>   and [**PEP 703**](https://peps.python.org/pep-0703/) — Making the Global Interpreter
>   Lock Optional in CPython.
> * Jim Anderson, "An Intro to Threading in Python", at Real Python; Caleb Hattingh, *Using
>   Asyncio in Python*, chapter 2, "The Truth About Threads".
> * *High Performance Python*, 2nd ed., by Micha Gorelick and Ian Ozsvald (O'Reilly).
> * David Beazley, "Understanding the Python GIL", and Anthony Shaw, *CPython Internals*.
> * Allen Downey, *The Little Book of Semaphores*, to learn the hard way how difficult it is
>   to reason about threads and locks.
> * Paul Butcher, *Seven Concurrency Models in Seven Weeks* (Pragmatic Bookshelf), and
>   Martin Kleppmann, *Designing Data-Intensive Applications* (O'Reilly).
> * Frank McSherry, Michael Isard and Derek G. Murray, "Scalability! But at what COST?",
>   which found parallel systems needing hundreds of cores to outperform a "competent
>   single-threaded implementation".
