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

# ฟังก์ชันสร้างซับไตเติ้ลแบบ Overlay (เทคนิคประหยัด RAM ป้องกันการเรนเดอร์ค้าง)
def create_subtitle_overlay(text, size):
    width, height = size
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    if text:
        font_path = "Kanit-Bold.ttf"
        try:
            # ขนาดฟอนต์ 3% เพื่อความพรีเมียม ไม่บังรายละเอียดที่ดิน
            font_size = int(height * 0.03) 
            font = ImageFont.truetype(font_path, font_size) if os.path.exists(font_path) else ImageFont.load_default()
        except:
            font = ImageFont.load_default()

        wrapped_text = textwrap.fill(text, width=50) 
        bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font, align="center")
        text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
        
        x, y = (width - text_w) / 2, height - text_h - 100 

        # วาด Outline สีดำเพื่อให้อ่านง่ายในทุกสภาพแสง
        for dx, dy in [(-2,-2), (2,2), (-2,2), (2,-2)]:
            draw.multiline_text((x+dx, y+dy), wrapped_text, font=font, fill=(0,0,0,255), align="center")
        
        # วาดตัวหนังสือสีขาว
        draw.multiline_text((x, y), wrapped_text, font=font, fill=(255,255,255,255), align="center")
    
    return np.array(overlay)

if 'final_video_path' not in st.session_state:
    st.session_state.final_video_path = None

st.title("🎬 Jigsaw Master (Universal Audio & Video Support)")

# --- หมวดที่ 2: UI Layout (Assets & Terminal) ---
col1, col2 = st.columns([1, 1])
with col1:
    st.header("📂 Assets")
    uploaded_files = st.file_uploader("Add Images or MP4", type=['jpg', 'png', 'jpeg', 'mp4'], accept_multiple_files=True)
    # รองรับการดึงเสียงจากทุกฟอร์แมต รวมถึงไฟล์วิดีโอ
    global_bgm = st.file_uploader("Upload BGM (MP3, WAV, M4A, MP4)", type=["mp3", "wav", "m4a", "mp4"])

with col2:
    st.header("🖥️ System Terminal")
    bgm_volume = st.slider("BGM Volume:", 0.0, 1.0, 0.15, 0.05)
    voice_volume = st.slider("Voiceover Volume:", 0.0, 1.0, 0.90, 0.05)
    
    st.markdown("### 🛡️ Safe Music Hub")
    m_col1, m_col2 = st.columns(2)
    with m_col1: st.link_button("🎵 FB Sound Collection", "https://www.facebook.com/sound/collection/")
    with m_col2: st.link_button("📺 YouTube Library", "https://www.youtube.com/audiolibrary")

st.divider()

# --- หมวดที่ 3: Render Engine ---
scene_configs = []

if uploaded_files:
    sorted_files = sorted(uploaded_files, key=lambda x: x.name)
    
    for i, file in enumerate(sorted_files):
        with st.expander(f"🎤 Scene {i+1}: {file.name}", expanded=True):
            sc_col1, sc_col2 = st.columns([2, 1])
            with sc_col1:
                cap = st.text_area(f"Subtitle (บทพูด):", key=f"cap_{i}")
            with sc_col2:
                # รองรับการใส่เสียงพากย์ราย Scene ได้ทุกฟอร์แมต
                v_file = st.file_uploader(f"Add Voiceover", type=['mp3', 'wav', 'm4a', 'mp4'], key=f"voice_{i}")
                dur = st.slider(f"Duration", 1.0, 30.0, get_reading_duration(cap), key=f"dur_{i}")
            
            scene_configs.append({"file": file, "cap": cap, "dur": dur, "voice": v_file})

    if st.button("🚀 Start Render Final Video"):
        with st.status("🎬 Processing All Assets...") as status:
            try:
                final_clips = []
                for config in scene_configs:
                    suffix = os.path.splitext(config["file"].name)[1].lower()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as t:
                        t.write(config["file"].getvalue())
                        temp_path = t.name

                    # 1. จัดการส่วนภาพ/วิดีโอ
                    if suffix == '.mp4':
                        base_v = VideoFileClip(temp_path).subclip(0, config["dur"]).resize(width=1280)
                        sub_img = create_subtitle_overlay(config["cap"], base_v.size)
                        sub_clip = ImageClip(sub_img).set_duration(base_v.duration).set_position(('center', 'center'))
                        clip = CompositeVideoClip([base_v, sub_clip])
                    else:
                        img = Image.open(temp_path).convert("RGB")
                        # ปรับขนาดภาพให้เป็นมาตรฐาน 720p (1280px width)
                        img_array = np.array(img.resize((1280, int(1280 * img.height / img.width))))
                        sub_img = create_subtitle_overlay(config["cap"], (img_array.shape[1], img_array.shape[0]))
                        pil_base = Image.fromarray(img_array).convert("RGBA")
                        pil_sub = Image.fromarray(sub_img, "RGBA")
                        combined = Image.alpha_composite(pil_base, pil_sub)
                        clip = ImageClip(np.array(combined.convert("RGB"))).set_duration(config["dur"])

                    # 2. จัดการเสียงพากย์ (Universal Format)
                    if config["voice"]:
                        v_suffix = os.path.splitext(config["voice"].name)[1].lower()
                        with tempfile.NamedTemporaryFile(delete=False, suffix=v_suffix) as v_temp:
                            v_temp.write(config["voice"].getvalue())
                            # ถ้าเป็นวิดีโอ ให้ดึงเฉพาะ Track เสียง
                            if v_suffix == ".mp4":
                                v_audio = VideoFileClip(v_temp.name).audio.volumex(voice_volume)
                            else:
                                v_audio = AudioFileClip(v_temp.name).volumex(voice_volume)
                            clip = clip.set_audio(v_audio)
                    
                    final_clips.append(clip)

                # 3. รวมคลิปและใส่เพลงประกอบ (BGM)
                full_video = concatenate_videoclips(final_clips, method="compose")
                
                if global_bgm:
                    bg_suffix = os.path.splitext(global_bgm.name)[1].lower()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=bg_suffix) as bg_temp:
                        bg_temp.write(global_bgm.getvalue())
                        if bg_suffix == ".mp4":
                            bg_audio = VideoFileClip(bg_temp.name).audio.volumex(bgm_volume).set_duration(full_video.duration)
                        else:
                            bg_audio = AudioFileClip(bg_temp.name).volumex(bgm_volume).set_duration(full_video.duration)
                        
                        # รวมเสียงพากย์รายฉากกับเพลงประกอบเข้าด้วยกัน
                        new_audio = CompositeAudioClip([full_video.audio, bg_audio]) if full_video.audio else bg_audio
                        full_video = full_video.set_audio(new_audio)

                # 4. เขียนไฟล์วิดีโอ (ใช้ Preset เร็วสุดเพื่อความเสถียร)
                out_file = "jigsaw_master_final.mp4"
                full_video.write_videofile(out_file, fps=24, codec="libx264", audio_codec="aac", threads=4, preset="ultrafast")
                st.session_state.final_video_path = out_file
                status.update(label="✅ Render สำเร็จสมบูรณ์!", state="complete")
            except Exception as e:
                st.error(f"❌ Render Error: {str(e)}")

# --- หมวดที่ 4: Social Share Hub ---
if st.session_state.final_video_path:
    st.divider()
    res_c1, res_c2 = st.columns([1.5, 1])
    with res_c1:
        st.subheader("📺 Video Preview")
        st.video(st.session_state.final_video_path)
