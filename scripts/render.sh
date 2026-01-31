#!/usr/bin/env bash
set -euo pipefail

OUT="${OUT:-final.mp4}"
BROLL_DIR="${BROLL_DIR:-out/broll}"
DEBUG_OVERLAY="${DEBUG_OVERLAY:-1}"  # 1 = muestra overlay para confirmar video

CLIP1="${BROLL_DIR}/clip1.mp4"
CLIP2="${BROLL_DIR}/clip2.mp4"
CLIP3="${BROLL_DIR}/clip3.mp4"

if [[ ! -f "${CLIP1}" || ! -f "${CLIP2}" || ! -f "${CLIP3}" ]]; then
  echo "Missing b-roll clips in ${BROLL_DIR}. Expected clip1.mp4, clip2.mp4, clip3.mp4"
  exit 1
fi

# overlay simple para debug (si lo pones en 0, no se pinta)
if [[ "${DEBUG_OVERLAY}" == "1" ]]; then
  OVERLAY_FILTER="drawtext=text='BROLL OK':x=30:y=30:fontsize=36:fontcolor=white:box=1:boxcolor=black@0.5"
else
  OVERLAY_FILTER="null"
fi

ffmpeg -y \
  -i "${CLIP1}" -i "${CLIP2}" -i "${CLIP3}" \
  -i voice.mp3 \
  -f lavfi -i "anoisesrc=color=white:amplitude=0.02" \
  -filter_complex "\
    [0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[v0]; \
    [1:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[v1]; \
    [2:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1[v2]; \
    [v0][v1][v2]concat=n=3:v=1:a=0, \
      eq=contrast=1.18:brightness=0.08:saturation=1.05, \
      vignette=PI/7, \
      ${OVERLAY_FILTER}, \
      subtitles=subs.srt:force_style='FontName=Arial,FontSize=54,PrimaryColour=&HFFFFFF&,OutlineColour=&H000000&,BorderStyle=1,Outline=4,Shadow=0,Alignment=2,MarginV=220' \
      [v]; \
    [3:a]aformat=fltp:44100:stereo,volume=1.0[voice]; \
    [4:a]aformat=fltp:44100:stereo,volume=0.22[amb]; \
    [voice][amb]amix=inputs=2:duration=first[a] \
  " \
  -map "[v]" -map "[a]" \
  -c:v libx264 -pix_fmt yuv420p -r 30 \
  -c:a aac -b:a 160k \
  -shortest \
  "${OUT}"

echo "OK: ${OUT} generated"
