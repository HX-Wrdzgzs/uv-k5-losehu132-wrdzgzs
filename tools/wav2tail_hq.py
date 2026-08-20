#!/usr/bin/env python3
"""Generate a compact single-tone/envelope approximation of a WAV tail.

The BK4819 can synthesize tones but cannot play arbitrary PCM from this
firmware path. This tool therefore keeps the dominant whistle frequency,
its amplitude envelope, and silence gaps, then compresses adjacent frames
into a small sequence that fits the firmware flash budget.
"""

from __future__ import annotations

import argparse
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np

FRAME_SIZE = 2048
HOP_SIZE = 256
MIN_FREQ = 800
MAX_FREQ = 2600
MAX_SEGMENTS = 64
# Keep retained low-level whistle transitions audible after BK4819 quantisation.
MIN_AUDIBLE_GAIN = 24
# Do not turn the low-level, unstable pitch-tracking pre-roll into an audible
# trill. The onset must stay above this fraction of the peak for a few frames.
OPENING_ONSET_RATIO = 0.05
OPENING_ONSET_STABLE_FRAMES = 3
# This delay is outside the source WAV timeline and only stabilises the TX path.
TAIL_TX_SETUP_DELAY_MS = 20


@dataclass
class Segment:
    f1: int
    g1: int
    ms: int


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as wav:
        channels = wav.getnchannels()
        width = wav.getsampwidth()
        rate = wav.getframerate()
        frames = wav.readframes(wav.getnframes())
    if width != 2:
        raise ValueError("only 16-bit PCM WAV is supported")
    audio = np.frombuffer(frames, dtype="<i2").astype(np.float64) / 32768.0
    if channels == 2:
        audio = audio.reshape(-1, 2).mean(axis=1)
    elif channels != 1:
        raise ValueError("only mono/stereo WAV is supported")
    return audio, rate


def interpolated_frequency(spectrum: np.ndarray, index: int, rate: int) -> float:
    if index <= 0 or index >= len(spectrum) - 1:
        return index * rate / FRAME_SIZE
    left, center, right = spectrum[index - 1:index + 2]
    denominator = left - 2.0 * center + right
    delta = 0.0 if abs(denominator) < 1e-12 else float(
        0.5 * (left - right) / denominator
    )
    return (index + max(-0.5, min(0.5, delta))) * rate / FRAME_SIZE


def find_opening_onset(
    raw: list[tuple[float, float, int]],
    max_rms: float,
    noise_floor: float,
    onset_ratio: float = OPENING_ONSET_RATIO,
    stable_frames: int = OPENING_ONSET_STABLE_FRAMES,
) -> int:
    """Find the first stable, audible frame and drop unstable pre-roll."""
    if not raw or stable_frames < 1:
        return 0
    threshold = max(max_rms * onset_ratio, noise_floor * 4.0)
    last_start = len(raw) - stable_frames + 1
    for start in range(max(0, last_start)):
        if all(item[0] >= threshold for item in raw[start:start + stable_frames]):
            return start
    # A completely quiet or unusual source is safer left at its original start
    # than silently shortened based on an unreliable onset guess.
    return 0


def analyse(
    audio: np.ndarray,
    rate: int,
    min_freq: int = MIN_FREQ,
    max_freq: int = MAX_FREQ,
    max_segments: int = MAX_SEGMENTS,
) -> list[Segment]:
    """Extract a dominant whistle track and compress it for BK4819 playback."""
    if not len(audio):
        raise ValueError("WAV contains no audio frames")
    if min_freq >= max_freq:
        raise ValueError("min_freq must be lower than max_freq")
    if max_segments < 1:
        raise ValueError("max_segments must be positive")

    window = np.hanning(FRAME_SIZE)
    frequencies = np.fft.rfftfreq(FRAME_SIZE, 1.0 / rate)
    bins = np.flatnonzero(
        (frequencies >= min_freq) & (frequencies <= max_freq)
    )
    if not len(bins):
        raise ValueError("frequency range does not intersect WAV spectrum")

    raw: list[tuple[float, float, int]] = []
    previous_end_ms = 0
    for start in range(0, len(audio), HOP_SIZE):
        frame = audio[start:start + FRAME_SIZE]
        if len(frame) < FRAME_SIZE:
            frame = np.pad(frame, (0, FRAME_SIZE - len(frame)))

        rms = float(np.sqrt(np.mean(frame * frame)))
        spectrum = np.abs(np.fft.rfft(frame * window))
        peak = int(bins[np.argmax(spectrum[bins])])
        frequency = interpolated_frequency(spectrum, peak, rate)
        end_ms = round(min(start + HOP_SIZE, len(audio)) * 1000 / rate)
        frame_ms = max(1, end_ms - previous_end_ms)
        previous_end_ms = end_ms
        raw.append((rms, frequency, frame_ms))

    max_rms = max(item[0] for item in raw) or 1.0
    # The old converter turned low-level noise and the two quiet gaps into
    # audible 440/480 Hz tones. Use a relative floor and a local noise
    # estimate so those frames become real mute intervals instead.
    noise_floor = float(np.percentile([item[0] for item in raw], 20))
    silence_threshold = max(max_rms * 0.01, noise_floor * 4.0)
    opening_onset = find_opening_onset(raw, max_rms, noise_floor)

    frames: list[Segment] = []
    for rms, frequency, frame_ms in raw:
        if rms < silence_threshold:
            frames.append(Segment(0, 0, frame_ms))
            continue
        envelope = max(0.0, min(1.0, rms / max_rms))
        gain = max(MIN_AUDIBLE_GAIN, min(108, round(8 + 100 * envelope ** 0.55)))
        # BK4819 tuning is coarse compared with the WAV FFT resolution; 10 Hz
        # quantisation avoids wasting segments on inaudible sub-step changes.
        frames.append(Segment(round(frequency / 10) * 10, gain, frame_ms))

    if opening_onset:
        frames = frames[opening_onset:]
    trimmed_ms = sum(item[2] for item in raw[:opening_onset])
    target_ms = round(len(audio) * 1000 / rate) - trimmed_ms
    frames[-1].ms = max(1, frames[-1].ms + target_ms - sum(x.ms for x in frames))
    result = compress(frames, max_segments)
    if sum(item.ms for item in result) != target_ms:
        raise RuntimeError("tail duration changed during compression")
    if any(item.ms < 1 or item.ms > 255 for item in result):
        raise RuntimeError("tail segment duration does not fit uint8 milliseconds")
    return result


def similar(a: Segment, b: Segment, freq_tol: int, gain_tol: int) -> bool:
    if a.g1 == 0 and b.g1 == 0:
        return True
    if a.g1 == 0 or b.g1 == 0:
        return False
    return abs(a.f1 - b.f1) <= freq_tol and abs(a.g1 - b.g1) <= gain_tol


def merge(a: Segment, b: Segment) -> Segment:
    total = a.ms + b.ms

    def average(x: int, y: int) -> int:
        return round((x * a.ms + y * b.ms) / total)

    return Segment(average(a.f1, b.f1), average(a.g1, b.g1), total)


def compress(source: list[Segment], max_segments: int) -> list[Segment]:
    freq_tol, gain_tol = 20, 5
    while True:
        output: list[Segment] = []
        for item in source:
            if (
                output
                and output[-1].ms + item.ms <= 255
                and similar(output[-1], item, freq_tol, gain_tol)
            ):
                output[-1] = merge(output[-1], item)
            else:
                output.append(item)
        if len(output) <= max_segments:
            return output
        freq_tol += 10
        gain_tol += 2


def c_array(name: str, ctype: str, values: list[int], width: int) -> str:
    lines = []
    for start in range(0, len(values), width):
        lines.append("    " + ", ".join(f"{value}u" for value in values[start:start + width]))
    return (
        f"static const {ctype} {name}[TAIL_COUNT] = {{\n"
        + ",\n".join(lines)
        + "\n};\n"
    )


def generate(source: Path, segments: list[Segment], total_ms: int) -> str:
    arrays = "\n".join((
        c_array("gCustomTailFreqs", "uint16_t", [x.f1 for x in segments], 12),
        c_array("gCustomTailGains", "uint8_t", [x.g1 for x in segments], 18),
        c_array("gCustomTailDurations", "uint8_t", [x.ms for x in segments], 18),
    ))
    return f'''/*
 * 自定义尾音 - 由 wav2tail_hq.py 自动生成
 * 源文件: {source.name}
 * 音调段数: {len(segments)}
 * 总时长: {total_ms / 1000:.2f}s
 *
 * BK4819 只能合成单音，以下序列保留 1.wav 的主频率、音量包络和静音段，
 * 是可编译进固件的近似，不是 PCM 播放。
 * 开头低电平且不稳定的频率跟踪段已裁掉，避免开场颤音。
 * 公版保留尾音菜单入口，但不嵌入个人尾音；个人构建才启用本数组。
 */

#include "bk4819.h"

#if CUSTOM_TAIL_EMBEDDED

#include "system.h"

static inline uint16_t freq_to_reg(uint16_t freq_hz)
{{
    return (uint16_t)(((uint32_t)freq_hz * 1353245u + (1u << 16)) >> 17);
}}

#define TAIL_COUNT {len(segments)}

{arrays}

void BK4819_PlayCustomTail(void)
{{
    bool active = false;

    BK4819_EnterTxMute();
    BK4819_SetAF(BK4819_AF_MUTE);
    BK4819_EnableTXLink();
    /* Stabilise the TX chain before the retained tail starts. */
    SYSTEM_DelayMs({TAIL_TX_SETUP_DELAY_MS});

    for (uint8_t i = 0; i < TAIL_COUNT; i++)
    {{
        if (gCustomTailFreqs[i] == 0u || gCustomTailGains[i] == 0u)
        {{
            BK4819_WriteRegister(BK4819_REG_70, 0u);
            if (active)
            {{
                BK4819_EnterTxMute();
                active = false;
            }}
        }}
        else
        {{
            BK4819_WriteRegister(BK4819_REG_71, freq_to_reg(gCustomTailFreqs[i]));
            BK4819_WriteRegister(
                BK4819_REG_70,
                BK4819_REG_70_ENABLE_TONE1
                | ((uint16_t)gCustomTailGains[i] << BK4819_REG_70_SHIFT_TONE1_TUNING_GAIN));
            if (!active)
            {{
                BK4819_ExitTxMute();
                active = true;
            }}
        }}
        SYSTEM_DelayMs(gCustomTailDurations[i]);
    }}

    BK4819_EnterTxMute();
    BK4819_TurnsOffTones_TurnsOnRX();
}}

#else

/* 公版保留入口，但不带维护者个人 1.wav 资源。 */
void BK4819_PlayCustomTail(void)
{{
    BK4819_PlayRogerNormal();
}}

#endif
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", "-o", type=Path, default=Path("driver/custom_tail.c"))
    parser.add_argument("--max-segments", type=int, default=MAX_SEGMENTS)
    parser.add_argument("--min-freq", type=int, default=MIN_FREQ)
    parser.add_argument("--max-freq", type=int, default=MAX_FREQ)
    args = parser.parse_args()

    audio, rate = read_wav(args.input)
    segments = analyse(
        audio,
        rate,
        min_freq=args.min_freq,
        max_freq=args.max_freq,
        max_segments=args.max_segments,
    )
    total_ms = round(len(audio) * 1000 / rate)
    args.output.write_text(generate(args.input, segments, total_ms), encoding="utf-8")
    print(
        f"Generated {len(segments)} segments; "
        f"silence={sum(x.g1 == 0 for x in segments)}; "
        f"duration={sum(x.ms for x in segments)}ms"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
