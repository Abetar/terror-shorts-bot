#!/usr/bin/env bash
set -euo pipefail

OUT="${OUT:-final.mp4}"

# Duración REAL (float) del audio: el audio manda
AUDIO_DUR="$(ffprobe -v error -show_entries format=duration -of default=nk=1:nw=1 voice.mp3)"
# Por si ffprobe devuelve vacío
if [[ -z "${AUDIO_DUR}" ]]; then
  echo "[render] ERROR: Could not read voice.mp3 duration via ffprobe"
  exit 1
fi

# Si DURATION no está definida, usamos la del audio (float)
DURATION="${DURATION:-$AUDIO_DUR}"

# Divide duración en 3 partes (float) para clip1/2/3
# (evita enteros para que no se recorte raro)
D1="${D1:-$(python - <<PY
d=float("${DURATION}")
print(d/3.0)
PY
)}"
D2="${D2:-$(python - <<PY
d=float("${DURATION}")
print(d/3.0)
PY
)}"
D3="${D3:-$(python - <<PY
d=float("${DURATION}")
d1=d/3.0
d2=d/3.0
print(max(0.1, d - d1 - d2))
PY
)}"

# Subtítulos: lower-third con caja semitransparente (NO tapa todo)
# OJO: FontSize=12 es muy chico para 1080x1920; si lo ves chico súbelo a 34–44.
SUB_STYLE="FontName=Arial,FontSize=12,PrimaryColour=&H00FFFFFF&,OutlineColour=&H00000000&,BorderStyle=3,Outline=0,Shadow=0,BackColour=&H33000000&,Alignment=2,MarginV=170,MarginL=140,MarginR=140,WrapStyle=2"

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
    -stream_loop -1 -i "$B1" \
    -stream_loop -1 -i "$B2" \
    -stream_loop -1 -i "$B3" \
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
    -t "${AUDIO_DUR}" \
    -c:v libx264 -pix_fmt yuv420p -r 30 \
    -c:a aac -b:a 160k \
    "${OUT}"
else
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
    -t "${AUDIO_DUR}" \
    -c:v libx264 -pix_fmt yuv420p -r 30 \
    -c:a aac -b:a 160k \
    "${OUT}"
fi

echo "OK: ${OUT} generated (AUDIO_DUR=${AUDIO_DUR}s, DURATION=${DURATION}s, D1=${D1}, D2=${D2}, D3=${D3})"
