import os
import random
from PIL import Image
import numpy as np
from collections import deque


def create_collage_optimized(input_folder, output_path, target_width, target_height, blend_width=5):
    """
    创建优化后的图片拼贴，带有边缘混合功能
    
    参数:
        input_folder: 输入图片文件夹路径
        output_path: 输出图片路径
        target_width: 目标宽度
        target_height: 目标高度
        blend_width: 边缘混合宽度(像素)
    """
    # 加载所有小图片
    small_images = []
    for filename in os.listdir(input_folder):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp', '.gif')):
            try:
                img = Image.open(os.path.join(input_folder, filename))
                small_images.append(img)
            except:
                print(f"无法加载图片: {filename}")

    if not small_images:
        print("没有找到可用的图片")
        return

    # 创建目标画布和覆盖检查数组
    collage = Image.new('RGB', (target_width, target_height))
    coverage = np.zeros((target_height, target_width), dtype=bool)
    
    # 维护一个空白区域队列（优先处理大区域）
    empty_areas = deque()
    empty_areas.append((0, 0, target_width, target_height))  # (x, y, w, h)

    # 计算需要覆盖的总面积
    total_area = target_width * target_height
    covered_area = 0

    while empty_areas and covered_area < total_area:
        # 获取当前最大的空白区域
        x, y, w, h = empty_areas.popleft()
        
        # 跳过已经完全覆盖的区域
        if is_area_covered(coverage, x, y, w, h):
            continue

        # 选择能覆盖此区域的最佳图片（按面积从大到小排序）
        best_img = None
        best_cover = 0
        best_orientation = None
        
        # 先尝试大图片
        for img in sorted(small_images, key=lambda i: i.width * i.height, reverse=True):
            img_w, img_h = img.size
            
            # 尝试两种方向（原始和旋转90度）
            for orientation in ['original', 'rotated']:
                if orientation == 'rotated':
                    img_w, img_h = img_h, img_w
                
                # 计算能覆盖的区域
                cover_w = min(img_w, w)
                cover_h = min(img_h, h)
                cover_area = cover_w * cover_h
                
                if cover_area > best_cover:
                    best_cover = cover_area
                    best_img = img
                    best_orientation = orientation
                    
                    # 如果已经能完全覆盖，就停止搜索
                    if cover_area == w * h:
                        break
            if best_cover == w * h:
                break

        if best_img is None:
            # 如果没有合适的图片，随机选择一个
            best_img = random.choice(small_images)
            best_orientation = 'original'

        # 应用旋转
        img_w, img_h = best_img.size
        if best_orientation == 'rotated':
            best_img = best_img.rotate(90, expand=True)
            img_w, img_h = img_h, img_w

        # 计算粘贴位置（尽量覆盖最大空白）
        paste_x = x + random.randint(0, max(0, w - img_w))
        paste_y = y + random.randint(0, max(0, h - img_h))
        
        # 确保在画布范围内
        paste_x = max(0, min(paste_x, target_width - img_w))
        paste_y = max(0, min(paste_y, target_height - img_h))

        # 粘贴图片（带边缘混合）
        blend_edges(collage, best_img, paste_x, paste_y, coverage, blend_width)

        # 更新覆盖状态并分割剩余空白区域
        new_empty_areas = update_coverage_and_split(
            coverage, paste_x, paste_y, img_w, img_h, x, y, w, h
        )
        
        # 计算新增的覆盖面积
        new_covered = img_w * img_h
        # 减去可能与其他区域重叠的部分
        for area in new_empty_areas:
            new_covered -= area[2] * area[3]
        covered_area += new_covered

        # 将新的空白区域加入队列（按面积从大到小排序）
        empty_areas.extend(new_empty_areas)
        empty_areas = deque(sorted(empty_areas, key=lambda a: a[2]*a[3], reverse=True))

    # 最终检查并填补小空白
    fill_small_gaps_optimized(collage, coverage, small_images, blend_width)

    # 保存结果
    collage.save(output_path)
    print(f"拼接完成，保存到: {output_path}")
    print(f"覆盖比例: {covered_area / total_area * 100:.2f}%")


def blend_edges(collage, new_img, paste_x, paste_y, coverage, blend_width):
    """
    将新图片粘贴到拼贴上，并混合边缘
    
    参数:
        collage: 目标拼贴图像
        new_img: 要粘贴的新图片
        paste_x: 粘贴位置x坐标
        paste_y: 粘贴位置y坐标
        coverage: 覆盖状态数组
        blend_width: 混合宽度(像素)
    """
    # 将图片转换为数组以便处理
    collage_arr = np.array(collage)
    new_img_arr = np.array(new_img)
    
    img_h, img_w = new_img_arr.shape[:2]
    
    # 获取粘贴区域的边界
    x_start = paste_x
    x_end = paste_x + img_w
    y_start = paste_y
    y_end = paste_y + img_h
    
    # 检查四个方向的边缘是否需要混合
    # 左边缘
    if x_start > 0:
        left_edge = max(0, x_start - blend_width)
        for x in range(left_edge, x_start):
            # 只混合未被覆盖的区域
            if not np.all(coverage[y_start:y_end, x]):
                # 计算混合权重 (从0到1线性变化)
                weight = (x - left_edge) / (x_start - left_edge)
                for y in range(y_start, y_end):
                    if not coverage[y, x]:
                        # 混合像素
                        collage_arr[y, x] = (collage_arr[y, x] * (1 - weight) + 
                                             new_img_arr[y - y_start, x - x_start] * weight).astype(np.uint8)
    
    # 右边缘
    if x_end < collage_arr.shape[1]:
        right_edge = min(collage_arr.shape[1], x_end + blend_width)
        for x in range(x_end, right_edge):
            # 只混合未被覆盖的区域
            if not np.all(coverage[y_start:y_end, x]):
                # 计算混合权重 (从1到0线性变化)
                weight = 1 - (x - x_end) / (right_edge - x_end)
                for y in range(y_start, y_end):
                    if not coverage[y, x]:
                        # 混合像素
                        collage_arr[y, x] = (collage_arr[y, x] * (1 - weight) + 
                                           new_img_arr[y - y_start, x_end - x_start - (right_edge - x)] * weight).astype(np.uint8)
    
    # 上边缘
    if y_start > 0:
        top_edge = max(0, y_start - blend_width)
        for y in range(top_edge, y_start):
            # 只混合未被覆盖的区域
            if not np.all(coverage[y, x_start:x_end]):
                # 计算混合权重 (从0到1线性变化)
                weight = (y - top_edge) / (y_start - top_edge)
                for x in range(x_start, x_end):
                    if not coverage[y, x]:
                        # 混合像素
                        collage_arr[y, x] = (collage_arr[y, x] * (1 - weight) + 
                                         new_img_arr[y - y_start, x - x_start] * weight).astype(np.uint8)
    
    # 下边缘
    if y_end < collage_arr.shape[0]:
        bottom_edge = min(collage_arr.shape[0], y_end + blend_width)
        for y in range(y_end, bottom_edge):
            # 只混合未被覆盖的区域
            if not np.all(coverage[y, x_start:x_end]):
                # 计算混合权重 (从1到0线性变化)
                weight = 1 - (y - y_end) / (bottom_edge - y_end)
                for x in range(x_start, x_end):
                    if not coverage[y, x]:
                        # 混合像素
                        collage_arr[y, x] = (collage_arr[y, x] * (1 - weight) + 
                                           new_img_arr[y_end - y_start - (bottom_edge - y), x - x_start] * weight).astype(np.uint8)
    
    # 直接粘贴中心区域（不混合）
    center_x_start = paste_x + blend_width
    center_x_end = paste_x + img_w - blend_width
    center_y_start = paste_y + blend_width
    center_y_end = paste_y + img_h - blend_width
    
    # 确保中心区域有效
    if center_x_start < center_x_end and center_y_start < center_y_end:
        collage_arr[center_y_start:center_y_end, center_x_start:center_x_end] = \
            new_img_arr[blend_width:img_h-blend_width, blend_width:img_w-blend_width]
    else:
        # 如果图片太小，没有中心区域，则直接粘贴
        collage_arr[y_start:y_end, x_start:x_end] = new_img_arr
    
    # 更新拼贴图像
    collage.paste(Image.fromarray(collage_arr), (0, 0))
    
    # 更新覆盖状态（不包括混合区域）
    coverage[y_start:y_end, x_start:x_end] = True


def is_area_covered(coverage, x, y, w, h):
    """检查区域是否已被完全覆盖"""
    return np.all(coverage[y:y+h, x:x+w])


def update_coverage_and_split(coverage, paste_x, paste_y, img_w, img_h, area_x, area_y, area_w, area_h):
    """更新覆盖状态并返回分割后的空白区域"""
    # 更新覆盖状态
    coverage[paste_y:paste_y+img_h, paste_x:paste_x+img_w] = True
    
    # 计算剩余空白区域
    empty_areas = []
    
    # 1. 左侧空白区域
    left_width = paste_x - area_x
    if left_width > 0:
        empty_areas.append((area_x, area_y, left_width, area_h))
    
    # 2. 右侧空白区域
    right_x = paste_x + img_w
    right_width = (area_x + area_w) - right_x
    if right_width > 0:
        empty_areas.append((right_x, area_y, right_width, area_h))
    
    # 3. 上方空白区域
    top_height = paste_y - area_y
    if top_height > 0:
        empty_areas.append((area_x, area_y, area_w, top_height))
    
    # 4. 下方空白区域
    bottom_y = paste_y + img_h
    bottom_height = (area_y + area_h) - bottom_y
    if bottom_height > 0:
        empty_areas.append((area_x, bottom_y, area_w, bottom_height))
    
    # 过滤掉完全被覆盖的区域
    return [area for area in empty_areas if not is_area_covered(coverage, *area)]


def fill_small_gaps_optimized(collage, coverage, small_images, blend_width=5, max_gap_size=50):
    """填补小的空白区域（优化版）"""
    height, width = coverage.shape
    collage_arr = np.array(collage)
    
    # 只检查可能的小空白
    for y in range(0, height, max_gap_size//2):
        for x in range(0, width, max_gap_size//2):
            if not coverage[y, x]:
                # 检查周围小区域
                for img in sorted(small_images, key=lambda i: i.width * i.height):
                    img_w, img_h = img.size
                    
                    # 尝试以(x,y)为中心的4个可能位置
                    for offset_x, offset_y in [(-img_w//2, -img_h//2),
                                               (0, -img_h//2),
                                               (-img_w//2, 0),
                                               (0, 0)]:
                        paste_x = x + offset_x
                        paste_y = y + offset_y
                        
                        if (paste_x >= 0 and paste_y >= 0 and
                            paste_x + img_w <= width and
                            paste_y + img_h <= height):
                            
                            # 检查这个粘贴是否能覆盖当前空白点
                            if (not coverage[y, x] and 
                                paste_x <= x < paste_x + img_w and
                                paste_y <= y < paste_y + img_h):
                                
                                # 使用带混合的粘贴
                                blend_edges(collage, img, paste_x, paste_y, coverage, blend_width)
                                break
                    else:
                        continue
                    break


# 使用示例
if __name__ == "__main__":
    input_folder = "za"  # 小图片所在的文件夹
    output_path = r"../../../desktop/dege原始文件/background/背景碎片/背景碎片/背景制作以此为准/background/za1.jpg"  # 输出文件路径
    target_width = 2000  # 目标宽度
    target_height = 800  # 目标高度
    blend_width = 10  # 边缘混合宽度(像素)

    create_collage_optimized(input_folder, output_path, target_width, target_height, blend_width)