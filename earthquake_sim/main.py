"""地震模拟器主程序 - pygame可视化"""
import pygame
import json
import math
import os
import sys
import io

import cairosvg

from config import *
from earthquake import Earthquake
from intensity import calc_jma_intensity, intensity_to_scale, get_intensity_color
from epicenter import EpicenterLocator
from map_renderer import MapRenderer
from projection import latlon_to_xy_km, xy_km_to_latlon

# 显示模式
MODE_STATION = 0  # 站点模式
MODE_REGION = 1   # 区域模式

def load_svg(path, scale=1.0):
    """加载SVG文件并转换为pygame surface"""
    png_data = cairosvg.svg2png(url=path, scale=scale)
    return pygame.image.load(io.BytesIO(png_data))

def scale_icon(icon, factor):
    """缩放图标"""
    w, h = icon.get_size()
    new_w = max(1, int(w * factor))
    new_h = max(1, int(h * factor))
    return pygame.transform.smoothscale(icon, (new_w, new_h))

# 震度颜色映射
SHINDO_COLORS = {
    1: (0x21, 0x99, 0xFA),  # #2199FA
    2: (0x37, 0xCD, 0x33),  # #37CD33
    3: (0xED, 0xAA, 0x00),  # #EDAA00
    4: (0xFB, 0x6E, 0x00),  # #FB6E00
    5: (0xF9, 0x10, 0x10),  # #F91010 (5-)
    6: (0xFB, 0x6E, 0x00),  # #FB6E00 (5+)
    7: (0xE9, 0x3D, 0x80),  # #E93D80 (6-)
    8: (0xC4, 0x35, 0x7A),  # #C4357A (6+)
    9: (0x95, 0x00, 0xB0),  # #9500B0 (7)
}

def get_shindo_color(intensity):
    """根据震度值获取颜色"""
    scale = intensity_to_scale(intensity)
    idx_map = {'1':1, '2':2, '3':3, '4':4, '5-':5, '5+':6, '6-':7, '6+':8, '7':9}
    idx = idx_map.get(scale, 3)
    return SHINDO_COLORS.get(idx, (0xED, 0xAA, 0x00))

class EarthquakeSimulator:
    def __init__(self):
        pygame.init()
        pygame.key.set_repeat(200, 50)  # 长按支持
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("地震波到达时间模拟器")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 24)

        # 尝试加载中文字体
        try:
            font_paths = [
                "C:/Windows/Fonts/msyh.ttc",
                "C:/Windows/Fonts/simhei.ttf",
                "/System/Library/Fonts/PingFang.ttc",
            ]
            for fp in font_paths:
                if os.path.exists(fp):
                    self.font_cn = pygame.font.Font(fp, 20)
                    self.font_cn_large = pygame.font.Font(fp, 36)
                    self.font_cn_small = pygame.font.Font(fp, 16)
                    break
            else:
                self.font_cn = self.font
                self.font_cn_large = pygame.font.Font(None, 40)
                self.font_cn_small = pygame.font.Font(None, 18)
        except:
            self.font_cn = self.font
            self.font_cn_large = pygame.font.Font(None, 40)
            self.font_cn_small = pygame.font.Font(None, 18)

        # 加载震央地名数据（用于定位）
        geojson_path = os.path.join(os.path.dirname(__file__),
                                     "../JMA_Region-main/震央地名.geojson")
        self.locator = EpicenterLocator(geojson_path if os.path.exists(geojson_path) else None)

        # 加载都道府县地图（用于显示日本轮廓）
        pref_path = os.path.join(os.path.dirname(__file__),
                                  "../JMA_Region-main/prefectures.geojson")
        self.prefectures = []
        if os.path.exists(pref_path):
            with open(pref_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.prefectures = data.get('features', [])

        # 地图参数
        self.map_bounds = MAP_BOUNDS.copy()
        self.default_bounds = MAP_BOUNDS.copy()  # 保存默认边界用于缩放限制
        self.zoom_level = 1.0
        self.earthquake = None
        self.running = True
        self.paused = False
        self.time_scale = 1.0

        # 设置模式
        self.setting_mode = True
        self.temp_lat = 35.7
        self.temp_lon = 139.7
        self.temp_depth = 10
        self.temp_mag = 6.0

        # 区域震度数据
        self.region_intensities = {}
        self.max_intensity = 0
        self.detected_regions = []

        # 显示模式
        self.display_mode = MODE_REGION

        # 加载图标
        self.load_icons()

        # 加载站点和区域数据
        self.stations = []
        self.regions_data = []  # 细分区域（用于填色）
        self.load_station_region_data()

        # 加载音频
        pygame.mixer.init()
        sound_path = os.path.join(os.path.dirname(__file__), "sounds/intensity4.wav")
        self.intensity4_sound = pygame.mixer.Sound(sound_path) if os.path.exists(sound_path) else None
        self.intensity4_played = False

        # 白色圆圈闪烁动画
        self.max_triggered_intensity = 0.0  # 已触发的最大震度值
        self.alert_animations = []  # 动画队列: [(lat, lon, start_time, scale), ...]

    def load_icons(self):
        """加载SVG图标"""
        assets_dir = os.path.join(os.path.dirname(__file__), "assets")

        # 站点图标 s1-s9 (圆形)
        self.station_icons = {}
        for i in range(1, 10):
            path = os.path.join(assets_dir, f"s{i}.svg")
            if os.path.exists(path):
                self.station_icons[i] = load_svg(path, scale=0.5)

        # 区域图标 t1-t9 (方形)
        self.region_icons = {}
        for i in range(1, 10):
            path = os.path.join(assets_dir, f"t{i}.svg")
            if os.path.exists(path):
                self.region_icons[i] = load_svg(path, scale=0.5)

        # 震度图标 (左上角最大震度显示)
        self.shindo_icons = {}
        shindo_files = {
            0: "震度0.svg", 1: "震度1.svg", 2: "震度2.svg", 3: "震度3.svg",
            4: "震度4.svg", 5: "震度5弱.svg", 6: "震度5強.svg",
            7: "震度6弱.svg", 8: "震度6強.svg", 9: "震度7.svg"
        }
        for idx, fname in shindo_files.items():
            path = os.path.join(assets_dir, fname)
            if os.path.exists(path):
                self.shindo_icons[idx] = load_svg(path, scale=1.0)

        # 震央图标
        path = os.path.join(assets_dir, "po央.svg")
        self.epicenter_icon = load_svg(path, scale=0.8) if os.path.exists(path) else None

        # 位置图标 (设置模式鼠标跟随)
        path = os.path.join(assets_dir, "位置.svg")
        self.position_icon = load_svg(path, scale=0.8) if os.path.exists(path) else None

        # S波圆圈图标
        path = os.path.join(assets_dir, "円.svg")
        self.s_wave_icon = load_svg(path, scale=1.0) if os.path.exists(path) else None

    def load_station_region_data(self):
        """加载站点和区域数据"""
        data_dir = os.path.join(os.path.dirname(__file__), "data")

        # 加载站点
        stations_path = os.path.join(data_dir, "stations.json")
        if os.path.exists(stations_path):
            with open(stations_path, 'r', encoding='utf-8') as f:
                self.stations = json.load(f)

        # 加载细分区域多边形（地震情報／細分区域）
        regions_path = os.path.join(data_dir, "area_forecast.geojson")
        if os.path.exists(regions_path):
            with open(regions_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.regions_data = data.get('features', [])

    def _view_km_params(self) -> tuple[float, float, float, float, float, float, float]:
        """把当前 map_bounds 转成 km 平面范围与屏幕映射参数（统一比例）。

        返回：x_min_km, x_max_km, y_min_km, y_max_km, pixels_per_km, x_offset_px, y_offset_px
        """
        cache_key = (
            self.map_bounds["min_lon"],
            self.map_bounds["max_lon"],
            self.map_bounds["min_lat"],
            self.map_bounds["max_lat"],
            WINDOW_WIDTH,
            WINDOW_HEIGHT,
        )
        if getattr(self, "_view_cache_key", None) == cache_key:
            return self._view_cache_params

        # km 平面边界
        x_min_km, _ = latlon_to_xy_km(0.0, self.map_bounds["min_lon"])
        x_max_km, _ = latlon_to_xy_km(0.0, self.map_bounds["max_lon"])
        _, y_min_km = latlon_to_xy_km(self.map_bounds["min_lat"], 0.0)
        _, y_max_km = latlon_to_xy_km(self.map_bounds["max_lat"], 0.0)

        x_span = max(1e-6, x_max_km - x_min_km)
        y_span = max(1e-6, y_max_km - y_min_km)
        pixels_per_km = min(WINDOW_WIDTH / x_span, WINDOW_HEIGHT / y_span)

        # 为了保持 x/y 同比例，可能会产生留白；这里居中显示
        x_offset = (WINDOW_WIDTH - x_span * pixels_per_km) / 2
        y_offset = (WINDOW_HEIGHT - y_span * pixels_per_km) / 2
        params = (x_min_km, x_max_km, y_min_km, y_max_km, pixels_per_km, x_offset, y_offset)
        self._view_cache_key = cache_key
        self._view_cache_params = params
        return params

    def latlon_to_screen(self, lat: float, lon: float) -> tuple:
        """经纬度转屏幕坐标（Scratch 兼容投影，波前为正圆）。"""
        x_min_km, x_max_km, y_min_km, y_max_km, ppk, x_off, y_off = self._view_km_params()
        x_km, y_km = latlon_to_xy_km(lat, lon)
        sx = x_off + (x_km - x_min_km) * ppk
        sy = y_off + (y_max_km - y_km) * ppk
        return int(sx), int(sy)

    def screen_to_latlon(self, x: int, y: int) -> tuple:
        """屏幕坐标转经纬度（Scratch 兼容投影）。"""
        x_min_km, x_max_km, y_min_km, y_max_km, ppk, x_off, y_off = self._view_km_params()
        x_km = x_min_km + (x - x_off) / ppk
        y_km = y_max_km - (y - y_off) / ppk
        return xy_km_to_latlon(x_km, y_km)

    def calculate_station_intensities(self):
        """计算各站点震度 - P波检测震度较低，S波检测震度为实际值"""
        if not self.earthquake:
            return

        # 获取当前波的震央距离半径
        p_radius = self.earthquake.get_p_wave_radius()
        s_radius = self.earthquake.get_s_wave_radius()
        self.station_intensities = {}  # (lat,lon) -> (intensity, is_s_wave)
        self.region_max_intensities = {}  # 区域代码 -> 最大震度
        self.max_intensity = 0
        self.max_intensity_location = ""

        prev_max = self.max_intensity

        for station in self.stations:
            lat = float(station['lat'])
            lon = float(station['lon'])
            area_code = station['area']['code']
            area_name = station['area']['name']
            amp = float(station.get('amp', 1.0))  # 站点放大系数

            # 使用震央距离判断波是否到达
            epicentral_dist = self.earthquake.get_epicentral_distance(lat, lon)

            # 计算S波实际震度（Scratch 兼容：场地系数 amp 先变换成 bai 再参与计算）
            bai = (amp * 4 + amp * amp) / 5.0
            s_intensity = calc_jma_intensity(
                self.earthquake.magnitude,
                self.earthquake.depth,
                epicentral_dist,
                bai=bai,
            )
            # P波震度计算 (Scratch公式: S波震度 / 1.5 - 0.5)
            p_intensity = s_intensity / 1.5 - 0.5

            if epicentral_dist <= s_radius and s_intensity >= 0.5:
                # S波已到达 - 显示实际震度
                self.station_intensities[(lat, lon)] = (s_intensity, True)
                if area_code not in self.region_max_intensities or s_intensity > self.region_max_intensities[area_code]:
                    self.region_max_intensities[area_code] = s_intensity
                if s_intensity > self.max_intensity:
                    self.max_intensity = s_intensity
                    self.max_intensity_location = area_name
            elif epicentral_dist <= p_radius and p_intensity >= 0.5:
                # P波已到达但S波未到 - 显示P波检测到的较低震度
                self.station_intensities[(lat, lon)] = (p_intensity, False)
                # P波震度也计入区域和最大震度（但值较低）
                if area_code not in self.region_max_intensities or p_intensity > self.region_max_intensities[area_code]:
                    self.region_max_intensities[area_code] = p_intensity
                if p_intensity > self.max_intensity:
                    self.max_intensity = p_intensity
                    self.max_intensity_location = area_name

        # 检测震度4并播放音频（震度4的范围是3.5-4.5）
        if not self.intensity4_played and self.max_intensity >= 3.5 and self.intensity4_sound:
            self.intensity4_sound.play()
            self.intensity4_played = True

        # 检测震度3+并触发白色圆圈动画（只在震度升高时触发）
        for (lat, lon), (intensity, is_s_wave) in self.station_intensities.items():
            if intensity >= 3.0 and intensity > self.max_triggered_intensity:
                scale = intensity_to_scale(intensity)
                self.max_triggered_intensity = intensity
                self.alert_animations.append((lat, lon, self.earthquake.time, scale))
                break  # 只触发第一个站点

    def draw_stations(self):
        """绘制站点模式 - 使用s1-s9图标"""
        # 图标缩放因子：限制在0.02-0.41之间
        icon_scale = min(0.41, max(0.02, 0.1 * self.zoom_level))

        for station in self.stations:
            lat = float(station['lat'])
            lon = float(station['lon'])
            data = self.station_intensities.get((lat, lon))
            if not data:
                continue

            intensity, is_s_wave = data
            x, y = self.latlon_to_screen(lat, lon)

            # 震度转图标索引
            icon_idx = intensity_to_scale(intensity)
            idx_map = {'1':1, '2':2, '3':3, '4':4, '5-':5, '5+':6, '6-':7, '6+':8, '7':9}
            idx = idx_map.get(icon_idx, 1)

            if idx in self.station_icons:
                icon = scale_icon(self.station_icons[idx], icon_scale)
                rect = icon.get_rect(center=(x, y))
                self.screen.blit(icon, rect)
            else:
                r = max(3, int(10 * icon_scale))
                color = get_intensity_color(intensity)
                pygame.draw.circle(self.screen, color, (x, y), r)
                pygame.draw.circle(self.screen, (0, 0, 0), (x, y), r, 1)

    def draw_regions_with_intensity(self):
        """绘制带震度的区域 - 使用t1-t9图标"""
        region_labels = []
        # 图标缩放因子：限制在0.15-0.6之间
        icon_scale = min(0.6, max(0.15, 0.1 * self.zoom_level))

        for region in self.regions_data:
            props = region.get('properties', {})
            code = props.get('code', '')
            geom = region.get('geometry', {})
            coords = geom.get('coordinates', [])
            geom_type = geom.get('type', '')

            intensity = self.region_max_intensities.get(code, 0)

            if geom_type == 'Polygon':
                polys = [coords[0]]
            elif geom_type == 'MultiPolygon':
                polys = [c[0] for c in coords]
            else:
                continue

            if intensity >= 1:
                all_lons = []
                all_lats = []
                for poly in polys:
                    for lon, lat in poly:
                        all_lons.append(lon)
                        all_lats.append(lat)
                if all_lons:
                    cx, cy = self.latlon_to_screen(sum(all_lats)/len(all_lats), sum(all_lons)/len(all_lons))
                    region_labels.append((cx, cy, intensity))

        # 绘制区域震度标签
        for cx, cy, intensity in region_labels:
            icon_idx = intensity_to_scale(intensity)
            idx_map = {'1':1, '2':2, '3':3, '4':4, '5-':5, '5+':6, '6-':7, '6+':8, '7':9}
            idx = idx_map.get(icon_idx, 1)

            if idx in self.region_icons:
                icon = scale_icon(self.region_icons[idx], icon_scale)
                rect = icon.get_rect(center=(cx, cy))
                self.screen.blit(icon, rect)
            else:
                s = max(6, int(20 * icon_scale))
                color = get_intensity_color(intensity)
                pygame.draw.rect(self.screen, color, (cx-s//2, cy-s//2, s, s))
                pygame.draw.rect(self.screen, (0, 0, 0), (cx-s//2, cy-s//2, s, s), 1)

    def draw_wave_circles(self):
        """绘制地震波圆和震央标记"""
        if not self.earthquake:
            return

        ex, ey = self.latlon_to_screen(self.earthquake.lat, self.earthquake.lon)
        _, _, _, _, pixels_per_km, _, _ = self._view_km_params()

        # P波 (蓝色) - 正圆
        p_radius_km = self.earthquake.get_p_wave_radius()
        p_radius_px = int(p_radius_km * pixels_per_km)
        if p_radius_px > 0 and p_radius_px < WINDOW_WIDTH * 3:
            pygame.draw.circle(self.screen, (0, 150, 255), (ex, ey), p_radius_px, 2)

        # S波 - 颜色跟随最大震度，无震度时灰色
        s_radius_km = self.earthquake.get_s_wave_radius()
        s_radius_px = int(s_radius_km * pixels_per_km)
        s_color = get_shindo_color(self.max_intensity) if self.max_intensity >= 0.5 else (128, 128, 128)

        # S波准备圆圈（从地震开始到S波到达地表时完成）
        # 使用Scratch速度常数（与earthquake.py一致）
        SCRATCH_P = 6.5
        SCRATCH_S = 4.0
        depth = self.earthquake.depth
        # S波到达地表时间：根据earthquake.py的公式反推
        # total_dist = 4*t + depth*4/6.5 > depth 时S波出现
        # t > depth * (1 - 4/6.5) / 4 = depth * 2.5 / 26
        s_arrival_time = depth * (1 - SCRATCH_S / SCRATCH_P) / SCRATCH_S
        current_time = self.earthquake.time

        if 0 < current_time < s_arrival_time:
            progress = current_time / s_arrival_time
            angle_deg = min(360, progress * 360)

            # 圆圈大小与震央图标同步缩放
            base_radius = 100
            arc_radius = max(15, int(base_radius * 0.15 * self.zoom_level))
            arc_rect = pygame.Rect(ex - arc_radius, ey - arc_radius, arc_radius * 2, arc_radius * 2)

            # 从顶部(90度)开始逆时针画弧，颜色跟随当前震度
            prep_color = get_shindo_color(self.max_intensity) if self.max_intensity >= 0.5 else (128, 128, 128)
            start_angle = math.pi / 2
            end_angle = start_angle + math.radians(angle_deg)
            if angle_deg > 1:
                pygame.draw.arc(self.screen, prep_color, arc_rect, start_angle, end_angle, 3)

        # S波圆圈（S波到达地表后显示）
        if current_time >= s_arrival_time and s_radius_px > 0 and s_radius_px < WINDOW_WIDTH * 3:
            # 先画S波圆圈边框
            pygame.draw.circle(self.screen, s_color, (ex, ey), s_radius_px, 3)

            # 再画円图标（半透明填充）
            if self.s_wave_icon and s_radius_px > 10:
                icon_size = s_radius_px * 2
                icon = pygame.transform.smoothscale(self.s_wave_icon, (icon_size, icon_size))
                tinted = icon.copy()
                tinted.fill(s_color + (0,), special_flags=pygame.BLEND_RGB_MULT)
                tinted.set_alpha(80)
                rect = tinted.get_rect(center=(ex, ey))
                self.screen.blit(tinted, rect)

        # 震央标记 - 使用po央图标（不变色）
        icon_scale = min(0.8, max(0.2, 0.15 * self.zoom_level))

        if self.epicenter_icon:
            icon = scale_icon(self.epicenter_icon, icon_scale)
            rect = icon.get_rect(center=(ex, ey))
            self.screen.blit(icon, rect)
        else:
            s = max(8, int(15 * icon_scale))
            pygame.draw.line(self.screen, (255, 0, 0), (ex-s, ey), (ex+s, ey), 3)
            pygame.draw.line(self.screen, (255, 0, 0), (ex, ey-s), (ex, ey+s), 3)

    def draw_alert_circles(self):
        """绘制站点首次检测震度时的白色圆圈闪烁动画"""
        if not self.earthquake or self.display_mode != MODE_STATION:
            return

        current_time = self.earthquake.time
        duration = 0.8  # 动画持续时间（秒）
        to_remove = []

        for i, (lat, lon, start_time, scale) in enumerate(self.alert_animations):
            elapsed = current_time - start_time
            if elapsed > duration:
                to_remove.append(i)
                continue

            # 计算动画进度（0到1）
            progress = elapsed / duration

            # 半径扩散：10px -> 60px
            radius = int(10 + 50 * progress)

            # 透明度衰减：255 -> 0
            alpha = int(255 * (1 - progress))

            # 转换为屏幕坐标
            x, y = self.latlon_to_screen(lat, lon)

            # 绘制白色圆圈（使用临时surface实现透明度）
            temp_surface = pygame.Surface((radius * 2 + 4, radius * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(temp_surface, (255, 255, 255, alpha), (radius + 2, radius + 2), radius, 3)
            self.screen.blit(temp_surface, (x - radius - 2, y - radius - 2))

        # 清理已完成的动画
        for i in reversed(to_remove):
            self.alert_animations.pop(i)

    def draw_earthquake_info(self):
        """绘制地震速报风格信息（左上角）- 使用震度图标"""
        if not self.earthquake:
            return

        if self.max_intensity < 0.5:
            return

        scale = intensity_to_scale(self.max_intensity)
        color = get_intensity_color(self.max_intensity)

        # 震度转图标索引
        idx_map = {'0':0, '1':1, '2':2, '3':3, '4':4, '5-':5, '5+':6, '6-':7, '6+':8, '7':9}
        idx = idx_map.get(scale, 0)

        # 背景框
        pygame.draw.rect(self.screen, (0, 0, 0), (10, 10, 360, 150))
        pygame.draw.rect(self.screen, color, (10, 10, 360, 150), 3)

        y = 20
        surf = self.font_cn.render(f"最大震度", True, (255, 255, 255))
        self.screen.blit(surf, (20, y))

        # 使用震度图标 - 放在文字右边，缩小显示
        if idx in self.shindo_icons:
            icon = scale_icon(self.shindo_icons[idx], 0.6)
            self.screen.blit(icon, (260, y - 5))
        else:
            surf = self.font_cn_large.render(f"{scale}", True, color)
            self.screen.blit(surf, (260, y - 5))
        y += 50

        # 最大震度所在地
        if hasattr(self, 'max_intensity_location') and self.max_intensity_location:
            surf = self.font_cn_small.render(f"({self.max_intensity_location})", True, (200, 200, 200))
            self.screen.blit(surf, (20, y))
            y += 20

        # 震央
        location = self.locator.get_location_name(self.earthquake.lon, self.earthquake.lat, 'ja')
        surf = self.font_cn.render(f" {location}", True, (255, 255, 255))
        self.screen.blit(surf, (20, y))
        y += 25

        surf = self.font_cn.render(f"M{self.earthquake.magnitude:.1f} {self.earthquake.depth}km", True, (255, 255, 255))
        self.screen.blit(surf, (20, y))
        y += 25

        surf = self.font_cn_small.render(f"経過: {self.earthquake.time:.1f}秒", True, (200, 200, 200))
        self.screen.blit(surf, (20, y))

    def draw_setting_info(self):
        """绘制设置信息（无背景框）"""
        if not self.setting_mode:
            return

        # 震央位置标记 - 使用位置图标，颜色随深度变化
        ex, ey = self.latlon_to_screen(self.temp_lat, self.temp_lon)
        depth = self.temp_depth
        depth_ratio = min(1.0, depth / 300)
        icon_scale = min(0.8, max(0.2, 0.15 * self.zoom_level))

        if self.position_icon:
            icon = scale_icon(self.position_icon, icon_scale)
            tinted = icon.copy()
            tint_color = (int(255 * (1 - depth_ratio)), 0, int(255 * depth_ratio))
            tinted.fill(tint_color, special_flags=pygame.BLEND_MULT)
            rect = tinted.get_rect(center=(ex, ey))
            self.screen.blit(tinted, rect)
        else:
            s = max(8, int(15 * icon_scale))
            cross_color = (int(255 * (1 - depth_ratio)), 0, int(255 * depth_ratio))
            pygame.draw.line(self.screen, cross_color, (ex-s, ey), (ex+s, ey), 2)
            pygame.draw.line(self.screen, cross_color, (ex, ey-s), (ex, ey+s), 2)

        # 左下角显示参数
        y = WINDOW_HEIGHT - 80
        location = self.locator.get_location_name(self.temp_lon, self.temp_lat, 'ja')

        texts = [
            (f"震央: {location}", (255, 255, 255)),
            (f"M{self.temp_mag:.1f} (←→) 深度{self.temp_depth}km (↑↓)", (255, 255, 0)),
            ("左键放置 / Enter开始", (180, 180, 180)),
        ]
        for text, color in texts:
            surf = self.font_cn.render(text, True, color)
            self.screen.blit(surf, (15, y))
            y += 25

    def draw_help(self):
        """绘制帮助信息"""
        if self.setting_mode:
            return
        helps = ["Space:暂停", "R:重置", "+/-:速度", "T:切换显示"]
        y = WINDOW_HEIGHT - 30
        text = "  ".join(helps)
        surf = self.font_cn_small.render(text, True, (150, 150, 150))
        self.screen.blit(surf, (15, y))

    def draw_mode_button(self):
        """绘制右上角模式切换按钮"""
        btn_w, btn_h = 80, 30
        btn_x = WINDOW_WIDTH - btn_w - 10
        btn_y = 10
        self.mode_btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)

        # 按钮背景
        pygame.draw.rect(self.screen, (40, 40, 60), self.mode_btn_rect)
        pygame.draw.rect(self.screen, (100, 100, 120), self.mode_btn_rect, 2)

        # 按钮文字
        text = "站点" if self.display_mode == MODE_STATION else "区域"
        surf = self.font_cn.render(text, True, (255, 255, 255))
        text_rect = surf.get_rect(center=self.mode_btn_rect.center)
        self.screen.blit(surf, text_rect)

    def zoom_map(self, mouse_pos, factor):
        """缩放地图，以鼠标位置为中心（km 平面等比例缩放）。"""
        new_zoom = self.zoom_level * factor

        # 限制缩放范围：最小1.0（默认），最大15.0
        if new_zoom < 1.0 or new_zoom > 15.0:
            return

        x_min_km, x_max_km, y_min_km, y_max_km, ppk, x_off, y_off = self._view_km_params()
        x_span = max(1e-6, x_max_km - x_min_km)
        y_span = max(1e-6, y_max_km - y_min_km)
        map_w_px = x_span * ppk
        map_h_px = y_span * ppk
        if map_w_px <= 1e-6 or map_h_px <= 1e-6:
            return

        mx, my = mouse_pos
        mouse_x_ratio = (mx - x_off) / map_w_px
        mouse_y_ratio = (my - y_off) / map_h_px
        mouse_x_ratio = max(0.0, min(1.0, mouse_x_ratio))
        mouse_y_ratio = max(0.0, min(1.0, mouse_y_ratio))

        # 鼠标对应的世界坐标(km)
        anchor_x_km = x_min_km + mouse_x_ratio * x_span
        anchor_y_km = y_max_km - mouse_y_ratio * y_span

        new_x_span = x_span / factor
        new_y_span = y_span / factor

        new_x_min_km = anchor_x_km - mouse_x_ratio * new_x_span
        new_x_max_km = new_x_min_km + new_x_span
        new_y_max_km = anchor_y_km + mouse_y_ratio * new_y_span
        new_y_min_km = new_y_max_km - new_y_span

        # km 边界反算到经纬度边界
        min_lat, _ = xy_km_to_latlon(0.0, new_y_min_km)
        max_lat, _ = xy_km_to_latlon(0.0, new_y_max_km)
        _, min_lon = xy_km_to_latlon(new_x_min_km, 0.0)
        _, max_lon = xy_km_to_latlon(new_x_max_km, 0.0)

        self.map_bounds['min_lon'] = min_lon
        self.map_bounds['max_lon'] = max_lon
        self.map_bounds['min_lat'] = min_lat
        self.map_bounds['max_lat'] = max_lat

        self.zoom_level = new_zoom

    def draw_map_boundaries(self):
        """绘制日本地图边界（使用都道府县数据）"""
        land_color = (0x3B, 0x42, 0x38)  # #3B4238
        border_color = (0xD2, 0xD4, 0xD8)  # #D2D4D8
        for pref in self.prefectures:
            geom = pref.get('geometry', {})
            coords = geom.get('coordinates', [])
            geom_type = geom.get('type', '')

            if geom_type == 'Polygon':
                polys = [coords[0]]
            elif geom_type == 'MultiPolygon':
                polys = [c[0] for c in coords]
            else:
                continue

            for poly in polys:
                points = [self.latlon_to_screen(lat, lon) for lon, lat in poly]
                if len(points) >= 3:
                    pygame.draw.polygon(self.screen, land_color, points)
                    pygame.draw.polygon(self.screen, border_color, points, 1)

    def handle_events(self):
        """处理事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif event.type == pygame.KEYDOWN:
                if self.setting_mode:
                    if event.key == pygame.K_UP:
                        self.temp_depth = min(700, self.temp_depth + 10)
                    elif event.key == pygame.K_DOWN:
                        self.temp_depth = max(0, self.temp_depth - 10)
                    elif event.key == pygame.K_RIGHT:
                        self.temp_mag = min(9.5, self.temp_mag + 0.1)
                    elif event.key == pygame.K_LEFT:
                        self.temp_mag = max(1.0, self.temp_mag - 0.1)
                    elif event.key == pygame.K_RETURN:
                        self.earthquake = Earthquake(
                            self.temp_lat, self.temp_lon,
                            self.temp_depth, self.temp_mag
                        )
                        self.setting_mode = False
                        self.region_intensities = {}
                        self.max_intensity = 0
                        self.detected_regions = []
                        self.intensity4_played = False
                        self.max_triggered_intensity = 0.0
                        self.alert_animations.clear()
                    elif event.key == pygame.K_r:
                        self.temp_lat = 35.7
                        self.temp_lon = 139.7
                        self.temp_depth = 10
                        self.temp_mag = 6.0
                else:
                    if event.key == pygame.K_SPACE:
                        self.paused = not self.paused
                    elif event.key == pygame.K_r:
                        self.earthquake = None
                        self.setting_mode = True
                        self.station_intensities = {}
                        self.region_max_intensities = {}
                        self.max_intensity = 0
                        self.intensity4_played = False
                        self.max_triggered_intensity = 0.0
                        self.alert_animations.clear()
                    elif event.key == pygame.K_t:
                        self.display_mode = MODE_STATION if self.display_mode == MODE_REGION else MODE_REGION
                    elif event.key == pygame.K_EQUALS or event.key == pygame.K_PLUS:
                        self.time_scale = min(10, self.time_scale * 1.5)
                    elif event.key == pygame.K_MINUS:
                        self.time_scale = max(0.1, self.time_scale / 1.5)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 左键
                    # 检查是否点击了模式按钮
                    if hasattr(self, 'mode_btn_rect') and self.mode_btn_rect.collidepoint(event.pos):
                        self.display_mode = MODE_STATION if self.display_mode == MODE_REGION else MODE_REGION
                    elif self.setting_mode:
                        lat, lon = self.screen_to_latlon(*event.pos)
                        self.temp_lat = lat
                        self.temp_lon = lon
                elif event.button == 3:  # 右键
                    if not self.setting_mode:
                        self.earthquake = None
                        self.setting_mode = True
                        self.station_intensities = {}
                        self.region_max_intensities = {}
                        self.intensity4_played = False
                elif event.button == 4:  # 滚轮向上 - 放大
                    self.zoom_map(event.pos, 1.2)
                elif event.button == 5:  # 滚轮向下 - 缩小
                    self.zoom_map(event.pos, 0.8)

            elif event.type == pygame.MOUSEWHEEL:
                # 支持现代pygame的滚轮事件
                if event.y > 0:
                    self.zoom_map(pygame.mouse.get_pos(), 1.2)
                elif event.y < 0:
                    self.zoom_map(pygame.mouse.get_pos(), 0.8)

    def run(self):
        """主循环"""
        self.station_intensities = {}
        self.region_max_intensities = {}

        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            self.handle_events()

            # 更新
            if self.earthquake and not self.paused:
                self.earthquake.update(dt * self.time_scale)
                self.calculate_station_intensities()

            # 绘制
            self.screen.fill((0x2B, 0x36, 0x45))  # 海洋颜色 #2B3645

            # 先绘制地图边界（两种模式共用）
            self.draw_map_boundaries()

            if self.display_mode == MODE_STATION:
                self.draw_stations()
            else:
                self.draw_regions_with_intensity()

            self.draw_wave_circles()
            self.draw_alert_circles()
            self.draw_earthquake_info()
            self.draw_setting_info()
            self.draw_help()
            self.draw_mode_button()

            pygame.display.flip()

        pygame.quit()

if __name__ == "__main__":
    sim = EarthquakeSimulator()
    sim.run()
