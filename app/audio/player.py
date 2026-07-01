"""mpv audio player wrapper via python-mpv IPC."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import time
from typing import Any, Callable, Optional

from app.audio.eq_presets import DEFAULT_PRESET, mpv_af_string
from app.audio.stream_info import StreamInfo, parse_stream_info

logger = logging.getLogger(__name__)

SOCKET_PATH = "/tmp/radio-pi-mpv.sock"
LOG_PATH = "/tmp/radio-pi-mpv.log"
# Gniazdo 3,5 mm na Pi 3; nadpisz: RADIO_AUDIO_DEVICE=auto
DEFAULT_AUDIO_DEVICE = os.environ.get(
    "RADIO_AUDIO_DEVICE",
    "pulse/alsa_output.platform-bcm2835_audio.analog-stereo",
)


class AudioPlayer:
    """Controls mpv for internet radio streaming."""

    def __init__(self, on_metadata: Optional[Callable[[str], None]] = None) -> None:
        self._on_metadata = on_metadata
        self._mpv = None
        self._proc: Optional[subprocess.Popen] = None
        self._current_url: Optional[str] = None
        self._playing = False
        self._volume = 80
        self._muted = False
        self._eq_preset = DEFAULT_PRESET
        self._init_mpv()

    def _init_mpv(self) -> None:
        try:
            import mpv  # type: ignore[import-untyped]

            self._mpv = mpv.MPV(
                input_default_bindings=False,
                input_vo_keyboard=False,
                vo="null",
                idle=True,
                volume=self._volume,
                ytdl=False,
                audio_device=DEFAULT_AUDIO_DEVICE,
            )
            if self._on_metadata:
                @self._mpv.property_observer("metadata")
                def _meta(_name, value):  # noqa: ANN001
                    if value and "title" in value:
                        self._on_metadata(value["title"])

            logger.info("mpv initialized via python-mpv (%s)", DEFAULT_AUDIO_DEVICE)
        except Exception as exc:
            logger.warning("python-mpv unavailable (%s), using subprocess IPC", exc)
            self._mpv = None

    @property
    def playing(self) -> bool:
        return self._playing

    @property
    def volume(self) -> int:
        return self._volume

    @property
    def muted(self) -> bool:
        return self._muted

    def set_eq_preset(self, preset_id: str) -> None:
        self._eq_preset = preset_id
        af = mpv_af_string(preset_id)
        if self._mpv is not None:
            try:
                self._mpv.af = af
            except Exception as exc:
                logger.error("mpv af failed: %s", exc)
        else:
            self._ensure_subprocess_mpv()
            self._subprocess_cmd(["set_property", "af", af])
        logger.info("EQ preset: %s", preset_id)

    @property
    def eq_preset(self) -> str:
        return self._eq_preset

    def play(self, url: str) -> None:
        self._current_url = url
        if self._mpv is not None:
            self._mpv.play(url)
        else:
            self._ensure_subprocess_mpv()
            self._subprocess_cmd(["loadfile", url, "replace"])
        self._playing = True
        self.set_eq_preset(self._eq_preset)

    def pause(self) -> None:
        if self._mpv is not None:
            self._mpv.pause = True
        else:
            self._subprocess_cmd(["set_property", "pause", "yes"])
        self._playing = False

    def resume(self) -> None:
        if self._mpv is not None:
            self._mpv.pause = False
        else:
            self._subprocess_cmd(["set_property", "pause", "no"])
        self._playing = True

    def toggle_pause(self) -> None:
        if self._playing:
            self.pause()
        elif self._current_url:
            self.resume()

    def stop(self) -> None:
        if self._mpv is not None:
            self._mpv.stop()
        else:
            self._subprocess_cmd(["stop"])
        self._playing = False

    def set_volume(self, level: int) -> None:
        self._volume = max(0, min(100, level))
        if self._mpv is not None:
            self._mpv.volume = self._volume
        else:
            self._subprocess_cmd(["set_property", "volume", str(self._volume)])

    def set_mute(self, muted: bool) -> None:
        self._muted = muted
        if self._mpv is not None:
            self._mpv.mute = muted
        else:
            val = "yes" if muted else "no"
            self._subprocess_cmd(["set_property", "mute", val])

    def toggle_mute(self) -> bool:
        self.set_mute(not self._muted)
        return self._muted

    def get_stream_info(self, config_station: Optional[dict] = None) -> StreamInfo:
        meta: dict = {}
        media_title = ""
        if self._mpv is not None:
            try:
                raw = self._mpv.metadata or {}
                if isinstance(raw, dict):
                    meta = raw
            except Exception:
                pass
            try:
                mt = self._mpv.media_title
                media_title = str(mt) if mt else ""
            except Exception:
                pass
        else:
            raw = self._subprocess_get_property("metadata")
            if isinstance(raw, dict):
                meta = raw
            mt = self._subprocess_get_property("media-title")
            media_title = str(mt) if mt else ""
        return parse_stream_info(
            meta,
            media_title=media_title,
            config_station=config_station,
            bitrate_kbps=self.get_bitrate_kbps(),
        )

    def get_stream_title(self) -> str:
        return self.get_stream_info().track_scroll_text()

    def get_bitrate_kbps(self) -> Optional[int]:
        if self._mpv is not None:
            try:
                br = self._mpv["audio-bitrate"]
                if br:
                    return int(br) // 1000
            except Exception:
                pass
            try:
                meta = self._mpv.metadata or {}
                if isinstance(meta, dict) and "icy-br" in meta:
                    return int(meta["icy-br"])
            except Exception:
                pass
            return None
        meta = self._subprocess_get_property("metadata")
        if isinstance(meta, dict) and meta.get("icy-br"):
            try:
                return int(meta["icy-br"])
            except (TypeError, ValueError):
                pass
        br = self._subprocess_get_property("audio-bitrate")
        if br:
            try:
                return int(br) // 1000
            except (TypeError, ValueError):
                pass
        return None

    def _subprocess_get_property(self, name: str) -> Any:
        if not os.path.exists(SOCKET_PATH):
            return None
        payload = f'{{"command": ["get_property", "{name}"]}}\n'
        try:
            result = subprocess.run(
                ["socat", "-", f"UNIX-CONNECT:{SOCKET_PATH}"],
                input=payload.encode(),
                check=False,
                timeout=2,
                capture_output=True,
            )
            if not result.stdout:
                return None
            data = json.loads(result.stdout.decode().strip().splitlines()[-1])
            if data.get("error") == "success":
                return data.get("data")
        except (json.JSONDecodeError, subprocess.TimeoutExpired, OSError) as exc:
            logger.debug("mpv get_property %s failed: %s", name, exc)
        return None

    def _ensure_subprocess_mpv(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            if os.path.exists(SOCKET_PATH):
                return
        self._kill_subprocess()
        os.makedirs(os.path.dirname(SOCKET_PATH), exist_ok=True)
        if os.path.exists(SOCKET_PATH):
            os.remove(SOCKET_PATH)
        log = open(LOG_PATH, "a", encoding="utf-8")  # noqa: SIM115
        self._proc = subprocess.Popen(
            [
                "mpv",
                f"--input-ipc-server={SOCKET_PATH}",
                "--no-video",
                "--idle=yes",
                f"--volume={self._volume}",
                f"--audio-device={DEFAULT_AUDIO_DEVICE}",
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        for _ in range(30):
            if os.path.exists(SOCKET_PATH):
                logger.info("mpv subprocess ready (audio=%s)", DEFAULT_AUDIO_DEVICE)
                self.set_eq_preset(self._eq_preset)
                return
            time.sleep(0.1)
        logger.error("mpv IPC socket not created — see %s", LOG_PATH)

    def _kill_subprocess(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None

    def _subprocess_cmd(self, args: list[str]) -> None:
        if not os.path.exists(SOCKET_PATH):
            self._ensure_subprocess_mpv()
        if not os.path.exists(SOCKET_PATH):
            return
        parts = ", ".join(f'"{a}"' for a in args)
        payload = f'{{"command": [{parts}]}}\n'
        try:
            subprocess.run(
                ["socat", "-", f"UNIX-CONNECT:{SOCKET_PATH}"],
                input=payload.encode(),
                check=False,
                timeout=3,
                capture_output=True,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            logger.error("mpv IPC failed: %s", exc)

    def shutdown(self) -> None:
        self.stop()
        if self._mpv is not None:
            self._mpv.terminate()
        self._kill_subprocess()
