
import cv2
import numpy as np
from PIL import Image, ImageDraw
from collections import namedtuple


Boundary = namedtuple('Boundary', ['top', 'bottom', 'left', 'right', 'corners'])


def refine_edge(edge, edge_points, width, height):
    """改进后的边界点精炼函数"""
    if len(edge_points) < 3:  # 点数太少不处理
        return edge_points, {}

    refined_points = []
    suspect_points = []  # 可疑的可能是其他边界的点

    # 确定当前边界的主要和次要坐标轴
    if edge in ['top', 'bottom']:
        primary_axis = 0  # x坐标是主要变化
        secondary_axis = 1  # y坐标应该变化不大
    else:  # 'left', 'right'
        primary_axis = 1  # y坐标是主要变化
        secondary_axis = 0  # x坐标应该变化不大

    # 计算主要坐标的变化率和次要坐标的变化率
    primary_changes = []
    secondary_changes = []
    for i in range(1, len(edge_points)):
        primary_diff = abs(edge_points[i][primary_axis] - edge_points[i - 1][primary_axis])
        secondary_diff = abs(edge_points[i][secondary_axis] - edge_points[i - 1][secondary_axis])
        primary_changes.append(primary_diff)
        secondary_changes.append(secondary_diff)

    # 计算平均变化率
    avg_primary_change = np.mean(primary_changes) if primary_changes else 0
    avg_secondary_change = np.mean(secondary_changes) if secondary_changes else 0

    # 确定更严格的变化率阈值
    primary_threshold = max(avg_primary_change * 0.3, 1)  # 降低阈值乘数
    secondary_threshold = max(avg_secondary_change * 3, 5)  # 提高阈值乘数

    # 检查每个点是否符合当前边界的特征
    for i in range(len(edge_points)):
        if i == 0 or i == len(edge_points) - 1:  # 保留第一个和最后一个点
            refined_points.append(edge_points[i])
            continue

        # 计算与前一个点的变化
        primary_diff = abs(edge_points[i][primary_axis] - edge_points[i - 1][primary_axis])
        secondary_diff = abs(edge_points[i][secondary_axis] - edge_points[i - 1][secondary_axis])

        # 更严格的判断条件
        if primary_diff > primary_threshold and secondary_diff < secondary_threshold:
            refined_points.append(edge_points[i])
        else:
            suspect_points.append(edge_points[i])

    # 对可疑点进行重新分类
    reclassified = {'top': [], 'bottom': [], 'left': [], 'right': []}
    for x, y in suspect_points:
        if edge in ['left', 'right']:
            # 更严格的重新分类条件
            if y < height / 3:  # 上1/3区域才归为上边界
                reclassified['top'].append((x, y))
            elif y > 2 * height / 3:  # 下1/3区域才归为下边界
                reclassified['bottom'].append((x, y))
        else:  # 'top', 'bottom'
            if x < width / 3:  # 左1/3区域才归为左边界
                reclassified['left'].append((x, y))
            elif x > 2 * width / 3:  # 右1/3区域才归为右边界
                reclassified['right'].append((x, y))

    # 确保精炼后的点至少包含首尾点
    if not refined_points and edge_points:
        refined_points = [edge_points[0], edge_points[-1]]

    # 对精炼后的点进行排序
    if edge in ['top', 'bottom']:
        refined_points.sort(key=lambda p: p[0])  # 按x排序
    else:
        refined_points.sort(key=lambda p: p[1])  # 按y排序

    return refined_points, reclassified


def find_contour_edges(binary, width, height):
    """使用轮廓检测获取更精确的边界"""
    # 查找轮廓
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    # 获取最大轮廓
    max_contour = max(contours, key=cv2.contourArea)
    epsilon = 0.002 * cv2.arcLength(max_contour, True)
    approx = cv2.approxPolyDP(max_contour, epsilon, True)

    # 将轮廓点转换为更密集的边界点
    dense_points = []
    for i in range(len(approx)):
        pt1 = approx[i][0]
        pt2 = approx[(i + 1) % len(approx)][0]
        num_points = max(10, int(np.linalg.norm(pt2 - pt1) / 2))  # 每2像素至少一个点
        dense_points.extend(
            [tuple(pt1 + (pt2 - pt1) * t / num_points) for t in range(num_points)]
        )

    # 初始分类边界点
    boundaries = {'top': [], 'bottom': [], 'left': [], 'right': []}

    # 初步分类（使用更宽松的区域划分）
    for x, y in dense_points:
        if y < height / 3:  # 上边区域
            boundaries['top'].append((x, y))
        elif y > 2 * height / 3:  # 下边区域
            boundaries['bottom'].append((x, y))
        elif x < width / 3:  # 左边区域
            boundaries['left'].append((x, y))
        elif x > 2 * width / 3:  # 右边区域
            boundaries['right'].append((x, y))
        else:
            # 中间区域点根据最近边缘分类
            dist_to_top = y
            dist_to_bottom = height - y
            dist_to_left = x
            dist_to_right = width - x
            min_dist = min(dist_to_top, dist_to_bottom, dist_to_left, dist_to_right)

            if min_dist == dist_to_top:
                boundaries['top'].append((x, y))
            elif min_dist == dist_to_bottom:
                boundaries['bottom'].append((x, y))
            elif min_dist == dist_to_left:
                boundaries['left'].append((x, y))
            else:
                boundaries['right'].append((x, y))

    # 两轮精炼处理
    for _ in range(2):  # 进行两轮精炼
        temp_boundaries = {'top': [], 'bottom': [], 'left': [], 'right': []}
        all_reclassified = {'top': [], 'bottom': [], 'left': [], 'right': []}

        for edge in ['top', 'bottom', 'left', 'right']:
            points = boundaries[edge]
            if points:
                # 对点进行排序
                if edge in ['top', 'bottom']:
                    points.sort(key=lambda p: p[0])
                else:
                    points.sort(key=lambda p: p[1])

                # 精炼边界点
                refined_points, reclassified = refine_edge(edge, points, width, height)
                temp_boundaries[edge] = refined_points
                for k, v in reclassified.items():
                    all_reclassified[k].extend(v)

        # 合并重新分类的点（这些点已从原边界中移除）
        for edge in ['top', 'bottom', 'left', 'right']:
            if all_reclassified[edge]:
                temp_boundaries[edge].extend(all_reclassified[edge])
                # 再次排序
                if edge in ['top', 'bottom']:
                    temp_boundaries[edge].sort(key=lambda p: p[0])
                else:
                    temp_boundaries[edge].sort(key=lambda p: p[1])

        boundaries = temp_boundaries

    # 计算角点 - 现在直接从边界点中获取最接近角落的点
    def get_corner_point(points, corner_type, width, height):
        if not points:
            if corner_type == 'top_left':
                return (0, 0)
            elif corner_type == 'top_right':
                return (width, 0)
            elif corner_type == 'bottom_left':
                return (0, height)
            else:  # 'bottom_right'
                return (width, height)

        if corner_type == 'top_left':
            return min(points, key=lambda p: p[0] + p[1])  # 最小x+y
        elif corner_type == 'top_right':
            return max(points, key=lambda p: p[0] - p[1])  # 最大x-y
        elif corner_type == 'bottom_left':
            return min(points, key=lambda p: p[0] - p[1])  # 最小x-y
        else:  # 'bottom_right'
            return max(points, key=lambda p: p[0] + p[1])  # 最大x+y

    corners = {
        'top_left': get_corner_point(boundaries['top'] + boundaries['left'], 'top_left', width, height),
        'top_right': get_corner_point(boundaries['top'] + boundaries['right'], 'top_right', width, height),
        'bottom_left': get_corner_point(boundaries['bottom'] + boundaries['left'], 'bottom_left', width, height),
        'bottom_right': get_corner_point(boundaries['bottom'] + boundaries['right'], 'bottom_right', width, height)
    }

    return Boundary(top=boundaries['top'],
                    bottom=boundaries['bottom'],
                    left=boundaries['left'],
                    right=boundaries['right'],
                    corners=corners)


def visualize_boundary(img, boundary):
    """改进的可视化函数：只绘制边界点，不绘制连接线"""
    draw = ImageDraw.Draw(img)

    # 定义边界颜色
    colors = {
        'top': 'red',  # 上边界-红色
        'bottom': 'blue',  # 下边界-蓝色
        'left': 'green',  # 左边界-绿色
        'right': 'yellow'  # 右边界-黄色
    }

    # 分别绘制四条边界的点（不连接）
    for edge in ['top', 'bottom', 'left', 'right']:
        points = getattr(boundary, edge)
        # 绘制边界点
        for x, y in points:
            draw.ellipse([x - 3, y - 3, x + 3, y + 3], fill=colors[edge], outline=colors[edge])

    # 绘制角点（用紫色标记）
    for corner_name, (x, y) in boundary.corners.items():
        draw.ellipse([x - 5, y - 5, x + 5, y + 5], fill='purple', outline='purple')
        draw.text((x + 7, y - 10), corner_name, fill='purple')

    return img


def is_point_on_boundary(point, boundary, tolerance=5):
    """检查点是否在边界上（包括角点）"""
    x, y = point
    # 检查是否在角点上
    for corner_name, (cx, cy) in boundary.corners.items():
        if abs(x - cx) <= tolerance and abs(y - cy) <= tolerance:
            return True, corner_name

    # 检查是否在边界上
    for edge in ['top', 'bottom', 'left', 'right']:
        edge_points = getattr(boundary, edge)
        for px, py in edge_points:
            if abs(x - px) <= tolerance and abs(y - py) <= tolerance:
                return True, edge

    return False, None


def draw_grid(img, boundary, rows, cols_list, draw_lines=True):
    """最终版网格绘制函数，确保100%封闭"""
    draw = ImageDraw.Draw(img)
    grid_cells = {}
    width, height = img.size

    # ===== 核心修复1：建立全局边界坐标系 =====
    # 将边界点转换为按坐标排序的字典
    edge_coords = {
        'top': sorted([(x, y) for x, y in boundary.top], key=lambda p: p[0]),
        'bottom': sorted([(x, y) for x, y in boundary.bottom], key=lambda p: p[0]),
        'left': sorted([(x, y) for x, y in boundary.left], key=lambda p: p[1]),
        'right': sorted([(x, y) for x, y in boundary.right], key=lambda p: p[1])
    }

    # ===== 核心修复2：边界点精确匹配函数 =====
    def get_closest_edge_point(x, y, edge_type):
        """找到距离指定点最近的边界点（精确匹配）"""
        if edge_type in ['top', 'bottom']:
            points = edge_coords[edge_type]
            # 找到最近的3个点取平均（平滑处理）
            distances = [abs(p[0] - x) for p in points]
            closest_indices = np.argsort(distances)[:3]
            closest_points = [points[i] for i in closest_indices]
            avg_x = sum(p[0] for p in closest_points) / len(closest_points)
            avg_y = sum(p[1] for p in closest_points) / len(closest_points)
            return (avg_x, avg_y)
        else:  # left/right
            points = edge_coords[edge_type]
            distances = [abs(p[1] - y) for p in points]
            closest_indices = np.argsort(distances)[:3]
            closest_points = [points[i] for i in closest_indices]
            avg_x = sum(p[0] for p in closest_points) / len(closest_points)
            avg_y = sum(p[1] for p in closest_points) / len(closest_points)
            return (avg_x, avg_y)

    # ===== 核心修复3：网格点生成新逻辑 =====
    # 生成行分割线（基于左右边界）
    row_lines = []
    for row in range(rows + 1):
        ratio = row / rows
        # 左边界点
        left_y = boundary.corners['top_left'][1] + ratio * (
                boundary.corners['bottom_left'][1] - boundary.corners['top_left'][1])
        # 右边界点
        right_y = boundary.corners['top_right'][1] + ratio * (
                boundary.corners['bottom_right'][1] - boundary.corners['top_right'][1])
        row_lines.append({
            'left': (boundary.corners['top_left'][0], left_y),
            'right': (boundary.corners['top_right'][0], right_y)
        })

    # 生成列分割线（基于行线的端点）
    for row in range(rows):
        current_cols = cols_list[row] if isinstance(cols_list, list) else cols_list
        y_start = row_lines[row]['left'][1]
        y_end = row_lines[row + 1]['left'][1]

        for col in range(current_cols + 1):
            col_ratio = col / current_cols
            # 上边界点
            top_x = row_lines[row]['left'][0] + col_ratio * (
                    row_lines[row]['right'][0] - row_lines[row]['left'][0])
            top_y = row_lines[row]['left'][1] + col_ratio * (
                    row_lines[row]['right'][1] - row_lines[row]['left'][1])
            # 下边界点
            bottom_x = row_lines[row + 1]['left'][0] + col_ratio * (
                    row_lines[row + 1]['right'][0] - row_lines[row + 1]['left'][0])
            bottom_y = row_lines[row + 1]['left'][1] + col_ratio * (
                    row_lines[row + 1]['right'][1] - row_lines[row + 1]['left'][1])

            # 强制对齐边界（关键修复！）
            if col == 0:  # 左边界
                top_x, top_y = get_closest_edge_point(top_x, top_y, 'left')
                bottom_x, bottom_y = get_closest_edge_point(bottom_x, bottom_y, 'left')
            elif col == current_cols:  # 右边界
                top_x, top_y = get_closest_edge_point(top_x, top_y, 'right')
                bottom_x, bottom_y = get_closest_edge_point(bottom_x, bottom_y, 'right')

            if row == 0:  # 上边界
                top_x, top_y = get_closest_edge_point(top_x, top_y, 'top')
            if row == rows - 1:  # 下边界
                bottom_x, bottom_y = get_closest_edge_point(bottom_x, bottom_y, 'bottom')

            # 存储网格点
            if col < current_cols:
                if (row, col) not in grid_cells:
                    grid_cells[(row, col)] = {}
                grid_cells[(row, col)].update({
                    'top_left': (top_x, top_y),
                    'top_right': (row_lines[row]['right'][0] if col == current_cols - 1 else None,
                                  row_lines[row]['right'][1] if col == current_cols - 1 else None),
                    'bottom_left': (bottom_x, bottom_y)
                })
            if col > 0:
                grid_cells[(row, col - 1)]['top_right'] = (top_x, top_y)
                grid_cells[(row, col - 1)]['bottom_right'] = (bottom_x, bottom_y)

    # ===== 最终闭合检查 =====
    for (row, col), cell in grid_cells.items():
        # 确保所有点都存在
        tl = cell['top_left']
        tr = cell['top_right']
        bl = cell['bottom_left']
        br = cell['bottom_right']

        # 绘制网格（使用抗锯齿）
        if draw_lines:
            draw.line([tl, tr], fill=(200, 200, 200, 128), width=1)
            draw.line([tl, bl], fill=(200, 200, 200, 128), width=1)
            if row == rows - 1:
                draw.line([bl, br], fill=(200, 200, 200, 128), width=1)
            if col == (cols_list[row] if isinstance(cols_list, list) else cols_list) - 1:
                draw.line([tr, br], fill=(200, 200, 200, 128), width=1)

        # 存储边界信息
        grid_cells[(row, col)]['on_boundary'] = {
            'top_left': is_point_on_boundary(tl, boundary),
            'top_right': is_point_on_boundary(tr, boundary),
            'bottom_left': is_point_on_boundary(bl, boundary),
            'bottom_right': is_point_on_boundary(br, boundary)
        }

    return img, grid_cells


def find_inner_boundary(image_path, rows=10, cols_list=None, show_boundary=True, transparent_bg=False,
                        draw_grid_lines=True):
    """主函数（单文件处理版）"""
    # 处理默认cols_list
    if cols_list is None:
        cols_list = [10] * rows
    elif isinstance(cols_list, int):
        cols_list = [cols_list] * rows

    try:
        # 打开图像并保留原始副本
        original_img = Image.open(image_path).convert("RGBA")
        width, height = original_img.size
        data = np.array(original_img)

        # 二值化处理
        alpha = data[:, :, 3]
        binary = cv2.adaptiveThreshold(alpha, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                       cv2.THRESH_BINARY, 11, 2)
        binary = np.where(binary > 50, 255, 0).astype(np.uint8)

        # 形态学处理
        kernel = np.ones((3, 3), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)

        # 获取边界
        boundary = find_contour_edges(binary, width, height)
        if not boundary:
            raise ValueError("无法检测到有效边界")

        # 创建结果图像
        if transparent_bg:
            result_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        else:
            result_img = Image.new("RGB", (width, height), "white")

        # 保留原始图像
        result_img.paste(original_img, (0, 0), original_img)

        # 可视化边界（根据开关决定）
        if show_boundary:
            result_img = visualize_boundary(result_img, boundary)

        # 计算网格（总是计算），根据开关决定是否绘制
        result_img, grid_cells = draw_grid(
            result_img,  # 使用结果图像而不是原始图像
            boundary,
            rows=rows,
            cols_list=cols_list,
            draw_lines=draw_grid_lines
        )

        return boundary, result_img, grid_cells
    except Exception as e:
        raise RuntimeError(f"图像处理失败: {str(e)}")


