from datetime import datetime, timezone
from pathlib import Path

from pydub import AudioSegment
from tqdm import tqdm

import voice_mapping_pb2

OGG_BITRATE = "64k"
OGG_SAMPLE_RATE = 44100
TARGET_BLOCK_BYTES = 512 * 1024
TARGET_BLOCK_TOLERANCE = 1.05
INDEX_OUTPUT_FILE = Path("Exported") / "voice_mapping.pb"

def trim_audio(audio_segment, trim_seconds=0.047):
    trim_ms = int(trim_seconds * 1000)
    new_length = len(audio_segment) - (2 * trim_ms)
    if new_length <= 0:
        tqdm.write(f"WARNING: Audio too short to trim {trim_seconds}s from both ends")
        return audio_segment
    trimmed = audio_segment[trim_ms:len(audio_segment) - trim_ms]
    
    return trimmed

def convert_wav(input_path, output_path, convert_format, trim_seconds=0.047):
    try:
        tqdm.write(f"Processing: {input_path}")
        audio = AudioSegment.from_wav(input_path)
        trimmed_audio = trim_audio(audio, trim_seconds)
        export_audio(trimmed_audio, output_path, convert_format)
        tqdm.write(f"Successfully converted: {output_path}")
    except Exception as e:
        tqdm.write(f"ERROR: Error processing {input_path}: {str(e)}")


def export_audio(audio_segment, output_path, convert_format):
    if convert_format.lower() == "ogg":
        last_error = None
        try:
            resampled_audio = audio_segment.set_frame_rate(OGG_SAMPLE_RATE)
            resampled_audio.export(
                output_path,
                format=convert_format,
                codec="libvorbis",
                bitrate=OGG_BITRATE,
                parameters=["-compression_level", "10"],
            )
            return
        except Exception as e:
            last_error = e
            tqdm.write(
                f"WARNING: OGG encode failed at {OGG_SAMPLE_RATE} Hz for {output_path.name}: {str(e)}"
            )

        raise RuntimeError(f"OGG encoding failed for {output_path}: {last_error}")

    audio_segment.export(output_path, format=convert_format)


def parse_voice_name_parts(stem):
    parts = stem.split(".")
    if len(parts) < 3:
        return None
    return parts[0], parts[1], ".".join(parts[2:])


def sort_sequence_key(sequence_part):
    if sequence_part.isdigit():
        return 0, int(sequence_part), sequence_part
    return 1, sequence_part


def estimate_encoded_size_bytes(duration_seconds):
    # 64kbit/s target bitrate is approximately 8000 bytes per second.
    bytes_per_second = 8000
    return max(1, int(duration_seconds * bytes_per_second))


def build_chapter_units(chapter_clips, target_block_bytes):
    units = []

    for chapter, clips in sorted(chapter_clips.items()):
        ordered_clips = sorted(
            clips,
            key=lambda clip: (sort_sequence_key(clip["sequence"]), clip["stem"]),
        )

        current_unit = []
        current_size = 0
        unit_index = 0

        for clip in ordered_clips:
            clip_size = clip["estimated_bytes"]
            if current_unit and current_size + clip_size > target_block_bytes:
                units.append(
                    {
                        "chapter": chapter,
                        "unit_index": unit_index,
                        "estimated_bytes": current_size,
                        "clips": current_unit,
                    }
                )
                unit_index += 1
                current_unit = []
                current_size = 0

            current_unit.append(clip)
            current_size += clip_size

        if current_unit:
            units.append(
                {
                    "chapter": chapter,
                    "unit_index": unit_index,
                    "estimated_bytes": current_size,
                    "clips": current_unit,
                }
            )

    return units


def assign_units_to_blocks(units, target_block_bytes):
    blocks = []

    for unit in units:
        selected_block = None
        selected_block_remaining = None

        for block in blocks:
            projected = block["estimated_bytes"] + unit["estimated_bytes"]
            if projected > int(target_block_bytes * TARGET_BLOCK_TOLERANCE):
                continue

            # Prefer keeping split chapter units together when possible.
            chapter_in_block = unit["chapter"] in block["chapters"]
            remaining = abs(target_block_bytes - projected)

            if selected_block is None:
                selected_block = block
                selected_block_remaining = (0 if chapter_in_block else 1, remaining)
                continue

            candidate_score = (0 if chapter_in_block else 1, remaining)
            if candidate_score < selected_block_remaining:
                selected_block = block
                selected_block_remaining = candidate_score

        if selected_block is None:
            selected_block = {
                "units": [],
                "estimated_bytes": 0,
                "chapters": set(),
            }
            blocks.append(selected_block)

        selected_block["units"].append(unit)
        selected_block["estimated_bytes"] += unit["estimated_bytes"]
        selected_block["chapters"].add(unit["chapter"])

    return blocks


def write_global_voice_index(index_data, preload_blocks, output_file=INDEX_OUTPUT_FILE):
    mappings = voice_mapping_pb2.VoiceMappings()
    mappings.version = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for source_name, info in sorted(index_data.items()):
        entry = mappings.voices[source_name]
        entry.bank = info["bank"]
        entry.time = info["time"]
        entry.duration = info["duration"]

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    for chapter, banks in sorted(preload_blocks.items()):
        preload = mappings.preload_blocks[chapter]
        preload.bank.extend(sorted(banks))

    output_path.write_bytes(mappings.SerializeToString())
    tqdm.write(f"Global voice index written: {output_path}")


def process_grouped_voice(wav_files, output_path, convert_format, trim_seconds=0.047):
    chapter_clips = {}
    index_data = {}
    preload_blocks = {}
    skipped_files = 0
    error_count = 0

    for wav_file in wav_files:
        parts = parse_voice_name_parts(wav_file.stem)
        if not parts:
            tqdm.write(f"WARNING: Skipping file with invalid voice name format: {wav_file.name}")
            skipped_files += 1
            continue
        _speaker, chapter, sequence = parts

        try:
            audio = AudioSegment.from_wav(wav_file)
            trimmed_audio = trim_audio(audio, trim_seconds)
            duration_seconds = len(trimmed_audio) / 1000.0

            chapter_clips.setdefault(chapter, []).append(
                {
                    "stem": wav_file.stem,
                    "chapter": chapter,
                    "sequence": sequence,
                    "audio": trimmed_audio,
                    "duration": duration_seconds,
                    "estimated_bytes": estimate_encoded_size_bytes(duration_seconds),
                }
            )
        except Exception as e:
            tqdm.write(f"ERROR: Failed to read/trim {wav_file.name}: {str(e)}")
            error_count += 1

    chapter_units = build_chapter_units(chapter_clips, TARGET_BLOCK_BYTES)
    blocks = assign_units_to_blocks(chapter_units, TARGET_BLOCK_BYTES)

    tqdm.write(f"Prepared {len(chapter_units)} chapter units into {len(blocks)} target blocks")
    processed_groups = 0

    for block_index, block in tqdm(
        enumerate(blocks, start=1),
        desc=f"Grouping WAV to {convert_format.upper()}",
        unit="block",
    ):
        bank_file_name = f"VOICE_BLOCK_{block_index:04d}.{convert_format}"
        bank_output_path = output_path / bank_file_name
        merged_audio = AudioSegment.empty()
        current_offset_seconds = 0.0
        group_entries = {}
        chapters_in_block = set()

        try:
            for unit in sorted(block["units"], key=lambda item: (item["chapter"], item["unit_index"])):
                chapters_in_block.add(unit["chapter"])
                for clip in unit["clips"]:
                    duration_seconds = clip["duration"]
                    group_entries[clip["stem"]] = {
                    "bank": bank_file_name,
                    "time": round(current_offset_seconds, 6),
                    "duration": round(duration_seconds, 6),
                }

                    merged_audio += clip["audio"]
                    current_offset_seconds += duration_seconds

            export_audio(merged_audio, bank_output_path, convert_format)
            index_data.update(group_entries)

            for chapter in chapters_in_block:
                preload_blocks.setdefault(chapter, set()).add(bank_file_name)

            processed_groups += 1

        except Exception as e:
            tqdm.write(f"ERROR: Failed to process block {bank_file_name}: {str(e)}")
            error_count += 1

    write_global_voice_index(index_data, preload_blocks)
    tqdm.write(
        "Grouped voice processing complete. "
        f"Blocks: {processed_groups}, Chapters: {len(chapter_clips)}, "
        f"Skipped files: {skipped_files}, Errors: {error_count}"
    )

def process_directory(voice_dir="Exported/VOICE", convert_format="ogg", group=False, trim_seconds=0.047):
    voice_path = Path(voice_dir)
    output_path = Path(f"{voice_dir}_{convert_format.upper()}")
    output_path.mkdir(parents=True, exist_ok=True)
    if not voice_path.exists():
        tqdm.write(f"ERROR: Voice directory not found: {voice_path}")
        return
    wav_files = list(voice_path.glob("*.WAV")) + list(voice_path.glob("*.wav"))
    tqdm.write(f"Found {len(wav_files)} WAV files to process")

    if group:
        process_grouped_voice(wav_files, output_path, convert_format, trim_seconds)
        return

    processed_count = 0
    error_count = 0
    
    for wav_file in tqdm(wav_files, desc=f"Converting WAV to {convert_format.upper()}", unit="file"):
        try:
            output_filename = wav_file.stem + f".{convert_format}"
            output_file_path = output_path / output_filename
            convert_wav(wav_file, output_file_path, convert_format, trim_seconds)
            processed_count += 1
            
        except Exception as e:
            tqdm.write(f"ERROR: Failed to process {wav_file}: {str(e)}")
            error_count += 1
    
    tqdm.write(f"Processing complete. Successfully processed: {processed_count}, Errors: {error_count}")

def main():
    process_directory("Exported/VOICE", "ogg", True)
    process_directory("Exported/SE", "ogg")

    tqdm.write("Audio processing completed!")

if __name__ == "__main__":
    main()
