from re import sub
from typing import Union, Any

from asyncspotify import FullTrack, SimpleTrack
from discord import Member, ApplicationContext, TextChannel


class PreparedSource:
    ctx: ApplicationContext
    requester: Union[Member, Any]  # Will always be Member
    channel: Union[TextChannel, Any]  # Will always be TextChannel

    name: str
    artists: list[str]
    duration: int  # seconds
    url: str
    _v_url: str

    search: str

    def __init__(self, ctx: ApplicationContext, track: Union[FullTrack, SimpleTrack, dict]) -> None:
        self.ctx = ctx
        self.requester = ctx.author
        self.channel = ctx.channel

        if not isinstance(track, dict):
            self.name = track.name
            self.artists = [artist.name for artist in track.artists]
            self.duration = int(track.duration.total_seconds())
            self.url, self._v_url = track.link, ""

        else:
            self.name = track.get("title")
            self.artists = [sub(r" - Topic$", "", track.get("uploader"))]
            self.duration = int(track.get("duration")) if track.get("duration") else 210
            self.url, self._v_url = track.get("url"), track.get("url")

    @property
    def search(self) -> str:
        return self._v_url or f"{self.name} " + sub(r"[\[\]]", "", f"{[artist for artist in self.artists]}")

    def __str__(self) -> str:
        return f"{self.name} by {self.artists[0]}"[:73]
