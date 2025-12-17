"""地震波传播计算模块"""
import math
from config import P_WAVE_SPEED, S_WAVE_SPEED
from projection import latlon_to_xy_km

# Scratch使用的波速常数
SCRATCH_P_SPEED = 6.5  # km/s
SCRATCH_S_SPEED = 4.0  # km/s

class Earthquake:
    def __init__(self, lat: float, lon: float, depth: float, magnitude: float):
        """
        初始化地震
        lat: 纬度
        lon: 经度
        depth: 深度 (km)
        magnitude: 震级 (M)
        """
        self.lat = lat
        self.lon = lon
        self.depth = depth
        self.magnitude = magnitude
        self.time = 0  # 发震后经过的秒数

    def get_epicentral_distance(self, lat: float, lon: float) -> float:
        """计算震央距离 (km)"""
        x0, y0 = latlon_to_xy_km(self.lat, self.lon)
        x1, y1 = latlon_to_xy_km(lat, lon)
        return math.hypot(x1 - x0, y1 - y0)

    def get_hypocentral_distance(self, lat: float, lon: float) -> float:
        """计算震源距离 (km)"""
        epicentral = self.get_epicentral_distance(lat, lon)
        return math.sqrt(epicentral**2 + self.depth**2)

    def get_p_wave_radius(self) -> float:
        """
        获取P波当前传播的震央距离半径 (km)
        Scratch公式: sqrt((6.5 * (t + depth/6.5))^2 - depth^2)
                   = sqrt((6.5*t + depth)^2 - depth^2)
        在t=0时，radius=0
        """
        # total_dist = 6.5 * t + depth
        total_dist = SCRATCH_P_SPEED * self.time + self.depth

        # 震央距离 = sqrt(总距离^2 - 深度^2)
        if total_dist <= self.depth:
            return 0
        return math.sqrt(total_dist**2 - self.depth**2)

    def get_s_wave_radius(self) -> float:
        """
        获取S波当前传播的震央距离半径 (km)
        Scratch公式: sqrt((4 * (t + depth/6.5))^2 - depth^2)
                   = sqrt((4*t + depth*4/6.5)^2 - depth^2)
        深发地震S波需要更长时间才能到达地表
        """
        # total_dist = 4 * (t + depth/6.5) = 4*t + depth*4/6.5
        total_dist = SCRATCH_S_SPEED * self.time + self.depth * SCRATCH_S_SPEED / SCRATCH_P_SPEED

        # 震央距离 = sqrt(总距离^2 - 深度^2)
        if total_dist <= self.depth:
            return 0  # S波还没到达地表
        return math.sqrt(total_dist**2 - self.depth**2)

    def get_p_arrival_time(self, lat: float, lon: float) -> float:
        """计算P波到达时间 (秒)"""
        epicentral = self.get_epicentral_distance(lat, lon)
        hypo_dist = math.sqrt(epicentral**2 + self.depth**2)
        # t = (hypo_dist - depth) / 6.5
        return (hypo_dist - self.depth) / SCRATCH_P_SPEED

    def get_s_arrival_time(self, lat: float, lon: float) -> float:
        """计算S波到达时间 (秒)"""
        epicentral = self.get_epicentral_distance(lat, lon)
        hypo_dist = math.sqrt(epicentral**2 + self.depth**2)
        # t = (hypo_dist - depth*4/6.5) / 4
        return (hypo_dist - self.depth * SCRATCH_S_SPEED / SCRATCH_P_SPEED) / SCRATCH_S_SPEED

    def update(self, dt: float):
        """更新时间"""
        self.time += dt
