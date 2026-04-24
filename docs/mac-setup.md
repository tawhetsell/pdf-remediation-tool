# Mac Setup Guide

Full prerequisites walkthrough for macOS. Run these steps once before using the remediation tool.

## 1 — Homebrew

Homebrew is the package manager used to install Java and ocrmypdf.

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the prompts — it will ask for your Mac password. When it finishes, run the command it shows to add Homebrew to your PATH. It looks like this:

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
source ~/.zshrc
```

Verify:

```bash
brew --version
```

If you see a version number, Homebrew is ready.

---

## 2 — Java 17

```bash
brew install openjdk@17
echo 'export PATH="/opt/homebrew/opt/openjdk/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Verify:

```bash
java -version
```

You should see `openjdk version "17..."`. If you still see a stub error, close and reopen your terminal and try again.

---

## 3 — Python 3.10+

macOS ships Python 3.9 by default. Check what you have:

```bash
python3 --version
```

If it shows 3.10 or higher, skip to step 4. If not:

```bash
brew install python@3.11
echo 'export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Verify:

```bash
python3 --version
```

---

## 4 — Python packages

```bash
pip3 install --upgrade opendataloader-pdf pypdf
```

---

## 5 — ocrmypdf (optional)

Only needed for scanned PDFs. Skip if your files are all born-digital.

```bash
brew install ocrmypdf
```

---

## 6 — Verify everything

```bash
bash scripts/bootstrap.sh
```

All required items should show `[ok]`. Optional items (`ocrmypdf`, `verapdf`) will show `[warn]` if missing — that's fine.

---

## Troubleshooting

**`brew: command not found` after install**
Homebrew wasn't added to your PATH. Run:
```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zshrc
source ~/.zshrc
```

**`java -version` still shows stub error after install**
Close and reopen your terminal, then retry. If still failing:
```bash
export PATH="/opt/homebrew/opt/openjdk/bin:$PATH"
java -version
```

**`python3 --version` still shows 3.9 after install**
The old Python is still winning on PATH. Run:
```bash
echo 'export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

**bootstrap.sh fails on `opendataloader_pdf` missing**
```bash
pip3 install --upgrade opendataloader-pdf pypdf
```
