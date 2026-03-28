#!/usr/bin/env python3
"""
从 Chrome DevTools MCP take_snapshot 保存的文件中提取酒店数据
用法: python3 parse_a11y_tree.py <snapshot_file_path>
"""
import re
import json
import sys
from pathlib import Path
from typing import Optional


def load_a11y_snapshot(filepath: str) -> str:
    """加载 A11Y Tree 文本内容"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 解析外层 JSON 包装 (MCP 返回格式)
    wrapper = json.loads(content)

    # 提取 text 字段（包含实际的 A11Y Tree 文本）
    return wrapper[0]['text']


def extract_hotels(text: str) -> list[dict]:
    """
    从 A11Y Tree 文本中提取酒店数据
    返回: [{name, price, score, location}, ...]
    """
    lines = text.split('\n')
    hotels = []
    current_hotel = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Hotel name link (contains 'Opens in new window' AND hotel URL)
        if ' Opens in new window' in stripped and re.search(r'hotel/jp/', stripped):
            # Save previous hotel if exists and has data
            if current_hotel and (current_hotel.get('price') or current_hotel.get('score')):
                hotels.append(current_hotel)

            # Parse new hotel
            match = re.search(r'link "([^"]+)"', stripped)
            if match:
                name = match.group(1).replace(' Opens in new window', '')
                current_hotel = {
                    'name': name,
                    'price': None,
                    'score': None,
                    'location': None,
                    'url': None
                }

                # Extract URL
                url_match = re.search(r'url="([^"]+)"', stripped)
                if url_match:
                    current_hotel['url'] = url_match.group(1)

        # Location link
        elif current_hotel and 'Show on map' in stripped:
            match = re.search(r'link "([^"]+)"', stripped)
            if match:
                current_hotel['location'] = match.group(1).replace('· Show on map', '').strip()

        # Score link (e.g., "Scored 8.8 Excellent 2,230 reviews")
        elif current_hotel and 'Scored' in stripped:
            match = re.search(r'Scored (\d+\.?\d*)', stripped)
            if match:
                current_hotel['score'] = match.group(1)

        # Price StaticText (e.g., "Original price CNY 17,090. Current price CNY 12,123.")
        elif current_hotel and 'Current price' in stripped:
            match = re.search(r'Current price (CNY|USD|¥)\s*([\d,]+)', stripped)
            if match:
                current_hotel['price'] = f'{match.group(1)} {match.group(2)}'

    # Don't forget last hotel
    if current_hotel and (current_hotel.get('price') or current_hotel.get('score')):
        hotels.append(current_hotel)

    return hotels


def format_hotel_list(hotels: list[dict], limit: int = 10) -> str:
    """格式化酒店列表为可读字符串"""
    lines = [f'共找到 {len(hotels)} 个酒店:\n']

    for i, h in enumerate(hotels[:limit], 1):
        lines.append(f'{i}. {h["name"][:50]}...')
        lines.append(f'   价格: {h["price"] or "N/A"} | 评分: {h["score"] or "N/A"}')
        if h.get('location'):
            lines.append(f'   位置: {h["location"]}')
        lines.append('')

    if len(hotels) > limit:
        lines.append(f'... 还有 {len(hotels) - limit} 个酒店')

    return '\n'.join(lines)


def main():
    # 默认文件路径
    default_file = Path(__file__).parent / "snapshot.txt"

    # 从命令行参数或默认获取文件路径
    if len(sys.argv) > 1:
        filepath = Path(sys.argv[1])
    else:
        # 尝试找最新的 snapshot 文件
        snapshot_dir = Path.home() / ".claude" / "projects" / "-Users-stofancy-workspaces-voice-agent" / "554dfe0e-5193-4e20-b57b-459619f29158" / "tool-results"
        if snapshot_dir.exists():
            snapshots = list(snapshot_dir.glob("mcp-chrome-devtools-take_snapshot-*.txt"))
            if snapshots:
                # 按修改时间排序，取最新的
                filepath = max(snapshots, key=lambda p: p.stat().st_mtime)
            else:
                print(f"错误: 未找到 snapshot 文件在 {snapshot_dir}")
                sys.exit(1)
        else:
            print(f"错误: 请提供 snapshot 文件路径")
            print(f"用法: python3 {sys.argv[0]} <snapshot_file_path>")
            sys.exit(1)

    print(f"读取文件: {filepath}")
    print("-" * 60)

    try:
        text = load_a11y_snapshot(str(filepath))
        print(f"文本长度: {len(text):,} 字符")

        hotels = extract_hotels(text)
        print(format_hotel_list(hotels))

        # 如果指定了输出文件，也保存为 JSON
        if len(sys.argv) > 2:
            output_file = sys.argv[2]
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(hotels, f, ensure_ascii=False, indent=2)
            print(f"\n数据已保存到: {output_file}")

    except FileNotFoundError:
        print(f"错误: 文件不存在 - {filepath}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"错误: JSON 解析失败 - {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
