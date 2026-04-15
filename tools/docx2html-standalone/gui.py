#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
DOCX → HTML 변환기 GUI (Tkinter)

심플하고 정렬된 UI. 폰트 크기 일관성 유지.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path


class DocxConverterGUI:
    # 다크 테마 컬러
    BG = "#1a1a2e"
    BG_CARD = "#22223a"
    BG_INPUT = "#2a2a44"
    FG = "#e2e8f0"
    FG_SUB = "#8a95a0"
    FG_PLACEHOLDER = "#5a6570"
    ACCENT = "#5ba3f5"
    SUCCESS = "#4ade80"
    ERROR = "#f87171"
    BORDER = "#334155"

    FONT = ("Segoe UI", 10)
    FONT_SM = ("Segoe UI", 9)
    FONT_LABEL = ("Segoe UI", 9)
    FONT_TITLE = ("Segoe UI", 16, "bold")
    FONT_BTN = ("Segoe UI", 11, "bold")

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DOCX → HTML 변환기")
        self.root.configure(bg=self.BG)
        self.root.resizable(False, False)

        w, h = 520, 520
        sx = (self.root.winfo_screenwidth() - w) // 2
        sy = (self.root.winfo_screenheight() - h) // 2
        self.root.geometry(f"{w}x{h}+{sx}+{sy}")

        self._advanced_visible = False
        self._build_ui()

    # ── UI 구성 ─────────────────────────────────────────────────

    def _build_ui(self):
        root = self.root
        pad_x = 24

        # 타이틀
        tk.Label(
            root, text="DOCX → HTML 변환기", font=self.FONT_TITLE,
            bg=self.BG, fg=self.FG
        ).pack(pady=(24, 2))

        tk.Label(
            root, text="Word 문서를 HTML로 변환합니다",
            font=self.FONT_SM, bg=self.BG, fg=self.FG_SUB
        ).pack(pady=(0, 16))

        # ── 메인 카드 ───────────────────────────────────────────
        card = tk.Frame(root, bg=self.BG_CARD,
                        highlightbackground=self.BORDER, highlightthickness=1)
        card.pack(fill="x", padx=pad_x, pady=(0, 12))

        inner = tk.Frame(card, bg=self.BG_CARD)
        inner.pack(fill="x", padx=16, pady=14)

        # 입력 파일
        self._add_label(inner, "입력 파일")
        input_row = tk.Frame(inner, bg=self.BG_CARD)
        input_row.pack(fill="x", pady=(2, 10))

        self.input_var = tk.StringVar()
        self.input_entry = tk.Entry(
            input_row, textvariable=self.input_var, font=self.FONT,
            state="readonly", bg=self.BG_INPUT, fg=self.FG,
            relief="flat", readonlybackground=self.BG_INPUT,
            insertbackground=self.FG
        )
        self.input_entry.pack(side="left", fill="x", expand=True, ipady=3)

        self.browse_btn = tk.Button(
            input_row, text="찾아보기", font=self.FONT_SM,
            bg=self.ACCENT, fg="#ffffff",
            activebackground="#4a93e5", activeforeground="#ffffff",
            relief="flat", cursor="hand2", padx=10, pady=1,
            command=self._browse_input
        )
        self.browse_btn.pack(side="right", padx=(8, 0))

        # 출력 디렉토리
        self._add_label(inner, "출력 위치")
        output_row = tk.Frame(inner, bg=self.BG_CARD)
        output_row.pack(fill="x", pady=(2, 10))

        self.output_var = tk.StringVar()
        self.output_entry = tk.Entry(
            output_row, textvariable=self.output_var, font=self.FONT,
            state="readonly", bg=self.BG_INPUT, fg=self.FG,
            relief="flat", readonlybackground=self.BG_INPUT,
            insertbackground=self.FG
        )
        self.output_entry.pack(side="left", fill="x", expand=True, ipady=3)

        tk.Button(
            output_row, text="변경", font=self.FONT_SM,
            bg=self.BG_INPUT, fg=self.FG_SUB,
            activebackground="#3a3a54", activeforeground=self.FG,
            relief="flat", cursor="hand2", padx=10, pady=1,
            command=self._browse_output
        ).pack(side="right", padx=(8, 0))

        # 체크박스: 전처리
        self.preprocess_var = tk.BooleanVar(value=True)
        self.preprocess_chk = tk.Checkbutton(
            inner, text="장절번호 전처리 (Word 설치 필요)",
            variable=self.preprocess_var, font=self.FONT_SM,
            bg=self.BG_CARD, fg=self.FG, selectcolor=self.BG_INPUT,
            activebackground=self.BG_CARD, activeforeground=self.FG,
            anchor="w"
        )
        self.preprocess_chk.pack(fill="x", pady=(0, 4))

        # ── 고급 옵션 토글 ──────────────────────────────────────
        self.adv_toggle = tk.Label(
            inner, text="▸ 고급 옵션", font=self.FONT_SM,
            bg=self.BG_CARD, fg=self.ACCENT, cursor="hand2", anchor="w"
        )
        self.adv_toggle.pack(fill="x", pady=(4, 0))
        self.adv_toggle.bind("<Button-1>", self._toggle_advanced)

        # 고급 옵션 프레임 (초기 숨김)
        self.adv_frame = tk.Frame(inner, bg=self.BG_CARD)
        # 3열 그리드: 라벨 | 입력 | 설명
        self._add_label(self.adv_frame, "")  # spacer
        adv_grid = tk.Frame(self.adv_frame, bg=self.BG_CARD)
        adv_grid.pack(fill="x")

        # HTML 파일명
        self.html_name_var = tk.StringVar()
        self._add_adv_row(adv_grid, 0, "HTML 파일명", self.html_name_var, "비우면 원본 파일명 사용")

        # 이미지 폴더명
        self.image_dir_var = tk.StringVar()
        self._add_adv_row(adv_grid, 1, "이미지 폴더", self.image_dir_var, "비우면 {파일명}_images")

        # 이미지 경로 접두사
        self.image_prefix_var = tk.StringVar()
        self._add_adv_row(adv_grid, 2, "이미지 경로", self.image_prefix_var, "비우면 상대경로 자동")

        # ── 실행 / 상태 ─────────────────────────────────────────

        # 진행률 바
        self.progress_frame = tk.Frame(root, bg=self.BG, height=6)
        self.progress_frame.pack(fill="x", padx=pad_x, pady=(0, 4))
        self.progress_frame.pack_propagate(False)

        self.progress_bar = tk.Frame(self.progress_frame, bg=self.ACCENT, width=0)
        self.progress_bar.place(x=0, y=0, relheight=1)

        # 상태 메시지
        self.status_var = tk.StringVar()
        self.status_label = tk.Label(
            root, textvariable=self.status_var, font=self.FONT_SM,
            bg=self.BG, fg=self.FG_SUB, wraplength=470, justify="center"
        )
        self.status_label.pack(pady=(0, 8), padx=pad_x)

        # 버튼 영역
        btn_frame = tk.Frame(root, bg=self.BG)
        btn_frame.pack(pady=(0, 8))

        self.run_btn = tk.Button(
            btn_frame, text="변환", font=self.FONT_BTN,
            bg=self.ACCENT, fg="#ffffff",
            activebackground="#4a93e5", activeforeground="#ffffff",
            relief="flat", cursor="hand2", padx=24, pady=6,
            state="disabled", command=self._run
        )
        self.run_btn.pack(side="left", padx=(0, 8))

        self.preprocess_btn = tk.Button(
            btn_frame, text="전처리만", font=self.FONT_SM,
            bg=self.BG_INPUT, fg=self.FG_SUB,
            activebackground="#3a3a54", activeforeground=self.FG,
            relief="flat", cursor="hand2", padx=12, pady=4,
            state="disabled", command=self._run_preprocess_only
        )
        self.preprocess_btn.pack(side="left", padx=(0, 8))

        self.open_btn = tk.Button(
            btn_frame, text="폴더 열기", font=self.FONT_SM,
            bg=self.BG_INPUT, fg=self.FG_SUB,
            activebackground="#3a3a54", activeforeground=self.FG,
            relief="flat", cursor="hand2", padx=12, pady=4,
            state="disabled", command=self._open_folder
        )
        self.open_btn.pack(side="left")

        # 하단 안내
        notes = (
            "※ 변환 대상 파일이 Word에서 열려 있으면 닫아주세요.\n"
            "   원본 파일은 변경되지 않습니다.\n"
            "   DRM 환경: '전처리만' → DRM 해제 → '변환' 순서로 진행"
        )
        tk.Label(
            root, text=notes, font=self.FONT_SM,
            bg=self.BG, fg=self.FG_SUB, justify="left", anchor="w",
            wraplength=470
        ).pack(side="bottom", fill="x", padx=pad_x, pady=(0, 16))

        # 드래그 앤 드롭
        try:
            import windnd
            windnd.hook_dropfiles(root, self._on_drop)
        except ImportError:
            pass

    # ── 헬퍼: UI 요소 생성 ──────────────────────────────────────

    def _add_label(self, parent, text):
        """일관된 폰트/색상으로 라벨 생성"""
        tk.Label(
            parent, text=text, font=self.FONT_LABEL,
            bg=self.BG_CARD, fg=self.FG_SUB, anchor="w"
        ).pack(fill="x")

    def _add_adv_row(self, parent, row, label, var, placeholder):
        """고급 옵션 그리드 행 추가 — 라벨(80px) | 입력(stretch) | 설명"""
        lbl = tk.Label(
            parent, text=label, font=self.FONT_LABEL,
            bg=self.BG_CARD, fg=self.FG_SUB, anchor="w", width=10
        )
        lbl.grid(row=row, column=0, sticky="w", pady=2)

        entry = tk.Entry(
            parent, textvariable=var, font=self.FONT,
            bg=self.BG_INPUT, fg=self.FG, relief="flat",
            insertbackground=self.FG
        )
        entry.grid(row=row, column=1, sticky="ew", padx=(4, 8), pady=2, ipady=2)

        hint = tk.Label(
            parent, text=placeholder, font=self.FONT_SM,
            bg=self.BG_CARD, fg=self.FG_PLACEHOLDER, anchor="w"
        )
        hint.grid(row=row, column=2, sticky="w", pady=2)

        parent.columnconfigure(1, weight=1)

    # ── 이벤트 핸들러 ───────────────────────────────────────────

    def _browse_input(self):
        path = filedialog.askopenfilename(
            title="DOCX 파일 선택",
            filetypes=[("Word 문서", "*.docx"), ("모든 파일", "*.*")]
        )
        if path:
            self._set_input(path)

    def _browse_output(self):
        current = self.output_var.get() or str(Path.home())
        path = filedialog.askdirectory(title="출력 디렉토리 선택", initialdir=current)
        if path:
            self.output_var.set(path)

    def _on_drop(self, files):
        if files:
            path = files[0]
            if isinstance(path, bytes):
                path = path.decode("utf-8", errors="replace")
            if path.lower().endswith(".docx"):
                self._set_input(path)

    def _set_input(self, path):
        self.input_var.set(path)
        self.output_var.set(str(Path(path).parent))
        self.run_btn.config(state="normal")
        self.preprocess_btn.config(state="normal")
        self.open_btn.config(state="disabled")
        self.status_var.set("")
        self.status_label.config(fg=self.FG_SUB)
        self._reset_progress()

    def _toggle_advanced(self, event=None):
        self._advanced_visible = not self._advanced_visible
        if self._advanced_visible:
            self.adv_toggle.config(text="▾ 고급 옵션")
            self.adv_frame.pack(fill="x", pady=(4, 0))
            # 창 높이 늘림
            self.root.geometry("520x600")
        else:
            self.adv_toggle.config(text="▸ 고급 옵션")
            self.adv_frame.pack_forget()
            self.root.geometry("520x520")

    def _open_folder(self):
        folder = self.output_var.get()
        if folder and os.path.isdir(folder):
            os.startfile(folder)

    # ── 변환 실행 ───────────────────────────────────────────────

    def _run(self):
        src = self.input_var.get()
        if not src or not os.path.isfile(src):
            self.status_var.set("파일을 찾을 수 없습니다.")
            self.status_label.config(fg=self.ERROR)
            return

        input_path = Path(src).resolve()
        output_dir = Path(self.output_var.get() or input_path.parent).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        # HTML 파일명
        html_name = self.html_name_var.get().strip()
        if html_name:
            if not html_name.endswith('.html'):
                html_name += '.html'
            output_path = output_dir / html_name
        else:
            output_path = output_dir / input_path.with_suffix('.html').name

        image_dir_name = self.image_dir_var.get().strip() or None
        image_prefix = self.image_prefix_var.get().strip() or None
        do_preprocess = self.preprocess_var.get()

        # UI 잠금
        self.run_btn.config(state="disabled", text="변환 중...")
        self.browse_btn.config(state="disabled")
        self.open_btn.config(state="disabled")
        self._set_status("변환 준비 중...", self.FG_SUB)
        self._set_progress(0.1)
        self.root.update()

        def worker():
            try:
                actual_input = input_path

                # 전처리
                if do_preprocess:
                    self.root.after(0, lambda: self._set_status("장절번호 전처리 중...", self.FG_SUB))
                    self.root.after(0, lambda: self._set_progress(0.2))
                    try:
                        from word_preprocessor import preprocess_docx
                        preprocessed = preprocess_docx(str(input_path))
                        if preprocessed != str(input_path):
                            actual_input = Path(preprocessed)
                            self.root.after(0, lambda: self._set_status(
                                "전처리 완료. HTML 변환 중...", self.FG_SUB))
                        else:
                            self.root.after(0, lambda: self._set_status(
                                "전처리 건너뜀 (원본 사용). HTML 변환 중...", self.FG_SUB))
                    except Exception as e:
                        err_msg = str(e)
                        self.root.after(0, lambda m=err_msg: self._set_status(
                            f"전처리 실패: {m} — 원본으로 변환 계속", self.ERROR))

                # 변환
                self.root.after(0, lambda: self._set_status("HTML 변환 중...", self.FG_SUB))
                self.root.after(0, lambda: self._set_progress(0.5))

                from converter import DocxConverter
                converter = DocxConverter()
                result = converter.convert(
                    str(actual_input), str(output_path),
                    image_dir_name=image_dir_name,
                    image_prefix=image_prefix
                )

                # 임시 파일 정리
                if actual_input != input_path and actual_input.exists():
                    try:
                        actual_input.unlink()
                    except OSError:
                        pass

                self.root.after(0, lambda: self._on_done(result))

            except Exception as e:
                self.root.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_done(self, result):
        self._unlock_ui()

        if result.success:
            self._set_progress(1.0)
            stats = result.stats
            msg = (
                f"변환 완료!\n"
                f"단락 {stats['paragraphs']}개 · "
                f"표 {stats['tables']}개 · "
                f"이미지 {stats['images']}개"
            )
            if result.warnings:
                msg += f"\n경고 {len(result.warnings)}건"
            self._set_status(msg, self.SUCCESS)
            self.open_btn.config(state="normal")
        else:
            self._reset_progress()
            self._set_status(f"변환 실패: {result.error_message}", self.ERROR)

    def _on_error(self, msg):
        self._unlock_ui()
        self._reset_progress()
        self._set_status(f"오류: {msg}", self.ERROR)

    def _run_preprocess_only(self):
        """전처리만 수행 (DRM 환경용 2단계 모드)"""
        src = self.input_var.get()
        if not src or not os.path.isfile(src):
            self.status_var.set("파일을 찾을 수 없습니다.")
            self.status_label.config(fg=self.ERROR)
            return

        input_path = Path(src).resolve()
        default_name = f"{input_path.stem}_preprocessed.docx"

        save_path = filedialog.asksaveasfilename(
            title="전처리 결과 저장 위치",
            initialdir=str(input_path.parent),
            initialfile=default_name,
            defaultextension=".docx",
            filetypes=[("Word 문서", "*.docx")]
        )
        if not save_path:
            return

        # UI 잠금
        self.run_btn.config(state="disabled")
        self.preprocess_btn.config(state="disabled", text="전처리 중...")
        self.browse_btn.config(state="disabled")
        self.open_btn.config(state="disabled")
        self._set_status("장절번호 전처리 중...", self.FG_SUB)
        self._set_progress(0.3)
        self.root.update()

        def worker():
            try:
                from word_preprocessor import preprocess_only
                result_path = preprocess_only(str(input_path), save_path)

                if result_path:
                    self.root.after(0, lambda: self._on_preprocess_done(result_path))
                else:
                    self.root.after(0, lambda: self._on_error(
                        "전처리 실패. 로그를 확인하세요."))
            except Exception as e:
                self.root.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=worker, daemon=True).start()

    def _on_preprocess_done(self, result_path):
        self._unlock_ui()
        self._set_progress(1.0)
        self._set_status(
            f"전처리 완료: {Path(result_path).name}\n"
            f"DRM 해제 후 '변환' 버튼으로 HTML 변환하세요.",
            self.SUCCESS)
        self.open_btn.config(state="normal")

    def _unlock_ui(self):
        self.run_btn.config(state="normal", text="변환")
        self.preprocess_btn.config(state="normal", text="전처리만")
        self.browse_btn.config(state="normal")

    # ── 상태/진행률 ─────────────────────────────────────────────

    def _set_status(self, text, color):
        self.status_var.set(text)
        self.status_label.config(fg=color)

    def _set_progress(self, fraction):
        """0.0~1.0 비율로 프로그레스바 업데이트"""
        total_w = self.progress_frame.winfo_width()
        if total_w <= 1:
            total_w = 472  # 초기 추정치
        bar_w = max(0, int(total_w * fraction))
        self.progress_bar.place(x=0, y=0, width=bar_w, relheight=1)

    def _reset_progress(self):
        self.progress_bar.place(x=0, y=0, width=0, relheight=1)

    # ── 실행 ────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()
