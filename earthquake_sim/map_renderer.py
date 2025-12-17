"""日本地图渲染模块"""
import json
import os

class MapRenderer:
    def __init__(self, geojson_path: str = None):
        """加载地图数据"""
        self.polygons = []
        if geojson_path and os.path.exists(geojson_path):
            self.load_geojson(geojson_path)

    def load_geojson(self, path: str):
        """从GeoJSON加载多边形"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for feature in data.get('features', []):
            geom = feature.get('geometry', {})
            geom_type = geom.get('type', '')
            coords = geom.get('coordinates', [])

            if geom_type == 'Polygon':
                self.polygons.append(coords[0])
            elif geom_type == 'MultiPolygon':
                for poly in coords:
                    self.polygons.append(poly[0])

    def draw(self, screen, latlon_to_screen_func, color=(60, 60, 80)):
        """绘制地图边界"""
        import pygame
        for polygon in self.polygons:
            if len(polygon) < 3:
                continue
            points = []
            for lon, lat in polygon:
                x, y = latlon_to_screen_func(lat, lon)
                points.append((x, y))
            if len(points) >= 3:
                pygame.draw.polygon(screen, color, points, 1)
