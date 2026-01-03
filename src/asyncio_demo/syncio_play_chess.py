import time

def play():
    # print("Playing chess sync...")
    for _ in range(5):
        # print("Enemy Making a move... awaiting...")
        time.sleep(1)
        for _ in range(1000):
            pass  # Simulate computation
        # print("My turn to move!")
    print("Finish, defeated a enemy!")


def main():
    start_time = time.time()
    for _ in range(10):
        play()
    print(f"Total time taken: {time.time() - start_time} seconds")

if __name__ == "__main__":
    main()