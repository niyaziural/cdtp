
class Rectangle:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.rotate = False
        self.index = -1
        self.bottom_left_pos = ()


class CandidatePoint:
    def __init__(self, x: int, y: int, is_left: bool = True) -> None:
        self.x = x
        self.y = y
        self.is_left = is_left
        self.w_base = 0
        self.w_max = 0
        self.h_left = 0
        self.h_right = 0

class Segment:
    def __init__(self, x: int, y: int, point: CandidatePoint = None) -> None:
        self.x = x
        self.y = y
        self.point = point


class Heuristic:
    def setup(self, sequence: list, bin_width: int, bin_height: int, max_spread: float):
        """Setups the heuristic and initializes values and sets up initial segments"""
        self.sequence = sequence
        self.unplaced_rectangles = set(sequence)
        self.bin_width = bin_width
        self.bin_height = bin_height
        self.max_spread = max_spread

        self.segments = []
        self.segments.append(Segment(x=-1, y=self.bin_height)) # No point for the left dummy segment
        self.segments.append(Segment(x=0, y=0, point=CandidatePoint(x=0, y=0)))
        self.segments.append(Segment(x=bin_width, y=bin_height,point=CandidatePoint(x=self.bin_width, y=0, is_left=False)))

    def find_min_values1(self):
        """Finds the minimum and second minimum width and height across the unplaces rectangles"""
        self.w_min = float("inf")
        self.w_sec = float("inf")
        self.h_min = float("inf")
        self.h_sec = float("inf")
        # Height of the lowest segment in all segments
        self.lowest_y = min(self.segments, key=lambda x: x.y).y
        # Special case for only one unplaces rectangle left
        if len(self.unplaced_rectangles) == 1:
            for rectangle in self.unplaced_rectangles:
                self.h_min = self.h_sec = self.w_min = self.w_sec = min(
                    rectangle.width, rectangle.height
                )
                return
        # Since we are allowing rotation h_min and w_min will be same, so will h_sec and w_sec
        for rectangle in self.unplaced_rectangles:
            min_width_or_height = min(rectangle.width, rectangle.height)
            if min_width_or_height < self.w_sec:
                if min_width_or_height < self.w_min:
                    self.w_sec = self.h_sec = self.w_min
                    self.w_min = self.h_min = min_width_or_height
                else:
                    self.w_sec = self.h_sec = min_width_or_height

    def find_valid_placements(self):
        """(Spread constraint)Finds valid pairs by checking if the rectangle can fit to space if placed to that point
        and the placement doesn't violate the max spread constraint."""
        valid_placements = []
        # For each point
        for i, segment in enumerate(self.segments[1:], 1):
            # Count for only fit constraint
            count = 0
            # For each unplaced rectangle
            for rectangle in self.unplaced_rectangles:
                # Check if it fits according to w_max, if it doesn't pass the top of the bin height and max spread
                if (
                    rectangle.width <= segment.point.w_max
                    and segment.point.y + rectangle.height - self.lowest_y
                    <= self.max_spread
                    and segment.point.y + rectangle.height <= self.bin_height
                ):
                    valid_placements.append((i, rectangle, False))
                    count += 1
                # Check for the rotated version of the rectangle too
                if (
                    rectangle.height <= segment.point.w_max
                    and segment.point.y + rectangle.width - self.lowest_y
                    <= self.max_spread
                    and segment.point.y + rectangle.width <= self.bin_height
                ):
                    valid_placements.append((i, rectangle, True))
                    count += 1
            # If there is only one rectangle that we can put on this point
            if count == 1:
                # Add this pair to only fits
                self.only_fits.append(valid_placements[-1])
        return valid_placements

    def find_candidate_points(self):
        """Finds points for each segment at the start of each iteration."""
        for i, segment in enumerate(self.segments[1:], 1):
            # If the left segment is higher than this segment it means this segment's point will be a left point
            if segment.y < self.segments[i - 1].y:
                segment.point = CandidatePoint(segment.x, segment.y, True)
                segment.point.w_base = self.segments[i + 1].x - segment.x
            else:
                segment.point = CandidatePoint(
                    segment.x, self.segments[i - 1].y, False
                )
                segment.point.w_base = segment.x - self.segments[i - 1].x
            # Find h_left, h_right and w_max values for this point
            segment.point.h_left = self.find_h_left(i)
            segment.point.h_right = self.find_h_right(i)
            segment.point.w_max = self.find_w_max(i)

    def find_h_left(self, i):
        """Finds the index of the first higher segment to the left of the point at index i."""
        # h_left is the height difference between this point and the first higher point to the left of this point 
        left_index = i - 1 if self.segments[i].point.is_left else i - 2
        while self.segments[left_index].y < self.segments[i].point.y:
            left_index -= 1
        # We only store the index of the first higher left segment to be able to navigate in the list in future
        return left_index
    def find_h_right(self, i):
        """Finds the index of the first higher segment to the right of the point at index i."""
        # Same as h_left but we're checking to the right
        right_index = i + 1 if self.segments[i].point.is_left else i
        while self.segments[right_index].y < self.segments[i].point.y:
            right_index += 1
        return right_index
    
    def find_w_max(self, i: int):
        """Finds the maximum width that can fit to this point"""
        # If this point is a left point
        if self.segments[i].point.is_left:
            pointer = i + 1
            # Move until the first higher segment to the right
            while self.segments[pointer].y <= self.segments[i].y:
                pointer += 1
            w_max = self.segments[pointer].x - self.segments[i].x
            return w_max
        else:
            pointer = i - 2
            # Move until the first higher segment to the left
            while self.segments[pointer].y <= self.segments[i - 1].y:
                pointer -= 1
            w_max = self.segments[i].x - self.segments[pointer + 1].x
            return w_max

    def find_top_waste(self, i, rec_width, rec_height):
        # We consider the space left at the top of the rectangle if we place this rectangle as wasted space
        # if height of this space is lower than the height of the remaining shortest rectangle
        # In short if we can't fit any rectangle to this space in next iterations 
        top_side = self.segments[i].point.y + rec_height
        min_height = self.h_sec if rec_height == self.h_min else self.h_min
        height_diff = self.bin_height - top_side
        if height_diff < min_height:
            return rec_width * height_diff
        return 0

    def find_side_wastes(self, i, rec_width, rec_height):
        # If the gaps between the sides of the rectangle and the first higher segments to the left and right
        # are lower than the remaining narrowest rectangle's width these spaces are wasted
        # because we won't be able to fit any rectangles to this space in next iterations
        min_width = self.w_sec if rec_width == self.w_min else self.w_min

        # x values of the left and right side of the placed rectangle
        if self.segments[i].point.is_left:
            left_side = self.segments[i].x
            right_side = self.segments[i].x + rec_width
        else:
            left_side = self.segments[i].x - rec_width
            right_side = self.segments[i].x
        top_side = self.segments[i].point.y + rec_height
        waste = 0

        # Left waste
        # We know the index of the first higher segment to the left as h_left
        # But after placing the rectangle, it's top might be higher than this point
        # So we keep going to left to find the first higher segment than the top side of 
        # this placement
        left_index = self.segments[i].point.h_left
        gap = left_side - self.segments[left_index + 1].x
        pointer = left_index
        while self.segments[pointer].y < top_side:
            gap += self.segments[pointer + 1].x - self.segments[pointer].x
            pointer -= 1
        if gap < min_width and gap > 0:
            while self.segments[pointer + 1].x < left_side:
                area_width = min(self.segments[pointer + 2].x, left_side) - self.segments[pointer + 1].x
                area_height = top_side - self.segments[pointer + 1].y
                waste += area_height * area_width
                pointer += 1

        # Right waste
        # We know the index of the first higher segment to the right as h_right
        right_index = self.segments[i].point.h_right
        gap = self.segments[right_index].x - right_side
        pointer = right_index
        while self.segments[pointer].y < top_side:
            gap += self.segments[pointer + 1].x - self.segments[pointer].x
            pointer += 1
        if gap < min_width and gap > 0:
            while self.segments[pointer].x > right_side:
                area_width = self.segments[pointer].x - max(self.segments[pointer - 1].x, right_side)
                area_height = top_side - self.segments[pointer - 1].y
                waste += area_height * area_width
                pointer -= 1
        return waste

    def find_bottom_waste(self, i, rec_width):
        # If width of the rectangle is larger than the w_base of the point
        # It means there will be leftover under the rectangle afther the placement
        # We calculate the area of this space here
        if self.segments[i].point.w_base >= rec_width:
            return 0
        waste = 0
        if self.segments[i].point.is_left:
            right_side = self.segments[i].x + rec_width
            pointer = i + 1
            segment_count = len(self.segments)
            while (
                pointer < segment_count - 1
                and self.segments[pointer + 1].x <= right_side
            ):
                area_width = self.segments[pointer + 1].x - self.segments[pointer].x
                area_height = self.segments[i].y - self.segments[pointer].y
                waste += area_width * area_height
                pointer += 1
            area_width = right_side - self.segments[pointer].x
            area_height = self.segments[i].y - self.segments[pointer].y
            waste += area_width * area_height
        else:
            left_side = self.segments[i].x - rec_width
            pointer = i
            while self.segments[pointer - 1].x >= left_side:
                area_width = self.segments[pointer].x - self.segments[pointer - 1].x
                area_height = self.segments[i].y - self.segments[pointer].y
                waste += area_width * area_height
                pointer -= 1
            area_width = self.segments[pointer].x - left_side
            area_height = self.segments[i].y - self.segments[pointer].y
            waste += area_width * area_height
        return waste

    def find_waste(self, placement):
        """Finds the wasted space for a point rectangle pair"""
        i = placement[0]
        rectangle = placement[1]
        if placement[2]:
            rec_width = rectangle.height
            rec_height = rectangle.width
        else:
            rec_width = rectangle.width
            rec_height = rectangle.height
        waste = 0
        waste += self.find_top_waste(i, rec_width, rec_height)
        waste += self.find_side_wastes(i, rec_width, rec_height)
        waste += self.find_bottom_waste(i, rec_width)
        return waste

    def min_waste_constraint(self, valid_placements: list):
        """Finds the pairs which have the minimum wasted space."""
        remaining_placemenets = []
        min_waste = float("inf")
        for placement in valid_placements:
            waste = self.find_waste(placement)
            if waste < min_waste:
                remaining_placemenets = [placement]
                min_waste = waste
            elif waste == min_waste:
                remaining_placemenets.append(placement)
        self.wasted_space += min_waste
        return remaining_placemenets

    def find_fitness(self, placement):
        """Finds the fitness value for a point rectangle point"""
        fitness = 0
        i = placement[0]  # Segment index
        segment = self.segments[i]
        rectangle = placement[1]
        # Check rotation
        if placement[2]:  # placment[2] -> Rotation or not
            rec_width = rectangle.height
            rec_height = rectangle.width
        else:
            rec_width = rectangle.width
            rec_height = rectangle.height
        if segment.point.is_left:
            # Check left side matches the height
            if self.segments[i - 1].y - segment.y == rec_height:
                fitness += 1
            # Check bottom matches the width
            if segment.point.w_base == rec_width:
                fitness += 1
                # Check right side too if bottom side is perfect placement
                if self.segments[i + 1].y - segment.y == rec_height:
                    fitness += 1
        else:
            # Check right side matches the height
            if segment.y - self.segments[i - 1].y == rec_height:
                fitness += 1
            # Check bottom matches the width
            if segment.point.w_base == rec_width:
                fitness += 1
                # Check left side too if bottom side is perfect placement
                if self.segments[i - 2].y - self.segments[i - 1].y == rec_height:
                    fitness += 1
        # Check if rectangle is touching to top of the bin
        if segment.point.y + rec_height == self.bin_height:
            fitness += 1
        return fitness

    def max_fitness_constraint(self, valid_placements: list):
        """Finds the pairs which have the maximum fitness value."""
        remaining_placemenets = []
        max_fitness = -1
        for placement in valid_placements:
            fitness = self.find_fitness(placement)
            if fitness > max_fitness:
                remaining_placemenets = [placement]
                max_fitness = fitness
            elif fitness == max_fitness:
                remaining_placemenets.append(placement)
        return remaining_placemenets

    def tiebreaker(self, valid_placements: list):
        """Finds the pair that has the earliest rectangle in the sequence 
        or pair with the lowest segment or pair with the segment with the minimum x value."""
        ealiest_rec_index = min(valid_placements, key=lambda x: x[1].index)[1].index
        valid_placements = [
            placement
            for placement in valid_placements
            if placement[1].index == ealiest_rec_index
        ]
        if len(valid_placements) == 1:
            return valid_placements[0]
        lowest_y = self.segments[
            min(valid_placements, key=lambda x: self.segments[x[0]].point.y)[0]
        ].point.y
        valid_placements = [
            placement
            for placement in valid_placements
            if self.segments[placement[0]].point.y == lowest_y
        ]
        if len(valid_placements) == 1:
            return valid_placements[0]
        lowest_x = self.segments[
            min(valid_placements, key=lambda x: self.segments[x[0]].point.x)[0]
        ].point.x
        for placement in valid_placements:
            if self.segments[placement[0]].point.x == lowest_x:
                return placement

    def place(self, placement):
        """Places the rectangle to the given point by adjusting the affected segments, inserting and deleting new segments"""
        i = placement[0]
        rectangle = placement[1]
        rotate = placement[2]
        rectangle.rotate = rotate
        if rotate:
            rec_width = rectangle.height
            rec_height = rectangle.width
        else:
            rec_width = rectangle.width
            rec_height = rectangle.height

        if self.segments[i].point.is_left:
            # Create a new segment for top of the placed rectangle
            rectangle.bottom_left_pos = (self.segments[i].x, self.segments[i].y)
            new_segment = Segment(self.segments[i].x, self.segments[i].y + rec_height)
            right_side = self.segments[i].x + rec_width
            pointer = i
            segment_count = len(self.segments)
            while (
                pointer < segment_count - 1
                and self.segments[pointer + 1].x <= right_side
            ):
                self.segments.pop(pointer)
                segment_count -= 1
            self.segments[pointer].x = right_side
            self.segments.insert(i, new_segment)
        else:
            rectangle.bottom_left_pos = (
                self.segments[i].x - rec_width,
                self.segments[i - 1].y,
            )
            left_side = self.segments[i].x - rec_width
            new_segment = Segment(left_side, self.segments[i - 1].y + rec_height)
            # Increase the height of the current segment# Create a new segment for top of the placed rectangle
            pointer = i
            while self.segments[pointer - 1].x >= left_side:
                self.segments.pop(pointer - 1)
                pointer -= 1
            self.segments.insert(pointer, new_segment)
        self.merge_unnecessary_segments(rec_width)
        self.unplaced_rectangles.remove(rectangle)

    def merge_unnecessary_segments(self, cur_placement_width):
        """Merges the narrow segments with its neighbors and the segments with the same height."""
        segments_to_remove = set()
        # Min width to compare against segment widths
        min_width = self.w_sec if cur_placement_width == self.w_min else self.w_min
        for i, segment in enumerate(self.segments[1:-1], 1):
            # Check for narrow segments
            segments_to_remove = segments_to_remove.union(
                self.check_segment_narrow(i, min_width)
            )
            # Check for adjacent segments with same height
            segments_to_remove = segments_to_remove.union(
                self.check_segment_same_height(i)
            )
        # If there is at least one segment to delete we need to run this function again to remove any new narrow segments
        if len(segments_to_remove) > 0:
            for segment in segments_to_remove:
                self.segments.remove(segment)
            self.merge_unnecessary_segments(cur_placement_width)

    def check_segment_narrow(self, i, min_width):
        """If a segment has a width lower than the remaining narrowest rectangles' width, it means we can't place
        any rectangle onto this segment. So we raise this segment and merge it with the neighbor segments. We check the
        new merged segments for the same condition recursively."""
        segments_to_remove = set()
        if (
            self.segments[i].y < self.segments[i - 1].y
            and self.segments[i].y < self.segments[i + 1].y
        ):
            # Check if we can't fit at least the remaining narrowest rectangle at the next iteration
            segment_length = self.segments[i + 1].x - self.segments[i].x
            if segment_length < min_width:
                # Check if previos and next segments at the same hight
                if self.segments[i - 1].y == self.segments[i + 1].y:
                    # We will delete (merge) current and next segment and only the previous one will stay
                    segments_to_remove.add(self.segments[i])
                    segments_to_remove.add(self.segments[i + 1])
                # Check if previous segment is lower than the next one
                elif self.segments[i - 1].y < self.segments[i + 1].y:
                    # We will only delete (merge) current segment
                    segments_to_remove.add(self.segments[i])
                # If next segment is lower than the previous one
                else:
                    # Only delete the next segment (merge with this one)
                    self.segments[i].y = self.segments[i + 1].y
                    segments_to_remove.add(self.segments[i + 1])
        return segments_to_remove

    def check_segment_same_height(self, i):
        """Checks and marks the segments with the same height accordingly to be deleted later."""
        segments_to_remove = set()
        # Special check for the first segment
        if i == 1 and self.segments[i - 1].y == self.segments[i].y:
            segments_to_remove.add(self.segments[i])
        if self.segments[i].y == self.segments[i + 1].y:
            segments_to_remove.add(self.segments[i + 1])
        return segments_to_remove

    def run(self, quit=None):
        """Runs the heuristic. Use setup function before running the heuristic."""
        for i in range(len(self.sequence)):
            self.sequence[i].index = i
        self.wasted_space = 0
        # Place a rectangle at each step
        for _ in self.sequence:
            if quit and quit.is_set():
                return False
            self.find_min_values1()
            self.find_candidate_points()
            self.only_fits = []
            valid_placements = self.find_valid_placements()
            if len(valid_placements) == 0:
                for rectangle in self.unplaced_rectangles:
                    rectangle.bottom_left_pos = None
                    rectangle.rotate = False
                return False
            if len(self.only_fits) == 1:
                self.place(self.only_fits[0])
                continue
            elif len(self.only_fits) > 1:
                valid_placements = self.only_fits
            valid_placements = self.min_waste_constraint(valid_placements)
            if len(valid_placements) == 1:
                self.place(valid_placements[0])
                continue
            valid_placements = self.max_fitness_constraint(valid_placements)
            if len(valid_placements) == 1:
                self.place(valid_placements[0])
                continue
            placement = self.tiebreaker(valid_placements)
            self.place(placement)
        return True
    
# We maintain a list of segments. Each element in the list represents the left point of a segment
# Initially there are 3 segments A[0] = (-1, H), A[1] = (0, 0), A[2] = (W, H). A[0] and A[2] are dummy segments
# If we have n segments then we have n + 1 candidate points to place a rectangle
# For example we have only one (non-dummy) segment in the beginning which is A[1] = (0, 0). In this case we have two candidate points
#   to place a rectangle. And those points are A[1].point = (0, 0) and A[2].point = (W, 0). We can store these points in the same list as well
#   since their x coordinates are the same with x coordinates of segments' left points.
# So each element in the list A we store left endpoint of a segment and informations of a candidate point at the same x coordinate.
# We store h_left, h_right, w_base, w_max, values for each candidate point
#   h_left is the difference betwen this candidate point and the first higher segment at this point's left
#   h_right is the same as h_left but difference with the first higher segment at right
#   w_base is width of the segment that this point sits on
#   w_max is the max width that we can place on this point

# We place a rectangle at each step. But how?
# We check for each point and unplaced rectangle pair
# We pick the best pair from these pairs. But how?
# If there is only one rectangle we can place on a point this pair has the highest priority.
#   If there are more than one pair like these or there is none, we pick the pair with the minimum wasted area.
#   If there is still a tie between two or more pairs, we pick the pair with the maximum fitness.
#   If there is still a tie between two or more pairs, we pick the pair with the rectangle that comes earliest in the input sequence.
#   If multiple pairs contains this rectangle, we pick the pair with the point with the lowest y value, if there is still tie we pick the point with the lowest x value.

# Once we find the best pair. We place the rectangular on that point. And update the segments. There will be deleted and inserted segments. 
# We find the candidate points and their h_left, h_right, w_base, w_max values at the beginning of each iteration

# At any iteration if we can't a single point rectangle pair to place we return with failure
# If we place all rectangles we return with success

# Spread Constraint
#   If difference between top of the placed rectangle and the lowest segment is greater than the max_spread value we completely reject these point-rectangle point
# Only Fit
#   If there is only one rectangle left to place for a point after the spread constraint, this pair has the highest priority to be picked as the best placement, record this point
# Min Waste
#   For each point we need to find the min waste. And the rectangle that gives this min waste value is the best rectangle for this point.
#   There can be more than more pair that gives the same min waste. If so we move to next step to find the best pair.
# Max Fitness
#   We find the pair or pairs with the maximum fitness value

