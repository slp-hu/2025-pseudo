#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
xvec_visualize.py

- 元音声 n 本 + 仮名化後 n 本から x-vector を抽出
- 必要に応じて pool_xvecs.npz の pool 群も読み込む
- PCA または UMAP で 2 次元に次元削減
- 特徴量空間を可視化（元=○, 仮名化=☆, pool=薄いグレー）

修正版のポイント:
- 2次元化の「学習」は orig + anon だけで行う
- pool は学習済みの 2D mapper に後から transform して重ね描きする
- これにより、pool を表示しつつも pool が座標系を支配しにくくなる
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


def make_2d_mapper(
    X_fit: np.ndarray,
    method: str = "pca",
    seed: int = 0,
    umap_n_neighbors: int = 15,
    umap_min_dist: float = 0.1,
):
    """
    X_fit: [N, D]
    2次元写像器を fit して返す。
    返り値は transform(X) を持つオブジェクト。
    """
    method = method.lower()

    if X_fit.ndim != 2:
        raise ValueError(f"X_fit must be 2D, got {X_fit.shape}")

    if method == "pca":
        from sklearn.decomposition import PCA

        mapper = PCA(n_components=2, random_state=seed)
        mapper.fit(X_fit)
        return mapper

    elif method == "umap":
        import umap

        mapper = umap.UMAP(
            n_components=2,
            random_state=seed,
            n_neighbors=umap_n_neighbors,
            min_dist=umap_min_dist,
            metric="cosine",
        )
        mapper.fit(X_fit)
        return mapper

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
    umap_n_neighbors: int = 15,
    umap_min_dist: float = 0.1,
) -> str:
    """
    orig / anon を基準に2次元写像を学習し、
    pool は同じ写像に transform して重ねて表示する。
    """
    orig_xvecs = np.asarray(orig_xvecs, dtype=np.float32)
    anon_xvecs = np.asarray(anon_xvecs, dtype=np.float32)

    if orig_xvecs.ndim != 2:
        raise ValueError(f"orig_xvecs must be 2D, got {orig_xvecs.shape}")
    if anon_xvecs.ndim != 2:
        raise ValueError(f"anon_xvecs must be 2D, got {anon_xvecs.shape}")
    if orig_xvecs.shape != anon_xvecs.shape:
        raise ValueError(
            f"orig_xvecs and anon_xvecs must have same shape, "
            f"got {orig_xvecs.shape} vs {anon_xvecs.shape}"
        )

    n = orig_xvecs.shape[0]

    # 2次元化の基準は orig + anon
    fit_X = np.concatenate([orig_xvecs, anon_xvecs], axis=0)
    mapper = make_2d_mapper(
        fit_X,
        method=method,
        seed=seed,
        umap_n_neighbors=umap_n_neighbors,
        umap_min_dist=umap_min_dist,
    )

    Yo = mapper.transform(orig_xvecs)
    Ya = mapper.transform(anon_xvecs)

    Yp = None
    if pool_xvecs is not None:
        pool_xvecs = np.asarray(pool_xvecs, dtype=np.float32)
        if pool_xvecs.ndim != 2:
            raise ValueError(f"pool_xvecs must be 2D, got {pool_xvecs.shape}")
        if pool_xvecs.shape[1] != orig_xvecs.shape[1]:
            raise ValueError(
                f"feature dim mismatch: pool={pool_xvecs.shape[1]} "
                f"orig={orig_xvecs.shape[1]}"
            )
        Yp = mapper.transform(pool_xvecs)

    colors = _speaker_colors(n)

    fig, ax = plt.subplots(figsize=(7, 6))

    # pool を背景として先に描画
    if Yp is not None:
        ax.scatter(
            Yp[:, 0],
            Yp[:, 1],
            marker="o",
            s=pool_size,
            c=pool_color,
            alpha=pool_alpha,
            edgecolors="none",
            label="pool",
            zorder=1,
        )

    # orig / anon の対応を描画
    for i in range(n):
        c = colors[i]

        ax.scatter(
            Yo[i, 0],
            Yo[i, 1],
            marker="o",
            s=circle_size,
            c=[c],
            edgecolors="none",
            zorder=3,
        )
        ax.scatter(
            Ya[i, 0],
            Ya[i, 1],
            marker="*",
            s=star_size,
            c=[c],
            edgecolors="none",
            zorder=4,
        )
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
    ax.set_title(
        title
        or f"x-vector: pool(gray) / orig(o) / pseudo(*) | n={n} | basis=orig+anon"
    )
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
    umap_n_neighbors: int = 15,
    umap_min_dist: float = 0.1,
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
        umap_n_neighbors=umap_n_neighbors,
        umap_min_dist=umap_min_dist,
    )

