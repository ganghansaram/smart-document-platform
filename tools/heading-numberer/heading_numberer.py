"""
장절번호 평문화 도구 (GUI)

Word 문서(.docx)의 자동번호 헤딩을 텍스트로 변환하여 저장합니다.
WebBook 업로드 전 전처리용으로, 문서 담당자가 직접 실행할 수 있습니다.

원본 로직: tools/converter/word_preprocessor.py — flatten_heading_numbers()
"""

import os
import re
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

# ── 장절번호 평문화 핵심 로직 ─────────────────────────────────────────────────

_HEADING_PATTERN = re.compile(r"^(heading|제목)\s*\d", re.IGNORECASE)


def flatten_heading_numbers(input_path, output_path):
    """Word COM으로 헤딩 자동번호를 텍스트로 삽입 후 번호 서식 제거.

    Returns:
        (success: bool, message: str)
    """
    try:
        import win32com.client
        import pythoncom
    except ImportError:
        return False, "pywin32가 설치되어 있지 않습니다.\npip install pywin32"

    input_path = str(Path(input_path).resolve())
    output_path = str(Path(output_path).resolve())

    word = None
    doc = None
    try:
        pythoncom.CoInitialize()
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = False

        doc = word.Documents.Open(input_path, ReadOnly=True)

        # Pass 1: 번호 수집
        targets = []
        for i, para in enumerate(doc.Paragraphs):
            style_name = para.Style.NameLocal
            if not _HEADING_PATTERN.match(style_name):
                continue
            list_string = para.Range.ListFormat.ListString
            if not list_string or not list_string.strip():
                continue
            number_text = list_string.strip().rstrip(".")
            targets.append((i + 1, number_text))

        if not targets:
            return False, "자동번호가 적용된 헤딩이 없습니다.\n이미 평문화되었거나, 헤딩 스타일이 아닐 수 있습니다."

        # Pass 2: 역순으로 적용
        for para_index, number_text in reversed(targets):
            para = doc.Paragraphs(para_index)
            para.Range.ListFormat.RemoveNumbers()
            para.Range.InsertBefore(number_text + " ")

        # 필드 갱신
        try:
            for story_range in doc.StoryRanges:
                story_range.Fields.Update()
        except Exception:
            pass

        doc.SaveAs2(output_path, FileFormat=12)
        return True, f"{len(targets)}개 헤딩의 장절번호를 평문화했습니다."

    except Exception as e:
        return False, f"처리 중 오류가 발생했습니다:\n{e}"

    finally:
        try:
            if doc is not None:
                doc.Close(False)
        except Exception:
            pass
        try:
            if word is not None:
                word.Quit()
        except Exception:
            pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


# ── GUI ───────────────────────────────────────────────────────────────────────

class App:
    BG = "#1a1a2e"
    BG_CARD = "#22223a"
    BG_INPUT = "#2a2a44"
    FG = "#e2e8f0"
    FG_SUB = "#8a95a0"
    ACCENT = "#5ba3f5"
    SUCCESS = "#4ade80"
    ERROR = "#f87171"
    BORDER = "#334155"

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("장절번호 평문화 도구")
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)

        # 창 크기 및 중앙 배치
        w, h = 520, 420
        sx = (self.root.winfo_screenwidth() - w) // 2
        sy = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{sx}+{sy}")

        self._build_ui()

    def _build_ui(self):
        root = self.root
        pad = {"padx": 24}
        font = ("Segoe UI", 11)
        font_sm = ("Segoe UI", 9)

        # 타이틀
        tk.Label(
            root, text="장절번호 평문화", font=("Segoe UI", 18, "bold"),
            bg=self.BG, fg=self.FG
        ).pack(pady=(28, 4), **pad)

        tk.Label(
            root, text="Word 헤딩 자동번호를 텍스트로 변환합니다",
            font=font_sm, bg=self.BG, fg=self.FG_SUB
        ).pack(pady=(0, 20), **pad)

        # 파일 선택 영역
        frame = tk.Frame(root, bg=self.BG_CARD, highlightbackground=self.BORDER, highlightthickness=1)
        frame.pack(fill="x", **pad, pady=(0, 12))

        inner = tk.Frame(frame, bg=self.BG_CARD)
        inner.pack(fill="x", padx=16, pady=14)

        tk.Label(inner, text="입력 파일", font=font_sm, bg=self.BG_CARD, fg=self.FG_SUB, anchor="w").pack(fill="x")

        row = tk.Frame(inner, bg=self.BG_CARD)
        row.pack(fill="x", pady=(4, 0))

        self.path_var = tk.StringVar()
        self.path_entry = tk.Entry(
            row, textvariable=self.path_var, font=font, state="readonly",
            bg=self.BG_INPUT, fg=self.FG, relief="flat",
            readonlybackground=self.BG_INPUT, insertbackground=self.FG
        )
        self.path_entry.pack(side="left", fill="x", expand=True, ipady=4)

        self.browse_btn = tk.Button(
            row, text="찾아보기", font=font_sm, bg=self.ACCENT, fg="#ffffff",
            activebackground="#4a93e5", activeforeground="#ffffff",
            relief="flat", cursor="hand2", padx=12, pady=2,
            command=self._browse
        )
        self.browse_btn.pack(side="right", padx=(8, 0))

        # 실행 버튼
        self.run_btn = tk.Button(
            root, text="변환 실행", font=("Segoe UI", 12, "bold"),
            bg=self.ACCENT, fg="#ffffff",
            activebackground="#4a93e5", activeforeground="#ffffff",
            relief="flat", cursor="hand2", padx=20, pady=8,
            state="disabled", command=self._run
        )
        self.run_btn.pack(pady=(8, 12), **pad)

        # 상태 메시지
        self.status_var = tk.StringVar()
        self.status_label = tk.Label(
            root, textvariable=self.status_var, font=font_sm,
            bg=self.BG, fg=self.FG_SUB, wraplength=470, justify="center"
        )
        self.status_label.pack(pady=(0, 12), **pad)

        # 하단 안내
        notes = (
            "※ 안내 사항\n"
            "• 변환 대상 파일이 Word에서 열려 있으면 닫아주세요.\n"
            "• 원본 파일은 변경되지 않으며, 결과는 별도 파일로 저장됩니다.\n"
            "• 변환 중 백그라운드에서 Word가 잠시 실행됩니다."
        )
        tk.Label(
            root, text=notes, font=font_sm,
            bg=self.BG, fg=self.FG_SUB, justify="left", anchor="w", wraplength=470
        ).pack(side="bottom", fill="x", **pad, pady=(0, 20))

        # 드래그 앤 드롭 (windnd 있을 때만)
        try:
            import windnd
            windnd.hook_dropfiles(root, self._on_drop)
        except ImportError:
            pass

    def _browse(self):
        path = filedialog.askopenfilename(
            title="DOCX 파일 선택",
            filetypes=[("Word 문서", "*.docx"), ("모든 파일", "*.*")]
        )
        if path:
            self._set_path(path)

    def _on_drop(self, files):
        if files:
            path = files[0]
            if isinstance(path, bytes):
                path = path.decode("utf-8", errors="replace")
            if path.lower().endswith(".docx"):
                self._set_path(path)

    def _set_path(self, path):
        self.path_var.set(path)
        self.run_btn.config(state="normal")
        self.status_var.set("")
        self.status_label.config(fg=self.FG_SUB)

    def _run(self):
        src = self.path_var.get()
        if not src or not os.path.isfile(src):
            self.status_var.set("파일을 찾을 수 없습니다.")
            self.status_label.config(fg=self.ERROR)
            return

        p = Path(src)
        dst = str(p.parent / f"{p.stem}_번호평문화{p.suffix}")

        self.run_btn.config(state="disabled", text="변환 중...")
        self.browse_btn.config(state="disabled")
        self.status_var.set("Word를 실행하여 처리 중입니다...")
        self.status_label.config(fg=self.FG_SUB)
        self.root.update()

        def worker():
            ok, msg = flatten_heading_numbers(src, dst)
            self.root.after(0, lambda: self._on_done(ok, msg, dst))

        threading.Thread(target=worker, daemon=True).start()

    def _on_done(self, ok, msg, dst):
        self.run_btn.config(state="normal", text="변환 실행")
        self.browse_btn.config(state="normal")

        if ok:
            self.status_var.set(f"{msg}\n→ {dst}")
            self.status_label.config(fg=self.SUCCESS)
        else:
            self.status_var.set(msg)
            self.status_label.config(fg=self.ERROR)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    # CLI 모드: 인자가 있으면 GUI 없이 실행
    if len(sys.argv) >= 2:
        src = sys.argv[1]
        if not os.path.isfile(src):
            print(f"파일을 찾을 수 없습니다: {src}")
            sys.exit(1)
        p = Path(src)
        dst = sys.argv[2] if len(sys.argv) >= 3 else str(p.parent / f"{p.stem}_번호평문화{p.suffix}")
        ok, msg = flatten_heading_numbers(src, dst)
        print(msg)
        sys.exit(0 if ok else 1)

    # GUI 모드
    App().run()
