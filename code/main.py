
import os
import json
from PIL import Image, ImageDraw, ImageFont
from boundary_grid import find_inner_boundary
from tibetan_character import extract_tibetan_blocks, Config

class AdvancedTextLayout:
    def __init__(self, font_path, base_size=15, text_color="#4a1818"):
        self.font_path = font_path
        self.base_size = base_size
        self.text_color = text_color
        self.characters = []
        self.original_positions = []
        self.debug_info = []
        
    def calculate_layout(self, text_blocks, grid_cells):
        """三阶段布局计算"""
        self._initial_positioning(text_blocks, grid_cells)
        self._adjust_tsheg_spacing()
        self._fine_tune_positions_based_on_pixels()
        self._adjust_margins()
        
    def _adjust_margins(self):
        """微调边距，每个字符都稍微缩小一点，整体向中间靠拢"""
        # 按行分组
        rows = {}
        for char in self.characters:
            if char['row'] not in rows:
                rows[char['row']] = []
            rows[char['row']].append(char)

        for row, chars in rows.items():
            if not chars:
                continue

            # 按列排序
            chars.sort(key=lambda c: c['col'])

            # 计算行的左右边界
            line_start = chars[0]['cell']['top_left'][0]
            line_end = chars[-1]['cell']['bottom_right'][0]
            line_width = line_end - line_start

            # 计算当前行总宽度
            current_width = sum(c['char_width'] for c in chars)

            # 如果当前行宽度已经等于或小于行宽，不需要调整
            if current_width <= line_width:
                continue

            # 计算需要减少的总宽度（一个字符宽度）
            avg_char_width = line_width / len(chars)
            total_reduce = avg_char_width  # 总共减少一个字符宽度

            # 计算每个字符需要减少的宽度（保持原有比例）
            reduce_ratio = (current_width - total_reduce) / current_width

            # 调整每个字符的宽度（按比例缩小）
            for char in chars:
                char['char_width'] = max(1, int(char['char_width'] * reduce_ratio))

            # 重新定位字符（保持原有相对位置）
            x_pos = line_start + (line_width - sum(c['char_width'] for c in chars)) / 2  # 居中但不改变间距
            for char in chars:
                char['x'] = x_pos
                x_pos += char['char_width']

                # 确保不超出单元格边界
                max_right = char['cell']['bottom_right'][0]
                if char['x'] + char['char_width'] > max_right:
                    char['char_width'] = max_right - char['x']
    
    def _initial_positioning(self, text_blocks, grid_cells):
        """初始定位，考虑音节点特殊处理"""
        font = ImageFont.truetype(self.font_path, self.base_size)

        # 第一次遍历：定位所有字符并记录第一行第二列的y值
        first_row_second_char_y = None
        for (row, col), block in zip(grid_cells.keys(), text_blocks):
            cell = grid_cells[(row, col)]
            text = block["text"]
            is_tsheg = text == "་"

            # 计算初始宽度 (音节点只占50%，实际只占0.25
            original_width = int(font.getlength(text))
            if is_tsheg:
                char_width = int(original_width * 0.25)
            else:
                char_width = original_width

            # 初始位置 (保持原始单元格内的相对比例)
            cell_width = cell['bottom_right'][0] - cell['top_left'][0]
            x = cell['top_left'][0] + (cell_width - char_width) * col / len(text_blocks)
            y = cell['top_left'][1] + (cell['bottom_right'][1] - cell['top_left'][1] - font.size) * 0.3

            # 记录第一行第二列的y值
            if row == 0 and col == 1:
                first_row_second_char_y = y

            # 存储原始信息
            self.original_positions.append({
                'text': text,
                'row': row,
                'col': col,
                'original_x': x,
                'original_y': y,
                'original_width': original_width,
                'original_size': self.base_size
            })

            # 存储字符信息（暂时不处理第一行第一列）
            self.characters.append({
                'text': text,
                'row': row,
                'col': col,
                'cell': cell,
                'font': font,
                'size': self.base_size,
                'x': x,
                'y': y,
                'char_width': char_width,
                'original_x': x,
                'original_width': original_width,
                'is_tsheg': is_tsheg,
                'is_composite': len(text) > 1 and not is_tsheg and text not in ["།", "༎"],
                'is_left_boundary': col == 0,
                'is_right_boundary': col == len(text_blocks) - 1
            })

        # 第二次遍历：调整第一行第一列的y值
        for char in self.characters:
            if char['row'] == 0 and char['col'] == 0 and first_row_second_char_y is not None:
                char['y'] = first_row_second_char_y
                char['original_y'] = first_row_second_char_y
    
    def _adjust_tsheg_spacing(self):
        """精确调整音节点间距，重新分配节省的空间"""
        # 按行处理
        rows = {}
        for char in self.characters:
            if char['row'] not in rows:
                rows[char['row']] = []
            rows[char['row']].append(char)

        for row, chars in rows.items():
            # 按列排序
            chars.sort(key=lambda c: c['col'])

            # 计算行的原始总宽度和单元格宽度
            line_start = chars[0]['cell']['top_left'][0]
            line_end = chars[-1]['cell']['bottom_right'][0]
            line_width = line_end - line_start
            original_total = sum(c['original_width'] for c in chars)

            # 计算音节点节省的总空间
            tsheg_chars = [c for c in chars if c['is_tsheg']]
            if not tsheg_chars:
                continue

            # 计算节省的总空间 (每个音节点节省50%宽度，实际0.25)
            total_saved = sum(c['original_width'] * 0.25 for c in tsheg_chars)

            # 将节省的空间按比例分配给非音节点字符
            non_tsheg_chars = [c for c in chars if not c['is_tsheg']]
            if not non_tsheg_chars:
                continue

            # 计算每个非音节点字符应得的额外空间
            total_non_tsheg_width = sum(c['original_width'] for c in non_tsheg_chars)
            extra_space_per_char = {}

            # 先计算理论分配值
            for char in non_tsheg_chars:
                if total_non_tsheg_width > 0:
                    extra_space = total_saved * (char['original_width'] / total_non_tsheg_width)
                    extra_space_per_char[id(char)] = extra_space

            # 确保分配后的总宽度不超过原始总宽度
            total_allocated = sum(int(v) for v in extra_space_per_char.values())
            if total_allocated > total_saved:
                # 按比例缩减分配值
                scale = total_saved / total_allocated
                for char_id in extra_space_per_char:
                    extra_space_per_char[char_id] *= scale

            # 应用分配值
            for char in non_tsheg_chars:
                char['char_width'] = char['original_width'] + int(extra_space_per_char.get(id(char), 0))

            # 重新定位整行字符
            self._reposition_row_with_ratio(chars)
    
    def _reposition_row_with_ratio(self, chars):
        """基于原始位置比例重新定位字符"""
        if not chars:
            return

        # 计算行的左右边界
        line_start = chars[0]['cell']['top_left'][0]
        line_end = chars[-1]['cell']['bottom_right'][0]
        line_width = line_end - line_start

        # 计算当前总宽度
        current_total = sum(c['char_width'] for c in chars)

        # 确保总宽度不超过行宽
        if current_total > line_width:
            # 按比例缩小所有非边界字符
            scale = line_width / current_total
            for char in chars:
                if not char['is_left_boundary'] and not char['is_right_boundary']:
                    char['char_width'] = int(char['char_width'] * scale)
            current_total = sum(c['char_width'] for c in chars)

        # 重新定位字符，固定边界字符的位置
        x_pos = line_start
        for i, char in enumerate(chars):
            # 如果是边界字符，保持原始位置不变
            if char['is_left_boundary'] or char['is_right_boundary']:
                char['x'] = char['original_x']
                x_pos = char['x'] + char['char_width']
                continue

            # 保持原始相对位置比例
            original_offset = char['original_x'] - line_start
            char['x'] = line_start + int(original_offset * (line_width / current_total))

            # 确保不超出单元格边界
            char['x'] = max(char['cell']['top_left'][0], 
                          min(char['x'], char['cell']['bottom_right'][0] - char['char_width']))

            # 确保字符间不重叠
            if x_pos > char['x']:
                char['x'] = x_pos

            x_pos = char['x'] + char['char_width']

        # 最终验证
        last_char = chars[-1]
        if last_char['x'] + last_char['char_width'] > line_end:
            # 如果仍有越界，强制调整最后一个字符
            overflow = (last_char['x'] + last_char['char_width']) - line_end
            last_char['char_width'] -= overflow
            last_char['x'] = line_end - last_char['char_width']
    
    def _fine_tune_positions_based_on_pixels(self):
        """
        基于像素微调字符位置，解决字符重叠问题
        
        该方法通过在虚拟画布上渲染字符并分析实际像素边界，
        来微调字符的水平位置，确保字符之间不会重叠。
        """
        # 计算虚拟画布的尺寸，确保能容纳所有字符
        img_width = int(max(c['cell']['bottom_right'][0] for c in self.characters) + 100)
        img_height = int(max(c['cell']['bottom_right'][1] for c in self.characters) + 100)
        
        # 创建白色虚拟画布和绘图对象
        dummy_img = Image.new('RGB', (img_width, img_height), (255, 255, 255))
        dummy_draw = ImageDraw.Draw(dummy_img)

        # 第一遍：计算每个字符的实际像素边界
        for i, char in enumerate(self.characters):
            # 在虚拟画布上绘制字符
            dummy_draw.text((char['x'], char['y']), char['text'], font=char['font'], fill=self.text_color)
            
            # 获取字符的实际像素边界框
            bbox = self._get_real_pixel_bbox(dummy_img, char['x'], char['y'], char['text'], char['font'])
            
            # 存储实际的左右边界位置
            char['real_left'] = bbox['left']
            char['real_right'] = bbox['right']
            
            # 清除该字符区域，为下一个字符做准备
            dummy_draw.rectangle([bbox['left'], bbox['top'], bbox['right'], bbox['bottom']], fill="white")

        # 第二遍：检查并调整字符间的重叠
        for i in range(1, len(self.characters)):
            prev_char = self.characters[i-1]  # 前一个字符
            curr_char = self.characters[i]    # 当前字符

            # 如果不在同一行，跳过
            if prev_char['row'] != curr_char['row']:
                continue

            # 如果前一个字符是右边界或当前字符是左边界，跳过
            if prev_char['is_right_boundary'] or curr_char['is_left_boundary']:
                continue

            # 计算字符间的重叠量
            overlap = max(0, prev_char['real_right'] - curr_char['real_left'])
            
            # 如果有重叠，需要调整位置
            if overlap > 0:
                # 计算需要移动的距离（重叠量+1像素缓冲）
                move_distance = int(overlap + 1)
                
                # 计算移动后的右边界位置
                new_right = curr_char['x'] + move_distance + curr_char['char_width']
                # 获取当前字符所在单元格的最大右边界
                max_right = curr_char['cell']['bottom_right'][0]

                # 检查移动后是否超出单元格边界
                if new_right > max_right:
                    # 调整移动距离，确保不超出边界
                    move_distance = max(0, max_right - (curr_char['x'] + curr_char['char_width']))
                    # 如果无法移动（移动距离为0），则跳过
                    if move_distance == 0:
                        continue

                # 执行移动
                curr_char['x'] += move_distance
                
                # 重新绘制字符并更新实际边界
                dummy_draw.text((curr_char['x'], curr_char['y']), curr_char['text'], font=curr_char['font'], fill=self.text_color)
                bbox = self._get_real_pixel_bbox(dummy_img, curr_char['x'], curr_char['y'], curr_char['text'], curr_char['font'])
                curr_char['real_left'] = bbox['left']
                curr_char['real_right'] = bbox['right']
                
                # 清除该字符区域
                dummy_draw.rectangle([bbox['left'], bbox['top'], bbox['right'], bbox['bottom']], fill="white")

                # 添加调试信息
                self.debug_info.append({
                    'prev_char': prev_char['text'],      # 前一个字符
                    'curr_char': curr_char['text'],      # 当前字符
                    'overlap': overlap,                  # 重叠量
                    'move_distance': move_distance,      # 移动距离
                    'new_x': curr_char['x']              # 新位置
                })
    
    def _get_real_pixel_bbox(self, image, x, y, text, font):
        """获取字符的实际像素边界"""
        # 获取图像数据
        pixels = image.load()
        width, height = image.size
        
        # 初始边界
        left = width
        right = 0
        top = height
        bottom = 0
        
        # 获取字体的大致边界
        approx_bbox = font.getbbox(text)
        approx_width = approx_bbox[2] - approx_bbox[0]
        approx_height = approx_bbox[3] - approx_bbox[1]
        
        # 搜索范围 (扩大20%以防万一)
        search_left = max(0, int(x) - 5)
        search_right = min(width, int(x + approx_width * 1.2) + 5)
        search_top = max(0, int(y) - 5)
        search_bottom = min(height, int(y + approx_height * 1.2) + 5)
        
        # 扫描像素寻找实际边界
        for i in range(search_left, search_right):
            for j in range(search_top, search_bottom):
                if pixels[i, j] != (255, 255, 255):  # 非白色像素
                    if i < left:
                        left = i
                    if i > right:
                        right = i
                    if j < top:
                        top = j
                    if j > bottom:
                        bottom = j
        
        # 如果没有找到任何像素，返回近似边界
        if left == width:
            return {
                'left': int(x),
                'right': int(x + approx_width),
                'top': int(y),
                'bottom': int(y + approx_height)
            }
        
        return {
            'left': left,
            'right': right,
            'top': top,
            'bottom': bottom
        }
    
    def save_position_data(self, output_path):
        """保存调整数据"""
        data = []
        for orig, final in zip(self.original_positions, self.characters):
            data.append({
                'text': orig['text'],
                'row': orig['row'],
                'col': orig['col'],
                'original_x': orig['original_x'],
                'original_y': orig['original_y'],
                'original_width': orig['original_width'],
                'original_size': orig['original_size'],
                'final_x': final['x'],
                'final_y': final['y'],
                'final_width': final['char_width'],
                'final_size': final['size'],
                'is_tsheg': final['is_tsheg'],
                'is_composite': final.get('is_composite', False)
            })
        
        # 保存JSON
        json_path = os.path.splitext(output_path)[0] + '_positions.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 保存调试信息
        debug_path = os.path.splitext(output_path)[0] + '_debug.txt'
        with open(debug_path, 'w', encoding='utf-8') as f:
            f.write("字符间距调整调试信息\n")
            f.write("="*50 + "\n")
            for info in self.debug_info:
                f.write(f"前字符: {info['prev_char']} | 当前字符: {info['curr_char']}\n")
                f.write(f"重叠像素: {info['overlap']} | 移动距离: {info['move_distance']} | 新X坐标: {info['new_x']}\n")
                f.write("-"*50 + "\n")

def process_image_with_text(image_path, text_path, output_path, font_size=15, debug=False, text_color="#4a1818"):
    with open(text_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    
    if not lines:
        raise ValueError("文本文件为空")
    
    cols_list = [len(extract_tibetan_blocks(line)) for line in lines]
    _, img, grid_cells = find_inner_boundary(
        image_path,
        rows=len(lines),
        cols_list=cols_list,
        show_boundary=False,
        transparent_bg=True,
        draw_grid_lines=False
    )
    
    text_blocks = []
    for row in range(len(lines)):
        blocks = extract_tibetan_blocks(lines[row])
        for col in range(len(blocks)):
            if (row, col) in grid_cells:
                text_blocks.append({
                    "text": blocks[col],
                    "cell": grid_cells[(row, col)]
                })
    
    layout_engine = AdvancedTextLayout(Config.FONT_PATH, font_size, text_color)
    layout_engine.calculate_layout(text_blocks, grid_cells)
    
    draw = ImageDraw.Draw(img)
    for char in layout_engine.characters:
        draw.text((char['x'], char['y']), char['text'], font=char['font'], fill=text_color)
        
        if debug:
            bbox = layout_engine._get_real_pixel_bbox(img, char['x'], char['y'], char['text'], char['font'])
            draw.rectangle([bbox['left'], bbox['top'], bbox['right'], bbox['bottom']], outline="red", width=1)
            info = f"{char['size']}px@{char['x']:.0f},{char['y']:.0f}"
            draw.text((char['x']-10, char['y']-10), info, fill="blue")
    
    img.save(output_path)
    layout_engine.save_position_data(output_path)
    
    tsheg_chars = sum(1 for c in layout_engine.characters if c['is_tsheg'])
    composite_chars = sum(1 for c in layout_engine.characters if c.get('is_composite', False))
    print(f"处理完成: {output_path}")
    print(f"字符总数: {len(layout_engine.characters)} | 音节点: {tsheg_chars} | 复合字符: {composite_chars}")
    print(f"调试信息已保存到: {os.path.splitext(output_path)[0]}_debug.txt")

def batch_process_images(txt_folder, img_folder, output_folder, font_size=14, debug=False, text_color="#4a1818"):
    os.makedirs(output_folder, exist_ok=True)
    
    txt_files = sorted([f for f in os.listdir(txt_folder) if f.endswith('.txt')])
    img_files = sorted([f for f in os.listdir(img_folder) if f.endswith('.png')])
    
    if not txt_files:
        raise ValueError("没有找到任何文本文件")
    if not img_files:
        raise ValueError("没有找到任何图片文件")
    
    for i, txt_file in enumerate(txt_files):
        img_file = img_files[i % len(img_files)]
        txt_path = os.path.join(txt_folder, txt_file)
        img_path = os.path.join(img_folder, img_file)
        output_filename = f"output_{os.path.splitext(txt_file)[0]}.png"
        output_path = os.path.join(output_folder, output_filename)
        
        try:
            print(f"正在处理: {txt_file} (使用图片: {img_file})")
            process_image_with_text(
                image_path=img_path,
                text_path=txt_path,
                output_path=output_path,
                font_size=font_size,
                debug=debug,
                text_color=text_color
            )
        except Exception as e:
            print(f"处理 {txt_file} 时出错: {str(e)}")
            continue

if __name__ == "__main__":
    try:
        batch_process_images(
            txt_folder="dege-k-51_txt祥云",
            img_folder="png",
            output_folder="results",
            font_size=14,
            debug=False,
            text_color="#671219"  # 深黑红色，可根据需要调整
        )
    except Exception as e:
        print(f"批量处理失败: {str(e)}")