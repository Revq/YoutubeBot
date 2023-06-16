#!/usr/bin/env python3.10
import asyncio
import os
import re
import shutil
import subprocess as sp
import sys
import urllib
import urllib.parse
import random

import nextcord
import yt_dlp
from nextcord.ext import commands
from nextcord.ext import menus
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
PREFIX = os.getenv("BOT_PREFIX", ".")
PRINT_STACK_TRACE = os.getenv("PRINT_STACK_TRACE", "1").lower() in ("true", "t", "1")
BOT_REPORT_COMMAND_NOT_FOUND = os.getenv(
    "BOT_REPORT_COMMAND_NOT_FOUND", "1"
).lower() in ("true", "t", "1")
BOT_REPORT_DL_ERROR = os.getenv("BOT_REPORT_DL_ERROR", "0").lower() in (
    "true",
    "t",
    "1",
)
try:
    COLOR = int(os.getenv("BOT_COLOR", "ff0000"), 16)
except ValueError:
    print("the BOT_COLOR in .env is not a valid hex color")
    print("using default color ff0000")
    COLOR = 0xFF0000

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=nextcord.Intents.all(),
)
queues = {}  # {server_id: [(vid_file, info), ...]}
loop_modes = {}


def main():
    if TOKEN is None:
        return (
            "No token provided. Please create a .env file containing the token.\n"
            "For more information view the README.md"
        )
    try:
        bot.run(TOKEN)
    except nextcord.PrivilegedIntentsRequired as error:
        return error


class QueueMenu(menus.Menu):
    def __init__(self, ctx, queue):
        super().__init__(timeout=30.0)
        self.ctx = ctx
        self.queue = queue
        self.items_per_page = 20
        self.current_page = 1  # Initialize current page

    async def send_initial_message(self, ctx, channel):
        return await channel.send(embed=self._create_embed(self.current_page))

    def _create_embed(self, page_number):
        start_index = (page_number - 1) * self.items_per_page
        end_index = start_index + self.items_per_page
        queue_chunk = self.queue[start_index:end_index]

        embed = nextcord.Embed(color=COLOR)
        embed.add_field(
            name="Now playing:", value=self._format_queue(queue_chunk, start_index)
        )

        total_pages = (len(self.queue) + self.items_per_page - 1) // self.items_per_page
        if total_pages > 1:
            embed.set_footer(text=f"Page {page_number}/{total_pages}")

        return embed

    def _format_queue(self, queue_chunk, start_index):
        title_str = lambda val: (
            "‣ %s\n\n" % val
            if isinstance(val, str)
            else "**%2d:** %s\n" % (val[0] + start_index, val[1])
        )
        return "".join(map(title_str, enumerate([i[1]["title"] for i in queue_chunk])))

    @menus.button("\u23ee")  # First Page
    async def on_first_page(self, payload):
        self.current_page = 1  # Update current page
        await self.message.edit(embed=self._create_embed(self.current_page))

    @menus.button("\u25c0")  # Previous Page
    async def on_previous_page(self, payload):
        if self.current_page > 1:  # Check if not on the first page
            self.current_page -= 1  # Update current page
            await self.message.edit(embed=self._create_embed(self.current_page))

    @menus.button("\u25b6")  # Next Page
    async def on_next_page(self, payload):
        total_pages = (len(self.queue) + self.items_per_page - 1) // self.items_per_page
        if self.current_page < total_pages:  # Check if not on the last page
            self.current_page += 1  # Update current page
            await self.message.edit(embed=self._create_embed(self.current_page))

    @menus.button("\u23ed")  # Last Page
    async def on_last_page(self, payload):
        total_pages = (len(self.queue) + self.items_per_page - 1) // self.items_per_page
        self.current_page = total_pages  # Update current page
        await self.message.edit(embed=self._create_embed(self.current_page))


@bot.command(name="queue", aliases=["q"])
async def queue(ctx: commands.Context, *args):
    try:
        queue = queues[ctx.guild.id]
    except KeyError:
        queue = None

    if queue is None:
        await ctx.send("The bot isn't playing anything")
        return

    menu = QueueMenu(ctx, queue)
    await menu.start(ctx)

    if not await sense_checks(ctx):
        return


@bot.command(name="skip", aliases=["s"])
async def skip(ctx: commands.Context, *args):
    try:
        queue_length = len(queues[ctx.guild.id])
    except KeyError:
        queue_length = 0
    if queue_length <= 0:
        await ctx.send("The bot isn't playing anything")
    if not await sense_checks(ctx):
        return

    try:
        n_skips = int(args[0])
    except IndexError:
        n_skips = 1
    except ValueError:
        if args[0] == "all":
            n_skips = queue_length
        else:
            n_skips = 1
    if n_skips == 1:
        message = "Skipping track"
    elif n_skips < queue_length:
        message = f"skipping `{n_skips}` of `{queue_length}` tracks"
    else:
        message = "Skipping all tracks"
        n_skips = queue_length
    await ctx.send(message)

    voice_client = get_voice_client_from_channel_id(ctx.author.voice.channel.id)
    for _ in range(n_skips - 1):
        queues[ctx.guild.id].pop(0)
    voice_client.stop()


@bot.command(name="pause", aliases=["pu"])
async def pause(ctx: commands.Context):
    voice_client = get_voice_client_from_channel_id(ctx.author.voice.channel.id)
    if voice_client.is_playing():
        voice_client.pause()
        await ctx.send("Music paused.")
    else:
        await ctx.send("No music is currently playing.")


@bot.command(name="unpause", aliases=["unp"])
async def unpause(ctx: commands.Context):
    voice_client = get_voice_client_from_channel_id(ctx.author.voice.channel.id)
    if voice_client.is_paused():
        voice_client.resume()
        await ctx.send("Music resumed.")
    else:
        await ctx.send("Music is not paused.")


@bot.command(name="exit", aliases=["e"])
async def exit(ctx: commands.Context):
    voice_client = get_voice_client_from_channel_id(ctx.author.voice.channel.id)
    if voice_client is not None:
        server_id = ctx.guild.id
        queues.pop(server_id, None)  # Clear the queue
        loop_modes[server_id] = "off"  # Set loop mode to "off"
        await voice_client.disconnect()  # Disconnect from the voice channel
        await ctx.send("Bot has left the voice channel and the queue has been cleared.")
    else:
        await ctx.send("Bot is not currently in a voice channel.")


@bot.command(name="play", aliases=["p"])
async def play(ctx: commands.Context, *args):
    voice_state = ctx.author.voice
    if not await sense_checks(ctx, voice_state=voice_state):
        return

    query = " ".join(args)
    parsed_query = urllib.parse.urlparse(query)

    if (
        parsed_query.scheme != "http"
        and parsed_query.scheme != "https"
        and parsed_query.netloc != "www.youtube.com"
    ):
        await ctx.send("Invalid YouTube link.")
        return
    # this is how it's determined if the url is valid (i.e. whether to search or not) under the hood of yt-dlp
    will_need_search = not urllib.parse.urlparse(query).scheme

    server_id = ctx.guild.id

    # source address as 0.0.0.0 to force ipv4 because ipv6 breaks it for some reason
    # this is equivalent to --force-ipv4 (line 312 of https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/options.py)
    await ctx.send(f"Looking for `{query}`...")
    with yt_dlp.YoutubeDL(
        {
            "format": "worstaudio",
            "source_address": "0.0.0.0",
            "default_search": "ytsearch",
            "outtmpl": "%(id)s.%(ext)s",
            "noplaylist": True,
            "ignoreerrors": True,
            "allow_playlist_files": False,
            # 'progress_hooks': [lambda info, ctx=ctx: video_progress_hook(ctx, info)],
            # 'match_filter': lambda info, incomplete, will_need_search=will_need_search, ctx=ctx: start_hook(ctx, info, incomplete, will_need_search),
            "paths": {"home": f"./dl/{server_id}"},
        }
    ) as ydl:
        try:
            info = ydl.extract_info(query, download=False)
        except yt_dlp.utils.DownloadError as err:
            await notify_about_failure(ctx, err)
            return

        if "entries" in info:
            info = info["entries"][0]
        # send link if it was a search, otherwise send title as sending link again would clutter chat with previews
        await ctx.send(
            "Downloading "
            + (
                f'https://youtu.be/{info["id"]}'
                if will_need_search
                else f'`{info["title"]}`'
            )
        )
        try:
            ydl.download([query])
        except yt_dlp.utils.DownloadError as err:
            await notify_about_failure(ctx, err)
            return

        path = f'./dl/{server_id}/{info["id"]}.{info["ext"]}'
        try:
            queues[server_id].append((path, info))
        except KeyError:  # first in queue
            queues[server_id] = [(path, info)]
            try:
                connection = await voice_state.channel.connect()
            except nextcord.ClientException:
                connection = get_voice_client_from_channel_id(voice_state.channel.id)
            connection.play(
                nextcord.FFmpegOpusAudio(path),
                after=lambda error=None, connection=connection, server_id=server_id: after_track(
                    error, connection, server_id
                ),
            )


@bot.command(name="playlist", aliases=["pl"])
async def playlist(ctx: commands.Context, *args):
    voice_state = ctx.author.voice
    if not await sense_checks(ctx, voice_state=voice_state):
        return

    query = " ".join(args)
    parsed_query = urllib.parse.urlparse(query)

    if (
        parsed_query.scheme != "http"
        and parsed_query.scheme != "https"
        and parsed_query.netloc != "www.youtube.com"
    ):
        await ctx.send("Invalid YouTube link.")
        return
    await ctx.send(f"Adding playlist: `{query}`...")

    server_id = ctx.guild.id

    # Download the playlist information
    with yt_dlp.YoutubeDL({"extract_flat": "in_playlist", "simulate": True}) as ydl:
        try:
            info = ydl.extract_info(query, download=False)
        except yt_dlp.utils.DownloadError as err:
            await notify_about_failure(ctx, err)
            return

        if "entries" not in info:
            await ctx.send("No playlist found.")
            return

        playlist_entries = info["entries"]
        playlist_titles = [entry["title"] for entry in playlist_entries]
        await ctx.send(f"Playlist found: `{len(playlist_entries)}` videos.")

        # Add each video in the playlist to the queue
        for entry in playlist_entries:
            video_url = f'https://youtu.be/{entry["id"]}'
            await ctx.invoke(bot.get_command("play"), video_url)

    await ctx.send(f"Playlist added to the queue: `{len(playlist_entries)}` videos.")


@bot.command(name="loop", aliases=["l"])
async def loop(ctx: commands.Context, mode: str = None):
    server_id = ctx.guild.id
    if mode is None:
        current_mode = loop_modes.get(server_id, "off")
        await ctx.send(f"Current loop mode: {current_mode}")
        return

    mode = mode.lower()
    if mode not in ["all", "single", "off"]:
        await ctx.send("Invalid loop mode. Available modes: All, Single, Off")
        return

    loop_modes[server_id] = mode
    await ctx.send(f"Loop mode set to: {mode.capitalize()}")


@bot.command(name="current", aliases=["c"])
async def current(ctx: commands.Context):
    try:
        queue = queues[ctx.guild.id]
    except KeyError:
        queue = None

    if queue is None or len(queue) == 0:
        await ctx.send("No song is currently playing.")
    else:
        current_song = queue[0]
        title = current_song[1]["title"]
        video_id = current_song[1]["id"]
        youtube_link = f"https://youtu.be/{video_id}"
        embed_var = nextcord.Embed(color=COLOR, title="Currently Playing")
        embed_var.add_field(name="Title:", value=title, inline=False)
        embed_var.add_field(name="YouTube Link:", value=youtube_link, inline=False)
        await ctx.send(embed=embed_var)

    if not await sense_checks(ctx):
        return


@bot.command(name="remove", aliases=["r"])
async def remove(ctx: commands.Context, position: str):
    try:
        position = int(position)
        if position <= 0:
            raise ValueError
    except ValueError:
        await ctx.send("Invalid position.")
        return

    try:
        queue = queues[ctx.guild.id]
    except KeyError:
        await ctx.send("The bot isn't playing anything")
        return

    if position > len(queue):
        await ctx.send("Invalid position.")
        return

    removed_song = queue.pop(position)
    await ctx.send(f"Removed song '{removed_song[1]['title']}' from the queue.")


@bot.command(name="move", aliases=["m"])
async def move(
    ctx: commands.Context, queue_number: str = None, new_position: str = None
):

    # Check if both queue_number and new_position are provided
    if queue_number is None or new_position is None:
        await ctx.send("Please provide both the queue number and the new position.")
        return

    # Get the server ID
    server_id = ctx.guild.id

    try:
        # Get the queue for the server ID
        queue = queues[server_id]
    except KeyError:
        await ctx.send("The bot isn't playing anything")
        return

    # Get the length of the queue
    queue_length = len(queue)

    try:
        # Convert queue_number and new_position to integers
        queue_number = int(queue_number)
        new_position = int(new_position)
    except ValueError:
        await ctx.send("Invalid input. Please provide valid queue numbers")
        return

    # Validate the queue_number and new_position
    if (
        queue_number < 1
        or queue_number > queue_length
        or new_position < 1
        or new_position > queue_length
    ):
        await ctx.send("Invalid queue number or new position.")
        return

    # Check if the song is already in the specified position
    if queue_number == new_position:
        await ctx.send("The song is already in the specified position.")
        return

    # Move the song to the new position in the queue
    song = queue.pop(queue_number - 1)
    queue.insert(new_position - 1, song)

    await ctx.send(
        f"Moved song from position {queue_number} to {new_position} in the queue."
    )


@bot.command(name="shuffle", aliases=["sh"])
async def shuffle(ctx: commands.Context):
    try:
        queue = queues[ctx.guild.id]
    except KeyError:
        await ctx.send("The bot isn't playing anything.")
        return

    if len(queue) <= 1:
        await ctx.send("Not enough songs in the queue to shuffle.")
        return

    current_song = queue[0]  # Get the currently playing song (position 0)
    remaining_songs = queue[
        1:
    ]  # Get the remaining songs in the queue (excluding the currently playing song)
    random.shuffle(remaining_songs)  # Shuffle the remaining songs
    queue = [
        current_song
    ] + remaining_songs  # Create a new queue with the shuffled songs

    queues[ctx.guild.id] = queue  # Update the queue in the dictionary

    await ctx.send("Queue shuffled.")


@bot.command(name="clear", aliases=["cl"])
async def clear(ctx: commands.Context):
    try:
        queue = queues[ctx.guild.id]
    except KeyError:
        await ctx.send("The bot isn't playing anything")
        return

    current_song = queue[0]  # Get the currently playing song
    queues[ctx.guild.id] = [
        current_song
    ]  # Replace the queue with only the current song

    await ctx.send("Queue cleared.")


def get_voice_client_from_channel_id(channel_id: int):
    for voice_client in bot.voice_clients:
        if voice_client.channel.id == channel_id:
            return voice_client
    return None


def after_track(error, connection, server_id):
    if error is not None:
        print(error)

    try:
        path, info = queues[server_id].pop(0)
    except KeyError:
        return  # probably got disconnected

    loop_mode = loop_modes.get(server_id, "off")
    if loop_mode == "single":
        queues[server_id].insert(0, (path, info))
    elif loop_mode == "all":
        queues[server_id].append((path, info))

    if path not in [i[0] for i in queues[server_id]]:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass

    if loop_mode == "off" and len(queues[server_id]) == 0:
        # No more tracks in the queue and loop mode is "Off"
        queues.pop(server_id)  # directory will be deleted on disconnect
        asyncio.run_coroutine_threadsafe(safe_disconnect(connection), bot.loop).result()
    else:
        try:
            connection.play(
                nextcord.FFmpegOpusAudio(queues[server_id][0][0]),
                after=lambda error=None, connection=connection, server_id=server_id: after_track(
                    error, connection, server_id
                ),
            )
        except IndexError:  # that was the last item in queue
            queues.pop(server_id)  # directory will be deleted on disconnect
            asyncio.run_coroutine_threadsafe(
                safe_disconnect(connection), bot.loop
            ).result()


async def safe_disconnect(connection):
    if not connection.is_playing():
        await connection.disconnect()


async def sense_checks(ctx: commands.Context, voice_state=None) -> bool:
    if voice_state is None:
        voice_state = ctx.author.voice
    if voice_state is None:
        await ctx.send("You have to be in a voice channel to use this command")
        return False

    if (
        bot.user.id not in [member.id for member in ctx.author.voice.channel.members]
        and ctx.guild.id in queues.keys()
    ):
        await ctx.send(
            "You have to be in the same voice channel as the bot to use this command"
        )
        return False
    return True


@bot.event
async def on_voice_state_update(
    member: nextcord.User, before: nextcord.VoiceState, after: nextcord.VoiceState
):
    if member != bot.user:
        return
    if before.channel is None and after.channel is not None:  # joined vc
        return
    if before.channel is not None and after.channel is None:  # disconnected from vc
        # clean up
        server_id = before.channel.guild.id
        try:
            queues.pop(server_id)
        except KeyError:
            pass
        try:
            shutil.rmtree(f"./dl/{server_id}/")
        except FileNotFoundError:
            pass


@bot.event
async def on_command_error(
    ctx: nextcord.ext.commands.Context, err: nextcord.ext.commands.CommandError
):
    # now we can handle command errors
    if isinstance(err, nextcord.ext.commands.errors.CommandNotFound):
        if BOT_REPORT_COMMAND_NOT_FOUND:
            await ctx.send(
                "Command not recognized. To see available commands type {}help".format(
                    PREFIX
                )
            )
        return

    # we ran out of handlable exceptions, re-start. type_ and value are None for these
    sys.stderr.write(f"unhandled command error raised, {err=}")
    sp.run(["./restart"])


@bot.event
async def on_ready():
    print(f"logged in successfully as {bot.user.name}")


async def notify_about_failure(ctx: commands.Context, err: yt_dlp.utils.DownloadError):
    if BOT_REPORT_DL_ERROR:
        # remove shell colors for nextcord message
        sanitized = re.compile(r"\x1b[^m]*m").sub("", err.msg).strip()
        if sanitized[0:5].lower() == "error":
            # if message starts with error, strip it to avoid being redundant
            sanitized = sanitized[5:].strip(" :")
        await ctx.send("Failed to download due to error: {}".format(sanitized))
    else:
        await ctx.send("Sorry, failed to download this video")
    return


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemError as error:
        if PRINT_STACK_TRACE:
            raise
        else:
            print(error)
