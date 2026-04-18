# 🌍 World Emotion Simulator

A Python simulation that models how real-world news events trigger emotions across countries and how those emotions spread globally over time. Outputs a rendered video ready to post on YouTube Shorts or Instagram Reels.

---

## 💡 Concept

Every week, you feed in real news headlines. The simulator:
1. Uses the **Claude API** to determine which countries are affected and by how much
2. Applies **emotion deltas** to those countries (fear, anger, sadness, anxiety, hope, joy)
3. Simulates **day-by-day spreading** — emotions ripple to neighboring countries at different rates
4. Renders each day as a **color-coded world map frame**
5. Tracks a **World Happiness Index** that rises and falls with global events
6. Compiles all frames into an **MP4 video**

---

## 📁 File Structure

```
ProjectWorldEmotions/
│
├── countries.py          # 37 countries with neighbor connections and map coordinates
├── emotions.py           # 6 emotions with spread rate, decay rate, happiness weight
├── simulation.py         # Core tick logic — spreading and decay per day
├── news_parser.py        # Sends headlines to Claude API, returns emotion deltas per country
├── renderer.py           # Draws world map + happiness graph using matplotlib + geopandas
├── main.py               # Entry point — runs simulation and exports video
│
├── ne_110m_admin_0_countries/   # Natural Earth shapefile (downloaded separately)
│   ├── ne_110m_admin_0_countries.shp
│   └── ...
│
├── frames/               # Auto-generated PNG frames (one per simulated day)
└── world_emotion.mp4     # Final output video
```

---

## 🧠 Emotions

| Emotion | Color  | Spreads | Decays | Happiness Weight |
|---------|--------|---------|--------|-----------------|
| Fear    | Red    | Fast    | Slow   | -0.8 |
| Anger   | Orange | Fast    | Medium | -0.7 |
| Sadness | Blue   | Slow    | Very slow | -0.6 |
| Anxiety | Purple | Medium  | Slow   | -0.5 |
| Hope    | Green  | Slow    | Medium | +0.9 |
| Joy     | Yellow | Very slow | Fast | +1.0 |

Key insight: **negative emotions spread faster than positive ones** — intentionally realistic.

---

## 🗺️ How the Map Works

- Built with **geopandas** using the Natural Earth 110m shapefile
- Each country polygon is colored by **blending all its active emotions** weighted by intensity
- Countries not in the simulation render as dark neutral grey
- Neighbor connections determine spread paths (defined in `countries.py`)

---

## ⚙️ Setup

### 1. Install Python dependencies
```bash
pip install matplotlib numpy geopandas
```

### 2. Install ffmpeg (for video export)
- **Windows**: https://ffmpeg.org/download.html
- **Mac**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

### 3. Download the world shapefile
Download **Admin 0 – Countries** from:
https://www.naturalearthdata.com/downloads/110m-cultural-vectors/

Extract and place the folder as `ne_110m_admin_0_countries/` in the project root.

### 4. Add your Anthropic API key
In `news_parser.py`:
```python
API_KEY = "sk-ant-..."
```
Get your key at: https://console.anthropic.com

Without a key, the simulator uses keyword-based fallback events so you can still test.

---

## 🚀 Running the Simulation

Edit your weekly headlines in `main.py`:
```python
WEEKLY_NEWS = [
    "Major earthquake hits Southeast Asia, thousands displaced",
    "Global economic recession fears grow as markets crash",
    "Historic peace deal signed in the Middle East",
]
```

Then run:
```bash
python main.py
```

Output: `world_emotion.mp4` ready to post.

---

## 🔧 Configuration (main.py)

| Variable | Default | Description |
|----------|---------|-------------|
| `DAYS_PER_NEWS_EVENT` | 7 | Days simulated between each headline |
| `FPS` | 6 | Frames per second in output video |
| `FRAMES_DIR` | `"frames"` | Where PNG frames are saved |
| `OUTPUT_VIDEO` | `"world_emotion.mp4"` | Output filename |

---

## 🗺️ Countries Tracked

37 countries across 6 regions:
- **Americas**: USA, Canada, Mexico, Brazil, Colombia, Argentina
- **Europe**: UK, France, Germany, Spain, Italy, Poland, Ukraine, Russia
- **Middle East**: Turkey, Iran, Iraq, Syria, Saudi Arabia
- **Africa**: Egypt, Nigeria, South Africa, Ethiopia, Libya, Sudan
- **Asia**: Kazakhstan, Afghanistan, Pakistan, India, Bangladesh, China, Japan, South Korea, North Korea, Vietnam, Thailand, Indonesia
- **Oceania**: Australia

---

## 🔮 Planned Features

- [ ] Claude API integration for automatic news parsing
- [ ] Animated smooth transitions between frames
- [ ] Regional emotion averages panel
- [ ] Historical episode mode (past events)
- [ ] Custom music that shifts with happiness index
