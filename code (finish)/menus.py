# menus.py
# All of the menu screens. In Iteration 18 this file was split into four smaller modules so each
# one is easier to read; this file just gathers them so the rest of the game can keep using
# "from menus import ...".
#   ui_base.py          - text helpers, themes, ScreenStack and the base screen classes
#   account_screens.py  - title screen, sign in, create account, passwords, account hub
#   game_screens.py     - shop, save slots, in-game menu, party, bag, starter choice, nicknames
#   info_screens.py     - leaderboard, search, settings, documents, map, badges, index, quests

from ui_base import *
from account_screens import *
from game_screens import *
from info_screens import *
