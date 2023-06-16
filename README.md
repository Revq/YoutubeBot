YoutubeBot - A Self-hosted Discord Bot for Playing YouTube Videos
=================================================================

Overview
--------

YoutubeBot is a self-hosted Discord bot that allows you to play YouTube videos directly in your Discord server. It provides a range of commands to control video playback, manage playlists, and interact with the bot. This README will guide you through the setup process to run the bot on your own server.

Table of Contents
-----------------

*   [Commands](#commands)
*   [Getting Started](#getting-started)
    *   [Step 1: Creating an Empty Bot](#step-1-creating-an-empty-bot)
    *   [Step 2: Adding it to Your Server](#step-2-adding-it-to-your-server)
    *   [Step 3: Cloning the Repository](#step-3-cloning-the-repository)
    *   [Step 4: Installing Dependencies](#step-4-installing-dependencies)
    *   [Step 5: Configuring the Bot](#step-5-configuring-the-bot)
    *   [Step 6: Starting the Bot](#step-6-starting-the-bot)
*   [Updating the Bot](#updating-the-bot)

Commands
--------

*   `.play {url or search}`: Plays or queues a video and joins the voice channel if not already connected.
    *   Alternate: `.p`
*   `.playlist`: Plays or queues a playlist of videos.
    *   Alternate: `.pl`
*   `.skip {n}`: Skips `n` videos. If no value is provided for `n`, it skips only one video. Use `.skip all` to skip every song and leave the voice channel.
    *   Alternate: `.s`
*   `.queue`: Shows a list of titles queued for playback.
    *   Alternate: `.q`
*   `.pause`: Pauses playback.
    *   Alternate: `.pu`
*   `.unpause`: Unpauses playback.
    *   Alternate: `.unp`
*   `.exit`: Clears the queue and leaves the voice channel.
    *   Alternate: `.e`
*   `.loop {All/Single/Off}`: Controls looping behavior. Use `All` to loop the entire queue, `Single` to play the current song indefinitely, and `Off` to disable looping.
    *   Alternate: `.l`
*   `.move {n} {x}`: Moves the song at position `n` in the queue to position `x`.
    *   Alternate: `.m`
*   `.remove {n}`: Removes the song at position `n` from the queue.
    *   Alternate: `.r`
*   `.current`: Shows the title and link of the currently playing song.
    *   Alternate: `.c`
*   `.shuffle`: Shuffles the current queue.
    *   Alternate: `.sh`
*   `.clear`: Clears the queue while keeping the currently playing song.
    *   Alternate: `.cl`

Getting Started
---------------

To run YoutubeBot on your server, follow the steps below:

### Step 1: Creating an Empty Bot

1.  Go to Discord's [developer portal](https://discord.com/developers/applications).
2.  Sign in if prompted and click the "New Application" button in the top right corner.
3.  Provide a name for your bot, e.g., "YoutubeBot."
4.  After creation, you can customize the bot's general info, such as the name, profile picture, and description (optional).
5.  In the sidebar, select "Bot" and click the "Add Bot" button.
6.  Set a username for your bot, which will be displayed in your server.
7.  Enable the "Message Content Intent" toggle to allow the bot to read command content. Make sure to save your changes.

### Step 2: Adding it to Your Server

1.  Navigate to the "OAuth2" page in the sidebar.
2.  Under "Scopes," select "bot," and under "Bot Permissions," select "Administrator." Alternatively, choose "Send Messages," "Connect," and "Speak" if you don't need the bot to work in private voice channels.
3.  Click "Copy" next to the generated URL and open it in your browser.
4.  Select your server from the dropdown and complete the captcha.

### Step 3: Cloning the Repository

1.  Open a terminal.
    
2.  Navigate to the directory where you want to clone the repository.
    
3.  Run the following command to clone the repository:
    
    ``` bash    
    git clone https://github.com/Revq/YoutubeBot.git
    ```

### Step 4: Installing Dependencies

1.  Navigate to the cloned repository's directory using the following command:
    
    ``` bash
    cd YoutubeBot
    ```
    
2.  Install the required dependencies by running the following command:
    
    ``` bash
    pip install -r requirements.txt
    ```
    
    If your system uses a different Python version, replace `pip` with the appropriate command (e.g., `pip3` or `pip3.10`).

    

### Step 5: Configuring the Bot

1.  Create a copy of the example environment file:  

    ``` bash
    cp .env_example .env
    ```
    
2.  Go back to the "Bot" page on Discord's developer portal. Under the "Token" section, click "Copy" to copy your bot's unique token
3.  Open the `.env` file and replace the placeholder `your-token-goes-here` with the token you copied:
  
    ``` bash
    nano .env
    ```

### Step 6: Starting the Bot

1.  Run the following command to start the bot in the background:
    
    ``` bash
    nohup ./youtubebot.py &
    ```    
    
    If you encounter a "permission denied" or "not executable" error, make the script executable by running the following command and try again:
    
    ``` bash    
    chmod +x youtubebot.py
    ```
    
2.  The bot is now running and ready to use. To stop it, run the following command:

    ``` bash
    pkill -f youtubebot.py
    ```
    
Congratulations! You have successfully set up YoutubeBot. You can now join a voice channel on your Discord server and use the provided commands to control YouTube video playback. If you encounter any issues, feel free to reach out for assistance.

Updating the Bot
----------------

To keep your YoutubeBot up to date with the latest changes and improvements, you can follow these steps to update the bot to the latest version from the repository:

1.  Open a terminal.
    
2.  Navigate to the directory where you have cloned the YoutubeBot repository.
    
3.  Pull the latest changes from the repository using the following command:
    
    ``` bash    
    git pull
    ```
    
4.  If there are any updates to the dependencies, you can install them by running the following command:
    
    ``` bash     
    pip install -r requirements.txt
    ```
    
    Make sure to use the appropriate `pip` command for your Python version (`pip3`, `pip3.10`, etc.) if needed.
    
5.  If there are any additional update instructions mentioned in the repository's documentation or release notes, follow those instructions to complete the update process.
    

That's it! Your YoutubeBot is now updated to the latest version. You can start the bot again using the instructions mentioned in [Step 6: Starting the Bot](#step-6-starting-the-bot).
