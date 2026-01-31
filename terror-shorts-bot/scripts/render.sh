#!/usr/bin/env bash
set -euo pipefail

DURATION="${DURATION:-72}"   # segundos aprox
OUT="${OUT:-final.mp4}"

# Fondo: negro + ruido + viñeta (barato y efectivo para terror)
# Audio ambiente: ruido suave (anoisesrc) mezclado con la voz
# Subtítulos: centrados abajo, grandes, con contorno

ffmpeg -y \
  -f lavfi -i "color=c=black:s=1080x1920:d=${DURATION}" \
  -i voice.mp3 \
  -f lavfi -i "anoisesrc=color=white:amplitude=0.02:d=${DURATION}" \
  -filter_complex "\
    [0:v]noise=alls=18:allf=t+u,vignette=PI/5,eq=contrast=1.15:brightness=-0.05[subbg]; \
    [subbg]subtitles=subs.srt:force_style='FontName=Arial,FontSize=54,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=1,Outline=4,Shadow=0,Alignment=2,MarginV=220'[v]; \
    [1:a]aformat=fltp:44100:stereo,volume=1.0[voice]; \
    [2:a]aformat=fltp:44100:stereo,volume=0.25[amb]; \
    [voice][amb]amix=inputs=2:duration=first[a] \
  " \
  -map "[v]" -map "[a]" \
  -c:v libx264 -pix_fmt yuv420p -r 30 \
  -c:a aac -b:a 160k \
  -shortest \
  "${OUT}"

echo "OK: ${OUT} generado"
