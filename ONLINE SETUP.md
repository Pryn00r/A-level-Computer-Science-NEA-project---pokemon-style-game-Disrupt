# Putting Disrupt online

Everything here is free. It takes about 30 minutes the first time.

## 0. Install the new library (once)

Open a terminal in this folder and run:

```
pip install -r requirements.txt
```

(It adds `websockets`, which the game uses to talk to the server.)

## 1. Try it on your own computer first

1. Double-click **Start Online Server.bat**. Leave that window open.
2. Double-click **Play Disrupt.bat** twice, so two copies of the game are open.
3. Sign in as a different account in each copy. Both copies share the same "stay signed in" file, so in the second copy press **Log Out** first and then sign in as someone else.
4. In both copies choose **Online** and type your password once.
5. In one copy choose **Find a player**, type the other account's name, then **Challenge**. Accept in the other copy.

## 2. The database (Neon)

The free server forgets everything when it restarts, so accounts and ratings are kept in a free database instead.

1. Go to **neon.com** and sign up (signing in with GitHub or Google is fine).
2. Create a project called `disrupt`. Pick the region closest to you (Europe).
3. On the project dashboard press **Connect** and copy the connection string. It starts with `postgresql://` and ends with `sslmode=require`. Keep it private, because it is the key to the database.

## 3. The code (GitHub)

1. Go to **github.com** and sign up.
2. Press **New repository**. Name it `disrupt-server`, choose **Private**, and press **Create repository**.
3. Click **uploading an existing file**. Drag in every file from the **Disrupt Server** folder, then press **Commit changes**.

If you change the game's battle rules later, run `python tools/make_server_folder.py` and upload the files again.

## 4. The server (Render)

1. Go to **render.com** and sign up with your GitHub account.
2. Press **New**, choose **Web Service**, and pick `disrupt-server`.
3. Fill in these settings:
   - Language: **Python 3**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python online_server.py`
   - Instance Type: **Free**
4. Under **Environment Variables**, add:
   - `DATABASE_URL` = the Neon connection string from step 2
   - `PYTHON_VERSION` = `3.12.8`
5. Press **Deploy**. When it says **Live**, copy the address at the top, which looks like `https://disrupt-server-abcd.onrender.com`.

**Send that address to Claude**, or do it yourself: make a file called `online_server.txt` in the `code (finish)` folder containing this one line:

```
wss://disrupt-server-abcd.onrender.com
```

Use your own address, with `wss://` instead of `https://`.

The free server goes to sleep after 15 minutes with nobody online. The first person to connect after that waits up to a minute; the game shows a message while it wakes up.

## 5. Giving the game to other people (itch.io)

1. Double-click **Build Disrupt.bat** and wait a few minutes. It makes `dist\Disrupt-Windows.zip`, so make sure `online_server.txt` is in place first.
2. Go to **itch.io**, sign up, and choose **Upload new project**.
3. Set Kind of project to **Downloadable**. Upload the zip and tick **Windows**.
4. Set it to **Public**, or to **Restricted** if only people with the link should see it. Then share the link.

Players download the zip, unzip it, and double-click **Disrupt.exe**. They don't need Python. Windows may show "Windows protected your PC" the first time, because the game isn't signed; they press **More info**, then **Run anyway**.
