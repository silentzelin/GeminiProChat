"""Utility for analyzing v8 style number sequences.

This script classifies input values into terrain-like segments, produces
size/odd-even/012-route statistics over rolling windows, and infers the
behavior label of the latest entry.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

SEGMENT_RULES = {
    (1, 2): "谷底",
    (3, 4): "山腰",
    (5, 5): "小高台",
    (6, 7): "山脊",
    (8, 9): "山顶主体",
    (10, 10): "尖顶",
}


@dataclass
class WindowStats:
    window: int
    size_ratio: Dict[str, float]
    odd_even: Dict[str, float]
    route_012: Dict[str, float]
    alternation_rate: float

    def to_dict(self) -> Dict[str, object]:
        return {
            "window": self.window,
            "size_ratio": self.size_ratio,
            "odd_even": self.odd_even,
            "route_012": self.route_012,
            "alternation_rate": round(self.alternation_rate, 3),
        }


def parse_sequence(seq: str) -> List[int]:
    if not seq:
        raise ValueError("Sequence string is empty")
    numbers = []
    for part in seq.replace(";", ",").split(","):
        if not part.strip():
            continue
        try:
            value = int(part.strip())
        except ValueError as exc:  # pragma: no cover - defensive
            raise ValueError(f"Invalid number: {part}") from exc
        if value < 1 or value > 10:
            raise ValueError("Values must be between 1 and 10 inclusive")
        numbers.append(value)
    if not numbers:
        raise ValueError("No valid numbers parsed")
    return numbers


def classify_segment(value: int) -> str:
    for (start, end), name in SEGMENT_RULES.items():
        if start <= value <= end:
            return name
    return "未知"


def compute_window_stats(sequence: Sequence[int], window: int) -> WindowStats:
    window_values = list(sequence[-window:])
    total = len(window_values)
    small_count = sum(1 for v in window_values if v <= 5)
    large_count = total - small_count
    odd_count = sum(1 for v in window_values if v % 2 == 1)
    even_count = total - odd_count
    route_counts = {str(r): 0 for r in range(3)}
    for v in window_values:
        route_counts[str(v % 3)] += 1
    alternations = 0
    for left, right in zip(window_values, window_values[1:]):
        if (left <= 5) != (right <= 5):
            alternations += 1
    alternation_rate = alternations / max(total - 1, 1)
    return WindowStats(
        window=window,
        size_ratio={
            "small": round(small_count / total, 3),
            "large": round(large_count / total, 3),
        },
        odd_even={"odd": round(odd_count / total, 3), "even": round(even_count / total, 3)},
        route_012={k: round(v / total, 3) for k, v in route_counts.items()},
        alternation_rate=alternation_rate,
    )


def determine_world(stats_10: WindowStats) -> str:
    small_ratio = stats_10.size_ratio["small"]
    if small_ratio >= 0.7:
        return "小号世界"
    if small_ratio <= 0.3:
        return "大号世界"
    return "均衡过渡"


def determine_oscillation(window_stats: WindowStats) -> str:
    if window_stats.alternation_rate >= 0.6:
        return "震荡明显"
    if window_stats.alternation_rate >= 0.4:
        return "轻微震荡"
    return "相对平稳"


def detect_behavior(sequence: Sequence[int]) -> Tuple[str, str]:
    if len(sequence) == 1:
        return "延续", "仅有一期记录，视为延续"

    curr = sequence[-1]
    prev = sequence[-2]
    pre_prev = sequence[-3] if len(sequence) >= 3 else None
    delta_curr = curr - prev
    delta_prev = prev - pre_prev if pre_prev is not None else None

    isolated_prev = False
    if pre_prev is not None:
        isolated_prev = abs(prev - pre_prev) >= 3 and abs(prev - curr) >= 3

    if isolated_prev and abs(curr - pre_prev) <= 1:
        return "假段", "上一期明显偏离，两侧回到同一层级"

    if delta_prev is not None and delta_prev != 0 and (delta_prev > 0 > delta_curr or delta_prev < 0 < delta_curr) and abs(delta_curr) >= 2:
        return "断点", "原有走势被反向的大跳变打断"

    if (prev <= 2 or prev >= 9) and abs(curr - prev) >= 2 and 3 <= curr <= 8:
        return "补缺", "极端值后回落或回升至主体区间"

    if delta_prev is not None and ((delta_prev > 0 and delta_curr > 0) or (delta_prev < 0 and delta_curr < 0) or delta_curr == 0):
        return "延续", "走势保持原有方向或持平"

    if abs(curr - 5) <= 1 and abs(prev - 5) > 1:
        return "补缺", "回到中枢做平衡"

    return "断点", "变化方向混乱，视为趋势断裂"


def analyze(sequence: Sequence[int]) -> Dict[str, object]:
    segments = [classify_segment(v) for v in sequence]
    windows: List[int] = []
    for w in (3, 5, 10):
        effective = min(w, len(sequence))
        if effective not in windows:
            windows.append(effective)
    window_stats = [compute_window_stats(sequence, w) for w in windows]
    stats_map = {str(ws.window): ws.to_dict() for ws in window_stats}
    stats_10 = next((ws for ws in window_stats if ws.window == 10), window_stats[-1])
    world = determine_world(stats_10)
    oscillation = determine_oscillation(window_stats[0])
    behavior, reason = detect_behavior(sequence)
    return {
        "inputs": sequence,
        "segments": segments,
        "window_stats": stats_map,
        "world": world,
        "oscillation": oscillation,
        "behavior": {"label": behavior, "reason": reason},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="v8 number analyzer")
    parser.add_argument("sequence", help='Number list, e.g. "3,4,2,5,9,9,10,9,3,2"')
    parser.add_argument("--format", choices=["json", "table"], default="json", help="Output format")
    args = parser.parse_args()

    sequence = parse_sequence(args.sequence)
    result = analyze(sequence)

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print("输入序列:", ",".join(map(str, result["inputs"])))
    print("分段分类:", " | ".join(result["segments"]))
    print(f"世界判断: {result['world']}，震荡: {result['oscillation']}")
    for ws in result["window_stats"].values():
        print(
            f"近{ws['window']}期-大小 {ws['size_ratio']} | 奇偶 {ws['odd_even']} | 012路 {ws['route_012']} | 震荡率 {ws['alternation_rate']}"
        )
    print(f"行为标签: {result['behavior']['label']} ({result['behavior']['reason']})")


if __name__ == "__main__":
    main()
