#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Timeline Layout Mind Map Tool
Generates timeline-style mind maps from Markdown text
Perfect for project planning, historical events, and time-based sequences
"""

import os
import re
import tempfile
import time
import math
import shutil
from typing import Any, Dict, Generator, List
from datetime import datetime

from dify_plugin import Tool
from .style_config import StyleConfig, StyleRenderer, PRESET_STYLES, ColorScheme, NodeShape, LineStyle


class MindMapTimelineTool(Tool):
    
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
    
    def _parse_markdown_to_timeline(self, markdown_text: str) -> dict:
        """解析Markdown为时间线结构"""
        lines = markdown_text.strip().split('\n')
        
        timeline_title = "时间线"
        events = []
        current_event = None
        
        for line in lines:
            line = line.rstrip()
            if not line or line.startswith('```'):
                continue
            
            # 一级标题作为时间线标题
            if line.startswith('# '):
                timeline_title = line[2:].strip()
                
            # 二级标题作为时间节点
            elif line.startswith('## '):
                if current_event:
                    events.append(current_event)
                
                event_text = line[3:].strip()
                # 尝试提取时间信息
                time_info, event_name = self._extract_time_info(event_text)
                
                current_event = {
                    'time': time_info,
                    'name': event_name,
                    'details': [],
                    'milestones': []
                }
                
            # 三级标题作为里程碑
            elif line.startswith('### ') and current_event:
                milestone = line[4:].strip()
                current_event['milestones'].append(self._clean_markdown_text(milestone))
                
            # 列表项作为事件详情
            elif re.match(r'^\s*[-\*\+]\s+', line) and current_event:
                detail = re.sub(r'^\s*[-\*\+]\s*', '', line)
                current_event['details'].append(self._clean_markdown_text(detail))
        
        # 添加最后一个事件
        if current_event:
            events.append(current_event)
        
        # 如果没有找到事件，创建默认事件
        if not events:
            events = [{
                'time': '阶段1',
                'name': '请在Markdown中使用## 时间 事件名称来定义时间节点',
                'details': [],
                'milestones': []
            }]
        
        return {
            'title': timeline_title,
            'events': events
        }
    
    def _extract_time_info(self, text: str) -> tuple:
        """从文本中提取时间信息"""
        # 常见时间格式
        time_patterns = [
            r'(\d{4}年?\d{1,2}月?\d{1,2}?日?)',  # 2024年1月1日
            r'(\d{4}-\d{1,2}-\d{1,2})',          # 2024-01-01
            r'(\d{4}/\d{1,2}/\d{1,2})',          # 2024/01/01
            r'(\d{1,2}月\d{1,2}日)',             # 1月1日
            r'(第\d+阶段)',                      # 第1阶段
            r'(阶段\d+)',                        # 阶段1
            r'(\d{4}年)',                        # 2024年
            r'(Q[1-4])',                         # Q1
            r'(第[一二三四五六七八九十]+季度)',    # 第一季度
        ]
        
        for pattern in time_patterns:
            match = re.search(pattern, text)
            if match:
                time_part = match.group(1)
                remaining_text = text.replace(time_part, '').strip()
                # 清理剩余文本
                remaining_text = re.sub(r'^[-:\s]+', '', remaining_text)
                remaining_text = re.sub(r'[-:\s]+$', '', remaining_text)
                
                if not remaining_text:
                    remaining_text = '事件'
                
                return time_part, remaining_text
        
        # 如果没有找到时间格式，前半部分作为时间，后半部分作为事件
        parts = text.split(':', 1)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
        
        # 尝试用空格分割
        parts = text.split(' ', 1)
        if len(parts) == 2:
            return parts[0].strip(), parts[1].strip()
        
        return '时间点', text

    def _clean_markdown_text(self, text: str) -> str:
        """清理Markdown格式文本"""
        # 移除markdown格式符号，但保留完整内容
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # 移除粗体
        text = re.sub(r'\*(.*?)\*', r'\1', text)      # 移除斜体
        # 保留括号内容，不删除书名号
        return text.strip()

    def _draw_text_with_pil(self, img, draw, x, y, text, style_dict, color, font_file, 
                           angle=0, anchor_point='center'):
        """使用PIL绘制中文文本，支持旋转"""
        try:
            from PIL import ImageFont, ImageDraw, Image
            
            safe_text = str(text).strip()
            if not safe_text:
                safe_text = f"Event"
            
            print(f"Drawing timeline text: '{safe_text}' at ({x:.0f}, {y:.0f})")
            
            font_size = style_dict['font_size']
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
            
            # 计算文本大小
            bbox = draw.textbbox((0, 0), safe_text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # 根据锚点调整位置
            if anchor_point == 'center':
                text_x = x - text_width // 2
                text_y = y - text_height // 2
                box_x1 = x - text_width // 2 - padding
                box_y1 = y - text_height // 2 - padding
            elif anchor_point == 'top':
                text_x = x - text_width // 2
                text_y = y
                box_x1 = x - text_width // 2 - padding
                box_y1 = y - padding
            elif anchor_point == 'bottom':
                text_x = x - text_width // 2
                text_y = y - text_height
                box_x1 = x - text_width // 2 - padding
                box_y1 = y - text_height - padding
            else:
                text_x = x - text_width // 2
                text_y = y - text_height // 2
                box_x1 = x - text_width // 2 - padding
                box_y1 = y - text_height // 2 - padding
            
            box_x2 = box_x1 + text_width + padding * 2
            box_y2 = box_y1 + text_height + padding * 2
            
            # 绘制背景框
            if style_dict.get('show_background', True):
                if hasattr(self, 'style_renderer'):
                    self.style_renderer.draw_node_shape(
                        draw, (box_x1, box_y1, box_x2, box_y2), color, style_dict
                    )
                else:
                    draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], 
                                         radius=5, fill='white', outline=color, width=border_width)
            
            # 绘制文字
            draw.text((text_x, text_y), safe_text, font=font, fill=color)
            
            print(f"Successfully drew timeline text: '{safe_text}'")
            
        except Exception as e:
            print(f"PIL timeline text drawing error: {e}")

    def _generate_png_mindmap(self, timeline_data: dict, output_file: str, temp_dir: str, 
                             style_config: StyleConfig = None) -> bool:
        """生成时间线PNG思维导图"""
        try:
            print("Starting timeline generation...")
            
            if style_config is None:
                style_config = PRESET_STYLES['default']
            
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
            
            # 计算画布大小
            num_events = len(timeline_data['events'])
            
            width = max(16, min(24, 12 + num_events * 2.5))
            height = max(8, min(12, 6 + num_events * 0.8))
            
            fig, ax = plt.subplots(1, 1, figsize=(width, height))
            
            x_limit = max(10, num_events * 2)
            y_limit = 5
            
            ax.set_xlim(-x_limit, x_limit)
            ax.set_ylim(-y_limit, y_limit)
            ax.axis('off')
            
            fig.patch.set_facecolor(self.style_renderer.get_background_color())
            
            text_elements = []
            
            def store_text_element(x, y, text, depth_level, color='#333333', 
                                 anchor='center', show_bg=True):
                """存储文本元素供PIL渲染"""
                style = self.style_renderer.get_node_style(depth_level)
                style['show_background'] = show_bg
                text_elements.append({
                    'x': x, 'y': y, 'text': text, 
                    'depth_level': depth_level, 'color': color,
                    'style': style, 'anchor': anchor
                })

            def draw_timeline_structure():
                """绘制时间线结构"""
                # 主时间线（水平线）
                timeline_y = 0
                timeline_start_x = -x_limit + 3
                timeline_end_x = x_limit - 1
                
                # 绘制主时间线（较细的线）
                ax.plot([timeline_start_x, timeline_end_x], [timeline_y, timeline_y], 
                       color='#333333', linewidth=2.5, alpha=0.9)
                
                # 添加箭头
                arrow_size = 0.25
                ax.plot([timeline_end_x - arrow_size, timeline_end_x, timeline_end_x - arrow_size], 
                       [timeline_y + arrow_size/2, timeline_y, timeline_y - arrow_size/2], 
                       color='#333333', linewidth=2.5)
                
                # 标题（如果有单独的标题且不是默认值）
                title = timeline_data.get('title', '')
                if title and title != '时间线':
                    # 标题放在左侧，作为椭圆形节点
                    from matplotlib.patches import Ellipse
                    title_ellipse = Ellipse((timeline_start_x - 2, timeline_y), 3.5, 1.2, 
                                           facecolor='white', edgecolor='#4A90E2', linewidth=2)
                    ax.add_patch(title_ellipse)
                    store_text_element(timeline_start_x - 2, timeline_y, title, 1, '#333333')
                    
                    # 连接线
                    ax.plot([timeline_start_x - 0.3, timeline_start_x], [timeline_y, timeline_y], 
                           color='#4A90E2', linewidth=2)
                
                # 绘制时间事件
                events = timeline_data['events']
                if not events:
                    return
                
                # 计算事件位置（增加间距）
                has_title_node = title and title != '时间线'
                start_offset = 1 if has_title_node else 0
                # 增大间距系数，让节点之间有更多空间
                event_spacing = (timeline_end_x - timeline_start_x - start_offset - 4) / max(len(events), 1)
                
                # 添加"待定"节点（如果事件数量较少）
                total_nodes = events + [{'time': '待定', 'name': '', 'details': [], 'milestones': []}]
                
                for i, event in enumerate(total_nodes):
                    # 增加起始位置偏移，让节点更分散
                    event_x = timeline_start_x + start_offset + 2 + (i + 0.5) * event_spacing
                    
                    # 使用蓝色系配色
                    if i == len(events):  # 待定节点
                        node_color = '#4A90E2'
                        fill_color = 'white'
                    else:
                        node_color = '#4A90E2'
                        # 可以为特定索引的节点设置不同颜色
                        if i == 1:  # 例如第二个节点突出显示
                            fill_color = '#E8F4FD'
                        else:
                            fill_color = 'white'
                    
                    # 绘制椭圆形节点
                    from matplotlib.patches import Ellipse
                    node_ellipse = Ellipse((event_x, timeline_y), 2.2, 0.9, 
                                          facecolor=fill_color, edgecolor=node_color, 
                                          linewidth=2, zorder=5)
                    ax.add_patch(node_ellipse)
                    
                    # 节点上的文字（时间）
                    time_text = event['time']
                    store_text_element(event_x, timeline_y, time_text, 2, '#333333', 'center', False)
                    
                    # 绘制上方或下方的详情（垂直分布）
                    if event['name'] or event.get('details') or event.get('milestones'):
                        # 判断上下位置
                        is_upper = (i % 2 == 0)
                        
                        # 绘制连接线（小圆点）
                        dot_y = timeline_y + (0.5 if is_upper else -0.5)
                        circle = plt.Circle((event_x, dot_y), 0.06, 
                                          color=node_color, zorder=6)
                        ax.add_patch(circle)
                        
                        # 绘制详情框
                        details_y = timeline_y + (2.2 if is_upper else -2.2)
                        
                        # 收集所有要显示的文本
                        display_texts = []
                        if event['name']:
                            display_texts.append(event['name'])
                        
                        # 添加详情 - 增加显示数量
                        for detail in event.get('details', [])[:5]:  # 增加到5个
                            display_texts.append(detail)
                        
                        # 添加里程碑 - 增加显示数量
                        for milestone in event.get('milestones', [])[:5]:  # 增加到5个
                            display_texts.append(milestone)
                        
                        if display_texts:
                            # 为每个文本项创建单独的矩形框（垂直堆叠）
                            from matplotlib.patches import FancyBboxPatch
                            
                            # 计算起始位置
                            box_width = 1.8
                            box_height = 0.5
                            spacing = 0.05  # 框之间的间距
                            
                            # 计算总高度
                            total_height = len(display_texts) * box_height + (len(display_texts) - 1) * spacing
                            start_y = details_y + total_height / 2 - box_height / 2
                            
                            # 为每个文本创建单独的框
                            for j, text in enumerate(display_texts):
                                box_y = start_y - j * (box_height + spacing)
                                
                                # 绘制圆角矩形框
                                text_box = FancyBboxPatch(
                                    (event_x - box_width/2, box_y - box_height/2), 
                                    box_width, box_height,
                                    boxstyle="round,pad=0.05",
                                    facecolor='white', edgecolor=node_color,
                                    linewidth=1.5, zorder=3
                                )
                                ax.add_patch(text_box)
                                
                                # 添加文本
                                store_text_element(event_x, box_y, text, 3, '#333333', 'center', False)
                            
                            # 绘制连接线（从节点到第一个框）
                            line_start_y = timeline_y + (0.5 if is_upper else -0.5)
                            if is_upper:
                                line_end_y = start_y - box_height/2
                            else:
                                line_end_y = start_y - (len(display_texts) - 1) * (box_height + spacing) + box_height/2
                            
                            # 绘制垂直连接线
                            ax.plot([event_x, event_x], [line_start_y, line_end_y], 
                                   color=node_color, linewidth=1.2, alpha=0.8, linestyle='-')
            
            # 绘制时间线结构
            draw_timeline_structure()
            
            # 保存matplotlib图像
            temp_matplotlib_file = os.path.join(temp_dir, 'temp_timeline_matplotlib.png')
            plt.savefig(temp_matplotlib_file, dpi=150, bbox_inches='tight', 
                       facecolor=self.style_renderer.get_background_color())
            plt.close()
            
            # 用PIL处理文本
            img = Image.open(temp_matplotlib_file)
            draw = ImageDraw.Draw(img)
            
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
                self._draw_text_with_pil(img, draw, pil_x, pil_y, 
                                       element['text'], element['style'],
                                       element['color'], font_file,
                                       0, element.get('anchor', 'center'))
            
            # 保存最终图像
            img.save(output_file, 'PNG', dpi=(150, 150))
            
            # 清理临时文件
            if os.path.exists(temp_matplotlib_file):
                os.remove(temp_matplotlib_file)
            
            print(f"Timeline saved to: {output_file}")
            return True
            
        except Exception as e:
            print(f"Error generating timeline: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _invoke(self, tool_parameters: dict):
        """工具调用入口"""
        try:
            markdown_text = tool_parameters.get('markdown_text', '')
            style_preset = tool_parameters.get('style_preset', 'default')
            
            style_config = PRESET_STYLES.get(style_preset, PRESET_STYLES['default'])
            
            if not markdown_text.strip():
                yield self.create_text_message('请提供有效的Markdown文本')
                return
            
            timeline_data = self._parse_markdown_to_timeline(markdown_text)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                output_file = os.path.join(temp_dir, f'timeline_mindmap_{int(time.time())}.png')
                
                success = self._generate_png_mindmap(timeline_data, output_file, temp_dir, style_config)
                
                if success and os.path.exists(output_file):
                    with open(output_file, 'rb') as f:
                        file_content = f.read()
                    
                    # 计算文件大小
                    file_size = len(file_content)
                    size_mb = file_size / (1024 * 1024)
                    size_text = f"{size_mb:.2f}M"
                    
                    yield self.create_blob_message(
                        blob=file_content,
                        meta={'mime_type': 'image/png', 'filename': f'timeline_mindmap_{int(time.time())}.png'}
                    )
                    yield self.create_text_message(f'时间线图生成成功！适合项目规划和时间序列展示。文件大小: {size_text}')
                else:
                    yield self.create_text_message('生成时间线图失败，请检查输入内容')
                    
        except Exception as e:
            print(f"Error in _invoke: {e}")
            import traceback
            traceback.print_exc()
            yield self.create_text_message(f'生成时间线图时发生错误：{str(e)}')