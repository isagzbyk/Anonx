import asyncio
import os
import re
from typing import Union

import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from youtubesearchpython.__future__ import VideosSearch

from AnonXMusic.utils.database import is_on_off
from AnonXMusic.utils.formatters import time_to_seconds

async def shell_cmd(cmd):
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

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        return re.search(self.regex, link) is not None

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        if offset is None:
            return None
        return text[offset : offset + length]

    async def details(self, link: str, videoid: Union[bool, str] = None):
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
            return None, None, None, None, None

    async def title(self, link: str, videoid: Union[bool, str] = None):
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

    async def duration(self, link: str, videoid: Union[bool, str] = None):
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

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
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

    async def video(self, link: str, videoid: Union[bool, str] = None):
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

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]
        try:
            playlist = await shell_cmd(
                f"yt-dlp -i --get-id --flat-playlist --playlist-end {limit} --skip-download {link}"
            )
            result = playlist.split("\n")
            return [key for key in result if key]
        except Exception as e:
            print(f"Error fetching playlist: {e}")
            return []

    async def track(self, link: str, videoid: Union[bool, str] = None):
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

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        try:
            ytdl_opts = {"quiet": True}
            ydl = yt_dlp.YoutubeDL(ytdl_opts)
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
        query_type: int,
        videoid: Union[bool, str] = None,
    ):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        try:
            a = VideosSearch(link, limit=10)
            result = (await a.next()).get("result")
            if len(result) > query_type:
                item = result[query_type]
                title = item["title"]
                duration_min = item["duration"]
                vidid = item["id"]
                thumbnail = item["thumbnails"][0]["url"].split("?")[0]
                return title, duration_min, thumbnail, vidid
            return None, None, None, None
        except Exception as e:
            print(f"Error fetching slider data: {e}")
            return None, None, None, None

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: str = None,
    ) -> str:
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]

        loop = asyncio.get_running_loop()

        def audio_dl():
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
            }
            x = yt_dlp.YoutubeDL(ydl_opts)
            try:
                info = x.extract_info(link, download=False)
                xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
                if os.path.exists(xyz):
                    return xyz
                x.download([link])
                return xyz
            except Exception as e:
                print(f"Error downloading audio: {e}")
                return None

        def video_dl():
            ydl_opts = {
                "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio[ext=m4a])",
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
            }
            x = yt_dlp.YoutubeDL(ydl_opts)
            try:
                info = x.extract_info(link, download=False)
                xyz = os.path.join("downloads", f"{info['id']}.{info['ext']}")
                if os.path.exists(xyz):
                    return xyz
                x.download([link])
                return xyz
            except Exception as e:
                print(f"Error downloading video: {e}")
                return None

        def song_video_dl():
            formats = f"{format_id}+140" if format_id else "best"
            fpath = f"downloads/{title}.mp4"
            ydl_opts = {
                "format": formats,
                "outtmpl": fpath,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "merge_output_format": "mp4",
            }
            x = yt_dlp.YoutubeDL(ydl_opts)
            try:
                x.download([link])
                return fpath
            except Exception as e:
                print(f"Error downloading song video: {e}")
                return None

        def song_audio_dl():
            fpath = f"downloads/{title}.%(ext)s"
            ydl_opts = {
                "format": format_id,
                "outtmpl": fpath,
                "geo_bypass": True,
                "nocheckcertificate": True,
                "quiet": True,
                "no_warnings": True,
                "prefer_ffmpeg": True,
                "postprocessors": [
                    {
                        "key": "FFmpegExtractAudio",
                        "preferredcodec": "mp3",
                        "preferredquality": "192",
                    }
                ],
            }
            x = yt_dlp.YoutubeDL(ydl_opts)
            try:
                x.download([link])
                return fpath
            except Exception as e:
                print(f"Error downloading song audio: {e}")
                return None

        try:
            if songvideo:
                return await loop.run_in_executor(None, song_video_dl)
            elif songaudio:
                return await loop.run_in_executor(None, song_audio_dl)
            elif video:
                if await is_on_off(1):
                    direct = True
                    downloaded_file = await loop.run_in_executor(None, video_dl)
                else:
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
                        downloaded_file = stdout.decode().split("\n")[0]
                        direct = None
                    else:
                        return None, None
            else:
                direct = True
                downloaded_file = await loop.run_in_executor(None, audio_dl)
            return downloaded_file, direct
        except Exception as e:
            print(f"Error during download: {e}")
            return None, None
