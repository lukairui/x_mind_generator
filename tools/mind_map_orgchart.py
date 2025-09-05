#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Organizational Chart Mind Map Tool
Generates organizational chart layout from Markdown text
Perfect for hierarchical structures and team organization
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


class MindMapOrgChartTool(Tool):
    
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
    
    def _parse_markdown_to_tree(self, markdown_text: str) -> dict:
        """通用Markdown解析器"""
        lines = markdown_text.strip().split('\n')
        nodes = []
        node_stack = []
        last_header_level = 0
        
        for line in lines:
            line = line.rstrip()
            if not line or line.startswith('```'):
                continue
                
            level = 0
            content = ""
            is_header = False
            
            if line.startswith('#'):
                header_count = 0
                for char in line:
                    if char == '#':
                        header_count += 1
                    else:
                        break
                level = header_count
                content = line[header_count:].strip()
                is_header = True
                last_header_level = level
                
            elif re.match(r'^\s*\d+\.\s+', line):
                leading_spaces = len(line) - len(line.lstrip())
                level = leading_spaces // 2 + 2
                content = re.sub(r'^\s*\d+\.\s*', '', line)
                content = self._clean_markdown_text(content)
                
            elif re.match(r'^\s*[-\*\+]\s+', line):
                leading_spaces = len(line) - len(line.lstrip())
                
                if leading_spaces == 0 and last_header_level > 0:
                    level = last_header_level + 1
                else:
                    level = leading_spaces // 2 + 2
                    
                content = re.sub(r'^\s*[-\*\+]\s*', '', line)
                content = self._clean_markdown_text(content)
                
            else:
                continue
                
            if not content:
                continue
                
            node = {
                'content': content,
                'level': level,
                'children': []
            }
            
            if not is_header and not re.match(r'^\s*[-\*\+]\s+', line):
                last_header_level = 0
            
            while node_stack and node_stack[-1]['level'] >= level:
                node_stack.pop()
            
            if node_stack:
                node_stack[-1]['children'].append(node)
            else:
                nodes.append(node)
            
            node_stack.append(node)
        
        if not nodes:
            return {'content': 'Organization', 'level': 1, 'children': []}
            
        if len(nodes) == 1:
            return nodes[0]
        
        return {
            'content': 'Organization',
            'level': 1, 
            'children': nodes
        }

    def _wrap_text(self, text, max_chars_per_line=8, max_lines=3):
        """文字换行处理，超过8个字符换行，最多3行，其他用省略号"""
        if not text:
            return ["Position"]
            
        # 清理文本
        text = str(text).strip()
        if not text:
            return ["Position"]
            
        lines = []
        remaining = text
        
        for line_num in range(max_lines):
            if not remaining:
                break
                
            if len(remaining) <= max_chars_per_line:
                # 如果剩余文字不超过一行，直接添加
                lines.append(remaining)
                break
            elif line_num == max_lines - 1:
                # 最后一行，需要添加省略号
                if len(remaining) > max_chars_per_line - 1:
                    lines.append(remaining[:max_chars_per_line-1] + "…")
                else:
                    lines.append(remaining)
                break
            else:
                # 中间行，正常截取
                lines.append(remaining[:max_chars_per_line])
                remaining = remaining[max_chars_per_line:]
                
        return lines if lines else ["Position"]

    def _clean_markdown_text(self, text: str) -> str:
        """清理Markdown格式文本"""
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        text = text.replace('《', '').replace('》', '')
        text = re.sub(r'\*\*(.*?)\*\*:\s*', r'\1: ', text)
        return text.strip()

    def _calculate_tree_depth(self, node: dict) -> int:
        """计算树的最大深度"""
        if not node.get('children'):
            return 1
        return 1 + max(self._calculate_tree_depth(child) for child in node['children'])

    def _calculate_tree_width(self, node: dict) -> int:
        """计算树的最大宽度"""
        if not node.get('children'):
            return 1
        return sum(self._calculate_tree_width(child) for child in node['children'])

    def _draw_rounded_rectangle(self, draw, bbox, fill, outline, width, radius=10):
        """绘制圆角矩形"""
        x1, y1, x2, y2 = bbox
        
        # 绘制圆角矩形
        draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, 
                               fill=fill, outline=outline, width=width)
    
    def _draw_text_with_pil(self, img, draw, x, y, text, style_dict, color, font_file):
        """使用PIL绘制中文文本"""
        try:
            from PIL import ImageFont, ImageDraw
            
            # 使用换行处理
            text_lines = self._wrap_text(text, max_chars_per_line=8, max_lines=3)
            
            print(f"Drawing org chart text: {text_lines} at ({x:.0f}, {y:.0f})")
            
            font_size = 14  # 固定合适的字体大小
            padding = 10  # 固定内边距
            border_width = 2  # 固定边框宽度
            
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
            
            # 计算多行文本的尺寸
            max_line_width = 0
            line_height = 0
            
            for line in text_lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                if line_height == 0:
                    line_height = bbox[3] - bbox[1]
                max_line_width = max(max_line_width, line_width)
            
            total_text_height = line_height * len(text_lines) + (len(text_lines) - 1) * 1  # 更小的行间距
            
            # 组织架构图使用更紧凑的矩形
            box_width = max(max_line_width + padding * 2, 90)  # 更小的最小宽度
            box_height = total_text_height + padding * 2
            
            box_x1 = x - box_width // 2
            box_y1 = y - box_height // 2
            box_x2 = x + box_width // 2
            box_y2 = y + box_height // 2
            
            # 绘制填充的圆角蓝色矩形节点
            node_color = '#87CEEB'  # 天蓝色
            text_color = '#000000'  # 黑色文字
            
            # 绘制圆角矩形
            try:
                # 使用rounded_rectangle方法（PIL 8.2.0+）
                draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], 
                                      radius=8, fill=node_color, 
                                      outline='#333333', width=border_width)
            except AttributeError:
                # 如果没有rounded_rectangle方法，使用普通矩形
                draw.rectangle([box_x1, box_y1, box_x2, box_y2], 
                             fill=node_color, outline='#333333', width=border_width)
            
            # 绘制多行文本
            start_y = y - total_text_height // 2
            for i, line in enumerate(text_lines):
                line_bbox = draw.textbbox((0, 0), line, font=font)
                line_width = line_bbox[2] - line_bbox[0]
                text_x = x - line_width // 2
                text_y = start_y + i * (line_height + 1)  # 减小行间距到1px
                draw.text((text_x, text_y), line, font=font, fill=text_color)
            
            print(f"Successfully drew org chart text: {text_lines}")
            
        except Exception as e:
            print(f"PIL org chart text drawing error: {e}")

    def _generate_png_mindmap(self, tree_data: dict, output_file: str, temp_dir: str, 
                             style_config: StyleConfig = None) -> bool:
        """生成组织架构图PNG"""
        try:
            print("Starting organizational chart generation...")
            
            if style_config is None:
                style_config = PRESET_STYLES['business']  # 组织架构图默认使用商务风格
            
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
            
            # 计算画布大小 - 增加宽度以显示完整内容
            tree_depth = self._calculate_tree_depth(tree_data)
            tree_width = self._calculate_tree_width(tree_data)
            
            # 增加画布宽度，保持高度紧凑
            width = min(max(18, tree_width * 2.2), 32)    # 增加宽度
            height = min(max(10, tree_depth * 2.5), 16)   # 保持紧凑高度
            
            fig, ax = plt.subplots(1, 1, figsize=(width, height))
            
            # 根据内容调整坐标范围 - 增加水平空间
            x_limit = max(14, tree_width * 1.8)  # 增加水平空间
            y_limit = max(8, tree_depth * 1.8)   # 保持紧凑的垂直空间
            
            ax.set_xlim(-x_limit, x_limit)
            ax.set_ylim(-y_limit, y_limit)
            ax.axis('off')
            
            fig.patch.set_facecolor(self.style_renderer.get_background_color())
            
            text_elements = []
            
            def store_text_element(x, y, text, depth_level, color='#333333'):
                """存储文本元素供PIL渲染"""
                style = self.style_renderer.get_node_style(depth_level)
                text_elements.append({
                    'x': x, 'y': y, 'text': text, 
                    'depth_level': depth_level, 'color': color,
                    'style': style
                })

            def layout_org_chart(node, x=0, y=None, depth_level=1, available_width=None):
                """组织架构图布局算法"""
                content = node.get('content', 'Position')
                children = node.get('children', [])
                
                # 如果y未指定，则根据树深度计算起始位置
                if y is None:
                    y = y_limit * 0.8  # 从80%的高度开始
                
                # 获取颜色（组织架构图使用层级颜色）
                color = self.style_renderer.get_color(depth_level - 1)
                
                # 存储当前节点文本
                store_text_element(x, y, content, depth_level, color)
                
                if not children:
                    return [(x, y)]
                
                # 计算子节点布局
                num_children = len(children)
                if available_width is None:
                    available_width = x_limit * 1.6
                
                # 子节点水平间距 - 适度增加以避免重叠
                min_spacing = 2.5  # 适度增加最小间距
                child_spacing = max(min_spacing, 
                                   min(available_width / max(num_children, 1), 
                                       available_width / 2) * 1.0)  # 正常spacing系数
                
                # 计算起始位置
                total_width = (num_children - 1) * child_spacing
                start_x = x - total_width / 2
                
                # 下一层Y坐标 - 紧凑的垂直间距
                vertical_spacing = y_limit / tree_depth * 0.9  # 减小垂直间距
                next_y = y - vertical_spacing
                
                child_positions = []
                
                # 绘制连接线 - 每个父节点独立管理自己的子节点连接
                if num_children > 0:
                    line_color = '#333333'  # 使用深色连接线
                    line_width = 2  # 固定线宽
                    line_opacity = 1.0  # 不透明
                    mid_y = y - vertical_spacing / 2
                    
                    # 从父节点画垂直线到中间位置
                    ax.plot([x, x], [y - 0.3, mid_y], 
                           color=line_color, linewidth=line_width, 
                           alpha=line_opacity)
                    
                    # 只有多个子节点时才画水平连接线
                    # 每个父节点只连接自己的子节点
                    if num_children > 1:
                        leftmost_x = start_x
                        rightmost_x = start_x + (num_children - 1) * child_spacing
                        ax.plot([leftmost_x, rightmost_x], [mid_y, mid_y], 
                               color=line_color, linewidth=line_width, 
                               alpha=line_opacity)
                    
                    # 为每个子节点画垂直连接线
                    for i, child in enumerate(children):
                        child_x = start_x + i * child_spacing
                        
                        # 从中间水平线（或父节点）画垂直线到子节点
                        if num_children == 1:
                            # 如果只有一个子节点，直接从父节点连到子节点
                            ax.plot([x, x], [mid_y, next_y + 0.3], 
                                   color=line_color, linewidth=line_width, 
                                   alpha=line_opacity)
                        else:
                            # 多个子节点时，从水平线位置画到子节点
                            ax.plot([child_x, child_x], [mid_y, next_y + 0.3], 
                                   color=line_color, linewidth=line_width, 
                                   alpha=line_opacity)
                        
                        # 递归布局子节点
                        child_positions.extend(
                            layout_org_chart(child, child_x, next_y, depth_level + 1, 
                                           child_spacing * 1.2)  # 正常子节点可用宽度
                        )
                else:
                    # 没有子节点的情况
                    pass
                
                return [(x, y)] + child_positions
            
            # 布局组织架构图
            positions = layout_org_chart(tree_data)
            
            # 保存matplotlib图像，减小边距
            temp_matplotlib_file = os.path.join(temp_dir, 'temp_orgchart_matplotlib.png')
            plt.savefig(temp_matplotlib_file, dpi=150, bbox_inches='tight', 
                       facecolor=self.style_renderer.get_background_color(),
                       pad_inches=0.2)  # 减小边距
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
                                       element['color'], font_file)
            
            # 保存最终图像
            img.save(output_file, 'PNG', dpi=(150, 150))
            
            # 清理临时文件
            if os.path.exists(temp_matplotlib_file):
                os.remove(temp_matplotlib_file)
            
            print(f"Organizational chart saved to: {output_file}")
            return True
            
        except Exception as e:
            print(f"Error generating organizational chart: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _invoke(self, tool_parameters: dict):
        """工具调用入口"""
        try:
            markdown_text = tool_parameters.get('markdown_text', '')
            style_preset = tool_parameters.get('style_preset', 'business')
            
            style_config = PRESET_STYLES.get(style_preset, PRESET_STYLES['business'])
            
            if not markdown_text.strip():
                yield self.create_text_message('请提供有效的Markdown文本')
                return
            
            tree_data = self._parse_markdown_to_tree(markdown_text)
            
            with tempfile.TemporaryDirectory() as temp_dir:
                output_file = os.path.join(temp_dir, f'orgchart_mindmap_{int(time.time())}.png')
                
                success = self._generate_png_mindmap(tree_data, output_file, temp_dir, style_config)
                
                if success and os.path.exists(output_file):
                    with open(output_file, 'rb') as f:
                        file_content = f.read()
                    
                    # 计算文件大小
                    file_size = len(file_content)
                    size_mb = file_size / (1024 * 1024)
                    size_text = f"{size_mb:.2f}M"
                    
                    yield self.create_blob_message(
                        blob=file_content,
                        meta={'mime_type': 'image/png', 'filename': f'orgchart_mindmap_{int(time.time())}.png'}
                    )
                    yield self.create_text_message(f'组织架构图生成成功！适合展示层级结构和团队组织。文件大小: {size_text}')
                else:
                    yield self.create_text_message('生成组织架构图失败，请检查输入内容')
                    
        except Exception as e:
            print(f"Error in _invoke: {e}")
            import traceback
            traceback.print_exc()
            yield self.create_text_message(f'生成组织架构图时发生错误：{str(e)}')