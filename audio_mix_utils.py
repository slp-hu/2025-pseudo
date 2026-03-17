#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
audio_mix_utils.py

- n本のwavを「レイヤーのように」0秒開始で重ね合わせ（overlay mix）
- 元音声群と変換後音声群のミックスwavを作る
- 変換後は outputs_seedvc/speaker*/ の「最新wav」を自動で拾う

想定:
- Colab/Jupyter から import して使う
"""

from __future__ import annotations
import glob
import os
from typing import List, Tuple, Optional

import numpy as np
import soundfile as sf


def load_wav_mono(path: str, target_sr: Optional[int] = None) -> Tuple[np.ndarray, int]:
    """Load wav, convert to mono float32, optionally resample to target_sr."""
    x, sr = sf.read(path, always_2d=False)
    if x.ndim == 2:
        x = x.mean(axis=1)
    x = x.astype(np.float32)

    if target_sr is not None and sr != target_sr:
        # librosa は依存を最小にしたいので遅延import
        import librosa
        x = librosa.resample(x, orig_sr=sr, target_sr=target_sr).astype(np.float32)
        sr = int(target_sr)
    return x, sr


def mix_overlay(
    paths: List[str],
    out_path: Optional[str] = None,
    target_sr: int = 22050,
    peak: float = 0.98,
) -> Tuple[np.ndarray, int]:
    """
    Overlay-mix (all start at t=0):
      - resample to target_sr
      - pad to max length
      - sum
      - peak-normalize to avoid clipping
    """
    if len(paths) == 0:
        raise ValueError("paths is empty")

    waves = []
    max_len = 0
    for p in paths:
        w, _sr = load_wav_mono(p, target_sr=target_sr)
        waves.append(w)
        max_len = max(max_len, len(w))

    mix = np.zeros(max_len, dtype=np.float32)
    for w in waves:
        mix[: len(w)] += w

    m = float(np.max(np.abs(mix)) + 1e-9)
    mix = (mix / m) * float(peak)

    if out_path:
        sf.write(out_path, mix, target_sr)
    return mix, int(target_sr)


def find_latest_wavs_in_speaker_dirs(outputs_dir: str = "outputs_seedvc") -> List[str]:
    """
    Pick newest wav in each outputs_seedvc/speaker*/ directory.
    Returns list sorted by speaker index (speaker0, speaker1, ... if present).
    """
    spk_dirs = sorted(glob.glob(os.path.join(outputs_dir, "speaker*")))
    latest = []
    for d in spk_dirs:
        wavs = glob.glob(os.path.join(d, "*.wav"))
        if not wavs:
            continue
        wavs = sorted(wavs, key=os.path.getmtime)
        latest.append(wavs[-1])
    return latest


def build_original_vs_converted_mixes(
    original_glob: str,
    outputs_dir: str = "outputs_seedvc",
    out_original_mix: str = "mix_original.wav",
    out_converted_mix: str = "mix_converted.wav",
    target_sr: int = 22050,
) -> Tuple[str, str]:
    """
    original_glob: e.g. "inputs/*.wav" or "demo_wavs/*.wav"
    outputs_dir:   e.g. "outputs_seedvc"

    Writes two wavs and returns their paths.
    """
    orig_paths = sorted(glob.glob(original_glob))
    conv_paths = find_latest_wavs_in_speaker_dirs(outputs_dir=outputs_dir)

    if len(orig_paths) == 0:
        raise FileNotFoundError(f"No original wavs found: {original_glob}")
    if len(conv_paths) == 0:
        raise FileNotFoundError(f"No converted wavs found under: {outputs_dir}/speaker*/")
    if len(orig_paths) != len(conv_paths):
        raise ValueError(f"Count mismatch: original={len(orig_paths)} converted={len(conv_paths)}")

    mix_overlay(orig_paths, out_path=out_original_mix, target_sr=target_sr)
    mix_overlay(conv_paths, out_path=out_converted_mix, target_sr=target_sr)
    return out_original_mix, out_converted_mix
