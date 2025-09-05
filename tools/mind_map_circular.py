#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Circular/Ring Layout Mind Map Tool
Generates circular and ring-style mind maps from Markdown text
Perfect for cyclical data, relationships, and categorical information
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


class MindMapCircularTool(Tool):
    
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
        
        embedded_font_path = os.path.join(os.path.dirname(__file__), '..', 'fonts', 'chinese_font.ttc')
        embedded_font_path = os.path.abspath(embedded_font_path)
        
        if os.path.exists(embedded_font_path):
            print(f"Found embedded Chinese font: {embedded_font_path}")
            return embedded_font_path
        
        print("Embedded font not found, trying system fonts...")
        
        font_file = None
        
        if system == 'Windows':
            font_paths = [
                r'C:\Windows\Fonts\msyh.ttc',
                r'C:\Windows\Fonts\simhei.ttf',
                r'C:\Windows\Fonts\simsun.ttc',
            ]
            
            for font_path in font_paths:
                if os.path.exists(font_path):
                    font_file = font_path
                    print(f"Found system Chinese font: {font_path}")
                    break
        elif system == 'Darwin':
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
        else:
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
    
    def _parse_markdown_to_circular(self, markdown_text: str) -> dict:
        """解析Markdown为圆形布局结构"""
        lines = markdown_text.strip().split('\n')
        
        center_title = "圆形图"
        categories = []
        current_category = None
        
        for line in lines:
            line = line.rstrip()
            if not line or line.startswith('```'):
                continue
            
            # 一级标题作为中心标题
            if line.startswith('# '):
                center_title = line[2:].strip()
                
            # 二级标题作为主要分类（外圈）
            elif line.startswith('## '):
                if current_category:
                    categories.append(current_category)
                
                category_name = line[3:].strip()
                current_category = {
                    'name': category_name,
                    'items': [],
                    'subcategories': []
                }
                
            # 三级标题作为子分类
            elif line.startswith('### ') and current_category:
                subcategory = line[4:].strip()
                current_category['subcategories'].append({
                    'name': self._clean_markdown_text(subcategory),
                    'items': []
                })
                
            # 列表项作为具体项目
            elif re.match(r'^\s*[-\*\+]\s+', line):
                if current_category:
                    item = re.sub(r'^\s*[-\*\+]\s*', '', line)
                    item = self._clean_markdown_text(item)
                    
                    # 如果有子分类，添加到最后一个子分类中
                    if current_category['subcategories']:
                        current_category['subcategories'][-1]['items'].append(item)
                    else:
                        current_category['items'].append(item)
        
        # 添加最后一个分类
        if current_category:
            categories.append(current_category)
        
        # 如果没有找到分类，创建默认分类
        if not categories:
            categories = [{
                'name': '分类1',
                'items': ['请在Markdown中使用## 分类名称来定义圆形分类'],
                'subcategories': []
            }]
        
        return {
            'center': center_title,
            'categories': categories
        }

    def _clean_markdown_text(self, text: str) -> str:
        """清理Markdown格式文本"""
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = text.replace('《', '').replace('》', '')
        text = re.sub(r'\*\*(.*?)\*\*:\s*', r'\1: ', text)
        return text.strip()

    def _draw_text_with_pil(self, img, draw, x, y, text, style_dict, color, font_file, 
                           angle=0, anchor_point='center', depth_level=1):
        """使用PIL绘制中文文本，支持旋转"""
        try:
            from PIL import ImageFont, ImageDraw, Image
            
            safe_text = str(text).strip()
            if not safe_text:
                safe_text = f"Item"
            
            # 第三层和第四层文字换行处理
            if depth_level >= 3 and len(safe_text) > 15:
                # 每15个字符换行
                lines = []
                for i in range(0, len(safe_text), 15):
                    lines.append(safe_text[i:i+15])
                safe_text = '\n'.join(lines)
            
            print(f"Drawing circular text: '{safe_text}' at ({x:.0f}, {y:.0f}), angle={angle}")
            
            font_size = style_dict['font_size']
            # 增大最外层文字大小
            if depth_level >= 3:  # 最外层文字
                font_size = int(font_size * 1.5) + 2  # 增大1.5倍再加4号
            
            # 根据层级调整内边距，外层文字减小背景框
            if depth_level >= 3:
                padding = max(2, style_dict['padding'] // 2)  # 外层文字减小内边距
            else:
                padding = style_dict['padding']
                
            border_width = style_dict['border_width']
            
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
                temp_size = max(text_width, text_height) + padding * 4
                text_img = Image.new('RGBA', (temp_size, temp_size), (255, 255, 255, 0))
                text_draw = ImageDraw.Draw(text_img)
                
                # 在临时图像中心绘制文字
                temp_x = temp_size // 2 - text_width // 2
                temp_y = temp_size // 2 - text_height // 2
                
                # 绘制背景框
                if style_dict.get('show_background', True):
                    box_coords = [temp_x - padding, temp_y - padding, 
                                temp_x + text_width + padding, temp_y + text_height + padding]
                    if hasattr(self, 'style_renderer'):
                        self.style_renderer.draw_node_shape(
                            text_draw, box_coords, color, style_dict
                        )
                    else:
                        text_draw.rounded_rectangle(box_coords, radius=3, 
                                                  fill='white', outline=color, width=border_width)
                
                # 绘制文字
                text_draw.text((temp_x, temp_y), safe_text, font=font, fill=color)
                
                # 旋转图像
                rotated = text_img.rotate(angle, expand=True)
                
                # 粘贴到主图像
                rotated_width, rotated_height = rotated.size
                paste_x = int(x - rotated_width // 2)
                paste_y = int(y - rotated_height // 2)
                
                img.paste(rotated, (paste_x, paste_y), rotated)
                
            else:
                # 正常绘制（无旋转）
                bbox = draw.textbbox((0, 0), safe_text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                text_x = x - text_width // 2
                text_y = y - text_height // 2
                
                # 绘制背景框
                if style_dict.get('show_background', True):
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
            
            print(f"Successfully drew circular text: '{safe_text}'")
            
        except Exception as e:
            print(f"PIL circular text drawing error: {e}")

    def _generate_png_mindmap(self, circular_data: dict, output_file: str, temp_dir: str, 
                             style_config: StyleConfig = None) -> bool:
        """生成圆形/环形PNG思维导图"""
        try:
            print("Starting circular layout generation...")
            
            if style_config is None:
                style_config = PRESET_STYLES['creative']  # 圆形布局默认使用创意风格
            
            self.style_renderer = StyleRenderer(style_config)
            
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
            
            # 计算画布大小（正方形适合圆形布局）
            num_categories = len(circular_data['categories'])
            
            size = max(14, min(18, 12 + num_categories))
            
            fig, ax = plt.subplots(1, 1, figsize=(size, size))
            
            limit = 8
            
            ax.set_xlim(-limit, limit)
            ax.set_ylim(-limit, limit)
            ax.axis('off')
            ax.set_aspect('equal')  # 确保圆形不变形
            
            fig.patch.set_facecolor(self.style_renderer.get_background_color())
            
            text_elements = []
            
            def store_text_element(x, y, text, depth_level, color='#333333', 
                                 angle=0, anchor='center', show_bg=True):
                """存储文本元素供PIL渲染"""
                style = self.style_renderer.get_node_style(depth_level)
                style['show_background'] = show_bg
                text_elements.append({
                    'x': x, 'y': y, 'text': text, 
                    'depth_level': depth_level, 'color': color,
                    'style': style, 'angle': angle, 'anchor': anchor
                })

            def draw_circular_structure():
                """绘制真正的环形结构"""
                categories = circular_data['categories']
                if not categories:
                    return
                
                # 中心文本
                center_text = circular_data['center']
                store_text_element(0, 0, center_text, 1, '#333333')
                
                # 定义同心圆环的半径
                ring_radii = [2.5, 4.0, 5.5, 7.0]  # 从内到外的圆环半径
                ring_width = 0.6  # 圆环宽度
                
                # 按层级组织数据
                all_ring_items = []
                
                # 第一层：主分类
                for i, category in enumerate(categories):
                    color = self.style_renderer.get_color(i)
                    all_ring_items.append({
                        'text': category['name'],
                        'level': 0,  # 内圈
                        'color': color,
                        'parent_angle': None,
                        'category_index': i
                    })
                    
                    # 第二层：分类的直接项目
                    items = category.get('items', [])
                    for item in items[:3]:  # 限制为最多3个项目避免拥挤
                        all_ring_items.append({
                            'text': item,
                            'level': 1,  # 第二圈
                            'color': color,
                            'parent_angle': None,
                            'category_index': i
                        })
                    
                    # 第三层：子分类
                    subcategories = category.get('subcategories', [])
                    for j, subcat in enumerate(subcategories[:3]):  # 限制为最多3个子分类
                        all_ring_items.append({
                            'text': subcat['name'],
                            'level': 2,  # 第三圈
                            'color': color,
                            'parent_angle': None,
                            'category_index': i,
                            'subcat_index': j
                        })
                        
                        # 第四层：子分类的项目
                        for item in subcat.get('items', [])[:3]:  # 每个子分类最多3个项目
                            all_ring_items.append({
                                'text': item,
                                'level': 3,  # 最外圈
                                'color': color,
                                'parent_angle': None,
                                'category_index': i,
                                'subcat_index': j
                            })
                
                # 按层级绘制圆环
                for level in range(4):
                    level_items = [item for item in all_ring_items if item['level'] == level]
                    if not level_items:
                        continue
                    
                    radius = ring_radii[level]
                    
                    # 绘制圆环背景
                    if level > 0:  # 中心不绘制圆环
                        ring_circle = plt.Circle((0, 0), radius, fill=False, 
                                               color='lightgray', alpha=0.2, linewidth=2)
                        ax.add_patch(ring_circle)
                    
                    # 按分类分组排列项目
                    if level == 0:  # 主分类均匀分布
                        for i, item in enumerate(level_items):
                            angle = 2 * math.pi * i / len(level_items)
                            x = radius * math.cos(angle)
                            y = radius * math.sin(angle)
                            
                            # 绘制分类扇形区域
                            sector_angle_range = 2 * math.pi / len(level_items) * 0.8
                            start_angle = angle - sector_angle_range / 2
                            end_angle = angle + sector_angle_range / 2
                            
                            # 绘制扇形背景
                            theta = np.linspace(start_angle, end_angle, 20)
                            inner_r = radius - ring_width / 2
                            outer_r = radius + ring_width / 2
                            
                            # 扇形区域
                            x_inner = inner_r * np.cos(theta)
                            y_inner = inner_r * np.sin(theta)
                            x_outer = outer_r * np.cos(theta)
                            y_outer = outer_r * np.sin(theta)
                            
                            # 绘制扇形
                            x_sector = np.concatenate([x_inner, x_outer[::-1]])
                            y_sector = np.concatenate([y_inner, y_outer[::-1]])
                            ax.fill(x_sector, y_sector, color=item['color'], alpha=0.1)
                            
                            store_text_element(x, y, item['text'], level + 1, item['color'])
                            
                    else:  # 其他层级按分类分组
                        category_groups = {}
                        for item in level_items:
                            cat_idx = item['category_index']
                            if cat_idx not in category_groups:
                                category_groups[cat_idx] = []
                            category_groups[cat_idx].append(item)
                        
                        total_categories = len(categories)
                        
                        for cat_idx, cat_items in category_groups.items():
                            # 计算该分类的角度范围
                            category_angle = 2 * math.pi * cat_idx / total_categories
                            angle_range = 2 * math.pi / total_categories * 0.6  # 进一步减小角度范围，让同扇区项目更集中
                            
                            if len(cat_items) == 1:
                                # 单个项目放在分类角度上
                                angle = category_angle
                                x = radius * math.cos(angle)
                                y = radius * math.sin(angle)
                                store_text_element(x, y, cat_items[0]['text'], 
                                                 level + 1, cat_items[0]['color'])
                                
                                # 连线到内圈对应位置
                                if level == 1:
                                    inner_x = ring_radii[0] * math.cos(angle)
                                    inner_y = ring_radii[0] * math.sin(angle)
                                    ax.plot([inner_x * 1.1, x * 0.9], [inner_y * 1.1, y * 0.9], 
                                           color=cat_items[0]['color'], linewidth=1, alpha=0.4)
                                
                            else:
                                # 多个项目在角度范围内分布，向中心靠拢
                                center_bias = 0.7  # 向中心偏移比例，让项目更集中
                                start_angle = category_angle - angle_range / 2 * center_bias
                                end_angle = category_angle + angle_range / 2 * center_bias
                                min_angle_gap = 0.2  # 减小最小角度间隔
                                
                                for i, item in enumerate(cat_items):
                                    if len(cat_items) == 1:
                                        angle = category_angle
                                    else:
                                        # 确保有足够的角度间距，但向中心聚拢
                                        if len(cat_items) > 1:
                                            actual_range = min(end_angle - start_angle, (len(cat_items) - 1) * min_angle_gap)
                                            angle = start_angle + i * actual_range / (len(cat_items) - 1)
                                        else:
                                            angle = category_angle
                                    
                                    x = radius * math.cos(angle)
                                    y = radius * math.sin(angle)
                                    
                                    # 调整文本角度以适应圆形布局
                                    text_angle = 0
                                    if level >= 2:  # 外圈文本可能需要旋转
                                        if abs(angle) > math.pi / 2:
                                            text_angle = math.degrees(angle + math.pi)
                                        else:
                                            text_angle = math.degrees(angle)
                                    
                                    store_text_element(x, y, item['text'], level + 1, 
                                                     item['color'], text_angle, 'center', level <= 1)
                                    
                                    # 连线到内圈（仅对第二层）
                                    if level == 1:
                                        inner_x = ring_radii[0] * math.cos(category_angle)
                                        inner_y = ring_radii[0] * math.sin(category_angle)
                                        ax.plot([inner_x * 1.1, x * 0.9], [inner_y * 1.1, y * 0.9], 
                                               color=item['color'], linewidth=1, alpha=0.4)
                
                # 中心圆已删除，不再绘制实心小圆
            
            # 绘制圆形结构
            draw_circular_structure()
            
            # 保存matplotlib图像
            temp_matplotlib_file = os.path.join(temp_dir, 'temp_circular_matplotlib.png')
            plt.savefig(temp_matplotlib_file, dpi=150, bbox_inches='tight', 
                       facecolor=self.style_renderer.get_background_color())
            plt.close()
            
            # 用PIL处理文本
            img = Image.open(temp_matplotlib_file)
            draw = ImageDraw.Draw(img)
            
            def matplotlib_to_pil(mat_x, mat_y, img_width, img_height):
                """将matplotlib坐标转换为PIL坐标"""
                pil_x = int((mat_x + limit) / (2 * limit) * img_width)
                pil_y = int((limit - mat_y) / (2 * limit) * img_height)
                return pil_x, pil_y
            
            # 绘制所有文本
            img_width, img_height = img.size
            for element in text_elements:
                pil_x, pil_y = matplotlib_to_pil(element['x'], element['y'], 
                                                img_width, img_height)
                self._draw_text_with_pil(img, draw, pil_x, pil_y, 
                                       element['text'], element['style'],
                                       element['color'], font_file,
                                       element.get('angle', 0),
                                       element.get('anchor', 'center'),
                                       element['depth_level'])
            
            # 保存最终图像
            img.save(output_file, 'PNG', dpi=(150, 150))
            
            # 清理临时文件
            if os.path.exists(temp_matplotlib_file):
                os.remove(temp_matplotlib_file)
            
            print(f"Circular layout saved to: {output_file}")
            return True
            
        except Exception as e:
            print(f"Error generating circular layout: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _invoke(self, tool_parameters: dict):
        """工具调用入口"""
        try:
            markdown_text = tool_parameters.get('markdown_text', '')
            style_preset = tool_parameters.get('style_preset', 'creative')
            
            style_config = PRESET_STYLES.get(style_preset, PRESET_STYLES['creative'])
            
            if not markdown_text.strip():
                yield self.create_text_message('请提供有效的Markdown文本')
                return
            
            circular_data = self._parse_markdown_to_circular(markdown_text)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                output_file = os.path.join(temp_dir, f'circular_mindmap_{int(time.time())}.png')
                
                success = self._generate_png_mindmap(circular_data, output_file, temp_dir, style_config)
                
                if success and os.path.exists(output_file):
                    with open(output_file, 'rb') as f:
                        file_content = f.read()
                    
                    # 计算文件大小
                    file_size = len(file_content)
                    size_mb = file_size / (1024 * 1024)
                    size_text = f"{size_mb:.2f}M"
                    
                    yield self.create_blob_message(
                        blob=file_content,
                        meta={'mime_type': 'image/png', 'filename': f'circular_mindmap_{int(time.time())}.png'}
                    )
                    yield self.create_text_message(f'圆形/环形布局图生成成功！适合展示分类关系和周期性数据。文件大小: {size_text}')
                else:
                    yield self.create_text_message('生成圆形/环形布局图失败，请检查输入内容')
                    
        except Exception as e:
            print(f"Error in _invoke: {e}")
            import traceback
            traceback.print_exc()
            yield self.create_text_message(f'生成圆形/环形布局图时发生错误：{str(e)}')