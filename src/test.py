import multiprocessing
import os
import time

from idbs import IDBS
from heuristic import Rectangle

ROOT_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT_DIR, "data")
RUN_PER_TEST = 10

def run(rectangles, bin_width, bin_height):
    quit = multiprocessing.Event()
    found = multiprocessing.Event()
    return_queue = multiprocessing.Queue()
    processes = []
    idbs = IDBS(100, bin_width, bin_height)
    for _ in range(multiprocessing.cpu_count() // 2):
        p = multiprocessing.Process(
            target=idbs.run, args=(rectangles, quit, found, return_queue)
        )
        processes.append(p)
        p.start()
    found.wait()
    quit.set()
    return return_queue.get()

def read_rectangles_from_file(file_path):
    rectangles = []
    with open(file_path, "r") as dataset:
        rectangle_count = int(dataset.readline())
        bin_width, bin_height = map(int, dataset.readline().split(" "))
        x = 0
        for i in range(rectangle_count):
            rec_width, rec_height = map(int, dataset.readline().split(" ")[:2])
            rectangle = Rectangle(rec_width, rec_height)
            rectangles.append(rectangle)
    return (rectangles, bin_width, bin_height)

if __name__ == "__main__":
    for filename in sorted(os.listdir(DATA_DIR)):
        path_to_file = os.path.join(DATA_DIR, filename)
        if os.path.isfile(path_to_file):
            rectangles, bin_width, bin_height = read_rectangles_from_file(path_to_file)
            min_run_time = float("inf")
            min_height = float("inf")
            max_run_time = 0.0
            total_run_time = 0
            for _ in range(RUN_PER_TEST):
                t0 = time.time()
                best_seq = run(rectangles, bin_width, bin_height)
                run_time = time.time() - t0
                if run_time < min_run_time:
                    min_run_time = run_time
                if run_time > max_run_time:
                    max_run_time = run_time
                if best_seq[1] < min_height:
                    min_height = best_seq[1]
                total_run_time += run_time
            avg_run_time = total_run_time / RUN_PER_TEST
            print(f"TEST FOR: {filename}")
            print(f"Min. Height: {min_height}")
            print(f"Min. Run Time: {min_run_time}")
            print(f"Max. Run Time: {max_run_time}")
            print(f"Avg. Run Time: {avg_run_time}\n\n")