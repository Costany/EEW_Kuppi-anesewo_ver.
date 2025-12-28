#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并Scratch项目的站点数据，添加小笠原（父岛）等缺失站点
"""

import json
import os

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. 加载当前站点数据
    current_path = os.path.join(base_dir, 'earthquake_sim', 'stations_data.json')
    print(f"加载当前站点: {current_path}")
    with open(current_path, 'r', encoding='utf-8') as f:
        current_stations = json.load(f)
    print(f"  当前站点数: {len(current_stations)}")

    # 2. 加载v1.10项目的JMA站点
    v110_path = os.path.join(base_dir, '強震モニタ風地震シュミレーション v1.10', 'project', 'project.json')
    print(f"\n加载v1.10项目JMA站点...")

    with open(v110_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 找到JMA的经纬度列表（4587个站点）
    lat_list = None
    lon_list = None

    targets = data.get('targets', [])
    for t in targets:
        lists = t.get('lists', {})
        for list_id, list_info in lists.items():
            if isinstance(list_info, list) and len(list_info) >= 2:
                values = list_info[1]
                if len(values) == 4587:
                    try:
                        first_val = float(values[0])
                        if 25 < first_val < 50:  # 纬度
                            lat_list = values
                        elif 120 < first_val < 155:  # 经度
                            lon_list = values
                    except:
                        pass

    if not lat_list or not lon_list:
        print("  错误：未找到JMA站点数据")
        return

    # 3. 从JMA中提取当前缺失的站点
    # 查找小笠原区域 (lat 26-28, lon 141-143) 和其他可能缺失的区域
    missing_stations = []

    for i in range(len(lat_list)):
        try:
            lat = float(lat_list[i])
            lon = float(lon_list[i])
        except:
            continue

        # 检查是否在当前数据中已存在（允许0.01度误差）
        exists = False
        for s in current_stations:
            if abs(s['lat'] - lat) < 0.01 and abs(s['lon'] - lon) < 0.01:
                exists = True
                break

        if not exists:
            # 只添加日本范围内的站点
            if 24 <= lat <= 46 and 122 <= lon <= 154:
                missing_stations.append({
                    'id': len(current_stations) + len(missing_stations),
                    'lat': lat,
                    'lon': lon,
                    'name': f'JMA_{i}',
                    'source': 'JMA'
                })

    print(f"  找到 {len(missing_stations)} 个缺失站点")

    # 4. 检查小笠原区域
    ogasawara_missing = [s for s in missing_stations if 26 <= s['lat'] <= 28 and 141 <= s['lon'] <= 143]
    print(f"\n小笠原区域新增站点: {len(ogasawara_missing)}")
    for s in ogasawara_missing:
        print(f"  {s['lat']:.4f}, {s['lon']:.4f}")

    # 5. 合并并保存
    merged = current_stations + missing_stations

    # 重新编号
    for i, s in enumerate(merged):
        s['id'] = i

    output_path = os.path.join(base_dir, 'earthquake_sim', 'stations_data.json')

    # 备份原文件
    backup_path = output_path + '.backup'
    with open(current_path, 'r', encoding='utf-8') as f:
        original = f.read()
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(original)
    print(f"\n原文件已备份到: {backup_path}")

    # 保存合并后的文件
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"保存到: {output_path}")
    print(f"总站点数: {len(merged)} (原{len(current_stations)} + 新{len(missing_stations)})")

    # 6. 验证
    final_ogasawara = [s for s in merged if 26 <= s['lat'] <= 28 and 141 <= s['lon'] <= 143]
    print(f"\n验证 - 小笠原区域站点: {len(final_ogasawara)}")

if __name__ == '__main__':
    main()
