视频总结：Python await 机制详解
视频来源:  https://youtu.be/K0BjgYZbgfE?si=7Ii-D-38bO-Z2mol 作者: 码农高天

1. 纠正误区：await vs Task [00:48]
误区：很多人认为 await 一个 Coroutine 会自动将其变成一个 Task。

真相：

await 一个 Coroutine 不会自动创建 Task。

它实际上像调用一个生成器（Generator）一样，同步地运行该 Coroutine 中的步骤，直到遇到无法继续的阻碍（如 IO 操作）[00:59]。

验证：

直接 await asyncio.sleep(1)：在主线程调用栈中直接运行，没有创建新 Task [01:25]。

asyncio.create_task() 后 await：确实创建了新 Task 并注册到 Event Loop，主函数交还控制权，Event Loop 在稍后调度新 Task [01:45]。

2. Event Loop 的调度单位 [02:55]
Event Loop 调度的最小单位永远是 Task。

Event Loop 无法直接执行一个 Coroutine，它必须被包装在 Task 中。

即使是直接 await Coroutine 的情况，顶层依然有一个 Task（例如 asyncio.run 创建的主 Task）在运行这些代码 [03:03]。

3. await 的底层实现原理 (Bytecode 层面) [03:30]
await 的核心 Bytecode 指令：GET_AWAITABLE 和 YIELD_FROM。

YIELD_FROM:

本质上是 Python 生成器的机制。

如果生成器（Coroutine）return 了（或抛出 StopIteration），返回值会被保存在 StopIteration 异常的 value 属性中，代表该步骤完成 [05:19]。

如果生成器 yield 了一个值（通常是 None 或另一个 Future），说明它暂停了。此时解释器会保存当前函数栈帧（Frame）的状态（Program Counter 指针回退），以便下次恢复运行时能接着跑 [06:52]。

4. 依赖与唤醒机制：Task 是如何“等待”的？ [07:53]
await 后面只能跟三种东西：Coroutine, Task, Future。

Task 等待的本质：

当一个 Task (Task A) 执行到 await future_B 时，如果 future_B 还没完成：

Task A 会调用 future_B.add_done_callback(Task_A.wakeup) [11:22]。

意思是告诉 future_B：“等你做完了，记得叫醒我”。

然后 Task A 就会 yield 出去，从 Event Loop 的就绪列表中消失，进入“休眠”状态 [12:08]。

Event Loop 转而去执行其他任务。

唤醒流程：

当 future_B 完成（set_result），它会检查身上的 callbacks 列表。

它发现 Task A 的唤醒回调，于是通过 loop.call_soon 之类的方法，告诉 Event Loop：“Task A 准备好了，可以继续跑了” [13:13]。

Event Loop 在下一轮循环中重新调度 Task A。

5. 为什么要用 call_soon 而不是直接运行 Callback？ [13:36]
在唤醒时，Python 不会立即原地执行唤醒的回调函数，而是将其调度到 Loop 中，原因有二：

Context (上下文) 隔离：不同的 Task 运行在不同的 Context 下（变量环境不同），需要分开运行 [13:41]。

公平性：如果直接递归运行 Callback，可能会导致嵌套过深或长时间占用，饿死其他已经在排队的任务。让 Loop 统一调度能保证每个任务都有公平的执行机会（低延迟）[13:58]。

核心逻辑图解：

运行中：Task A 运行 -> 遇到 await Task B。

挂起：Task B 没做完 -> Task A 把自己注册到 Task B 的回调里 -> Task A 暂停 (Yield)，移出 Loop 运行列表。

完成：Task B 做完了 -> 触发回调 -> 告诉 Loop "Task A 可以跑了"。

恢复：Loop 在下一轮循环中捡起 Task A -> Task A 从暂停处继续运行。