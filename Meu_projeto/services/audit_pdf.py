"""Gera PDF administrativo em memoria, sem criar arquivos no servidor."""

from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Iterable
from zoneinfo import ZoneInfo


PAGE_WIDTH = 842.0  # A4 paisagem, pontos
PAGE_HEIGHT = 595.0
MARGIN = 18.0
LINE_HEIGHT = 9.0
BOTTOM = 28.0
COLUMNS = [
    ("Data e hora", "data", 78.0),
    ("Usuário", "usuario", 82.0),
    ("Ação", "acao", 58.0),
    ("Entidade", "entidade", 70.0),
    ("Registro", "registro", 44.0),
    ("Resumo", "resumo", 220.0),
    ("Alterações", "alteracoes", 254.0),
]
assert math.isclose(sum(width for _, _, width in COLUMNS), PAGE_WIDTH - 2 * MARGIN)


def _pdf_text(value: str) -> str:
    printable = str(value).replace("→", "->").replace("—", "-")
    return "<" + printable.encode("cp1252", errors="replace").hex().upper() + ">"


def _wrap(value: str, width: float, font_size: float = 7.2) -> list[str]:
    # Helvetica média aproxima 0.52em; sempre quebrar palavras muito longas.
    limit = max(5, int((width - 8) / (font_size * 0.52)))
    result: list[str] = []
    line = ""
    for word in str(value or "").split() or [""]:
        while len(word) > limit:
            if line:
                result.append(line)
                line = ""
            result.append(word[:limit])
            word = word[limit:]
        candidate = f"{line} {word}".strip()
        if len(candidate) > limit:
            result.append(line)
            line = word
        else:
            line = candidate
    if line or not result:
        result.append(line)
    return result


def build_audit_pdf(
    rows: Iterable[dict[str, str]],
    *,
    filters_description: str,
    emitted_at: datetime | None = None,
) -> bytes:
    """Cria A4 paisagem paginado; textos longos quebram e continuam na página seguinte."""
    emitted_at = emitted_at or datetime.now(ZoneInfo("America/Sao_Paulo"))
    all_rows = list(rows)
    pages: list[list[str]] = []
    commands: list[str] = []
    y = 0.0

    def text(x: float, baseline: float, value: str, *, size: float = 7.2, font: str = "F1") -> None:
        commands.append(
            # PDF fill color is stateful. Table backgrounds set it to pale/white,
            # so reset it for every text run to keep labels and cells visible.
            f"0 0 0 rg BT /{font} {size:.1f} Tf 1 0 0 1 {x:.2f} {baseline:.2f} Tm {_pdf_text(value)} Tj ET"
        )

    def finish_page() -> None:
        if commands:
            pages.append(commands.copy())

    def table_header(top: float) -> float:
        height = 22.0
        commands.append("0.91 0.94 0.92 rg")
        commands.append(f"{MARGIN} {top-height:.2f} {PAGE_WIDTH-2*MARGIN:.2f} {height:.2f} re f")
        commands.append("0.70 0.75 0.72 RG 0.4 w")
        commands.append(f"{MARGIN} {top-height:.2f} {PAGE_WIDTH-2*MARGIN:.2f} {height:.2f} re S")
        x = MARGIN
        for index, (label, _, width) in enumerate(COLUMNS):
            text(x + 4, top - 14, label, size=7.2, font="F2")
            x += width
            if index < len(COLUMNS) - 1:
                commands.append(f"{x:.2f} {top-height:.2f} m {x:.2f} {top:.2f} l S")
        return top - height

    def start_page(first: bool) -> None:
        nonlocal commands, y
        if commands:
            finish_page()
        commands = ["0 0 0 rg", "0.30 0.47 0.39 RG 0.7 w"]
        if first:
            text(MARGIN, PAGE_HEIGHT - 26, "NextStock", size=17, font="F2")
            text(MARGIN, PAGE_HEIGHT - 45, "Relatório de Auditoria", size=11, font="F2")
            text(MARGIN, PAGE_HEIGHT - 60, "Emitido em " + emitted_at.strftime("%d/%m/%Y %H:%M:%S %Z"), size=7.2)
            filter_lines = _wrap("Filtros: " + (filters_description or "Todos os registros"), PAGE_WIDTH - 2 * MARGIN, 7.2)
            for index, line in enumerate(filter_lines[:3]):
                text(MARGIN, PAGE_HEIGHT - 73 - index * LINE_HEIGHT, line, size=7.2)
            header_top = PAGE_HEIGHT - 80 - (len(filter_lines[:3]) - 1) * LINE_HEIGHT
        else:
            text(MARGIN, PAGE_HEIGHT - 25, "NextStock — Relatório de Auditoria", size=12, font="F2")
            header_top = PAGE_HEIGHT - 37
        y = table_header(header_top)

    start_page(True)
    for row in all_rows:
        cell_lines = [
            _wrap(row.get(key, ""), width)
            for _, key, width in COLUMNS
        ]
        while any(cell_lines):
            room = y - BOTTOM
            lines_fit = max(1, int((room - 8) // LINE_HEIGHT))
            segment = [lines[:lines_fit] for lines in cell_lines]
            height = max(18.0, max((len(lines) for lines in segment), default=1) * LINE_HEIGHT + 7)
            if height > room and y < PAGE_HEIGHT - 45:
                start_page(False)
                continue
            commands.append("1 1 1 rg")
            commands.append(f"{MARGIN} {y-height:.2f} {PAGE_WIDTH-2*MARGIN:.2f} {height:.2f} re f")
            commands.append("0.82 0.85 0.83 RG 0.3 w")
            commands.append(f"{MARGIN} {y-height:.2f} {PAGE_WIDTH-2*MARGIN:.2f} {height:.2f} re S")
            x = MARGIN
            for col_index, ((_, _, width), lines) in enumerate(zip(COLUMNS, segment)):
                for line_index, line in enumerate(lines):
                    text(x + 4, y - 11 - line_index * LINE_HEIGHT, line)
                x += width
                if col_index < len(COLUMNS) - 1:
                    commands.append(f"{x:.2f} {y-height:.2f} m {x:.2f} {y:.2f} l S")
            y -= height
            cell_lines = [lines[lines_fit:] for lines in cell_lines]
            if any(cell_lines):
                start_page(False)

    finish_page()
    page_count = len(pages)
    for page_number, page_commands in enumerate(pages, start=1):
        page_commands.append("0.65 0.68 0.66 RG 0.3 w")
        page_commands.append(f"{MARGIN} 20 m {PAGE_WIDTH-MARGIN} 20 l S")
        page_commands.append(
            f"0 0 0 rg BT /F1 7 Tf 1 0 0 1 {PAGE_WIDTH-MARGIN-70:.2f} 9 Tm "
            f"{_pdf_text(f'Página {page_number} de {page_count}')} Tj ET"
        )

    content_streams = ["\n".join(page).encode("ascii") for page in pages]
    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"",  # Pages tree
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    ]
    page_ids: list[int] = []
    for content in content_streams:
        page_id = len(objects) + 1
        stream_id = page_id + 1
        page_ids.append(page_id)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH:.2f} {PAGE_HEIGHT:.2f}] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> /Contents {stream_id} 0 R >>".encode("ascii")
        )
        objects.append(
            f"<< /Length {len(content)} >>\nstream\n".encode("ascii")
            + content + b"\nendstream"
        )
    kids = " ".join(f"{object_id} 0 R" for object_id in page_ids)
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {page_count} >>".encode("ascii")
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_position = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref_position}\n%%EOF".encode("ascii"))
    return bytes(output)


def extract_hex_pdf_text(pdf: bytes) -> str:
    """Helper simples de teste para conferir os textos WinAnsi do PDF gerado."""
    pieces = re.findall(rb"<([0-9A-F]+)> Tj", pdf)
    return "".join(bytes.fromhex(piece.decode("ascii")).decode("cp1252", errors="replace") for piece in pieces)
