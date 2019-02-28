import random
import time

HOLE_WEIGHT = 1.034
JAGGED_WEIGHT = 0.008

HEIGHT_POWER = 1.0
HOLE_POWER = 1.0
JAGGED_POWER = 1.0

RECURSION_DEPTH = 1

WELL_HEIGHT = 25
WELL_WIDTH = 10

block_chars = ['\x1b[%sm  \x1b[0m' % ';'.join(["1", "30", str(bg)]) for bg in range(40, 48)]

fitness_cache = {}
well_cache = {}

iBlock = [
	[1],
	[1],
	[1],
	[1]
]

jBlock = [
	[0, 2],
	[0, 2],
	[2, 2]
]

lBlock = [
	[3, 0],
	[3, 0],
	[3, 3]
]

zBlock = [
	[4, 4, 0],
	[0, 4, 4]
]

sBlock = [
	[0, 5, 5],
	[5, 5, 0]
]

tBlock = [
	[0, 6, 0],
	[6, 6, 6]
]

oBlock = [
	[7, 7],
	[7, 7]
]

blocks = [iBlock, jBlock, lBlock, zBlock, sBlock, tBlock, oBlock]
random.shuffle(blocks)


def print_well(well):
	print(" " + "=" * len(well[0]) * 2)
	print("|" + "|\n|".join("".join(block_chars[b] for b in row) for row in well) + "|")
	print(" " + "=" * len(well[0]) * 2)


class GameState(object):
	def __init__(self, well, hold, next_up, was_held=False):
		self.well = well
		self.hold = hold
		self.next_up = next_up
		self.was_held = was_held
		self.fitness = None

	def get_fitness(self):
		if self.fitness is None:
			self.fitness = self.calculate_fitness()
		return self.fitness

	def calculate_fitness(self):
		if not self.is_alive():
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
		total_fitness = row_fitness ** HEIGHT_POWER * 1.0 + hole_fitness ** HOLE_POWER * HOLE_WEIGHT + jagged_fitness ** JAGGED_POWER * JAGGED_WEIGHT
		return total_fitness

	def is_alive(self):
		return sum(self.well[0]) == 0

	def update_well_with_block(self, block, rotate, x_offset):
		def rotate_right(grid):
			return list(zip(*grid[::-1]))

		def rotate_left(grid):
			return list(zip(*grid))[::-1]

		if rotate == 1:
			new_block = rotate_right(block)
		elif rotate == 2:
			new_block = rotate_right(rotate_right(block))
		elif rotate == -1:
			new_block = rotate_left(block)
		else:
			new_block = block
		well_width = len(self.well[0])
		well_height = len(self.well)
		block_width = len(new_block[0])
		block_height = len(new_block)

		if block_width + x_offset > well_width:
			return None

		def find_highest_well_row():
			highest_well_row = well_height
			for x in range(block_width):
				current_block_row = block_height - 1
				while not new_block[current_block_row][x]:
					current_block_row -= 1

				current_well_row = 0
				while current_well_row < well_height and not self.well[current_well_row][x + x_offset]:
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
			for x in range(well_width):
				block_x = x - x_offset
				block_y = y - y_offset
				if 0 <= block_x < block_width and new_block[block_y][block_x]:
					new_well[y].append(new_block[block_y][block_x])
				else:
					new_well[y].append(self.well[y][x])
					if to_clear and new_well[y][x] == 0:
						to_clear = False
			if to_clear:
				del new_well[y]
				new_well.insert(0, [0 for _ in range(well_width)])

		y_offset = find_highest_well_row()

		return insert_block_into_well()


def find_max_fitness(state, recurse=0):
	possible_futures = []
	well = state.well
	blocks = state.next_up
	hold = state.hold
	block = blocks[0]
	for offset in range(WELL_WIDTH):
		for rotation in (0, 1, -1, 2):
			if rotation == -1 and block in (iBlock, zBlock, sBlock):
				break
			elif block is oBlock and rotation != 0:
				break
			future_state = GameState(state.update_well_with_block(block, rotation, offset), hold, blocks[1:])
			if future_state.well is not None:
				possible_futures.append(future_state)
	if not state.was_held:
		if hold is None:
			possible_futures.append(GameState(well, block, blocks[1:], was_held=True))
		else:
			possible_futures.append(GameState(well, block, [hold] + blocks[1:], was_held=True))
	if recurse:
		return min(possible_futures,
		           key=lambda future: find_max_fitness(future, recurse - 1).get_fitness())
	else:
		return min(possible_futures, key=lambda future: future.get_fitness())


def main():
	iterations_run = 0
	block_counts = []
	for _ in range(200):
		well = [[0] * WELL_WIDTH] * WELL_HEIGHT
		hold = None
		next_up = blocks[:]
		state = GameState(well, hold, next_up)
		block_count = 0
		while state.is_alive():
			if len(state.next_up) < len(blocks):
				random.shuffle(blocks)
				state.next_up += blocks
			best_future = find_max_fitness(state, recurse=RECURSION_DEPTH)

			# print("next up:")
			# for next in state.next_up[1:4]:
			# 	print_well(next)
			# if best_future.hold is not None:
			# 	print("hold:")
			# 	print_well(best_future.hold)
			# print_well(best_future.well)
			# print("best future", best_future.get_fitness())
			#
			# print(block_count)
			# time.sleep(0.25)

			state = best_future

			block_count += 1
			if block_count % 1000 == 0:
				print("block count:", block_count)
		iterations_run += 1
		block_counts.append(block_count)
		print("well died :( block_count:", block_count, "iterations run:", iterations_run)
		print("average:", sum(block_counts) / len(block_counts), "min:", min(block_counts), "max:", max(block_counts))
	print("hole_weight:", HOLE_WEIGHT, "jagged_weight:", JAGGED_WEIGHT, "average:",
	      sum(block_counts) / len(block_counts),
	      "min:", min(block_counts), "max:", max(block_counts))


if __name__ == "__main__":
	main()
