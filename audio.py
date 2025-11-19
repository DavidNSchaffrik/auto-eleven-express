import os
import sys
import uuid
import shutil
import subprocess
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

# Load environment variables
load_dotenv()

# Initialize Client
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    raise ValueError("Please set ELEVENLABS_API_KEY in your .env file")

elevenlabs = ElevenLabs(api_key=ELEVENLABS_API_KEY)

def generate_segment_audio(text: str, settings: Dict[str, float], output_dir: str, voice_id: str) -> Optional[str]:
    """
    Generates audio for a single segment using ElevenLabs.
    """
    # Sanitize text just in case
    if not text or not isinstance(text, str) or not text.strip():
        return None
        
    print(f"    > Generating speech ({len(text)} chars): '{text[:20]}...'")
    try:
        response = elevenlabs.text_to_speech.convert(
            voice_id=voice_id,
            output_format="mp3_44100_128",
            text=text,
            model_id="eleven_multilingual_v2",
            voice_settings=VoiceSettings(
                stability=settings.get("stability", 0.5),
                similarity_boost=settings.get("similarity_boost", 0.75),
                style=settings.get("style", 0.0),
                use_speaker_boost=True,
                speed=settings.get("speed", 1.0),
            ),
        )

        temp_filename = os.path.join(output_dir, f"segment_{uuid.uuid4()}.mp3")
        
        with open(temp_filename, "wb") as f:
            for chunk in response:
                if chunk:
                    f.write(chunk)
        return temp_filename
    except Exception as e:
        print(f"    ! Error generating segment: {e}")
        return None

def generate_silence(duration: float, output_dir: str, ffmpeg_path: str) -> Optional[str]:
    """
    Generates a silent MP3 file using FFmpeg.
    """
    print(f"    > Generating {duration}s silence...")
    filename = os.path.join(output_dir, f"silence_{uuid.uuid4()}.mp3")
    
    cmd = [
        ffmpeg_path, "-y", "-f", "lavfi", 
        "-i", "anullsrc=r=44100:cl=mono", 
        "-t", str(duration), 
        "-c:a", "libmp3lame", "-b:a", "128k", 
        filename
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return filename
    except Exception as e:
        print(f"    ! Error generating silence: {e}")
        return None

def stitch_files(file_list: List[str], output_path: str, output_dir: str, ffmpeg_path: str) -> bool:
    """
    Stitches a list of MP3 files together into one output file.
    """
    concat_list_path = os.path.join(output_dir, f"concat_list_{uuid.uuid4()}.txt")
    
    try:
        # Write list file
        with open(concat_list_path, "w", encoding="utf-8") as f:
            for path in file_list:
                abs_path = os.path.abspath(path).replace("\\", "/")
                f.write(f"file '{abs_path}'\n")
        
        # FFmpeg command (re-encode for safety)
        cmd = [
            ffmpeg_path, "-y", "-f", "concat", "-safe", "0", 
            "-i", concat_list_path, 
            output_path
        ]
        
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        return True

    except Exception as e:
        print(f"    ! Error during stitching: {e}")
        return False
    finally:
        # Cleanup the list file
        if os.path.exists(concat_list_path):
            try: os.remove(concat_list_path)
            except: pass

def process_job(job_name: str, segments_data: List[Dict[str, Any]], output_dir: str, ffmpeg_path: str, voice_id: str):
    """
    Orchestrates the generation of one full audio file from a list of segment data.
    """
    print(f"\n--- Processing Job: {job_name} ---")
    generated_files = []
    
    for segment in segments_data:
        text = segment.get("text")
        settings = segment.get("settings")
        pause = segment.get("pause_duration", 0.0)
        
        # 1. Generate Audio
        if text:
            audio_path = generate_segment_audio(text, settings, output_dir, voice_id)
            if audio_path:
                generated_files.append(audio_path)
        
        # 2. Generate Silence
        if pause > 0:
            silence_path = generate_silence(pause, output_dir, ffmpeg_path)
            if silence_path:
                generated_files.append(silence_path)
    
    if generated_files:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_name = f"{job_name}_{timestamp}.mp3"
        final_path = os.path.join(output_dir, final_name)
        
        success = stitch_files(generated_files, final_path, output_dir, ffmpeg_path)
        
        if success:
            print(f"--> Success! Saved to: {final_name}")
        
        # Cleanup temps
        for f in generated_files:
            try: os.remove(f)
            except: pass
    else:
        print("--> No audio generated for this job.")

def main():
    # --- CONFIGURATION ---
    
    # Mode: "excel" or "file"
    INPUT_MODE = "excel" 
    
    # Settings
    OUTPUT_DIR = "output"
    EXCEL_PATH = "script_variations.xlsx"
    MANUAL_FFMPEG_PATH = r"C:\ffmpeg-8.0-essentials_build\bin\ffmpeg.exe" 
    
    # *** PASTE YOUR VOICE ID HERE ***
    VOICE_ID = "ohItIVrXTBI80RrUECOD" 
    
    # Define the Voice Settings for the 3 Sections
    # These apply to both Excel columns (Section 1, 2, 3) and text files
    SECTION_CONFIG = {
        1: {
            "pause_after": 0.8,
            "settings": {"stability": 0.9, "similarity_boost": 0.8, "style": 1.0, "speed": 1.05} # Fast/Stable
        },
        2: {
            "pause_after": 0.5,
            "settings": {"stability": 0.5, "similarity_boost": 1.0, "style": 0.0, "speed": 0.70} # Slow/Expressive
        },
        3: {
            "pause_after": 0.0,
            "settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 1.0, "speed": 1.0} # Normal
        }
    }

    # --- SETUP ---
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Locate FFmpeg
    ffmpeg_executable = None
    if MANUAL_FFMPEG_PATH: ffmpeg_executable = MANUAL_FFMPEG_PATH
    if not ffmpeg_executable: ffmpeg_executable = shutil.which("ffmpeg")
    if not ffmpeg_executable:
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            ffmpeg_executable = "ffmpeg"
        except: pass

    if not ffmpeg_executable:
         print("\nCRITICAL ERROR: Python cannot find 'ffmpeg'. Set MANUAL_FFMPEG_PATH.")
         return
    print(f"Using FFmpeg: {ffmpeg_executable}")

    # --- EXECUTION ---

    if INPUT_MODE == "excel":
        if not os.path.exists(EXCEL_PATH):
            print(f"Error: Excel file '{EXCEL_PATH}' not found.")
            print("Please create an Excel file with columns: 'id', 'section 1', 'section 2', 'section 3'")
            return

        print(f"Reading Excel: {EXCEL_PATH}...")
        try:
            df = pd.read_excel(EXCEL_PATH)
            # Normalize headers to lower case strip for easier matching
            df.columns = df.columns.str.strip().str.lower()
            
            required_cols = ['id', 'section 1', 'section 2', 'section 3']
            if not all(col in df.columns for col in required_cols):
                print(f"Error: Excel missing required columns. Found: {list(df.columns)}")
                print(f"Expected: {required_cols}")
                return

            # Iterate rows
            for index, row in df.iterrows():
                job_id = str(row['id'])
                
                # Build segment list for this row
                job_segments = []
                
                # Section 1
                job_segments.append({
                    "text": str(row['section 1']),
                    "settings": SECTION_CONFIG[1]["settings"],
                    "pause_duration": SECTION_CONFIG[1]["pause_after"]
                })
                # Section 2
                job_segments.append({
                    "text": str(row['section 2']),
                    "settings": SECTION_CONFIG[2]["settings"],
                    "pause_duration": SECTION_CONFIG[2]["pause_after"]
                })
                # Section 3
                job_segments.append({
                    "text": str(row['section 3']),
                    "settings": SECTION_CONFIG[3]["settings"],
                    "pause_duration": SECTION_CONFIG[3]["pause_after"]
                })

                # Process this row
                process_job(job_id, job_segments, OUTPUT_DIR, ffmpeg_executable, VOICE_ID)

        except Exception as e:
            print(f"Error processing Excel: {e}")

    else: # INPUT_MODE == "file"
        print("Reading from text files (section1.txt, etc)...")
        
        # Build segment list from files
        job_segments = []
        file_map = ["section1.txt", "section2.txt", "section3.txt"]
        
        for i, filename in enumerate(file_map):
            section_num = i + 1
            if os.path.exists(filename):
                with open(filename, "r", encoding="utf-8") as f:
                    content = f.read()
                
                job_segments.append({
                    "text": content,
                    "settings": SECTION_CONFIG[section_num]["settings"],
                    "pause_duration": SECTION_CONFIG[section_num]["pause_after"]
                })
            else:
                print(f"Warning: {filename} not found.")

        process_job("manual_file_input", job_segments, OUTPUT_DIR, ffmpeg_executable, VOICE_ID)

if __name__ == "__main__":
    main()