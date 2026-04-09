import streamlit as st
from moviepy.editor import ImageClip, VideoFileClip, AudioFileClip, concatenate_videoclips, CompositeVideoClip, CompositeAudioClip, vfx
from moviepy.audio.AudioClip import AudioArrayClip
import tempfile, os, textwrap, numpy as np
from PIL import Image, ImageDraw, ImageFont

# --- 1. ระบบพื้นฐาน ---
st.set_page_config(page_title="Jigsaw Branding Master", layout="wide")

def create_sub(text, size):
    w, h = size
    ov = Image.new('RGBA', (w, h), (0,0,0,0))
    d = ImageDraw.Draw(ov)
    if text:
        try: f = ImageFont.truetype("Kanit-Bold.ttf", int(h*0.04))
        except: f = ImageFont.load_default()
        wt = textwrap.fill(text, width=40)
        bx = d.multiline_textbbox((0,0), wt, font=f)
        tw, th = bx[2]-bx[0], bx[3]-bx[1]
        d.multiline_text(((w-tw)/2, h-th-80), wt, font=f, fill=(255,255,255,255), align="center", stroke_width=2, stroke_fill=(0,0,0,255))
    return np.array(ov)

# ✅ ฟังก์ชันสำหรับสร้างลายน้ำด้านบน
def create_watermark(text, size):
    w, h = size
    ov = Image.new('RGBA', (w, h), (0,0,0,0))
    d = ImageDraw.Draw(ov)
    if text:
        try: f = ImageFont.truetype("Kanit-Bold.ttf", int(h*0.025))
        except: f = ImageFont.load_default()
        # วางไว้มุมขวาบน แบบโปร่งใส (100)
        d.text((w-200, 40), text, font=f, fill=(255,255,255,100))
    return np.array(ov)

# ✅ ฟังก์ชันใหม่สำหรับสร้างแบนเนอร์เบอร์โทรด้านบน
def create_contact_banner(phone, message, size):
    w, h = size
    b_h = int(h * 0.08) # ความสูงแบนเนอร์ 8%
    ov = Image.new('RGBA', (w, h), (0,0,0,0))
    d = ImageDraw.Draw(ov)
    if phone:
        # แถบสีดำบางๆ ด้านบน
        d.rectangle((0, 0, w, b_h), fill=(0,0,0,180)) # โปร่งใสเล็กน้อย (180)
        try: f = ImageFont.truetype("Kanit-Bold.ttf", int(h*0.03))
        except: f = ImageFont.load_default()
        full_text = f"{message}: {phone}"
        d.text((40, 10), full_text, font=f, fill=(255,255,255,255))
    return np.array(ov)

def make_silence(duration, fps=44100):
    return AudioArrayClip(np.zeros((int(fps*duration), 2)), fps=fps)

if 'v_path' not in st.session_state: st.session_state.v_path = None
if 'line_v_path' not in st.session_state: st.session_state.line_v_path = None

st.title("🎬 Jigsaw Master (Branding Edition)")

# --- 2. UI Layout ---
col1, col2 = st.columns([1, 1])
with col1:
    st.header("📂 Assets & Data")
    files = st.file_uploader("Add Video/Images", type=['jpg','png','jpeg','mp4'], accept_multiple_files=True)
    bgm_f = st.file_uploader("🎵 Global BGM", type=["mp3","wav","m4a"])

with col2:
    st.header("⚙️ Branding & Export")
    # ✅ ช่องใส่ลายน้ำ (Watermark)
    wm_text = st.text_input("Watermark Text (Top):", value="Property of [USER NAME]")
    # ✅ ช่องใส่แบนเนอร์เบอร์โทร (Contact Banner)
    phone_num = st.text_input("Contact Banner (Phone):", value="[USER PHONE NUMBER]")
    contact_msg = st.text_input("Contact Message:", value="Call Us Now!")
    
    bgm_v = st.slider("BGM Volume", 0.0, 1.0, 0.10, 0.05)
    voice_v = st.slider("Voice Balance", 0.0, 1.0, 0.90, 0.05)
