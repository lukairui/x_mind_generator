#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Output Module for Mind Maps
Converts mind map images and SVG to high-quality PDF format
Provides professional output suitable for printing and document sharing
"""

import os
import tempfile
from typing import Optional, Tuple
from io import BytesIO


class PDFRenderer:
    """PDF渲染器"""
    
    def __init__(self, page_size: str = 'A4', orientation: str = 'landscape', 
                 margin: float = 20, quality: int = 300):
        """
        初始化PDF渲染器
        
        Args:
            page_size: 页面大小 ('A4', 'A3', 'Letter', 'Custom')
            orientation: 页面方向 ('portrait', 'landscape')
            margin: 页边距 (单位: mm)
            quality: 图像质量 (DPI)
        """
        self.page_size = page_size
        self.orientation = orientation
        self.margin = margin
        self.quality = quality
        
        # 页面尺寸定义 (mm)
        self.page_sizes = {
            'A4': (210, 297),
            'A3': (297, 420),
            'Letter': (216, 279),
            'Legal': (216, 356),
            'Custom': (300, 400)
        }
    
    def get_page_dimensions(self) -> Tuple[float, float]:
        """获取页面尺寸"""
        width, height = self.page_sizes.get(self.page_size, self.page_sizes['A4'])
        
        if self.orientation == 'landscape':
            width, height = height, width
        
        return width, height
    
    def png_to_pdf(self, png_path: str, output_path: str, title: str = "") -> bool:
        """将PNG图像转换为PDF"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import letter, A4, A3
            from reportlab.lib.units import mm
            from PIL import Image
            
            # 获取页面尺寸
            page_width, page_height = self.get_page_dimensions()
            page_width_pt = page_width * mm
            page_height_pt = page_height * mm
            
            # 创建PDF
            c = canvas.Canvas(output_path, pagesize=(page_width_pt, page_height_pt))
            
            # 添加标题
            if title:
                c.setFont("Helvetica-Bold", 16)
                c.drawString(self.margin * mm, (page_height - self.margin - 10) * mm, title)
            
            # 打开PNG图像
            img = Image.open(png_path)
            img_width, img_height = img.size
            
            # 计算可用空间
            available_width = (page_width - 2 * self.margin) * mm
            available_height = (page_height - 2 * self.margin - (20 if title else 0)) * mm
            
            # 计算缩放比例
            scale_width = available_width / img_width
            scale_height = available_height / img_height
            scale = min(scale_width, scale_height)
            
            # 计算实际显示尺寸
            display_width = img_width * scale
            display_height = img_height * scale
            
            # 计算居中位置
            x = (page_width_pt - display_width) / 2
            y = (page_height_pt - display_height) / 2
            
            # 如果有标题，稍微下移
            if title:
                y -= 10 * mm
            
            # 将图像绘制到PDF
            c.drawImage(png_path, x, y, width=display_width, height=display_height)
            
            # 保存PDF
            c.save()
            
            print(f"PDF saved successfully: {output_path}")
            return True
            
        except ImportError:
            print("ReportLab not available. Installing...")
            try:
                import subprocess
                import sys
                subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
                return self.png_to_pdf(png_path, output_path, title)
            except Exception as e:
                print(f"Failed to install ReportLab: {e}")
                return False
            
        except Exception as e:
            print(f"Error converting PNG to PDF: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def svg_to_pdf(self, svg_path: str, output_path: str, title: str = "") -> bool:
        """将SVG图像转换为PDF"""
        try:
            # 先将SVG转换为PNG，然后转换为PDF
            temp_png = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            temp_png.close()
            
            if self.svg_to_png(svg_path, temp_png.name):
                result = self.png_to_pdf(temp_png.name, output_path, title)
                os.unlink(temp_png.name)
                return result
            else:
                os.unlink(temp_png.name)
                return False
                
        except Exception as e:
            print(f"Error converting SVG to PDF: {e}")
            return False
    
    def svg_to_png(self, svg_path: str, png_path: str) -> bool:
        """将SVG转换为PNG"""
        try:
            # 尝试使用cairosvg
            try:
                import cairosvg
                cairosvg.svg2png(url=svg_path, write_to=png_path, dpi=self.quality)
                return True
            except ImportError:
                pass
            
            # 尝试使用svglib + reportlab
            try:
                from svglib.svglib import renderSVG
                from reportlab.graphics import renderPDF, renderPM
                
                drawing = renderSVG.renderSVG(svg_path)
                renderPM.drawToFile(drawing, png_path, fmt='PNG', dpi=self.quality)
                return True
            except ImportError:
                pass
            
            # 尝试使用wand (ImageMagick)
            try:
                from wand.image import Image as WandImage
                with WandImage(filename=svg_path, resolution=self.quality) as img:
                    img.format = 'png'
                    img.save(filename=png_path)
                return True
            except ImportError:
                pass
            
            # 最后尝试使用PIL + svglib
            try:
                from PIL import Image
                import xml.etree.ElementTree as ET
                
                # 简单的SVG转PNG（可能质量有限）
                print("Using basic SVG to PNG conversion...")
                # 这里可以实现基础的SVG解析和转换
                # 由于实现复杂，暂时返回False，建议安装专业库
                return False
                
            except Exception as e:
                print(f"All SVG conversion methods failed: {e}")
                return False
            
        except Exception as e:
            print(f"Error in SVG to PNG conversion: {e}")
            return False
    
    def create_multi_page_pdf(self, image_paths: list, output_path: str, 
                             title: str = "", descriptions: list = None) -> bool:
        """创建多页PDF文档"""
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.units import mm
            from PIL import Image
            
            # 获取页面尺寸
            page_width, page_height = self.get_page_dimensions()
            page_width_pt = page_width * mm
            page_height_pt = page_height * mm
            
            # 创建PDF
            c = canvas.Canvas(output_path, pagesize=(page_width_pt, page_height_pt))
            
            for i, img_path in enumerate(image_paths):
                if i > 0:
                    c.showPage()  # 新页面
                
                # 页面标题
                page_title = title
                if descriptions and i < len(descriptions):
                    page_title += f" - {descriptions[i]}"
                
                if page_title:
                    c.setFont("Helvetica-Bold", 16)
                    c.drawString(self.margin * mm, (page_height - self.margin - 10) * mm, page_title)
                
                # 打开图像
                img = Image.open(img_path)
                img_width, img_height = img.size
                
                # 计算可用空间
                available_width = (page_width - 2 * self.margin) * mm
                available_height = (page_height - 2 * self.margin - 20) * mm
                
                # 计算缩放比例
                scale_width = available_width / img_width
                scale_height = available_height / img_height
                scale = min(scale_width, scale_height)
                
                # 计算实际显示尺寸
                display_width = img_width * scale
                display_height = img_height * scale
                
                # 计算居中位置
                x = (page_width_pt - display_width) / 2
                y = (page_height_pt - display_height) / 2 - 10 * mm
                
                # 将图像绘制到PDF
                c.drawImage(img_path, x, y, width=display_width, height=display_height)
                
                # 页码
                c.setFont("Helvetica", 10)
                c.drawString((page_width - self.margin - 20) * mm, self.margin * mm, 
                           f"Page {i + 1}/{len(image_paths)}")
            
            # 保存PDF
            c.save()
            
            print(f"Multi-page PDF saved successfully: {output_path}")
            return True
            
        except Exception as e:
            print(f"Error creating multi-page PDF: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def add_metadata(self, pdf_path: str, metadata: dict) -> bool:
        """添加PDF元数据"""
        try:
            from reportlab.pdfgen import canvas
            
            # 这里可以使用PyPDF2或其他库来添加元数据
            # 简化实现，返回True
            print(f"Metadata would be added: {metadata}")
            return True
            
        except Exception as e:
            print(f"Error adding metadata: {e}")
            return False


def create_pdf_from_png(png_path: str, output_path: str, title: str = "", 
                       page_size: str = 'A4', orientation: str = 'landscape') -> bool:
    """便捷函数：从PNG创建PDF"""
    renderer = PDFRenderer(page_size=page_size, orientation=orientation)
    return renderer.png_to_pdf(png_path, output_path, title)


def create_pdf_from_svg(svg_path: str, output_path: str, title: str = "", 
                       page_size: str = 'A4', orientation: str = 'landscape') -> bool:
    """便捷函数：从SVG创建PDF"""
    renderer = PDFRenderer(page_size=page_size, orientation=orientation)
    return renderer.svg_to_pdf(svg_path, output_path, title)


def batch_create_pdf(image_paths: list, output_path: str, title: str = "",
                     descriptions: list = None, page_size: str = 'A4', 
                     orientation: str = 'landscape') -> bool:
    """便捷函数：批量创建多页PDF"""
    renderer = PDFRenderer(page_size=page_size, orientation=orientation)
    return renderer.create_multi_page_pdf(image_paths, output_path, title, descriptions)


# 支持的页面配置
PAGE_CONFIGS = {
    'A4_portrait': {'page_size': 'A4', 'orientation': 'portrait'},
    'A4_landscape': {'page_size': 'A4', 'orientation': 'landscape'},
    'A3_portrait': {'page_size': 'A3', 'orientation': 'portrait'},
    'A3_landscape': {'page_size': 'A3', 'orientation': 'landscape'},
    'Letter_portrait': {'page_size': 'Letter', 'orientation': 'portrait'},
    'Letter_landscape': {'page_size': 'Letter', 'orientation': 'landscape'},
}


def get_recommended_page_config(layout_type: str) -> dict:
    """根据布局类型获取推荐的页面配置"""
    recommendations = {
        'center': PAGE_CONFIGS['A4_portrait'],
        'horizontal': PAGE_CONFIGS['A4_landscape'],
        'vertical': PAGE_CONFIGS['A4_portrait'],
        'fishbone': PAGE_CONFIGS['A3_landscape'],
        'orgchart': PAGE_CONFIGS['A3_portrait'],
        'timeline': PAGE_CONFIGS['A3_landscape'],
        'circular': PAGE_CONFIGS['A4_portrait'],
    }
    
    return recommendations.get(layout_type, PAGE_CONFIGS['A4_landscape'])