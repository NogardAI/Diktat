# Diktát – návod pro AI asistenta

Tento soubor je pro AI (Claude Code, Codex, Cursor…), která má Diktát zprovoznit a doladit na novém počítači. Uživatel je Čech a nemusí být programátor – komunikuj česky, vysvětluj jednoduše a před zásahy do kódu se zeptej.

## Co to je

Push-to-talk diktování pro Windows: uživatel drží klávesu (výchozí pravý Ctrl), mluví, pustí → text se vloží do aktivního okna. Vše lokálně, bez cloudu.

## Datový tok

```
hotkey.py      globální hook (knihovna keyboard). Držení = nahrávání. Jiná klávesa během držení = zrušení (aby fungovalo pravý Ctrl+C).
   ↓
recorder.py    sounddevice, 16 kHz mono float32 do paměti; level pro indikátor
   ↓
transcriber.py faster-whisper. Na Windows přidá CUDA DLL z pip balíčků nvidia-*; když GPU selže, spadne na CPU (int8).
               Pokud je PyAV blokovaný, nahradí ho prázdným modulem (audio jde jako numpy, av není potřeba).
   ↓
cleanup.py     Ollama /api/chat, temperature 0, think false. Hunspell slovník hlídá výstup (viz níže).
   ↓
inserter.py    text do schránky → Ctrl+V → původní schránka se vrátí
```

UI: `overlay.py` (malé Tk okno – nahrávám / zpracovávám), `tray.py` (pystray ikona: přepínač úpravy textu, otevření configu, konec).
`__main__.py` drží vše dohromady: Tk hlavní vlákno + fronta UI, worker vlákno pro model a zpracování nahrávek.
`run.pyw` = vstup bez konzole. `toggle.ps1` (přes `Diktat.bat`) zapíná/vypíná proces. `install_autostart.ps1` dá zástupce do Po spuštění.

## Nejdůležitější: pojistka úpravy textu (nerozbít)

Malé LLM (gemma4:e4b) mělo sklon přepisovat platná slova (např. „Chtěl“ → „Chrěl“) nebo odpovídat na obsah. Proto `cleanup.py`:

1. `spelling_hints` – najde ve Whisper přepisu slova mimo český slovník a navrhne kandidáty lišící se o 1 písmeno; pošle je LLM jako řádek `NÁPOVĚDA:`.
2. LLM smí jen: mazat vycpávky/opakování, upravit interpunkci a velká písmena, opravit slovo mimo slovník.
3. `_invented_words` + `_is_spelling_fix` – každé slovo ve výstupu, které v přepisu nebylo, musí být číslovka nebo oprava překlepu (původní slovo NENÍ ve slovníku, nové JE a jsou si podobná ≥ 0,75).
4. Cokoli jiného, prázdný nebo příliš dlouhý výstup, timeout, Ollama neběží → vloží se **surový přepis**.

Když budeš měnit model nebo prompt, tuhle logiku zachovej. Raději vložit surový text než text se změněným významem.

## Konfigurace (`config.toml`)

| Sekce / klíč | Význam |
|---|---|
| `hotkey.key` | Klávesa podle knihovny keyboard: `"right ctrl"`, `"right alt"`, `"caps lock"`, `"f9"`… |
| `hotkey.min_seconds` | Kratší nahrávky se zahodí (náhodný stisk). |
| `whisper.model` | `large-v3` (nejpřesnější v češtině), `medium`, `small`. **`large-v3-turbo` je v češtině znatelně horší.** |
| `whisper.device` / `compute_type` | `cuda` + `float16`, nebo `cpu` (automaticky `int8`). Při málo VRAM zkus `int8_float16`. |
| `whisper.vocabulary` | Jde do Whisperu jako `initial_prompt`. Má to být **běžná česká věta s odbornými termíny** uživatele, ne seznam slov. Přizpůsob oboru uživatele. |
| `cleanup.enabled` | Zapnutí úpravy LLM (přepíná se i v trayi). |
| `cleanup.model` | Model v Ollamě. Musí být nainstalovaný (`ollama pull …`). |
| `cleanup.timeout_seconds` | Po vypršení se vloží surový přepis. Na pomalém HW zvyš. |
| `cleanup.keep_alive` | Jak dlouho Ollama drží model v paměti. |
| `insert.trailing_space` | Mezera za vloženým textem. |

Po změně configu je nutný restart aplikace (dvakrát `Diktat.bat`).

## Ladění podle hardwaru

Nejdřív zjisti HW: `nvidia-smi` (GPU a VRAM), RAM, CPU.

| Hardware | Whisper | Úprava textu |
|---|---|---|
| NVIDIA ≥ 10 GB VRAM | `large-v3`, `cuda`, `float16` | `gemma4:e4b` |
| NVIDIA 6–8 GB VRAM | `large-v3` + `int8_float16`, případně `medium` | malý model (`gemma4:e2b` apod.), nebo LLM na CPU |
| NVIDIA < 6 GB | `medium` / `small`, `int8_float16` | vypnout, nebo malý model |
| Bez NVIDIA (jen CPU) | `small` nebo `medium`, `cpu` | spíš vypnout (zdržuje); případně malý model a vyšší timeout |

Whisper a LLM sdílí VRAM – když se nevejdou, LLM poběží z RAM a bude pomalé. Cíl: celé zpracování do ~2 s po puštění klávesy. Časy obou kroků jsou v `diktat.log` (`whisper X.XXs`, `cleanup X.XXs`).

## Postup zprovoznění na novém PC

1. Ověř Python 3.11+ (`python --version`), zjisti GPU.
2. Nainstaluj Ollamu (https://ollama.com) a stáhni model: `ollama pull gemma4:e4b` (nebo menší podle tabulky).
3. V kořeni repa:
   ```powershell
   python -m venv .venv
   .venv\Scripts\python -m pip install -r requirements.txt
   ```
   Bez NVIDIA GPU nejsou balíčky `nvidia-cublas-cu12` a `nvidia-cudnn-cu12` potřeba (ale neškodí).
4. Uprav `config.toml` podle HW a oboru uživatele (`vocabulary`).
5. Otestuj části samostatně:
   ```powershell
   .venv\Scripts\python -m diktat.transcriber          # načte model, vypíše device
   .venv\Scripts\python -m diktat.cleanup "ehm tak jako zítra se sejdem v deset"
   ```
6. Spusť s konzolí `.venv\Scripts\python -m diktat`, nech uživatele nadiktovat pár vět, čti `diktat.log`.
7. Pak už běžně přes `Diktat.bat` (zástupce na plochu) a případně `install_autostart.ps1`.

## Ladění přesnosti

- `last.wav` je poslední nahrávka – použij ji k opakovanému testu: `python -m diktat.transcriber last.wav`.
- `diktat.log` obsahuje surový přepis, upravený text, slova mimo slovník a důvody, proč se úprava zahodila („LLM změnil slova …“).
- Chyby v termínech → doplnit je do `vocabulary`. Chyby v obecných slovech → větší Whisper model. Úprava se často zahazuje → menší zásah promptu, ne vypnutí pojistky.

## Známé záludnosti (Windows)

- **Smart App Control** (Windows 11) blokuje nepodepsané binárky: `pythonw.exe`, `pip.exe`, některé DLL (např. PyAV). Proto: `python -m pip`, `toggle.ps1` spouští `python.exe` se skrytým oknem místo `pythonw.exe`, `av` se nahrazuje prázdným modulem.
- Do aplikací spuštěných jako správce se text vloží jen, když Diktát běží také jako správce.
- PowerShell 5.1 čte `.ps1` bez BOM jako ANSI – skripty v repu jsou uložené jako UTF-8 s BOM, při úpravách to zachovej.
- Klávesa: pokud zvolená klávesa koliduje se zkratkami uživatele, změň `hotkey.key`.

## Pravidla pro úpravy

- Nejdřív ladit přes `config.toml`, až potom kód.
- Na pojistku v `cleanup.py` nesahat bez otestování na reálných nahrávkách.
- `diktat.log` a `last.wav` obsahují osobní data – nikdy je necommitovat (jsou v `.gitignore`).
