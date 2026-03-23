#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""xvec_visualize.py

- 元音声n本 + 仮名化後n本 から x-vector を抽出
- 必要に応じて pool_xvecs.npz の pool 群も読み込む
- PCA または UMAP で2次元に次元削減
- 特徴量空間を可視化（元=○, 仮名化=☆, pool=薄いグレー）
"""

from __future__ import annotations

import glob
import os
from typing import List, Optional, Tuple

import numpy as np
import matplotlib.pyplot as plt

from pseudonymize_meeting_tts_seedvc import (
    extract_xvector_jtubespeech,
    load_jtubespeech_xvector,
)


def _latest_wavs_in_speaker_dirs(outputs_dir: str = "outputs_seedvc") -> List[str]:
    spk_dirs = sorted(glob.glob(os.path.join(outputs_dir, "speaker*")))
    latest = []
    for d in spk_dirs:
        wavs = glob.glob(os.path.join(d, "*.wav"))
        if not wavs:
            continue
        wavs = sorted(wavs, key=os.path.getmtime)
        latest.append(wavs[-1])
    return latest


def _list_wavs_in_dir(inputs_dir: str) -> List[str]:
    return sorted(glob.glob(os.path.join(inputs_dir, "*.wav")))


def _load_pool_xvecs(pool_npz: str) -> np.ndarray:
    data = np.load(pool_npz, allow_pickle=True)
    if "xvecs" not in data:
        raise KeyError(f"'xvecs' is not found in {pool_npz}")

    pool_xvecs = data["xvecs"].astype(np.float32)
    if pool_xvecs.ndim != 2:
        raise ValueError(f"pool_xvecs must be 2D, got {pool_xvecs.shape}")
    return pool_xvecs


def extract_xvectors_for_pairs(
    orig_wavs: List[str],
    anon_wavs: List[str],
    device: Optional[str] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    if len(orig_wavs) != len(anon_wavs):
        raise ValueError(f"count mismatch: orig={len(orig_wavs)} anon={len(anon_wavs)}")

    xvec_model, dev = load_jtubespeech_xvector(device=device)

    orig_x = []
    anon_x = []
    for ow, aw in zip(orig_wavs, anon_wavs):
        ox = extract_xvector_jtubespeech(ow, xvec_model, dev).numpy()[0]
        ax = extract_xvector_jtubespeech(aw, xvec_model, dev).numpy()[0]
        orig_x.append(ox)
        anon_x.append(ax)

    return np.asarray(orig_x, dtype=np.float32), np.asarray(anon_x, dtype=np.float32)


def reduce_2d(
    X: np.ndarray,
    method: str = "pca",
    seed: int = 0,
    umap_n_neighbors: int = 15,
    umap_min_dist: float = 0.1,
) -> np.ndarray:
    """X:[N,D] -> Y:[N,2]"""
    method = method.lower()
    if method == "pca":
        from sklearn.decomposition import PCA
        return PCA(n_components=2, random_state=seed).fit_transform(X)
    elif method == "umap":
        import umap
        return umap.UMAP(
            n_components=2,
            random_state=seed,
            n_neighbors=umap_n_neighbors,
            min_dist=umap_min_dist,
            metric="cosine",
        ).fit_transform(X)
    else:
        raise ValueError("method must be 'pca' or 'umap'")


def _speaker_colors(n: int):
    if n <= 10:
        cmap = plt.get_cmap("tab10")
        return [cmap(i) for i in range(n)]
    if n <= 20:
        cmap = plt.get_cmap("tab20")
        return [cmap(i) for i in range(n)]
    cmap = plt.get_cmap("hsv")
    return [cmap(i / n) for i in range(n)]


def plot_orig_vs_anon(
    orig_xvecs: np.ndarray,
    anon_xvecs: np.ndarray,
    method: str = "pca",
    seed: int = 0,
    out_png: str = "xvec_viz.png",
    title: Optional[str] = None,
    circle_size: int = 100,
    star_size: int = 200,
    line_width: float = 1.6,
    line_alpha: float = 0.75,
    pool_xvecs: Optional[np.ndarray] = None,
    pool_size: int = 18,
    pool_alpha: float = 0.75,
    pool_color: str = "gray",
) -> str:
    n = orig_xvecs.shape[0]
    if anon_xvecs.shape[0] != n:
        raise ValueError("orig_xvecs and anon_xvecs must have same length")

    parts = []
    pool_count = 0
    if pool_xvecs is not None:
        pool_xvecs = np.asarray(pool_xvecs, dtype=np.float32)
        if pool_xvecs.ndim != 2:
            raise ValueError(f"pool_xvecs must be 2D, got {pool_xvecs.shape}")
        parts.append(pool_xvecs)
        pool_count = pool_xvecs.shape[0]

    parts.extend([orig_xvecs, anon_xvecs])
    X = np.concatenate(parts, axis=0)
    Y = reduce_2d(X, method=method, seed=seed)

    offset = 0
    Yp = None
    if pool_count > 0:
        Yp = Y[offset:offset + pool_count]
        offset += pool_count

    Yo = Y[offset:offset + n]
    offset += n
    Ya = Y[offset:offset + n]

    colors = _speaker_colors(n)

    fig, ax = plt.subplots(figsize=(7, 6))

    if Yp is not None:
        ax.scatter(
            Yp[:, 0], Yp[:, 1],
            marker="o",
            s=pool_size,
            c=pool_color,
            alpha=pool_alpha,
            edgecolors="none",
            label="pool",
            zorder=1,
        )

    for i in range(n):
        c = colors[i]

        ax.scatter(Yo[i, 0], Yo[i, 1], marker="o", s=circle_size, c=[c], edgecolors="none", zorder=3)
        ax.scatter(Ya[i, 0], Ya[i, 1], marker="*", s=star_size, c=[c], edgecolors="none", zorder=4)
        ax.plot(
            [Yo[i, 0], Ya[i, 0]],
            [Yo[i, 1], Ya[i, 1]],
            color=c,
            linewidth=line_width,
            alpha=line_alpha,
            zorder=2,
        )

        ax.text(Yo[i, 0], Yo[i, 1], f"{i}", fontsize=9, alpha=0.9)
        ax.text(Ya[i, 0], Ya[i, 1], f"{i}'", fontsize=9, alpha=0.9)

    ax.set_xlabel("dim1")
    ax.set_ylabel("dim2")
    ax.set_title(title or f"x-vector 2D ({method.upper()})  (pool=gray, orig=o, anon=*)")
    ax.grid(True, alpha=0.2)
    fig.tight_layout()
    fig.savefig(out_png, dpi=180)
    plt.close(fig)
    return out_png


def visualize_from_dirs(
    inputs_dir: str,
    outputs_dir: str = "outputs_seedvc",
    method: str = "pca",
    seed: int = 0,
    out_png: str = "xvec_viz.png",
    device: Optional[str] = None,
    pool_npz: Optional[str] = None,
) -> str:
    orig_wavs = _list_wavs_in_dir(inputs_dir)
    anon_wavs = _latest_wavs_in_speaker_dirs(outputs_dir)

    if len(orig_wavs) == 0:
        raise FileNotFoundError(f"no wav found in {inputs_dir}")
    if len(anon_wavs) == 0:
        raise FileNotFoundError(f"no converted wav found under {outputs_dir}/speaker*/")
    if len(orig_wavs) != len(anon_wavs):
        raise ValueError(f"count mismatch: inputs={len(orig_wavs)} outputs={len(anon_wavs)}")

    ox, axv = extract_xvectors_for_pairs(orig_wavs, anon_wavs, device=device)
    pool_xvecs = _load_pool_xvecs(pool_npz) if pool_npz else None

    return plot_orig_vs_anon(
        ox,
        axv,
        method=method,
        seed=seed,
        out_png=out_png,
        title=f"x-vector: pool(gray) / orig(o) / pseudo(*) | n={len(orig_wavs)}",
        pool_xvecs=pool_xvecs,
    )
