#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vertical Tree Layout Mind Map Tool
Generates top-to-bottom tree mind maps from Markdown text
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


class MindMapVerticalTool(Tool):
    
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
            
            # 处理标题 (# ## ### ...)
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
                
            # 处理数字列表 (1. 2. 3. ...)
            elif re.match(r'^\s*\d+\.\s+', line):
                leading_spaces = len(line) - len(line.lstrip())
                level = leading_spaces // 2 + 2
                content = re.sub(r'^\s*\d+\.\s*', '', line)
                content = self._clean_markdown_text(content)
                
            # 处理无序列表 (- * +)
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
                
            # 创建节点
            node = {
                'content': content,
                'level': level,
                'children': []
            }
            
            # 重置last_header_level
            if not is_header and not re.match(r'^\s*[-\*\+]\s+', line):
                last_header_level = 0
            
            # 调整栈 - 移除level >= 当前level的节点
            while node_stack and node_stack[-1]['level'] >= level:
                node_stack.pop()
            
            # 添加到正确的父节点
            if node_stack:
                node_stack[-1]['children'].append(node)
            else:
                nodes.append(node)
            
            # 当前节点入栈
            node_stack.append(node)
        
        # 处理结果
        if not nodes:
            return {'content': 'Mind Map', 'level': 1, 'children': []}
            
        if len(nodes) == 1:
            return nodes[0]
        
        # 多个根节点 - 创建包装器
        return {
            'content': 'Mind Map',
            'level': 1, 
            'children': nodes
        }

    def _smart_text_wrap(self, text: str, max_chars_per_line: int = 15) -> str:
        """智能文本换行处理，保持完整性，优先在合适位置断行"""
        if not text or len(text) <= max_chars_per_line:
            return text
        
        # 清理文本
        text = text.strip()
        
        # 简单的方案：对于长文本，优先在空格和特殊字符处断行
        lines = []
        current_line = ""
        words = []
        current_word = ""
        
        # 逐字符处理，识别单词边界
        for char in text:
            if char in ' 	（）()[]{},.;:。、，：；“”《》':
                # 遇到分隔符，结束当前单词
                if current_word:
                    words.append(current_word)
                    current_word = ""
                if char.strip():  # 保留非空格分隔符
                    words.append(char)
            else:
                current_word += char
        
        # 添加最后一个单词
        if current_word:
            words.append(current_word)
        
        # 按单词组装行
        for word in words:
            # 如果当前行加上这个单词不会超过限制
            if len(current_line) + len(word) <= max_chars_per_line:
                current_line += word
            else:
                # 如果当前行有内容，先保存
                if current_line.strip():
                    lines.append(current_line.strip())
                
                # 如果单个单词太长，强制分割
                if len(word) > max_chars_per_line:
                    for i in range(0, len(word), max_chars_per_line):
                        chunk = word[i:i + max_chars_per_line]
                        lines.append(chunk)
                    current_line = ""
                else:
                    current_line = word
        
        # 添加最后一行
        if current_line.strip():
            lines.append(current_line.strip())
        
        # 如果只有一行，直接返回
        if len(lines) <= 1:
            return text
        
        # 组合成换行文本，除了第一行，其他行句首加两个空格
        result_lines = [lines[0]]
        for line in lines[1:]:
            result_lines.append("  " + line)
        
        return "\n".join(result_lines)

    def _clean_markdown_text(self, text: str) -> str:
        """清理Markdown格式文本"""
        # 移除 **粗体** 格式
        text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
        # 移除 *斜体* 格式  
        text = re.sub(r'\*(.*?)\*', r'\1', text)
        # 移除 《》 括号
        text = text.replace('《', '').replace('》', '')
        # 处理 **粗体**: 模式 - 保留冒号
        text = re.sub(r'\*\*(.*?)\*\*:\s*', r'\1: ', text)
        return text.strip()

    def _calculate_tree_depth(self, node: dict) -> int:
        """计算树的最大深度"""
        if not node.get('children'):
            return 1
        return 1 + max(self._calculate_tree_depth(child) for child in node['children'])

    def _calculate_tree_width(self, node: dict) -> int:
        """计算树的最大宽度（叶子节点数量）"""
        if not node.get('children'):
            return 1
        return sum(self._calculate_tree_width(child) for child in node['children'])

    def _calculate_required_canvas_size(self, tree_data: dict) -> tuple:
        """智能计算所需的画布尺寸，确保所有节点都能显示"""
        
        def calculate_node_width(text):
            """估算节点文本的显示宽度"""
            if not text:
                return 2.0
            
            # 中文字符宽度约为英文的2倍
            chinese_chars = len([c for c in text if ord(c) > 127])
            english_chars = len(text) - chinese_chars
            
            # 基础宽度估算（考虑换行）
            wrapped_text = self._smart_text_wrap(text, max_chars_per_line=15)
            lines = wrapped_text.split('\n')
            max_line_length = max(len(line.strip()) for line in lines)
            
            # 估算显示宽度（单位：坐标系单位）
            estimated_width = max_line_length * 0.15 + 1.0  # 加上padding
            return max(2.0, estimated_width)
        
        def calculate_subtree_width(node, depth_level=1):
            """递归计算子树所需的宽度"""
            children = node.get('children', [])
            
            if not children:
                # 叶子节点：返回自身宽度
                return calculate_node_width(node.get('content', 'Node'))
            
            # 计算所有子节点的宽度需求
            child_widths = []
            for child in children:
                child_width = calculate_subtree_width(child, depth_level + 1)
                child_widths.append(child_width)
            
            # 计算子节点布局所需的总宽度
            num_children = len(children)
            
            # 根据层级确定基础间距
            if depth_level == 1:
                base_spacing = 7.0  # 主分支间距大
            elif depth_level == 2:
                base_spacing = 4.5  # 二级分支间距中等
            else:
                base_spacing = 3.5  # 叶子节点间距小
            
            # 计算总宽度：节点宽度 + 间距
            total_child_width = sum(child_widths)
            total_spacing = (num_children - 1) * base_spacing if num_children > 1 else 0
            subtree_width = total_child_width + total_spacing
            
            # 返回子树宽度和当前节点宽度的最大值
            current_node_width = calculate_node_width(node.get('content', 'Node'))
            return max(subtree_width, current_node_width)
        
        # 计算所需的宽度和高度
        tree_depth = self._calculate_tree_depth(tree_data)
        required_width = calculate_subtree_width(tree_data)
        
        print(f"Calculated required width: {required_width}, tree depth: {tree_depth}")
        
        # 计算画布尺寸（英寸）
        # 宽度：根据内容需求动态调整，但设置合理的最小值和最大值
        min_width = 12
        max_width = 50  # 增加最大宽度限制
        canvas_width = max(min_width, min(max_width, required_width * 0.8 + 8))
        
        # 高度：根据树深度调整
        min_height = 10
        max_height = 30  # 增加最大高度限制
        canvas_height = max(min_height, min(max_height, tree_depth * 4 + 6))
        
        # 坐标系范围
        x_limit = required_width * 0.6 + 4  # 给边缘留出空间
        y_limit = tree_depth * 4 + 3
        
        return canvas_width, canvas_height, x_limit, y_limit

    def _draw_text_with_pil(self, img, draw, x, y, text, style_dict, color, font_file):
        """使用PIL绘制中文文本，支持智能换行"""
        try:
            from PIL import ImageFont, ImageDraw
            
            safe_text = str(text).strip()
            if not safe_text:
                safe_text = f"Node"
            
            # 应用智能换行处理 - 增加每行字符数，显示更多内容
            wrapped_text = self._smart_text_wrap(safe_text, max_chars_per_line=15)
            
            # 添加调试信息
            print(f"Original: '{safe_text}'")
            print(f"Wrapped: '{wrapped_text}'")
            
            print(f"Drawing vertical text with PIL: '{safe_text}' -> '{wrapped_text}' at ({x:.0f}, {y:.0f})")
            
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
            
            # 处理多行文本
            lines = wrapped_text.split('\n')
            line_height = font_size + 4  # 行间距
            
            # 计算整个文本块的尺寸
            max_line_width = 0
            total_height = len(lines) * line_height
            
            for line in lines:
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                max_line_width = max(max_line_width, line_width)
            
            # 绘制背景框（整个文本块）
            box_x1 = x - max_line_width // 2 - padding
            box_y1 = y - total_height // 2 - padding
            box_x2 = x + max_line_width // 2 + padding
            box_y2 = y + total_height // 2 + padding
            
            # 使用样式渲染器绘制节点形状
            from .style_config import StyleRenderer
            if hasattr(self, 'style_renderer'):
                self.style_renderer.draw_node_shape(
                    draw, (box_x1, box_y1, box_x2, box_y2), color, style_dict
                )
            else:
                # 默认圆角矩形
                draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], 
                                     radius=5, fill='white', outline=color, width=border_width)
            
            # 绘制每一行文本
            start_y = y - total_height // 2
            for i, line in enumerate(lines):
                # 计算当前行的位置
                bbox = draw.textbbox((0, 0), line, font=font)
                line_width = bbox[2] - bbox[0]
                text_x = x - line_width // 2
                text_y = start_y + i * line_height
                
                draw.text((text_x, text_y), line, font=font, fill=color)
            
            print(f"Successfully drew vertical wrapped text: '{wrapped_text}'")
            
        except Exception as e:
            print(f"PIL vertical text drawing error: {e}")

    def _generate_png_mindmap(self, tree_data: dict, output_file: str, temp_dir: str, 
                             style_config: StyleConfig = None) -> bool:
        """生成垂直树状PNG思维导图"""
        try:
            print("Starting vertical tree mind map generation...")
            
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
            
            # 使用智能画布尺寸计算
            canvas_width, canvas_height, x_limit, y_limit = self._calculate_required_canvas_size(tree_data)
            
            print(f"Canvas size: {canvas_width:.1f}x{canvas_height:.1f} inches")
            print(f"Coordinate limits: x=±{x_limit:.1f}, y=±{y_limit:.1f}")
            
            fig, ax = plt.subplots(1, 1, figsize=(canvas_width, canvas_height))
            
            ax.set_xlim(-x_limit, x_limit)
            ax.set_ylim(-y_limit, y_limit)
            ax.axis('off')
            
            # 设置背景颜色
            fig.patch.set_facecolor(self.style_renderer.get_background_color())
            
            # 存储文本信息，稍后用PIL绘制
            text_elements = []
            
            def store_text_element(x, y, text, depth_level, color='#333333'):
                """存储文本元素供PIL渲染"""
                style = self.style_renderer.get_node_style(depth_level)
                text_elements.append({
                    'x': x, 'y': y, 'text': text, 
                    'depth_level': depth_level, 'color': color,
                    'style': style
                })

            def calculate_node_width(text):
                """估算节点文本的显示宽度"""
                if not text:
                    return 2.0
                
                # 中文字符宽度约为英文的2倍
                chinese_chars = len([c for c in text if ord(c) > 127])
                english_chars = len(text) - chinese_chars
                
                # 基础宽度估算（考虑换行）
                wrapped_text = self._smart_text_wrap(text, max_chars_per_line=15)
                lines = wrapped_text.split('\n')
                max_line_length = max(len(line.strip()) for line in lines)
                
                # 估算显示宽度（单位：坐标系单位）
                estimated_width = max_line_length * 0.15 + 1.0  # 加上padding
                return max(2.0, estimated_width)

            def layout_vertical_tree(node, x=0, y=None, depth_level=1, branch_index=0, available_width=None, parent_left=None, parent_right=None):
                """严格层级布局算法 - 避免连线交叉，每个父节点的子节点只在其区域内"""
                if y is None:
                    y = y_limit * 0.8  # 从顶部开始
                
                if available_width is None:
                    available_width = x_limit * 1.6  # 可用宽度
                
                # 如果有父节点边界限制，使用更严格的可用宽度
                if parent_left is not None and parent_right is not None:
                    available_width = parent_right - parent_left
                
                content = node.get('content', 'Node')
                children = node.get('children', [])
                
                # 获取颜色
                color = self.style_renderer.get_color(branch_index)
                
                # 存储当前节点文本
                store_text_element(x, y, content, depth_level, color)
                
                if not children:
                    return [(x, y)]
                
                # 计算子节点布局 - 严格层级布局，避免交叉
                num_children = len(children)
                
                # 垂直间距：根据层级调整
                if depth_level == 1:
                    level_spacing = 4.5 * style_config.level_spacing  # 主标题到分类
                elif depth_level == 2:
                    level_spacing = 3.8 * style_config.level_spacing  # 分类到子项
                else:
                    level_spacing = 3.2 * style_config.level_spacing  # 其他层级
                
                next_y = y - level_spacing
                
                # 计算每个子节点的预估宽度
                child_widths = []
                for child in children:
                    child_content = child.get('content', 'Node')
                    width = calculate_node_width(child_content)
                    child_widths.append(width)
                
                # 严格层级布局算法 - 先分配区域，再在区域内布局
                # 确定当前节点的可用宽度范围
                if parent_left is not None and parent_right is not None:
                    # 有父节点边界限制，严格在边界内分布
                    left_bound = parent_left
                    right_bound = parent_right
                else:
                    # 根节点或第一层，使用整个可用宽度
                    left_bound = x - available_width / 2
                    right_bound = x + available_width / 2
                
                if num_children == 1:
                    # 单个子节点：在父节点区域中心
                    child_positions_x = [x]
                    # 子节点区域边界
                    child_regions = [(left_bound, right_bound)]
                else:
                    # 多个子节点：平均分配父节点区域，每个子节点在其分配区域的中心
                    region_width = (right_bound - left_bound) / num_children
                    child_positions_x = []
                    child_regions = []
                    
                    for i in range(num_children):
                        # 计算子节点的区域边界
                        child_left = left_bound + i * region_width
                        child_right = left_bound + (i + 1) * region_width
                        child_regions.append((child_left, child_right))
                        
                        # 子节点位置在其区域的中心
                        child_center = (child_left + child_right) / 2
                        child_positions_x.append(child_center)
                
                child_positions = []
                
                for i, child in enumerate(children):
                    child_x = child_positions_x[i]
                    child_branch_index = i if depth_level == 1 else branch_index
                    
                    # 绘制连接线
                    line_style = self.style_renderer.get_line_style(depth_level)
                    line_color = color
                    
                    if hasattr(self.style_renderer, 'draw_connection_line'):
                        self.style_renderer.draw_connection_line(
                            ax, (x, y), (child_x, next_y), line_color, line_style
                        )
                    else:
                        # 默认连线 - 垂直树状线条
                        ax.plot([x, child_x], [y, next_y], 
                               color=line_color, linewidth=line_style['width'], 
                               alpha=line_style['opacity'])
                    
                    # 为子节点计算可用宽度（避免兄弟节点重叠）
                    if i == 0:
                        if num_children > 1:
                            child_available_width = abs(child_positions_x[1] - child_x) * 1.8
                        else:
                            child_available_width = available_width * 0.8
                    elif i == num_children - 1:
                        child_available_width = abs(child_x - child_positions_x[i - 1]) * 1.8
                    else:
                        left_space = abs(child_x - child_positions_x[i - 1])
                        right_space = abs(child_positions_x[i + 1] - child_x)
                        child_available_width = min(left_space, right_space) * 1.8
                    
                    # 使用预分配的区域边界进行递归布局
                    child_left, child_right = child_regions[i]
                    
                    # 递归布局子节点，传递严格的边界限制
                    child_positions.extend(
                        layout_vertical_tree(child, child_x, next_y, depth_level + 1, 
                                           child_branch_index, child_right - child_left,
                                           child_left, child_right)
                    )
                
                return [(x, y)] + child_positions
            
            # 布局树状结构 - 传递可用宽度
            available_width = x_limit * 1.6  # 可用宽度为坐标系宽度的80%
            positions = layout_vertical_tree(tree_data, available_width=available_width)
            
            # 保存matplotlib图像
            temp_matplotlib_file = os.path.join(temp_dir, 'temp_vertical_matplotlib.png')
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
                self._draw_text_with_pil(img, draw, pil_x, pil_y, 
                                       element['text'], element['style'],
                                       element['color'], font_file)
            
            # 保存最终图像
            img.save(output_file, 'PNG', dpi=(150, 150))
            
            # 清理临时文件
            if os.path.exists(temp_matplotlib_file):
                os.remove(temp_matplotlib_file)
            
            print(f"Vertical tree mind map saved to: {output_file}")
            return True
            
        except Exception as e:
            print(f"Error generating vertical tree mind map: {e}")
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
            
            # 解析Markdown
            tree_data = self._parse_markdown_to_tree(markdown_text)
            
            # 添加调试信息
            def print_tree_structure(node, indent=0):
                prefix = "  " * indent
                print(f"{prefix}- {node.get('content', 'Unknown')} (level: {node.get('level', 'Unknown')})")
                for child in node.get('children', []):
                    print_tree_structure(child, indent + 1)
            
            print("=== 解析的树结构 ===")
            print_tree_structure(tree_data)
            print("========================")
            
            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                output_file = os.path.join(temp_dir, f'vertical_mindmap_{int(time.time())}.png')
                
                # 生成思维导图
                success = self._generate_png_mindmap(tree_data, output_file, temp_dir, style_config)
                
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
                        meta={'mime_type': 'image/png', 'filename': f'vertical_mindmap_{int(time.time())}.png'}
                    )
                    yield self.create_text_message(f'垂直树状思维导图生成成功！文件大小: {size_text}')
                else:
                    yield self.create_text_message('生成垂直树状思维导图失败，请检查输入内容')
                    
        except Exception as e:
            print(f"Error in _invoke: {e}")
            import traceback
            traceback.print_exc()
            yield self.create_text_message(f'生成垂直树状思维导图时发生错误：{str(e)}')