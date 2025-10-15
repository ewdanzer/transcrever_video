#!/usr/bin/env python3
"""
Transcreve um vídeo e gera duas VTTs:
 - <prefix>.original.vtt  -> texto na língua original por segmento (com tag de idioma)
 - <prefix>.en.vtt        -> tradução para inglês por segmento

Também pode salvar <prefix>.json com os segments (start,end,lang,text,translation).

Uso:
  python3 transcribe_and_translate_dual_vtt.py video.mp4 out_prefix --model small --refine-per-segment --no-translate

Opções relevantes:
  --model                Whisper model (tiny, base, small, medium, large)
  --refine-per-segment   Re-transcreve segmentos forçando idioma detectado (melhora acurácia para áudio misto)
  --no-translate         NÃO gera o arquivo de tradução em inglês (por padrão gera)
  --keep-audio           mantém o arquivo de áudio extraído no diretório atual
  --verbose
"""

import argparse
import os
import subprocess
import tempfile
import json
from math import floor
from tqdm import tqdm

import whisper
from langdetect import detect, DetectorFactory, LangDetectException

# Determinismo para langdetect
DetectorFactory.seed = 0

def extract_audio(video_path, out_audio_path):
    """Extrai áudio em WAV mono 16k usando ffmpeg"""
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000",
        out_audio_path
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def extract_audio_segment(input_audio, out_segment, start, end):
    """Corta intervalo do áudio (start, end em segundos) para um arquivo WAV"""
    cmd = [
        "ffmpeg", "-y", "-i", input_audio,
        "-ss", str(start), "-to", str(end),
        "-acodec", "pcm_s16le", "-ac", "1", "-ar", "16000",
        out_segment
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def seconds_to_vtt_timestamp(seconds):
    """Converte segundos float para HH:MM:SS.mmm (VTT)"""
    ms = int(round((seconds - floor(seconds)) * 1000))
    total_seconds = int(floor(seconds))
    s = total_seconds % 60
    m = (total_seconds // 60) % 60
    h = (total_seconds // 3600)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"

def detect_lang_of_text(text):
    """Tenta detectar pt/es; fallback '' se incerto"""
    try:
        lang = detect(text)
    except LangDetectException:
        return ""
    if lang.startswith("pt"):
        return "pt"
    if lang.startswith("es"):
        return "es"
    return lang  # pode retornar 'en' etc.

def write_vtt_original(segments, path):
    """Gera VTT com o texto original (marcando idioma entre colchetes)"""
    with open(path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for i, s in enumerate(segments, start=1):
            f.write(f"{i}\n")
            f.write(f"{seconds_to_vtt_timestamp(s['start'])} --> {seconds_to_vtt_timestamp(s['end'])}\n")
            lang_tag = s.get("lang","")
            text = s.get("text","").strip()
            if lang_tag:
                f.write(f"[{lang_tag}] {text}\n\n")
            else:
                f.write(f"{text}\n\n")

def write_vtt_translation(segments, path):
    """Gera VTT com a tradução para inglês (cada cue contém apenas o texto em inglês quando disponível).
       Se não houver tradução, usa texto original como fallback.
    """
    with open(path, "w", encoding="utf-8") as f:
        f.write("WEBVTT\n\n")
        for i, s in enumerate(segments, start=1):
            f.write(f"{i}\n")
            f.write(f"{seconds_to_vtt_timestamp(s['start'])} --> {seconds_to_vtt_timestamp(s['end'])}\n")
            trans = s.get("translation")
            if trans and trans.strip():
                f.write(f"{trans.strip()}\n\n")
            else:
                # fallback: original text if no translation
                f.write(f"{s.get('text','').strip()}\n\n")

def seconds_to_srt_timestamp(seconds):
    """Converte segundos float para HH:MM:SS,mmm (SRT)"""
    ms = int(round((seconds - floor(seconds)) * 1000))
    total_seconds = int(floor(seconds))
    s = total_seconds % 60
    m = (total_seconds // 60) % 60
    h = (total_seconds // 3600)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def write_srt_original(segments, path):
    """Gera SRT com o texto original (marcando idioma entre colchetes)"""
    with open(path, "w", encoding="utf-8") as f:
        for i, s in enumerate(segments, start=1):
            f.write(f"{i}\n")
            f.write(f"{seconds_to_srt_timestamp(s['start'])} --> {seconds_to_srt_timestamp(s['end'])}\n")
            lang_tag = s.get("lang","")
            text = s.get("text","").strip()
            if lang_tag:
                f.write(f"[{lang_tag}] {text}\n\n")
            else:
                f.write(f"{text}\n\n")

def write_srt_translation(segments, path):
    """Gera SRT com a tradução para inglês.
       Se não houver tradução, usa texto original como fallback.
    """
    with open(path, "w", encoding="utf-8") as f:
        for i, s in enumerate(segments, start=1):
            f.write(f"{i}\n")
            f.write(f"{seconds_to_srt_timestamp(s['start'])} --> {seconds_to_srt_timestamp(s['end'])}\n")
            trans = s.get("translation")
            if trans and trans.strip():
                f.write(f"{trans.strip()}\n\n")
            else:
                # fallback: original text if no translation
                f.write(f"{s.get('text','').strip()}\n\n")

def transcribe_full_audio(model, audio_path, verbose=False):
    """Transcreve o áudio completo com whisper (detecção automática de idioma e segments)."""
    if verbose:
        print("Transcrevendo áudio completo (detecção automática de idioma)...")
    res = model.transcribe(audio_path)  # autodetect language
    segments = res.get("segments", [])
    overall_lang = res.get("language")
    return segments, overall_lang

def transcribe_segment_audio(model, seg_audio_path, language=None, task=None, verbose=False):
    """
    Transcreve/Tradução de um segmento de áudio:
     - language: 'pt' ou 'es' para forçar, ou None
     - task: None -> transcribe, "translate" -> translate to english
    """
    options = {}
    if language:
        options["language"] = language
    if task:
        options["task"] = task
    if verbose:
        print(f"-> whisper.transcribe(segment, language={language}, task={task})")
    res = model.transcribe(seg_audio_path, **options)
    # Quando task="translate", a resposta tem segmentos com text em inglês.
    text = ""
    segs = res.get("segments", [])
    if segs:
        text = " ".join([s.get("text","").strip() for s in segs]).strip()
    else:
        # fallback: use top-level 'text' if present
        text = res.get("text","").strip()
    return text

def main():
    parser = argparse.ArgumentParser(description="Transcribe video and produce original and English VTTs.")
    parser.add_argument("video", help="Input video file (mp4, mkv, etc.)")
    parser.add_argument("out_prefix", help="Output prefix (will produce <prefix>.original.vtt and <prefix>.en.vtt)")
    parser.add_argument("--model", default="small", help="Whisper model (tiny, base, small, medium, large)")
    parser.add_argument("--refine-per-segment", action="store_true",
                        help="Re-transcribe each segment forcing detected language (improves mixed-language accuracy).")
    parser.add_argument("--no-translate", action="store_true", help="Do not produce the English VTT (default: produce it).")
    parser.add_argument("--keep-audio", action="store_true", help="Keep extracted audio file in current dir.")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    if not os.path.isfile(args.video):
        print("Arquivo de vídeo não encontrado:", args.video)
        return

    if args.verbose:
        print("Carregando modelo whisper:", args.model)
    model = whisper.load_model(args.model)

    with tempfile.TemporaryDirectory() as td:
        audio_file = os.path.join(td, "extracted_audio.wav")
        if args.verbose:
            print("Extraindo áudio para:", audio_file)
        extract_audio(args.video, audio_file)

        # transcrição inicial (gera segments)
        base_segments, overall_lang = transcribe_full_audio(model, audio_file, verbose=args.verbose)
        if args.verbose:
            print(f"Segments iniciais: {len(base_segments)} — idioma global detectado: {overall_lang}")

        processed = []
        for idx, seg in enumerate(tqdm(base_segments, desc="Processando segmentos")):
            start = seg.get("start", 0.0)
            end = seg.get("end", start + 0.5)
            text = seg.get("text","").strip()

            # detect language from text (pt/es preferred)
            detected = detect_lang_of_text(text) if text else ""
            chosen_lang = detected if detected else (overall_lang if overall_lang else "")

            # optional refinement: re-transcribe the segment forcing the detected language
            if args.refine_per_segment and chosen_lang in ("pt","es"):
                if args.verbose:
                    print(f"Refinando segmento {idx+1} ({start:.2f}-{end:.2f}) forçando idioma {chosen_lang}")
                seg_audio = os.path.join(td, f"segment_{idx+1}.wav")
                try:
                    extract_audio_segment(audio_file, seg_audio, start, end)
                    new_text = transcribe_segment_audio(model, seg_audio, language=chosen_lang, task=None, verbose=args.verbose)
                    if new_text:
                        text = new_text
                except subprocess.CalledProcessError:
                    if args.verbose:
                        print("Falha ao extrair segmento para refinamento; mantendo texto original.")
                finally:
                    if os.path.exists(seg_audio):
                        try:
                            os.remove(seg_audio)
                        except:
                            pass

            seg_dict = {
                "start": start,
                "end": end,
                "lang": chosen_lang,
                "text": text,
                "translation": None
            }

            # translation: generate english text for the same time region (using whisper task='translate')
            if not args.no_translate:
                if args.verbose:
                    print(f"Traduzindo segmento {idx+1} para inglês...")
                seg_audio_t = os.path.join(td, f"segment_{idx+1}_t.wav")
                try:
                    extract_audio_segment(audio_file, seg_audio_t, start, end)
                    # Use whisper task="translate" to get english text
                    trans_text = transcribe_segment_audio(model, seg_audio_t, language=None, task="translate", verbose=args.verbose)
                    if trans_text:
                        seg_dict["translation"] = trans_text
                except subprocess.CalledProcessError:
                    if args.verbose:
                        print("Falha ao extrair áudio para tradução; pulando tradução deste segmento.")
                finally:
                    if os.path.exists(seg_audio_t):
                        try:
                            os.remove(seg_audio_t)
                        except:
                            pass

            processed.append(seg_dict)

        # outputs VTT
        original_vtt = f"{args.out_prefix}.original.vtt"
        write_vtt_original(processed, original_vtt)
        if args.verbose:
            print("Arquivo de legendas VTT original salvo em:", original_vtt)

        if not args.no_translate:
            en_vtt = f"{args.out_prefix}.en.vtt"
            write_vtt_translation(processed, en_vtt)
            if args.verbose:
                print("Arquivo de legendas VTT (inglês) salvo em:", en_vtt)

        # outputs SRT
        original_srt = f"{args.out_prefix}.original.srt"
        write_srt_original(processed, original_srt)
        if args.verbose:
            print("Arquivo de legendas SRT original salvo em:", original_srt)

        if not args.no_translate:
            en_srt = f"{args.out_prefix}.en.srt"
            write_srt_translation(processed, en_srt)
            if args.verbose:
                print("Arquivo de legendas SRT (inglês) salvo em:", en_srt)

        # json export
        json_out = f"{args.out_prefix}.json"
        with open(json_out, "w", encoding="utf-8") as jf:
            json.dump(processed, jf, ensure_ascii=False, indent=2)
        if args.verbose:
            print("JSON com segmentos salvo em:", json_out)

        # keep audio optionally
        if args.keep_audio:
            kept = os.path.abspath(f"{args.out_prefix}.extracted_audio.wav")
            subprocess.run(["cp", audio_file, kept])
            if args.verbose:
                print("Áudio extraído salvo em:", kept)

    if args.verbose:
        print("Processamento concluído.")

if __name__ == "__main__":
    main()
