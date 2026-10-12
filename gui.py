"""Single-window Tk interface for the EMU8086 assembler analyzer."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Callable

from assembler import AnalysisResult, assemble


@dataclass(frozen=True, slots=True)
class UiRows:
    token_rows: list[tuple[str, ...]]
    diagnostic_rows: list[tuple[str, ...]]
    symbol_rows: list[tuple[str, ...]]
    machine_rows: list[tuple[str, ...]]


def _display_value(value: object | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.hex(" ").upper()
    return str(value)


def render_result(result: AnalysisResult) -> UiRows:
    """Convert engine output into display rows without internal separators."""
    token_rows = [
        (str(token.line), token.lexeme, token.category, _display_value(token.value))
        for token in result.tokens
        if token.category != "separator"
    ]
    diagnostic_rows = [
        ("" if diagnostic.line is None else str(diagnostic.line), diagnostic.phase, diagnostic.code, diagnostic.message)
        for diagnostic in result.diagnostics
    ]
    symbol_rows = [
        (
            symbol.name,
            symbol.kind,
            symbol.segment or "default",
            "" if symbol.address is None else f"{symbol.address:04X}",
            "" if symbol.value is None else str(symbol.value),
        )
        for symbol in result.symbols
    ]
    machine_rows = [
        (str(row.line), row.segment, f"{row.address:04X}", row.display_hex, row.source)
        for row in result.machine_rows
    ]
    return UiRows(token_rows, diagnostic_rows, symbol_rows, machine_rows)


_SAMPLE = """org 100h
inicio: mov ax, 1234h
        int 21h
"""


class AssemblerApp:
    def __init__(self, root: tk.Tk, analyzer: Callable[[str, Path | None], AnalysisResult] = assemble):
        self.root = root
        self.analyzer = analyzer
        self.file_path: Path | None = None
        self._line_refresh_pending = False
        self._configure_window()
        self._build_layout()
        self._set_source(_SAMPLE)
        self.analyze()

    def _configure_window(self) -> None:
        self.root.title("Analizador de ensamblador · EMU8086 4.08")
        self.root.geometry("1440x900")
        self.root.minsize(1080, 680)
        self.root.configure(background="#eef2f6")
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#eef2f6")
        style.configure("Toolbar.TFrame", background="#17324d")
        style.configure("Toolbar.TLabel", background="#17324d", foreground="#ffffff", font=("Segoe UI", 11, "bold"))
        style.configure("TLabel", background="#eef2f6", foreground="#243b53", font=("Segoe UI", 9))
        style.configure("TLabelframe", background="#f8fafc", bordercolor="#cbd5e1")
        style.configure("TLabelframe.Label", background="#f8fafc", foreground="#17324d", font=("Segoe UI", 9, "bold"))
        style.configure("Treeview", background="#ffffff", fieldbackground="#ffffff", foreground="#172b4d", rowheight=23, font=("Consolas", 9))
        style.configure("Treeview.Heading", background="#dce6ef", foreground="#17324d", font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#c7e7e2")], foreground=[("selected", "#102a43")])
        style.configure("Accent.TButton", background="#19a58a", foreground="#ffffff", font=("Segoe UI", 9, "bold"), padding=(12, 7))
        style.map("Accent.TButton", background=[("active", "#138b75")])

    def _build_layout(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self.root, style="Toolbar.TFrame", padding=(14, 10))
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(3, weight=1)
        ttk.Label(toolbar, text="ANALIZADOR EMU8086", style="Toolbar.TLabel").grid(row=0, column=0, padx=(0, 16))
        ttk.Button(toolbar, text="Abrir .asm", command=self.open_file).grid(row=0, column=1, padx=(0, 8))
        ttk.Button(toolbar, text="Analizar", style="Accent.TButton", command=self.analyze).grid(row=0, column=2, padx=(0, 14))
        self.path_label = ttk.Label(toolbar, text="Ejemplo integrado", style="Toolbar.TLabel")
        self.path_label.grid(row=0, column=3, sticky="w")
        self.status_label = ttk.Label(toolbar, text="Listo", style="Toolbar.TLabel")
        self.status_label.grid(row=0, column=4, sticky="e")

        main = ttk.Panedwindow(self.root, orient=tk.VERTICAL)
        main.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        top = ttk.Panedwindow(main, orient=tk.HORIZONTAL)
        bottom = ttk.Panedwindow(main, orient=tk.HORIZONTAL)
        main.add(top, weight=1)
        main.add(bottom, weight=1)

        editor_frame = ttk.LabelFrame(top, text="Código fuente", padding=7)
        token_frame = ttk.LabelFrame(top, text="Etapa 1 · análisis léxico", padding=7)
        top.add(editor_frame, weight=5)
        top.add(token_frame, weight=6)
        self._build_editor(editor_frame)
        self.token_tree = self._build_tree(token_frame, ("line", "lexeme", "category", "value"), ("Línea", "Lexema", "Categoría", "Valor"), (55, 150, 125, 140))

        diagnostic_frame = ttk.LabelFrame(bottom, text="Etapa 2 · sintaxis y semántica", padding=7)
        stage_three = ttk.LabelFrame(bottom, text="Etapa 3 · símbolos, direcciones y código máquina", padding=7)
        bottom.add(diagnostic_frame, weight=4)
        bottom.add(stage_three, weight=7)
        self.diagnostic_tree = self._build_tree(diagnostic_frame, ("line", "phase", "code", "message"), ("Línea", "Tipo", "Código", "Mensaje"), (54, 95, 78, 330))

        stage_split = ttk.Panedwindow(stage_three, orient=tk.HORIZONTAL)
        stage_split.pack(fill="both", expand=True)
        symbol_frame = ttk.LabelFrame(stage_split, text="Tabla de símbolos", padding=6)
        machine_frame = ttk.LabelFrame(stage_split, text="Listado hexadecimal", padding=6)
        stage_split.add(symbol_frame, weight=4)
        stage_split.add(machine_frame, weight=6)
        self.symbol_tree = self._build_tree(symbol_frame, ("name", "kind", "segment", "address", "value"), ("Nombre", "Tipo", "Segmento", "Offset", "Valor/tamaño"), (105, 75, 80, 70, 95))
        self.machine_tree = self._build_tree(machine_frame, ("line", "segment", "address", "bytes", "source"), ("Línea", "Segmento", "Offset", "Bytes", "Fuente"), (48, 70, 70, 220, 210))

    def _build_editor(self, parent: ttk.LabelFrame) -> None:
        editor_wrap = ttk.Frame(parent)
        editor_wrap.pack(fill="both", expand=True)
        editor_wrap.rowconfigure(0, weight=1)
        editor_wrap.columnconfigure(1, weight=1)
        self.line_numbers = tk.Text(editor_wrap, width=4, padx=5, pady=6, takefocus=0, wrap="none", borderwidth=0, background="#e8eef4", foreground="#61758a", font=("Consolas", 10), state="disabled")
        self.line_numbers.grid(row=0, column=0, sticky="ns")
        self.editor = tk.Text(editor_wrap, wrap="none", undo=True, padx=8, pady=6, borderwidth=0, background="#ffffff", foreground="#172b4d", insertbackground="#17324d", font=("Consolas", 10), tabs=(32,))
        self.editor.grid(row=0, column=1, sticky="nsew")
        scroll = ttk.Scrollbar(editor_wrap, orient="vertical", command=self._scroll_editor)
        self.editor_scrollbar = scroll
        scroll.grid(row=0, column=2, sticky="ns")
        horizontal = ttk.Scrollbar(editor_wrap, orient="horizontal", command=self.editor.xview)
        horizontal.grid(row=1, column=1, sticky="ew")
        self.editor.configure(yscrollcommand=self._editor_scrolled, xscrollcommand=horizontal.set)
        self.editor.bind("<<Modified>>", self._source_modified)
        self.editor.bind("<KeyRelease>", self._source_modified)

    def _build_tree(self, parent: ttk.LabelFrame, columns: tuple[str, ...], headings: tuple[str, ...], widths: tuple[int, ...]) -> ttk.Treeview:
        wrap = ttk.Frame(parent)
        wrap.pack(fill="both", expand=True)
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=1)
        tree = ttk.Treeview(wrap, columns=columns, show="headings", selectmode="browse")
        for name, heading, width in zip(columns, headings, widths):
            tree.heading(name, text=heading)
            tree.column(name, width=width, minwidth=45, anchor="w", stretch=name in {"message", "source", "bytes", "value"})
        vertical = ttk.Scrollbar(wrap, orient="vertical", command=tree.yview)
        horizontal = ttk.Scrollbar(wrap, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        tree.tag_configure("error", foreground="#a4262c")
        tree.tag_configure("warning", foreground="#986f0b")
        tree.tag_configure("success", foreground="#16794b")
        return tree

    def _scroll_editor(self, *args) -> None:
        self.editor.yview(*args)
        self.line_numbers.yview(*args)

    def _editor_scrolled(self, first: str, last: str) -> None:
        self.editor_scrollbar.set(first, last)
        self.line_numbers.yview_moveto(first)
        self._source_modified()

    def _source_modified(self, _event=None) -> None:
        if self._line_refresh_pending:
            return
        self._line_refresh_pending = True
        self.root.after_idle(self._refresh_line_numbers)

    def _refresh_line_numbers(self) -> None:
        self._line_refresh_pending = False
        if not hasattr(self, "editor"):
            return
        count = int(self.editor.index("end-1c").split(".")[0])
        content = "\n".join(str(line) for line in range(1, count + 1))
        self.line_numbers.configure(state="normal")
        self.line_numbers.delete("1.0", "end")
        self.line_numbers.insert("1.0", content)
        self.line_numbers.configure(state="disabled")
        self.line_numbers.yview_moveto(self.editor.yview()[0])
        self.editor.edit_modified(False)

    def _set_source(self, source: str) -> None:
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", source)
        self.editor.edit_modified(False)
        self._source_modified()

    def open_file(self) -> None:
        selected = filedialog.askopenfilename(
            parent=self.root,
            title="Abrir archivo ensamblador",
            filetypes=(("Archivos ensamblador", "*.asm"), ("Todos los archivos", "*.*")),
        )
        if not selected:
            return
        path = Path(selected)
        try:
            source = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError) as exc:
            self.status_label.configure(text=f"No se pudo abrir: {exc}")
            return
        self.file_path = path
        self.path_label.configure(text=str(path))
        self._set_source(source)
        self.analyze()

    def analyze(self) -> None:
        source = self.editor.get("1.0", "end-1c")
        base_dir = self.file_path.parent if self.file_path else None
        result = self.analyzer(source, base_dir)
        rows = render_result(result)
        self._fill(self.token_tree, rows.token_rows)
        diagnostics = rows.diagnostic_rows or [("", "estado", "OK", "No se encontraron errores.")]
        self._fill(self.diagnostic_tree, diagnostics, diagnostic_tags=True)
        self._fill(self.symbol_tree, rows.symbol_rows)
        self._fill(self.machine_tree, rows.machine_rows)
        errors = sum(diagnostic.severity == "error" for diagnostic in result.diagnostics)
        if errors:
            self.status_label.configure(text=f"{errors} error(es) · sin código máquina")
        else:
            self.status_label.configure(text=f"Correcto · {len(result.machine_rows)} fila(s) de salida")

    @staticmethod
    def _fill(tree: ttk.Treeview, rows: list[tuple[str, ...]], diagnostic_tags: bool = False) -> None:
        children = tree.get_children()
        if children:
            tree.delete(*children)
        for row in rows:
            tag = ""
            if diagnostic_tags:
                tag = "error" if row[2] != "OK" else "success"
            tree.insert("", "end", values=row, tags=(tag,) if tag else ())

