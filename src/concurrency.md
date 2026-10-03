# Concurrency

> Concurrency is about dealing with lots of things at once.
> Parallelism is about doing lots of things at once.
> Not the same, but related.
> One is about structure, one is about execution.
>
> — Rob Pike, co-inventor of the Go language

The chapters in this part are about how to make Python deal with "lots of things at
once".  You already met one standard library tool for that in
[Multi-threading](stdlib2.md#tut-multi-threading), in the second tour of the standard
library.  Here we go much further:

* [Concurrency Models in Python](concurrency-models.md) introduces the jargon and
  compares Python's three native approaches — threads, processes and coroutines — with
  the same small "spinner" program written three ways.  It explains the real impact of
  the Global Interpreter Lock (GIL), builds a homegrown process pool with queues, and
  surveys how Python thrives in a multicore world anyway.
* [Concurrent Executors](executors.md) shows the `concurrent.futures` package, the
  easiest way to run many independent jobs on a pool of threads or processes, through
  the example of downloading many files over the network.
* [Asynchronous Programming](asyncio.md) covers native coroutines, `async def` and
  `await`, the `asyncio` package, asynchronous context managers and iterators, and
  asynchronous generators.

Parallelism is a special case of concurrency.  All parallel systems are concurrent, but
not all concurrent systems are parallel.  A laptop with a handful of CPU cores routinely
runs hundreds of processes at the same time.  To execute 200 tasks in parallel, you'd
need 200 cores.  So, in practice, most computing is concurrent and not parallel: the
operating system manages hundreds of processes, making sure each has an opportunity to
make progress, even if the CPU itself can't do more than a few things at once.

These chapters assume no prior knowledge of concurrent or parallel programming.

> **Note**
>
> Python's concurrency story has been changing quickly.  Python 3.13 introduced an
> experimental *free-threaded* build of CPython, without the GIL
> ([**PEP 703**](https://peps.python.org/pep-0703/)), and Python 3.14 made it an
> officially supported, optional build ([**PEP 779**](https://peps.python.org/pep-0779/)).
> Python 3.14 also added the `concurrent.interpreters` module, for running multiple
> isolated interpreters in one process ([**PEP 734**](https://peps.python.org/pep-0734/)).
> The chapters in this part explain the classic models first, because they are still the
> default and they are the foundation for everything else, and then point out where
> these newer options fit.
