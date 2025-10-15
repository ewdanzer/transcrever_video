# Ferramenta de Transcrição e Tradução de Vídeos

Esta ferramenta ajuda você a criar legendas automaticamente para seus vídeos e pode até traduzi-las para inglês! Ela gera dois arquivos de legendas:
- Um com o idioma original (detectado automaticamente)
- Um com a tradução para inglês

## Requisitos de Hardware

Eu particularmente usei com uma NVIDIA RTX 4060 Ti (8GB VRAM) e funciona bem com os modelos até 'medium'. 
- Para GPUs com 8GB VRAM ou menos: recomendo usar modelos 'tiny', 'base', 'small' ou 'medium'
- Para GPUs com mais de 8GB VRAM: você pode usar o modelo 'large' para maior precisão
- Quanto maior a VRAM disponível, mais rápido será o processamento

## Requisitos de Software

Antes de começar, certifique-se de ter:

1. Python 3 instalado no seu computador
2. FFmpeg instalado (para processamento de áudio)
3. Os seguintes pacotes Python:
   ```bash
   pip install whisper tqdm langdetect
   ```

## Instalação

1. Baixe o script `transcribe_and_translate_dual_vtt.py` para seu computador
2. Torne-o executável (no Linux/Mac):
   ```bash
   chmod +x transcribe_and_translate_dual_vtt.py
   ```

## Como Usar

### Uso Básico

A forma mais simples de usar a ferramenta é:

```bash
python3 transcribe_and_translate_dual_vtt.py seu_video.mp4 nome_saida
```

Por exemplo, se seu vídeo se chama `aula.mp4` e você quer que os arquivos de saída comecem com "minhas_legendas", você executaria:

```bash
python3 transcribe_and_translate_dual_vtt.py aula.mp4 minhas_legendas
```

Isso irá criar:
- `minhas_legendas.original.vtt` - Legendas no idioma original (formato WebVTT)
- `minhas_legendas.en.vtt` - Legendas traduzidas para inglês (formato WebVTT)
- `minhas_legendas.original.srt` - Legendas no idioma original (formato SubRip/SRT)
- `minhas_legendas.en.srt` - Legendas traduzidas para inglês (formato SubRip/SRT)
- `minhas_legendas.json` - Arquivo técnico com todas as informações

Nota: Os arquivos .srt são compatíveis com a maioria dos players de vídeo e programas de edição.

### Opções Avançadas

A ferramenta possui várias opções para personalizar seu funcionamento:

1. Escolher Tamanho do Modelo:
   ```bash
   python3 transcribe_and_translate_dual_vtt.py video.mp4 saida --model small
   ```
   Modelos disponíveis:
   - `tiny`: Mais rápido mas menos preciso (ideal para testes)
   - `base`: Bom equilíbrio para vídeos curtos
   - `small`: Recomendado para a maioria dos usos
   - `medium`: Mais preciso mas mais lento (funciona bem com 8GB VRAM)
   - `large`: O mais preciso mas requer mais VRAM (recomendado 12GB+ VRAM)

2. Melhorar Vídeos com Múltiplos Idiomas:
   ```bash
   python3 transcribe_and_translate_dual_vtt.py video.mp4 saida --refine-per-segment
   ```
   Esta opção é útil quando seu vídeo tem múltiplos idiomas

3. Pular Tradução:
   ```bash
   python3 transcribe_and_translate_dual_vtt.py video.mp4 saida --no-translate
   ```
   Use isso se você quiser apenas legendas no idioma original

4. Manter o Áudio Extraído:
   ```bash
   python3 transcribe_and_translate_dual_vtt.py video.mp4 saida --keep-audio
   ```
   Isso salvará o arquivo de áudio usado para transcrição

5. Ver Progresso Detalhado:
   ```bash
   python3 transcribe_and_translate_dual_vtt.py video.mp4 saida --verbose
   ```
   Mostra informações detalhadas sobre o que a ferramenta está fazendo

## Arquivos de Saída

A ferramenta cria vários arquivos:

1. Arquivos WebVTT (para navegadores web):
   - `[nome_saida].original.vtt` - Legendas no idioma original
   - `[nome_saida].en.vtt` - Legendas traduzidas para inglês
   - Ideal para uso em players HTML5 e streaming

2. Arquivos SubRip/SRT (para players de vídeo):
   - `[nome_saida].original.srt` - Legendas no idioma original
   - `[nome_saida].en.srt` - Legendas traduzidas para inglês
   - Compatível com a maioria dos players de vídeo e programas de edição
   - Formato mais comum e amplamente suportado

3. Arquivo de Dados:
   - `[nome_saida].json` - Arquivo técnico com todos os segmentos, timestamps e traduções
   - Útil se você quiser processar os dados posteriormente
   - Contém informações detalhadas sobre cada segmento

## Algumas dicas

1. Use áudio de boa qualidade em seus vídeos
3. Se seu vídeo tem múltiplos idiomas, use a opção `--refine-per-segment`
4. Para projetos importantes, use a opção `--verbose` para ver o que está acontecendo
5. Se você tiver uma GPU com mais de 8GB de VRAM, experimente o modelo 'large' para melhor precisão

## Resolução de Problemas

1. Se você receber um erro sobre ffmpeg:
   - Certifique-se de que o ffmpeg está instalado no seu sistema
   - No Ubuntu/Debian: `sudo apt install ffmpeg`

2. Se o script estiver lento:
   - Tente um modelo menor (tiny ou base)
   - Verifique se sua GPU tem VRAM suficiente para o modelo escolhido
   - Considere dividir vídeos longos em partes menores

3. Se a qualidade da transcrição estiver ruim:
   - Use um modelo maior (medium se tiver 8GB VRAM, large se tiver mais)
   - Use a opção `--refine-per-segment`
   - Verifique se a qualidade do áudio do seu vídeo está boa

## Exemplos de Comandos

1. Transcrição rápida de um vídeo curto:
   ```bash
   python3 transcribe_and_translate_dual_vtt.py video_curto.mp4 legendas_rapidas --model tiny
   ```

2. Transcrição de alta qualidade para RTX 4060 Ti (8GB VRAM):
   ```bash
   python3 transcribe_and_translate_dual_vtt.py video_importante.mp4 alta_qualidade --model medium --refine-per-segment --verbose
   ```

3. Apenas legendas no idioma original:
   ```bash
   python3 transcribe_and_translate_dual_vtt.py video.mp4 apenas_original --no-translate
   ```

## Suporte

Esta ferramenta foi projetada para funcionar com vários formatos de vídeo e idiomas. Se você encontrar algum problema, tente executar com a opção `--verbose` para obter mais informações sobre o que pode estar errado.

