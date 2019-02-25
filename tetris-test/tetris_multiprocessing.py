import random
import sys
import time

from multiprocessing.pool import Pool
from multiprocessing import JoinableQueue


def print_well(well):
	print(" " + "=" * len(well[0]) * 2)
	print("|" + "|\n|".join("".join(block_chars[b] for b in row) for row in well) + "|")
	print(" " + "=" * len(well[0]) * 2)


def update_well_with_block(old_well, block, rotate, x_offset):
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
	well_width = len(old_well[0])
	well_height = len(old_well)
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
			while current_well_row < well_height and not old_well[current_well_row][x + x_offset]:
				current_well_row += 1

			if current_well_row - current_block_row - 1 < highest_well_row:
				highest_well_row = current_well_row - current_block_row - 1
		return highest_well_row

	def insert_block_into_well():
		new_well = []

		for y in range(0, y_offset):
			new_well.append(old_well[y][:])

		for y in range(max(0, y_offset), y_offset + block_height):
			insert_block_rows(new_well, y)

		for y in range(y_offset + block_height, well_height):
			new_well.append(old_well[y][:])

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
				new_well[y].append(old_well[y][x])
				if to_clear and new_well[y][x] == 0:
					to_clear = False
		if to_clear:
			del new_well[y]
			new_well.insert(0, [0 for _ in range(well_width)])

	y_offset = find_highest_well_row()

	return insert_block_into_well()


def evalutate_well_fitness(well):
	row_fitness = 0
	hole_fitness = 0
	well_height = len(well)
	well_width = len(well[0])
	for column in range(well_width):
		y = 0
		while y < well_height and well[y][column] == 0:
			y += 1
		if well_height - y > row_fitness:
			row_fitness = well_height - y
		while y < well_height:
			if well[y][column] == 0:
				hole_fitness += 1
			y += 1
	# print ("row_fitness", row_fitness, "hole_fitness", hole_fitness)
	return row_fitness * 1.0 + hole_fitness * 1.0


def is_well_alive(well):
	return sum(well[0]) == 0


block_chars = ['\x1b[%sm  \x1b[0m' % ';'.join(["1", "30", str(bg)]) for bg in range(40, 48)]

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

block_counts = []

blocks = [iBlock, jBlock, lBlock, zBlock, sBlock, tBlock, oBlock]
random.shuffle(blocks)
next_up = blocks.copy()
iterations_run = 0

inQueue = JoinableQueue()
outQueue = JoinableQueue()


def parallel_worker():
	while True:
		well, block, rotation, offset = inQueue.get()
		future_well = update_well_with_block(well, block, rotation, offset)
		if future_well is not None:
			future_fitness = evalutate_well_fitness(future_well)
			outQueue.put((future_well, future_fitness))
		inQueue.task_done()


pool = Pool(8)
for i in range(8):
	pool.apply_async(parallel_worker)

while True:
	well = [[0 for i in range(10)] for j in range(25)]
	block_count = 0
	while is_well_alive(well):
		random.shuffle(blocks)
		block = next_up.pop(0)
		if len(next_up) < len(blocks):
			random.shuffle(blocks)
			next_up += blocks
		possible_futures = []
		for offset in range(10):
			for rotation in (0, -1, 1, 2):
				if rotation == 2 and block in (iBlock, zBlock, sBlock):
					continue
				elif block is oBlock and rotation != 0:
					break
				inQueue.put((well, block, rotation, offset))
			# future_well = update_well_with_block(well, block, rotation, offset)
			# if future_well is not None:
			# 	possible_futures.append(future_well)

		inQueue.join()

		best_future, best_fitness = outQueue.get()
		while outQueue.qsize() != 0:
			new_future, new_fitness = outQueue.get()
			if new_fitness < best_fitness:
				best_future = new_future
				best_fitness = new_fitness
		# best_future = min(possible_futures, key=evalutate_well_fitness)

		# print("next up:")
		# for next in next_up[0:3]:
		# 	print_well(next)
		# print_well(best_future)
		# print("best future", evalutate_well_fitness(best_future))

		well = best_future

		# print(block_count)
		# time.sleep(0.1)

		block_count += 1
	iterations_run += 1
	print("well died :( block_count:", block_count, "iterations run:", iterations_run)
	block_counts.append(block_count)
