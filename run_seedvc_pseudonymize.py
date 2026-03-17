#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
run_seedvc_anonymize.py

- inputs/*.wav (n本; 話者ごと) を入力
- Hugging Faceからダウンロード済みの pool_xvecs.npz を読む
- 入力話者 x-vector と pool_xvecs を使って、(球面kmeans+直交化)+(Hungarian)で置換先を決定
- 置換先x-vectorで短い参照音声(ref)をTTS合成
- Seed-VC で source->ref voice へ speech->speech 変換

前提:
- seed-vc リポジトリが ./seed-vc にある（git clone しておく）
"""

import argparse, glob, json, os, subprocess, sys
import numpy as np
import torch

from pseudonymize_meeting_tts_seedvc import (
    download_tts_model_files,
    load_tts,
    load_jtubespeech_xvector,
    extract_xvector_jtubespeech,
    choose_anonymization_xvectors,
    save_wav,
    synthesize_with_spembs,
)

def synth_ref(tts, spemb, out_path, text, max_sec=10.0):
    wav, sr = synthesize_with_spembs(tts, text, spemb)
    if max_sec and max_sec > 0:
        wav = wav[: int(sr * max_sec)]
    save_wav(out_path, wav, sr)
    return out_path

def seedvc_convert(seed_vc_dir, source, target, out_dir, steps, cfg, fp16=True):
    os.makedirs(out_dir, exist_ok=True)
    script = os.path.join(seed_vc_dir, "inference.py")
    if not os.path.exists(script):
        raise SystemExit(f"Missing {script}. Did you git clone seed-vc?")
    cmd = [
        "python", script,
        "--source", source,
        "--target", target,
        "--output", out_dir,
        "--diffusion-steps", str(int(steps)),
        "--inference-cfg-rate", str(float(cfg)),
        "--fp16", str(bool(fp16)),
    ]
    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

def newest_wav(dirpath):
    wavs = sorted(glob.glob(os.path.join(dirpath, "*.wav")), key=os.path.getmtime)
    return wavs[-1] if wavs else None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs_dir", default="inputs", help="inputs/*.wav (n speakers)")
    ap.add_argument("--pool_npz", required=True, help="precomputed pool npz (xvecs, ids)")
    ap.add_argument("--seed_vc_dir", default="seed-vc", help="Seed-VC repo dir")
    ap.add_argument("--out_dir", default="outputs_seedvc", help="output directory")
    ap.add_argument("--refs_dir", default="refs", help="reference audio output directory")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--use_center", action="store_true", help="use cluster center instead of real pool member")
    ap.add_argument("--ref_text", default="これは参照用の短い音声です。", help="TTS text for reference prompt")
    ap.add_argument("--ref_max_sec", type=float, default=10.0)
    ap.add_argument("--diffusion_steps", type=int, default=25)
    ap.add_argument("--cfg", type=float, default=0.7, help="Seed-VC inference-cfg-rate")
    ap.add_argument("--device", default=None, help="cuda or cpu (default:auto)")
    args = ap.parse_args()

    speaker_wavs = sorted(glob.glob(os.path.join(args.inputs_dir, "*.wav")))
    if len(speaker_wavs) == 0:
        raise SystemExit(f"No wavs found: {args.inputs_dir}/*.wav")
    n = len(speaker_wavs)
    print("n_speakers =", n)

    # load pool xvecs
    data = np.load(args.pool_npz, allow_pickle=True)
    pool_xvecs = data["xvecs"].astype(np.float32)
    if pool_xvecs.ndim != 2 or pool_xvecs.shape[1] != 512:
        raise SystemExit(f"pool_xvecs must be [M,512], got {pool_xvecs.shape}")
    print("pool_xvecs:", pool_xvecs.shape)

    # load models
    paths = download_tts_model_files(output_dir="model_files")
    tts = load_tts(paths["config_file"], paths["model_file"], device=args.device)
    xvec_model, xvec_device = load_jtubespeech_xvector(device=args.device)

    # meeting xvecs
    meeting_xvecs = []
    for w in speaker_wavs:
        meeting_xvecs.append(extract_xvector_jtubespeech(w, xvec_model, xvec_device).numpy()[0])
    meeting_xvecs = np.stack(meeting_xvecs, axis=0).astype(np.float32)

    # mapping
    mapping = choose_anonymization_xvectors(
        meeting_speaker_xvecs=meeting_xvecs,
        pool_xvecs=pool_xvecs,
        n_clusters=n,
        seed=args.seed,
    )

    os.makedirs(args.refs_dir, exist_ok=True)
    os.makedirs(args.out_dir, exist_ok=True)

    for i, src in enumerate(speaker_wavs):
        info = mapping[i]
        target_xv = info["target_center"] if args.use_center else info["target_pool_member"]

        ref_path = os.path.join(args.refs_dir, f"ref_speaker{i}.wav")
        synth_ref(tts, target_xv, ref_path, args.ref_text, args.ref_max_sec)

        out_spk_dir = os.path.join(args.out_dir, f"speaker{i}")
        seedvc_convert(args.seed_vc_dir, src, ref_path, out_spk_dir, args.diffusion_steps, args.cfg, fp16=True)
        out_wav = newest_wav(out_spk_dir)

        print(
            f"speaker{i} -> cluster{int(info['cluster_index'])}, pool_idx={int(info['pool_index'])}, "
            f"cos_sim(orig, center)={float(info['cos_sim_to_orig']):.3f}"
        )
        print("  ref:", ref_path)
        print("  out:", out_wav or out_spk_dir)

if __name__ == "__main__":
    main()
