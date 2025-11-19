import os
import sys
import uuid
import shutil
import subprocess
from datetime import datetime
from typing import List, Dict, Any
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

def generate_segment_audio(text: str, settings: Dict[str, float], output_dir: str, voice_id: str = "ohItIVrXTBI80RrUECOD") -> str:
    """
    Generates audio for a single segment using ElevenLabs.
    """
    print(f"  > Generating speech for: '{text[:20]}...'")
    try:
        response = elevenlabs.text_to_speech.convert(
            voice_id=voice_id,
            output_format="mp3_44100_128",
            text=text,
            model_id="eleven_turbo_v2_5",
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
        print(f"Error generating segment: {e}")
        return None

def generate_silence(duration: float, output_dir: str, ffmpeg_path: str) -> str:
    """
    Generates a silent MP3 file of the specified duration using FFmpeg.
    """
    print(f"  > Generating {duration}s silence...")
    filename = os.path.join(output_dir, f"silence_{uuid.uuid4()}.mp3")
    
    # Generate silence matching standard MP3 specs (44.1kHz, mono or stereo)
    # We re-encode later, so exact layout matters less, but we aim for standard.
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
        print(f"Error generating silence: {e}")
        return None

def main():
    # --- CONFIGURATION ---
    OUTPUT_DIR = "output"
    
    # IMPORTANT: If Python can't find ffmpeg, paste the full path here.
    # Example: r"C:\ffmpeg\bin\ffmpeg.exe"
    MANUAL_FFMPEG_PATH = r"C:\ffmpeg-8.0-essentials_build\bin\ffmpeg.exe" 
    
    # Ensure output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # --- 1. LOCATE FFMPEG (Early Detection) ---
    ffmpeg_executable = None
    
    if MANUAL_FFMPEG_PATH:
        ffmpeg_executable = MANUAL_FFMPEG_PATH
    
    if not ffmpeg_executable:
        ffmpeg_executable = shutil.which("ffmpeg")

    # Blind execution check
    if not ffmpeg_executable:
        try:
            subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            ffmpeg_executable = "ffmpeg"
        except:
            pass

    if not ffmpeg_executable:
         print("\nCRITICAL ERROR: Python cannot find 'ffmpeg'.")
         print("Please set MANUAL_FFMPEG_PATH in the script or check your installation.")
         return
    
    print(f"Using FFmpeg: {ffmpeg_executable}")

    # --- 2. DEFINE SECTIONS ---
    script_segments = [
        {
            "file_path": "section1.txt",
            "pause_duration": 1.5,  # Pause in seconds AFTER this clip
            "settings": {
                "stability": 0.9,       
                "similarity_boost": 0.8,
                "style": 0.0,
                "speed": 1.05            
            }
        },
        {
            "file_path": "section2.txt",
            "pause_duration": 0.8,  # Short pause
            "settings": {
                "stability": 0.3,       
                "similarity_boost": 1.0,
                "style": 0.5,           
                "speed": 0.75            
            }
        },
        {
            "file_path": "section3.txt",
            "pause_duration": 0.0,  # No pause after last clip
            "settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "speed": 1.0            
            }
        }
    ]

    generated_files = []
    
    # --- 3. PROCESS LOOP ---
    print(f"--- Starting Generation (Output Folder: {OUTPUT_DIR}) ---")
    
    for i, segment in enumerate(script_segments):
        file_path = segment["file_path"]
        pause_time = segment.get("pause_duration", 0.0)
        
        # A. Read text
        if not os.path.exists(file_path):
            print(f"Error: File '{file_path}' not found. Skipping.")
            continue
            
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                text_content = f.read()
        except Exception as e:
            print(f"Error reading '{file_path}': {e}")
            continue

        # B. Generate Speech
        audio_file = generate_segment_audio(
            text=text_content, 
            settings=segment["settings"],
            output_dir=OUTPUT_DIR
        )
        
        if audio_file:
            generated_files.append(audio_file)

        # C. Generate Silence (if requested)
        if pause_time > 0:
            silence_file = generate_silence(pause_time, OUTPUT_DIR, ffmpeg_executable)
            if silence_file:
                generated_files.append(silence_file)

    # --- 4. STITCH FILES ---
    if generated_files:
        print("\n--- Stitching Audio Files ---")
        
        concat_list_path = os.path.join(OUTPUT_DIR, "concat_list.txt")
        
        # GENERATE UNIQUE FILENAME
        # Uses timestamp: combined_output_YYYYMMDD_HHMMSS.mp3
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_output_path = os.path.join(OUTPUT_DIR, f"combined_output_{timestamp}.mp3")

        try:
            # Write list file
            with open(concat_list_path, "w", encoding="utf-8") as f:
                for path in generated_files:
                    # Windows path safety
                    abs_path = os.path.abspath(path).replace("\\", "/")
                    f.write(f"file '{abs_path}'\n")
            
            # FFmpeg command
            cmd = [
                ffmpeg_executable, "-y", "-f", "concat", "-safe", "0", 
                "-i", concat_list_path, 
                final_output_path
            ]
            
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            print(f"Success! Final audio saved to: {final_output_path}")

        except Exception as e:
            print(f"\nError during stitching: {e}")

        # Cleanup
        print("--- Cleaning up temporary files ---")
        for file_path in generated_files:
            try: os.remove(file_path)
            except: pass
        if os.path.exists(concat_list_path):
            try: os.remove(concat_list_path)
            except: pass
        print("Done.")
    else:
        print("No audio was generated.")

if __name__ == "__main__":
    main()