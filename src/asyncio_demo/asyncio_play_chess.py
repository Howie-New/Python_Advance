import time
import asyncio

async def play():
    # print("Playing chess sync...")
    for _ in range(5):
        # print("Enemy Making a move... awaiting...")
        await asyncio.sleep(1)
        for _ in range(1000):
            pass  # Simulate computation
        # print("My turn to move!")
    print("Finish, defeated a enemy!")


async def main():
    start_time = time.time()
    tasks = []
    for _ in range(10):
        play_coro = play()
        tasks.append(asyncio.create_task(play_coro))
    await asyncio.gather(*tasks)
    print(f"Total time taken: {time.time() - start_time} seconds")

if __name__ == "__main__":
    asyncio.run(main())