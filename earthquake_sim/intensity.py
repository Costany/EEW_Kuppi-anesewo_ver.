"""JMA震度计算模块"""
import math

def calc_jma_intensity(magnitude: float, depth: float, epicentral_distance: float, bai: float = 1.0) -> float:
    """计算计测震度（对齐 Scratch 原版）。

    参数
    - magnitude: 震级 (M)
    - depth: 震源深度 (km)
    - epicentral_distance: 震央距离 (km)（注意：Scratch 是在投影平面(km)里计算的）
    - bai: 场地倍率派生量（Scratch 的“倍率”经过变换后的值，默认 1.0）
    """
    if magnitude <= 0:
        return 0.0

    # Scratch 的 kyori 是震源距离（在平面里合成：sqrt(震央距离^2 + 深度^2)）
    kyori = math.hypot(epicentral_distance, depth)
    kyori = max(0.001, kyori)

    # Scratch: dep < 154.609... 时直接用 dep，否则用二次式近似（用于深发地震）
    if depth < 154.609339438205:
        dep_eff = depth
    else:
        dep_eff = 1.505324359113294 + 1.1346691181025712 * depth - 0.0009340019684323403 * (depth**2)

    bai = max(0.001, bai)

    # 10^(0.5*M)
    m_half_pow = 10 ** (0.5 * magnitude)

    # list[2] = 10^( 0.58*M + 0.0038*dep_eff - 1.29 - log10(kyori + 0.0028*10^(0.5*M)) - 0.002*kyori )
    denom = max(0.001, kyori + 0.0028 * m_half_pow)
    log10_base = (
        0.58 * magnitude
        + 0.0038 * dep_eff
        - 1.29
        - math.log10(denom)
        - 0.002 * kyori
    )
    base = 10 ** log10_base

    # list[3] = list[2] * 10^( 2.367 - 0.852*log10(400 / (bai * (2 + 0.1833584358*ln(bai)))) )
    bai_term = max(0.001, bai * (2.0 + 0.1833584358 * math.log(bai)))
    strength = base * (10 ** (2.367 - 0.852 * math.log10(400.0 / bai_term)))

    # 计测震度映射（低震度线性，高震度二次）
    strength = max(0.001, strength)
    l = math.log10(strength)
    intensity_hi = 2.002 + 2.603 * l - 0.213 * (l * l)
    intensity_lo = 2.165 + 2.262 * l
    intensity = intensity_hi if intensity_hi > 4.0 else intensity_lo

    return max(0.0, min(7.0, float(intensity)))

def calc_intensity_from_pga(pga: float) -> float:
    """
    从加速度计算震度
    JMA公式: I = 2 * log10(PGA) + 0.94

    pga: 地动加速度 (gal, cm/s²)
    返回: 计测震度
    """
    if pga <= 0:
        return 0
    return 2.0 * math.log10(pga) + 0.94

def intensity_to_scale(intensity: float) -> str:
    """将计测震度转换为震度阶级"""
    if intensity < 0.5:
        return "0"
    elif intensity < 1.5:
        return "1"
    elif intensity < 2.5:
        return "2"
    elif intensity < 3.5:
        return "3"
    elif intensity < 4.5:
        return "4"
    elif intensity < 5.0:
        return "5-"
    elif intensity < 5.5:
        return "5+"
    elif intensity < 6.0:
        return "6-"
    elif intensity < 6.5:
        return "6+"
    else:
        return "7"

def get_intensity_color(intensity: float) -> tuple:
    """根据震度返回颜色 (RGB)"""
    if intensity < 0.5:
        return (200, 200, 200)
    elif intensity < 1.5:
        return (100, 150, 200)
    elif intensity < 2.5:
        return (50, 180, 50)
    elif intensity < 3.5:
        return (200, 200, 0)
    elif intensity < 4.5:
        return (255, 150, 0)
    elif intensity < 5.0:
        return (255, 80, 0)
    elif intensity < 5.5:
        return (255, 0, 0)
    elif intensity < 6.0:
        return (180, 0, 50)
    elif intensity < 6.5:
        return (150, 0, 100)
    else:
        return (100, 0, 100)
