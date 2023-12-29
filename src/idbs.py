import copy
import math
import time
from tabu_search import TabuSearchSolver


class IDBS:
    def __init__(self, time_limit, bin_width, bin_height, tabu_seq_length=10, tabu_tenure_multiplier=3):
        """Iterative Doubling Binary Search.
        Tries to find the optimal bin height to fit the given rectangles into.
        Lower bound is set as the total area of all rectangles divided by the bin width.
        Upper bound is set as the LB * 1.1. We run our tabu search on the middle height.
        If our tabu search places the rectangles to this height successfully we set the upper bound to this height.
        If not then we raise the lower bound as. At each iteration we double the iteration value
        that we give to our tabu search. That's where "iterative doubling" comes from. This means at the start
        we are confident that our tabu search and heuristic can place the rectangles into the given height. So we don't
        want to waste much time at the start. But as the search height gets lower we want our tabu search to search deeper
        and wider range. If we give a lower iteration count to tabu search it means it won't search as deeper. If we give a
        large iteration count it will widen the search range of the tabu search by allowing it to generate new sequences from the
        previous best sequence longer. If we reach the optimal height and place all the rectangles to this height successfully, then we 
        return with success."""
        self.time_limit = time_limit
        self.bin_width = bin_width
        self.bin_height = bin_height
        self.solver = TabuSearchSolver(tabu_seq_length, tabu_tenure_multiplier)
        self.best_seq = None

    def reset_rectangles(self):
        """Reset bottom left position and rotation values of the rectangles"""
        for rectangle in self.rectangles:
            rectangle.bottom_left_pos = None
            rectangle.rotate = False

    def run(self, rectangles, quit, found, return_queue):
        self.rectangles = copy.deepcopy(rectangles)
        self.reset_rectangles()
        # Compute lower bound
        total_rec_area = sum(rec.width * rec.height for rec in self.rectangles)
        lower_bound = math.ceil(total_rec_area / self.bin_width)
        # UB = LB  * 1.1
        upper_bound = math.ceil(lower_bound * 1.1)
        
        iter = 1
        ub_found = False
        t0 = time.time()
        # while any other process hasn't found a solution and time limit not exceeded and LB != UB do
        while (
            not quit.is_set()
            and time.time() - t0 < self.time_limit
            and lower_bound != upper_bound
        ):
            tmp_lower_bound = lower_bound
            # while tempLB < UB do
            while tmp_lower_bound < upper_bound:
                height = (tmp_lower_bound + upper_bound) // 2
                # if tabu search (H,iter) is successful then
                if self.solver.run(self.rectangles, self.bin_width, height, iter, quit):
                    # Record solution
                    self.best_seq = (copy.deepcopy(self.solver.best_seq), height)
                    # Return the solution immediately if we found an optimal height solution
                    if height == self.bin_height:
                        return_queue.put(self.best_seq)
                        # Inform other processes that this process found a solution
                        found.set()
                        return
                    # Lower the upper bound
                    upper_bound = height
                    ub_found = True
                else:
                    # Raise the lower bound
                    tmp_lower_bound = height + 1
            if not ub_found:
                # Raise the upper bound if we haven't found a single solution
                upper_bound = math.ceil(upper_bound * 1.1)
            # Double the iteration count for next search
            iter *= 2
        # If we didn't find an optimal solution in the given time limit return the best solution found so far
        return_queue.put(self.best_seq)
        found.set()
