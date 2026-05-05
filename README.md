# Transcritor Local/API de Entrevistas

Este projeto transcreve áudios de entrevistas usando Python.

Ele tem dois modos:

1. **Modo local**, usando `faster-whisper`, sem enviar o áudio para a internet.
2. **Modo OpenRouter**, usando uma chave de API para transcrever via nuvem, quando você quiser mais praticidade, velocidade ou rodar sem depender do processamento do seu computador.

Para entrevistas sensíveis, o modo mais seguro continua sendo o **local**. O modo OpenRouter é opcional e envia o áudio para uma API externa.

---

## Estrutura do projeto

```txt
transcritor-entrevistas/
├── audios/
│   └── SEUS ÁUDIOS AQUI !!!!!
├── transcricoes/
├── transcrever_entrevistas.py
├── requirements.txt
├── .env
├── .gitignore
└── README.md
```

---

## O que ele faz

- Transcreve um único áudio
- Transcreve uma pasta inteira de áudios em um comando
- Busca arquivos em subpastas automaticamente
- Gera `.txt` com a transcrição limpa
- Gera `.txt` com timestamps quando usado em modo local
- Gera `.json` com metadados
- Gera um arquivo combinado com todas as entrevistas
- Remove automaticamente CPF, telefone e e-mail, se você usar `--redact`
- Permite escolher entre transcrição local e transcrição via OpenRouter

---

## Formatos aceitos

```txt
.mp3
.wav
.m4a
.ogg
.flac
.aac
.webm
.mp4
```

---

## 1. Instalação no Ubuntu

Entre na pasta do projeto:

```bash
cd transcritor-entrevistas
```

Atualize os pacotes:

```bash
sudo apt update
```

Instale o `ffmpeg`:

```bash
sudo apt install ffmpeg -y
```

Crie um ambiente virtual:

```bash
python3 -m venv .venv
```

Ative o ambiente virtual:

```bash
source .venv/bin/activate
```

Atualize o `pip`:

```bash
pip install --upgrade pip
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

---

## 2. Como colocar os áudios

Coloque seus arquivos dentro da pasta `audios/`.

Exemplo:

```txt
audios/
├── entrevista_01.mp3
├── entrevista_02.m4a
└── clientes/
    └── entrevista_03.wav
```

Por padrão, o script também procura áudios dentro de subpastas.

---

# Modo 1: transcrição local

Use este modo quando os áudios forem sensíveis.

Neste modo, o áudio fica no seu computador.

---

## Transcrever uma pasta inteira localmente

```bash
python transcrever_entrevistas.py --input ./audios --output-dir ./transcricoes --backend local --local-model small --redact --combine
```

Esse é o comando mais recomendado para começar.

Ele faz isto:

- lê todos os áudios da pasta `audios/`
- também lê áudios em subpastas
- salva os resultados em `transcricoes/`
- usa o modelo local `small`
- remove CPF, telefone e e-mail
- cria um arquivo combinado chamado `transcricoes_combinadas.md`

---

## Transcrever um único arquivo localmente

```bash
python transcrever_entrevistas.py --input ./audios/entrevista_01.mp3 --output-dir ./transcricoes --backend local --local-model small --redact
```

---

## Usar modelo local mais rápido

```bash
python transcrever_entrevistas.py --input ./audios --backend local --local-model base
```

Use `base` se quiser velocidade.

---

## Usar modelo local com mais qualidade

```bash
python transcrever_entrevistas.py --input ./audios --backend local --local-model medium
```

Use `medium` se quiser mais qualidade.

---

## Usar máxima qualidade local

```bash
python transcrever_entrevistas.py --input ./audios --backend local --local-model large-v3
```

Esse modo é mais pesado e pode demorar bastante sem GPU.

---

## Modelos locais disponíveis

```txt
tiny
base
small
medium
large-v3
```

Recomendação prática:

```txt
tiny      = muito rápido, menos preciso
base      = rápido, razoável
small     = melhor equilíbrio
medium    = boa qualidade, mais lento
large-v3  = melhor qualidade, mais pesado
```

---

# Modo 2: transcrição via OpenRouter

Use este modo quando você quiser integrar uma chave da OpenRouter e transcrever usando API.

Atenção: neste modo, o áudio é enviado para a API. Não use com entrevista sensível sem consentimento e sem avaliar os termos, o custo e a política de privacidade.

---

## 1. Criar arquivo `.env`

Copie o arquivo de exemplo:

```bash
cp .env.example .env
```

Abra o arquivo:

```bash
nano .env
```

Coloque sua chave:

```env
OPENROUTER_API_KEY=sua_chave_aqui
```

Você também pode configurar o modelo:

```env
OPENROUTER_STT_MODEL=openai/whisper-large-v3
```

Salve com:

```txt
CTRL + O
ENTER
CTRL + X
```

---

## 2. Transcrever uma pasta inteira com OpenRouter

```bash
python transcrever_entrevistas.py --input ./audios --output-dir ./transcricoes --backend openrouter --redact --combine
```

Esse comando:

- lê todos os áudios da pasta `audios/`
- envia cada áudio para o OpenRouter
- salva as transcrições em `transcricoes/`
- remove CPF, telefone e e-mail
- cria um arquivo combinado com tudo

---

## 3. Transcrever um único áudio com OpenRouter

```bash
python transcrever_entrevistas.py --input ./audios/entrevista_01.mp3 --output-dir ./transcricoes --backend openrouter --redact
```

---

## 4. Escolher modelo OpenRouter no comando

```bash
python transcrever_entrevistas.py --input ./audios --backend openrouter --openrouter-model openai/whisper-large-v3 --redact
```

Você também pode trocar o modelo no `.env`, usando:

```env
OPENROUTER_STT_MODEL=openai/whisper-large-v3
```

---

## Comandos principais

### Transcrever pasta inteira localmente

```bash
python transcrever_entrevistas.py --input ./audios --output-dir ./transcricoes --backend local --local-model small --redact --combine
```

### Transcrever pasta inteira via OpenRouter

```bash
python transcrever_entrevistas.py --input ./audios --output-dir ./transcricoes --backend openrouter --redact --combine
```

### Transcrever um arquivo localmente

```bash
python transcrever_entrevistas.py --input ./audios/entrevista_01.mp3 --backend local --local-model small --redact
```

### Transcrever um arquivo via OpenRouter

```bash
python transcrever_entrevistas.py --input ./audios/entrevista_01.mp3 --backend openrouter --redact
```

### Não buscar em subpastas

```bash
python transcrever_entrevistas.py --input ./audios --no-recursive
```

### Sobrescrever transcrições antigas

```bash
python transcrever_entrevistas.py --input ./audios --overwrite
```

### Criar arquivo combinado com todas as transcrições

```bash
python transcrever_entrevistas.py --input ./audios --combine
```

### Detectar idioma automaticamente

```bash
python transcrever_entrevistas.py --input ./audios --language auto
```

### Transcrever áudio em português

```bash
python transcrever_entrevistas.py --input ./audios --language pt
```

### Transcrever áudio em inglês

```bash
python transcrever_entrevistas.py --input ./audios --language en
```

---

## Arquivos gerados

Para cada áudio, o script gera:

```txt
entrevista_01.txt
entrevista_01_com_tempos.txt
entrevista_01.json
```

Se você usar `--combine`, também gera:

```txt
transcricoes_combinadas.md
```

---

## Diferença entre os arquivos

### `.txt`

Transcrição limpa:

```txt
A entrevista começou com a participante explicando sua rotina de trabalho.
```

### `_com_tempos.txt`

No modo local, contém timestamps:

```txt
[00:00:00 - 00:00:05] A entrevista começou com a participante explicando sua rotina.
[00:00:05 - 00:00:12] Depois, ela comentou sobre as dificuldades no atendimento.
```

No modo OpenRouter, se o modelo não retornar timestamps, o arquivo será gerado sem marcações reais de tempo.

### `.json`

Contém metadados, como:

- backend usado
- nome do arquivo
- idioma
- modelo
- duração, quando disponível
- uso/custo, quando a API retornar
- segmentos, quando disponíveis

---

## Segurança e privacidade

Para entrevistas sensíveis, prefira:

```bash
--backend local
```

O modo local não envia o áudio para APIs externas.

Use OpenRouter apenas se:

- você tiver autorização para processar o áudio em serviço externo
- o conteúdo não for extremamente sensível
- você aceitar o custo da API
- você entender que o áudio sai do seu computador
- a política de privacidade fizer sentido para o seu caso

---

## Sobre a chave da OpenRouter

Nunca coloque sua chave diretamente no código.

Use o arquivo `.env`.

Não envie `.env` para o GitHub.

Este projeto já inclui `.gitignore` para ignorar:

```txt
.env
.venv/
audios/
transcricoes/
```

---

## Exemplo de `.env`

```env
OPENROUTER_API_KEY=coloque_sua_chave_aqui
OPENROUTER_STT_MODEL=openai/whisper-large-v3

TRANSCRIPTION_BACKEND=local
TRANSCRIPTION_LANGUAGE=pt

LOCAL_WHISPER_MODEL=small
WHISPER_DEVICE=cpu
WHISPER_COMPUTE_TYPE=int8

MAX_OPENROUTER_MB=25
OPENROUTER_TIMEOUT=300

OPENROUTER_SITE_URL=
OPENROUTER_APP_NAME=Transcritor Local de Entrevistas
```

---

## Variáveis do `.env`

### `OPENROUTER_API_KEY`

Sua chave da OpenRouter.

Obrigatória apenas se você usar:

```bash
--backend openrouter
```

### `OPENROUTER_STT_MODEL`

Modelo usado na API.

Exemplo:

```env
OPENROUTER_STT_MODEL=openai/whisper-large-v3
```

### `TRANSCRIPTION_BACKEND`

Backend padrão:

```env
TRANSCRIPTION_BACKEND=local
```

ou:

```env
TRANSCRIPTION_BACKEND=openrouter
```

Mesmo assim, você pode sobrescrever no comando com `--backend`.

### `TRANSCRIPTION_LANGUAGE`

Idioma padrão:

```env
TRANSCRIPTION_LANGUAGE=pt
```

Use `auto` para detecção automática.

### `MAX_OPENROUTER_MB`

Limite de tamanho por arquivo enviado ao OpenRouter.

```env
MAX_OPENROUTER_MB=25
```

Se o áudio for maior, divida ou comprima antes.

---

## Como saber se está funcionando

Rode:

```bash
python transcrever_entrevistas.py --input ./audios --backend local --local-model base
```

Se tudo estiver certo, você verá algo parecido com:

```txt
========================================================================
Transcritor de Entrevistas
========================================================================
Backend: local
Arquivos encontrados: 2
Entrada: /caminho/transcritor-entrevistas/audios
Saída: /caminho/transcritor-entrevistas/transcricoes
Idioma: pt
Redact: não
Modelo local: base
```

Ao final, veja os arquivos:

```bash
ls transcricoes
```

---

## Erros comuns

### `ffmpeg not found`

Instale:

```bash
sudo apt install ffmpeg -y
```

---

### `ModuleNotFoundError: No module named 'faster_whisper'`

Ative o ambiente e instale as dependências:

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

---

### `OPENROUTER_API_KEY não encontrada`

Crie o `.env`:

```bash
cp .env.example .env
nano .env
```

E preencha:

```env
OPENROUTER_API_KEY=sua_chave_aqui
```

---

### Arquivo muito grande no OpenRouter

O script bloqueia arquivos acima do limite configurado em `MAX_OPENROUTER_MB`.

Soluções:

- comprimir o áudio
- dividir o áudio em partes
- usar o modo local
- aumentar `MAX_OPENROUTER_MB` somente se o modelo/endpoint que você usa aceitar

---

### O script diz que os arquivos já existem

Use:

```bash
--overwrite
```

Exemplo:

```bash
python transcrever_entrevistas.py --input ./audios --overwrite
```

---

## Dicas para entrevistas

Para ter melhor transcrição:

- grave em lugar silencioso
- deixe o microfone perto da pessoa
- evite duas pessoas falando ao mesmo tempo
- teste o áudio antes
- prefira `.wav`, `.m4a` ou `.mp3` em boa qualidade
- evite áudio muito comprimido de WhatsApp, se possível

---

## Comando recomendado para entrevistas sensíveis

```bash
python transcrever_entrevistas.py --input ./audios --output-dir ./transcricoes --backend local --local-model small --redact --combine
```

---

## Comando recomendado para velocidade/praticidade com API

```bash
python transcrever_entrevistas.py --input ./audios --output-dir ./transcricoes --backend openrouter --redact --combine
```

---

## Observações importantes

O script ajuda, mas não substitui revisão humana.

Modelos de transcrição podem errar:

- nomes próprios
- termos técnicos
- falas rápidas
- áudio baixo
- ruído
- pessoas falando juntas
- sotaques
- siglas

Sempre revise antes de usar a transcrição como fonte oficial.
