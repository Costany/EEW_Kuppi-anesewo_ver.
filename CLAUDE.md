# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Interactive earthquake arrival-time simulator for Japan. Python/Pygame rewrite of the Scratch project "地震の到達時間シミュレーション". Visualizes P- and S-wave propagation, calculates JMA (Japan Meteorological Agency) seismic intensities, and renders Japan's map with epicenter region labeling.

## Setup & Running

This project uses **Conda** for environment management. The user manages the environment, not Claude Code.

```bash
# Setup (user does this)
conda activate meteo
cd earthquake_sim
pip install -r requirements.txt

# Run simulator (user does this)
python earthquake_sim/main.py
```

## Architecture

```
earthquake_sim/
├── main.py          # EarthquakeSimulator class - pygame loop, UI, event handling
├── config.py        # Constants: wave speeds, window size, map bounds, intensity colors
├── earthquake.py    # Earthquake model - epicenter params, wave radius/arrival calculations
├── intensity.py     # JMA intensity formulas (distance attenuation, PGA conversion)
├── epicenter.py     # EpicenterLocator - GeoJSON point-in-polygon region lookup
└── map_renderer.py  # MapRenderer - draws GeoJSON polygons on pygame surface
```

Key data flow:
- `main.py` creates `Earthquake` instance with user-set lat/lon/depth/magnitude
- `Earthquake.update(dt)` advances time; `get_p_wave_radius()` / `get_s_wave_radius()` compute current wave fronts
- `EpicenterLocator` and `MapRenderer` both load `JMA_Region-main/震央地名.geojson` for region names and map outlines

## Key Constants (config.py)

- P_WAVE_SPEED: 7.3 km/s
- S_WAVE_SPEED: 4.1 km/s
- MAP_BOUNDS: Japan region (lon 122-154, lat 24-46)
- Window: 1200x800 @ 60 FPS

## Simulator Controls

- Arrow keys: adjust lat/lon
- D/F: adjust depth
- M/N: adjust magnitude
- Enter: start simulation
- Space: pause/resume
- R: reset
- +/-: change playback speed

## IMPORTANT: Package Installation Policy

**Claude Code AI MUST NOT execute `pip install` or `python -m pip install` commands.**

- This repository uses a pre-bash hook to **block** all pip install attempts from Claude Code
- Package installation is **exclusively the user's responsibility**
- The user manages their Conda environment (`conda activate meteo`)
- If code needs new dependencies, Claude Code should:
  1. Tell the user which packages are needed
  2. Let the user run `pip install` in their activated environment
  3. Test after the user has installed packages

**Why?** This prevents accidental package installation to the system or wrong environment, and ensures the user has full control over their development environment.
