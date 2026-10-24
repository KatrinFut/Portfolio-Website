import sys
import os
import urllib.request
import threading
import numpy as np 		#numpy gives the 2D grid for the board
import pygame

#-------settings-------
ROW_COUNT = 6
COLUMN_COUNT = 7
SQ = 100						#size of one quare in pixels
RADIUS = SQ // 2 - 5			#radius of a circle (a bit smaller than the square)
WIDTH = COLUMN_COUNT * SQ 		#window width = 700
HEIGHT = (ROW_COUNT + 1) * SQ 	#window height = 700 (+1 for an extra top row for the hovering thingy piece)

HOLE_COL = COLUMN_COUNT // 2
HOLE_ROW = ROW_COUNT - 1

IMAGE_URL = "https://i.postimg.cc/G3qt6Rsg/Bild-2026-10-24-164850843.png"
IMAGE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "corner_picture.png")
IMAGE_MAX_SIZE = 120
CORNER_IMAGE = None
IMAGE_READY = False

BLUE = (0, 0, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)		#Player 1
YELLOW = (255, 255, 0)	#Player 2
WHITE = (240, 240, 240)
GRAY = (70, 70, 70)
PLAYER_COLORS = {1: RED, 2: YELLOW}

#A dictionary: each key BEATS its value. Rock beats scissors, etc.
BEATS = {"rock": "scissors", "scissors": "paper", "paper": "rock"}
CHOICES = ["rock", "paper", "scissors"]

#-------board functions-------

def create_board():
	#Makes a 6x7 grid filled iwht zeroes. 0 = empty spot
	return np.zeros((ROW_COUNT, COLUMN_COUNT))

def drop_piece(board, row, col, piece):
	#Puts a piece (1 or 2) into the chosen spot on the board
	board[row][col]= piece

def is_valid_location(board, col):
	#Checks the top row of that column. If it's still 0, the column isn't full
	return board[ROW_COUNT - 1][col] == 0

def get_next_open_row(board, col):
	#Looks from the bottom (row 0) upwards for the first empty spot, which is where a dropped piece would land
	for r in range(ROW_COUNT):
		if board[r][col]==0:
			return r

def print_board(board):
	#Row 0 is the BOTTOM of the board, but print shows row 0 first
	#np.flip(board, 0) flips it upside down so it looks right on the screen
	print(np.flip(board,0))

#-------drawing helpers-------

def draw_text(screen, text, y, font, color=WHITE):
	#Draws text horizontally centered at height y
	img = font.render(text, True, color)
	screen.blit(img, (WIDTH // 2 - img.get_width() // 2, y))

def download_corner_image():
	global IMAGE_READY
	if not os.path.exists(IMAGE_FILE):
		try:
			req = urllib.request.Request(IMAGE_URL, headers={"User-Agent": "Mozilla/5.0"})
			with urllib.request.urlopen(req, timeout=10) as response:
				data = response.read()
			with open(IMAGE_FILE + ".part", "wb") as f:
				f.write(data)
			os.replace(IMAGE_FILE + ".part", IMAGE_FILE)
		except Exception as e:
			print("Couldn't download the picture:", e)
			return
	IMAGE_READY = True

def load_corner_image():
	try:
		img = pygame.image.load(IMAGE_FILE).convert_alpha()
	except Exception as e:
		print("Couldn't load the picture:", e)
		os.remove(IMAGE_FILE)
		return None
	scale = IMAGE_MAX_SIZE / max(img.get_width(), img.get_height())
	return pygame.transform.smoothscale(img, (int(img.get_width() * scale), int(img.get_height() * scale)))

def draw_corner_image(screen):
	if CORNER_IMAGE is not None:
		screen.blit(CORNER_IMAGE, (WIDTH - CORNER_IMAGE.get_width(), HEIGHT - CORNER_IMAGE.get_height()))

def draw_board(screen, board):
	#Pieces: board row 0 is the bottom, but screen y=0 is the top so we flip it
	for c in range(COLUMN_COUNT):
		for r in range(ROW_COUNT):
			if board[r][c] != 0:
				color = PLAYER_COLORS[int(board[r][c])]
				pygame.draw.circle(screen, color, (c * SQ + SQ // 2, HEIGHT - r * SQ - SQ // 2), RADIUS)

	#Blue board with black "holes"
	board_surface = pygame.Surface((WIDTH, HEIGHT - SQ), pygame.SRCALPHA)
	board_surface.fill(BLUE)
	hole_center = (HOLE_COL * SQ + SQ // 2, (ROW_COUNT - 1 - HOLE_ROW) * SQ + SQ // 2)
	pygame.draw.circle(board_surface, (0, 0, 0, 0), hole_center, RADIUS)
	screen.blit(board_surface, (0, SQ))

def animate_drop(screen, clock, board, col, row, color):
	#Little falling animation
	x = col * SQ + SQ // 2
	target_y = HEIGHT - row * SQ - SQ // 2
	y, speed = SQ // 2, 0
	while y < target_y:
		pygame.event.pump()			#keeps the window responsive
		speed += 1.5				#falls faster and faster
		y = min(y + speed, target_y)
		screen.fill(BLACK)
		pygame.draw.circle(screen, color, (x, int(y)), RADIUS)
		draw_board(screen, board)
		draw_corner_image(screen)
		pygame.display.update()
		clock.tick(60)

def rps_buttons():
	#Three clickable rectangles: (name, rect)
	return [(name, pygame.Rect(30 + i * 225, 330, 190, 90)) for i, name in enumerate(CHOICES)]

def draw_rps_buttons(screen, font):
	mouse = pygame.mouse.get_pos()
	for name, rect in rps_buttons():
		color = (100, 100, 100) if rect.collidepoint(mouse) else GRAY		#highlighting on hovering over
		pygame.draw.rect(screen, color, rect, border_radius=12)
		label = font.render(name.upper(), True, WHITE)
		screen.blit(label, (rect.centerx - label.get_width() // 2, rect.centery - label.get_height() // 2))

def reset():
	return create_board(), "rps_p1", None, None, 0, ""

#-------main game-------

def main():
	global CORNER_IMAGE, IMAGE_READY
	pygame.init()
	screen = pygame.display.set_mode((WIDTH, HEIGHT))
	pygame.display.set_caption("Connect One")
	threading.Thread(target=download_corner_image, daemon=True).start()
	clock = pygame.time.Clock()
	big = pygame.font.SysFont("arial", 48, bold=True)
	mid = pygame.font.SysFont("arial", 32)
	small = pygame.font.SysFont("arial", 22)

	#state is one of: rps_p1, rps_p2, rps_result, play, gameover
	board, state, p1_choice, p2_choice, turn, result_text = reset()
	#turn 1 or 2 (whose turn it is / who won)

	while True:
		if IMAGE_READY and CORNER_IMAGE is None:
			IMAGE_READY = False
			CORNER_IMAGE = load_corner_image()

		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				pygame.quit()
				sys.exit()

			if event.type == pygame.MOUSEBUTTONDOWN:
				#-------rock paper scissors-------
				if state in ("rps_p1", "rps_p2"):
					for name, rect in rps_buttons():
						if rect.collidepoint(event.pos):
							if state == "rps_p1":
								p1_choice = name		#hidden from player 2
								state = "rps_p2"
							else:
								p2_choice = name		#single = to assign
								if p1_choice == p2_choice:
									result_text = "Tie! Click to go again."
									turn = 0
								elif BEATS[p1_choice] == p2_choice:
									result_text = "Player 1 wins and goes first!"
									turn = 1
								else:
									result_text = "Player 2 wins and goes first!"
									turn = 2
								state = "rps_result"
							break

				elif state == "rps_result":
					#Tie -> pick again, otherwise start the game
					state = "rps_p1" if turn == 0 else "play"

				#-------placing the ONE piece-------
				elif state == "play":
					col = event.pos[0] // SQ
					if col == HOLE_COL and is_valid_location(board, col):
						row = HOLE_ROW
						animate_drop(screen, clock, board, col, row, PLAYER_COLORS[turn])
						drop_piece(board, row, col, turn)
						state = "gameover"				#ONE piece = instant win

				#-------restart-------
				elif state == "gameover":
					board, state, p1_choice, p2_choice, turn, result_text = reset()

		#-------drawing-------
		screen.fill(BLACK)

		if state == "rps_p1":
			draw_text(screen, "CONNECT ONE", 80, big, YELLOW)
			draw_text(screen, "Rock Paper Scissors decides who goes first", 160, small)
			draw_text(screen, "Player 1: choose!", 250, mid, RED)
			draw_rps_buttons(screen, mid)

		elif state == "rps_p2":
			draw_text(screen, "CONNECT ONE", 80, big, YELLOW)
			draw_text(screen, "Player 1 has chosen. Don't peek!", 160, small)
			draw_text(screen, "Player 2: choose!", 250, mid, YELLOW)
			draw_rps_buttons(screen, mid)

		elif state == "rps_result":
			draw_text(screen, f"Player 1: {p1_choice.upper()}", 200, mid, RED)
			draw_text(screen, f"Player 2: {p2_choice.upper()}", 260, mid, YELLOW)
			draw_text(screen, result_text, 360, big)
			draw_text(screen, "(click to continue)", 450, small, GRAY)

		elif state == "play":
			draw_board(screen, board)
			#Hovering piece follows the mouse in the top row
			mx = min(max(pygame.mouse.get_pos()[0], RADIUS), WIDTH - RADIUS)
			pygame.draw.circle(screen, PLAYER_COLORS[turn], (mx, SQ // 2), RADIUS)

		elif state == "gameover":
			draw_board(screen, board)
			draw_text(screen, f"Player {turn} wins!", 25, mid, PLAYER_COLORS[turn])
			draw_text(screen, "(click to play again)", 70, small, WHITE)

		draw_corner_image(screen)
		pygame.display.update()
		clock.tick(60)

if __name__ == "__main__":
	main()