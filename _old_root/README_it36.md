# Disrupt

A monster-catching RPG made in Python with pygame-ce, for my A-level Computer Science NEA. Made by Prabnoor.

You were playing a monster game, and now you're stuck inside it. The only way out is to beat all three gym leaders: plant, fire and water.

## Running the game

1. Install Python 3.11 or newer.
2. Install the libraries. If the normal `pygame` is installed, uninstall it first, because it clashes with pygame-ce.
   ```
   pip uninstall pygame
   pip install -r requirements.txt
   ```
3. Start the game in one of these ways:
   - double-click **Play Disrupt.bat**
   - run `Create Desktop Shortcut.bat` once to get a desktop icon
   - run `python "code (finish)/main.py"` (this works from any folder)

## Controls

| Action | Keys |
|---|---|
| Move | Arrow keys or WASD |
| Sprint | Hold Shift |
| Talk / confirm | Space or Enter |
| Back / menu | Esc (in the game menu, "Back to Main Menu" saves and returns to the account menu) |
| Party | Enter (in the world) |
| Map | M |
| Fullscreen | F11 (the window can also be resized) |
| Fast travel | T |
| Index filter | F in the monster index |
| Stop an evolution | Esc while the monster is glowing |
| Battle log | L in a battle |
| Controller | Stick/D-pad to move, A = Space, B = Esc, X = Map, Y/Start = menu, right bumper = sprint |

The second key for moving and sprinting can be changed in Settings > Controls.

On a touch screen, buttons appear when you touch the screen and hide again when you use a keyboard or mouse.

## Running the tests

```
python "code (finish)/run_tests.py"
```

This runs every `test_*.py` file and prints a summary (16 files, from `test_core_subroutines` to `test_world_activities`). Each file can also be run on its own. `verify_saves.py` checks the checksums of the save files in `saves/`.

## Folder layout

| Folder | What's in it |
|---|---|
| `code (finish)/` | All the Python code; the game starts from `main.py` |
| `graphics/` | Images, tilesets and fonts |
| `audio/` | Music and sound effects |
| `data/maps/` | The Tiled maps (`.tmx`) |
| `tools/make_sfx.py` | Generates the chiptune sound effects (menus, catching, levelling up...) |
| `tools/make_music.py` | Generates the area and battle music (bounce beat with West African percussion; tense battle themes) |
| `tools/make_icons.py` | Draws the potion and ether bottle icons |
| `code (finish)/saves/` | Accounts, save slots and settings, created when the game first runs |

### Main code files

- **`main.py`**: the `Game` class (world, battles, saving, economy, HUD).
- **`battle.py`**: turn-based battles.
- **`monster.py`**: monster stats, levelling up and evolution.
- **`game_data.py`**: all the trainers, monsters, attacks, items, quests and shop data.
- **Menus** (`menus.py` gathers these together):
  - `ui_base.py`: text helpers, themes and the base screen classes
  - `account_screens.py`: title screen, signing in and accounts
  - `game_screens.py`: shop, save slots, the in-game menu, party, bag and starter choice
  - `info_screens.py`: leaderboard, search, settings, help documents, map, badges, index and quests
  - `ui_style.py`: the pixel-art frames, buttons and icons
- **`save_system.py`**: accounts with salted PBKDF2 passwords, and save files protected by a checksum and a backup.
  - The checksum spots damaged or hand-edited files. There is no secret key, though, so it is not cheat-proof.
- **`localisation.py`** and **`dialog_text.py`**: English, Italian and Spanish text.
- **`intro.py`** and **`ending.py`**: the opening and the ending.
- **`battle_rules.py`**: the type chart, priority, charge-up moves, accuracy, status effects and stat stages.
- **`looks.py`**, **`story_screens.py`**: the player's clothes colour and the monster box (both in the menu; the bedroom furniture and the rival were removed in Iteration 31).
- **`options.py`**: colour-blind colours, large text, difficulty, autosave, encounter rate and key bindings.
- **`outdoors.py`**: day and night and the step counter (fishing, digging, hidden items and Repel were removed in Iteration 31).
- **`records.py`**: achievements, daily and weekly quests, stats and where monsters live.
- **`training.py`**: training mode (Iteration 33).
- **`town.py`**, **`extra_screens.py`**: fast travel and local two-player battles (the daycare, crafting, move tutor, trading, bounties, phone calls and photo mode were removed in Iteration 31).
- **`postgame.py`**: the Glitch Zone, boss monsters and rematches.
- **`audio_manager.py`**, **`atmosphere.py`**, **`item_art.py`**: sound channels, weather and pictures drawn in code.
- Tools: `tools/make_sounds.py` (footsteps, ambience, hit sounds, monster cries, the battle-start sound), `tools/import_packs.py` and `tools/import_new_art.py` (copy the art below into `graphics/`).
- Iteration 36: fixed monsters with the same speed taking each other's turn (the battle seemed frozen), battles are now 1 v 1, 2 v 2 or 3 v 3 to match the other side, and B on the party screen opens the Monster Box.
- Iteration 35: the full badge art (wings, frame and gem), battle name tags and stats placed round each monster so nothing overlaps, ten moves removed and others renamed or changed after playtesting, new dark, ghost and fairy move types, new Solar Beam and Dark Pulse animations.
- Iteration 34: what each move does is shown in battle, attack animations are trimmed to the same size and drawn bigger for stronger moves, every move has its own animation, Inferno charges up, Esc leaves training (R resets it), clearer battle menus and stat pills.
- Iteration 33: training mode (menu > Training: any monster at level 50 with every move it learns, against a Pouch that never attacks and gets back up), 43 more moves so every attack animation is used, the green box when a monster fainted is fixed, and no repeated menu icons.
- Iteration 32: each monster uses 4 moves at a time (swap them with M on the party screen), new moves (heal, headbutt and confusion, fire pillar, lightning, acid, dark and plant moves), softer damage, stat icons and a turn bar in battle, gem badges, type icons, a loading spinner and controller button hints.

## Art packs (free, credited as their licences ask)

| Used for | Pack | By |
|---|---|---|
| Item and status icons | Shikashi's Fantasy Icons Pack v2 | Shikashi |
| Attack animations | Super Pixel Effects Gigapack (Free Version) | Will Tice / unTied Games |
| Attack animations | FREE 20+ VFX Pixel Art Asset Pack | ThePixelGame |
| Attack animations | Acid VFX, Dark VFX, Wood VFX, Fire Effect 2, Plants | itch.io free packs |
| Item and type icons | Openmon item icons | Openmon project |
| Spinner, gems, turn bar, menu and controller icons, heal/confused/pillar/acid-pool animations | the "New folder" UI and effect packs | itch.io free packs |

The original game art (maps, the 16 monsters, the player and all the other characters) is from the Python Monsters tutorial project.
