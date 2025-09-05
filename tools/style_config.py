#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mind Map Style Configuration System
Supports customizable colors, node shapes, line styles, fonts, and backgrounds
"""

from enum import Enum
from typing import Dict, Any, Tuple, List
from dataclasses import dataclass


class NodeShape(Enum):
    """节点形状枚举"""
    RECTANGLE = "rectangle"
    ROUNDED_RECTANGLE = "rounded_rectangle"
    CIRCLE = "circle"
    ELLIPSE = "ellipse"
    DIAMOND = "diamond"
    HEXAGON = "hexagon"


class LineStyle(Enum):
    """连线样式枚举"""
    STRAIGHT = "straight"
    CURVED = "curved"
    BEZIER = "bezier"
    STEPPED = "stepped"


class ColorScheme(Enum):
    """颜色方案枚举"""
    DEFAULT = "default"
    BUSINESS = "business"
    CREATIVE = "creative"
    ACADEMIC = "academic"
    DARK = "dark"
    COLORFUL = "colorful"
    PASTEL = "pastel"
    MONOCHROME = "monochrome"


@dataclass
class StyleConfig:
    """样式配置类"""
    # 节点样式
    node_shape: NodeShape = NodeShape.ROUNDED_RECTANGLE
    node_border_width: int = 4
    node_padding: int = 12
    node_shadow: bool = True
    
    # 文字样式
    font_size_base: int = 26
    font_size_scaling: float = 0.8  # 每级递减比例
    font_weight: str = "normal"  # normal, bold
    font_family: str = "default"
    
    # 颜色方案
    color_scheme: ColorScheme = ColorScheme.DEFAULT
    background_color: str = "white"
    
    # 连线样式
    line_style: LineStyle = LineStyle.CURVED
    line_width_base: int = 3
    line_opacity: float = 0.8
    
    # 布局参数
    node_spacing: float = 1.5  # 节点间距倍数
    level_spacing: float = 2.0  # 层级间距倍数
    
    # 自定义颜色
    custom_colors: List[str] = None


class ColorSchemes:
    """预定义颜色方案"""
    
    SCHEMES = {
        ColorScheme.DEFAULT: {
            'branch_colors': [
                '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', 
                '#FECA57', '#FF9FF3', '#54A0FF', '#5F27CD'
            ],
            'background': 'white',
            'text_color': '#333333',
            'border_color': '#333333'
        },
        
        ColorScheme.BUSINESS: {
            'branch_colors': [
                '#2C3E50', '#34495E', '#3498DB', '#2980B9',
                '#1ABC9C', '#16A085', '#27AE60', '#229954'
            ],
            'background': '#F8F9FA',
            'text_color': '#2C3E50',
            'border_color': '#34495E'
        },
        
        ColorScheme.CREATIVE: {
            'branch_colors': [
                '#E74C3C', '#F39C12', '#F1C40F', '#2ECC71',
                '#3498DB', '#9B59B6', '#E67E22', '#E91E63'
            ],
            'background': '#FFF8E1',
            'text_color': '#8E24AA',
            'border_color': '#E65100'
        },
        
        ColorScheme.ACADEMIC: {
            'branch_colors': [
                '#37474F', '#546E7A', '#607D8B', '#78909C',
                '#90A4AE', '#B0BEC5', '#CFD8DC', '#ECEFF1'
            ],
            'background': '#FAFAFA',
            'text_color': '#263238',
            'border_color': '#455A64'
        },
        
        ColorScheme.DARK: {
            'branch_colors': [
                '#FF5722', '#FF9800', '#FFC107', '#CDDC39',
                '#8BC34A', '#4CAF50', '#009688', '#00BCD4'
            ],
            'background': '#263238',
            'text_color': '#FFFFFF',
            'border_color': '#37474F'
        },
        
        ColorScheme.COLORFUL: {
            'branch_colors': [
                '#FF1744', '#FF6D00', '#FFD600', '#00E676',
                '#00B0FF', '#651FFF', '#FF4081', '#1DE9B6'
            ],
            'background': 'white',
            'text_color': '#212121',
            'border_color': '#424242'
        },
        
        ColorScheme.PASTEL: {
            'branch_colors': [
                '#FFCDD2', '#F8BBD9', '#E1BEE7', '#C5CAE9',
                '#BBDEFB', '#B3E5FC', '#B2EBF2', '#B2DFDB'
            ],
            'background': '#FAFAFA',
            'text_color': '#424242',
            'border_color': '#757575'
        },
        
        ColorScheme.MONOCHROME: {
            'branch_colors': [
                '#212121', '#424242', '#616161', '#757575',
                '#9E9E9E', '#BDBDBD', '#E0E0E0', '#EEEEEE'
            ],
            'background': 'white',
            'text_color': '#212121',
            'border_color': '#424242'
        }
    }
    
    @classmethod
    def get_colors(cls, scheme: ColorScheme) -> Dict[str, Any]:
        """获取指定配色方案的颜色"""
        return cls.SCHEMES.get(scheme, cls.SCHEMES[ColorScheme.DEFAULT])


class StyleRenderer:
    """样式渲染器"""
    
    def __init__(self, config: StyleConfig):
        self.config = config
        self.colors = ColorSchemes.get_colors(config.color_scheme)
        
    def get_node_style(self, depth_level: int) -> Dict[str, Any]:
        """获取节点样式"""
        # 计算字体大小
        font_size = max(
            int(self.config.font_size_base * (self.config.font_size_scaling ** (depth_level - 1))),
            12
        )
        
        # 计算内边距
        padding = max(self.config.node_padding - (depth_level - 1) * 2, 6)
        
        # 计算边框宽度
        border_width = max(self.config.node_border_width - (depth_level - 1), 2)
        
        return {
            'font_size': font_size,
            'padding': padding,
            'border_width': border_width,
            'shape': self.config.node_shape,
            'shadow': self.config.node_shadow
        }
    
    def get_line_style(self, depth_level: int) -> Dict[str, Any]:
        """获取连线样式"""
        # 计算线宽
        line_width = max(self.config.line_width_base - (depth_level - 1), 1)
        
        return {
            'style': self.config.line_style,
            'width': line_width,
            'opacity': self.config.line_opacity
        }
    
    def get_color(self, branch_index: int) -> str:
        """获取分支颜色"""
        if self.config.custom_colors:
            colors = self.config.custom_colors
        else:
            colors = self.colors['branch_colors']
        
        return colors[branch_index % len(colors)]
    
    def get_text_color(self) -> str:
        """获取文字颜色"""
        return self.colors['text_color']
    
    def get_background_color(self) -> str:
        """获取背景颜色"""
        if self.config.background_color != 'white':
            return self.config.background_color
        return self.colors['background']
    
    def draw_node_shape(self, draw, bbox: Tuple[int, int, int, int], 
                       color: str, style: Dict[str, Any]):
        """绘制节点形状"""
        x1, y1, x2, y2 = bbox
        shape = style['shape']
        border_width = style['border_width']
        
        if shape == NodeShape.RECTANGLE:
            draw.rectangle([x1, y1, x2, y2], 
                         fill='white', outline=color, width=border_width)
                         
        elif shape == NodeShape.ROUNDED_RECTANGLE:
            draw.rounded_rectangle([x1, y1, x2, y2], 
                                 radius=5, fill='white', outline=color, width=border_width)
                                 
        elif shape == NodeShape.CIRCLE:
            # 确保是圆形
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            radius = min((x2 - x1) // 2, (y2 - y1) // 2)
            draw.ellipse([center_x - radius, center_y - radius, 
                         center_x + radius, center_y + radius],
                        fill='white', outline=color, width=border_width)
                        
        elif shape == NodeShape.ELLIPSE:
            draw.ellipse([x1, y1, x2, y2], 
                        fill='white', outline=color, width=border_width)
                        
        elif shape == NodeShape.DIAMOND:
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            width = x2 - x1
            height = y2 - y1
            points = [
                (center_x, y1),          # 上
                (x2, center_y),          # 右
                (center_x, y2),          # 下
                (x1, center_y)           # 左
            ]
            draw.polygon(points, fill='white', outline=color, width=border_width)
            
        elif shape == NodeShape.HEXAGON:
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            width = x2 - x1
            height = y2 - y1
            offset_x = width // 4
            points = [
                (x1 + offset_x, y1),     # 左上
                (x2 - offset_x, y1),     # 右上
                (x2, center_y),          # 右
                (x2 - offset_x, y2),     # 右下
                (x1 + offset_x, y2),     # 左下
                (x1, center_y)           # 左
            ]
            draw.polygon(points, fill='white', outline=color, width=border_width)
    
    def draw_connection_line(self, ax, start_pos: Tuple[float, float], 
                           end_pos: Tuple[float, float], color: str, 
                           style: Dict[str, Any]):
        """绘制连接线"""
        import numpy as np
        import math
        
        start_x, start_y = start_pos
        end_x, end_y = end_pos
        line_style = style['style']
        line_width = style['width']
        opacity = style['opacity']
        
        if line_style == LineStyle.STRAIGHT:
            ax.plot([start_x, end_x], [start_y, end_y], 
                   color=color, linewidth=line_width, alpha=opacity)
                   
        elif line_style == LineStyle.CURVED:
            self._draw_curved_line(ax, start_x, start_y, end_x, end_y, 
                                 color, line_width, opacity)
                                 
        elif line_style == LineStyle.BEZIER:
            self._draw_bezier_line(ax, start_x, start_y, end_x, end_y, 
                                 color, line_width, opacity)
                                 
        elif line_style == LineStyle.STEPPED:
            self._draw_stepped_line(ax, start_x, start_y, end_x, end_y, 
                                  color, line_width, opacity)
    
    def _draw_curved_line(self, ax, start_x, start_y, end_x, end_y, 
                         color, width, opacity):
        """绘制曲线"""
        import numpy as np
        import math
        
        dx = end_x - start_x
        dy = end_y - start_y
        distance = math.sqrt(dx*dx + dy*dy)
        
        if distance < 0.1:
            ax.plot([start_x, end_x], [start_y, end_y], 
                   color=color, linewidth=width, alpha=opacity)
            return
        
        control_distance = min(distance * 0.4, 2.0)
        
        if abs(dx) > abs(dy):
            cp1_x = start_x + control_distance * (1 if dx > 0 else -1)
            cp1_y = start_y
            cp2_x = end_x - control_distance * (1 if dx > 0 else -1)
            cp2_y = end_y
        else:
            cp1_x = start_x
            cp1_y = start_y + control_distance * (1 if dy > 0 else -1)
            cp2_x = end_x
            cp2_y = end_y - control_distance * (1 if dy > 0 else -1)
        
        t = np.linspace(0, 1, 50)
        curve_x = (1-t)**3 * start_x + 3*(1-t)**2*t * cp1_x + 3*(1-t)*t**2 * cp2_x + t**3 * end_x
        curve_y = (1-t)**3 * start_y + 3*(1-t)**2*t * cp1_y + 3*(1-t)*t**2 * cp2_y + t**3 * end_y
        
        ax.plot(curve_x, curve_y, color=color, linewidth=width, alpha=opacity)
    
    def _draw_bezier_line(self, ax, start_x, start_y, end_x, end_y, 
                         color, width, opacity):
        """绘制贝塞尔曲线"""
        import numpy as np
        
        # 更平滑的贝塞尔曲线控制点
        dx = end_x - start_x
        dy = end_y - start_y
        
        cp1_x = start_x + dx * 0.3
        cp1_y = start_y + dy * 0.1
        cp2_x = start_x + dx * 0.7
        cp2_y = start_y + dy * 0.9
        
        t = np.linspace(0, 1, 60)
        curve_x = (1-t)**3 * start_x + 3*(1-t)**2*t * cp1_x + 3*(1-t)*t**2 * cp2_x + t**3 * end_x
        curve_y = (1-t)**3 * start_y + 3*(1-t)**2*t * cp1_y + 3*(1-t)*t**2 * cp2_y + t**3 * end_y
        
        ax.plot(curve_x, curve_y, color=color, linewidth=width, alpha=opacity)
    
    def _draw_stepped_line(self, ax, start_x, start_y, end_x, end_y, 
                          color, width, opacity):
        """绘制阶梯线"""
        # 阶梯线：先水平，再垂直
        mid_x = start_x + (end_x - start_x) * 0.7
        
        ax.plot([start_x, mid_x], [start_y, start_y], 
               color=color, linewidth=width, alpha=opacity)
        ax.plot([mid_x, mid_x], [start_y, end_y], 
               color=color, linewidth=width, alpha=opacity)
        ax.plot([mid_x, end_x], [end_y, end_y], 
               color=color, linewidth=width, alpha=opacity)


def create_style_config(**kwargs) -> StyleConfig:
    """创建样式配置的便捷函数"""
    return StyleConfig(**kwargs)


# 预定义样式配置
PRESET_STYLES = {
    'default': StyleConfig(),
    'business': StyleConfig(
        color_scheme=ColorScheme.BUSINESS,
        node_shape=NodeShape.RECTANGLE,
        line_style=LineStyle.STRAIGHT,
        font_weight='bold'
    ),
    'creative': StyleConfig(
        color_scheme=ColorScheme.CREATIVE,
        node_shape=NodeShape.CIRCLE,
        line_style=LineStyle.BEZIER,
        node_shadow=True
    ),
    'academic': StyleConfig(
        color_scheme=ColorScheme.ACADEMIC,
        node_shape=NodeShape.ROUNDED_RECTANGLE,
        line_style=LineStyle.CURVED,
        font_size_base=24
    ),
    'minimal': StyleConfig(
        color_scheme=ColorScheme.MONOCHROME,
        node_shape=NodeShape.RECTANGLE,
        line_style=LineStyle.STRAIGHT,
        node_border_width=2,
        node_shadow=False
    )
}