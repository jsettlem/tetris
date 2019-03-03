import random
import sys
import time

MULTIPROCESSESED = False

if MULTIPROCESSESED:
	import pathos.pools as pp

pool = None

# HOLE_WEIGHT = 1.034
# JAGGED_WEIGHT = 0.008

HOLE_WEIGHT = 1.1741144934787453
JAGGED_WEIGHT = 0.04604025903232776

HEIGHT_POWER = 1.0
HOLE_POWER = 1.0
JAGGED_POWER = 1.0

RECURSION_DEPTH = 3

WELL_HEIGHT = 25
WELL_WIDTH = 10

block_chars = ['\x1b[%sm  \x1b[0m' % ';'.join(["1", "30", str(bg)]) for bg in range(40, 48)]

fitness_cache = {}
well_cache = {}


class Block(object):
	def __init__(self, grid, rotations):
		self.grid = grid
		self.rotations = []
		for rotation in rotations:
			if rotation == 1:
				self.rotations.append(self.rotate_right(self.grid))
			elif rotation == 2:
				self.rotations.append(self.rotate_right(self.rotate_right(self.grid)))
			elif rotation == -1:
				self.rotations.append(self.rotate_left(self.grid))
			else:
				self.rotations.append(self.grid)

	@staticmethod
	def rotate_right(grid):
		return list(zip(*grid[::-1]))

	@staticmethod
	def rotate_left(grid):
		return list(zip(*grid))[::-1]


iBlock = Block([
	[1],
	[1],
	[1],
	[1]
], (0, 1))

jBlock = Block([
	[0, 2],
	[0, 2],
	[2, 2]
], (0, 1, 2, -1))

lBlock = Block([
	[3, 0],
	[3, 0],
	[3, 3]
], (0, 1, 2, -1))

zBlock = Block([
	[4, 4, 0],
	[0, 4, 4]
], (0, 1))

sBlock = Block([
	[0, 5, 5],
	[5, 5, 0]
], (0, 1))

tBlock = Block([
	[0, 6, 0],
	[6, 6, 6]
], (0, 1, 2, -1))

oBlock = Block([
	[7, 7],
	[7, 7]
], (0,))

blocks = [iBlock, jBlock, lBlock, zBlock, sBlock, tBlock, oBlock]
random.shuffle(blocks)


def print_well(well):
	print(" " + "=" * len(well[0]) * 2)
	print("|" + "|\n|".join("".join(block_chars[b] for b in row) for row in well) + "|")
	print(" " + "=" * len(well[0]) * 2)


class Well(object):
	def __init__(self, columns, rows):
		self.columns = columns
		self.rows = rows

	def clear_row(self, row):
		del self.rows[row]
		self.rows.insert(0, 0)

		for column in self.columns:
			pass

	def do_a_tetris_move(self, block, xoffset):
		pass

	def get_fitness(self):
		pass

	def calculate_fitness(self):
		pass

	def is_alive(self):
		pass


class GameState(object):
	def __init__(self, well, hold, next_up, was_held=False):
		self.well = well
		self.hold = hold
		self.next_up = next_up
		self.was_held = was_held
		if len(self.next_up) < len(blocks):
			self.next_up += blocks
			self.was_shuffled = True
		else:
			self.was_shuffled = False
		self.possible_futures = None
		self.fitness = None
		self.alive = self.is_alive()

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
			y = 0
			while y < well_height and self.well[y][column] == 0:
				y += 1
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

				current_well_row = 0
				well_x = x + x_offset
				while current_well_row < well_height and not self.well[current_well_row][well_x]:
					current_well_row += 1

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
				block_width = len(rotation[0])
				max_offset = WELL_WIDTH - block_width + 1
				# if block is iBlock:
				# 	max_offset = WELL_WIDTH - block_width + 1
				# else:
				# 	max_offset = WELL_WIDTH - block_width
				for offset in range(max_offset):
					future_well = self.do_a_tetris_move(rotation, offset)
					self.possible_futures.append(GameState(future_well, self.hold, self.next_up[1:]))
			if not self.was_held:
				if self.hold is None:
					self.possible_futures.append(GameState(self.well, block, self.next_up[1:], was_held=True))
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
		next_up = blocks[:]
		state = GameState(well, hold, next_up)
		block_count = 0
		while state.alive:
			best_future = state.find_max_fitness()
			if best_future.was_shuffled:
				random.shuffle(blocks)

			# print("next up:")
			# for next in state.next_up[1:4]:
			# 	print_well(next.grid)
			# if best_future.hold is not None:
			# 	print("hold:")
			# 	print_well(best_future.hold.grid)
			# print_well(best_future.well)
			# print("best future", best_future.get_fitness())
			#
			# print(block_count)
			# time.sleep(0.25)

			state = best_future

			block_count += 1
			if block_count % 100 == 0:
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
