"""Scratch 兼容的经纬度→平面(km)投影与反算。

Scratch 原版项目在绘图与距离计算时，先把经纬度转换到一个近似等距的平面坐标系（单位近似为 km），
再在该平面里用欧氏距离画波前与判断到达时间，因此波前在屏幕上是正圆。
"""

from __future__ import annotations

import math

from config import SCRATCH_MERCATOR_Y_SCALE, SCRATCH_REF_LAT, SCRATCH_REF_LON, SCRATCH_X_KM_PER_DEG


def _mercator_lat_term(lat_deg: float) -> float:
    """返回 0.5*ln((1+sinφ)/(1-sinφ))，其中 φ 为纬度（度）。"""
    sin_phi = math.sin(math.radians(lat_deg))
    # 数值保护：避免 1±sin_phi 为 0 导致溢出
    sin_phi = max(-0.999999999999, min(0.999999999999, sin_phi))
    return 0.5 * math.log((1.0 + sin_phi) / (1.0 - sin_phi))


_REF_MERCATOR_TERM = _mercator_lat_term(SCRATCH_REF_LAT)


def latlon_to_xy_km(lat_deg: float, lon_deg: float) -> tuple[float, float]:
    """经纬度(度) → 平面坐标(km)。"""
    x_km = (lon_deg - SCRATCH_REF_LON) * SCRATCH_X_KM_PER_DEG
    y_km = (_mercator_lat_term(lat_deg) - _REF_MERCATOR_TERM) * SCRATCH_MERCATOR_Y_SCALE
    return x_km, y_km


def xy_km_to_latlon(x_km: float, y_km: float) -> tuple[float, float]:
    """平面坐标(km) → 经纬度(度)。"""
    lon = x_km / SCRATCH_X_KM_PER_DEG + SCRATCH_REF_LON

    merc = y_km / SCRATCH_MERCATOR_Y_SCALE + _REF_MERCATOR_TERM
    # merc = atanh(sin(phi))  =>  sin(phi) = tanh(merc)  =>  phi = asin(tanh(merc))
    sin_phi = math.tanh(merc)
    sin_phi = max(-1.0, min(1.0, sin_phi))
    lat = math.degrees(math.asin(sin_phi))
    return lat, lon

