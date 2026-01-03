"""
await 原理深度解析 Demo
基于 await_detail.md 的学习笔记

核心概念：
1. await coroutine 不会自动创建 Task，只是同步执行直到遇到阻塞
2. Event Loop 只调度 Task，不调度 Coroutine
3. await 底层使用 YIELD_FROM 机制（生成器）
4. Task 通过回调机制实现依赖和唤醒
5. call_soon 保证上下文隔离和调度公平性
"""

import asyncio
import sys
from typing import Any


# ============================================================================
# Demo 1: await coroutine vs await task 的区别
# ============================================================================
print("=" * 80)
print("Demo 1: await coroutine vs await Task 的本质区别")
print("=" * 80)


async def worker(name: str, delay: float) -> str:
    """一个简单的工作协程"""
    print(f"  [{name}] 开始工作")
    await asyncio.sleep(delay)
    print(f"  [{name}] 工作完成")
    return f"{name} 的结果"


async def demo1_direct_await():
    """直接 await coroutine - 同步执行，不创建新 Task"""
    print("\n方式1: 直接 await coroutine (同步执行)")
    print("执行顺序: main -> worker1 -> worker2 (串行)")

    result1 = await worker("worker1", 1)
    print(f"  收到结果: {result1}")

    result2 = await worker("worker2", 1)
    print(f"  收到结果: {result2}")

    print("  总结: 两个 worker 串行执行，总耗时 2 秒+")


async def demo1_create_task():
    """使用 create_task 创建 Task - 并发执行"""
    print("\n方式2: 使用 asyncio.create_task() 创建 Task (并发执行)")
    print("执行顺序: main 创建两个 Task -> Event Loop 并发调度")

    # 创建 Task 立即返回，不等待完成
    task1 = asyncio.create_task(worker("task1", 1))
    task2 = asyncio.create_task(worker("task2", 1))

    print("  两个 Task 已创建并提交给 Event Loop")

    # 等待两个 Task 完成
    result1 = await task1
    result2 = await task2

    print(f"  收到结果: {result1}, {result2}")
    print("  总结: 两个 Task 并发执行，总耗时 1 秒+")


# ============================================================================
# Demo 2: 回调机制 - Task 如何通过 Future 的回调实现唤醒
# ============================================================================
print("\n" + "=" * 80)
print("Demo 2: Task 的依赖与唤醒机制")
print("=" * 80)


async def demo2_callback_mechanism():
    """演示 Task 通过回调机制实现依赖和唤醒"""
    print("\n演示: Task A 等待 Future B，通过回调唤醒")

    loop = asyncio.get_event_loop()

    # 创建一个 Future 对象
    future = asyncio.Future()

    # 定义一个回调函数
    def on_future_done(fut):
        print(f"  [回调] Future 完成了！结果是: {fut.result()}")
        print(f"  [回调] 现在会通过 loop.call_soon 唤醒等待的 Task")

    # 手动添加回调（模拟 Task 的 add_done_callback）
    future.add_done_callback(on_future_done)

    # 创建一个等待 Future 的协程
    async def waiter():
        print("  [Waiter] 开始等待 Future...")
        print("  [Waiter] 此时会 yield 出去，进入休眠状态")
        result = await future  # 这里会 yield，等待 future 完成
        print(f"  [Waiter] 被唤醒了！收到结果: {result}")
        return result

    # 创建 Task
    task = asyncio.create_task(waiter())

    # 模拟一段时间后完成 Future
    async def complete_future():
        await asyncio.sleep(1)
        print("  [Completer] 1秒后，设置 Future 的结果")
        future.set_result("Future 的结果")  # 这会触发回调

    await complete_future()
    result = await task

    print(f"\n总结:")
    print(f"  1. Waiter Task await future 时，调用 future.add_done_callback(wakeup)")
    print(f"  2. Waiter Task yield 出去，从 Event Loop 就绪列表移除")
    print(f"  3. Future 完成时，触发回调，通过 loop.call_soon 唤醒 Waiter")
    print(f"  4. Event Loop 在下一轮循环重新调度 Waiter Task")


# ============================================================================
# Demo 3: YIELD_FROM 机制 - await 的底层实现
# ============================================================================
print("\n" + "=" * 80)
print("Demo 3: YIELD_FROM 机制 - 生成器的暂停与恢复")
print("=" * 80)


async def demo3_yield_mechanism():
    """演示 await 的 YIELD_FROM 机制"""
    print("\n演示: await 如何暂停和恢复执行")

    async def step_by_step():
        print("  [步骤1] 开始执行")

        print("  [步骤2] 准备 await sleep(1)，即将 yield")
        await asyncio.sleep(1)  # yield None，保存栈帧状态
        print("  [步骤2] 从 yield 恢复，继续执行")

        print("  [步骤3] 再次 await sleep(1)，再次 yield")
        await asyncio.sleep(1)
        print("  [步骤3] 再次恢复")

        print("  [步骤4] 完成，return 结果")
        return "最终结果"

    print("开始执行协程...")
    result = await step_by_step()
    print(f"收到返回值: {result}")

    print("\n总结:")
    print("  - 每次 await 都对应一个 YIELD_FROM 操作")
    print("  - yield 时保存当前栈帧（Program Counter 回退）")
    print("  - 恢复时从暂停处继续执行")
    print("  - return 值包装在 StopIteration.value 中")


# ============================================================================
# Demo 4: 调度公平性 - 为什么使用 call_soon 而不是直接执行回调
# ============================================================================
print("\n" + "=" * 80)
print("Demo 4: call_soon 保证调度公平性")
print("=" * 80)


async def demo4_fairness():
    """演示为什么需要 call_soon 而不是直接执行回调"""
    print("\n演示: 多个 Task 的公平调度")

    execution_order = []

    async def task_a():
        execution_order.append("Task A 开始")
        print("  [Task A] 开始执行")
        await asyncio.sleep(0.1)  # 短暂暂停
        execution_order.append("Task A 恢复")
        print("  [Task A] 恢复执行")
        return "A"

    async def task_b():
        execution_order.append("Task B 开始")
        print("  [Task B] 开始执行")
        await asyncio.sleep(0.1)
        execution_order.append("Task B 恢复")
        print("  [Task B] 恢复执行")
        return "B"

    async def task_c():
        execution_order.append("Task C 开始")
        print("  [Task C] 开始执行")
        await asyncio.sleep(0.1)
        execution_order.append("Task C 恢复")
        print("  [Task C] 恢复执行")
        return "C"

    # 创建多个 Task
    tasks = [
        asyncio.create_task(task_a()),
        asyncio.create_task(task_b()),
        asyncio.create_task(task_c()),
    ]

    # 等待所有 Task 完成
    results = await asyncio.gather(*tasks)

    print(f"\n执行顺序: {' -> '.join(execution_order)}")
    print(f"\n总结:")
    print(f"  - Event Loop 使用 call_soon 将就绪的 Task 加入队列")
    print(f"  - 保证每个 Task 都有公平的执行机会")
    print(f"  - 避免某个 Task 长时间占用 CPU，饿死其他 Task")
    print(f"  - 保持低延迟，响应更及时")


# ============================================================================
# Demo 5: 完整流程演示 - Task 的生命周期
# ============================================================================
print("\n" + "=" * 80)
print("Demo 5: Task 的完整生命周期")
print("=" * 80)


async def demo5_task_lifecycle():
    """演示 Task 的完整生命周期：创建 -> 运行 -> 挂起 -> 唤醒 -> 完成"""
    print("\n演示: Task 从创建到完成的完整流程")

    async def dependent_task():
        print("  [Dependent] 1. Task 创建并开始运行")
        print("  [Dependent] 2. 执行到 await，遇到未完成的 Future")

        # 模拟一个耗时操作
        print("  [Dependent] 3. 注册回调: future.add_done_callback(self.wakeup)")
        print("  [Dependent] 4. yield 出去，进入休眠状态（移出就绪列表）")

        await asyncio.sleep(1)  # 这里实际上 await 的是一个 Future

        print("  [Dependent] 8. 被唤醒！从暂停处恢复执行")
        print("  [Dependent] 9. 继续执行剩余代码")

        return "任务完成"

    print("主程序创建 Task...")
    task = asyncio.create_task(dependent_task())

    # 模拟 Event Loop 的其他工作
    print("  [EventLoop] 5. Task 已挂起，继续执行其他任务")
    await asyncio.sleep(0.5)
    print("  [EventLoop] 6. 时间到，Future 完成，触发回调")
    print("  [EventLoop] 7. 通过 call_soon 将 Task 加回就绪列表")

    result = await task
    print(f"\n最终结果: {result}")

    print(f"\n完整流程总结:")
    print(f"  创建 -> 运行 -> 遇到 await -> 注册回调 -> yield 挂起")
    print(f"  -> Future 完成 -> 触发回调 -> call_soon 唤醒 -> 继续运行 -> 完成")


# ============================================================================
# 主函数：运行所有 Demo
# ============================================================================
async def main():
    """运行所有演示"""

    # Demo 1: await coroutine vs await task
    await demo1_direct_await()
    await demo1_create_task()

    # Demo 2: 回调机制
    await demo2_callback_mechanism()

    # Demo 3: YIELD_FROM 机制
    await demo3_yield_mechanism()

    # Demo 4: 调度公平性
    await demo4_fairness()

    # Demo 5: Task 生命周期
    await demo5_task_lifecycle()

    print("\n" + "=" * 80)
    print("所有演示完成！")
    print("=" * 80)
    print("\n核心要点回顾：")
    print("1. await coroutine 是同步执行，不创建 Task")
    print("2. await task 是并发执行，需要 create_task()")
    print("3. Task 通过 add_done_callback 注册唤醒回调")
    print("4. await 底层使用 YIELD_FROM（生成器机制）")
    print("5. call_soon 保证上下文隔离和调度公平性")
    print("6. Event Loop 只调度 Task，不调度裸 Coroutine")


if __name__ == "__main__":
    # 运行主程序
    asyncio.run(main())
