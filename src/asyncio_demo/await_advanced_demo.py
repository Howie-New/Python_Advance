"""
await 高级原理演示
深入理解 await 的内部机制

主题：
1. 手动模拟 await 的 YIELD_FROM 机制
2. 栈帧保存与恢复的可视化
3. Future 和 Task 的关系
4. 异常在 await 中的传播
"""

import asyncio
import inspect
import traceback
from typing import Generator, Any


# ============================================================================
# Demo 1: 手动实现一个简化版的 await 机制
# ============================================================================
print("=" * 80)
print("Demo 1: 手动模拟 await 的底层机制")
print("=" * 80)


class SimpleFuture:
    """简化版的 Future，用于理解原理"""

    def __init__(self):
        self._result = None
        self._done = False
        self._callbacks = []

    def set_result(self, result):
        """设置结果并触发所有回调"""
        print(f"    [Future] 设置结果: {result}")
        self._result = result
        self._done = True

        # 触发所有回调
        print(f"    [Future] 触发 {len(self._callbacks)} 个回调")
        for callback in self._callbacks:
            callback(self)

    def add_done_callback(self, callback):
        """添加完成回调"""
        print(f"    [Future] 添加回调: {callback.__name__}")
        if self._done:
            # 如果已经完成，立即调用
            callback(self)
        else:
            self._callbacks.append(callback)

    def result(self):
        """获取结果"""
        if not self._done:
            raise RuntimeError("Future not done yet")
        return self._result

    def __await__(self):
        """使这个 Future 可以被 await"""
        if not self._done:
            # yield self 表示暂停，等待完成
            yield self
        return self._result


def manual_await_demo():
    """手动演示 await 的工作流程"""
    print("\n演示: 手动模拟 await future 的过程\n")

    # 创建一个 Future
    future = SimpleFuture()

    # 模拟一个等待 Future 的协程
    def waiter_coroutine():
        print("  [Waiter] 第1步: 开始执行")
        print("  [Waiter] 第2步: 准备 await future")

        # 这里模拟 await future 的过程
        # 实际上会调用 future.__await__()，返回一个生成器
        # 然后通过 yield from 暂停
        result = yield from future.__await__()

        print(f"  [Waiter] 第5步: 被唤醒，收到结果: {result}")
        return result

    # 创建生成器
    gen = waiter_coroutine()

    # 第一次调用 send(None)，开始执行
    print("[Driver] 调用 gen.send(None) 启动协程")
    try:
        yielded = gen.send(None)
        print(f"  [Waiter] 第3步: yield 了: {yielded}")
        print(f"  [Waiter] 协程暂停，等待 Future 完成")
    except StopIteration as e:
        print(f"协程已完成，结果: {e.value}")
        return

    # 模拟一段时间后完成 Future
    print("\n[Driver] 第4步: 模拟一段时间后，设置 Future 的结果")
    future.set_result("Future 的数据")

    # 第二次调用 send(None)，恢复执行
    print("\n[Driver] 调用 gen.send(None) 恢复协程")
    try:
        gen.send(None)
    except StopIteration as e:
        print(f"\n[Driver] 第6步: 协程完成，返回值: {e.value}")

    print("\n总结:")
    print("  - await 本质上是 yield from future.__await__()")
    print("  - 第一次 send(None) 启动，yield 暂停")
    print("  - Future 完成后，第二次 send(None) 恢复")
    print("  - 返回值包装在 StopIteration.value 中")


# ============================================================================
# Demo 2: 栈帧保存与恢复 - 可视化演示
# ============================================================================
print("\n" + "=" * 80)
print("Demo 2: 栈帧保存与恢复的可视化")
print("=" * 80)


async def visualize_frame_demo():
    """可视化展示栈帧的保存与恢复"""
    print("\n演示: 查看协程暂停时的栈帧信息\n")

    async def nested_coroutine(depth: int):
        frame = inspect.currentframe()
        print(f"  [深度 {depth}] 当前栈帧信息:")
        print(f"    - 函数名: {frame.f_code.co_name}")
        print(f"    - 行号: {frame.f_lineno}")
        print(f"    - 局部变量: {list(frame.f_locals.keys())}")

        if depth > 0:
            print(f"  [深度 {depth}] 准备 await 更深层的协程")
            result = await nested_coroutine(depth - 1)
            print(f"  [深度 {depth}] 从暂停恢复，收到结果: {result}")
            return f"depth-{depth}: {result}"
        else:
            print(f"  [深度 0] 到达最深层，模拟 IO 操作")
            await asyncio.sleep(0.1)
            print(f"  [深度 0] IO 操作完成")
            return "bottom"

    print("开始嵌套调用，深度为 3:\n")
    result = await nested_coroutine(3)
    print(f"\n最终结果: {result}")

    print("\n总结:")
    print("  - 每次 await 都会保存当前栈帧（包括局部变量、行号）")
    print("  - 协程可以嵌套，形成调用栈")
    print("  - 恢复时从保存的行号继续执行")
    print("  - 这就是协程能够'暂停'和'恢复'的原理")


# ============================================================================
# Demo 3: Future vs Task 的关系
# ============================================================================
print("\n" + "=" * 80)
print("Demo 3: Future 和 Task 的关系")
print("=" * 80)


async def future_vs_task_demo():
    """演示 Future 和 Task 的区别与联系"""
    print("\n演示: Future 是基础，Task 是特殊的 Future\n")

    # 1. 直接使用 Future
    print("1. 直接使用 Future:")
    future = asyncio.Future()

    async def use_future():
        print("  [使用者] 等待 Future 完成...")
        result = await future
        print(f"  [使用者] 收到结果: {result}")
        return result

    # 创建任务
    task_using_future = asyncio.create_task(use_future())

    # 等一会儿再设置结果
    await asyncio.sleep(0.1)
    print("  [设置者] 设置 Future 的结果")
    future.set_result("Future 的值")

    result = await task_using_future
    print(f"  结果: {result}\n")

    # 2. Task 本身就是 Future
    print("2. Task 是 Future 的子类:")
    async def simple_coro():
        await asyncio.sleep(0.1)
        return "Task 的值"

    task = asyncio.create_task(simple_coro())

    print(f"  task 是 Future 吗? {isinstance(task, asyncio.Future)}")
    print(f"  task 是 Task 吗? {isinstance(task, asyncio.Task)}")

    # Task 也可以添加回调
    def on_task_done(t):
        print(f"  [回调] Task 完成了，结果: {t.result()}")

    task.add_done_callback(on_task_done)

    result = await task

    print("\n总结:")
    print("  - Future: 表示一个未来会有结果的对象")
    print("  - Task: 是 Future 的子类，专门用于包装 Coroutine")
    print("  - Task 会自动驱动 Coroutine 的执行")
    print("  - Future 需要手动 set_result()")
    print("  - 两者都支持 await 和 add_done_callback()")


# ============================================================================
# Demo 4: 异常在 await 中的传播
# ============================================================================
print("\n" + "=" * 80)
print("Demo 4: 异常在 await 中的传播")
print("=" * 80)


async def exception_propagation_demo():
    """演示异常如何在 await 链中传播"""
    print("\n演示: 异常通过 await 链向上传播\n")

    async def level_3():
        print("  [Level 3] 开始执行")
        await asyncio.sleep(0.1)
        print("  [Level 3] 抛出异常！")
        raise ValueError("在 Level 3 发生的错误")

    async def level_2():
        print("  [Level 2] 开始执行")
        try:
            result = await level_3()
        except ValueError as e:
            print(f"  [Level 2] 捕获到异常: {e}")
            print(f"  [Level 2] 重新抛出一个新异常")
            raise RuntimeError("在 Level 2 重新包装的错误") from e

    async def level_1():
        print("  [Level 1] 开始执行")
        try:
            result = await level_2()
        except RuntimeError as e:
            print(f"  [Level 1] 捕获到异常: {e}")
            print(f"  [Level 1] 原始异常: {e.__cause__}")
            return f"已处理异常: {e}"

    result = await level_1()
    print(f"\n最终结果: {result}")

    print("\n总结:")
    print("  - 异常会沿着 await 链向上传播")
    print("  - 可以在任何层级捕获和处理异常")
    print("  - 使用 raise ... from ... 保留异常链")
    print("  - await 对异常是透明的（不改变传播方式）")


# ============================================================================
# Demo 5: await 的三种对象：Coroutine, Task, Future
# ============================================================================
print("\n" + "=" * 80)
print("Demo 5: await 的三种对象")
print("=" * 80)


async def three_awaitable_types_demo():
    """演示可以 await 的三种对象"""
    print("\n演示: Coroutine、Task、Future 都可以被 await\n")

    # 1. await Coroutine
    print("1. await Coroutine (协程函数的返回值):")

    async def my_coroutine():
        await asyncio.sleep(0.1)
        return "Coroutine 结果"

    result1 = await my_coroutine()
    print(f"  结果: {result1}\n")

    # 2. await Task
    print("2. await Task (通过 create_task 创建):")

    async def my_task_coro():
        await asyncio.sleep(0.1)
        return "Task 结果"

    task = asyncio.create_task(my_task_coro())
    result2 = await task
    print(f"  结果: {result2}\n")

    # 3. await Future
    print("3. await Future (手动创建和设置):")

    future = asyncio.Future()

    async def set_future_later():
        await asyncio.sleep(0.1)
        future.set_result("Future 结果")

    asyncio.create_task(set_future_later())
    result3 = await future
    print(f"  结果: {result3}\n")

    print("总结:")
    print("  - Coroutine: async def 定义的函数，调用后返回协程对象")
    print("  - Task: 包装协程的对象，由 Event Loop 调度")
    print("  - Future: 表示未来结果的占位符")
    print("  - 三者都实现了 __await__() 方法，所以都可以被 await")


# ============================================================================
# Demo 6: 深入理解 yield from 和 await 的关系
# ============================================================================
print("\n" + "=" * 80)
print("Demo 6: yield from 和 await 的等价关系")
print("=" * 80)


def yield_from_vs_await_demo():
    """演示 yield from 和 await 的关系"""
    print("\n演示: await 本质上是 yield from\n")

    # 使用生成器模拟协程
    def generator_based_coroutine():
        print("  [生成器协程] 开始")
        # 在旧式协程中，yield from 用于委托
        value = yield "waiting"
        print(f"  [生成器协程] 恢复，收到: {value}")
        return "生成器结果"

    # 手动驱动
    gen = generator_based_coroutine()

    print("第一次 send(None) 启动:")
    yielded = gen.send(None)
    print(f"  yield 的值: {yielded}")

    print("\n第二次 send('恢复数据') 恢复:")
    try:
        gen.send("恢复数据")
    except StopIteration as e:
        print(f"  返回值: {e.value}")

    print("\n历史演进:")
    print("  Python 3.4: 使用 @asyncio.coroutine 和 yield from")
    print("  Python 3.5: 引入 async/await 语法糖")
    print("  本质: await 就是 yield from 的语法糖")
    print("  差异: await 只能在 async def 中使用，类型检查更严格")


# ============================================================================
# 主函数
# ============================================================================
async def main():
    """运行所有高级演示"""

    # Demo 1: 手动模拟 await
    manual_await_demo()

    # Demo 2: 栈帧保存与恢复
    await visualize_frame_demo()

    # Demo 3: Future vs Task
    await future_vs_task_demo()

    # Demo 4: 异常传播
    await exception_propagation_demo()

    # Demo 5: 三种 awaitable 对象
    await three_awaitable_types_demo()

    # Demo 6: yield from vs await
    yield_from_vs_await_demo()

    print("\n" + "=" * 80)
    print("高级演示完成！")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
