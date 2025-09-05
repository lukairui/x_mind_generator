#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Fishbone (Ishikawa) Diagram Mind Map Tool
Generates fishbone/cause-and-effect diagrams from Markdown text
Perfect for problem analysis and root cause analysis
"""

import os
import re
import tempfile
import time
import math
import shutil
from typing import Any, Dict, Generator, List

from dify_plugin import Tool
from .style_config import StyleConfig, StyleRenderer, PRESET_STYLES, ColorScheme, NodeShape, LineStyle


class MindMapFishboneTool(Tool):
    
    def _setup_pil_chinese_font(self, temp_dir):
        """设置PIL中文字体"""
        try:
            from PIL import Image, ImageDraw, ImageFont
        except ImportError:
            print("PIL/Pillow not available, using fallback")
            return None
            
        import platform
        
        system = platform.system()
        print(f"System: {system}")
        
        # 优先使用嵌入的字体文件
        embedded_font_path = os.path.join(os.path.dirname(__file__), '..', 'fonts', 'chinese_font.ttc')
        embedded_font_path = os.path.abspath(embedded_font_path)
        
        if os.path.exists(embedded_font_path):
            print(f"Found embedded Chinese font: {embedded_font_path}")
            return embedded_font_path
        
        print("Embedded font not found, trying system fonts...")
        
        # 查找系统中文字体文件（作为备用）
        font_file = None
        
        if system == 'Windows':
            font_paths = [
                r'C:\Windows\Fonts\msyh.ttc',      # 微软雅黑
                r'C:\Windows\Fonts\simhei.ttf',    # 黑体
                r'C:\Windows\Fonts\simsun.ttc',    # 宋体
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    font_file = font_path
                    print(f"Found system Chinese font: {font_path}")
                    break
        elif system == 'Darwin':  # macOS
            font_paths = [
                '/System/Library/Fonts/STHeiti Light.ttc',
                '/System/Library/Fonts/PingFang.ttc',
                '/System/Library/Fonts/Hiragino Sans GB.ttc',
            ]
            for font_path in font_paths:
                if os.path.exists(font_path):
                    font_file = font_path
                    print(f"Found system Chinese font: {font_path}")
                    break
        else:  # Linux
            font_paths = [
                '/usr/share/fonts/wqy-microhei/wqy-microhei.ttc',
                '/usr/share/fonts/truetype/wqy/wqy-microhei.ttc',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            ]
            for font_path in font_paths:
                if os.path.exists(font_path):
                    font_file = font_path
                    print(f"Found system Chinese font: {font_path}")
                    break
        
        return font_file
    
    def _parse_markdown_to_fishbone(self, markdown_text: str) -> dict:
        """解析Markdown为鱼骨图结构"""
        lines = markdown_text.strip().split('\n')
        
        # 鱼骨图特殊结构：第一个标题作为问题/效果，其他作为原因分类
        problem = "问题分析"
        categories = []
        current_category = None
        
        for line in lines:
            line = line.rstrip()
            if not line or line.startswith('```'):
                continue
            
            # 一级标题作为问题/效果
            if line.startswith('# '):
                problem = line[2:].strip()
                
            # 二级标题作为主要原因分类
            elif line.startswith('## '):
                category_name = line[3:].strip()
                current_category = {
                    'name': category_name,
                    'causes': []
                }
                categories.append(current_category)
                
            # 三级标题或列表作为具体原因
            elif line.startswith('### ') and current_category:
                cause = line[4:].strip()
                current_category['causes'].append({
                    'content': self._clean_markdown_text(cause),
                    'subcauses': []
                })
                
            # 无序列表作为具体原因
            elif re.match(r'^\s*[-\*\+]\s+', line):
                if current_category:
                    leading_spaces = len(line) - len(line.lstrip())
                    cause_text = re.sub(r'^\s*[-\*\+]\s*', '', line)
                    cause_text = self._clean_markdown_text(cause_text)
                    
                    if leading_spaces == 0:  # 主要原因
                        current_category['causes'].append({
                            'content': cause_text,
                            'subcauses': []
                        })
                    elif leading_spaces >= 2 and current_category['causes']:  # 子原因
                        current_category['causes'][-1]['subcauses'].append(cause_text)
        
        # 如果没有找到分类，创建默认分类
        if not categories:
            categories = [{
                'name': '主要原因',
                'causes': [{'content': '请在Markdown中使用## 标题来定义原因分类', 'subcauses': []}]
            }]
        
        return {
            'problem': problem,
            'categories': categories
        }

    def _clean_markdown_text(self, text: str) -> str:
        """清理Markdown格式文本"""
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = text.replace('《', '').replace('》', '')
        text = re.sub(r'\*\*(.*?)\*\*:\s*', r'\1: ', text)
        return text.strip()
    
    def _wrap_text_for_box(self, text: str, max_chars: int = 6) -> str:
        """为文本框优化的文字换行处理，限制为2行，保留完整内容"""
        if len(text) <= max_chars:
            return text
        
        # 先尝试智能分行：在空格、括号等位置分行
        smart_break_chars = [' ', '(', '（', '-', '—', '、', '，']
        
        # 如果文本长度在合理范围内，尝试智能分行
        if len(text) <= max_chars * 2:
            best_break_pos = -1
            # 从中间位置开始向两边查找合适的分行点
            for i in range(max_chars - 2, max_chars + 3):
                if i < len(text) and text[i] in smart_break_chars:
                    best_break_pos = i
                    break
            
            if best_break_pos > 0:
                line1 = text[:best_break_pos].strip()
                line2 = text[best_break_pos:].strip()
                # 确保两行都不超过限制
                if len(line1) <= max_chars + 2 and len(line2) <= max_chars + 2:
                    return line1 + '\n' + line2
        
        # 如果智能分行失败，使用强制分行但尽量保留内容
        if len(text) <= max_chars * 2:
            # 分成2行，允许略微超出限制
            mid_point = len(text) // 2
            line1 = text[:mid_point]
            line2 = text[mid_point:]
            return line1 + '\n' + line2
        else:
            # 超过限制的情况，优先保留前面的内容
            line1 = text[:max_chars + 2]  # 略微放宽限制
            remaining = text[max_chars + 2:]
            if len(remaining) <= max_chars + 2:
                line2 = remaining
            else:
                line2 = remaining[:max_chars - 1] + '…'
            return line1 + '\n' + line2
    
    def _wrap_text(self, text: str, max_chars: int = 8) -> str:
        """文字换行处理，超过指定字符数智能换行，保留完整内容"""
        if len(text) <= max_chars:
            return text
        
        # 智能分行：在空格、括号等位置分行
        smart_break_chars = [' ', '(', '（', '-', '—', '、', '，', '：']
        lines = []
        current_text = text
        
        while len(current_text) > max_chars:
            best_break_pos = -1
            # 在合适的范围内查找分行点
            for i in range(max_chars - 3, min(len(current_text), max_chars + 3)):
                if current_text[i] in smart_break_chars:
                    best_break_pos = i
                    break
            
            if best_break_pos > 0:
                # 在智能分行点分行
                lines.append(current_text[:best_break_pos].strip())
                current_text = current_text[best_break_pos:].strip()
            else:
                # 没有找到合适的分行点，强制分行
                lines.append(current_text[:max_chars])
                current_text = current_text[max_chars:]
        
        # 添加最后一行
        if current_text:
            lines.append(current_text)
        
        return '\n'.join(lines)

    def _draw_text_with_pil(self, img, draw, x, y, text, style_dict, color, font_file, 
                           angle=0, anchor_point='center'):
        """使用PIL绘制中文文本，支持旋转"""
        try:
            from PIL import ImageFont, ImageDraw, Image
            
            safe_text = str(text).strip()
            if not safe_text:
                safe_text = f"Text"
            
            print(f"Drawing fishbone text: '{safe_text}' at ({x:.0f}, {y:.0f}), angle={angle}")
            
            font_size = style_dict['font_size']
            padding = style_dict['padding']
            border_width = style_dict['border_width']
            
            # 加载字体
            font = None
            if font_file and os.path.exists(font_file):
                try:
                    font = ImageFont.truetype(font_file, font_size)
                except Exception as e:
                    print(f"Failed to load font: {e}")
            
            if font is None:
                try:
                    font = ImageFont.load_default()
                except:
                    return
            
            # 如果需要旋转文字
            if angle != 0:
                # 创建临时图像用于文字旋转
                bbox = draw.textbbox((0, 0), safe_text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # 创建文字图像
                text_img = Image.new('RGBA', (text_width + padding*2, text_height + padding*2), (255, 255, 255, 0))
                text_draw = ImageDraw.Draw(text_img)
                
                # 绘制背景框（只有在显示背景时才绘制）
                if style_dict.get('show_background', False):
                    box_coords = [0, 0, text_width + padding*2, text_height + padding*2]
                    if hasattr(self, 'style_renderer'):
                        self.style_renderer.draw_node_shape(
                            text_draw, box_coords, color, style_dict
                        )
                    else:
                        text_draw.rounded_rectangle(box_coords, radius=3, 
                                                  fill='white', outline=color, width=border_width)
                
                # 绘制文字
                text_draw.text((padding, padding), safe_text, font=font, fill=color)
                
                # 旋转图像
                rotated = text_img.rotate(angle, expand=True)
                
                # 粘贴到主图像
                rotated_width, rotated_height = rotated.size
                paste_x = int(x - rotated_width // 2)
                paste_y = int(y - rotated_height // 2)
                
                if anchor_point == 'left':
                    paste_x = int(x)
                elif anchor_point == 'right':
                    paste_x = int(x - rotated_width)
                
                img.paste(rotated, (paste_x, paste_y), rotated)
                
            else:
                # 正常绘制（无旋转）
                bbox = draw.textbbox((0, 0), safe_text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                # 计算位置
                if anchor_point == 'center':
                    text_x = x - text_width // 2
                    text_y = y - text_height // 2
                elif anchor_point == 'left':
                    text_x = x
                    text_y = y - text_height // 2
                elif anchor_point == 'right':
                    text_x = x - text_width
                    text_y = y - text_height // 2
                else:
                    text_x = x - text_width // 2
                    text_y = y - text_height // 2
                
                # 绘制背景框（只有在显示背景时才绘制）
                if style_dict.get('show_background', False):
                    box_x1 = text_x - padding
                    box_y1 = text_y - padding
                    box_x2 = text_x + text_width + padding
                    box_y2 = text_y + text_height + padding
                    
                    if hasattr(self, 'style_renderer'):
                        self.style_renderer.draw_node_shape(
                            draw, (box_x1, box_y1, box_x2, box_y2), color, style_dict
                        )
                    else:
                        draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], 
                                             radius=3, fill='white', outline=color, width=border_width)
                
                # 绘制文字
                draw.text((text_x, text_y), safe_text, font=font, fill=color)
            
            print(f"Successfully drew fishbone text: '{safe_text}'")
            
        except Exception as e:
            print(f"PIL fishbone text drawing error: {e}")

    def _generate_png_mindmap(self, fishbone_data: dict, output_file: str, temp_dir: str, 
                             style_config: StyleConfig = None) -> bool:
        """生成鱼骨图PNG思维导图"""
        try:
            print("Starting fishbone diagram generation...")
            
            # 设置默认样式
            if style_config is None:
                style_config = PRESET_STYLES['default']
            
            self.style_renderer = StyleRenderer(style_config)
            
            # 设置PIL中文字体
            font_file = self._setup_pil_chinese_font(temp_dir)
            
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import numpy as np
            from PIL import Image, ImageDraw
            
            # 配置matplotlib
            if font_file and os.path.exists(font_file):
                try:
                    import matplotlib.font_manager as fm
                    fm.fontManager.addfont(font_file)
                    font_prop = fm.FontProperties(fname=font_file)
                    plt.rcParams['font.family'] = font_prop.get_name()
                except Exception as e:
                    print(f"Failed to configure matplotlib font: {e}")
                    plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
                    plt.rcParams['axes.unicode_minus'] = False
            else:
                plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'DejaVu Sans']
                plt.rcParams['axes.unicode_minus'] = False
            
            # 计算画布大小（根据分类数量和内容动态调整）
            num_categories = len(fishbone_data['categories'])
            
            # 计算每个分类的内容数量
            max_causes = max([len(cat['causes']) for cat in fishbone_data['categories']], default=1)
            
            # 根据分类数量和内容复杂度动态调整尺寸
            width = max(20, min(28, 18 + num_categories * 2 + max_causes * 0.5))
            height = max(14, min(18, 12 + num_categories * 1.5 + max_causes * 0.3))
            
            fig, ax = plt.subplots(1, 1, figsize=(width, height))
            
            # 设置坐标轴范围（根据内容和更大文字动态调整）
            x_limit = 18  # 从16增加到18，适应更长的鱼骨和更大的文字
            y_limit = 14  # 从12增加到14
            
            ax.set_xlim(-x_limit, x_limit)
            ax.set_ylim(-y_limit, y_limit)
            ax.axis('off')
            
            # 设置背景颜色
            fig.patch.set_facecolor(self.style_renderer.get_background_color())
            
            # 存储文本信息，稍后用PIL绘制
            text_elements = []
            
            def store_text_element(x, y, text, depth_level, color='#333333', 
                                 angle=0, anchor='center', show_bg=True, text_box_info=None):
                """存储文本元素供PIL渲染"""
                style = self.style_renderer.get_node_style(depth_level)
                
                # 为鱼骨图调整样式 - 除鱼头外其他文字减小1号
                if depth_level == 1:  # 鱼头主题 - 保持不变
                    style['font_size'] = 24  # 保持24不变
                    style['padding'] = 8
                    style['show_background'] = False  # 鱼头已有背景
                    processed_text = self._wrap_text(text, 8)
                elif depth_level == 2:  # 分类标签 - 减小1号
                    style['font_size'] = 21  # 从22减小到21
                    style['padding'] = 6
                    style['show_background'] = False  # 去掉背景框
                    # 如果有文本框信息，按照文本框尺寸进行换行（放宽限制以保留完整内容）
                    if text_box_info:
                        processed_text = self._wrap_text_for_box(text, 8)  # 从6增加到8，更好地处理长内容
                    else:
                        processed_text = self._wrap_text(text, 10)  # 也放宽一些
                elif depth_level == 3:  # 主要原因 - 减小1号
                    style['font_size'] = 19  # 从20减小到19
                    style['padding'] = 5
                    style['show_background'] = False  # 去掉背景框
                    # 如果有文本框信息，按照文本框尺寸进行换行
                    if text_box_info:
                        processed_text = self._wrap_text_for_box(text, 7)  # 从5增加到7，适合原因文本框
                    else:
                        processed_text = self._wrap_text(text, 10)  # 放宽限制
                else:  # 子原因 - 减小1号，使用黑色字体
                    style['font_size'] = 17  # 从18减小到17
                    style['padding'] = 4
                    style['show_background'] = False  # 去掉背景框
                    color = '#000000'  # 子原因统一使用黑色
                    processed_text = self._wrap_text(text, 8)
                
                text_elements.append({
                    'x': x, 'y': y, 'text': processed_text, 
                    'depth_level': depth_level, 'color': color,
                    'style': style, 'angle': angle, 'anchor': anchor,
                    'text_box_info': text_box_info
                })

            def draw_fishbone_structure():
                """绘制鱼骨图结构 - 参考标准鱼骨图样式，修复重叠和长度问题"""
                problem = fishbone_data['problem']
                categories = fishbone_data['categories']
                num_categories = len(categories)
                
                # 鱼头位置（左侧椭圆形）
                fish_head_x = -11
                fish_head_y = 0
                fish_head_width = 2.8
                fish_head_height = 1.8
                
                # 绘制鱼头（椭圆形）
                from matplotlib.patches import Ellipse
                ellipse = Ellipse((fish_head_x, fish_head_y), fish_head_width, fish_head_height, 
                                 facecolor='lightblue', edgecolor='#2c3e50', linewidth=3, alpha=0.8)
                ax.add_patch(ellipse)
                
                # 鱼头文本
                store_text_element(fish_head_x, fish_head_y, problem, 1, '#2c3e50', 0, 'center', False)
                
                # 主干线（鱼脊）- 从鱼头向右延伸，进一步延长
                spine_start_x = fish_head_x + fish_head_width/2
                spine_end_x = 11  # 从10增加到11，为更长的鱼骨提供空间
                spine_y = 0
                
                # 绘制主干线
                ax.plot([spine_start_x, spine_end_x], [spine_y, spine_y], 
                       color='#2c3e50', linewidth=5, alpha=0.9, solid_capstyle='round')
                
                # 计算分支位置 - 优化分布避免重叠
                available_length = spine_end_x - spine_start_x - 2
                if num_categories > 0:
                    # 根据分类数量动态调整间距
                    min_spacing = 1.5  # 最小间距
                    ideal_spacing = available_length / num_categories
                    branch_spacing = max(min_spacing, ideal_spacing)
                else:
                    branch_spacing = available_length
                
                for i, category in enumerate(categories):
                    # 交替上下分布
                    is_upper = i % 2 == 0
                    side = 1 if is_upper else -1
                    
                    # 分支起始位置（更合理的分布，避免过于靠近）
                    branch_start_x = spine_start_x + 1.5 + i * branch_spacing
                    # 确保不超出主干线范围
                    if branch_start_x > spine_end_x - 1:
                        branch_start_x = spine_end_x - 1
                    
                    branch_start_y = spine_y
                    
                    # 主分支终点（严格45度角，确保精确角度）
                    branch_length = 6.5  # 从5.5增加到6.5，让鱼骨更长
                    # 使用精确的45度角计算
                    cos_45 = 0.7071067811865476  # math.cos(math.radians(45))
                    sin_45 = 0.7071067811865476  # math.sin(math.radians(45))
                    
                    branch_end_x = branch_start_x + branch_length * cos_45
                    branch_end_y = branch_start_y + side * branch_length * sin_45
                    
                    # 绘制主分支线
                    branch_color = self.style_renderer.get_color(i)
                    ax.plot([branch_start_x, branch_end_x], [branch_start_y, branch_end_y], 
                           color=branch_color, linewidth=4, alpha=0.8, solid_capstyle='round')
                    
                    # 分类标签位置（在分支线的1/3到2/3范围内创建文本框，但偏移避开鱼骨线）
                    # 计算文本框的起始和结束位置
                    text_box_start_ratio = 0.33  # 1/3位置
                    text_box_end_ratio = 0.67    # 2/3位置
                    
                    box_start_x = branch_start_x + (branch_end_x - branch_start_x) * text_box_start_ratio
                    box_start_y = branch_start_y + (branch_end_y - branch_start_y) * text_box_start_ratio
                    box_end_x = branch_start_x + (branch_end_x - branch_start_x) * text_box_end_ratio
                    box_end_y = branch_start_y + (branch_end_y - branch_start_y) * text_box_end_ratio
                    
                    # 文本框中心位置
                    box_center_x = (box_start_x + box_end_x) / 2
                    box_center_y = (box_start_y + box_end_y) / 2
                    
                    # 计算避开鱼骨线的偏移量（垂直于分支线方向）
                    offset_distance = 0.8  # 偏移距离，确保文字不与线条重叠
                    cos_45 = 0.7071067811865476
                    sin_45 = 0.7071067811865476
                    
                    if is_upper:
                        # 上方分支，文字放在鱼骨下方（向下偏移）
                        label_x = box_center_x - offset_distance * sin_45 * 0.3  # 轻微向左
                        label_y = box_center_y - offset_distance * cos_45  # 向下偏移
                    else:
                        # 下方分支，文字偏移到分支线的外侧（向右下）
                        label_x = box_center_x + offset_distance * sin_45  # 向右偏移
                        label_y = box_center_y - offset_distance * cos_45  # 向下偏移
                    
                    # 计算文字倾斜角度（与分支线平行）
                    text_angle = 45 if is_upper else -45
                    
                    category_name = category['name']
                    # 存储文本框信息用于绘制
                    store_text_element(label_x, label_y, category_name, 2, branch_color, text_angle, 'center', 
                                     text_box_info={'start_x': box_start_x, 'start_y': box_start_y, 
                                                  'end_x': box_end_x, 'end_y': box_end_y})
                    
                    # 绘制具体原因（优化布局避免重叠）
                    causes = category['causes']
                    if not causes:
                        continue
                        
                    # 计算原因分布，增加间距避免重叠
                    for j, cause in enumerate(causes):
                        # 原因在主分支上的位置比例（分布更加均匀）
                        if len(causes) == 1:
                            ratio = 0.4  # 单个原因靠近根部
                        else:
                            # 多个原因时，从0.2到0.6分布，避免过于靠近末端
                            ratio = 0.2 + (j * 0.4 / (len(causes) - 1))
                        
                        cause_branch_x = branch_start_x + ratio * (branch_end_x - branch_start_x)
                        cause_branch_y = branch_start_y + ratio * (branch_end_y - branch_start_y)
                        
                        # 原因分支线（与主分支垂直，增加长度）
                        base_cause_length = 2.2  # 从1.8增加到2.2
                        # 阶梯增长更温和，避免过长
                        cause_length = base_cause_length + j * 0.4  # 从0.3增加到0.4
                        
                        # 计算垂直方向（与主分支严格垂直，保持45度角）
                        # 原因分支与主分支垂直，所以角度为 45° + 90° = 135° 或 45° - 90° = -45°
                        if is_upper:
                            # 上方分支，原因分支向下右（135度角）
                            cos_135 = -0.7071067811865476  # math.cos(math.radians(135))
                            sin_135 = 0.7071067811865476   # math.sin(math.radians(135))
                            cause_end_x = cause_branch_x + cause_length * cos_135
                            cause_end_y = cause_branch_y + cause_length * sin_135
                        else:
                            # 下方分支，原因分支向上右（-135度角或225度角）
                            cos_neg135 = -0.7071067811865476  # math.cos(math.radians(-135))
                            sin_neg135 = -0.7071067811865476  # math.sin(math.radians(-135))
                            cause_end_x = cause_branch_x + cause_length * cos_neg135
                            cause_end_y = cause_branch_y + cause_length * sin_neg135
                        
                        # 绘制原因分支线
                        ax.plot([cause_branch_x, cause_end_x], [cause_branch_y, cause_end_y], 
                               color=branch_color, linewidth=3, alpha=0.7)
                        
                        # 原因文本位置（在原因分支线的1/3到2/3范围内创建文本框，但偏移避开鱼骨线）
                        cause_text_box_start_ratio = 0.33
                        cause_text_box_end_ratio = 0.67
                        
                        cause_box_start_x = cause_branch_x + (cause_end_x - cause_branch_x) * cause_text_box_start_ratio
                        cause_box_start_y = cause_branch_y + (cause_end_y - cause_branch_y) * cause_text_box_start_ratio
                        cause_box_end_x = cause_branch_x + (cause_end_x - cause_branch_x) * cause_text_box_end_ratio
                        cause_box_end_y = cause_branch_y + (cause_end_y - cause_branch_y) * cause_text_box_end_ratio
                        
                        # 原因文本框中心位置
                        cause_box_center_x = (cause_box_start_x + cause_box_end_x) / 2
                        cause_box_center_y = (cause_box_start_y + cause_box_end_y) / 2
                        
                        # 计算避开鱼骨线的偏移量（垂直于原因分支线方向）
                        cause_offset_distance = 0.6  # 原因文字的偏移距离
                        cos_45 = 0.7071067811865476
                        sin_45 = 0.7071067811865476
                        
                        if is_upper:
                            # 上方分支，原因文字放在鱼骨下方（向下偏移）
                            text_x = cause_box_center_x - cause_offset_distance * sin_45 * 0.5  # 轻微向左
                            text_y = cause_box_center_y - cause_offset_distance * cos_45  # 向下偏移
                            text_angle = -45  # 上方分支向下右倾斜
                        else:
                            # 下方分支，原因文字偏移到分支线的外侧（向下左）
                            text_x = cause_box_center_x - cause_offset_distance * sin_45  # 向左偏移
                            text_y = cause_box_center_y - cause_offset_distance * cos_45  # 向下偏移
                            text_angle = 45   # 下方分支向上右倾斜
                        
                        store_text_element(text_x, text_y, cause['content'], 3, 
                                         branch_color, text_angle, 'center',
                                         text_box_info={'start_x': cause_box_start_x, 'start_y': cause_box_start_y,
                                                      'end_x': cause_box_end_x, 'end_y': cause_box_end_y})
                        
                        # 绘制子原因（简化布局，避免重叠）
                        subcauses = cause.get('subcauses', [])
                        for k, subcause in enumerate(subcauses):
                            # 子原因线长度和位置
                            sub_length = 1.0
                            sub_x = text_x + sub_length
                            
                            # 子原因垂直分布，减少间距避免过度扩散
                            vertical_spacing = 0.4
                            if is_upper:
                                sub_y = text_y - (k + 1) * vertical_spacing
                            else:
                                sub_y = text_y + (k + 1) * vertical_spacing
                            
                            # 绘制子原因线
                            ax.plot([text_x + 0.2, sub_x], [text_y, sub_y], 
                                   color=branch_color, linewidth=1.5, alpha=0.4)
                            
                            # 子原因文字位置（上下分支分开处理）
                            sub_offset = 0.15  # 适中的偏移量
                            if is_upper:
                                # 上方分支，子原因文字放在鱼骨下方
                                sub_text_x = sub_x + sub_offset * 0.3  # 轻微向右
                                sub_text_y = sub_y - sub_offset * 1.5  # 向下偏移
                            else:
                                # 下方分支，子原因文字稍微向下偏移
                                sub_text_x = sub_x + sub_offset * 0.3  # 轻微向右
                                sub_text_y = sub_y - sub_offset  # 向下偏移
                            
                            # 子原因使用黑色字体，无倾斜角度
                            store_text_element(sub_text_x, sub_text_y, subcause, 4, 
                                             '#000000', 0, 'left')  # 使用水平文字，左对齐
            
            # 绘制鱼骨图结构
            draw_fishbone_structure()
            
            # 保存matplotlib图像
            temp_matplotlib_file = os.path.join(temp_dir, 'temp_fishbone_matplotlib.png')
            plt.savefig(temp_matplotlib_file, dpi=150, bbox_inches='tight', 
                       facecolor=self.style_renderer.get_background_color())
            plt.close()
            
            # 用PIL处理文本
            img = Image.open(temp_matplotlib_file)
            draw = ImageDraw.Draw(img)
            
            # 坐标转换函数
            def matplotlib_to_pil(mat_x, mat_y, img_width, img_height):
                """将matplotlib坐标转换为PIL坐标"""
                pil_x = int((mat_x + x_limit) / (2 * x_limit) * img_width)
                pil_y = int((y_limit - mat_y) / (2 * y_limit) * img_height)
                return pil_x, pil_y
            
            # 绘制所有文本
            img_width, img_height = img.size
            for element in text_elements:
                pil_x, pil_y = matplotlib_to_pil(element['x'], element['y'], 
                                                img_width, img_height)
                
                # 如果有文本框信息，绘制文本框
                if element.get('text_box_info'):
                    box_info = element['text_box_info']
                    # 转换文本框坐标
                    box_start_pil_x, box_start_pil_y = matplotlib_to_pil(box_info['start_x'], box_info['start_y'], 
                                                                        img_width, img_height)
                    box_end_pil_x, box_end_pil_y = matplotlib_to_pil(box_info['end_x'], box_info['end_y'], 
                                                                      img_width, img_height)
                    
                    # 计算文本框的宽度和高度（以2行文字的高度）
                    box_width = abs(box_end_pil_x - box_start_pil_x)
                    box_height = element['style']['font_size'] * 2.5  # 2行文字的高度
                    
                    # 计算旋转后的文本框位置
                    angle_rad = math.radians(element.get('angle', 0))
                    
                    # 绘制文本框轮廓（调试用）
                    # 计算旋转后的四个角点
                    cos_a = math.cos(angle_rad)
                    sin_a = math.sin(angle_rad)
                    
                    # 相对于中心点的四个角点
                    corners = [
                        (-box_width/2, -box_height/2),
                        (box_width/2, -box_height/2),
                        (box_width/2, box_height/2),
                        (-box_width/2, box_height/2)
                    ]
                    
                    # 旋转和平移后的角点
                    rotated_corners = []
                    for x, y in corners:
                        new_x = x * cos_a - y * sin_a + pil_x
                        new_y = x * sin_a + y * cos_a + pil_y
                        rotated_corners.append((new_x, new_y))
                    
                    # 绘制文本框轮廓（调试线，可选）
                    # draw.polygon(rotated_corners, outline='red', width=1)
                
                self._draw_text_with_pil(img, draw, pil_x, pil_y, 
                                       element['text'], element['style'],
                                       element['color'], font_file,
                                       element.get('angle', 0),
                                       element.get('anchor', 'center'))
            
            # 保存最终图像
            img.save(output_file, 'PNG', dpi=(150, 150))
            
            # 清理临时文件
            if os.path.exists(temp_matplotlib_file):
                os.remove(temp_matplotlib_file)
            
            print(f"Fishbone diagram saved to: {output_file}")
            return True
            
        except Exception as e:
            print(f"Error generating fishbone diagram: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _invoke(self, tool_parameters: dict):
        """工具调用入口"""
        try:
            markdown_text = tool_parameters.get('markdown_text', '')
            style_preset = tool_parameters.get('style_preset', 'default')
            
            # 获取样式配置
            style_config = PRESET_STYLES.get(style_preset, PRESET_STYLES['default'])
            
            if not markdown_text.strip():
                yield self.create_text_message('请提供有效的Markdown文本')
                return
            
            # 解析Markdown为鱼骨图
            fishbone_data = self._parse_markdown_to_fishbone(markdown_text)
            
            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                output_file = os.path.join(temp_dir, f'fishbone_mindmap_{int(time.time())}.png')
                
                # 生成鱼骨图
                success = self._generate_png_mindmap(fishbone_data, output_file, temp_dir, style_config)
                
                if success and os.path.exists(output_file):
                    # 读取文件内容
                    with open(output_file, 'rb') as f:
                        file_content = f.read()
                    
                    # 计算文件大小
                    file_size = len(file_content)
                    size_mb = file_size / (1024 * 1024)
                    size_text = f"{size_mb:.2f}M"
                    
                    yield self.create_blob_message(
                        blob=file_content,
                        meta={'mime_type': 'image/png', 'filename': f'fishbone_mindmap_{int(time.time())}.png'}
                    )
                    yield self.create_text_message(f'鱼骨图生成成功！适合问题分析和原因追溯。文件大小: {size_text}')
                else:
                    yield self.create_text_message('生成鱼骨图失败，请检查输入内容')
                    
        except Exception as e:
            print(f"Error in _invoke: {e}")
            import traceback
            traceback.print_exc()
            yield self.create_text_message(f'生成鱼骨图时发生错误：{str(e)}')