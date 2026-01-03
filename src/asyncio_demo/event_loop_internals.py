"""
Event Loop 内部机制可视化
深入理解 Event Loop 如何调度 Task 和处理 await

主题：
1. Event Loop 的运行机制
2. Ready Queue 和 Scheduled Queue
3. Task 的状态转换
4. await 触发的调度过程
5. 模拟 Event Loop 的简化实现
"""

import asyncio
import time
from collections import deque
from typing import Optional, Coroutine, Any


# ============================================================================
# Demo 1: 监控 Event Loop 的状态
# ============================================================================
print("=" * 80)
print("Demo 1: Event Loop 的基本信息")
print("=" * 80)


async def demo1_loop_info():
    """获取 Event Loop 的基本信息"""
    loop = asyncio.get_running_loop()

    print(f"\nEvent Loop 信息:")
    print(f"  类型: {type(loop).__name__}")
    print(f"  是否运行中: {loop.is_running()}")
    print(f"  是否已关闭: {loop.is_closed()}")

    # 获取当前 Task
    current_task = asyncio.current_task()
    print(f"\n当前 Task:")
    print(f"  名称: {current_task.get_name()}")
    print(f"  状态: {'完成' if current_task.done() else '运行中'}")

    # 创建几个 Task
    async def sample_task(name: str, delay: float):
        await asyncio.sleep(delay)
        return f"{name} done"

    task1 = asyncio.create_task(sample_task("Task1", 0.1), name="Task1")
    task2 = asyncio.create_task(sample_task("Task2", 0.2), name="Task2")

    # 获取所有 Task
    all_tasks = asyncio.all_tasks()
    print(f"\n所有 Task 数量: {len(all_tasks)}")
    for task in all_tasks:
        print(f"  - {task.get_name()}: {'完成' if task.done() else '运行中'}")

    await asyncio.gather(task1, task2)

    print("\n总结:")
    print("  - Event Loop 是单线程的")
    print("  - 所有 Task 都在同一个 Loop 中调度")
    print("  - 可以随时查看所有 Task 的状态")


# ============================================================================
# Demo 2: call_soon 和 call_later
# ============================================================================
print("\n" + "=" * 80)
print("Demo 2: call_soon 和调度机制")
print("=" * 80)


async def demo2_call_soon():
    """演示 call_soon 的调度机制"""
    loop = asyncio.get_running_loop()
    execution_order = []

    def callback(name: str):
        execution_order.append(name)
        print(f"  [回调] {name} 执行")

    print("\n使用 call_soon 调度回调:")

    # 注册多个回调
    loop.call_soon(callback, "回调1")
    loop.call_soon(callback, "回调2")
    loop.call_soon(callback, "回调3")

    print("  已注册 3 个回调到 Ready Queue")
    print("  等待下一个 Event Loop 循环...")

    # 让出控制权，让 Event Loop 执行回调
    await asyncio.sleep(0)

    print(f"  执行顺序: {' -> '.join(execution_order)}")

    print("\n使用 call_later 延迟调度:")
    execution_order.clear()

    loop.call_later(0.2, callback, "延迟回调1")
    loop.call_later(0.1, callback, "延迟回调2")
    loop.call_later(0.3, callback, "延迟回调3")

    print("  已注册 3 个延迟回调到 Scheduled Queue")
    await asyncio.sleep(0.35)

    print(f"  执行顺序: {' -> '.join(execution_order)}")

    print("\n总结:")
    print("  - call_soon: 加入 Ready Queue，下一轮循环立即执行")
    print("  - call_later: 加入 Scheduled Queue，到时间后移到 Ready Queue")
    print("  - 这就是 Future 回调的调度方式")


# ============================================================================
# Demo 3: Task 的生命周期可视化
# ============================================================================
print("\n" + "=" * 80)
print("Demo 3: Task 的完整生命周期")
print("=" * 80)


async def demo3_task_lifecycle():
    """可视化 Task 的状态转换"""

    def print_task_state(task: asyncio.Task, label: str):
        """打印 Task 状态"""
        states = []
        if task.done():
            states.append("✓ 完成")
        else:
            states.append("⏳ 未完成")
        if task.cancelled():
            states.append("✗ 已取消")
        print(f"  [{label}] {' | '.join(states)}")

    async def monitored_task():
        """被监控的任务"""
        print("    → Task 开始执行")
        await asyncio.sleep(0.1)
        print("    → Task 第一次暂停后恢复")
        await asyncio.sleep(0.1)
        print("    → Task 第二次暂停后恢复")
        return "完成"

    print("\nTask 状态转换过程:\n")

    # 1. 创建
    print("步骤1: 创建 Task")
    task = asyncio.create_task(monitored_task())
    print_task_state(task, "创建后")

    # 2. 运行中
    print("\n步骤2: Task 开始运行")
    await asyncio.sleep(0.05)
    print_task_state(task, "运行中")

    # 3. 完成
    print("\n步骤3: Task 完成")
    result = await task
    print_task_state(task, "完成后")
    print(f"  结果: {result}")

    # 4. 取消
    print("\n步骤4: 演示取消 Task")
    task2 = asyncio.create_task(monitored_task())
    await asyncio.sleep(0.05)
    print("  发起取消...")
    task2.cancel()
    try:
        await task2
    except asyncio.CancelledError:
        print("  捕获到 CancelledError")
    print_task_state(task2, "取消后")

    print("\n状态图:")
    print("  创建 → 运行中 → 暂停(await) → 运行中 → 完成")
    print("                    ↓")
    print("                  取消")


# ============================================================================
# Demo 4: 模拟简化版的 Event Loop
# ============================================================================
print("\n" + "=" * 80)
print("Demo 4: 简化版 Event Loop 实现")
print("=" * 80)


class SimpleEventLoop:
    """简化版的 Event Loop 实现，用于理解原理"""

    def __init__(self):
        self.ready_queue = deque()  # 就绪队列
        self.current_task = None

    def create_task(self, coro: Coroutine) -> "SimpleTask":
        """创建任务"""
        task = SimpleTask(coro, self)
        self.ready_queue.append(task)
        print(f"  [Loop] 创建 Task，加入 Ready Queue")
        return task

    def call_soon(self, callback):
        """调度回调"""
        self.ready_queue.append(callback)

    def run_until_complete(self, coro: Coroutine):
        """运行直到完成"""
        main_task = self.create_task(coro)

        print("\n  [Loop] 开始 Event Loop\n")
        while self.ready_queue or not main_task.done:
            if not self.ready_queue:
                print("  [Loop] Ready Queue 为空，等待...")
                break

            # 从队列取出一个可执行项
            item = self.ready_queue.popleft()

            if isinstance(item, SimpleTask):
                self.current_task = item
                print(f"  [Loop] 调度 {item.name}")
                item.step()
            else:
                # 执行回调
                item()

        print("\n  [Loop] Event Loop 结束")
        return main_task.result if main_task.done else None


class SimpleTask:
    """简化版的 Task"""

    _counter = 0

    def __init__(self, coro: Coroutine, loop: SimpleEventLoop):
        self.coro = coro
        self.loop = loop
        self.done = False
        self.result = None
        SimpleTask._counter += 1
        self.name = f"Task-{SimpleTask._counter}"

    def step(self):
        """执行一步"""
        try:
            # 驱动协程执行
            print(f"    [{self.name}] 执行中...")
            future = self.coro.send(None)

            if future:
                # 如果 yield 了一个 Future，注册回调
                print(f"    [{self.name}] yield Future，注册回调")

                def wakeup():
                    print(f"    [{self.name}] 被唤醒，重新加入 Ready Queue")
                    self.loop.ready_queue.append(self)

                future.add_callback(wakeup)
            else:
                # 没有 yield，继续执行
                print(f"    [{self.name}] 继续执行，重新加入 Ready Queue")
                self.loop.ready_queue.append(self)

        except StopIteration as e:
            # 协程完成
            print(f"    [{self.name}] 完成，结果: {e.value}")
            self.done = True
            self.result = e.value


class SimpleFuture:
    """简化版的 Future"""

    def __init__(self, loop: SimpleEventLoop):
        self.loop = loop
        self._done = False
        self._result = None
        self._callbacks = []

    def add_callback(self, callback):
        """添加回调"""
        if self._done:
            self.loop.call_soon(callback)
        else:
            self._callbacks.append(callback)

    def set_result(self, result):
        """设置结果"""
        self._result = result
        self._done = True
        for callback in self._callbacks:
            self.loop.call_soon(callback)


def demo4_simple_loop():
    """演示简化版 Event Loop"""
    print("\n模拟 Event Loop 的工作流程:\n")

    loop = SimpleEventLoop()

    # 创建一个 Future
    future = SimpleFuture(loop)

    def simple_coro():
        """简单的协程"""
        print("    [Coro] 步骤1: 开始执行")
        yield future  # 暂停，等待 future
        print("    [Coro] 步骤2: 恢复执行")
        yield None  # 再次让步
        print("    [Coro] 步骤3: 完成")
        return "最终结果"

    # 创建任务
    task = loop.create_task(simple_coro())

    # 模拟异步设置 Future 结果
    def set_future_result():
        print("  [外部] 设置 Future 结果")
        future.set_result("Future 的值")

    # 延迟设置结果（模拟异步操作完成）
    loop.call_soon(lambda: None)  # 第一轮循环
    loop.call_soon(set_future_result)  # 第二轮循环设置结果

    # 运行
    result = loop.run_until_complete(simple_coro())

    print(f"\n最终结果: {result}")

    print("\n这个简化实现展示了:")
    print("  1. Ready Queue 存放就绪的 Task")
    print("  2. Task yield Future 时暂停，注册回调")
    print("  3. Future 完成时，通过回调唤醒 Task")
    print("  4. Loop 不断从队列取 Task 执行")


# ============================================================================
# Demo 5: 深入理解 await 的调度过程
# ============================================================================
print("\n" + "=" * 80)
print("Demo 5: await 触发的完整调度过程")
print("=" * 80)


async def demo5_await_scheduling():
    """详细展示 await 时发生的事情"""
    print("\n详细流程: await task 时发生了什么\n")

    loop = asyncio.get_running_loop()
    events = []

    async def target_task():
        """被 await 的目标任务"""
        events.append("1. target_task 开始执行")
        await asyncio.sleep(0.1)
        events.append("4. target_task IO 完成，恢复执行")
        return "结果"

    async def waiter_task():
        """执行 await 的任务"""
        events.append("0. waiter_task 开始执行")

        # 创建 Task（此时已在 Ready Queue）
        task = asyncio.create_task(target_task())
        events.append("2. waiter_task 创建了 target_task")

        # await task（关键时刻）
        events.append("3. waiter_task 准备 await task")
        result = await task
        events.append("5. waiter_task 被唤醒，收到结果")

        return result

    result = await waiter_task()

    print("事件序列:")
    for event in events:
        print(f"  {event}")

    print(f"\n最终结果: {result}")

    print("\n详细解释:")
    print("  步骤0: waiter_task 在主 Task 中开始执行")
    print("  步骤1: target_task 创建并被 Loop 调度")
    print("  步骤2: waiter_task 记录创建事件")
    print("  步骤3: waiter_task await task 时:")
    print("    - 检查 task 是否完成")
    print("    - 未完成则调用 task.add_done_callback(waiter.wakeup)")
    print("    - waiter_task yield，从 Ready Queue 移除")
    print("  步骤4: target_task 完成:")
    print("    - 调用所有 callbacks")
    print("    - 通过 loop.call_soon 唤醒 waiter_task")
    print("  步骤5: waiter_task 恢复:")
    print("    - 从 await 处继续执行")
    print("    - 获取 task 的结果")


# ============================================================================
# Demo 6: CPU 密集型任务的影响
# ============================================================================
print("\n" + "=" * 80)
print("Demo 6: CPU 密集型任务对 Event Loop 的影响")
print("=" * 80)


async def demo6_cpu_blocking():
    """演示 CPU 密集型任务会阻塞 Event Loop"""
    print("\n演示: CPU 密集型任务的影响\n")

    async def io_task():
        """IO 密集型任务（正确）"""
        print("  [IO Task] 开始")
        await asyncio.sleep(1)
        print("  [IO Task] 完成")

    def cpu_intensive():
        """CPU 密集型计算"""
        total = 0
        for i in range(10_000_000):
            total += i
        return total

    # 场景1: 混合 IO 和 CPU 任务
    print("场景1: 阻塞式 CPU 任务（错误）")

    task1 = asyncio.create_task(io_task())

    print("  [Main] 开始 CPU 密集型计算...")
    start = time.time()
    result = cpu_intensive()  # 这会阻塞 Event Loop！
    cpu_time = time.time() - start
    print(f"  [Main] CPU 计算完成，耗时: {cpu_time:.2f}秒")

    await task1
    print(f"  ✗ 问题: CPU 任务阻塞了 Event Loop，IO 任务无法并发执行")

    # 场景2: 使用 run_in_executor 避免阻塞
    print("\n场景2: 使用 run_in_executor（正确）")

    task2 = asyncio.create_task(io_task())

    loop = asyncio.get_running_loop()
    print("  [Main] 在线程池中执行 CPU 任务...")
    start = time.time()

    # 在线程池中执行 CPU 密集型任务
    cpu_result = await loop.run_in_executor(None, cpu_intensive)
    cpu_time = time.time() - start

    print(f"  [Main] CPU 计算完成，耗时: {cpu_time:.2f}秒")

    await task2
    print(f"  ✓ 正确: CPU 任务在线程池执行，不阻塞 Event Loop")

    print("\n总结:")
    print("  - Event Loop 是单线程的")
    print("  - CPU 密集型任务会阻塞整个 Loop")
    print("  - 使用 run_in_executor 在线程池中执行 CPU 任务")
    print("  - 这样可以保持 Event Loop 的响应性")


# ============================================================================
# 主函数
# ============================================================================
async def main():
    """运行所有演示"""

    # Demo 1: Loop 基本信息
    await demo1_loop_info()

    # Demo 2: call_soon
    await demo2_call_soon()

    # Demo 3: Task 生命周期
    await demo3_task_lifecycle()

    # Demo 4: 简化版 Loop
    demo4_simple_loop()

    # Demo 5: await 调度
    await demo5_await_scheduling()

    # Demo 6: CPU 阻塞
    await demo6_cpu_blocking()

    print("\n" + "=" * 80)
    print("Event Loop 内部机制演示完成！")
    print("=" * 80)

    print("\n核心概念:")
    print("  1. Event Loop 维护 Ready Queue 和 Scheduled Queue")
    print("  2. Task yield 时暂停，移出 Ready Queue")
    print("  3. Future 完成时通过 call_soon 唤醒等待的 Task")
    print("  4. Loop 不断从队列取 Task 执行（单线程）")
    print("  5. CPU 密集型任务应该放到线程池")
    print("  6. 这就是 asyncio 的核心运行机制！")


if __name__ == "__main__":
    asyncio.run(main())
