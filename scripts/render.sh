#!/usr/bin/env bash
set -euo pipefail

OUT="${OUT:-final.mp4}"

# Si no defines DURATION, la calculamos desde voice.mp3 (recomendado)
if [[ -z "${DURATION:-}" ]]; then
  DURATION="$(ffprobe -v error -show_entries format=duration -of default=nk=1:nw=1 voice.mp3 | awk '{print int($1+0.5)}')"
fi

# Divide duración en 3 partes (para clip1/2/3)
D1="${D1:-$((DURATION/3))}"
D2="${D2:-$((DURATION/3))}"
D3="${D3:-$((DURATION - D1 - D2))}"

# Subtítulos: lower-third con caja semitransparente (NO tapa todo)
SUB_STYLE="FontName=Arial,FontSize=34,PrimaryColour=&H00FFFFFF&,OutlineColour=&H00000000&,BorderStyle=3,Outline=1,Shadow=0,BackColour=&H4D000000&,Alignment=2,MarginV=80,MarginL=120,MarginR=120,WrapStyle=2"

B1="out/broll/clip1.mp4"
B2="out/broll/clip2.mp4"
B3="out/broll/clip3.mp4"

use_broll=true
if [[ ! -f "$B1" || ! -f "$B2" || ! -f "$B3" ]]; then
  echo "[render] Missing b-roll clips in out/broll/. Falling back to black background."
  use_broll=false
fi

if [[ "$use_broll" == "true" ]]; then
  ffmpeg -y \
    -i "$B1" -i "$B2" -i "$B3" \
    -i voice.mp3 \
    -f lavfi -i "anoisesrc=color=white:amplitude=0.02:d=${DURATION}" \
    -filter_complex "\
      [0:v]trim=0:${D1},setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,eq=contrast=1.05:brightness=-0.03[v0]; \
      [1:v]trim=0:${D2},setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,eq=contrast=1.05:brightness=-0.03[v1]; \
      [2:v]trim=0:${D3},setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,eq=contrast=1.05:brightness=-0.03[v2]; \
      [v0][v1][v2]concat=n=3:v=1:a=0,noise=alls=10:allf=t+u,vignette=PI/7[base]; \
      [base]subtitles=subs.srt:original_size=1080x1920:force_style='${SUB_STYLE}'[v]; \
      [3:a]aformat=fltp:44100:stereo,volume=1.0[voice]; \
      [4:a]aformat=fltp:44100:stereo,volume=0.18[amb]; \
      [voice][amb]amix=inputs=2:duration=first[a] \
    " \
    -map "[v]" -map "[a]" \
    -c:v libx264 -pix_fmt yuv420p -r 30 \
    -c:a aac -b:a 160k \
    -shortest \
    "${OUT}"
else
  # fallback: fondo negro si no hay clips
  ffmpeg -y \
    -f lavfi -i "color=c=black:s=1080x1920:d=${DURATION}" \
    -i voice.mp3 \
    -f lavfi -i "anoisesrc=color=white:amplitude=0.02:d=${DURATION}" \
    -filter_complex "\
      [0:v]noise=alls=12:allf=t+u,vignette=PI/7,eq=contrast=1.08:brightness=-0.04[base]; \
      [base]subtitles=subs.srt:original_size=1080x1920:force_style='${SUB_STYLE}'[v]; \
      [1:a]aformat=fltp:44100:stereo,volume=1.0[voice]; \
      [2:a]aformat=fltp:44100:stereo,volume=0.18[amb]; \
      [voice][amb]amix=inputs=2:duration=first[a] \
    " \
    -map "[v]" -map "[a]" \
    -c:v libx264 -pix_fmt yuv420p -r 30 \
    -c:a aac -b:a 160k \
    -shortest \
    "${OUT}"
fi

echo "OK: ${OUT} generated (DURATION=${DURATION}s, D1=${D1}, D2=${D2}, D3=${D3})"
