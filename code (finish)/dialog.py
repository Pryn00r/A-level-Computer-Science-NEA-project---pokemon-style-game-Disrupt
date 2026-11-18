# dialog.py
# Contains DialogTree, which steps through a character's lines of dialogue one at a time,
# and DialogSprite, which draws one line as a speech bubble above the character's head.

from settings import *
from timery import Timer
import controls
import localisation
from dialog_text import translate_line

# minimum time in ms a line stays on screen before space can skip it (stops lines being skipped by accident)
DIALOG_DELAY = 500

class DialogTree:
	# Constructor.
	# Parameters: character (Character speaking), player (Player), all_sprites (group to draw the bubble in),
	# font (dialogue font), end_dialog (function in Game called after the last line)
	def __init__(self, character, player, all_sprites, font, end_dialog):
		self.player = player
		self.character = character
		self.font = font
		self.all_sprites = all_sprites
		self.end_dialog = end_dialog

		self.dialog = character.get_dialog()   # list of lines (strings)
		self.dialog_num = len(self.dialog)     # number of lines
		self.dialog_index = 0                  # line currently shown

		self.current_dialog = self.create_line(self.dialog[self.dialog_index])
		self.dialog_timer = Timer(DIALOG_DELAY, autostart = True)

	# Iteration 14: a line can be a string (said by the character) or ('player', text) (said by the
	# player), so conversations can go back and forth. Returns the speech bubble for the line.
	# Iteration 18: lines are shown in the chosen language (see dialog_text.py).
	def create_line(self, line):
		if isinstance(line, tuple) and line[0] == 'player':
			return DialogSprite(translate_line(line[1], localisation.current_language), self.player, self.all_sprites, self.font, player_line = True)
		return DialogSprite(translate_line(line, localisation.current_language), self.character, self.all_sprites, self.font)

	# Space shows the next line (only once the delay timer has finished). After the last line,
	# calls end_dialog. Called from update.
	def input(self):
		keys = controls.get_just_pressed()
		if keys[pygame.K_SPACE] and not self.dialog_timer.active:
			self.current_dialog.kill()
			self.dialog_index += 1
			if self.dialog_index < self.dialog_num:
				self.current_dialog = self.create_line(self.dialog[self.dialog_index])
				self.dialog_timer.activate()
			else:
				self.end_dialog(self.character)

	# Called every frame from Game.run while a dialogue is open.
	def update(self):
		self.dialog_timer.update()
		self.input()

# Iteration 24: the top of the speaker's first "facing down" frame (their head), scaled to a height.
_portraits = {}
def face_portrait(character, height):
	frames = getattr(character, 'frames', None)
	if not isinstance(frames, dict) or not frames.get('down'):
		return None
	frame = frames['down'][0]
	key = (id(frame), height)
	if key not in _portraits:
		box = frame.get_bounding_rect()
		if box.width < 4 or box.height < 4:
			return None
		face = frame.subsurface(pygame.Rect(box.left, box.top, box.width, min(box.height, int(box.width * 0.8))))
		_portraits[key] = pygame.transform.scale_by(face, height / face.get_height())
	return _portraits[key]


class DialogSprite(pygame.sprite.Sprite):
	# Builds a rounded white speech bubble containing one line of text.
	# Parameters: message (string), character (Character/Player to place it above), groups, font,
	# player_line (True for the player's own lines, which get a blue bubble so it is clear who is talking)
	def __init__(self, message, character, groups, font, player_line = False):
		super().__init__(groups)
		self.z = WORLD_LAYERS['top']   # drawn above everything else in the world

		# text
		text_surf = font.render(message, False, COLORS['black'])
		padding = 5                                              # gap between the text and the edge of the bubble
		# Iteration 24: a small picture of the speaker's face on the left of the bubble
		portrait = face_portrait(character, max(30, text_surf.get_height()))
		face_width = portrait.get_width() + padding if portrait else 0
		width = max(30, text_surf.get_width() + padding * 2 + face_width)     # bubble is at least 30 px wide
		height = max(text_surf.get_height(), portrait.get_height() if portrait else 0) + padding * 2

		# background
		surf = pygame.Surface((width, height), pygame.SRCALPHA)
		surf.fill((0,0,0,0))
		pygame.draw.rect(surf, COLORS['blue'] if player_line else COLORS['pure white'], surf.get_frect(topleft = (0,0)),0, 4)
		if portrait:
			frame = portrait.get_frect(midleft = (padding, height / 2))
			pygame.draw.rect(surf, (225, 225, 230) if not player_line else (120, 190, 220), frame.inflate(2, 2), 0, 3)
			surf.blit(portrait, frame)
		surf.blit(text_surf, text_surf.get_frect(center = (face_width + (width - face_width) / 2, height / 2)))

		self.image = surf
		self.rect = self.image.get_frect(midbottom = character.rect.midtop + vector(0,-10))
