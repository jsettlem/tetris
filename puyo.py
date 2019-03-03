import os

import numpy as np
import cv2
import serial
from tetris.tetris import *

print("Hello world!")

going = False

NEXT_UP_DIMENSIONS = (55, 40)
NEXT_UP_X = 480
NEXT_UP_Y = 120
NEXT_UP_Y_GAP = 67

# ser = serial.Serial("COM6", 38400, writeTimeout=0)

cap = cv2.VideoCapture(3)

l_block = 17
o_block = 25
s_block = 49
z_block = 75
i_block = 91
j_block = 100
t_block = 148
block_hues = t_block, z_block, l_block, i_block, s_block, o_block, j_block
block_names = ["T", "Z", "L", "I", "S", "O", "J"]
cap.set(3, 1280)
cap.set(4, 720)
state = None
last_block = None
fsm_state = "START"
try:
	last_up = []
	while True:
		ret, frame = cap.read()
		cv2.imshow('frame', frame)
		w = cv2.waitKey(1) & 0xFF
		next_ups = []
		average_hues = []
		for i in range(5):
			x1 = NEXT_UP_X
			x2 = x1 + NEXT_UP_DIMENSIONS[0]
			y1 = NEXT_UP_Y + NEXT_UP_Y_GAP * i
			y2 = NEXT_UP_Y + NEXT_UP_Y_GAP * i + NEXT_UP_DIMENSIONS[1]
			img = frame[y1:y2, x1:x2]
			img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
			img_hsv = img_hsv.reshape((img.shape[0] * img.shape[1], 3))
			# rows = np.where(img_hsv[:, 2] > 50)
			rows = [p[0] for p in img_hsv if p[2] > 200 > p[1]]
			# average_hue = np.average(img_hsv[rows, 0])
			average_hue = np.average(rows)
			block_index = block_hues.index(min(block_hues, key=lambda b: abs(b - average_hue)))
			next_ups.append(block_names[block_index])
			average_hues.append(average_hue)
		# print(np.round(average_hues))
		if w == ord('q'):
			break
		if w == ord('s'):
			if not going:
				print("s time!")
				next_up = [blocks[block_names.index(block)] for block in next_ups]
				well = [[0] * WELL_WIDTH] * WELL_HEIGHT
				hold = None
				state = GameState(well, hold, next_up)
				going = True
				last_block = next_up[0]
				fsm_state = "START"


		if going:
			if fsm_state == "START":
				if last_up[0] != next_ups[0]:
					print("The game has started")
					fsm_state = "BLOCK_PLACED"
			elif fsm_state == "BLOCK_PLACED":
				print("the block has been placeD!")
				next_up = [blocks[block_names.index(block)] for block in next_ups]
				state.next_up = [last_block] + next_up
				best_future = state.find_max_fitness(recurse=1)
				for next in best_future.next_up[:3]:
					print_well(next.grid)
				print_well(best_future.well)
				state = best_future
				state.possible_futures = None
				last_block = next_up[0]
				fsm_state = "PLACING_BLOCK"
			elif fsm_state == "PLACING_BLOCK":
				if last_up[:3] != next_ups[:3]:
					fsm_state = "BLOCK_PLACED"
		if next_ups[:3] != last_up[:3]:
			# print(next_ups)
			last_up = next_ups[:]
		last_up = next_ups[:]
finally:
	cap.release()

