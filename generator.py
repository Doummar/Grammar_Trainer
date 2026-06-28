# -*- coding: utf-8 -*-
import urllib.request
import json
import base64
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, showWarning

class GeminiWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, prompt, api_key, api_provider="gemini"):
        super().__init__()
        self.prompt = prompt
        self.api_key = api_key.strip() if api_key else ""
        self.api_provider = api_provider
        
    def run(self):
        import urllib.error
        import time
        
        # Response validation schema
        schema = {
            "type": "object",
            "properties": {
                "sentence": {"type": "string"},
                "language": {"type": "string"},
                "difficulty": {"type": "string"},
                "grammarType": {"type": "string"},
                "blanks": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "blankId": {"type": "string"},
                            "targetWord": {"type": "string"},
                            "options": {
                                "type": "array",
                                "items": {"type": "string"}
                            },
                            "hint": {"type": "string"},
                            "explanation": {"type": "string"}
                        },
                        "required": ["blankId", "targetWord", "options", "hint", "explanation"]
                    }
                }
            },
            "required": ["sentence", "language", "difficulty", "grammarType", "blanks"]
        }
        
        if self.api_provider == "gemini":
            # Configurations to try sequentially
            configs = [
                {"model": "gemini-2.5-flash", "version": "v1beta"},
                {"model": "gemini-2.0-flash", "version": "v1beta"},
                {"model": "gemini-1.5-flash", "version": "v1"},
                {"model": "gemini-1.5-flash", "version": "v1beta"},
                {"model": "gemini-1.5-pro", "version": "v1"},
                {"model": "gemini-1.5-pro", "version": "v1beta"}
            ]
            
            attempted_errors = []
            
            for config in configs:
                model = config["model"]
                version = config["version"]
                url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent?key={self.api_key}"
                
                payload = {
                    "contents": [{"parts": [{"text": self.prompt}]}],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "responseSchema": schema
                    }
                }
                
                err_msg = ""
                
                # Retry up to 3 times per config
                for attempt in range(3):
                    try:
                        req = urllib.request.Request(
                            url,
                            data=json.dumps(payload).encode("utf-8"),
                            headers={"Content-Type": "application/json"},
                            method="POST"
                        )
                        
                        with urllib.request.urlopen(req) as response:
                            res_data = json.loads(response.read().decode("utf-8"))
                            text_content = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                            
                            # Clean up markdown code blocks if the response contains them
                            if text_content.startswith("```"):
                                lines = text_content.splitlines()
                                if lines[0].startswith("```"):
                                    lines = lines[1:]
                                if lines and lines[-1].strip() == "```":
                                    lines = lines[:-1]
                                text_content = "\n".join(lines).strip()
                                
                            parsed = json.loads(text_content)
                            self.finished.emit(parsed)
                            return # Success!
                            
                    except urllib.error.HTTPError as e:
                        try:
                            error_body = e.read().decode("utf-8")
                            error_json = json.loads(error_body)
                            error_detail = error_json.get("error", {}).get("message", error_body)
                        except Exception:
                            error_detail = str(e)
                            
                        err_msg = f"{model} ({version}): {error_detail}"
                        
                        # If we get a 400 Bad Request, pop responseSchema and responseMimeType to fall back to plain text
                        if e.code == 400:
                            removed = False
                            if "responseSchema" in payload["generationConfig"]:
                                payload["generationConfig"].pop("responseSchema")
                                removed = True
                            elif "responseMimeType" in payload["generationConfig"]:
                                payload["generationConfig"].pop("responseMimeType")
                                removed = True
                            if removed:
                                time.sleep(0.5)
                                continue
                            
                        # If transient/quota limit, sleep and retry.
                        # Otherwise (like bad key or other 400s), abort this model/version immediately to try fallback.
                        if e.code in [429, 500, 503, 504]:
                            time.sleep(1.5 * (attempt + 1))
                            continue
                        else:
                            if err_msg not in attempted_errors:
                                attempted_errors.append(err_msg)
                            break # Try fallback
                            
                    except Exception as e:
                        err_msg = f"{model} ({version}): {str(e)}"
                        if err_msg not in attempted_errors:
                            attempted_errors.append(err_msg)
                        time.sleep(1)
                        continue
                else:
                    # Exhausted attempts for this model config without breaking out
                    if err_msg and err_msg not in attempted_errors:
                        attempted_errors.append(err_msg)
                        
            # All configurations failed
            combined_errors = "\n".join([f"- {err}" for err in attempted_errors])
            self.error.emit(combined_errors)
        else: # mistral
            models = ["mistral-large-latest", "mistral-small-latest", "open-mixtral-8x7b", "codestral-latest"]
            attempted_errors = []
            
            for model in models:
                url = "https://api.mistral.ai/v1/chat/completions"
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": self.prompt}
                    ],
                    "response_format": {"type": "json_object"}
                }
                err_msg = ""
                
                # Retry up to 3 times per model
                for attempt in range(3):
                    try:
                        req = urllib.request.Request(
                            url,
                            data=json.dumps(payload).encode("utf-8"),
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {self.api_key}"
                            },
                            method="POST"
                        )
                        
                        with urllib.request.urlopen(req) as response:
                            res_data = json.loads(response.read().decode("utf-8"))
                            text_content = res_data["choices"][0]["message"]["content"].strip()
                            
                            # Clean up markdown code blocks if the response contains them
                            if text_content.startswith("```"):
                                lines = text_content.splitlines()
                                if lines[0].startswith("```"):
                                    lines = lines[1:]
                                if lines and lines[-1].strip() == "```":
                                    lines = lines[:-1]
                                text_content = "\n".join(lines).strip()
                                
                            parsed = json.loads(text_content)
                            self.finished.emit(parsed)
                            return # Success!
                            
                    except urllib.error.HTTPError as e:
                        try:
                            error_body = e.read().decode("utf-8")
                            error_json = json.loads(error_body)
                            error_detail = error_json.get("message", error_body)
                        except Exception:
                            error_detail = str(e)
                            
                        err_msg = f"{model}: {error_detail}"
                        
                        # If transient/quota limit, sleep and retry.
                        if e.code in [429, 500, 503, 504]:
                            time.sleep(1.5 * (attempt + 1))
                            continue
                        else:
                            if err_msg not in attempted_errors:
                                attempted_errors.append(err_msg)
                            break # Try fallback
                            
                    except Exception as e:
                        err_msg = f"{model}: {str(e)}"
                        if err_msg not in attempted_errors:
                            attempted_errors.append(err_msg)
                        time.sleep(1)
                        continue
                else:
                    if err_msg and err_msg not in attempted_errors:
                        attempted_errors.append(err_msg)
                        
            combined_errors = "\n".join([f"- {err}" for err in attempted_errors])
            self.error.emit(combined_errors)

class OptionsWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)
    
    def __init__(self, prompt, api_key, api_provider="gemini"):
        super().__init__()
        self.prompt = prompt
        self.api_key = api_key.strip() if api_key else ""
        self.api_provider = api_provider
        
    def run(self):
        import urllib.error
        import time
        
        schema = {
            "type": "object",
            "properties": {
                "options": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["options"]
        }
        
        if self.api_provider == "gemini":
            configs = [
                {"model": "gemini-2.5-flash", "version": "v1beta"},
                {"model": "gemini-2.0-flash", "version": "v1beta"},
                {"model": "gemini-1.5-flash", "version": "v1"},
                {"model": "gemini-1.5-flash", "version": "v1beta"},
                {"model": "gemini-1.5-pro", "version": "v1"},
                {"model": "gemini-1.5-pro", "version": "v1beta"}
            ]
            
            attempted_errors = []
            for config in configs:
                model = config["model"]
                version = config["version"]
                url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent?key={self.api_key}"
                
                payload = {
                    "contents": [{"parts": [{"text": self.prompt}]}],
                    "generationConfig": {
                        "responseMimeType": "application/json",
                        "responseSchema": schema
                    }
                }
                
                err_msg = ""
                for attempt in range(3):
                    try:
                        req = urllib.request.Request(
                            url,
                            data=json.dumps(payload).encode("utf-8"),
                            headers={"Content-Type": "application/json"},
                            method="POST"
                        )
                        
                        with urllib.request.urlopen(req) as response:
                            res_data = json.loads(response.read().decode("utf-8"))
                            text_content = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                            
                            if text_content.startswith("```"):
                                lines = text_content.splitlines()
                                if lines[0].startswith("```"):
                                    lines = lines[1:]
                                if lines and lines[-1].strip() == "```":
                                    lines = lines[:-1]
                                text_content = "\n".join(lines).strip()
                                
                            parsed = json.loads(text_content)
                            options_list = []
                            if isinstance(parsed, list):
                                options_list = parsed
                            elif isinstance(parsed, dict):
                                options_list = parsed.get("options", [])
                                if not options_list:
                                    for key, val in parsed.items():
                                        if isinstance(val, list):
                                            options_list = val
                                            break
                            self.finished.emit(options_list)
                            return
                            
                    except urllib.error.HTTPError as e:
                        try:
                            error_body = e.read().decode("utf-8")
                            error_json = json.loads(error_body)
                            error_detail = error_json.get("error", {}).get("message", error_body)
                        except Exception:
                            error_detail = str(e)
                            
                        err_msg = f"{model} ({version}): {error_detail}"
                        
                        if e.code == 400:
                            removed = False
                            if "responseSchema" in payload["generationConfig"]:
                                payload["generationConfig"].pop("responseSchema")
                                removed = True
                            elif "responseMimeType" in payload["generationConfig"]:
                                payload["generationConfig"].pop("responseMimeType")
                                removed = True
                            if removed:
                                time.sleep(0.5)
                                continue
                                
                        if e.code in [429, 500, 503, 504]:
                            time.sleep(1.5 * (attempt + 1))
                            continue
                        else:
                            if err_msg not in attempted_errors:
                                attempted_errors.append(err_msg)
                            break
                            
                    except Exception as e:
                        err_msg = f"{model} ({version}): {str(e)}"
                        if err_msg not in attempted_errors:
                            attempted_errors.append(err_msg)
                        time.sleep(1)
                        continue
                else:
                    if err_msg and err_msg not in attempted_errors:
                        attempted_errors.append(err_msg)
            
            combined_errors = "\n".join([f"- {err}" for err in attempted_errors])
            self.error.emit(combined_errors)
        else: # mistral
            models = ["mistral-large-latest", "mistral-small-latest", "open-mixtral-8x7b", "codestral-latest"]
            attempted_errors = []
            
            for model in models:
                url = "https://api.mistral.ai/v1/chat/completions"
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "user", "content": self.prompt}
                    ],
                    "response_format": {"type": "json_object"}
                }
                err_msg = ""
                for attempt in range(3):
                    try:
                        req = urllib.request.Request(
                            url,
                            data=json.dumps(payload).encode("utf-8"),
                            headers={
                                "Content-Type": "application/json",
                                "Authorization": f"Bearer {self.api_key}"
                            },
                            method="POST"
                        )
                        
                        with urllib.request.urlopen(req) as response:
                            res_data = json.loads(response.read().decode("utf-8"))
                            text_content = res_data["choices"][0]["message"]["content"].strip()
                            
                            if text_content.startswith("```"):
                                lines = text_content.splitlines()
                                if lines[0].startswith("```"):
                                    lines = lines[1:]
                                if lines and lines[-1].strip() == "```":
                                    lines = lines[:-1]
                                text_content = "\n".join(lines).strip()
                                
                            parsed = json.loads(text_content)
                            options_list = []
                            if isinstance(parsed, list):
                                options_list = parsed
                            elif isinstance(parsed, dict):
                                options_list = parsed.get("options", [])
                                if not options_list:
                                    for key, val in parsed.items():
                                        if isinstance(val, list):
                                            options_list = val
                                            break
                            self.finished.emit(options_list)
                            return
                            
                    except urllib.error.HTTPError as e:
                        try:
                            error_body = e.read().decode("utf-8")
                            error_json = json.loads(error_body)
                            error_detail = error_json.get("message", error_body)
                        except Exception:
                            error_detail = str(e)
                            
                        err_msg = f"{model}: {error_detail}"
                        
                        if e.code in [429, 500, 503, 504]:
                            time.sleep(1.5 * (attempt + 1))
                            continue
                        else:
                            if err_msg not in attempted_errors:
                                attempted_errors.append(err_msg)
                            break
                            
                    except Exception as e:
                        err_msg = f"{model}: {str(e)}"
                        if err_msg not in attempted_errors:
                            attempted_errors.append(err_msg)
                        time.sleep(1)
                        continue
                else:
                    if err_msg and err_msg not in attempted_errors:
                        attempted_errors.append(err_msg)
                        
            combined_errors = "\n".join([f"- {err}" for err in attempted_errors])
            self.error.emit(combined_errors)

class GeneratorDialog(QDialog):
    def __init__(self, parent=None, editor=None):
        super().__init__(parent)
        self.editor = editor
        self.setWindowTitle("Grammar Trainer")
        self.resize(550, 540)
        self.checkboxes = []
        
        # Detect Anki theme (dark/night mode vs light mode)
        self.is_dark = False
        try:
            self.is_dark = mw.theme_manager.night_mode
        except Exception:
            try:
                self.is_dark = mw.pm.night_mode()
            except Exception:
                pass
        
        addon_name = __package__ or __name__.split('.')[0]
        self.config = mw.addonManager.getConfig(addon_name) or {}
        self.api_provider = self.config.get("api_provider", "gemini")
        self.api_key = self.config.get("api_key", "") if self.api_provider == "gemini" else self.config.get("mistral_api_key", "")
        
        self.init_ui()
        
    def accept(self):
        super().accept()
        if self.editor and getattr(self.editor, "parentWindow", None):
            self.editor.parentWindow.raise_()
            self.editor.parentWindow.activateWindow()

    def reject(self):
        super().reject()
        if self.editor and getattr(self.editor, "parentWindow", None):
            self.editor.parentWindow.raise_()
            self.editor.parentWindow.activateWindow()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Check API Key status
        if not self.api_key:
            provider_name = "Gemini" if self.api_provider == "gemini" else "Mistral"
            warning_lbl = QLabel(f"⚠️ {provider_name} API Key not found! Configure it in Tools -> Grammar Trainer Settings first.")
            if self.is_dark:
                warning_lbl.setStyleSheet("color: #fca5a5; font-weight: bold; padding: 4px; border: 1px solid #7f1d1d; border-radius: 4px; background-color: #310d0d;")
            else:
                warning_lbl.setStyleSheet("color: #b91c1c; font-weight: bold; padding: 4px; border: 1px solid #fca5a5; border-radius: 4px; background-color: #fef2f2;")
            warning_lbl.setWordWrap(True)
            layout.addWidget(warning_lbl)
            
        # Shared Config grid at top
        grid = QGridLayout()
        
        grid.addWidget(QLabel("Language:"), 0, 0)
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "Danish", "German", "Swedish", "Norwegian", "French", "Spanish", "Italian"])
        self.lang_combo.setCurrentText(self.config.get("default_language", "English"))
        grid.addWidget(self.lang_combo, 0, 1)
        
        grid.addWidget(QLabel("Difficulty:"), 0, 2)
        self.diff_combo = QComboBox()
        self.diff_combo.addItems(["A1", "A2", "B1", "B2", "C1", "C2"])
        self.diff_combo.setCurrentText(self.config.get("default_difficulty", "A1"))
        grid.addWidget(self.diff_combo, 0, 3)
        
        grid.addWidget(QLabel("Grammar Topic:"), 1, 0)
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "Verb Forms", "Noun Forms", "Adjective Forms", "Pronouns", "Articles", "Prepositions", "Adverbs",
            "Word Order", "Tense Selection", "Modal Verbs", "Conjunctions", "Question Formation", "Negation",
            "Passive Voice", "Relative Pronouns", "Fixed Expressions", "Sentence Connectors", "Word Choice", "Idioms"
        ])
        grid.addWidget(self.type_combo, 1, 1)
        
        grid.addWidget(QLabel("Distractors:"), 1, 2)
        self.dist_spin = QSpinBox()
        self.dist_spin.setRange(2, 7)
        self.dist_spin.setValue(self.config.get("default_distractors", 5))
        grid.addWidget(self.dist_spin, 1, 3)
        
        layout.addLayout(grid)

        # Tab Widget
        self.tabs = QTabWidget()
        
        # TAB 1: INSTANT GENERATOR
        self.tab_instant = QWidget()
        tab_instant_layout = QVBoxLayout()
        
        tab_instant_layout.addWidget(QLabel("Enter source sentence (Or leave completely empty for AI-generated sentences):"))
        self.sentence_input = QTextEdit()
        self.sentence_input.setPlaceholderText("e.g. Jeg accepterer, at det valgte sprog og niveau gælder til eksamen.")
        self.sentence_input.setFixedHeight(80)
        tab_instant_layout.addWidget(self.sentence_input)
        
        self.multi_blank_chk = QCheckBox("Generate two blanks in the sentence (Multi-cloze)")
        tab_instant_layout.addWidget(self.multi_blank_chk)
        
        self.tab_instant.setLayout(tab_instant_layout)
        self.tabs.addTab(self.tab_instant, "✨ Instant Generator")
        
        # TAB 2: SUGGEST & REFINE (TWO-STEP)
        self.tab_twostep = QWidget()
        tab_twostep_layout = QVBoxLayout()
        
        # Step 1 input
        tab_twostep_layout.addWidget(QLabel("Step 1: Enter word or sentence (e.g. 'at fyge' or 'sløj'):"))
        step1_lbl_layout = QHBoxLayout()
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("e.g. at fyge")
        self.suggest_btn = QPushButton("🔍 Suggest Options")
        self.suggest_btn.clicked.connect(self.start_suggest_options)
        self.suggest_btn.setStyleSheet("font-weight: bold; padding: 4px 10px;")
        if not self.api_key:
            self.suggest_btn.setEnabled(False)
            
        step1_lbl_layout.addWidget(self.word_input)
        step1_lbl_layout.addWidget(self.suggest_btn)
        tab_twostep_layout.addLayout(step1_lbl_layout)
        
        # Step 2 checkboxes
        tab_twostep_layout.addWidget(QLabel("Step 2: Choose / Refine Options to Include:"))
        self.options_scroll = QScrollArea()
        self.options_scroll.setWidgetResizable(True)
        self.options_scroll.setFixedHeight(110)
        self.options_scroll_widget = QWidget()
        self.options_scroll_layout = QVBoxLayout()
        self.options_scroll_layout.setContentsMargins(4, 4, 4, 4)
        self.options_scroll_layout.setSpacing(4)
        
        no_options_lbl = QLabel("No options suggested yet. Enter a word in Step 1.")
        no_options_lbl.setStyleSheet("color: #8e8e93; font-style: italic;")
        self.options_scroll_layout.addWidget(no_options_lbl)
        
        self.options_scroll_widget.setLayout(self.options_scroll_layout)
        self.options_scroll.setWidget(self.options_scroll_widget)
        tab_twostep_layout.addWidget(self.options_scroll)
        
        # Manual options list
        tab_twostep_layout.addWidget(QLabel("Final Options List (separated by |):"))
        self.final_options_input = QLineEdit()
        self.final_options_input.setPlaceholderText("e.g. fyge|fyg|fygede|fygende")
        self.final_options_input.textChanged.connect(self.on_final_options_changed)
        tab_twostep_layout.addWidget(self.final_options_input)
        
        # Step 3 input
        tab_twostep_layout.addWidget(QLabel("Step 3: Target Sentence (Optional):"))
        self.step3_sentence_input = QTextEdit()
        self.step3_sentence_input.setPlaceholderText("Leave blank to let AI create a natural sentence around your options.")
        self.step3_sentence_input.setFixedHeight(50)
        tab_twostep_layout.addWidget(self.step3_sentence_input)
        
        self.tab_twostep.setLayout(tab_twostep_layout)
        self.tabs.addTab(self.tab_twostep, "🔄 Suggest & Refine Options")
        
        layout.addWidget(self.tabs)
        
        # Status / Progress Indicators
        self.loading_lbl = QLabel("")
        if self.is_dark:
            self.loading_lbl.setStyleSheet("color: #9ca3af; font-style: italic;")
        else:
            self.loading_lbl.setStyleSheet("color: #4b5563; font-style: italic;")
        self.loading_lbl.setWordWrap(True)
        layout.addWidget(self.loading_lbl)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Interaction buttons
        btn_layout = QHBoxLayout()
        button_text = "✨ Generate and Insert into Card" if self.editor else "✨ Generate and Create Card"
        self.gen_btn = QPushButton(button_text)
        self.gen_btn.clicked.connect(self.start_generation)
        self.gen_btn.setStyleSheet("font-weight: bold; padding: 6px 14px;")
        if not self.api_key:
            self.gen_btn.setEnabled(False)
            
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("padding: 6px 14px;")
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.gen_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
    def start_suggest_options(self):
        source_text = self.word_input.text().strip()
        if not source_text:
            showWarning("Please enter a word or sentence in Step 1 first.")
            return
            
        language = self.lang_combo.currentText()
        difficulty = self.diff_combo.currentText()
        grammar_type = self.type_combo.currentText()
        
        user_prompt = f'Given the source word or sentence: "{source_text}"\nLanguage: {language}\nGrammar Focus: {grammar_type}\nTarget Difficulty: {difficulty}\n\nGenerate a list of 4 to 6 grammatically related options/words/inflections that are highly relevant to this source text, representing different grammatical forms (such as different noun cases, verb tenses, adjective inflections, or plurals) of the word, or related words that would fit in a typical drop-down cloze exercise.\n\nEnsure the output is a clean JSON array of strings containing the options. Include the base word itself as one of the options.'
        
        self.suggest_btn.setEnabled(False)
        self.gen_btn.setEnabled(False)
        self.loading_lbl.setText("Asking AI for option suggestions...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        self.options_worker = OptionsWorker(user_prompt, self.api_key, self.api_provider)
        self.options_worker.finished.connect(self.on_suggest_success)
        self.options_worker.error.connect(self.on_suggest_error)
        self.options_worker.start()
        
    def on_suggest_success(self, options):
        self.progress_bar.setVisible(False)
        self.suggest_btn.setEnabled(True)
        self.gen_btn.setEnabled(True)
        self.loading_lbl.setText("Suggestions loaded!")
        
        while self.options_scroll_layout.count():
            item = self.options_scroll_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
                
        self.checkboxes = []
        if not options:
            no_options_lbl = QLabel("No suggestions returned.")
            no_options_lbl.setStyleSheet("color: #8e8e93; font-style: italic;")
            self.options_scroll_layout.addWidget(no_options_lbl)
            self.final_options_input.setText("")
            return
            
        for opt in options:
            cb = QCheckBox(opt)
            cb.setChecked(True)
            cb.stateChanged.connect(self.update_final_options_from_checkboxes)
            self.options_scroll_layout.addWidget(cb)
            self.checkboxes.append(cb)
            
        self.update_final_options_from_checkboxes()
        
    def on_suggest_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.suggest_btn.setEnabled(True)
        self.gen_btn.setEnabled(True)
        self.loading_lbl.setText("")
        showWarning(f"Failed to suggest options:\n\n{error_msg}")
        
    def update_final_options_from_checkboxes(self):
        selected = []
        for cb in self.checkboxes:
            if cb.isChecked():
                selected.append(cb.text())
        self.final_options_input.blockSignals(True)
        self.final_options_input.setText("|".join(selected))
        self.final_options_input.blockSignals(False)
        
    def on_final_options_changed(self, text):
        opts = text.split("|")
        for cb in self.checkboxes:
            cb.blockSignals(True)
            cb.setChecked(cb.text() in opts)
            cb.blockSignals(False)

    def start_generation(self):
        active_tab = self.tabs.currentIndex()
        language = self.lang_combo.currentText()
        difficulty = self.diff_combo.currentText()
        grammar_type = self.type_combo.currentText()
        dist_count = self.dist_spin.value()
        
        if active_tab == 0:
            sentence = self.sentence_input.toPlainText().strip()
            multi_blank = self.multi_blank_chk.isChecked()
            
            # Prompt formulation
            prompt = f"Create a grammar dropdown cloze exercise. Language: {language}, Difficulty: {difficulty}, Grammar Category: {grammar_type}."
            if sentence:
                prompt += f" Create options and explanations based on the user sentence: '{sentence}'."
            else:
                prompt += f" Create a brand new sentence from scratch."
            
            prompt += f" Generate exactly {dist_count} smart distractors (total options: {dist_count + 1}) for each blank."
            if multi_blank:
                prompt += " Generate exactly two blanks, named blank1 and blank2."
            else:
                prompt += " Generate exactly one blank, named blank."
        else:
            sentence = self.step3_sentence_input.toPlainText().strip()
            options_str = self.final_options_input.text().strip()
            if not options_str:
                showWarning("Please suggest and select options in Tab 2 first before generating a card.")
                return
                
            prompt = f"Create a grammar dropdown cloze exercise. Language: {language}, Difficulty: {difficulty}, Grammar Category: {grammar_type}.\n\n"
            prompt += f"You MUST use the following word options for the cloze drop-down list: {options_str.replace('|', ', ')}.\n"
            if sentence:
                prompt += f"Generate the exercise based on this custom target sentence context: '{sentence}', replacing the target word with {{{{blank}}}}.\n"
            else:
                prompt += "Create a brand new natural sentence from scratch that uses one of the provided options as the correct answer, and the other options as dropdown distractors.\n"
            
            prompt += "Generate exactly one blank, named blank."
            
        prompt += "\n\nCRITICAL: You MUST respond with a raw JSON object matching the following structure. Do not wrap in markdown code blocks starting with three backticks and 'json'.\n"
        prompt += "{\n"
        prompt += '  "sentence": "The complete sentence containing the blank placeholder(s) like {{blank}} or {{blank1}} and {{blank2}}.",\n'
        prompt += f'  "language": "{language}",\n'
        prompt += f'  "difficulty": "{difficulty}",\n'
        prompt += f'  "grammarType": "{grammar_type}",\n'
        prompt += '  "blanks": [\n'
        prompt += '    {\n'
        if active_tab == 0 and multi_blank:
            prompt += '      "blankId": "blank1" or "blank2",\n'
        else:
            prompt += '      "blankId": "blank",\n'
        prompt += '      "targetWord": "the correct answer for this blank",\n'
        prompt += '      "options": ["the targetWord", "distractor1", "distractor2", ...],\n'
        prompt += '      "hint": "a short hint for this blank",\n'
        prompt += '      "explanation": "why targetWord is correct and distractors are wrong"\n'
        prompt += '    }\n'
        prompt += '  ]\n'
        prompt += '}'
            
        self.gen_btn.setEnabled(False)
        provider_name = "Gemini" if self.api_provider == "gemini" else "Mistral"
        self.loading_lbl.setText(f"Connecting to {provider_name} API... Analyzing grammar structures and drafting realistic distractors...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0) # Pulse mode
        
        # Launch Worker Thread
        self.worker = GeminiWorker(prompt, self.api_key, self.api_provider)
        self.worker.finished.connect(self.on_generation_success)
        self.worker.error.connect(self.on_generation_error)
        self.worker.start()
        
    def on_generation_success(self, data):
        self.progress_bar.setVisible(False)
        self.loading_lbl.setText("Success! Card parsed. Saving...")
        
        try:
            import re
            sentence = data.get("sentence", "")
            sentence = re.sub(r'[{]+blank(d*)[}]+', lambda m: '{{blank' + m.group(1) + '}}', sentence)
            
            blanks = data.get("blanks", [])
            if len(blanks) == 1:
                b = blanks[0]
                target_word = b.get("targetWord", "")
                options_str = "|".join(b.get("options", []))
                explanation = b.get("explanation", "")
            else:
                targets = []
                options_group = []
                explanations = []
                for b in blanks:
                    targets.append(b.get("targetWord", ""))
                    options_group.append("|".join(b.get("options", [])))
                    explanations.append(f"<strong>Blank '{b.get('blankId')}':</strong> {b.get('explanation')}")
                    
                target_word = " || ".join(targets)
                options_str = " || ".join(options_group)
                explanation = "<br><br>".join(explanations)
                
            grammar_type = data.get("grammarType", self.type_combo.currentText())
            difficulty = data.get("difficulty", self.diff_combo.currentText())
            language = data.get("language", self.lang_combo.currentText())
            
            if self.editor:
                # Update current note fields directly in the active editor
                note = self.editor.note
                fields_set = []
                for field, val in [
                    ("Sentence", sentence),
                    ("TargetWord", target_word),
                    ("Options", options_str),
                    ("Explanation", explanation),
                    ("GrammarType", grammar_type),
                    ("Difficulty", difficulty),
                    ("Language", language),
                    ("FrontAudio", ""),
                    ("BackAudio", "")
                ]:
                    if field in note:
                        note[field] = val
                        fields_set.append(field)
                
                # Reload active editor representation to update GUI fields
                self.editor.loadNote()
                
                if fields_set:
                    showInfo(f"✨ Grammar Trainer card populated successfully!\n\nFields updated: {', '.join(fields_set)}")
                else:
                    showInfo("⚠️ Grammar Trainer card generated successfully!\n\nNote: The current note type does not have the expected fields (Sentence, TargetWord, etc.) so they could not be filled automatically.")
                
                self.accept()
                
            else:
                col = mw.col
                note_type = col.models.by_name("Grammar Trainer")
                if not note_type:
                    from .note_type import setup_note_type
                    note_type = setup_note_type()
                    
                note = col.new_note(note_type)
                note["Sentence"] = sentence
                note["TargetWord"] = target_word
                note["Options"] = options_str
                note["Explanation"] = explanation
                note["GrammarType"] = grammar_type
                note["Difficulty"] = difficulty
                note["Language"] = language
                note["FrontAudio"] = ""
                note["BackAudio"] = ""
                
                # Add to active deck
                deck_id = mw.col.decks.active()
                if isinstance(deck_id, list):
                    deck_id = deck_id[0] if deck_id else 1
                note.model()["did"] = deck_id
                mw.col.add_note(note, deck_id)
                
                # Reset and show feedback
                mw.reset()
                showInfo("✨ Grammar Trainer card created successfully!")
                self.accept()
                
        except Exception as e:
            showWarning(f"Database write error: {str(e)}")
            self.gen_btn.setEnabled(True)
            self.loading_lbl.setText("")
            
    def on_generation_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.gen_btn.setEnabled(True)
        self.loading_lbl.setText("")
        showWarning(f"Gemini API failure:\n\n{error_msg}\n\nPlease verify your API key in Settings or try again.")

def show_generator_dialog(editor=None):
    from aqt.editor import Editor
    if not isinstance(editor, Editor):
        editor = None
    dialog = GeneratorDialog(mw, editor=editor)
    dialog.exec()
