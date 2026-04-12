# 🎬 Thumbnail Maker v4

![Python](https://img.shields.io/badge/Python-3.9+-blue)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey)
![License](https://img.shields.io/badge/License-MIT-green)

> ⚠ **Built for bitporn.eu**
>
> This tool was originally built specifically for **bitporn.eu**.
>
> If you want to customize it for your own site or workflow:
>
> - Change **line 926** from:
>   ```
>   bitporn.eu_
>   ```
>   to:
>   ```
>   your.wanted.filename_
>   ```
>
> - Edit the logo on **line 39** to your own desired logo.

Generate thumbnail sheets, animated WEBP previews, automatic center animations, and banner/cover animations for video folders.

---

# 📌 Overview

Thumbnail Maker v4 is a Windows GUI application that:

- Generates professional thumbnail sheets (JPG)
- Creates animated WEBP previews
- Automatically generates center-longest animations per folder
- Creates animated cover/banner images
- Creates `screen.jpg`
- Supports drag & drop
- Uses multi-threading
- Automatically falls back to FFmpeg for WMV decoding

---

# 🖥 System Requirements

- Windows OS
- Python 3.9+
- FFmpeg installed
- Required Python libraries

---

# 🚀 Installation Guide

## 1️⃣ Download Project

Either:

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
```

OR download ZIP and extract.

---

## 2️⃣ Install Python Dependencies

Open Command Prompt inside the project folder and run:

```bash
pip install opencv-python pillow numpy requests tkinterdnd2 psutil
```

---

## 3️⃣ Install FFmpeg (Required)

This program expects FFmpeg in:

```
C:\ffmpeg\bin\
```

You must have:

```
C:\ffmpeg\bin\ffmpeg.exe
C:\ffmpeg\bin\ffprobe.exe
```

If not:

1. Download FFmpeg Windows build  
2. Extract it  
3. Move the folder to `C:\ffmpeg\`

---

# ▶️ How To Run

From the project folder:

```bash
python ThumbsWebP2.py
```

Or double-click `ThumbsWebP2.py`.

---

# 🖱 How To Use

1. Click **Choose Files**  
   OR  
   Click **Add Folder**  
   OR  
   Drag & drop videos into the window  

2. Select Speed Mode:
   - **Normal** → Best quality  
   - **Fast** → Balanced (recommended)  
   - **Fastest** → Maximum speed  

3. Click **Start**

4. Wait until processing completes.

---

# 📂 Output Files

For each video folder, a `scr` directory will be created:

```
VIDEO_FOLDER/scr/
```

Inside:

- bitporn.eu_filename.jpg  
- center1.webp  
- center2.webp  
- center3.webp  
- center4.webp  
- center5.webp  
- centerlongest_foldername.webp  
- screen.jpg  

---

# 📁 Supported Formats

- .mp4  
- .m4v  
- .mkv  
- .mov  
- .avi  
- .wmv  

---

# ⚡ Speed Modes Explained

| Mode      | Description |
|-----------|------------|
| Normal    | Best visual quality |
| Fast      | Balanced performance |
| Fastest   | Maximum speed |

---

# ⏹ Stop Processing

Click **Stop** anytime to safely cancel processing.

---

# 🛠 Technical Details

- CPU usage limited automatically  
- Proxy-safe mode enabled by default  
- FFmpeg fallback for problematic codecs  
- Multi-threaded per-folder processing  

---

# 👤 Author

Made by Pumpkinpounder  
