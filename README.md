<p align="center">
  <img src="images/banneer.png" alt="GestuApp Banner" width="800"/>
</p>

<h1 align="center">GestuApp</h1>

<p align="center">
  <b>Control your media and scroll with hand gestures using your webcam</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/MediaPipe-Hand_Tracking-00A98F?logo=google&logoColor=white" alt="MediaPipe"/>
  <img src="https://img.shields.io/badge/OpenCV-Computer_Vision-5C3EE8?logo=opencv&logoColor=white" alt="OpenCV"/>
  <img src="https://img.shields.io/badge/UI-CustomTkinter-1F6FEB?logo=python&logoColor=white" alt="CustomTkinter"/>
</p>

---

## What is GestuApp?

GestuApp is a desktop application that lets you **control your computer with hand gestures** detected in real time through your webcam. Using MediaPipe for hand tracking and OpenCV for video processing, it recognizes specific finger positions and movements to trigger media actions — play/pause music, skip tracks, adjust volume, or scroll through pages — all without touching your keyboard.

It runs quietly in your system tray and comes with a modern configuration UI built with CustomTkinter, where you can fine-tune every parameter and remap gestures to different actions.

<p align="center">
  <table>
    <tr>
        <td><img src="images/gesto1.png" alt="Gesture 1"/></td>
        <td><img src="images/gesto2.png" alt="Gesture 2"/></td>
    </tr>
    <tr>
      <td><img src="images/gesto3.png" alt="Gesture 3"/></td>
      <td><img src="images/gesto4.png" alt="Gesture 4"/></td>
    </tr>
  </table>
</p>


---

## Features

- **Hand gesture recognition** — Real-time hand tracking using MediaPipe with angle and distance-based gesture detection
- **Media control** — Play/pause, next track, and previous track via configurable hand gestures
- **Volume control** — Adjust system volume by pinching your thumb and index finger closer or further apart
- **Scroll control** — Scroll pages up and down with adjustable speed using finger position
- **Modern config UI** — CustomTkinter interface with tabs for parameter tuning and gesture remapping
- **System tray integration** — Runs in the background; left-click the tray icon to toggle the camera window
- **Fully configurable** — Adjust distance thresholds, angle thresholds, cooldown times, scroll speed, and invert directions
- **Gesture remapping** — Assign any available action to any detected gesture from the UI
- **Persistent settings** — Configuration is saved to a JSON file and survives restarts
- **Anti-bounce system** — Configurable cooldown between actions to prevent accidental repeated triggers

---

## How It Works

```mermaid
flowchart LR
    A[Webcam] -->|video frames| B[OpenCV]
    B -->|RGB image| C[MediaPipe Hands]
    C -->|hand landmarks| D[Gesture Engine]
    D -->|angle + distance| E{Gesture Classification}
    E -->|play/pause| F[Keyboard Simulation]
    E -->|next/prev track| F
    E -->|volume up/down| F
    E -->|scroll up/down| F
    G[Config UI] -->|parameters| D
    H[System Tray] -->|start/stop| B
```

1. The **webcam** captures video frames in real time via OpenCV
2. Each frame is converted to RGB and sent to **MediaPipe Hands** for landmark detection
3. The **gesture engine** calculates the angle between thumb, wrist, and index finger, plus the distance between thumb and index fingertips
4. Based on configurable **thresholds**, the gesture is classified into one of the available actions
5. The corresponding **keyboard shortcut** is simulated (media keys, volume keys, or page up/down)
6. An **anti-bounce timer** prevents repeated triggers within the configured cooldown period

---

## Gestures

| Gesture | Default Action | How to Perform |
|---|---|---|
| **Thumb + index touching** | Play / Pause | Bring your thumb and index fingertips together |
| **Wide angle, hand left** | Previous track | Open your thumb and index finger wide, pointing left |
| **Wide angle, hand right** | Next track | Open your thumb and index finger wide, pointing right |
| **Pinch** | Volume control | Make a pinch and change its size (distance between thumb and index) — closer to lower, further to raise |
| **Pinch (U shape)** | Scroll down | Form a U-shaped pinch with thumb and index to scroll down |
| **Pinch (C shape)** | Scroll up | Form a C-shaped pinch with thumb and index to scroll up |

> All gesture-to-action mappings can be changed from the **Gesture Mapping** tab in the configuration window.

---

## Getting Started

### Prerequisites

- **Python 3.10+**
- A working **webcam**
- **Windows 10/11** (tested on Windows 10) — may work on other platforms with minor adjustments

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/pepinisillo/GestuApp.git
cd GestuApp
```

2. **Install dependencies**

```bash
pip install -r requirements.txt
```

3. **Run the application**

```bash
python gestuapp.py
```

> **Note:** On Linux, the `keyboard` library requires root privileges. Run with `sudo` if needed, or configure udev rules for your user.

### First Launch

When you run GestuApp for the first time:

1. The camera window opens automatically showing the live feed with hand tracking overlay
2. A **system tray icon** appears — right-click it to access options
3. The configuration window is hidden by default — right-click the tray icon and select **Show/Hide Config**

---

## Configuration

### Parameters Tab

<img src="images/parameters.png" alt="Parameters Configuration Interface" width="600"/>

| Parameter | Description | Default |
|---|---|---|
| **Min volume distance** | Minimum finger distance for volume control | 0.05 |
| **Max volume distance** | Maximum finger distance for volume control | 0.15 |
| **Pause threshold** | Distance threshold to detect the touch gesture | 0.025 |
| **Song change angle** | Minimum angle to trigger track change | 50° |
| **Volume/scroll angle** | Maximum angle for volume/scroll mode | 30° |
| **Scroll speed** | Speed of page scrolling (0.1 slow — 1.0 fast) | 0.5 |
| **Action cooldown** | Minimum time between consecutive actions | 1.5s |
| **Invert track direction** | Swap left/right for next/previous track | Off |

### Gesture Mapping Tab

<img src="images/mapping_gesture.png" alt="Gesture Mapping Interface" width="600"/>


Each detected gesture can be remapped to any of the following actions:

- Play/Pause
- Previous Track
- Next Track
- Volume Control
- Scroll Control
- Do Nothing

---

## Keyboard Shortcuts (Camera Window)

| Key | Action |
|---|---|
| `q` | Hide camera window (minimizes to tray) |
| `p` | Pause / resume gesture detection |

---

## Project Structure

```
GestuApp/
├── gestuapp.py        # Main application (gesture engine + UI + tray)
├── requirements.txt   # Python dependencies
├── images/            # UI and gesture screenshots for documentation
│   ├── banneer.png
│   ├── gesto1.png
│   ├── gesto2.png
│   ├── gesto3.png
│   ├── gesto4.png
│   ├── parameters.png
│   └── mapping_gesture.png
├── .gitignore
└── README.md
```

---

## Tech Stack

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white&style=for-the-badge" alt="Python"/>
  <img src="https://img.shields.io/badge/OpenCV-4.8-5C3EE8?logo=opencv&logoColor=white&style=for-the-badge" alt="OpenCV"/>
  <img src="https://img.shields.io/badge/MediaPipe-0.10-00A98F?logo=google&logoColor=white&style=for-the-badge" alt="MediaPipe"/>
  <img src="https://img.shields.io/badge/CustomTkinter-5.2-1F6FEB?logo=python&logoColor=white&style=for-the-badge" alt="CustomTkinter"/>
  <img src="https://img.shields.io/badge/NumPy-1.26-013243?logo=numpy&logoColor=white&style=for-the-badge" alt="NumPy"/>
  <img src="https://img.shields.io/badge/pystray-System_Tray-333333?logo=windows&logoColor=white&style=for-the-badge" alt="pystray"/>
</p>

---

<p align="center">
  <img src="https://github.com/pepinisillo/pepinisillo/blob/main/ons2.jpg" alt="Owari no Seraph"/>
  <i>"If you smile everyday and live happily from now on, then that's enough"</i><br/>
  <b>— Yuuichirou Hyakuya</b>
</p>
