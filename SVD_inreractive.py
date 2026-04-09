import streamlit as st
from moviepy.editor import (
    ImageClip, VideoFileClip, AudioFileClip, 
    concatenate_videoclips, CompositeVideoClip, CompositeAudioClip
)
import tempfile
import os
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import textwrap

# --- หมวดที่ 1: ระบบพื้นฐาน ---
st.set_page_config(page_title="Jigsaw Universal Assembler", layout="wide")

def create_subtitle_overlay(text, size):
    width, height = size
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    if text:
        font_path = "Kanit-Bold.ttf"
        try:
            font_size = int(height * 0.04) 
            font = ImageFont.truetype(font_path, font_size) if os.path.exists(font_path) else ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        wrapped_text = textwrap.fill(text, width=40) 
        bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, align="center")
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x, y = (width - text_w) / 2, height - text_h - 80 
        draw.multiline_text((x, y), wrapped_text, font=font, fill=(255,255,255,255), align="center", stroke_width=2, stroke_fill=(0,0,0,255))
    return np.array(overlay)

if 'final_video_path' not in st.session_state:
    st.session_state.final_video_path = None

st.title("🎬 Jigsaw Master (Dual-Channel Fixed)")

# --- หมวดที่ 2: ส่วนรับข้อมูล ---
col1, col2 = st.columns([1, 1])
with col1:
    st.header("📂 Assets")
    uploaded_files = st.file_uploader("Add Images/MP4", type=['jpg','png','jpeg','mp4'], accept_multiple_files=True)
    global_bgm = st.file_uploader("🎵 Global BGM", type=["mp3","wav","m4a"])

with col2:
    st.header("🖥️ Audio Mixer")
    bgm_volume = st.slider("BGM Volume", 0.0, 1.0, 0.15, 0.05)
    voice_volume = st.slider("Voiceover Volume", 0.0, 1.0, 0.90, 0.05)

st.divider()

# --- หมวดที่ 3: ระบบเรนเดอร์ ---
scene_configs = []
if uploaded_files:
    sorted_files = sorted(uploaded_files, key=lambda x: x.name)
    for i, file in enumerate(sorted_files):
        with st.expander(f"🎤 Scene {i+1}", expanded=True):
            sc_col1, sc_col2 = st.columns([2, 1])
            with sc_col1:
                cap = st.text_area(f"Subtitle:", key=f"cap_{i}", value=f"Scene {i+1}")
            with sc_col2:
                v_file = st.file_uploader(f"Voiceover", type=['mp3','wav','m4a'], key=f"voice_{i}")
                dur = st.slider(f"Duration", 1.0, 15.0, 4.0, key=f"dur_{i}")
            scene_configs.append({"file": file, "cap": cap, "dur": dur, "voice": v_file})

    if st.button("🚀 Start Render Final Video"):
        with st.status("🎬 Final Rendering...") as status:
            try:
                final_clips = []
                TARGET_FPS = 24 

                for i, config in enumerate(scene_configs):
                    suffix = os.path.splitext(config["file"].name)[1].lower()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as t:
                        t.write(config["file"].getvalue())
                        temp_path = t.name

                    if suffix == '.mp4':
                        base_v = VideoFileClip(temp_path).subclip(0, config["dur"]).resize(width=1280).set_fps(TARGET_FPS).without_audio()
                    else:
                        img = Image.open(temp_path).convert("RGB")
                        img_array = np.array(img.resize((1280, int(1280 * img.height / img.width))))
                        base_v = ImageClip(img_array).set_duration(config["dur"]).set_fps(TARGET_FPS)

                    sub_img = create_subtitle_overlay(config["cap"], base_v.size)
                    sub_clip = ImageClip(sub_img).set_duration(base_v.duration).set_position(('center', 'center'))
                    clip = CompositeVideoClip([base_v, sub_clip])

                    # Voiceover Channel (Per Scene)
                    if config["voice"]:
                        v_suffix = os.path.splitext(config["voice"].name)[1].lower()
                        with tempfile.NamedTemporaryFile(delete=False, suffix=v_suffix) as v_temp:
                            v_temp.write(config["voice"].getvalue())
                            v_audio = AudioFileClip(v_temp.name).volumex(voice_volume).set_duration(clip.duration)
                            clip = clip.set_audio(v_audio)
                    
                    final_clips.append(clip)

                # รวมคลิปวิดีโอเข้าด้วยกัน
                full_video = concatenate_videoclips(final_clips, method="compose").set_fps(TARGET_FPS)
                
                # Global BGM Channel Mixing
                final_audio_tracks = []
                if full_video.audio:
                    final_audio_tracks.append(full_video.audio)

                if global_bgm:
                    bg_suffix = os.path.splitext(global_bgm.name)[1].lower()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=bg_suffix) as bg_temp:
                        bg_temp.write(global_bgm.getvalue())
                        bg_audio = AudioFileClip(bg_temp.name).volumex(bgm_volume).set_duration(full_video.duration)
                        final_audio_tracks.append(bg_audio)

                if final_audio_tracks:
                    full_video.audio = CompositeAudioClip(final_audio_tracks)

                out_file = "jigsaw_dual_fixed.mp4"
                full_video.write_videofile(
                    out_file, 
                    fps=TARGET_FPS, 
                    codec="libx264", 
                    audio_codec="aac", 
                    audio_fps=44100, 
                    temp_audiofile='temp-fix.m4a', 
                    remove_temp=True
                )
                
                st.session_state.final_video_path = out_file
