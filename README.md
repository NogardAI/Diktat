# Diktát

Lokální push-to-talk diktování v češtině pro Windows (obdoba Wispr Flow). Držíš klávesu, mluvíš, pustíš a text se vloží do aktivního okna. Všechno běží offline na tvém PC.

- Přepis: faster-whisper `large-v3` (na NVIDIA GPU, jinak CPU)
- Úprava textu: lokální LLM přes Ollamu (interpunkce, „ehm“, opravy překlepů), hlídaná českým slovníkem. Dá se vypnout v trayi.
- Ovládání: podržet **pravý Ctrl** (lze změnit v `config.toml`)

> **Používáš AI asistenta (Claude Code, Codex, Cursor…)?** Řekni mu: *„Přečti AGENTS.md a nastav Diktát pro můj počítač.“* V [AGENTS.md](AGENTS.md) je popis architektury a postup ladění podle hardwaru.

## Požadavky

- Windows 10/11, Python 3.11+
- [Ollama](https://ollama.com) a model pro úpravu textu: `ollama pull gemma4:e4b` (volitelné – bez Ollamy se vloží surový přepis)
- Doporučeno NVIDIA GPU s ~10 GB VRAM; bez ní to jede na CPU s menším modelem (viz AGENTS.md)

## Instalace

```powershell
git clone https://github.com/NogardAI/Diktat.git
cd Diktat
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
```

`python -m pip` místo `pip.exe` – Smart App Control ve Windows 11 může nepodepsané `pip.exe` blokovat.

## Spuštění

```powershell
.\Diktat.bat                         # zapne / vypne (bez konzole); hodí se zástupce na plochu
.venv\Scripts\python -m diktat       # s konzolí (vidíš log) - na ladění
.\install_autostart.ps1              # spouštět po přihlášení
```

Při prvním spuštění se stáhne model Whisper (~3 GB). Stav ukazuje ikona v liště: oranžová = načítá, zelená = připraveno, červená = nahrává.

## Testy jednotlivých částí

```powershell
.venv\Scripts\python -m diktat.transcriber nahravka.wav
.venv\Scripts\python -m diktat.cleanup "ehm tak jako zítra se sejdem v deset"
```

## Poznámky

- Stiskneš-li během držení klávesy jinou klávesu (např. pravý Ctrl+C), nahrávka se zruší a zkratka funguje normálně.
- Do aplikací spuštěných jako správce se text vloží jen tehdy, když Diktát běží také jako správce.
- Úpravu LLM hlídá český slovník (`dict\cs_CZ.*`). LLM smí jen mazat vycpávková slova, upravit interpunkci a opravit slovo, které není ve slovníku. Když změní cokoli jiného, vloží se surový přepis.
- Log: `diktat.log` (surový přepis, upravený text, slova mimo slovník). Poslední nahrávka: `last.wav`. Oba soubory jsou lokální a do gitu nejdou.

## Licence

Kód: MIT (viz `LICENSE`). Slovník `dict/cs_CZ.*` je český hunspell slovník z LibreOffice a má vlastní licenci (GPL).
