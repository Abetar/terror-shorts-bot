#!/usr/bin/env bash
set -euo pipefail

DURATION="${DURATION:-72}"
OUT="${OUT:-final.mp4}"

# Estilo de subtítulos: lower-third, caja semitransparente, sin tapar la escena
SUB_STYLE="FontName=Arial,FontSize=46,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=3,Outline=2,Shadow=0,BackColour=&H80000000&,Alignment=2,MarginV=140,MarginL=70,MarginR=70,WrapStyle=2"

ffmpeg -y \
  -f lavfi -i "color=c=black:s=1080x1920:d=${DURATION}" \
  -i voice.mp3 \
  -f lavfi -i "anoisesrc=color=white:amplitude=0.02:d=${DURATION}" \
  -filter_complex "\
    [0:v]noise=alls=18:allf=t+u,vignette=PI/5,eq=contrast=1.10:brightness=-0.04[subbg]; \
    [subbg]subtitles=subs.srt:original_size=1080x1920:force_style='${SUB_STYLE}'[v]; \
    [1:a]aformat=fltp:44100:stereo,volume=1.0[voice]; \
    [2:a]aformat=fltp:44100:stereo,volume=0.22[amb]; \
    [voice][amb]amix=inputs=2:duration=first[a] \
  " \
  -map "[v]" -map "[a]" \
  -c:v libx264 -pix_fmt yuv420p -r 30 \
  -c:a aac -b:a 160k \
  -shortest \
  "${OUT}"

echo "OK: ${OUT} generated"
