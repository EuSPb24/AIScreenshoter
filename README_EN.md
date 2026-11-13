[English](README_EN.md) | [Русский](README.md)

# AIScreenshoter

**AIScreenshoter** is a lightweight background utility for Windows (10, 11) that intercepts screenshots and helps you prepare clear visual specifications for AI models or colleagues in seconds.

> This is not a heavy graphics editor. The core idea is to quickly highlight an area, draw an arrow, blur sensitive data, and paste a single combined image with all annotations into any chat using `Ctrl + V`.

---

## Key Features

* **Instant Clipboard Interception**
  Runs quietly in the system tray and automatically opens the annotation canvas when you press `Win + Shift + S` or `PrintScreen`. Screenshots are processed 1:1 in physical pixels without blur or offset across mixed-DPI multi-monitor setups (e.g., FullHD + 2K/4K).
* **Annotation Tools with Smart Badge Placement**
  * **Rectangle** — highlights a UI area and assigns a sequential focus index.
  * **Line & Arrow** — underlines text or points to specific elements with horizontal/vertical auto-snap. The badge is placed at the base and automatically shifts in dense layouts to avoid overlapping text or arrowheads.
  * **Blur** — permanently obscures passwords, tokens, and personal data before sharing.
  * **Select Entire Image** — frames the entire current layer in one click from the tool dropdown.
* **Inline Editing & Visual-Only Markers**
  Click any numbered badge (`1`, `2`, `3`...) to edit its comment right next to the marker. Pressing `Enter` with an empty input leaves a visual-only marker on the image without adding an entry to the bottom footer\*.
* **Multi-Layer Sessions (Multiple Screenshots in One Strip)**
  Pressing `Win + Shift + S` while working automatically hides the utility overlay before Windows freezes the screen and adds the new capture as the next layer (`1/2`, `2/2`...). When saved, all layers are stitched into a single vertical strip with continuous numbering.
* **Combined Image + Text in One Click (Ready for `Ctrl + V`)**
  Clicking **Save (OK)** automatically appends a dark footer\* with an adaptive font size listing all your comments, copies the resulting image to the clipboard, and saves three files to `Pictures\AIScreenshoter\YYYY-MM`: the clean original (`_clean`), the annotated image (`_marked`), and an `.ai` project file for later editing.
* **Native Windows Spell Checking**
  Built-in Windows spell checker underlines typos with a red wavy line based on your active keyboard layout (English, Russian, Chinese, French, Italian, etc.) and provides correction suggestions on right-click.
* **Multi-Language Support (`RU` / `EN` / `ZH` + Custom Locales)**
  Automatically detects your Windows language on first launch and supports adding custom `.ini` translation files to `%APPDATA%\AIScreenshoter\lang\`.

> **\* How the Annotation Footer Works:**
> Most AI chats and messengers do not allow pasting both an image and text from the clipboard at the same time — forcing you to paste the screenshot first and then manually type what markers `1`, `2`, and `3` mean.
> **AIScreenshoter** solves this automatically:
> * When you click the green Save button, the utility renders a clean dark panel at the bottom of your screenshot containing all your text comments mapped to their badge numbers (`1`, `2`, `3`...).
> * A single unified image is placed into your clipboard — with the annotated screenshot on top and a readable breakdown of every point underneath.
> * Font and badge sizes in the footer automatically scale to match the image width: even if you capture two monitors at once via `PrintScreen`, the text remains sharp and easy to read for both humans and AI vision models.
> * Simply press `Ctrl + V` in any AI chat or messenger to send the complete context at once.

---

## Installation & Running

### Option 1. Ready-to-Use Installer (For Users)
1. [Download]([https://github.com](https://github.com/EuSPb24/AIScreenshoter/releases/download/v1.2.4/AIScreenshoter_Setup_1.2.4.exe])) **`AIScreenshoter_Setup_1.2.4.exe`** (direct download) or pick a release on the [Releases]([https://github.com](https://github.com/EuSPb24/AIScreenshoter/releases])) page.
2. Run the installer (Python is not required).
3. The utility icon will appear in your system tray. Press `Win + Shift + S` or `PrintScreen` to start.

---

### Option 2. Building `.exe` and Installer from Source (`build.py` + `installer.iss`)
Use this option if you want to compile the standalone `AIScreenshoter.exe` and `AIScreenshoter_Setup_1.2.4.exe` installer yourself.

**Requirements:** Windows 10/11, **Python 3.11+**, **Inno Setup 6 or 7** (to compile `installer.iss`).

```bash
git clone https://github.com
cd AIScreenshoter
pip install PySide6 pyinstaller
python build.py
```

**What `build.py` does:**
1. Generates `app_icon.ico` from the vector definitions in `assets.py`.
2. Bundles the application and `.ini` localization files into a single executable: **`dist/AIScreenshoter.exe`**.
3. Automatically locates the Inno Setup compiler (`ISCC.exe`) and builds **`dist_setup/AIScreenshoter_Setup_1.2.4.exe`** using **`installer.iss`**.

*(You can also open and compile `installer.iss` manually via the Inno Setup Compiler GUI).*

---

### Option 3. Running & Developing in Visual Studio Code (VS Code)
1. Clone the repository and open the project folder in **VS Code** (`File -> Open Folder...`).
2. Install the official **Python** extension by Microsoft.
3. Open the integrated terminal in VS Code (`Ctrl + ~`) and install the dependency:
   ```bash
   pip install PySide6
   ```
4. Select **`main.py`** and press **`F5`** (run with debugging) or **`Ctrl + F5`** (run without debugging).
5. The utility icon will appear in the Windows system tray.

---

## Shortcuts & Controls

| Action | Control |
| :--- | :--- |
| Capture screenshot / add a new layer | `Win + Shift + S` or `PrintScreen` |
| Confirm marker comment | `Enter` (new line: `Shift + Enter`) |
| Edit existing marker text | Left-click on the numbered badge (`1`, `2`...) |
| Switch between layers | `Prev` / `Next` buttons on toolbar or `PageUp` / `PageDown` |
| Undo / Redo action in current layer | `Undo` / `Redo` toolbar buttons |
| Close without saving | Double-press `ESC` (when markers are present) |

---

## Authors

Created jointly by **EvGen** and **Gemini AI Assistant (Google)** in 2026 (`v.1.2.4`).
