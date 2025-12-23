#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF转Markdown工具 - 简化可靠版
直接提取文本，保留所有内容，手动优化格式
"""

import pdfplumber
import sys
import re

def clean_text(text):
    """清理文本，保留结构"""
    if not text:
        return ""
    # 移除多余的空白字符，但保留换行
    text = re.sub(r'[ \t]+', ' ', text)
    # 保留段落分隔（多个连续换行）
    text = re.sub(r'\n{4,}', '\n\n\n', text)
    return text.strip()

def format_code_in_text(text):
    """在文本中识别并格式化代码块"""
    lines = text.split('\n')
    result = []
    i = 0
    
    while i < len(lines):
        line = lines[i]
        line_stripped = line.strip()
        
        # 检测"Code block"标记（可能包含特殊字符）
        if re.search(r'Code[\s\x01]*block', line_stripped, re.IGNORECASE):
            # 跳过"Code block"标记行，开始代码块
            result.append("```")
            i += 1
            # 收集后续的代码行
            code_lines = []
            consecutive_code_lines = 0
            
            while i < len(lines):
                next_line = lines[i]
                next_stripped = next_line.strip()
                
                # 如果是以数字开头的行，认为是代码
                if re.match(r'^\d+\s+', next_stripped):
                    # 移除行号
                    code_line = re.sub(r'^\d+\s+', '', next_line)
                    code_lines.append(code_line)
                    consecutive_code_lines += 1
                    i += 1
                # 如果包含代码特征，也认为是代码
                elif (next_stripped.startswith('//') or 
                      next_stripped.startswith('func') or
                      next_stripped.startswith('type') or
                      '{' in next_line or '}' in next_line or
                      re.match(r'^\s*[A-Z]\w+:', next_stripped) or
                      re.match(r'^\s*[A-Z]\w+\s*\{', next_stripped) or
                      re.match(r'^\s*[A-Z]\w+\s+[A-Z]', next_stripped)):
                    code_lines.append(next_line)
                    consecutive_code_lines += 1
                    i += 1
                # 空行：如果在代码块中，保留；否则结束代码块
                elif next_stripped == '':
                    if code_lines:  # 如果已有代码行，保留空行
                        code_lines.append("")
                        consecutive_code_lines = 0  # 重置连续计数
                        i += 1
                    else:  # 如果还没有代码行，跳过
                        i += 1
                        break
                else:
                    # 如果已经有代码行，且遇到非代码行，检查是否是代码块的结束
                    if code_lines and consecutive_code_lines == 0:
                        # 连续空行后遇到非代码，结束代码块
                        break
                    elif code_lines:
                        # 有代码行但遇到非代码，可能是代码块结束
                        # 检查下一行是否还是代码
                        if i + 1 < len(lines):
                            next_next = lines[i + 1].strip()
                            if (re.match(r'^\d+\s+', next_next) or
                                next_next.startswith('//') or
                                next_next.startswith('func') or
                                next_next.startswith('type')):
                                # 下一行还是代码，继续
                                code_lines.append(next_line)
                                i += 1
                                continue
                        # 否则结束代码块
                        break
                    else:
                        # 没有代码行，直接结束
                        break
            
            # 添加收集的代码行
            if code_lines:
                # 移除末尾的空行
                while code_lines and code_lines[-1].strip() == '':
                    code_lines.pop()
                result.extend(code_lines)
            result.append("```")
            result.append("")
            continue
        
        result.append(line)
        i += 1
    
    return '\n'.join(result)

def extract_tables_basic(pdf_page):
    """基本表格提取"""
    tables = pdf_page.extract_tables()
    markdown_tables = []
    
    for table in tables:
        if not table or len(table) == 0:
            continue
        
        markdown_table = []
        header_processed = False
        
        for row in table:
            if not row:
                continue
            
            row_data = [str(cell or "").strip() for cell in row]
            
            # 跳过完全空的行
            if not any(row_data):
                continue
            
            if not header_processed:
                if any(row_data):
                    markdown_table.append("| " + " | ".join(row_data) + " |")
                    markdown_table.append("| " + " | ".join(["---"] * len(row_data)) + " |")
                    header_processed = True
            else:
                # 确保列数一致
                if len(row_data) != len(markdown_table[0].split('|')) - 2:
                    # 调整列数
                    expected_cols = len(markdown_table[0].split('|')) - 2
                    while len(row_data) < expected_cols:
                        row_data.append("")
                    row_data = row_data[:expected_cols]
                markdown_table.append("| " + " | ".join(row_data) + " |")
        
        if len(markdown_table) > 2:
            markdown_tables.append("\n".join(markdown_table))
    
    return markdown_tables

def pdf_to_markdown_simple(pdf_path, output_path):
    """将PDF转换为Markdown - 简化版"""
    markdown_content = []
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)
            print(f"正在处理PDF文件，共 {total_pages} 页...")
            
            for page_num, page in enumerate(pdf.pages, 1):
                print(f"处理第 {page_num}/{total_pages} 页...")
                
                # 添加页面分隔符
                if page_num > 1:
                    markdown_content.append("\n---\n")
                
                markdown_content.append(f"## 第 {page_num} 页\n")
                
                # 直接提取文本（使用默认方法，保持原始顺序）
                text = page.extract_text()
                if text:
                    # 格式化代码块
                    formatted_text = format_code_in_text(text)
                    cleaned_text = clean_text(formatted_text)
                    if cleaned_text:
                        markdown_content.append(cleaned_text)
                        markdown_content.append("\n")
                
                # 提取表格
                tables = extract_tables_basic(page)
                if tables:
                    markdown_content.append("\n### 表格内容\n")
                    for table in tables:
                        markdown_content.append(table)
                        markdown_content.append("\n")
                
                # 提取图片信息
                images = page.images
                if images:
                    markdown_content.append("\n### 图片\n")
                    for img_num, img in enumerate(images, 1):
                        markdown_content.append(f"![图片 {img_num}](位置: x0={img.get('x0', 'N/A')}, y0={img.get('y0', 'N/A')}, x1={img.get('x1', 'N/A')}, y1={img.get('y1', 'N/A')})\n")
                
                # 提取绘图对象信息
                if hasattr(page, 'curves') and page.curves:
                    markdown_content.append(f"\n<!-- 页面包含 {len(page.curves)} 个绘图对象 -->\n")
            
            # 写入Markdown文件
            final_content = "\n".join(markdown_content)
            
            # 后处理：统一处理代码块
            # 处理所有"Code block"标记后的代码
            lines = final_content.split('\n')
            processed_lines = []
            i = 0
            
            while i < len(lines):
                line = lines[i]
                
                # 检测"Code block"标记（可能包含特殊字符）
                if re.search(r'Code[\s\x01]*block', line, re.IGNORECASE):
                    # 跳过"Code block"行，添加代码块开始标记
                    processed_lines.append("```")
                    i += 1
                    
                    # 收集后续的代码行（以数字开头的行）
                    code_lines = []
                    while i < len(lines):
                        next_line = lines[i]
                        next_stripped = next_line.strip()
                        
                        # 如果是以数字开头的行，移除行号
                        if re.match(r'^\d+\s+', next_stripped):
                            code_line = re.sub(r'^\d+\s+', '', next_line)
                            code_lines.append(code_line)
                            i += 1
                        # 空行：如果在代码块中，保留
                        elif next_stripped == '':
                            if code_lines:  # 已有代码行，保留空行
                                code_lines.append("")
                            i += 1
                        # 遇到下一个"Code block"或明显的非代码内容，结束
                        elif re.search(r'Code[\s\x01]*block', next_stripped, re.IGNORECASE):
                            break
                        elif (next_stripped and 
                              not next_stripped.startswith('//') and
                              not next_stripped.startswith('func') and
                              not next_stripped.startswith('type') and
                              '{' not in next_line and '}' not in next_line and
                              not re.match(r'^\s*[A-Z]\w+:', next_stripped) and
                              not re.match(r'^\s*[A-Z]\w+\s*\{', next_stripped)):
                            # 检查是否是标题或段落开始
                            if (len(next_stripped) < 100 and 
                                (next_stripped.isupper() or 
                                 next_stripped.endswith(':') or
                                 re.match(r'^(Op_\d+|Phase\s+\d+):', next_stripped))):
                                break
                            # 如果下一行还是代码，继续
                            if i + 1 < len(lines):
                                next_next = lines[i + 1].strip()
                                if re.match(r'^\d+\s+', next_next):
                                    code_lines.append(next_line)
                                    i += 1
                                    continue
                            break
                        else:
                            # 其他情况，可能是代码的延续
                            code_lines.append(next_line)
                            i += 1
                    
                    # 添加收集的代码行
                    if code_lines:
                        # 移除末尾的空行
                        while code_lines and code_lines[-1].strip() == '':
                            code_lines.pop()
                        processed_lines.extend(code_lines)
                    processed_lines.append("```")
                    processed_lines.append("")
                    continue
                
                processed_lines.append(line)
                i += 1
            
            final_content = '\n'.join(processed_lines)
            
            # 后处理：清理格式
            # 移除重复的代码块标记
            final_content = re.sub(r'```\s*\n\s*```', '```', final_content)
            # 清理多余的空行
            final_content = re.sub(r'\n{4,}', '\n\n\n', final_content)
            # 确保代码块前后有空行
            final_content = re.sub(r'([^\n])\n```', r'\1\n\n```', final_content)
            final_content = re.sub(r'```\n([^\n])', r'```\n\n\1', final_content)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(final_content)
            
            print(f"\n转换完成！Markdown文件已保存到: {output_path}")
            print(f"总页数: {total_pages}")
            print(f"文件大小: {len(final_content)} 字符")
            
    except Exception as e:
        print(f"错误: {str(e)}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    pdf_path = "交易路径优化和执行编排的设计方案 .pdf"
    output_path = "交易路径优化和执行编排的设计方案.md"
    
    pdf_to_markdown_simple(pdf_path, output_path)

