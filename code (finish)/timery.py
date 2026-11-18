# timery.py
# Contains the Timer class, a reusable countdown used all over the game (encounter delay,
# opponent thinking time, dialogue delay, evolution animation, trainer look-around, etc.).
# Note: this file was originally called timer.py. It was renamed to timery.py because the name
# 'timer' clashed with an existing module/name, which caused an import error (see Iteration 1).

from pygame.time import get_ticks

class Timer:
	# Constructor.
	# Parameters: duration (integer, milliseconds), repeat (Boolean - restart automatically when finished),
	# autostart (Boolean - start counting straight away), func (function to call when the time is up, or None)
	def __init__(self, duration, repeat = False, autostart = False, func = None):
		self.duration = duration     # how long the timer lasts in milliseconds
		self.start_time = 0          # time in ms (from get_ticks) when the timer was activated
		self.active = False          # True while the timer is counting
		self.repeat = repeat
		self.func = func
		if autostart:
			self.activate()

	# Starts (or restarts) the timer from the current time.
	def activate(self):
		self.active = True
		self.start_time = get_ticks()

	# Stops the timer, and restarts it straight away if it is a repeating timer.
	def deactivate(self):
		self.active = False
		self.start_time = 0
		if self.repeat:
			self.activate()

	# Checks if the duration has passed. If it has, calls func (if there is one) and deactivates.
	# Must be called every frame by whatever owns the timer.
	def update(self):
		if self.active:
			current_time = get_ticks()
			if current_time - self.start_time >= self.duration:
				if self.func: self.func()
				self.deactivate()
