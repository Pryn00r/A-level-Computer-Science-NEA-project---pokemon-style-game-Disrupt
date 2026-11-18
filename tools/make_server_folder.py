# tools/make_server_folder.py
# Iteration 37: copies everything the online server needs into the folder "Disrupt Server", ready to be
# uploaded to GitHub and run on Render. The server uses the game's own rules (battle_rules.py, monster.py,
# game_data.py ...), so this is run again whenever those change, to keep the server the same as the game.
# Run with:  python tools/make_server_folder.py

import shutil
from os import makedirs
from os.path import abspath, dirname, join, isdir

ROOT = dirname(dirname(abspath(__file__)))
CODE = join(ROOT, 'code (finish)') if isdir(join(ROOT, 'code (finish)')) else join(ROOT, 'code')
OUT = join(ROOT, 'Disrupt Server')
FILES = ('online_server.py', 'online_engine.py', 'online_db.py', 'battle_rules.py', 'game_data.py', 'monster.py', 'settings.py', 'save_system.py')

REQUIREMENTS = 'websockets>=13.0\npsycopg[binary]>=3.1\npygame-ce>=2.5.0\n'

RENDER = '''services:
  - type: web
    name: disrupt-server
    runtime: python
    plan: free
    buildCommand: pip install -r requirements.txt
    startCommand: python online_server.py
    healthCheckPath: /
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.8
      - key: DATABASE_URL
        sync: false
'''

README = '''# Disrupt Server

The online server for Disrupt. Made by tools/make_server_folder.py - do not edit these files here,
edit them in the game's code folder and run the tool again.

Run on your own computer:  pip install -r requirements.txt   then   python online_server.py
(the game connects to ws://localhost:8765 unless online_server.txt says otherwise)
'''

makedirs(OUT, exist_ok = True)
for name in FILES:
	shutil.copyfile(join(CODE, name), join(OUT, name))
for name, text in (('requirements.txt', REQUIREMENTS), ('render.yaml', RENDER), ('README.md', README), ('.gitignore', '__pycache__/\n*.db\n')):
	with open(join(OUT, name), 'w', encoding = 'utf-8', newline = '\n') as file:
		file.write(text)
print('made', OUT)
