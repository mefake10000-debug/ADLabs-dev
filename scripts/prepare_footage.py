"""
Turn a raw CCTV/NVR export into clean, short clips the pipeline can use -- in one command.

Real recorder exports arrive broken in ways that standard decoders mishandle (see
docs/footage-tools.md for the garage footage that prompted this):
  * corrupted stretches that leave the decoder in a bad state, so everything AFTER them comes
    out grey, rotated or slanted, even though VLC plays on after you skip ahead;
  * scrambled timestamps (jumping hours back and forth), which make ffmpeg duplicate or drop
    frames, and inflate the file's apparent length;
  * H.265, which some tools and boards handle worse than H.264.

What this does:
  1. Copies the video stream out as raw H.264/H.265 data -- no timestamps at all, so scrambled
     ones simply disappear. Frames are numbered at a steady rate instead.
  2. Cuts that into ~60 s pieces at clean (key)frames, and decodes EACH piece with a FRESH
     decoder. A corrupted stretch can then spoil at most its own piece, never the rest.
  3. Re-encodes to H.264 (720p by default) and checks each piece for grey or garbled frames.
  4. Joins the pieces and slices them into N-minute clips, plus a contact sheet (one frame per
     minute per clip) and a report of anything suspect.

Run inside the edge container (it has ffmpeg + OpenCV); see docs/footage-tools.md:
    docker compose run --rm --no-deps \\
        -v "C:/path/to/raw/folder:/raw:ro" -v "./data/sample_videos/garage:/out" \\
        edge-analyzer python scripts/prepare_footage.py /raw/D01_20261013091838.mp4 --out-dir /out --name garage
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RAW_FORMATS = {"h264": "h264", "hevc": "hevc"}


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def probe(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=codec_name,width,height,r_frame_rate:format=duration", "-of", "json", path])
    info = json.loads(out.stdout or "{}")
    if not info.get("streams"):
        sys.exit(f"ERROR: no video stream found in {path}\n{out.stderr}")
    s = info["streams"][0]
    num, den = (s.get("r_frame_rate") or "0/1").split("/")
    fps = float(num) / float(den) if float(den) else 0.0
    return {"codec": s.get("codec_name"), "width": s.get("width"), "height": s.get("height"),
            "fps": fps, "duration_s": float(info.get("format", {}).get("duration") or 0)}


def timestamp_problems(path):
    """Counts packets whose timestamp goes backwards or jumps forward by more than 10 s."""
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time",
               "-of", "csv=p=0", path])
    backwards = jumps = 0
    prev = None
    for line in out.stdout.splitlines():
        try:
            t = float(line.strip().rstrip(","))
        except ValueError:
            continue
        if prev is not None:
            if t < prev - 1.0:
                backwards += 1
            elif t > prev + 10.0:
                jumps += 1
        prev = t
    return backwards, jumps


def frame_stats(img):
    """Share of the frame that is flat mid-grey (a 'grey frame') and near-black (slanted/garbled
    frames leave black wedges)."""
    g = cv2.resize(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (160, 90))
    grey = float(np.mean(np.abs(g.astype(np.int16) - 128) <= 3))
    black = float(np.mean(g <= 8))
    return grey, black


def sample_piece(path, every_s, fps):
    cap = cv2.VideoCapture(path)
    step = max(1, int(round(every_s * fps)))
    stats, n = [], 0
    while True:
        ok = cap.grab()
        if not ok:
            break
        if n % step == 0:
            ok, img = cap.retrieve()
            if ok:
                stats.append(frame_stats(img))
        n += 1
    cap.release()
    return stats, n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("input", help="Raw recorder export (mp4/avi/mkv/ts/...)")
    ap.add_argument("--name", required=True, help="Short name; clips are named <name>_partNN.mp4")
    ap.add_argument("--out-dir", default=None, help="Default: data/sample_videos/<name>/")
    ap.add_argument("--clip-minutes", type=float, default=10)
    ap.add_argument("--height", type=int, default=720, help="Output height in px (YOLO works at 640 anyway)")
    ap.add_argument("--fps", type=float, default=None, help="Override the frame rate (default: from the file)")
    ap.add_argument("--piece-seconds", type=float, default=60,
                    help="Fresh-decoder piece length: the most a corrupted stretch can spoil")
    ap.add_argument("--drop-bad", action="store_true",
                    help="Leave out pieces where most sampled frames look grey/garbled (default: keep, report)")
    ap.add_argument("--keep-work", action="store_true")
    args = ap.parse_args()

    started = time.time()
    out_dir = args.out_dir or os.path.join(ROOT, "data", "sample_videos", args.name)
    work = os.path.join(ROOT, "data", "storage", "footage_work", args.name)
    shutil.rmtree(work, ignore_errors=True)
    os.makedirs(work)
    os.makedirs(out_dir, exist_ok=True)

    # 1. Inspect
    info = probe(args.input)
    fps = args.fps or info["fps"]
    if not fps or fps > 60:
        print(f"WARNING: frame rate from the file looks wrong ({info['fps']}); using 15. Pass --fps to override.")
        fps = 15.0
    backwards, jumps = timestamp_problems(args.input)
    print(f"Input: {info['codec']} {info['width']}x{info['height']} @ {fps:g} fps, "
          f"claims {info['duration_s'] / 60:.1f} min")
    if backwards or jumps:
        print(f"  Timestamps are broken: {backwards} go backwards, {jumps} jump forward >10 s "
              f"(ignored -- frames are renumbered at {fps:g} fps)")
    raw_fmt = RAW_FORMATS.get(info["codec"])
    if not raw_fmt:
        sys.exit(f"ERROR: codec {info['codec']} not supported (expected H.264 or H.265)")

    # 2. Raw stream (drops every timestamp), cut into pieces at keyframes
    raw = os.path.join(work, f"stream.{raw_fmt}")
    r = run(["ffmpeg", "-v", "error", "-y", "-i", args.input, "-map", "0:v:0", "-c", "copy", "-f", raw_fmt, raw])
    if not os.path.exists(raw) or os.path.getsize(raw) == 0:
        sys.exit(f"ERROR: could not extract the video stream:\n{r.stderr[-2000:]}")
    if r.returncode != 0:
        print(f"  Note: stream extraction stopped early ({r.stderr.strip().splitlines()[-1][:120] if r.stderr.strip() else 'error'})"
              " -- continuing with what was extracted")
    run(["ffmpeg", "-v", "error", "-y", "-framerate", f"{fps:g}", "-i", raw, "-c", "copy", "-f", "segment",
         "-segment_time", f"{args.piece_seconds:g}", "-segment_format", raw_fmt, "-reset_timestamps", "1",
         os.path.join(work, f"piece%04d.{raw_fmt}")])
    os.remove(raw)
    pieces = sorted(glob.glob(os.path.join(work, f"piece*.{raw_fmt}")))
    print(f"  {len(pieces)} pieces of ~{args.piece_seconds:g} s")

    # 3. Fresh decode + re-encode per piece, then check it
    vf = f"setpts=N/{fps:g}/TB,scale=-2:{args.height}"
    report_pieces, kept = [], []
    for i, piece in enumerate(pieces):
        mp4 = piece.rsplit(".", 1)[0] + ".mp4"
        r = run(["ffmpeg", "-v", "error", "-y", "-err_detect", "ignore_err", "-fflags", "+discardcorrupt",
                 "-framerate", f"{fps:g}", "-i", piece, "-vf", vf, "-fps_mode", "cfr", "-r", f"{fps:g}",
                 "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-g", str(int(round(2 * fps))),
                 "-pix_fmt", "yuv420p", "-an", mp4])
        os.remove(piece)
        if not os.path.exists(mp4) or os.path.getsize(mp4) == 0:
            report_pieces.append({"piece": i, "frames": 0, "decode_errors": None, "verdict": "unreadable"})
            continue
        errors = sum(1 for line in r.stderr.splitlines() if line.startswith("["))
        stats, frames = sample_piece(mp4, 2.0, fps)
        report_pieces.append({"piece": i, "file": mp4, "frames": frames, "decode_errors": errors, "stats": stats})
        print(f"  piece {i + 1}/{len(pieces)}: {frames / fps:5.1f} s, {errors} decoder errors", end="\r")
    print()

    # Garbled frames are judged against this video's own normal look (some scenes are dark).
    all_black = [b for p in report_pieces for _, b in p.get("stats", [])]
    black_limit = max(0.15, 4 * float(np.median(all_black))) if all_black else 0.15
    for p in report_pieces:
        if p.get("verdict") == "unreadable":
            continue
        stats = p.pop("stats")
        bad = sum(1 for grey, black in stats if grey > 0.4 or black > black_limit)
        p["suspect_frames"] = f"{bad}/{len(stats)}"
        p["verdict"] = "bad" if stats and bad / len(stats) > 0.3 else ("some bad frames" if bad else "ok")
        if not (args.drop_bad and p["verdict"] == "bad"):
            kept.append(p)

    # 4. Join kept pieces and slice into clips
    listing = os.path.join(work, "pieces.txt")
    with open(listing, "w") as f:
        for p in kept:
            f.write(f"file '{p['file']}'\n")
    for old in glob.glob(os.path.join(out_dir, f"{args.name}_part*.mp4")):
        os.remove(old)
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", listing, "-c", "copy", "-f", "segment",
         "-segment_time", f"{args.clip_minutes * 60:g}", "-reset_timestamps", "1",
         os.path.join(out_dir, f"{args.name}_part%02d.mp4")])
    clips = sorted(glob.glob(os.path.join(out_dir, f"{args.name}_part*.mp4")))

    # Where each kept piece landed, so problems can be found in the clips
    clip_s = args.clip_minutes * 60
    position = 0.0
    for p in report_pieces:
        if p in kept:
            p["clip"] = f"{args.name}_part{int(position // clip_s):02d}.mp4"
            p["clip_time"] = f"{int(position % clip_s // 60):02d}:{position % 60:04.1f}"
            position += p["frames"] / fps
        p.pop("file", None)

    # Contact sheet: one frame per minute, one row per clip
    rows = []
    for c in clips:
        cap = cv2.VideoCapture(c)
        n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 1
        tiles = []
        for k in range(0, max(1, int(n / fps // 60)) + 1):
            cap.set(cv2.CAP_PROP_POS_FRAMES, min(n - 1, int(k * 60 * fps)))
            ok, img = cap.read()
            if ok:
                tile = cv2.resize(img, (256, 144))
                cv2.putText(tile, f"{os.path.basename(c)[-6:-4]} {k:02d}m", (4, 16), cv2.FONT_HERSHEY_SIMPLEX,
                            0.45, (0, 255, 255), 1)
                tiles.append(tile)
        cap.release()
        if tiles:
            row = np.hstack(tiles + [np.zeros_like(tiles[0])] * (11 - len(tiles))) if len(tiles) < 11 else np.hstack(tiles[:11])
            rows.append(row)
    if rows:
        cv2.imwrite(os.path.join(out_dir, "contact_sheet.jpg"), np.vstack(rows))

    total_s = sum(p["frames"] for p in kept) / fps
    flagged = [p for p in report_pieces if p["verdict"] != "ok"]
    report = {
        "input": args.input, "source": info, "fps_used": fps,
        "timestamps_backwards": backwards, "timestamps_jumps": jumps,
        "real_footage_minutes": round(total_s / 60, 1),
        "pieces": len(report_pieces), "pieces_kept": len(kept),
        "clips": [os.path.basename(c) for c in clips],
        "flagged_pieces": flagged,
        "minutes_taken": round((time.time() - started) / 60, 1),
    }
    with open(os.path.join(out_dir, "prep_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    if not args.keep_work:
        shutil.rmtree(work, ignore_errors=True)

    print("=" * 72)
    print(f"{len(clips)} clips, {total_s / 60:.1f} min of real footage, in {out_dir}")
    if flagged:
        print(f"{len(flagged)} piece(s) with grey/garbled frames"
              + (" (dropped)" if args.drop_bad else " (kept; --drop-bad leaves the worst out)") + ":")
        for p in flagged:
            where = f"{p.get('clip', '(dropped)')} at {p.get('clip_time', '-')}"
            print(f"  piece {p['piece']:3d}: {p['verdict']:16} suspect frames {p.get('suspect_frames', '-'):>6}, "
                  f"{p['decode_errors']} decoder errors -> {where}")
    print("Check contact_sheet.jpg, then prep_report.json for details.")
    print("=" * 72)


if __name__ == "__main__":
    main()
