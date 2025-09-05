#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SVG Output Module for Mind Maps
Generates scalable vector graphics for all mind map layouts
Provides high-quality, resolution-independent output
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple, Any
import math
import re


class SVGRenderer:
    """SVG渲染器"""
    
    def __init__(self, width: int = 800, height: int = 600, style_config=None):
        self.width = width
        self.height = height
        self.style_config = style_config
        
        # 创建SVG根元素
        self.svg = ET.Element('svg')
        self.svg.set('width', str(width))
        self.svg.set('height', str(height))
        self.svg.set('viewBox', f'0 0 {width} {height}')
        self.svg.set('xmlns', 'http://www.w3.org/2000/svg')
        
        # 添加样式定义
        self._add_styles()
        
        # 文本元素列表
        self.text_elements = []
    
    def _add_styles(self):
        """添加CSS样式定义"""
        style_content = """
        <![CDATA[
        .mind-map-text {
            font-family: 'Microsoft YaHei', 'SimHei', 'Arial Unicode MS', sans-serif;
            text-anchor: middle;
            dominant-baseline: central;
        }
        .mind-map-node {
            stroke-width: 2;
            fill: white;
            fill-opacity: 0.9;
        }
        .mind-map-line {
            fill: none;
            stroke-linecap: round;
            stroke-linejoin: round;
        }
        .shadow {
            filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.3));
        }
        ]]>
        """
        
        defs = ET.SubElement(self.svg, 'defs')
        style = ET.SubElement(defs, 'style')
        style.set('type', 'text/css')
        style.text = style_content
    
    def add_background(self, color: str = 'white'):
        """添加背景"""
        bg = ET.SubElement(self.svg, 'rect')
        bg.set('width', '100%')
        bg.set('height', '100%')
        bg.set('fill', color)
    
    def add_line(self, start: Tuple[float, float], end: Tuple[float, float], 
                 color: str = '#333333', width: float = 2, style: str = 'straight'):
        """添加连接线"""
        if style == 'straight':
            line = ET.SubElement(self.svg, 'line')
            line.set('x1', str(start[0]))
            line.set('y1', str(start[1]))
            line.set('x2', str(end[0]))
            line.set('y2', str(end[1]))
            line.set('stroke', color)
            line.set('stroke-width', str(width))
            line.set('class', 'mind-map-line')
            
        elif style == 'curved':
            self._add_curved_line(start, end, color, width)
            
        elif style == 'bezier':
            self._add_bezier_line(start, end, color, width)
    
    def _add_curved_line(self, start: Tuple[float, float], end: Tuple[float, float], 
                        color: str, width: float):
        """添加曲线"""
        x1, y1 = start
        x2, y2 = end
        
        # 计算控制点
        dx = x2 - x1
        dy = y2 - y1
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance < 1:
            return self.add_line(start, end, color, width, 'straight')
        
        control_distance = min(distance * 0.4, 50)
        
        if abs(dx) > abs(dy):
            cp1_x = x1 + control_distance * (1 if dx > 0 else -1)
            cp1_y = y1
            cp2_x = x2 - control_distance * (1 if dx > 0 else -1)
            cp2_y = y2
        else:
            cp1_x = x1
            cp1_y = y1 + control_distance * (1 if dy > 0 else -1)
            cp2_x = x2
            cp2_y = y2 - control_distance * (1 if dy > 0 else -1)
        
        path = ET.SubElement(self.svg, 'path')
        d = f'M {x1} {y1} C {cp1_x} {cp1_y}, {cp2_x} {cp2_y}, {x2} {y2}'
        path.set('d', d)
        path.set('stroke', color)
        path.set('stroke-width', str(width))
        path.set('fill', 'none')
        path.set('class', 'mind-map-line')
    
    def _add_bezier_line(self, start: Tuple[float, float], end: Tuple[float, float], 
                        color: str, width: float):
        """添加贝塞尔曲线"""
        x1, y1 = start
        x2, y2 = end
        
        dx = x2 - x1
        dy = y2 - y1
        
        cp1_x = x1 + dx * 0.3
        cp1_y = y1 + dy * 0.1
        cp2_x = x1 + dx * 0.7
        cp2_y = y1 + dy * 0.9
        
        path = ET.SubElement(self.svg, 'path')
        d = f'M {x1} {y1} C {cp1_x} {cp1_y}, {cp2_x} {cp2_y}, {x2} {y2}'
        path.set('d', d)
        path.set('stroke', color)
        path.set('stroke-width', str(width))
        path.set('fill', 'none')
        path.set('class', 'mind-map-line')
    
    def add_node(self, x: float, y: float, width: float, height: float, 
                 shape: str = 'rounded_rect', color: str = '#333333', 
                 fill_color: str = 'white', border_width: float = 2):
        """添加节点形状"""
        if shape == 'rectangle':
            rect = ET.SubElement(self.svg, 'rect')
            rect.set('x', str(x - width/2))
            rect.set('y', str(y - height/2))
            rect.set('width', str(width))
            rect.set('height', str(height))
            rect.set('fill', fill_color)
            rect.set('stroke', color)
            rect.set('stroke-width', str(border_width))
            rect.set('class', 'mind-map-node')
            
        elif shape == 'rounded_rect':
            rect = ET.SubElement(self.svg, 'rect')
            rect.set('x', str(x - width/2))
            rect.set('y', str(y - height/2))
            rect.set('width', str(width))
            rect.set('height', str(height))
            rect.set('rx', '5')
            rect.set('ry', '5')
            rect.set('fill', fill_color)
            rect.set('stroke', color)
            rect.set('stroke-width', str(border_width))
            rect.set('class', 'mind-map-node')
            
        elif shape == 'circle':
            radius = min(width, height) / 2
            circle = ET.SubElement(self.svg, 'circle')
            circle.set('cx', str(x))
            circle.set('cy', str(y))
            circle.set('r', str(radius))
            circle.set('fill', fill_color)
            circle.set('stroke', color)
            circle.set('stroke-width', str(border_width))
            circle.set('class', 'mind-map-node')
            
        elif shape == 'ellipse':
            ellipse = ET.SubElement(self.svg, 'ellipse')
            ellipse.set('cx', str(x))
            ellipse.set('cy', str(y))
            ellipse.set('rx', str(width/2))
            ellipse.set('ry', str(height/2))
            ellipse.set('fill', fill_color)
            ellipse.set('stroke', color)
            ellipse.set('stroke-width', str(border_width))
            ellipse.set('class', 'mind-map-node')
            
        elif shape == 'diamond':
            points = [
                (x, y - height/2),  # 上
                (x + width/2, y),   # 右
                (x, y + height/2),  # 下
                (x - width/2, y)    # 左
            ]
            polygon = ET.SubElement(self.svg, 'polygon')
            polygon.set('points', ' '.join([f'{px},{py}' for px, py in points]))
            polygon.set('fill', fill_color)
            polygon.set('stroke', color)
            polygon.set('stroke-width', str(border_width))
            polygon.set('class', 'mind-map-node')
    
    def add_text(self, x: float, y: float, text: str, font_size: int = 14, 
                 color: str = '#333333', font_weight: str = 'normal',
                 anchor: str = 'middle'):
        """添加文本"""
        text_elem = ET.SubElement(self.svg, 'text')
        text_elem.set('x', str(x))
        text_elem.set('y', str(y))
        text_elem.set('font-size', str(font_size))
        text_elem.set('fill', color)
        text_elem.set('font-weight', font_weight)
        text_elem.set('text-anchor', anchor)
        text_elem.set('dominant-baseline', 'central')
        text_elem.set('class', 'mind-map-text')
        text_elem.text = text
        
        # 存储文本信息用于计算布局
        self.text_elements.append({
            'x': x, 'y': y, 'text': text, 'font_size': font_size,
            'element': text_elem
        })
    
    def add_multiline_text(self, x: float, y: float, text: str, font_size: int = 14,
                          color: str = '#333333', max_width: float = 200):
        """添加多行文本"""
        lines = self._wrap_text(text, max_width, font_size)
        line_height = font_size * 1.2
        
        start_y = y - (len(lines) - 1) * line_height / 2
        
        for i, line in enumerate(lines):
            line_y = start_y + i * line_height
            self.add_text(x, line_y, line, font_size, color)
    
    def _wrap_text(self, text: str, max_width: float, font_size: int) -> List[str]:
        """文本换行"""
        # 简单的字符数量估算换行
        char_width = font_size * 0.6  # 估算每个字符宽度
        max_chars = int(max_width / char_width)
        
        if len(text) <= max_chars:
            return [text]
        
        lines = []
        words = text.split()
        current_line = ""
        
        for word in words:
            if len(current_line + word) <= max_chars:
                current_line += word + " "
            else:
                if current_line:
                    lines.append(current_line.strip())
                current_line = word + " "
        
        if current_line:
            lines.append(current_line.strip())
        
        return lines
    
    def add_title(self, title: str, font_size: int = 24):
        """添加标题"""
        self.add_text(self.width / 2, 30, title, font_size, '#333333', 'bold')
    
    def save(self, filename: str) -> str:
        """保存SVG文件"""
        # 美化XML输出
        self._indent(self.svg)
        
        tree = ET.ElementTree(self.svg)
        tree.write(filename, encoding='utf-8', xml_declaration=True)
        
        return filename
    
    def to_string(self) -> str:
        """转换为SVG字符串"""
        self._indent(self.svg)
        return ET.tostring(self.svg, encoding='unicode')
    
    def _indent(self, elem, level=0):
        """美化XML格式"""
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self._indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i


class SVGMindMapConverter:
    """SVG思维导图转换器"""
    
    def __init__(self, style_config=None):
        self.style_config = style_config
    
    def convert_center_layout(self, tree_data: dict, width: int = 1200, height: int = 800) -> str:
        """转换中心布局为SVG"""
        renderer = SVGRenderer(width, height, self.style_config)
        renderer.add_background('white')
        
        center_x = width / 2
        center_y = height / 2
        
        # 简化的中心布局算法
        self._draw_center_node(renderer, tree_data, center_x, center_y, 0, 0)
        
        return renderer.to_string()
    
    def convert_horizontal_layout(self, tree_data: dict, width: int = 1200, height: int = 800) -> str:
        """转换水平布局为SVG"""
        renderer = SVGRenderer(width, height, self.style_config)
        renderer.add_background('white')
        
        # 简化的水平布局算法
        self._draw_horizontal_node(renderer, tree_data, 100, height/2, 1)
        
        return renderer.to_string()
    
    def convert_vertical_layout(self, tree_data: dict, width: int = 1200, height: int = 800) -> str:
        """转换垂直布局为SVG"""
        renderer = SVGRenderer(width, height, self.style_config)
        renderer.add_background('white')
        
        # 简化的垂直布局算法
        self._draw_vertical_node(renderer, tree_data, width/2, 100, 1)
        
        return renderer.to_string()
    
    def convert_fishbone_layout(self, fishbone_data: dict, width: int = 1200, height: int = 800) -> str:
        """转换鱼骨图为SVG"""
        renderer = SVGRenderer(width, height, self.style_config)
        renderer.add_background('white')
        
        # 绘制鱼骨图主干
        spine_start_x = 100
        spine_end_x = width - 200
        spine_y = height / 2
        
        renderer.add_line((spine_start_x, spine_y), (spine_end_x, spine_y), '#333333', 4)
        
        # 绘制问题/效果
        problem = fishbone_data.get('problem', '问题')
        renderer.add_text(spine_end_x + 50, spine_y, problem, 18, '#333333', 'bold')
        
        # 绘制分类分支
        categories = fishbone_data.get('categories', [])
        for i, category in enumerate(categories):
            is_upper = i % 2 == 0
            side = 1 if is_upper else -1
            
            branch_x = spine_start_x + (i + 1) * (spine_end_x - spine_start_x) / (len(categories) + 1)
            branch_end_y = spine_y + side * 100
            
            renderer.add_line((branch_x, spine_y), (branch_x + 80, branch_end_y), '#4ECDC4', 3)
            renderer.add_text(branch_x + 90, branch_end_y, category['name'], 14, '#4ECDC4')
        
        return renderer.to_string()
    
    def _draw_center_node(self, renderer: SVGRenderer, node: dict, x: float, y: float, 
                         depth: int, angle_offset: float):
        """绘制中心布局节点"""
        content = node.get('content', 'Node')
        children = node.get('children', [])
        
        # 计算节点大小
        font_size = max(16 - depth * 2, 10)
        text_width = len(content) * font_size * 0.6
        text_height = font_size * 1.5
        
        # 绘制节点
        renderer.add_node(x, y, text_width + 20, text_height + 10, 'rounded_rect', '#FF6B6B')
        renderer.add_text(x, y, content, font_size, '#333333')
        
        # 绘制子节点
        if children:
            num_children = len(children)
            angle_step = 2 * math.pi / num_children
            radius = 120 + depth * 40
            
            for i, child in enumerate(children):
                child_angle = angle_offset + i * angle_step
                child_x = x + radius * math.cos(child_angle)
                child_y = y + radius * math.sin(child_angle)
                
                renderer.add_line((x, y), (child_x, child_y), '#666666', 2, 'curved')
                self._draw_center_node(renderer, child, child_x, child_y, depth + 1, child_angle)
    
    def _draw_horizontal_node(self, renderer: SVGRenderer, node: dict, x: float, y: float, depth: int):
        """绘制水平布局节点"""
        content = node.get('content', 'Node')
        children = node.get('children', [])
        
        # 计算节点大小
        font_size = max(16 - depth * 2, 10)
        text_width = len(content) * font_size * 0.6
        text_height = font_size * 1.5
        
        # 绘制节点
        color = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'][depth % 4]
        renderer.add_node(x, y, text_width + 20, text_height + 10, 'rounded_rect', color)
        renderer.add_text(x, y, content, font_size, '#333333')
        
        # 绘制子节点
        if children:
            child_x = x + 150
            start_y = y - (len(children) - 1) * 40 / 2
            
            for i, child in enumerate(children):
                child_y = start_y + i * 40
                renderer.add_line((x, y), (child_x, child_y), '#666666', 2, 'curved')
                self._draw_horizontal_node(renderer, child, child_x, child_y, depth + 1)
    
    def _draw_vertical_node(self, renderer: SVGRenderer, node: dict, x: float, y: float, depth: int):
        """绘制垂直布局节点"""
        content = node.get('content', 'Node')
        children = node.get('children', [])
        
        # 计算节点大小
        font_size = max(16 - depth * 2, 10)
        text_width = len(content) * font_size * 0.6
        text_height = font_size * 1.5
        
        # 绘制节点
        color = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'][depth % 4]
        renderer.add_node(x, y, text_width + 20, text_height + 10, 'rounded_rect', color)
        renderer.add_text(x, y, content, font_size, '#333333')
        
        # 绘制子节点
        if children:
            child_y = y + 100
            start_x = x - (len(children) - 1) * 120 / 2
            
            for i, child in enumerate(children):
                child_x = start_x + i * 120
                renderer.add_line((x, y), (child_x, child_y), '#666666', 2, 'straight')
                self._draw_vertical_node(renderer, child, child_x, child_y, depth + 1)