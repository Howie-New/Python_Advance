## 1. 什么是 asyncio？

- **适用场景**：`asyncio` 并不是多线程或多进程，它本质上是**单进程、单线程**的程序 []。它不能提升纯计算任务的速度，而是专门用于处理需要**等待**的任务（I/O 密集型），最典型的就是网络通讯 []。
- **核心机制 (Event Loop)**：
  - Event Loop 就像一个大脑，面对众多可执行的任务，决定执行哪一个 []。
  - 在 Python 的 `asyncio` 中，**同一时刻只有一个任务在运行**。
  - 任务必须**主动**告诉 Event Loop “我这边结束了（或我在等待）”，Event Loop 才会切换到下一个任务。因此不存在线程竞争冒险（Race Condition）的问题 []。

## 2. 核心概念：Coroutine (协程) 与 Task (任务)

### Coroutine (协程) []

- **Coroutine Function**: 使用 `async def` 定义的函数。
- **Coroutine Object**: 调用 Coroutine Function 时返回的对象。
  - **重要特性**：调用协程函数**不会**立即运行其中的代码，而是返回一个协程对象（类似于生成器） []。
  - 必须将协程对象放入 Event Loop 中才能执行。

### Task (任务)

- **定义**：是 Event Loop 中排队执行的基本单位。
- **关系**：Coroutine 必须被包装成 Task 才能被 Event Loop 调度执行 []。

## 3. 如何运行 asyncio 代码

### 入口函数：`asyncio.run()` []

- 用于从同步模式（Synchronous）切换到异步模式（Asynchronous）。
- **作用**：
  1. 建立 Event Loop。
  2. 将传入的协程变成 Loop 中的第一个 Task 并开始运行。
  3. 代码示例：`asyncio.run(main())`。

### 运行机制 1：直接使用 `await` []

- 当在协程内部 `await` 另一个协程时：
  1. 该协程被包装成 Task 并注册到 Event Loop。
  2. **暂停当前任务**，告诉 Loop "我要等这个新任务完成才能继续"。
  3. **交出控制权 (Yield)**，Loop 转而去运行那个新任务 []。
  4. 任务完成后，提取返回值。
- **缺点**：如果是连续 `await` 多个任务，它们是**串行**执行的（一个接一个等），无法利用并发优势 []。

### 运行机制 2：`asyncio.create_task()` []

- **并发的关键**：
  - 参数是一个协程对象。
  - 作用：将协程立即包装成 Task 并注册到 Loop 中，告诉 Loop "这个任务可以运行了"。
  - **非阻塞**：它不会像 `await` 那样立刻交出控制权，主程序会继续往下走。
- **实现并发**：先用 `create_task` 创建多个任务，再统一 `await` 它们。这样在等待 Task 1 的时候，Loop 发现 Task 2 也在排队且准备好了，就会去运行 Task 2，从而实现同时等待 []。

### 运行机制 3：`asyncio.gather()` []

- **更优雅的并发写法**：
  - 参数是若干个 Coroutine 或 Task。
  - 如果传入的是 Coroutine，它会自动将其包装成 Task 放入 Loop。
  - 返回一个 `Future`，`await` 这个 `Future` 会等待所有传入的任务完成。
  - **返回值**：返回一个列表，包含所有任务的运行结果，顺序与传入顺序一致 []。
  - 代码示例：`results = await asyncio.gather(task1(), task2())`。

## 4. 关键总结与注意事项 []

- **控制权交接**：Event Loop 无法强行打断一个任务，必须由任务**显式**交还控制权。
  - 交还方式：1. `await`；2. 函数运行完毕。
  - **警告**：如果在 Task 中写了死循环（且没有 await），整个 Event Loop 就会卡死 []。
- **并发的本质**：代码并不是真正同时在 CPU 上跑，而是利用了**等待时间**（如 sleep, 网络请求）。如果代码中没有等待操作，协程没有任何帮助。
- **获取返回值**：想要拿到协程的返回值，必须使用 `await`（例如 `val = await task`）[]。

## 5. video cource link:

https://youtu.be/YCVQPL8bxqY?si=KVd0q2cyODjr834

https://youtu.be/brYsDi-JajI?si=IpEJC8j3PSw14z11