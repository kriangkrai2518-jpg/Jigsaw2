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

# --- หมวดที่ 1: มาตรฐานระบบ (Locked 🔒) ---
st.set_page_config(page_title="Jigsaw Universal Assembler", layout="wide")

def get_reading_duration(text):
    if not text: return 4.0
    return min(max(4.0, len(text) / 15), 12.0)

def create_subtitle_overlay(text, size):
    width, height = size
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    if text:
        font_path = "Kanit-Bold.ttf"
        try:
            font_size = int(height * 0.03) # ขนาดฟอนต์ 3% เพื่อความพรีเมียม
            font = ImageFont.truetype(font_path, font_size) if os.path.exists(font_path) else ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        wrapped_text = textwrap.fill(text, width=50) 
        bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, align="center")
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        x, y = (width - text_w) / 2, height - text_h - 100 
        for dx, dy in [(-2,-2), (2,2), (-2,2), (2,-2)]:
            draw.multiline_text((x+dx, y+dy), wrapped_text, font=font, fill=(0,0,0,255), align="center")
        draw.multiline_text((x, y), wrapped_text, font=font, fill=(255,255,255,255), align="center")
    return np.array(overlay)

if 'final_video_path' not in st.session_state:
    st.session_state.final_video_path = None

st.title("🎬 Jigsaw Master (Ultra-Stable Engine)")

# --- หมวดที่ 2: UI Layout ---
col1, col2 = st.columns([1, 1])
with col1:
    st.header("📂 Assets")
    uploaded_files = st.file_uploader("Add Images/MP4", type=['jpg','png','jpeg','mp4'], accept_multiple_files=True)
    global_bgm = st.file_uploader("Upload BGM (All Formats)", type=["mp3","wav","m4a","mp4"])

with col2:
    st.header("🖥️ Terminal")
    bgm_volume = st.slider("BGM Volume:", 0.0, 1.0, 0.15, 0.05)
    voice_volume = st.slider("Voiceover Volume:", 0.0, 1.0, 0.90, 0.05)
    st.markdown("### 🛡️ Safe Music Hub")
    m_col1, m_col2 = st.columns(2)
    with m_col1: st.link_button("🎵 FB Sound", "https://www.facebook.com/sound/collection/")
    with m_col2: st.link_button("📺 YT Library", "https://www.youtube.com/audiolibrary")

st.divider()

# --- หมวดที่ 3: Render Engine ---
scene_configs = []
if uploaded_files:
    sorted_files = sorted(uploaded_files, key=lambda x: x.name)
    for i, file in enumerate(sorted_files):
        with st.expander(f"🎤 Scene {i+1}: {file.name}", expanded=True):
            sc_col1, sc_col2 = st.columns([2, 1])
            with sc_col1:
                cap = st.text_area(f"Subtitle:", key=f"cap_{i}")
            with sc_col2:
                v_file = st.file_uploader(f"Voiceover", type=['mp3','wav','m4a','mp4'], key=f"voice_{i}")
                dur = st.slider(f"Duration", 1.0, 30.0, get_reading_duration(cap), key=f"dur_{i}")
            scene_configs.append({"file": file, "cap": cap, "dur": dur, "voice": v_file})

    if st.button("🚀 Start Render Final Video"):
        with st.status("🎬 Processing with Ultra-Stable Engine...") as status:
            try:
                final_clips = []
                for i, config in enumerate(scene_configs):
                    suffix = os.path.splitext(config["file"].name)[1].lower()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as t:
                        t.write(config["file"].getvalue())
                        temp_path = t.name

                    # Visual Processing
                    if suffix == '.mp4':
                        base_v = VideoFileClip(temp_path).subclip(0, config["dur"]).resize(width=1280)
                        sub_img = create_subtitle_overlay(config["cap"], base_v.size)
                        sub_clip = ImageClip(sub_img).set_duration(base_v.duration).set_position(('center', 'center'))
                        clip = CompositeVideoClip([base_v, sub_clip])
                    else:
                        img = Image.open(temp_path).convert("RGB")
                        img_array = np.array(img.resize((1280, int(1280 * img.height / img.width))))
                        sub_img = create_subtitle_overlay(config["cap"], (img_array.shape[1], img_array.shape[0]))
                        pil_base, pil_sub = Image.fromarray(img_array).convert("RGBA"), Image.fromarray(sub_img, "RGBA")
                        combined = Image.alpha_composite(pil_base, pil_sub)
                        clip = ImageClip(np.array(combined.convert("RGB"))).set_duration(config["dur"])

                    # 🛡️ Robust Voiceover Handler (ป้องกันไฟล์เสีย)
                    if config["voice"]:
                        try:
                            v_bytes = config["voice"].getvalue()
                            if len(v_bytes) > 0: # ตรวจสอบขนาดไฟล์
                                v_suffix = os.path.splitext(config["voice"].name)[1].lower()
                                with tempfile.NamedTemporaryFile(delete=False, suffix=v_suffix) as v_temp:
                                    v_temp.write(v_bytes)
                                    v_audio = VideoFileClip(v_temp.name).audio if v_suffix == ".mp4" else AudioFileClip(v_temp.name)
                                    v_audio = v_audio.volumex(voice_volume).set_duration(clip.duration)
                                    clip = clip.set_audio(v_audio)
                        except:
                            st.warning(f"⚠️ ข้ามเสียงพากย์ Scene {i+1} เพราะไฟล์มีปัญหา")
                    
                    final_clips.append(clip)

                full_video = concatenate_videoclips(final_clips, method="compose")
                
                # 🛡️ Robust BGM Handler
                if global_bgm:
                    try:
                        bg_bytes = global_bgm.getvalue()
                        if len(bg_bytes) > 0:
                            bg_suffix = os.path.splitext(global_bgm.name)[1].lower()
                            with tempfile.NamedTemporaryFile(delete=False, suffix=bg_suffix) as bg_temp:
                                bg_temp.write(bg_bytes)
                                bg_audio = VideoFileClip(bg_temp.name).audio if bg_suffix == ".mp4" else AudioFileClip(bg_temp.name)
                                bg_audio = bg_audio.volumex(bgm_volume).set_duration(full_video.duration)
                                
                                tracks = [bg_audio]
                                if full_video.audio: tracks.append(full_video.audio)
                                full_video = full_video.set_audio(CompositeAudioClip(tracks))
                    except:
                        st.warning("⚠️ ไม่สามารถโหลด BGM ได้")

                out_file = "jigsaw_ultra_stable.mp4"
                full_video.write_videofile(out_file, fps=24, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast")
                st.session_state.final_video_path = out_file
                status.update(label="✅ Render สำเร็จ!", state="complete")
            except Exception as e:
                st.error(f"❌ ระบบขัดข้อง: {str(e)}")

# --- หมวดที่ 4: Social Hub ---
if st.session_state.final_video_path:
    st.divider()
    res_c1, res_c2 = st.columns([1.5, 1])
    with res_c1:
        st.video(st.session_state.final_video_path)
        with open(st.session_state.final_video_path, "rb") as f:
            st.download_button("📥 Download Video", f, "jigsaw_render.mp4", use_container_width=True)
    with res_c2:
        st.subheader("🚀 Social Share")
        st.link_button("🔵 Facebook Reels", "https://www.facebook.com/reels/create/", use_container_width=True)
        st.link_button("⚫ TikTok Upload", "https://www.tiktok.com/upload", use_container_width=True)
        st.link_button("🔴 YouTube Shorts", "https://www.youtube.com/upload", use_container_width=True)
