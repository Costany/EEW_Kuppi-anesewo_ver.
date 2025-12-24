"""
EEW Mode entry: real-time intensity with rise/decay envelopes.

This extends the existing EarthquakeSimulator without modifying core files.
Run this file to use the EEW-style diminishing intensity visualization:

    python earthquake_sim/eew_mode.py
"""

from __future__ import annotations

import os
import pygame

from intensity import intensity_to_scale, get_intensity_color
from eew_calculator import envelope_single, envelope_multi

# Import the base simulator from the same directory
from main import EarthquakeSimulator


class EEWEarthquakeSimulator(EarthquakeSimulator):
    """Simulator that overrides station intensity calculation to use
    P/S attack-decay envelopes (EEW-like real-time behavior).
    """

    def __init__(self):
        super().__init__()
        # How to drive the header max value: "current" or "peak" (future option)
        self.header_mode = "current"

    # Override dispatcher to use EEW envelope calculators
    def calculate_station_intensities(self):
        if self.sim_mode == "multi":
            return self._calculate_station_intensities_multi_eew()
        return self._calculate_station_intensities_single_eew()

    def _calculate_station_intensities_single_eew(self):
        if not self.earthquake:
            return

        self.station_intensities = {}
        self.region_max_intensities = {}
        self.max_intensity = 0.0
        self.max_intensity_location = ""

        for station in self.stations:
            lat = float(station['lat'])
            lon = float(station['lon'])
            area_code = station['area']['code']
            area_name = station['area']['name']
            amp = float(station.get('amp', 1.0))

            intensity, is_s_wave = envelope_single(self.earthquake, lat, lon, amp=amp)
            if intensity < 0.5:
                continue

            self.station_intensities[(lat, lon)] = (intensity, is_s_wave)
            prev = self.region_max_intensities.get(area_code, 0.0)
            if intensity > prev:
                self.region_max_intensities[area_code] = intensity
            if intensity > self.max_intensity:
                self.max_intensity = intensity
                self.max_intensity_location = area_name

        # Sounds: trigger once when passing thresholds
        if not self.intensity4_played and self.max_intensity >= 3.5 and self.intensity4_sound:
            self.intensity4_sound.play()
            self.intensity4_played = True

        if not self.intensity7_played and self.max_intensity >= 6.5 and self.intensity7_sound:
            self.intensity7_sound.play()
            self.intensity7_played = True

        # White circle alert when first reaching >= 3.0 (monotonic trigger)
        for (lat, lon), (intensity, is_s_wave) in self.station_intensities.items():
            if intensity >= 3.0 and intensity > self.max_triggered_intensity:
                scale = intensity_to_scale(intensity)
                self.max_triggered_intensity = intensity
                self.alert_animations.append((lat, lon, self._current_time_value(), scale))
                break

    def _calculate_station_intensities_multi_eew(self):
        if not self.multi_manager:
            return

        self.station_intensities = {}
        self.region_max_intensities = {}
        self.max_intensity = 0.0
        self.max_intensity_location = ""

        for station in self.stations:
            lat = float(station['lat'])
            lon = float(station['lon'])
            area_code = station['area']['code']
            area_name = station['area']['name']
            amp = float(station.get('amp', 1.0))

            intensity, is_s_wave = envelope_multi(self.multi_manager, lat, lon, amp=amp)
            if intensity < 0.5:
                continue

            self.station_intensities[(lat, lon)] = (intensity, is_s_wave)
            prev = self.region_max_intensities.get(area_code, 0.0)
            if intensity > prev:
                self.region_max_intensities[area_code] = intensity
            if intensity > self.max_intensity:
                self.max_intensity = intensity
                self.max_intensity_location = area_name

        if not self.intensity4_played and self.max_intensity >= 3.5 and self.intensity4_sound:
            self.intensity4_sound.play()
            self.intensity4_played = True

        if not self.intensity7_played and self.max_intensity >= 6.5 and self.intensity7_sound:
            self.intensity7_sound.play()
            self.intensity7_played = True

        for (lat, lon), (intensity, is_s_wave) in self.station_intensities.items():
            if intensity >= 3.0 and intensity > self.max_triggered_intensity:
                scale = intensity_to_scale(intensity)
                self.max_triggered_intensity = intensity
                self.alert_animations.append((lat, lon, self._current_time_value(), scale))
                break


if __name__ == "__main__":
    sim = EEWEarthquakeSimulator()
    sim.run()
