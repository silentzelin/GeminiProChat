import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from PySide6 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg


CONFIG_PATH = Path(__file__).with_name("config.json")


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with CONFIG_PATH.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except json.JSONDecodeError:
            return {}
    return {}


def save_config(config: dict) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as fh:
        json.dump(config, fh, ensure_ascii=False, indent=2)


@dataclass
class Draw:
    issue: str
    numbers: List[int]


class DataManager:
    def __init__(self) -> None:
        self.draws: List[Draw] = []
        self.error_lines = 0
        self.file_path: Optional[Path] = None
        self._file_position = 0
        self._buffer = ""

    def reset(self) -> None:
        self.draws = []
        self.error_lines = 0
        self._file_position = 0
        self._buffer = ""

    def load_file(self, file_path: Path, incremental: bool = False) -> None:
        if not incremental or self.file_path != file_path or not file_path.exists():
            self.reset()
        self.file_path = file_path
        if not file_path.exists():
            return

        mode = "r"
        with file_path.open(mode, encoding="utf-8", errors="ignore") as fh:
            if incremental and self._file_position:
                fh.seek(self._file_position)
            content = fh.read()
            self._file_position = fh.tell()

        if not content:
            return

        if self._buffer:
            content = self._buffer + content
            self._buffer = ""

        if not content.endswith("\n"):
            parts = content.splitlines()
            if parts:
                self._buffer = parts[-1]
                content = "\n".join(parts[:-1])

        lines = content.splitlines()
        new_draws, errors = self._parse_lines(lines)
        self.draws.extend(new_draws)
        self.error_lines += errors

    def _parse_lines(self, lines: List[str]) -> Tuple[List[Draw], int]:
        draws: List[Draw] = []
        errors = 0
        for line in lines:
            line = line.strip()
            if not line:
                continue
            draw = self._parse_line(line)
            if draw is None:
                errors += 1
                continue
            draws.append(draw)
        return draws, errors

    def _parse_line(self, line: str) -> Optional[Draw]:
        tokens = [token for token in line.replace(",", " ").split() if token]
        issue = ""
        numbers: List[int] = []

        if len(tokens) == 1 and tokens[0].isdigit() and len(tokens[0]) == 10:
            numbers = self._parse_digit_string(tokens[0])
        elif len(tokens) == 2 and tokens[1].isdigit() and len(tokens[1]) == 10:
            issue = tokens[0]
            numbers = self._parse_digit_string(tokens[1])
        elif len(tokens) >= 11:
            issue = tokens[0]
            numbers = self._parse_number_tokens(tokens[1:11])
        elif len(tokens) == 10:
            numbers = self._parse_number_tokens(tokens)

        if not numbers or len(numbers) != 10:
            return None
        if any(num < 1 or num > 10 for num in numbers):
            return None
        return Draw(issue=issue, numbers=numbers)

    @staticmethod
    def _parse_digit_string(value: str) -> List[int]:
        numbers: List[int] = []
        for ch in value:
            if not ch.isdigit():
                return []
            digit = int(ch)
            if digit == 0:
                numbers.append(10)
            else:
                numbers.append(digit)
        return numbers

    @staticmethod
    def _parse_number_tokens(tokens: List[str]) -> List[int]:
        numbers: List[int] = []
        for token in tokens:
            if not token.isdigit():
                return []
            numbers.append(int(token))
        return numbers


class Lucky10Window(QtWidgets.QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("澳洲幸运10 可视化")
        self.resize(1200, 760)

        self.data_manager = DataManager()
        self.config = load_config()

        self._setup_ui()
        self._setup_watcher()
        self._load_initial_data()

    def _setup_ui(self) -> None:
        self.toolbar = QtWidgets.QToolBar("工具栏")
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        self.file_button = QtWidgets.QToolButton()
        self.file_button.setText("选择文件")
        self.file_button.clicked.connect(self._select_file)
        self.toolbar.addWidget(self.file_button)

        self.monitor_checkbox = QtWidgets.QCheckBox("监控")
        self.monitor_checkbox.setChecked(self.config.get("monitor", True))
        self.monitor_checkbox.toggled.connect(self._toggle_monitor)
        self.toolbar.addWidget(self.monitor_checkbox)

        self.toolbar.addSeparator()
        self.toolbar.addWidget(QtWidgets.QLabel("最近N期"))
        self.recent_spin = QtWidgets.QSpinBox()
        self.recent_spin.setRange(100, 5000)
        self.recent_spin.setSingleStep(100)
        self.recent_spin.setValue(self.config.get("recent_n", 2000))
        self.recent_spin.valueChanged.connect(self._refresh_views)
        self.toolbar.addWidget(self.recent_spin)

        self.toolbar.addSeparator()
        self.toolbar.addWidget(QtWidgets.QLabel("模式"))
        self.mode_combo = QtWidgets.QComboBox()
        self.mode_combo.addItems(["偏温", "偏热", "偏冷回补"])
        self.mode_combo.setCurrentText(self.config.get("mode", "偏温"))
        self.mode_combo.currentTextChanged.connect(self._update_recommendation)
        self.toolbar.addWidget(self.mode_combo)

        self.toolbar.addSeparator()
        self.toolbar.addWidget(QtWidgets.QLabel("图表"))
        self.chart_combo = QtWidgets.QComboBox()
        self.chart_combo.addItems(
            [
                "前五滚动频次(20)",
                "前五滚动频次(60)",
                "前五滚动频次(120)",
                "前五和值",
                "号码遗漏曲线",
            ]
        )
        self.chart_combo.setCurrentText(
            self.config.get("chart_type", "前五滚动频次(20)")
        )
        self.chart_combo.currentTextChanged.connect(self._refresh_chart)
        self.toolbar.addWidget(self.chart_combo)

        self.toolbar.addWidget(QtWidgets.QLabel("号码"))
        self.number_combo = QtWidgets.QComboBox()
        self.number_combo.addItems([str(i) for i in range(1, 11)])
        self.number_combo.setCurrentText(str(self.config.get("selected_number", 1)))
        self.number_combo.currentTextChanged.connect(self._refresh_chart)
        self.toolbar.addWidget(self.number_combo)

        self.table = QtWidgets.QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels(
            ["期号"] + [f"{i}名" for i in range(1, 11)]
        )
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.showGrid(x=True, y=True)

        self.reason_label = QtWidgets.QLabel()
        self.reason_label.setWordWrap(True)
        self.reason_label.setMinimumHeight(80)
        self.reason_label.setFrameShape(QtWidgets.QFrame.StyledPanel)

        right_panel = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.plot_widget, stretch=3)
        right_layout.addWidget(QtWidgets.QLabel("独胆建议"))
        right_layout.addWidget(self.reason_label, stretch=1)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.addWidget(self.table)
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)

        container = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(container)
        layout.addWidget(splitter)
        self.setCentralWidget(container)

        self.statusBar().showMessage("就绪")

    def _setup_watcher(self) -> None:
        self.watcher = QtCore.QFileSystemWatcher(self)
        self.watcher.fileChanged.connect(self._on_file_changed)
        self.debounce_timer = QtCore.QTimer(self)
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(self.config.get("debounce_ms", 300))
        self.debounce_timer.timeout.connect(self._reload_file)

    def _load_initial_data(self) -> None:
        file_path = self.config.get("file_path", "")
        if file_path:
            self._set_file(Path(file_path))
            self._reload_file(full=True)

    def _select_file(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "选择数据文件", str(Path.cwd()), "Data Files (*.txt *.csv);;All Files (*)"
        )
        if not path:
            return
        self._set_file(Path(path))
        self._reload_file(full=True)

    def _set_file(self, path: Path) -> None:
        self.config["file_path"] = str(path)
        save_config(self.config)
        self.watcher.removePaths(self.watcher.files())
        if path.exists():
            self.watcher.addPath(str(path))
        self.statusBar().showMessage(f"当前文件: {path}")

    def _toggle_monitor(self, checked: bool) -> None:
        self.config["monitor"] = checked
        save_config(self.config)
        if not checked:
            self.watcher.removePaths(self.watcher.files())
        else:
            if self.data_manager.file_path:
                self.watcher.addPath(str(self.data_manager.file_path))

    def _on_file_changed(self, _: str) -> None:
        if not self.monitor_checkbox.isChecked():
            return
        self.debounce_timer.start()

    def _reload_file(self, full: bool = False) -> None:
        file_path_str = self.config.get("file_path", "")
        if not file_path_str:
            return
        file_path = Path(file_path_str)
        if full:
            self.data_manager.reset()
            self.data_manager.file_path = file_path
            self.data_manager._file_position = 0

        before_count = len(self.data_manager.draws)
        self.data_manager.load_file(file_path, incremental=not full)
        if len(self.data_manager.draws) != before_count or full:
            self._refresh_views()

        self.statusBar().showMessage(
            f"有效期数: {len(self.data_manager.draws)} | 错误行: {self.data_manager.error_lines}"
        )
        if file_path.exists() and file_path not in map(Path, self.watcher.files()):
            self.watcher.addPath(str(file_path))

    def _refresh_views(self) -> None:
        self._refresh_table()
        self._refresh_chart()
        self._update_recommendation()

    def _refresh_table(self) -> None:
        draws = self.data_manager.draws
        if not draws:
            self.table.setRowCount(0)
            return
        recent = self.recent_spin.value()
        display = list(reversed(draws[-recent:]))
        self.table.setRowCount(len(display))
        for row, draw in enumerate(display):
            issue_item = QtWidgets.QTableWidgetItem(draw.issue or "-")
            self.table.setItem(row, 0, issue_item)
            for idx, num in enumerate(draw.numbers, start=1):
                item = QtWidgets.QTableWidgetItem(str(num))
                self.table.setItem(row, idx, item)
        self.table.resizeColumnsToContents()

    def _refresh_chart(self) -> None:
        draws = self.data_manager.draws
        self.plot_widget.clear()
        if not draws:
            return
        chart_type = self.chart_combo.currentText()
        recent = self.recent_spin.value()

        if chart_type.startswith("前五滚动频次"):
            window = 20 if "20" in chart_type else 60 if "60" in chart_type else 120
            self._plot_rolling_frequency(draws, window, recent)
        elif chart_type == "前五和值":
            self._plot_front_five_sum(draws, recent)
        else:
            number = int(self.number_combo.currentText())
            self._plot_omission(draws, number, recent)

    def _plot_rolling_frequency(self, draws: List[Draw], window: int, recent: int) -> None:
        presence = {num: [] for num in range(1, 11)}
        for draw in draws:
            front_five = set(draw.numbers[:5])
            for num in range(1, 11):
                presence[num].append(1 if num in front_five else 0)

        x_values = list(range(1, len(draws) + 1))
        for num in range(1, 11):
            counts = presence[num]
            cumsum = [0]
            for value in counts:
                cumsum.append(cumsum[-1] + value)
            rolling = []
            for idx in range(len(counts)):
                start = max(0, idx + 1 - window)
                rolling.append(cumsum[idx + 1] - cumsum[start])
            x_slice = x_values[-recent:]
            y_slice = rolling[-recent:]
            self.plot_widget.plot(
                x_slice,
                y_slice,
                pen=pg.mkPen(width=2),
                name=str(num),
            )
        self.plot_widget.setTitle(f"前五滚动频次 (窗口 {window})")
        self.plot_widget.setLabel("left", "次数")
        self.plot_widget.setLabel("bottom", "期数")

    def _plot_front_five_sum(self, draws: List[Draw], recent: int) -> None:
        values = [sum(draw.numbers[:5]) for draw in draws]
        x_values = list(range(1, len(draws) + 1))
        self.plot_widget.plot(x_values[-recent:], values[-recent:], pen=pg.mkPen(width=2))
        self.plot_widget.setTitle("前五和值")
        self.plot_widget.setLabel("left", "和值")
        self.plot_widget.setLabel("bottom", "期数")

    def _plot_omission(self, draws: List[Draw], number: int, recent: int) -> None:
        omissions = []
        current = 0
        for draw in draws:
            if number in draw.numbers[:5]:
                current = 0
            else:
                current += 1
            omissions.append(current)
        x_values = list(range(1, len(draws) + 1))
        self.plot_widget.plot(x_values[-recent:], omissions[-recent:], pen=pg.mkPen(width=2))
        self.plot_widget.setTitle(f"号码 {number} 遗漏曲线")
        self.plot_widget.setLabel("left", "遗漏")
        self.plot_widget.setLabel("bottom", "期数")

    def _update_recommendation(self) -> None:
        draws = self.data_manager.draws
        if not draws:
            self.reason_label.setText("暂无数据")
            return
        stats = self._compute_number_stats(draws)
        mode = self.mode_combo.currentText()
        best_numbers, reason = self._select_candidate(stats, mode)
        self.reason_label.setText(reason)

    def _compute_number_stats(self, draws: List[Draw]) -> dict:
        stats = {}
        total = len(draws)
        for num in range(1, 11):
            stats[num] = {
                "F20": self._count_front_five(draws, num, 20),
                "F60": self._count_front_five(draws, num, 60),
                "F120": self._count_front_five(draws, num, 120),
                "O": self._current_omission(draws, num),
                "total": total,
            }
        return stats

    @staticmethod
    def _count_front_five(draws: List[Draw], number: int, window: int) -> int:
        if not draws:
            return 0
        window_draws = draws[-window:] if len(draws) >= window else draws
        count = 0
        for draw in window_draws:
            if number in draw.numbers[:5]:
                count += 1
        return count

    @staticmethod
    def _current_omission(draws: List[Draw], number: int) -> int:
        omission = 0
        for draw in reversed(draws):
            if number in draw.numbers[:5]:
                break
            omission += 1
        return omission

    def _select_candidate(self, stats: dict, mode: str) -> Tuple[List[int], str]:
        scores = {}
        for num, data in stats.items():
            f20 = data["F20"]
            f60 = data["F60"]
            f120 = data["F120"]
            o = data["O"]
            p20 = f20 / min(20, data["total"]) if data["total"] else 0
            p60 = f60 / min(60, data["total"]) if data["total"] else 0
            p120 = f120 / min(120, data["total"]) if data["total"] else 0
            trend = p20 - p60
            stability = abs(p20 - p60) + abs(p60 - p120)

            if mode == "偏热":
                score = p20 * 0.6 + p60 * 0.4 - max(0, p20 - 0.8) * 0.5
            elif mode == "偏冷回补":
                score = -abs(o - 5) + trend * 0.5 + p60 * 0.2
            else:
                temperature = 1 - abs(p60 - 0.5)
                score = temperature - stability - abs(trend) * 0.2

            scores[num] = {
                "score": score,
                "trend": trend,
                "stability": stability,
                "p20": p20,
                "p60": p60,
                "p120": p120,
                "data": data,
            }

        best_score = max(values["score"] for values in scores.values())
        best_numbers = [num for num, values in scores.items() if values["score"] == best_score]
        best_numbers.sort()
        selected = best_numbers[0]
        info = scores[selected]
        data = info["data"]
        trend_desc = "短期略强" if info["trend"] > 0.05 else "短期略弱" if info["trend"] < -0.05 else "短期稳定"
        stability_desc = (
            "走势稳定" if info["stability"] < 0.15 else "波动明显" if info["stability"] > 0.35 else "中等波动"
        )
        reason = (
            f"推荐独胆：{selected}（模式：{mode}）\n"
            f"F20={data['F20']} / F60={data['F60']} / F120={data['F120']} / 当前遗漏={data['O']}\n"
            f"趋势：{trend_desc}；稳定性：{stability_desc}。"
        )
        if len(best_numbers) > 1:
            reason += f"\n并列候选：{', '.join(map(str, best_numbers))}"
        return best_numbers, reason

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.config["recent_n"] = self.recent_spin.value()
        self.config["mode"] = self.mode_combo.currentText()
        self.config["chart_type"] = self.chart_combo.currentText()
        self.config["selected_number"] = int(self.number_combo.currentText())
        save_config(self.config)
        super().closeEvent(event)


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    window = Lucky10Window()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
