"""
EEW Mode (RT) entry: real-time intensity with rise/decay envelopes
and visual fixes (S-wave color sticks to historical peak; one-shot alert).

Run:
    python earthquake_sim/eew_mode_rt.py
"""

from __future__ import annotations

import os
import math
import pygame

from intensity import intensity_to_scale
import eew_calculator as eew
from eew_calculator import envelope_single, envelope_multi
from main import EarthquakeSimulator, get_shindo_color


class EEWRTSimulator(EarthquakeSimulator):
    def __init__(self):
        super().__init__()
        # Header keeps historical maximum per your preference
        self.header_mode = "peak"  # informational only; draw uses self.max_intensity

        # Per-event states
        self.peak_intensity_ever = 0.0
        self._alert_fired_once = False
        self._current_eq_id = None
        self._current_mgr_id = None

    # Dispatcher override
    def calculate_station_intensities(self):
        if self.sim_mode == "multi":
            return self._calc_multi()
        return self._calc_single()

    def _reset_for_new_eq(self):
        self.peak_intensity_ever = 0.0
        self._alert_fired_once = False
        self.max_intensity = 0.0  # header historical max per event
        self.max_intensity_location = ""

    def _calc_single(self):
        if not self.earthquake:
            return

        if self._current_eq_id is not id(self.earthquake):
            self._current_eq_id = id(self.earthquake)
            self._reset_for_new_eq()

        self.station_intensities = {}
        self.region_max_intensities = {}

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
            if intensity > self.peak_intensity_ever:
                self.peak_intensity_ever = intensity

        if not self.intensity4_played and self.max_intensity >= 3.5 and self.intensity4_sound:
            self.intensity4_sound.play()
            self.intensity4_played = True
        if not self.intensity7_played and self.max_intensity >= 6.5 and self.intensity7_sound:
            self.intensity7_sound.play()
            self.intensity7_played = True

        # FIX #2: Only trigger alert once, using the station with max intensity
        if not self._alert_fired_once and self.max_intensity >= 3.0:
            if self.station_intensities:
                max_station = max(self.station_intensities.items(), key=lambda x: x[1][0])
                (lat, lon), (intensity, _) = max_station
                scale = intensity_to_scale(intensity)
                self.max_triggered_intensity = intensity
                self.alert_animations.append((lat, lon, self._current_time_value(), scale))
                self._alert_fired_once = True

    def _calc_multi(self):
        if not self.multi_manager:
            return

        if self._current_mgr_id is not id(self.multi_manager):
            self._current_mgr_id = id(self.multi_manager)
            self._reset_for_new_eq()

        self.station_intensities = {}
        self.region_max_intensities = {}

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
            if intensity > self.peak_intensity_ever:
                self.peak_intensity_ever = intensity

        if not self.intensity4_played and self.max_intensity >= 3.5 and self.intensity4_sound:
            self.intensity4_sound.play()
            self.intensity4_played = True
        if not self.intensity7_played and self.max_intensity >= 6.5 and self.intensity7_sound:
            self.intensity7_sound.play()
            self.intensity7_played = True

        # FIX #2: Only trigger alert once, using the station with max intensity
        if not self._alert_fired_once and self.max_intensity >= 3.0:
            if self.station_intensities:
                max_station = max(self.station_intensities.items(), key=lambda x: x[1][0])
                (lat, lon), (intensity, _) = max_station
                scale = intensity_to_scale(intensity)
                self.max_triggered_intensity = intensity
                self.alert_animations.append((lat, lon, self._current_time_value(), scale))
                self._alert_fired_once = True

    # Keep S-wave ring color fixed to historical peak intensity
    def draw_wave_circles(self):
        if self.sim_mode == "multi":
            if not self.multi_manager:
                return
            _, _, _, _, pixels_per_km, _, _ = self._view_km_params()
            # FIX #1: Use peak_intensity_ever instead of max_intensity for fixed color
            s_color = get_shindo_color(self.peak_intensity_ever) if self.peak_intensity_ever >= 0.5 else (128, 128, 128)

            for circle in self.multi_manager.get_wave_circles():
                cx, cy = self.latlon_to_screen(circle["lat"], circle["lon"])
                p_px = int(circle["p_radius"] * pixels_per_km)
                s_px = int(circle["s_radius"] * pixels_per_km)
                if p_px > 0 and p_px < self.screen.get_width() * 3:
                    pygame.draw.circle(self.screen, (0, 150, 255), (cx, cy), p_px, 2)
                if s_px > 0 and s_px < self.screen.get_width() * 3:
                    pygame.draw.circle(self.screen, s_color, (cx, cy), s_px, 3)

            icon_scale = min(0.8, max(0.2, 0.15 * self.zoom_level))
            for src in self.multi_manager.sources:
                if src.active:
                    ex, ey = self.latlon_to_screen(src.lat, src.lon)
                    if self.epicenter_icon:
                        icon = pygame.transform.smoothscale(self.epicenter_icon, (
                            int(self.epicenter_icon.get_width() * icon_scale),
                            int(self.epicenter_icon.get_height() * icon_scale)
                        ))
                        rect = icon.get_rect(center=(ex, ey))
                        self.screen.blit(icon, rect)
                    else:
                        s = max(8, int(15 * icon_scale))
                        pygame.draw.line(self.screen, (255, 0, 0), (ex - s, ey), (ex + s, ey), 3)
                        pygame.draw.line(self.screen, (255, 0, 0), (ex, ey - s), (ex, ey + s), 3)
            return

        if not self.earthquake:
            return

        ex, ey = self.latlon_to_screen(self.earthquake.lat, self.earthquake.lon)
        _, _, _, _, pixels_per_km, _, _ = self._view_km_params()

        p_radius_km = self.earthquake.get_p_wave_radius()
        p_radius_px = int(p_radius_km * pixels_per_km)
        if p_radius_px > 0 and p_radius_px < self.screen.get_width() * 3:
            pygame.draw.circle(self.screen, (0, 150, 255), (ex, ey), p_radius_px, 2)

        s_radius_km = self.earthquake.get_s_wave_radius()
        s_radius_px = int(s_radius_km * pixels_per_km)
        # FIX #1: Use peak_intensity_ever instead of max_intensity for fixed color
        s_color = get_shindo_color(self.peak_intensity_ever) if self.peak_intensity_ever >= 0.5 else (128, 128, 128)

        SCRATCH_P = 6.5
        SCRATCH_S = 4.0
        depth = self.earthquake.depth
        s_arrival_time = depth * (1 - SCRATCH_S / SCRATCH_P) / SCRATCH_S
        current_time = self.earthquake.time

        if 0 < current_time < s_arrival_time:
            progress = current_time / s_arrival_time
            angle_deg = min(360, progress * 360)
            base_radius = 100
            arc_radius = max(15, int(base_radius * 0.15 * self.zoom_level))
            arc_rect = pygame.Rect(ex - arc_radius, ey - arc_radius, arc_radius * 2, arc_radius * 2)
            # FIX #1: Also use peak_intensity_ever for arc prep color
            prep_color = s_color if self.peak_intensity_ever >= 0.5 else (128, 128, 128)
            start_angle = math.pi / 2
            end_angle = start_angle + math.radians(angle_deg)
            if angle_deg > 1:
                pygame.draw.arc(self.screen, prep_color, arc_rect, start_angle, end_angle, 3)

        if current_time >= s_arrival_time and s_radius_px > 0 and s_radius_px < self.screen.get_width() * 3:
            pygame.draw.circle(self.screen, s_color, (ex, ey), s_radius_px, 3)
            if self.s_wave_icon and s_radius_px > 10:
                icon_size = s_radius_px * 2
                icon = pygame.transform.smoothscale(self.s_wave_icon, (icon_size, icon_size))
                tinted = icon.copy()
                tinted.fill(s_color + (0,), special_flags=pygame.BLEND_RGB_MULT)
                tinted.set_alpha(80)
                rect = tinted.get_rect(center=(ex, ey))
                self.screen.blit(tinted, rect)

        icon_scale = min(0.8, max(0.2, 0.15 * self.zoom_level))
        if self.epicenter_icon:
            icon = pygame.transform.smoothscale(self.epicenter_icon, (
                int(self.epicenter_icon.get_width() * icon_scale),
                int(self.epicenter_icon.get_height() * icon_scale)
            ))
            rect = icon.get_rect(center=(ex, ey))
            self.screen.blit(icon, rect)
        else:
            s = max(8, int(15 * icon_scale))
            pygame.draw.line(self.screen, (255, 0, 0), (ex - s, ey), (ex + s, ey), 3)
            pygame.draw.line(self.screen, (255, 0, 0), (ex, ey - s), (ex, ey + s), 3)


if __name__ == "__main__":
    sim = EEWRTSimulator()
    sim.run()
