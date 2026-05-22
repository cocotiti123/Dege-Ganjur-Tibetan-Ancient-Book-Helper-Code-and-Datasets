
class Config:
    FONT_PATH = "Qomolangma-UchenSutung.ttf"
    FONT_SIZE = 80
    IMAGE_SIZE = (12000, 10000)  # 增大画布尺寸
    
    # 手动指定随机坐标范围 [x_min, x_max, y_min, y_max]
    RANDOM_RANGE = [100, 11000, 100, 9000]  # 可以修改这四个值
    
    # 空格标记设置
    SPACE_COLOR = "#FF0000"
    SPACE_WIDTH_RATIO = 0.5
    SPACE_MARKER_HEIGHT = 8

    # 藏文字符偏移量配置（保持不变）
    OFFSETS = {
        "base": {"x": 0.0, "y": 0.0},
        "top": {"x": 0.0, "y": -0.1},
        "sub": {"x": 0.4, "y": 0.4},
        "vowel": {"x": 0.7, "y": -0.5},
        "tsek": {"x": 0.15, "y": 0.0},
        "shad": {"x": 0.25, "y": 0.0},
        "other": {"x": 0.0, "y": 0.0}
    }

def extract_tibetan_blocks(content):
    """改进的藏文字符提取，确保组合字符保持完整"""
    blocks = []
    i = 0
    content = content.replace(",", "")  # 移除逗号
    
    while i < len(content):
        char = content[i]
        
        # 处理空格
        if char == " ":
            blocks.append(char)
            i += 1
            continue
            
        # 处理藏文字符
        if 0x0F00 <= ord(char) <= 0x0FFF:
            block = char
            # 检查后续字符是否属于组合字符
            while i+1 < len(content):
                next_char = content[i+1]
                # 检查是否构成组合字符（下加字、元音符号等）
                if (ord(next_char) in range(0x0F71, 0x0F7D+1) or
                    ord(next_char) in range(0x0F90, 0x0FBC+1) or
                    next_char in ["ྷ", "ྲ", "ླ", "ྭ", "ྶ", "ྦ", "ྜ", "ྙ"]):

                    block += next_char
                    i += 1
                else:
                    break
            blocks.append(block)
            i += 1
        else:
            blocks.append(char)
            i += 1
    
    return blocks

