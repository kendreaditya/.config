"""Shared infrastructure utilities for config scripts."""
import os
import re
import sys


def ensure_config_venv():
    """Re-exec under ~/.config/config-venv if not already."""
    VENV_DIR = os.path.expanduser("~/.config/config-venv")
    VENV_PYTHON = os.path.join(VENV_DIR, "bin", "python3")
    if os.path.exists(VENV_PYTHON) and not sys.prefix.startswith(VENV_DIR):
        os.execv(VENV_PYTHON, [VENV_PYTHON] + sys.argv)


def sanitize_filename(name: str) -> str:
    """Turn a string into a safe filename slug."""
    name = re.sub(r'[^\w\s-]', '', name)
    name = re.sub(r'\s+', '_', name.strip())
    return name or 'untitled'


class ProgressLogger:
    """Configurable Rich progress bar with named metrics.

    Args:
        verbose: If True, print text instead of progress bar.
        total: Initial total count.
        task_label: Label for the progress bar task.
        metrics: List of dicts with 'name' and 'color' keys, e.g.
                 [{"name": "processed", "color": "green"}].
        show_eta: Whether to show time elapsed/remaining columns.
    """

    def __init__(self, verbose=False, total=0, task_label="Processing",
                 metrics=None, show_eta=True):
        self.verbose = verbose
        self.total = total
        self.task_label = task_label
        self.show_eta = show_eta
        self.progress = None
        self.task_id = None

        # Initialize metric counters
        self._metrics = metrics or [{"name": "processed", "color": "green"}]
        self._counts = {m["name"]: 0 for m in self._metrics}
        self._color_map = {m["name"]: m["color"] for m in self._metrics}

    def __getattr__(self, name):
        # Allow direct access to metric counts like self.processed, self.skipped, etc.
        if name.startswith('_') or name in ('verbose', 'total', 'task_label', 'show_eta',
                                             'progress', 'task_id'):
            raise AttributeError(name)
        if '_counts' in self.__dict__ and name in self._counts:
            return self._counts[name]
        raise AttributeError(name)

    def __setattr__(self, name, value):
        if not name.startswith('_') and '_counts' in self.__dict__ and name in self._counts:
            self._counts[name] = value
        else:
            super().__setattr__(name, value)

    def start(self):
        if not self.verbose and self.total > 0:
            from rich.progress import (
                Progress, SpinnerColumn, TextColumn, BarColumn,
                TaskProgressColumn, TimeRemainingColumn, TimeElapsedColumn,
            )
            columns = [
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TextColumn("[cyan]{task.completed}/{task.total}"),
            ]
            if self.show_eta:
                columns.append(TimeElapsedColumn())
                columns.append(TimeRemainingColumn())

            self.progress = Progress(*columns)
            self.progress.start()
            self.task_id = self.progress.add_task(self.task_label, total=self.total)

    def stop(self):
        if self.progress:
            self.progress.stop()

    def update_total(self, total):
        self.total = total
        if self.progress and self.task_id is not None:
            self.progress.update(self.task_id, total=total)

    def _update_description(self, current_item=""):
        if self.progress and self.task_id is not None:
            stats = []
            for m in self._metrics:
                name = m["name"]
                count = self._counts[name]
                if count > 0:
                    color = m["color"]
                    label = name.replace('_', ' ')
                    stats.append(f"[{color}]{count} {label}[/{color}]")

            stats_str = ", ".join(stats) if stats else "Starting..."

            if current_item:
                desc = f"{stats_str} | [cyan]Current:[/cyan] {current_item[:50]}..."
            else:
                desc = stats_str

            self.progress.update(self.task_id, description=desc)

    def set_current(self, title):
        """Set the current item being processed (updates progress bar)."""
        if not self.verbose:
            self._update_description(title)
        else:
            print(f"  [PROCESSING] {title[:60]}...")

    def _advance(self):
        if self.progress and self.task_id is not None:
            self.progress.advance(self.task_id)

    def advance(self, metric_name, label=""):
        """Increment a metric counter and advance the progress bar."""
        self._counts[metric_name] = self._counts.get(metric_name, 0) + 1
        self._advance()
        if self.verbose and label:
            print(f"  [{metric_name.upper()}] {label[:60]}...")
        elif not self.verbose:
            self._update_description()

    def summary(self):
        self.stop()
        parts = []
        for m in self._metrics:
            name = m["name"]
            count = self._counts[name]
            if count > 0 or name == self._metrics[0]["name"]:
                label = name.replace('_', ' ')
                parts.append(f"{count} {label}")
        print(f"\nSummary: {', '.join(parts)}")


class MarkdownWriter:
    """Buffered markdown file writer with header and append/flush support.

    Args:
        path: Output file path.
        header: Markdown header to write at the top.
        resume: If True, skip writing header when file already exists.
    """

    def __init__(self, path, header, resume=False):
        self.path = str(path)
        self._buffer = []
        if resume and os.path.exists(self.path):
            # File exists, don't write header — appending
            pass
        else:
            with open(self.path, 'w', encoding='utf-8') as f:
                f.write(header)

    def append(self, section):
        """Buffer a section."""
        self._buffer.append(section)

    def flush(self):
        """Write buffered sections to file."""
        if self._buffer:
            with open(self.path, 'a', encoding='utf-8') as f:
                f.writelines(self._buffer)
            self._buffer = []

    def close(self):
        """Flush remaining and close."""
        self.flush()
