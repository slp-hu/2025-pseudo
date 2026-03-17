#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""anonymize_meeting_tts_seedvc.py

Seed-VCパイプライン向けに必要なものだけ残した軽量版。

含む機能:
- JTubeSpeech x-vector 抽出 (extract_xvector_jtubespeech)
- pool->nクラスタ（球面kmeans + 直交化）+ Hungarian割当 (choose_anonymization_xvectors)
- ESPnet TTS: spembs指定で参照音声を合成 (synthesize_with_spembs)
- TTSモデルファイルDL & ロード (download_tts_model_files, load_tts)
- x-vectorモデルロード (load_jtubespeech_xvector)
- wav保存 (save_wav)

※ VAD/文字起こし前提の分割・結合処理は削除。
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import os
import numpy as np

import torch
import torchaudio
import soundfile as sf

from torchaudio.compliance.kaldi import mfcc as kaldi_mfcc


# -------------------------
# x-vector extraction (JTubeSpeech)
# -------------------------

def extract_xvector_jtubespeech(
    wav_path: str,
    model: torch.nn.Module,
    device: torch.device,
) -> torch.Tensor:
    """JTubeSpeech仕様に合わせてwavファイルからx-vectorを抽出。

    Returns:
        torch.Tensor shape [1, 512] on CPU
    """
    wav_numpy, sample_rate = sf.read(wav_path)
    wav_tensor = torch.from_numpy(wav_numpy).float()

    # (Time) -> (1, Time) ; (Time, Ch) -> (Ch, Time)
    if wav_tensor.ndim == 1:
        wav_tensor = wav_tensor.unsqueeze(0)
    else:
        wav_tensor = wav_tensor.t()

    # mono
    if wav_tensor.shape[0] > 1:
        wav_tensor = torch.mean(wav_tensor, dim=0, keepdim=True)

    # resample to 16k
    if sample_rate != 16000:
        resampler = torchaudio.transforms.Resample(sample_rate, 16000)
        wav_tensor = resampler(wav_tensor)

    # Kaldi MFCC: num_mel_bins=80, num_ceps=24
    mfcc = kaldi_mfcc(
        wav_tensor,
        num_ceps=24,
        num_mel_bins=80,
        sample_frequency=16000
    )  # [T, 24]

    mfcc = mfcc.unsqueeze(0).to(device)  # [1, T, 24]

    with torch.no_grad():
        xvec = model.vectorize(mfcc)  # [1, 512]
    return xvec.to("cpu")


# -------------------------
# Spherical k-means with orthogonality encouragement
# -------------------------

def l2_normalize(x: np.ndarray, axis: int = 1, eps: float = 1e-12) -> np.ndarray:
    n = np.linalg.norm(x, axis=axis, keepdims=True)
    return x / np.maximum(n, eps)


def farthest_first_init(X: np.ndarray, k: int, rng: np.random.Generator) -> np.ndarray:
    """Farthest-first initialization on cosine distance (1 - cosine sim)."""
    n, _d = X.shape
    idx0 = int(rng.integers(0, n))
    centers = [X[idx0]]
    chosen = {idx0}
    for _ in range(1, k):
        C = np.stack(centers, axis=0)  # [m, d]
        sims = X @ C.T                 # [n, m]
        best_sim = sims.max(axis=1)    # similarity to nearest center
        dist = 1.0 - best_sim
        dist[list(chosen)] = -1.0
        idx = int(dist.argmax())
        centers.append(X[idx])
        chosen.add(idx)
    return np.stack(centers, axis=0)


def gram_schmidt_rows(C: np.ndarray, eps: float = 1e-12) -> np.ndarray:
    """Row-wise Gram-Schmidt to encourage orthogonality among k centers."""
    k, _d = C.shape
    Q = np.zeros_like(C)
    for i in range(k):
        v = C[i].copy()
        for j in range(i):
            denom = float(np.dot(Q[j], Q[j]) + eps)
            v = v - (np.dot(v, Q[j]) / denom) * Q[j]
        norm = float(np.linalg.norm(v) + eps)
        Q[i] = v / norm
    return Q


def spherical_kmeans_orthogonal(
    X: np.ndarray,
    k: int,
    n_iter: int = 30,
    ortho_every: int = 1,
    ortho_blend: float = 0.35,
    seed: int = 0,
) -> Tuple[np.ndarray, np.ndarray]:
    """Spherical k-means + periodic soft orthogonalization."""
    rng = np.random.default_rng(seed)
    Xn = l2_normalize(X.astype(np.float32), axis=1)

    centers = farthest_first_init(Xn, k, rng)  # normalized
    labels = np.zeros(Xn.shape[0], dtype=np.int64)

    for it in range(n_iter):
        sims = Xn @ centers.T
        labels = sims.argmax(axis=1)

        new_centers = np.zeros_like(centers)
        for j in range(k):
            idx = np.where(labels == j)[0]
            if idx.size == 0:
                new_centers[j] = Xn[int(rng.integers(0, Xn.shape[0]))]
            else:
                new_centers[j] = Xn[idx].mean(axis=0)
        new_centers = l2_normalize(new_centers, axis=1)

        if ortho_every > 0 and (it % ortho_every == 0):
            ortho = gram_schmidt_rows(new_centers)
            new_centers = l2_normalize(
                (1.0 - ortho_blend) * new_centers + ortho_blend * ortho,
                axis=1
            )

        centers = new_centers

    return centers, labels


# -------------------------
# Assignment (Hungarian algorithm) for minimizing total cost
# -------------------------

def hungarian_min_cost(cost: np.ndarray) -> List[int]:
    """Min-cost assignment for square cost matrix (O(n^3))."""
    cost = cost.copy().astype(np.float64)
    n, m = cost.shape
    if n != m:
        raise ValueError("cost must be square")

    u = np.zeros(n + 1)
    v = np.zeros(n + 1)
    p = np.zeros(n + 1, dtype=int)
    way = np.zeros(n + 1, dtype=int)

    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = np.full(n + 1, np.inf)
        used = np.zeros(n + 1, dtype=bool)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = np.inf
            j1 = 0
            for j in range(1, n + 1):
                if not used[j]:
                    cur = cost[i0 - 1, j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur
                        way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]
                        j1 = j
            for j in range(0, n + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break

        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break

    assign = [-1] * n
    for j in range(1, n + 1):
        if p[j] != 0:
            assign[p[j] - 1] = j - 1
    return assign


# -------------------------
# High-level mapping: pool -> n clusters -> assignment
# -------------------------

def choose_anonymization_xvectors(
    meeting_speaker_xvecs: np.ndarray,  # [n, d]
    pool_xvecs: np.ndarray,             # [M, d]
    n_clusters: Optional[int] = None,
    seed: int = 0,
) -> Dict[int, Dict[str, np.ndarray]]:
    """プールx-vectorをnクラスタに分け(≈直交)、入力話者へ同時最適割当する。"""
    S = l2_normalize(meeting_speaker_xvecs, axis=1)
    P = l2_normalize(pool_xvecs, axis=1)
    n = S.shape[0]
    k = int(n_clusters or n)

    centers, labels = spherical_kmeans_orthogonal(P, k=k, seed=seed)

    # cost: cosine similarity（小さいほど匿名性寄り）
    cost = S @ centers.T  # [n, k]
    assign = hungarian_min_cost(cost)

    mapping: Dict[int, Dict[str, np.ndarray]] = {}
    for spk in range(n):
        j = assign[spk]
        c = centers[j]

        idx = np.where(labels == j)[0]
        if idx.size == 0:
            nearest = int((P @ c).argmax())
        else:
            nearest_local = int((P[idx] @ c).argmax())
            nearest = int(idx[nearest_local])

        target_member = P[nearest]
        sim = float(np.dot(S[spk], c))

        mapping[spk] = {
            "target_center": c.astype(np.float32),
            "target_pool_member": target_member.astype(np.float32),
            "cos_sim_to_orig": np.array(sim, dtype=np.float32),
            "cluster_index": np.array(j, dtype=np.int64),
            "pool_index": np.array(nearest, dtype=np.int64),
        }

    return mapping


# -------------------------
# TTS wrapper (ESPnet Text2Speech)
# -------------------------

def synthesize_with_spembs(
    tts,  # espnet2.bin.tts_inference.Text2Speech
    text: str,
    spembs: np.ndarray | torch.Tensor,
) -> Tuple[np.ndarray, int]:
    """ESPnet Text2Speech: spembs指定で合成。 Returns (wav_float32, fs)."""
    if isinstance(spembs, np.ndarray):
        spembs_t = torch.from_numpy(spembs).float().view(-1)
    else:
        spembs_t = spembs.float().view(-1)

    out = tts(text, spembs=spembs_t)
    wav = out["wav"].detach().cpu().numpy().astype(np.float32)
    return wav, int(tts.fs)


def save_wav(path: str, wav: np.ndarray, sr: int):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    sf.write(path, wav, sr)


# -------------------------
# Model download & loading (same release URLs as the provided script)
# -------------------------

def download_tts_model_files(
    output_dir: str = "model_files",
    github_user: str = "CClemonjj",
    repo_name: str = "TTS_jtubespeech",
    tag: str = "v1.0",
) -> Dict[str, str]:
    """GitHub releases からTTSモデル一式をダウンロード（存在しない場合のみ）。"""
    import torch

    base_url = f"https://github.com/{github_user}/{repo_name}/releases/download/{tag}"
    os.makedirs(output_dir, exist_ok=True)

    def _dl(filename: str) -> str:
        url = f"{base_url}/{filename}"
        save_path = os.path.join(output_dir, filename)
        if not os.path.exists(save_path):
            print(f"Downloading {filename} ...")
            torch.hub.download_url_to_file(url, save_path)
        return save_path

    return {
        "model_file": _dl("1000epoch.pth"),
        "config_file": _dl("config.yaml"),
        "feats_stats": _dl("feats_stats.npz"),
        "pitch_stats": _dl("pitch_stats.npz"),
        "energy_stats": _dl("energy_stats.npz"),
    }


def load_tts(
    config_path: str,
    model_path: str,
    device: Optional[str] = None,
):
    """ESPnet Text2Speech をロード。"""
    from espnet2.bin.tts_inference import Text2Speech
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    return Text2Speech.from_pretrained(
        train_config=config_path,
        model_file=model_path,
        vocoder_tag=None,
        device=device,
    )


def load_jtubespeech_xvector(device: Optional[str] = None):
    """JTubeSpeech x-vectorモデルを torch.hub からロード。"""
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    xvector_model = torch.hub.load(
        "sarulab-speech/xvector_jtubespeech",
        "xvector",
        trust_repo=True
    )
    xvector_model.to(device)
    xvector_model.eval()
    return xvector_model, torch.device(device)
