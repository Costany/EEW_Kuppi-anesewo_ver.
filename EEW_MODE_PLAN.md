# EEW模式扩展计划 (Earthquake Early Warning Mode)

## 可行性评估：✅ 完全可行

### 为什么可行？

1. **现有架构完全支持扩展**
   - 已有 `get_p_arrival_time()` 和 `get_s_arrival_time()` 函数 (earthquake.py)
   - 已有 `calc_jma_intensity()` 完整震度计算 (intensity.py)
   - 已有多震源管理器 `MultiSourceManager` 支持多源聚合 (multisource.py)

2. **不需要修改源码核心逻辑**
   - 通过**继承** (`subclassing`) 扩展 `EarthquakeSimulator`
   - 新增独立入口或模式切换逻辑
   - UI、地图渲染复用现有代码

3. **满足"回落"需求**
   - 引入**时间包络 (Time Envelope)** 模型
   - 实现震度随时间的 `Rise (上升)` -> `Peak (峰值)` -> `Decay (衰减)` 过程
   - 支持多震源的复杂波形叠加（包络叠加或取最大值）

---

## 核心设计思路：震度包络模型 (Intensity Envelope Model)

为了实现"震度从高回落"的效果，我们不能只计算单一的峰值震度，而是要计算**任意时刻 t 的瞬时震度** `I(t)`。

### 1. 包络函数设计

我们需要两个独立的包络函数：P波包络和S波包络。

#### P波包络 (P-wave Envelope)
P波通常较弱，到达快，衰减也相对较快。
为了防止P波震度一直维持在高位，必须引入**衰减项**。

$$ I_P(t) = I_{P,peak} \times \text{Attack}(t, t_P, \tau_{P,rise}) \times \text{Decay}(t, t_P, \tau_{P,decay}) $$

- **$t_P$**: P波到达时间
- **$I_{P,peak}$**: P波峰值预测值 (约 $I_{S,peak} - 1.5$ 或 $/1.5$)
- **形态**: 快速上升，随即缓慢衰减。

**代码简化模型**:
```python
if t < tP:
    val = 0
else:
    dt = t - tP
    # Rise: 1 - exp(-dt/rise)  | Decay: exp(-dt/decay)
    # 组合: 先升后降
    val = I_P_peak * (1 - math.exp(-dt / 0.5)) * math.exp(-dt / 10.0)
```

#### S波包络 (S-wave Envelope)
S波是主震，能量强，持续时间长（Coda wave）。

$$ I_S(t) = I_{S,peak} \times \text{Attack}(t, t_S, \tau_{S,rise}) \times \text{Decay}(t, t_S, \tau_{S,decay}) $$

- **$t_S$**: S波到达时间
- **$I_{S,peak}$**: S波峰值预测值 (标准震度公式计算值)
- **$	au_{S,decay}$**: 关键参数，决定震动持续多久。需根据震级(M)和距离(R)动态计算。

**代码简化模型**:
```python
if t < tS:
    val = 0
else:
    dt = t - tS
    # Rise: S波上升通常也很快，但不是瞬时，设为 1.0s 左右
    # Decay: 动态计算 tau_s
    val = I_S_peak * (1 - math.exp(-dt / 1.0)) * math.exp(-dt / tau_s)
```

#### 最终显示震度
$$ I_{display}(t) = \max(I_P(t), I_S(t)) $$
*注意：这样可以保证当S波过去很久后，震度会趋近于0，实现"回落"效果。*

---


### 2. 动态衰减常数 ($	au_S$)

为了模拟大地震震动时间长，小地震震动时间短的物理特性：

```python
def get_decay_constant(magnitude, distance, amp):
    # 基础衰减 (秒)
    base = 3.0 
    
    # 震级影响: M越大，断层破裂时间越长，尾波越长
    # M6 -> +5s, M7 -> +10s, M9 -> +25s
    mag_factor = (magnitude - 5.0) * 5.0 if magnitude > 5 else 0
    
    # 距离影响: 距离越远，高频衰减，低频长周期波占主导，持续时间拉长
    dist_factor = distance * 0.05 
    
    # 场地影响: 软土(amp大)容易产生共振，延长震动
    amp_factor = (amp - 1.0) * 2.0
    
    return base + mag_factor + dist_factor + amp_factor
```

---

## 功能实现模式：双模式切换 (Selectable Modes)

用户需要在"最大震度保持"（现有模式）和"实时震度衰减"（新模式）之间切换。

### 方案 A：运行时切换 (推荐)
在主界面增加键盘快捷键（如 `D` - Decay Mode）或在配置中设置。

1. **Max Hold Mode (默认)**: 
   - 逻辑: `Display_I = max(Previous_I, Current_I)`
   - 表现: 震度只升不降，记录历史最大值。
   - 用途: 灾后报告，确认各地最大受害程度。

2. **Real-time Decay Mode (新功能)**:
   - 逻辑: `Display_I = Current_Instant_I`
   - 表现: 震度随波形起伏，波过后归零。
   - 用途: 模拟真实体感，观察多震源的波次叠加。

### 数据结构扩展
在 `EarthquakeSimulator` 类中：

```python
class EEWSimulator(EarthquakeSimulator):
    def __init__(self):
        super().__init__()
        self.mode = "REALTIME" # or "MAX_HOLD"
        self.station_max_history = {} # 记录每个站点历史最大值(用于Max Hold模式)

    def calculate_intensities(self):
        # ... 计算出 instant_intensity ...
        
        if self.mode == "MAX_HOLD":
            # 更新历史最大
            self.station_max_history[id] = max(self.station_max_history.get(id, 0), instant_intensity)
            final_intensity = self.station_max_history[id]
        else:
            # 实时模式直接使用瞬时值
            final_intensity = instant_intensity
            
        # ... 更新UI ...
```

---

## 实施细节检查清单 (Checklist)

### 1. 物理真实性细节
- [ ] **P波衰减**: 必须添加 P 波衰减项。如果 P 波不衰减，当 S 波衰减后，震度会卡在 P 波的强度无法归零。
- [ ] **S波上升**: 建议给 S 波 0.5s~1.0s 的上升缓冲，避免震度突变看起来像 BUG。
- [ ] **多震源叠加**: 
    - 简单的 `max(source1, source2)` 即可。
    - 如果两个震波同时到达，物理上能量会叠加，但在震度计模拟中，取最大值通常足够近似且稳定。

### 2. 性能优化
- [ ] **Exp计算**: `math.exp` 很耗时。
    - 优化：预计算查找表，或者仅对 `intensity > 0.5` 的站点进行精细计算。
    - 距离过远的站点（如 `intensity_peak < 0.5`）直接跳过计算。

### 3. UI/UX 细节
- [ ] **颜色映射**: 震度回落时，站点颜色应同步从"红/紫"变回"蓝/绿/灰"。
- [ ] **左上角信息**: 
    - Real-time 模式下，左上角显示的是"当前最高震度"还是"历史最高震度"？
    - **建议**: 左上角始终保留显示"历史最大震度 (Max Int)"，但在地图上动态显示实时颜色。或者分两行显示。

### 4. 扩展性接口
- [ ] **地震事件选择**: 
    - 代码应支持从列表加载不同的 `Earthquake` 对象（目前是硬编码或随机）。
    - 允许通过按键触发新的地震（用于测试多震源）。

---

## 待办事项 (TODO)

1.  **创建 `eew_calculator.py`**: 实现带衰减的 `calc_intensity_at_time(t)` 函数。
2.  **更新 `config.py`**: 添加 `EEW_MODE` 开关和衰减参数配置。
3.  **修改主循环**: 集成模式切换逻辑。
4.  **测试**: 
    - 验证 M9.0 地震在 300km 外是否有长周期的摇晃（衰减慢）。
    - 验证 M4.0 地震是否快速结束（衰减快）。

---

## 结论

此计划修正了原设计中 P 波不衰减导致无法归零的问题，并明确了双模式切换的实现路径。通过引入 Rise/Decay 包络，可以完美模拟地震波过后的平静过程。