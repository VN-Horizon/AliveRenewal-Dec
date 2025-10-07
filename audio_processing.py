import os
import sys
from pathlib import Path
from pydub import AudioSegment
from tqdm import tqdm

def trim_audio(audio_segment, trim_seconds=0.047):
    trim_ms = int(trim_seconds * 1000)
    new_length = len(audio_segment) - (2 * trim_ms)
    if new_length <= 0:
        tqdm.write(f"WARNING: Audio too short to trim {trim_seconds}s from both ends")
        return audio_segment
    trimmed = audio_segment[trim_ms:len(audio_segment) - trim_ms]
    
    return trimmed

def convert_wav_to_ogg(input_path, output_path, trim_seconds=0.047):
    try:
        tqdm.write(f"Processing: {input_path}")
        audio = AudioSegment.from_wav(input_path)
        trimmed_audio = trim_audio(audio, trim_seconds)
        trimmed_audio.export(output_path, format="ogg")
        tqdm.write(f"Successfully converted: {output_path}")
    except Exception as e:
        tqdm.write(f"ERROR: Error processing {input_path}: {str(e)}")

def process_voice_directory(voice_dir="Exported/VOICE", output_dir="Exported/VOICE_OGG", trim_seconds=0.047):
    voice_path = Path(voice_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    if not voice_path.exists():
        tqdm.write(f"ERROR: Voice directory not found: {voice_path}")
        return
    wav_files = list(voice_path.glob("*.WAV")) + list(voice_path.glob("*.wav"))
    tqdm.write(f"Found {len(wav_files)} WAV files to process")
    processed_count = 0
    error_count = 0
    
    for wav_file in tqdm(wav_files, desc="Converting WAV to OGG", unit="file"):
        try:
            output_filename = wav_file.stem + ".ogg"
            output_file_path = output_path / output_filename
            convert_wav_to_ogg(wav_file, output_file_path, trim_seconds)
            processed_count += 1
            
        except Exception as e:
            tqdm.write(f"ERROR: Failed to process {wav_file}: {str(e)}")
            error_count += 1
    
    tqdm.write(f"Processing complete. Successfully processed: {processed_count}, Errors: {error_count}")

def main():
    if not os.path.exists("Exported/VOICE"):
        tqdm.write("ERROR: Exported/VOICE directory not found!")
        sys.exit(1)
    
    process_voice_directory()
    
    tqdm.write("Audio processing completed!")

if __name__ == "__main__":
    main()
