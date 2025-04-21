# Rock-Paper-Scissors Gesture Recognition Setup Guide

This guide walks you through setting up the Rock-Paper-Scissors hand-gesture recognition project locally using MiniConda and PyQt6.

## 1. Install Miniconda

1. Download the Miniconda installer for your platform:
   - **Windows (64-bit)**: https://repo.anaconda.com/miniconda/Miniconda3-latest-Windows-x86_64.exe
   - **macOS (Intel)**: https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh
   - **macOS (Apple Silicon)**: https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh
   - **Linux (64-bit)**: https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh

2. Run the installer:
   - **Windows**: Double-click the `.exe` and follow the prompts.
   - **macOS/Linux**: Open a terminal and run:
     ```bash
     bash Miniconda3-latest-*.sh
     ```
     Then follow the on-screen instructions.

3. Close and reopen your terminal (or PowerShell) to activate conda.

## 2. Clone the Project Repository

In your terminal, choose a directory and run:

```bash
git clone https://github.com/your-username/rps-gesture.git
cd rps-gesture
```

## 3. Create and Activate the Conda Environment

1. Ensure you have the `environment.yml` file in the project root (it should contain PyQt6, OpenCV, MediaPipe, etc.).

2. Create the environment:

   ```bash
   conda env create -f environment.yml
   ```

3. Activate it:

   ```bash
   conda activate rps-gesture
   ```

## 4. Run the Application

With the environment active, start the PyQt6 app:

```bash
python rps_game.py
```

## 5. Troubleshooting

- **Camera access issues**: Ensure no other application is using the camera. On Windows, run the script natively (not WSL).
- **Missing GUI**: Verify PyQt6 installed (`pip show PyQt6` or `conda list pyqt`).
- **MediaPipe errors**: Confirm `mediapipe` is installed via pip in the environment.

---

You’re now ready to play Rock-Paper-Scissors with the computer! Enjoy!