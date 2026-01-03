"""
await 最佳实践和常见模式
Real-world use cases and best practices

主题：
1. 并发模式：gather vs wait vs as_completed
2. 超时控制和取消
3. 错误处理策略
4. 性能优化技巧
5. 常见陷阱和如何避免
"""

import asyncio
import time
from typing import List, Any
import random


# ============================================================================
# Demo 1: 并发模式对比
# ============================================================================
print("=" * 80)
print("Demo 1: 不同的并发模式")
print("=" * 80)


async def fetch_data(task_id: int, delay: float) -> dict:
    """模拟异步获取数据"""
    await asyncio.sleep(delay)
    return {"id": task_id, "data": f"Data from task {task_id}"}


async def demo1_concurrency_patterns():
    """演示不同的并发模式"""

    print("\n模式1: 使用 gather - 并发执行，等待所有完成")
    start = time.time()
    results = await asyncio.gather(
        fetch_data(1, 1.0),
        fetch_data(2, 0.5),
        fetch_data(3, 0.8),
    )
    print(f"  耗时: {time.time() - start:.2f}秒")
    print(f"  结果: {results}")
    print(f"  特点: 返回结果列表，保持顺序")

    print("\n模式2: 使用 wait - 更灵活的控制")
    start = time.time()
    tasks = [
        asyncio.create_task(fetch_data(4, 1.0)),
        asyncio.create_task(fetch_data(5, 0.5)),
        asyncio.create_task(fetch_data(6, 0.8)),
    ]
    # 等待第一个完成
    done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    print(f"  第一个完成耗时: {time.time() - start:.2f}秒")
    print(f"  完成的任务数: {len(done)}")
    print(f"  待完成的任务数: {len(pending)}")

    # 取消剩余任务
    for task in pending:
        task.cancel()

    print(f"  特点: 可以选择等待策略（第一个完成、所有完成、第一个异常）")

    print("\n模式3: 使用 as_completed - 按完成顺序处理")
    start = time.time()
    tasks = [
        fetch_data(7, 1.0),
        fetch_data(8, 0.3),
        fetch_data(9, 0.6),
    ]

    print("  按完成顺序处理结果:")
    for coro in asyncio.as_completed(tasks):
        result = await coro
        elapsed = time.time() - start
        print(f"    {elapsed:.2f}秒: {result}")

    print(f"  特点: 立即处理完成的任务，不用等待全部完成")

    print("\n总结:")
    print("  - gather: 简单场景，需要所有结果")
    print("  - wait: 需要更细粒度的控制")
    print("  - as_completed: 流式处理，边完成边处理")


# ============================================================================
# Demo 2: 超时控制
# ============================================================================
print("\n" + "=" * 80)
print("Demo 2: 超时控制")
print("=" * 80)


async def slow_operation(duration: float) -> str:
    """模拟慢速操作"""
    await asyncio.sleep(duration)
    return f"Completed after {duration}s"


async def demo2_timeout_control():
    """演示超时控制的不同方式"""

    print("\n方式1: 使用 wait_for 设置超时")
    try:
        result = await asyncio.wait_for(slow_operation(0.5), timeout=1.0)
        print(f"  ✓ 在超时前完成: {result}")
    except asyncio.TimeoutError:
        print(f"  ✗ 超时了！")

    try:
        result = await asyncio.wait_for(slow_operation(2.0), timeout=1.0)
        print(f"  ✓ 完成: {result}")
    except asyncio.TimeoutError:
        print(f"  ✗ 超时了！操作被取消")

    print("\n方式2: 使用 wait 配合超时")
    task = asyncio.create_task(slow_operation(2.0))
    done, pending = await asyncio.wait([task], timeout=1.0)

    if pending:
        print(f"  超时了，任务还未完成")
        task.cancel()
        print(f"  已取消任务")
    else:
        result = done.pop().result()
        print(f"  及时完成: {result}")

    print("\n总结:")
    print("  - wait_for: 简单直接，自动取消超时的任务")
    print("  - wait + timeout: 更灵活，可以选择是否取消")
    print("  - 超时后 Task 会被取消，抛出 CancelledError")


# ============================================================================
# Demo 3: 错误处理策略
# ============================================================================
print("\n" + "=" * 80)
print("Demo 3: 错误处理策略")
print("=" * 80)


async def risky_operation(task_id: int, fail: bool = False) -> str:
    """可能失败的操作"""
    await asyncio.sleep(0.1)
    if fail:
        raise ValueError(f"Task {task_id} failed!")
    return f"Task {task_id} succeeded"


async def demo3_error_handling():
    """演示不同的错误处理策略"""

    print("\n策略1: gather 的 return_exceptions 参数")
    results = await asyncio.gather(
        risky_operation(1, fail=False),
        risky_operation(2, fail=True),
        risky_operation(3, fail=False),
        return_exceptions=True,  # 不抛出异常，而是作为结果返回
    )

    print("  结果:")
    for i, result in enumerate(results, 1):
        if isinstance(result, Exception):
            print(f"    Task {i}: ✗ 失败 - {result}")
        else:
            print(f"    Task {i}: ✓ 成功 - {result}")

    print("\n策略2: 单独捕获每个 Task 的异常")
    tasks = [
        asyncio.create_task(risky_operation(4, fail=False)),
        asyncio.create_task(risky_operation(5, fail=True)),
        asyncio.create_task(risky_operation(6, fail=False)),
    ]

    results = []
    for i, task in enumerate(tasks, 4):
        try:
            result = await task
            print(f"  Task {i}: ✓ {result}")
            results.append(result)
        except Exception as e:
            print(f"  Task {i}: ✗ 捕获异常: {e}")
            results.append(None)

    print("\n策略3: 使用包装函数处理异常")

    async def safe_wrapper(coro, default=None):
        """安全包装器，捕获所有异常"""
        try:
            return await coro
        except Exception as e:
            print(f"    捕获到异常: {e}")
            return default

    results = await asyncio.gather(
        safe_wrapper(risky_operation(7, fail=False)),
        safe_wrapper(risky_operation(8, fail=True), default="fallback"),
        safe_wrapper(risky_operation(9, fail=False)),
    )

    print(f"  最终结果: {results}")

    print("\n总结:")
    print("  - return_exceptions=True: 不中断其他任务")
    print("  - 单独捕获: 更细粒度的控制")
    print("  - 包装函数: 统一的错误处理逻辑")


# ============================================================================
# Demo 4: 性能优化技巧
# ============================================================================
print("\n" + "=" * 80)
print("Demo 4: 性能优化技巧")
print("=" * 80)


async def demo4_performance_tips():
    """演示性能优化的最佳实践"""

    print("\n技巧1: 避免串行 await - 使用并发")

    # 错误示例：串行执行
    print("  ✗ 串行执行（慢）:")
    start = time.time()
    result1 = await fetch_data(1, 0.3)
    result2 = await fetch_data(2, 0.3)
    result3 = await fetch_data(3, 0.3)
    serial_time = time.time() - start
    print(f"    耗时: {serial_time:.2f}秒")

    # 正确示例：并发执行
    print("  ✓ 并发执行（快）:")
    start = time.time()
    results = await asyncio.gather(
        fetch_data(1, 0.3),
        fetch_data(2, 0.3),
        fetch_data(3, 0.3),
    )
    concurrent_time = time.time() - start
    print(f"    耗时: {concurrent_time:.2f}秒")
    print(f"    性能提升: {serial_time / concurrent_time:.1f}x")

    print("\n技巧2: 合理使用 Task - 提前创建，延迟等待")

    # 立即创建 Task，让它们开始执行
    print("  创建所有 Task，它们立即开始执行...")
    task1 = asyncio.create_task(fetch_data(10, 0.3))
    task2 = asyncio.create_task(fetch_data(11, 0.3))

    # 在等待结果之前，可以做其他事情
    print("  在等待期间做其他工作...")
    await asyncio.sleep(0.1)
    print("  其他工作完成")

    # 现在等待结果
    result1 = await task1
    result2 = await task2
    print(f"  所有结果: {result1}, {result2}")

    print("\n技巧3: 使用 TaskGroup (Python 3.11+)")
    if hasattr(asyncio, 'TaskGroup'):
        print("  使用 TaskGroup 自动管理任务生命周期:")
        async with asyncio.TaskGroup() as tg:
            task1 = tg.create_task(fetch_data(12, 0.2))
            task2 = tg.create_task(fetch_data(13, 0.2))
            # TaskGroup 会自动等待所有任务完成
        print(f"  所有任务已自动完成: {task1.result()}, {task2.result()}")
    else:
        print("  (TaskGroup 需要 Python 3.11+)")

    print("\n总结:")
    print("  - 识别可以并发的操作，避免不必要的串行")
    print("  - 使用 create_task 提前启动，充分利用并发")
    print("  - TaskGroup 提供更安全的任务管理（自动清理）")


# ============================================================================
# Demo 5: 常见陷阱
# ============================================================================
print("\n" + "=" * 80)
print("Demo 5: 常见陷阱和如何避免")
print("=" * 80)


async def demo5_common_pitfalls():
    """演示常见错误和正确做法"""

    print("\n陷阱1: 忘记 await")
    print("  ✗ 错误: 忘记 await，协程不会执行")

    async def my_coro():
        return "结果"

    # 错误：忘记 await
    result = my_coro()  # 这只是创建了协程对象，不会执行！
    print(f"    result 的类型: {type(result)}")  # <class 'coroutine'>
    result.close()  # 清理未执行的协程

    # 正确：使用 await
    result = await my_coro()
    print(f"  ✓ 正确: {result}")

    print("\n陷阱2: 在循环中串行 await")
    print("  ✗ 错误: 循环中串行 await")

    async def process(i):
        await asyncio.sleep(0.1)
        return i * 2

    start = time.time()
    results = []
    for i in range(5):
        result = await process(i)  # 串行执行
        results.append(result)
    serial_time = time.time() - start
    print(f"    串行耗时: {serial_time:.2f}秒")

    # 正确：先创建所有任务，再等待
    print("  ✓ 正确: 并发执行")
    start = time.time()
    tasks = [process(i) for i in range(5)]
    results = await asyncio.gather(*tasks)
    concurrent_time = time.time() - start
    print(f"    并发耗时: {concurrent_time:.2f}秒")

    print("\n陷阱3: 阻塞操作混入异步代码")
    print("  ✗ 错误: 使用阻塞的 time.sleep")

    async def bad_sleep():
        time.sleep(0.5)  # 这会阻塞整个 Event Loop！
        return "bad"

    async def good_sleep():
        await asyncio.sleep(0.5)  # 正确：使用异步 sleep
        return "good"

    print("    使用阻塞 sleep:")
    start = time.time()
    await bad_sleep()
    print(f"      耗时: {time.time() - start:.2f}秒 (阻塞了 Event Loop)")

    print("    使用异步 sleep:")
    start = time.time()
    await good_sleep()
    print(f"      耗时: {time.time() - start:.2f}秒 (正确)")

    print("\n陷阱4: 不处理 Task 的异常")
    print("  ✗ 错误: 创建 Task 后不检查异常")

    async def failing_task():
        await asyncio.sleep(0.1)
        raise ValueError("Oops!")

    task = asyncio.create_task(failing_task())
    await asyncio.sleep(0.2)

    # Task 已经失败，但没有人 await 它
    # 这会导致异常被忽略（仅打印警告）
    print("    Task 状态:", "完成" if task.done() else "运行中")

    # 正确：总是 await Task 或检查异常
    try:
        await task  # 这会重新抛出异常
    except ValueError as e:
        print(f"  ✓ 正确: 捕获到异常: {e}")

    print("\n总结:")
    print("  1. 永远不要忘记 await")
    print("  2. 识别可以并发的操作")
    print("  3. 不要使用阻塞操作（time.sleep, requests.get 等）")
    print("  4. 总是处理 Task 的异常")


# ============================================================================
# Demo 6: 实际应用案例
# ============================================================================
print("\n" + "=" * 80)
print("Demo 6: 实际应用案例")
print("=" * 80)


async def demo6_real_world_example():
    """模拟真实场景：批量请求 API"""
    print("\n场景: 批量请求多个 API 端点\n")

    # 模拟 API 请求
    async def fetch_user(user_id: int):
        """获取用户信息"""
        await asyncio.sleep(random.uniform(0.1, 0.3))
        if random.random() < 0.1:  # 10% 失败率
            raise Exception(f"Failed to fetch user {user_id}")
        return {"id": user_id, "name": f"User{user_id}"}

    async def fetch_user_posts(user_id: int):
        """获取用户文章"""
        await asyncio.sleep(random.uniform(0.1, 0.3))
        return [{"id": i, "user_id": user_id} for i in range(3)]

    # 使用包装器处理错误
    async def safe_fetch(coro, error_msg="Error"):
        try:
            return await coro
        except Exception as e:
            print(f"  ⚠ {error_msg}: {e}")
            return None

    # 批量获取用户和他们的文章
    user_ids = [1, 2, 3, 4, 5]

    print("步骤1: 并发获取所有用户信息")
    users = await asyncio.gather(*[
        safe_fetch(fetch_user(uid), f"User {uid}")
        for uid in user_ids
    ])

    valid_users = [u for u in users if u is not None]
    print(f"  成功获取 {len(valid_users)}/{len(user_ids)} 个用户")

    print("\n步骤2: 为每个用户并发获取文章")
    all_posts = await asyncio.gather(*[
        safe_fetch(fetch_user_posts(u["id"]), f"Posts for user {u['id']}")
        for u in valid_users
    ])

    print(f"  成功获取 {sum(len(p) if p else 0 for p in all_posts)} 篇文章")

    print("\n步骤3: 组合结果")
    result = []
    for user, posts in zip(valid_users, all_posts):
        if posts:
            result.append({
                "user": user,
                "post_count": len(posts),
                "posts": posts,
            })

    print(f"\n最终结果: {len(result)} 个用户数据")
    for item in result[:2]:  # 只显示前两个
        print(f"  - {item['user']['name']}: {item['post_count']} 篇文章")

    print("\n这个例子展示了:")
    print("  ✓ 批量并发请求提高性能")
    print("  ✓ 优雅的错误处理")
    print("  ✓ 分步处理复杂逻辑")
    print("  ✓ 组合多个异步操作的结果")


# ============================================================================
# 主函数
# ============================================================================
async def main():
    """运行所有最佳实践演示"""

    # Demo 1: 并发模式
    await demo1_concurrency_patterns()

    # Demo 2: 超时控制
    await demo2_timeout_control()

    # Demo 3: 错误处理
    await demo3_error_handling()

    # Demo 4: 性能优化
    await demo4_performance_tips()

    # Demo 5: 常见陷阱
    await demo5_common_pitfalls()

    # Demo 6: 实际应用
    await demo6_real_world_example()

    print("\n" + "=" * 80)
    print("最佳实践演示完成！")
    print("=" * 80)

    print("\n关键要点:")
    print("  1. 选择合适的并发模式 (gather/wait/as_completed)")
    print("  2. 合理设置超时，避免无限等待")
    print("  3. 妥善处理异常，不中断其他任务")
    print("  4. 最大化并发，避免不必要的串行")
    print("  5. 避免常见陷阱（忘记 await、阻塞操作等）")
    print("  6. 在实际项目中组合使用这些技巧")


if __name__ == "__main__":
    asyncio.run(main())
