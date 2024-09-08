import asyncio
import os
import re
from typing import Union, List, Tuple, Dict

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch

from AnonXMusic.utils.database import is_on_off
from AnonXMusic.utils.formatters import time_to_seconds

async def shell_cmd(cmd: str) -> str:
    """Runs a shell command and returns its output. Handles errors."""
    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, errorz = await proc.communicate()
        if errorz:
            error_msg = errorz.decode("utf-8")
            if "unavailable videos are hidden" in error_msg.lower():
                return out.decode("utf-8")
            else:
                print(f"Shell command error: {error_msg}")
                return error_msg
        return out.decode("utf-8")
    except Exception as e:
        print(f"Exception running shell command: {e}")
        return str(e)

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: Union[bool, str] = None) -> bool:
        """Checks if a YouTube link exists."""
        if videoid:
            link = self.base + link
        return re.search(self.regex, link) is not None

    async def url(self, message_1: Message) -> Union[str, None]:
        """Extracts URL from a message."""
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        for message in messages:
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        return message.text[entity.offset: entity.offset + entity.length]
            if message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        return None

    async def details(self, link: str, videoid: Union[bool, str] = None) -> Tuple[Union[str, None], Union[str, None], int, Union[str, None], Union[str, None]]:
        """Fetches details of a YouTube video."""
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        try:
            results = VideosSearch(link, limit=1)
            result = (await results.next())["result"][0]
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            duration_sec = int(time_to_seconds(duration_min)) if duration_min else 0
            return title, duration_min, duration_sec, thumbnail, vidid
        except Exception as e:
            print(f"Error fetching details: {e}")
            return None, None, 0, None, None

    async def title(self, link: str, videoid: Union[bool, str] = None) -> Union[str, None]:
        """Fetches the title of a YouTube video."""
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        try:
            results = VideosSearch(link, limit=1)
            result = (await results.next())["result"][0]
            return result["title"]
        except Exception as e:
            print(f"Error fetching title: {e}")
            return None

    async def duration(self, link: str, videoid: Union[bool, str] = None) -> Union[str, None]:
        """Fetches the duration of a YouTube video."""
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        try:
            results = VideosSearch(link, limit=1)
            result = (await results.next())["result"][0]
            return result["duration"]
        except Exception as e:
            print(f"Error fetching duration: {e}")
            return None

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None) -> Union[str, None]:
        """Fetches the thumbnail URL of a YouTube video."""
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        try:
            results = VideosSearch(link, limit=1)
            result = (await results.next())["result"][0]
            return result["thumbnails"][0]["url"].split("?")[0]
        except Exception as e:
            print(f"Error fetching thumbnail: {e}")
            return None

    async def video(self, link: str, videoid: Union[bool, str] = None) -> Tuple[int, Union[str, None]]:
        """Fetches the video URL."""
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        try:
            proc = await asyncio.create_subprocess_exec(
                "yt-dlp",
                "-g",
                "-f",
                "best[height<=?720][width<=?1280]",
                f"{link}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            if stdout:
                return 1, stdout.decode().split("\n")[0]
            else:
                return 0, stderr.decode()
        except Exception as e:
            print(f"Error fetching video URL: {e}")
            return 0, str(e)

    async def playlist(self, link: str, limit: int, videoid: Union[bool, str] = None) -> List[str]:
        """Fetches playlist items."""
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        try:
            playlist = await shell_cmd(
                f"yt-dlp -i --get-id --flat-playlist --playlist-end {limit} --skip-download {link}"
            )
            return [item for item in playlist.split("\n") if item]
        except Exception as e:
            print(f"Error fetching playlist: {e}")
            return []

    async def track(self, link: str, videoid: Union[bool, str] = None) -> Tuple[Dict[str, Union[str, None]], Union[str, None]]:
        """Fetches track details."""
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        try:
            results = VideosSearch(link, limit=1)
            result = (await results.next())["result"][0]
            title = result["title"]
            duration_min = result["duration"]
            vidid = result["id"]
            yturl = result["link"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            track_details = {
                "title": title,
                "link": yturl,
                "vidid": vidid,
                "duration_min": duration_min,
                "thumb": thumbnail,
            }
            return track_details, vidid
        except Exception as e:
            print(f"Error fetching track: {e}")
            return None, None

    async def formats(self, link: str, videoid: Union[bool, str] = None) -> Tuple[List[Dict[str, Union[str, None]]], str]:
        """Fetches available formats for the video."""
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        try:
            ydl_opts = {"quiet": True}
            ydl = yt_dlp.YoutubeDL(ydl_opts)
            with ydl:
                formats_available = []
                r = ydl.extract_info(link, download=False)
                for format in r["formats"]:
                    if "dash" in str(format["format"]).lower():
                        continue
                    try:
                        formats_available.append(
                            {
                                "format": format["format"],
                                "filesize": format.get("filesize"),
                                "format_id": format.get("format_id"),
                                "ext": format["ext"],
                                "format_note": format.get("format_note"),
                                "yturl": link,
                            }
                        )
                    except KeyError:
                        continue
            return formats_available, link
        except Exception as e:
            print(f"Error fetching formats: {e}")
            return [], link

    async def slider(
        self,
        link: str,
        query_type: str,
        download: bool,
        format_id: Union[str, None] = None,
    ) -> Tuple[Union[str, None], Union[str, None]]:
        """Handles downloading and streaming of videos."""
        try:
            video_id = link
            if query_type == "video":
                ytlink = f"https://youtu.be/{video_id}"
            elif query_type == "playlist":
                ytlink = f"https://youtube.com/playlist?list={video_id}"
            elif query_type == "url":
                ytlink = link
            else:
                return None, "Invalid query type"

            if download:
                command = f"yt-dlp -f {format_id} {ytlink} --quiet --no-warnings --no-progress"
                output = await shell_cmd(command)
                return output, None
            else:
                output, _ = await self.video(link)
                if output:
                    return output, None
                return None, "Unable to fetch video URL"
        except Exception as e:
            print(f"Error in slider method: {e}")
            return None, str(e)

    async def download(
        self,
        link: str,
        videoid: Union[bool, str] = None,
        format_id: Union[str, None] = None,
        download: bool = True,
    ) -> Tuple[Union[str, None], Union[str, None]]:
        """Handles video downloading and returns the file path."""
        try:
            if videoid:
                link = self.base + link
            if "&" in link:
                link = link.split("&")[0]

            file_path = f"downloads/{videoid}.mp4" if videoid else "downloads/temp.mp4"

            if not os.path.exists(file_path) or not download:
                formats_available, link = await self.formats(link, videoid)
                if formats_available:
                    format_id = format_id or formats_available[0]["format_id"]
                    output = await self.slider(link, "url", download, format_id)
                    if output[0]:
                        with open(file_path, 'wb') as f:
                            f.write(output[0])
                        return file_path, None
                    return None, output[1]
                return None, "No formats available"
            return file_path, None
        except Exception as e:
            print(f"Error in download method: {e}")
            return None, str(e)
