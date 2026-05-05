from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv

try:
    from faster_whisper import WhisperModel
except ImportError:
    WhisperModel = None


AUDIO_EXTENSIONS = {
    ".mp3",
    ".wav",
    ".m4a",
    ".ogg",
    ".flac",
    ".aac",
    ".webm",
    ".mp4",
}


@dataclass
class TranscriptionResult:
    text: str
    segments: list[dict[str, Any]]
    metadata: dict[str, Any]


def format_time(seconds: float) -> str:
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def redact_sensitive_data(text: str) -> str:
    """
    Remoção básica de dados sensíveis.

    Atenção!!! ISSO PODE NÃO SER CEM POR CENTO EFICAZ
    Remove apenas padrões simples de e-mail, telefone e CPF.
    
    IMPORTANTE SEMPRE FAZER REVISÃO
    
    """

    # Pra email
    text = re.sub(r"\b[\w\.-]+@[\w\.-]+\.\w+\b", "[EMAIL_REMOVIDO]", text)

	#pra telefones comuns no BR
    text = re.sub(
        r"(?:\+55\s?)?(?:\(?\d{2}\)?\s?)?\d{4,5}-?\d{4}",
        "[TELEFONE_REMOVIDO]",
        text,
    )

    # CPF
    text = re.sub(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b", "[CPF_REMOVIDO]", text)

    return text


def get_audio_files(input_path: Path, recursive: bool = True) -> list[Path]:
    if input_path.is_file():
        if input_path.suffix.lower() in AUDIO_EXTENSIONS:
            return [input_path]
        raise ValueError(f"Arquivo não suportado: {input_path}")

    if input_path.is_dir():
        iterator = input_path.rglob("*") if recursive else input_path.glob("*")
        files = [
            file
            for file in iterator
            if file.is_file() and file.suffix.lower() in AUDIO_EXTENSIONS
        ]
        return sorted(files)

    raise FileNotFoundError(f"Caminho não encontrado: {input_path}")


def ensure_output_dir(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)


def build_output_paths(audio_path: Path, output_dir: Path) -> dict[str, Path]:
    safe_name = audio_path.stem
    return {
        "txt": output_dir / f"{safe_name}.txt",
        "timestamped": output_dir / f"{safe_name}_com_tempos.txt",
        "json": output_dir / f"{safe_name}.json",
    }


def save_transcription(
    result: TranscriptionResult,
    audio_path: Path,
    output_dir: Path,
    overwrite: bool = False,
) -> dict[str, Path]:
    ensure_output_dir(output_dir)

    paths = build_output_paths(audio_path, output_dir)

    if not overwrite:
        existing = [path for path in paths.values() if path.exists()]
        if existing:
            raise FileExistsError(
                "Arquivos de saída já existem. Use --overwrite para sobrescrever: "
                + ", ".join(str(path) for path in existing)
            )

    paths["txt"].write_text(result.text.strip() + "\n", encoding="utf-8")

    if result.segments:
        timestamped_content = "\n".join(
            f"[{item['start_formatted']} - {item['end_formatted']}] {item['text']}"
            for item in result.segments
        )
    else:
        timestamped_content = (
            "Este backend não retornou timestamps por trecho.\n\n"
            + result.text.strip()
            + "\n"
        )

    paths["timestamped"].write_text(timestamped_content, encoding="utf-8")

    paths["json"].write_text(
        json.dumps(result.metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return paths


def transcribe_local(
    local_model: Any,
    audio_path: Path,
    language: str | None,
    redact: bool,
) -> TranscriptionResult:
    segments_generator, info = local_model.transcribe(
        str(audio_path),
        language=language,
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )

    segments_data: list[dict[str, Any]] = []
    full_text_parts: list[str] = []

    for segment in segments_generator:
        text = segment.text.strip()

        if redact:
            text = redact_sensitive_data(text)

        item = {
            "start": segment.start,
            "end": segment.end,
            "start_formatted": format_time(segment.start),
            "end_formatted": format_time(segment.end),
            "text": text,
        }

        segments_data.append(item)
        full_text_parts.append(text)

    full_text = "\n".join(full_text_parts).strip()

    metadata = {
        "backend": "local",
        "audio_file": str(audio_path),
        "created_at": datetime.now().isoformat(),
        "language_requested": language or "auto",
        "detected_language": getattr(info, "language", None),
        "language_probability": getattr(info, "language_probability", None),
        "duration_seconds": getattr(info, "duration", None),
        "redacted": redact,
        "segments": segments_data,
    }

    return TranscriptionResult(
        text=full_text,
        segments=segments_data,
        metadata=metadata,
    )


def transcribe_openrouter(
    audio_path: Path,
    api_key: str,
    model: str,
    language: str | None,
    redact: bool,
    timeout: int,
    max_openrouter_mb: float,
) -> TranscriptionResult:
    file_size_mb = audio_path.stat().st_size / (1024 * 1024)

    if file_size_mb > max_openrouter_mb:
        raise ValueError(
            f"O arquivo tem {file_size_mb:.2f} MB, acima do limite configurado "
            f"de {max_openrouter_mb:.2f} MB. Comprima ou divida o áudio antes de usar a API."
        )

    audio_format = audio_path.suffix.lower().replace(".", "")

    audio_b64 = base64.b64encode(audio_path.read_bytes()).decode("utf-8")

    payload: dict[str, Any] = {
        "input_audio": {
            "data": audio_b64,
            "format": audio_format,
        },
        "model": model,
    }

    if language:
        payload["language"] = language

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    site_url = os.getenv("OPENROUTER_SITE_URL")
    app_name = os.getenv("OPENROUTER_APP_NAME")

    if site_url:
        headers["HTTP-Referer"] = site_url

    if app_name:
        headers["X-OpenRouter-Title"] = app_name

    response = requests.post(
        "https://openrouter.ai/api/v1/audio/transcriptions",
        headers=headers,
        json=payload,
        timeout=timeout,
    )

    if response.status_code >= 400:
        raise RuntimeError(
            f"Erro OpenRouter {response.status_code}: {response.text[:1000]}"
        )

    data = response.json()
    text = data.get("text", "").strip()

    if redact:
        text = redact_sensitive_data(text)

    metadata = {
        "backend": "openrouter",
        "audio_file": str(audio_path),
        "created_at": datetime.now().isoformat(),
        "language_requested": language or "auto",
        "model": model,
        "file_size_mb": round(file_size_mb, 4),
        "redacted": redact,
        "usage": data.get("usage"),
        "raw_response_without_text": {
            key: value for key, value in data.items() if key != "text"
        },
        "segments": [],
    }

    return TranscriptionResult(
        text=text,
        segments=[],
        metadata=metadata,
    )


def append_combined_file(
    combined_path: Path,
    audio_path: Path,
    result: TranscriptionResult,
) -> None:
    with combined_path.open("a", encoding="utf-8") as file:
        file.write(f"\n\n# {audio_path.name}\n\n")
        file.write(result.text.strip())
        file.write("\n")


def parse_language(language: str) -> str | None:
    if language.lower() in {"auto", "none", "detectar", "detect"}:
        return None
    return language


def main() -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Transcreve áudios de entrevistas localmente ou via OpenRouter."
    )

    parser.add_argument(
        "--input",
        required=True,
        help="Caminho para um arquivo de áudio ou uma pasta com áudios.",
    )

    parser.add_argument(
        "--output-dir",
        default="transcricoes",
        help="Pasta onde as transcrições serão salvas.",
    )

    parser.add_argument(
        "--backend",
        choices=["local", "openrouter"],
        default=os.getenv("TRANSCRIPTION_BACKEND", "local"),
        help="Backend de transcrição: local ou openrouter.",
    )

    parser.add_argument(
        "--local-model",
        default=os.getenv("LOCAL_WHISPER_MODEL", "small"),
        help="Modelo local do faster-whisper: tiny, base, small, medium, large-v3.",
    )

    parser.add_argument(
        "--openrouter-model",
        default=os.getenv("OPENROUTER_STT_MODEL", "openai/whisper-large-v3"),
        help="Modelo STT do OpenRouter. Ex: openai/whisper-large-v3.",
    )

    parser.add_argument(
        "--language",
        default=os.getenv("TRANSCRIPTION_LANGUAGE", "pt"),
        help="Idioma do áudio. Use pt, en, es etc. Use auto para detectar automaticamente.",
    )

    parser.add_argument(
        "--device",
        default=os.getenv("WHISPER_DEVICE", "cpu"),
        choices=["cpu", "cuda"],
        help="Dispositivo do faster-whisper: cpu ou cuda.",
    )

    parser.add_argument(
        "--compute-type",
        default=os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
        help="Tipo de computação do faster-whisper. Para CPU use int8. Para GPU use float16.",
    )

    parser.add_argument(
        "--redact",
        action="store_true",
        help="Remove automaticamente CPF, telefone e e-mail da transcrição.",
    )

    parser.add_argument(
        "--combine",
        action="store_true",
        help="Cria um arquivo combinado com todas as transcrições da pasta.",
    )

    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Não buscar áudios em subpastas.",
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Sobrescreve arquivos já existentes na pasta de saída.",
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.getenv("OPENROUTER_TIMEOUT", "300")),
        help="Timeout em segundos para chamadas OpenRouter.",
    )

    parser.add_argument(
        "--max-openrouter-mb",
        type=float,
        default=float(os.getenv("MAX_OPENROUTER_MB", "25")),
        help="Tamanho máximo do áudio em MB para envio ao OpenRouter.",
    )

    args = parser.parse_args()

    input_path = Path(args.input).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    language = parse_language(args.language)

    try:
        audio_files = get_audio_files(
            input_path=input_path,
            recursive=not args.no_recursive,
        )
    except Exception as error:
        print(f"Erro ao procurar arquivos: {error}", file=sys.stderr)
        return 1

    if not audio_files:
        print("Nenhum arquivo de áudio encontrado.")
        return 0

    print("=" * 72)
    print("Transcritor de Entrevistas")
    print("=" * 72)
    print(f"Backend: {args.backend}")
    print(f"Arquivos encontrados: {len(audio_files)}")
    print(f"Entrada: {input_path}")
    print(f"Saída: {output_dir}")
    print(f"Idioma: {language or 'auto'}")
    print(f"Redact: {'sim' if args.redact else 'não'}")

    local_model = None

    if args.backend == "local":
        if WhisperModel is None:
            print(
                "Erro: faster-whisper não está instalado. Rode: pip install faster-whisper",
                file=sys.stderr,
            )
            return 1

        print(f"Modelo local: {args.local_model}")
        print(f"Device: {args.device}")
        print(f"Compute type: {args.compute_type}")

        local_model = WhisperModel(
            args.local_model,
            device=args.device,
            compute_type=args.compute_type,
        )

    if args.backend == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")

        if not api_key:
            print(
                "Erro: OPENROUTER_API_KEY não encontrada. Crie um arquivo .env "
                "ou exporte a variável no terminal.",
                file=sys.stderr,
            )
            return 1

        print(f"Modelo OpenRouter: {args.openrouter_model}")
        print(f"Limite por arquivo: {args.max_openrouter_mb} MB")
    else:
        api_key = ""

    ensure_output_dir(output_dir)

    combined_path = output_dir / "transcricoes_combinadas.md"

    if args.combine:
        if combined_path.exists() and not args.overwrite:
            print(
                f"Erro: {combined_path} já existe. Use --overwrite para sobrescrever.",
                file=sys.stderr,
            )
            return 1

        combined_path.write_text(
            f"# Transcrições combinadas\n\nGerado em: {datetime.now().isoformat()}\n",
            encoding="utf-8",
        )

    success_count = 0
    error_count = 0

    for index, audio_file in enumerate(audio_files, start=1):
        print("\n" + "-" * 72)
        print(f"[{index}/{len(audio_files)}] Transcrevendo: {audio_file.name}")

        try:
            if args.backend == "local":
                result = transcribe_local(
                    local_model=local_model,
                    audio_path=audio_file,
                    language=language,
                    redact=args.redact,
                )
            else:
                result = transcribe_openrouter(
                    audio_path=audio_file,
                    api_key=api_key,
                    model=args.openrouter_model,
                    language=language,
                    redact=args.redact,
                    timeout=args.timeout,
                    max_openrouter_mb=args.max_openrouter_mb,
                )

            paths = save_transcription(
                result=result,
                audio_path=audio_file,
                output_dir=output_dir,
                overwrite=args.overwrite,
            )

            if args.combine:
                append_combined_file(
                    combined_path=combined_path,
                    audio_path=audio_file,
                    result=result,
                )

            print("Arquivos salvos:")
            print(f"  TXT: {paths['txt']}")
            print(f"  TXT com tempos: {paths['timestamped']}")
            print(f"  JSON: {paths['json']}")

            success_count += 1

        except Exception as error:
            error_count += 1
            print(f"Erro ao transcrever {audio_file.name}: {error}", file=sys.stderr)

    print("\n" + "=" * 72)
    print("Finalizado")
    print("=" * 72)
    print(f"Sucesso: {success_count}")
    print(f"Erros: {error_count}")

    if args.combine:
        print(f"Arquivo combinado: {combined_path}")

    return 0 if error_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
