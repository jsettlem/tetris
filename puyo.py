import os
import threading

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

A_BUTTON = 0b00010000
B_BUTTON = 0b10000000
L_BUTTON = 0b00001000
xp = 0
yp = 0
to_press = 0

cap = cv2.VideoCapture(3)

to_direct = 0
to_rotate = 0
to_hold = False
hard_droppin = False

l_hue = 17
o_hue = 25
s_hue = 49
z_hue = 75
i_hue = 91
j_hue = 100
t_hue = 148
block_hues = t_hue, z_hue, l_hue, i_hue, s_hue, o_hue, j_hue
block_names = ["T", "Z", "L", "I", "S", "O", "J"]
cap.set(3, 1280)
cap.set(4, 720)


def main():
	global going
	global xp
	global yp
	global to_direct
	global to_press
	global to_rotate
	global hard_droppin
	global to_hold
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
			for i in range(3):
				x1 = NEXT_UP_X
				x2 = x1 + NEXT_UP_DIMENSIONS[0]
				y1 = NEXT_UP_Y + NEXT_UP_Y_GAP * i
				y2 = NEXT_UP_Y + NEXT_UP_Y_GAP * i + NEXT_UP_DIMENSIONS[1]
				img = frame[y1:y2, x1:x2]
				img_hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
				img_hsv = img_hsv.reshape((img.shape[0] * img.shape[1], 3))
				rows = [p[0] for p in img_hsv if p[2] > 200 > p[1]]
				average_hue = np.average(rows)
				block_index = block_hues.index(min(block_hues, key=lambda b: abs(b - average_hue)))
				next_ups.append(block_names[block_index])
				average_hues.append(average_hue)
			# print(np.round(average_hues))
			if w == ord('a'):
				xp = -127
			elif w == ord('d'):
				xp = 127
			else:
				xp = 0

			if w == ord('w'):
				yp = -127
			elif w == ord('s'):
				yp = 127
			else:
				yp = 0

			if w == ord(' '):
				to_press = A_BUTTON
			elif w == ord('z'):
				to_press = B_BUTTON
			else:
				to_press = 0

			if w == ord('q'):
				break
			if w == ord('b'):
				if not going:
					print("start time!")
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
				elif fsm_state == "PLACING_BLOCK":
					if last_up[:3] != next_ups[:3]:
						fsm_state = "BLOCK_PLACED"
				if fsm_state == "BLOCK_PLACED":
					print("the block has been placeD!")
					next_up = [blocks[block_names.index(block)] for block in next_ups]
					if state.was_first_hold or not state.was_held:
						state.next_up = [last_block] + next_up
					best_future = state.find_max_fitness(recurse=2)
					if best_future.was_held:
						to_hold = True
					else:
						to_rotate = best_future.rotation.rotation
						to_direct = best_future.offset - best_future.rotation.offset
						hard_droppin = True
						print("last placed:")
						print_well(best_future.rotation.grid)
						print("rotation:", best_future.rotation.rotation, "offset:", best_future.offset)
					last_block = next_up[0]
					print ("next up:")
					for next in best_future.next_up[:3]:
						print_well(next.grid)
					if best_future.hold:
						print("Hold:")
						print_well(best_future.hold.grid)
					print("was_held:", best_future.was_held, "was first hold:", best_future.was_first_hold)
					print_well(best_future.well)
					state = best_future
					state.possible_futures = None

					# time.sleep(0.1)

					if state.was_first_hold or not state.was_held:
						fsm_state = "PLACING_BLOCK"


			if next_ups[:3] != last_up[:3]:
				# print(next_ups)
				last_up = next_ups[:]
			last_up = next_ups[:]


	finally:
		cap.release()


def serial_loop():
	global xp
	global yp
	global to_press
	global to_direct
	global to_rotate
	global hard_droppin
	global to_hold
	ser = serial.Serial("COM6", 57600, writeTimeout=0)
	try:
		while True:
			if not going:
				ser.write(bytearray([xp + 128, yp + 128, 128, 128, to_press]))
				ser.read()
			else:
				# if to_direct != 0 or to_rotate != 0:
				# 	print(to_direct, to_rotate)
				if to_hold:
					to_press = L_BUTTON
					to_hold = False
				else:
					if to_direct > 0:
						xp = 127
						to_direct -= 1
					elif to_direct < 0:
						xp = -128
						to_direct += 1
					else:
						xp = 0

					if to_rotate > 0:
						to_press = A_BUTTON
						to_rotate -= 1
					elif to_rotate < 0:
						to_press = B_BUTTON
						to_rotate += 1
					else:
						to_press = 0

				if to_press != 0 or xp != 0:
					ser.write(bytearray([xp + 128, yp + 128, 128, 128, to_press]))
					ser.read()
					time.sleep(1/45)

					ser.write(bytearray([128, 128, 128, 128, 0]))
					ser.read()
					time.sleep(1/45)
				elif hard_droppin:
					hard_droppin = False
					ser.write(bytearray([128, 0, 128, 128, 0]))
					ser.read()
					time.sleep(1/45)
					ser.write(bytearray([128, 128, 128, 128, 0]))
					ser.read()
				else:
					ser.write(bytearray([128, 128, 128, 128, 0]))
					ser.read()


	finally:
		print("the end")
		ser.close()


serial_thread = threading.Thread(target=serial_loop)
serial_thread.daemon = True
serial_thread.start()

if __name__ == "__main__":
	main()
