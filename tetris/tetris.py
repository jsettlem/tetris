import itertools
import random
import sys
import time

MULTIPROCESSESED = False
GO_FOR_TETRISES = True

if MULTIPROCESSESED:
	import pathos.pools as pp

pool = None

if GO_FOR_TETRISES:
	HOLE_WEIGHT = 1.1741144934787453 * 2
	JAGGED_WEIGHT = 0.04604025903232776 * 2
else:
	HOLE_WEIGHT = 1.1741144934787453
	JAGGED_WEIGHT = 0.04604025903232776

HEIGHT_POWER = 1.0
HOLE_POWER = 1.0
JAGGED_POWER = 1.0

RECURSION_DEPTH = 3

WELL_HEIGHT = 20
WELL_WIDTH = 10

block_chars = ['\x1b[%sm  \x1b[0m' % ';'.join(["1", "30", str(bg)]) for bg in range(40, 48)]

fitness_cache = {}
well_cache = {}

class Rotation(object):
	def __init__(self, grid, parent, rotation, initial_offset):
		self.grid = grid
		self.parent = parent
		self.rotation = rotation
		self.offset = initial_offset

class Block(object):
	def __init__(self, grid, rotations):
		self.grid = grid
		self.rotations = []
		for rotation, offset in rotations:
			if rotation == 1:
				new_grid = self.rotate_right(self.grid)
			elif rotation == 2:
				new_grid = self.rotate_right(self.rotate_right(self.grid))
			elif rotation == -1:
				new_grid = self.rotate_left(self.grid)
			else:
				new_grid = self.grid

			self.rotations.append(Rotation(new_grid, self, rotation, offset))

	@staticmethod
	def rotate_right(grid):
		return list(zip(*grid[::-1]))

	@staticmethod
	def rotate_left(grid):
		return list(zip(*grid))[::-1]


if GO_FOR_TETRISES:
	iBlock = Block([
		[1, 1, 1, 1]
	], ((1, 5),))
else:
	iBlock = Block([
		[1, 1, 1, 1]
	], ((0, 3), (1, 5)))

jBlock = Block([
	[2, 0, 0],
	[2, 2, 2],
], ((0, 3), (1, 4), (2, 3), (-1, 3)))

lBlock = Block([
	[0, 0, 3],
	[3, 3, 3]
], ((0, 3), (1, 4), (2, 3), (-1, 3)))

zBlock = Block([
	[4, 4, 0],
	[0, 4, 4]
], ((0, 3), (1, 4)))

sBlock = Block([
	[0, 5, 5],
	[5, 5, 0]
], ((0, 3), (1, 4)))

tBlock = Block([
	[0, 6, 0],
	[6, 6, 6]
], ((0, 3), (1, 4), (2, 3), (-1, 3)))

oBlock = Block([
	[7, 7],
	[7, 7]
], ((0, 4),))

blocks = [tBlock, zBlock, lBlock, iBlock, sBlock, oBlock,  jBlock]
bag = blocks[:]
random.shuffle(bag)


def print_well(well):
	print(" " + "=" * len(well[0]) * 2)
	print("|" + "|\n|".join("".join(block_chars[b] for b in row) for row in well) + "|")
	print(" " + "=" * len(well[0]) * 2)


class GameState(object):
	def __init__(self, well, hold, next_up, was_held=False, was_first_hold=False, rotation=None, offset=None):
		self.well = well
		self.hold = hold
		self.next_up = next_up
		self.was_held = was_held
		self.was_first_hold = was_first_hold
		if len(self.next_up) < len(bag):
			self.next_up += bag
			self.was_shuffled = True
		else:
			self.was_shuffled = False
		self.possible_futures = None
		self.fitness = None
		self.alive = self.is_alive()
		self.rotation = rotation
		self.offset = offset
		self.column_heights = self.find_highest_rows()

	def find_highest_rows(self):
		column_heights = [0] * WELL_WIDTH
		for x in range(WELL_WIDTH):
			current_well_row = 0
			while current_well_row < WELL_HEIGHT and not self.well[current_well_row][x]:
				current_well_row += 1

			column_heights[x] = WELL_HEIGHT - current_well_row

		return column_heights

	def get_fitness(self):
		if self.fitness is None:
			self.fitness = self.calculate_fitness()
		return self.fitness

	def calculate_fitness(self):
		if not self.alive:
			return 9999999

		row_fitness = 0
		hole_fitness = 0
		jagged_fitness = 0
		well_height = len(self.well)
		well_width = len(self.well[0])
		last_height = None
		for column in range(well_width):
			y = WELL_HEIGHT - self.column_heights[column]
			# while y < well_height and self.well[y][column] == 0:
			# 	y += 1
			if last_height is not None:
				jagged_fitness += abs(y - last_height)
			last_height = y
			if well_height - y > row_fitness:
				row_fitness = well_height - y
			while y < well_height:
				if self.well[y][column] == 0:
					hole_fitness += 1
				y += 1
		total_fitness = row_fitness + hole_fitness * HOLE_WEIGHT + jagged_fitness * JAGGED_WEIGHT
		return total_fitness

	def is_alive(self):
		for cell in self.well[0]:
			if cell:
				return False
		# bad_column = 2
		# for y in range(len(self.well)):
		# 	if self.well[y][bad_column]:
		# 		return False
		return True

	def do_a_tetris_move(self, block, x_offset):
		well_width = len(self.well[0])
		well_height = len(self.well)
		block_width = len(block[0])
		block_height = len(block)

		def find_highest_well_row():
			highest_well_row = well_height
			for x in range(block_width):
				current_block_row = block_height - 1
				while not block[current_block_row][x]:
					current_block_row -= 1

				# current_well_row = 0
				well_x = x + x_offset
				# while current_well_row < well_height and not self.well[current_well_row][well_x]:
				# 	current_well_row += 1

				current_well_row = WELL_HEIGHT - self.column_heights[well_x]

				if current_well_row - current_block_row - 1 < highest_well_row:
					highest_well_row = current_well_row - current_block_row - 1
			return highest_well_row

		def insert_block_into_well():
			new_well = []

			for y in range(0, y_offset):
				new_well.append(self.well[y][:])

			for y in range(max(0, y_offset), y_offset + block_height):
				insert_block_rows(new_well, y)

			for y in range(y_offset + block_height, well_height):
				new_well.append(self.well[y][:])

			return new_well

		def insert_block_rows(new_well, y):
			new_well.append([])
			to_clear = True
			block_y = y - y_offset
			for x in range(0, x_offset):
				new_well[y].append(self.well[y][x])
				if to_clear and new_well[y][x] == 0:
					to_clear = False

			for x in range(max(0, x_offset), x_offset + block_width):
				block_x = x - x_offset
				if block[block_y][block_x]:
					new_well[y].append(block[block_y][block_x])
				else:
					new_well[y].append(self.well[y][x])
					if to_clear and new_well[y][x] == 0:
						to_clear = False

			for x in range(x_offset + block_width, well_width):
				new_well[y].append(self.well[y][x])
				if to_clear and new_well[y][x] == 0:
					to_clear = False

			if to_clear:
				del new_well[y]
				new_well.insert(0, [0 for _ in range(well_width)])

		y_offset = find_highest_well_row()

		return insert_block_into_well()

	def find_max_fitness(self, recurse=RECURSION_DEPTH):
		if self.possible_futures is None:
			self.possible_futures = []
			block = self.next_up[0]
			for rotation in block.rotations:
				block_width = len(rotation.grid[0])
				max_offset = WELL_WIDTH - block_width + 1
				valid_offsets = range(max_offset)
				if GO_FOR_TETRISES and (block is not iBlock or not all(height >= 4 for height in self.column_heights[:-1])):
					valid_offsets = range(max_offset - 1)
				for offset in valid_offsets:
					future_well = self.do_a_tetris_move(rotation.grid, offset)
					self.possible_futures.append(GameState(future_well, self.hold, self.next_up[1:], rotation=rotation, offset=offset))
			if not self.was_held:
				if self.hold is None:
					self.possible_futures.append(GameState(self.well, block, self.next_up[1:], was_held=True, was_first_hold=True))
				else:
					self.possible_futures.append(
						GameState(self.well, block, [self.hold] + self.next_up[1:], was_held=True))
		if MULTIPROCESSESED and recurse == RECURSION_DEPTH:
			future_fitnesses = pool.map(lambda future: future.find_max_fitness(recurse - 1).get_fitness(),
			                            self.possible_futures)
			max_index = future_fitnesses.index(min(future_fitnesses))
			return self.possible_futures[max_index]
		elif recurse:
			self.possible_futures.sort(key=lambda future: future.get_fitness())
			self.possible_futures = self.possible_futures[:5]
			return min(self.possible_futures, key=lambda future: future.find_max_fitness(recurse - 1).get_fitness())
		else:
			return min(self.possible_futures, key=lambda future: future.get_fitness())


def main():
	iterations_run = 0
	block_counts = []
	last_time = time.time()
	for _ in range(100):
		well = [[0] * WELL_WIDTH] * WELL_HEIGHT
		hold = None
		next_up = bag[:]
		state = GameState(well, hold, next_up)
		block_count = 0
		while state.alive:
			best_future = state.find_max_fitness()
			if best_future.was_shuffled:
				random.shuffle(bag)

			print("next up:")
			for next in state.next_up[1:4]:
				print_well(next.grid)
			if best_future.hold is not None:
				print("hold:")
				print_well(best_future.hold.grid)
			print_well(best_future.well)
			print("best future", best_future.get_fitness())

			print(block_count)
			time.sleep(0.25)

			state = best_future

			block_count += 1
			if block_count % 1000 == 0:
				print("block count:", block_count)
				print("time:", time.time() - last_time)
				last_time = time.time()
		iterations_run += 1
		block_counts.append(block_count)
		print("well died :( block_count:", block_count, "iterations run:", iterations_run)
		print("average:", sum(block_counts) / len(block_counts), "min:", min(block_counts), "max:", max(block_counts))
	print("hole_weight:", HOLE_WEIGHT, "jagged_weight:", JAGGED_WEIGHT, "average:",
	      sum(block_counts) / len(block_counts),
	      "min:", min(block_counts), "max:", max(block_counts))
	return sum(block_counts) / len(block_counts)


if __name__ == "__main__":
	if len(sys.argv) > 1:
		HOLE_WEIGHT = float(sys.argv[1])
		JAGGED_WEIGHT = float(sys.argv[2])

	if MULTIPROCESSESED:
		with pp.ProcessPool(processes=8) as p:
			pool = p
			main()
	else:
		print(main())
