Plant Health AI & Zen Vision
=============================

Lightweight open-source toolkit for plant health monitoring and integrated ecosystem management.

## Applications

### 🌿 Plant Health AI
Core plant analysis toolkit for detecting health issues from photos and videos.

### 🌱 Zen Vision
Integrated application combining plant health monitoring with solar power management for a complete ecosystem solution.

## Features

### Plant Health AI
- Rule-based image heuristics for yellowing, nutrient burn, brown edges, spots (mold/pests), and light stress.
- Video sampling to detect trends (declining green levels) over time.
- CLI for single image, folder, or video analysis.

### Zen Vision
- Unified interface for plant health analysis and solar AI simulation
- Real-time solar power management with intelligent load balancing
- Comprehensive system monitoring and diagnostics
- Menu-driven interface for easy operation

## Quick Start

### Plant Health AI

1. Create a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Analyze an image:

```bash
python -m plant_health.cli image /path/to/leaf.jpg --out result.json
```

3. Analyze a folder of images:

```bash
python -m plant_health.cli folder ./images --out report.json
```

4. Analyze a video (samples every 5 seconds by default):

```bash
python -m plant_health.cli video /path/to/clip.mp4 --sample 5 --out video_report.json
```

### Zen Vision

1. Install dependencies (same as above)

2. Run the integrated application:

```bash
python zen_vision.py
```

3. Use the menu to:
   - Analyze plant images and videos
   - Run solar power simulations
   - Monitor system status
   - Perform full system checks

## Project Structure

```
├── zen_vision.py              # Integrated Zen Vision application
├── chatbot.py                 # Ghost in the Shell themed chatbot (separate)
├── plant_health/              # Plant health analysis package
│   ├── __init__.py
│   ├── cli.py                 # Command-line interface
│   ├── image_analyzer.py      # Single image analysis
│   ├── video_analyzer.py      # Video analysis with trends
│   └── solar_ai.py           # Solar power management AI
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Dependencies

- opencv-python: Computer vision and image processing
- numpy: Numerical computations
- scikit-image: Advanced image processing
- matplotlib: Plotting and visualization
- imutils: Image processing utilities

## Notes

- This is a prototype using image heuristics. For earlier-than-eye detection, consider adding temporal ML models trained on timelapse datasets.
- The solar AI simulates intelligent power routing between solar, battery, and grid sources.
- Zen Vision provides a harmonious integration of plant monitoring and renewable energy management.
- Contributions welcome. License: MIT (add LICENSE file to project).
