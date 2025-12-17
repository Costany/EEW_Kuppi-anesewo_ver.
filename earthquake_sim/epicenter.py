"""震央地名定位模块"""
import json
import os

class EpicenterLocator:
    def __init__(self, geojson_path: str = None):
        """加载震央地名GeoJSON数据"""
        self.regions = []
        if geojson_path and os.path.exists(geojson_path):
            self.load_geojson(geojson_path)

    def load_geojson(self, path: str):
        """加载GeoJSON文件"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for feature in data.get('features', []):
            props = feature.get('properties', {})
            geom = feature.get('geometry', {})

            region = {
                'id': props.get('id', ''),
                'name': props.get('name', ''),
                'name_zh': props.get('name_zh-cn', props.get('name', '')),
                'name_en': props.get('name_en', ''),
                'geometry': geom
            }
            self.regions.append(region)

    def point_in_polygon(self, lon: float, lat: float, polygon: list) -> bool:
        """射线法判断点是否在多边形内"""
        n = len(polygon)
        inside = False

        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]

            if ((yi > lat) != (yj > lat)) and \
               (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
                inside = not inside
            j = i

        return inside

    def get_location_name(self, lon: float, lat: float, lang: str = 'zh') -> str:
        """根据经纬度获取震央地名"""
        for region in self.regions:
            geom = region['geometry']
            geom_type = geom.get('type', '')
            coords = geom.get('coordinates', [])

            found = False
            if geom_type == 'Polygon':
                if self.point_in_polygon(lon, lat, coords[0]):
                    found = True
            elif geom_type == 'MultiPolygon':
                for poly in coords:
                    if self.point_in_polygon(lon, lat, poly[0]):
                        found = True
                        break

            if found:
                if lang == 'zh':
                    return region['name_zh'] or region['name']
                elif lang == 'en':
                    return region['name_en'] or region['name']
                else:
                    return region['name']

        return "未知区域"
