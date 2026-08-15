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
        import ssl
        
        try:
            ssl_context = ssl._create_unverified_context()
        except Exception:
            ssl_context = None
        
        # Response validation schema
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "sentence": {"type": "string"},
                "language": {"type": "string"},
                "difficulty": {"type": "string"},
                "grammarType": {"type": "string"},
                "cefrReason": {"type": "string"},
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
                            "explanation": {"type": "string"},
                            "lemma": {"type": "string"},
                            "partOfSpeech": {"type": "string"},
                            "grammarPoint": {"type": "string"},
                            "commonMistake": {"type": "string"},
                            "memoryTip": {"type": "string"},
                            "frequency": {"type": "string"},
                            "register": {"type": "string"},
                            "collocations": {
                                "type": "array",
                                "items": {"type": "string"}
                            }
                        },
                        "required": ["blankId", "targetWord", "options", "hint", "explanation", "lemma", "partOfSpeech", "grammarPoint", "commonMistake", "memoryTip", "frequency", "register", "collocations"]
                    }
                }
            },
            "required": ["status", "sentence", "language", "difficulty", "grammarType", "cefrReason", "blanks"]
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
                        
                        with urllib.request.urlopen(req, timeout=15, context=ssl_context) as response:
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
                        
                        with urllib.request.urlopen(req, timeout=15, context=ssl_context) as response:
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
        import ssl
        
        try:
            ssl_context = ssl._create_unverified_context()
        except Exception:
            ssl_context = None
            
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
                        
                        with urllib.request.urlopen(req, timeout=15, context=ssl_context) as response:
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
                        
                        with urllib.request.urlopen(req, timeout=15, context=ssl_context) as response:
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
        self.resize(550, 600)
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
            warning_lbl = QLabel(f"Warning: {provider_name} API Key not found! Configure it in Tools -> Grammar Trainer, or use the Manual Entry tab, which doesn't need one.")
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
        self.tabs.addTab(self.tab_instant, "Instant Generator")
        
        # TAB 2: SUGGEST & REFINE (TWO-STEP)
        self.tab_twostep = QWidget()
        tab_twostep_layout = QVBoxLayout()
        
        # Step 1 input
        tab_twostep_layout.addWidget(QLabel("Step 1: Enter word or sentence (e.g. 'at fyge' or 'sløj'):"))
        step1_lbl_layout = QHBoxLayout()
        self.word_input = QLineEdit()
        self.word_input.setPlaceholderText("e.g. at fyge")
        self.suggest_btn = QPushButton("Suggest Options")
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
        self.tabs.addTab(self.tab_twostep, "Suggest & Refine Options")
        
        # TAB 3: MANUAL ENTRY (no AI / no API key needed)
        self.tab_manual = QWidget()
        tab_manual_outer_layout = QVBoxLayout()
        tab_manual_outer_layout.setContentsMargins(0, 0, 0, 0)
        
        manual_scroll = QScrollArea()
        manual_scroll.setWidgetResizable(True)
        manual_scroll.setFrameShape(QFrame.Shape.NoFrame)
        manual_scroll_content = QWidget()
        tab_manual_layout = QVBoxLayout()
        
        tab_manual_layout.addWidget(QLabel("Sentence — type ___ (three or more underscores) where each blank goes:"))
        self.manual_sentence_input = QTextEdit()
        self.manual_sentence_input.setPlaceholderText("e.g. Hun blev meget ___ over den uretfærdige behandling.")
        self.manual_sentence_input.setFixedHeight(60)
        tab_manual_layout.addWidget(self.manual_sentence_input)
        
        self.manual_multi_blank_chk = QCheckBox("This sentence has two blanks (use ___ twice)")
        self.manual_multi_blank_chk.stateChanged.connect(self.on_manual_multi_blank_toggled)
        tab_manual_layout.addWidget(self.manual_multi_blank_chk)
        
        self.manual_blank1_group = QGroupBox("Blank 1")
        blank1_form = QFormLayout()
        self.manual_answer1_input = QLineEdit()
        self.manual_answer1_input.setPlaceholderText("e.g. forarget")
        blank1_form.addRow("Correct answer:", self.manual_answer1_input)
        self.manual_distractors1_input = QLineEdit()
        self.manual_distractors1_input.setPlaceholderText("e.g. forarg, forarger, forargede")
        blank1_form.addRow("Wrong options (comma separated):", self.manual_distractors1_input)
        self.manual_correct_expl1_input = QLineEdit()
        self.manual_correct_expl1_input.setPlaceholderText("Optional — shown when the correct answer is picked")
        blank1_form.addRow("Why it's correct (optional):", self.manual_correct_expl1_input)
        self.manual_incorrect_expl1_input = QLineEdit()
        self.manual_incorrect_expl1_input.setPlaceholderText("Optional — shown when any wrong option is picked")
        blank1_form.addRow("Why others are wrong (optional):", self.manual_incorrect_expl1_input)
        self.manual_blank1_group.setLayout(blank1_form)
        tab_manual_layout.addWidget(self.manual_blank1_group)
        
        self.manual_blank2_group = QGroupBox("Blank 2")
        blank2_form = QFormLayout()
        self.manual_answer2_input = QLineEdit()
        self.manual_answer2_input.setPlaceholderText("e.g. lærte")
        blank2_form.addRow("Correct answer:", self.manual_answer2_input)
        self.manual_distractors2_input = QLineEdit()
        self.manual_distractors2_input.setPlaceholderText("e.g. lærer, lære, lærende")
        blank2_form.addRow("Wrong options (comma separated):", self.manual_distractors2_input)
        self.manual_correct_expl2_input = QLineEdit()
        self.manual_correct_expl2_input.setPlaceholderText("Optional — shown when the correct answer is picked")
        blank2_form.addRow("Why it's correct (optional):", self.manual_correct_expl2_input)
        self.manual_incorrect_expl2_input = QLineEdit()
        self.manual_incorrect_expl2_input.setPlaceholderText("Optional — shown when any wrong option is picked")
        blank2_form.addRow("Why others are wrong (optional):", self.manual_incorrect_expl2_input)
        self.manual_blank2_group.setLayout(blank2_form)
        self.manual_blank2_group.setVisible(False)
        tab_manual_layout.addWidget(self.manual_blank2_group)
        
        tab_manual_layout.addStretch()
        manual_scroll_content.setLayout(tab_manual_layout)
        manual_scroll.setWidget(manual_scroll_content)
        tab_manual_outer_layout.addWidget(manual_scroll)
        self.tab_manual.setLayout(tab_manual_outer_layout)
        self.tabs.addTab(self.tab_manual, "Manual Entry")
        
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
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
        self._ai_btn_text = "Generate and Insert into Card" if self.editor else "Generate and Create Card"
        self._manual_btn_text = "Insert into Card" if self.editor else "Create Card"
        self.gen_btn = QPushButton(self._ai_btn_text)
        self.gen_btn.clicked.connect(self.start_generation)
        self.gen_btn.setStyleSheet("font-weight: bold; padding: 6px 14px;")
        if not self.api_key:
            self.gen_btn.setEnabled(False)
            
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_active_workers)
        self.stop_btn.setStyleSheet("padding: 6px 14px;")
            
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet("padding: 6px 14px;")
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.gen_btn)
        btn_layout.addWidget(self.stop_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
    def stop_active_workers(self):
        # Stop worker if running
        if hasattr(self, "worker") and self.worker and self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self.worker = None
        # Stop options worker if running
        if hasattr(self, "options_worker") and self.options_worker and self.options_worker.isRunning():
            self.options_worker.terminate()
            self.options_worker.wait()
            self.options_worker = None
            
        self.progress_bar.setVisible(False)
        self.gen_btn.setEnabled(True if self.api_key else False)
        self.suggest_btn.setEnabled(True if self.api_key else False)
        self.stop_btn.setEnabled(False)
        self.loading_lbl.setText("Generation stopped by user.")
        
    def on_tab_changed(self, index):
        if index == 2:
            # Manual Entry tab: no AI call involved, so no API key is needed
            self.gen_btn.setText(self._manual_btn_text)
            self.gen_btn.setEnabled(True)
        else:
            self.gen_btn.setText(self._ai_btn_text)
            self.gen_btn.setEnabled(True if self.api_key else False)
            
    def on_manual_multi_blank_toggled(self, state):
        self.manual_blank2_group.setVisible(self.manual_multi_blank_chk.isChecked())
        
    def start_suggest_options(self):
        source_text = self.word_input.text().strip()
        if not source_text:
            showWarning("Please enter a word or sentence in Step 1 first.")
            return
            
        language = self.lang_combo.currentText()
        difficulty = self.diff_combo.currentText()
        grammar_type = self.type_combo.currentText()
        
        user_prompt = f'Given the source word or sentence: "{source_text}"\nLanguage: {language}\nGrammar Focus: {grammar_type}\nTarget Difficulty: {difficulty}\n\nFollow these strict steps before suggesting options:\nSTEP 1: Determine the exact lemma of the target word in the context of the sentence (if a sentence is provided). Use context to eliminate alternative lemmas.\nSTEP 2: Validate that the meaning of the lemma fits perfectly. Reject any lemma whose meaning does not match.\nSTEP 3: Generate a list of 4 to 6 grammatically related inflections/forms. All suggested options MUST belong to the EXACT SAME dictionary lemma as the target word. Do not include options with a different dictionary lemma even if they share a spelling or root. No derivationally, phonetically, or semantically related words of a different lemma.\nDanish example: "tage", "tog", "taget", "tager" are ALLOWED (same lemma "tage"). "tiltage", "modtage", "foretage" are FORBIDDEN (different lemmas).\nEnglish example: "take", "takes", "taking", "took", "taken" are ALLOWED (same lemma "take"). "take", "undertake", "mistake" are FORBIDDEN (different lemmas).\n\nEnsure the output is a clean JSON array of strings containing the options. Include the base word itself as one of the options.'
        
        self.suggest_btn.setEnabled(False)
        self.gen_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
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
        self.stop_btn.setEnabled(False)
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
        self.stop_btn.setEnabled(False)
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
        
        if active_tab == 2:
            self.create_manual_card()
            return
        
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
            
        prompt += (
            "\n\nCRITICAL QUALITY ASSURANCE AND DISAMBIGUATION WORKFLOW:\n"
            "You MUST perform the following 3 steps sequentially before returning the exercise. If you fail to do so, the card will be rejected.\n\n"
            "STEP 1: Lexical Disambiguation\n"
            "- Determine the exact dictionary lemma of the target word.\n"
            "- Use the surrounding sentence context to eliminate all alternative lemmas.\n"
            "- If multiple lemmas share the same surface form, choose the only one that makes semantic and grammatical sense.\n"
            "- Never generate an exercise until the lemma has been uniquely and confidently identified.\n"
            "- CRITICAL RULE: If there is ANY uncertainty or ambiguity about the correct lemma, STOP IMMEDIATELY! Do not guess. You must return {\"status\": \"ambiguous\", \"sentence\": \"\", \"language\": \"\", \"difficulty\": \"\", \"grammarType\": \"\", \"blanks\": []} instead of generating an exercise. We prefer no card over an incorrect card.\n\n"
            "STEP 2: Semantic Validation\n"
            "- After identifying the lemma, validate that the meaning of the lemma fits perfectly in the sentence.\n"
            "- For example: For Danish sentence 'Han tog en pause.', the correct lemma is 'tage'. You must reject other lemmas whose meanings do not fit the sentence (like 'tiltage', 'foretage', 'modtage').\n"
            "- Reject any lemma whose meaning does not fit the sentence. Validate by meaning, not spelling.\n\n"
            "STEP 3: Distractor Validation\n"
            "- Before returning the distractors, verify each distractor against these 5 rules:\n"
            "  1. Is it the same lemma? (All distractors MUST belong to the EXACT SAME dictionary lemma! Not merely a similar spelling, same root, derivationally related, phonetically related, or semantically related. Exactly the same dictionary lemma! No exceptions.)\n"
            "  2. Is it the same lexical family?\n"
            "  3. Is it a real word?\n"
            "  4. Does it fit the intended grammar exercise?\n"
            "  5. Is it NOT a different dictionary entry?\n"
            "- If the answer to any of these 5 rules is 'No', you MUST discard that distractor and choose/generate a valid one.\n"
            "- All distractors MUST belong to the EXACT SAME dictionary lemma.\n"
            "  - Danish Example: 'tage', 'tog', 'taget', 'tager' are ALLOWED (all belong to lemma 'tage'). 'tiltage', 'foretage', 'modtage' are FORBIDDEN (different lemmas).\n"
            "  - English Example: 'take', 'takes', 'taking', 'took', 'taken' are ALLOWED (all belong to lemma 'take'). 'take', 'undertake', 'mistake' are FORBIDDEN (different lemmas).\n"
        )
            
        prompt += "\n\nCRITICAL: You MUST respond with a raw JSON object matching the following structure. Do not wrap in markdown code blocks starting with three backticks and 'json'.\n"
        prompt += "{\n"
        prompt += '  "status": "ok" or "ambiguous" (set to "ambiguous" if you had to stop in STEP 1 due to lemma ambiguity or uncertainty, otherwise "ok"),\n'
        prompt += '  "sentence": "The complete sentence containing the blank placeholder(s) like {{blank}} or {{blank1}} and {{blank2}}.",\n'
        prompt += f'  "language": "{language}",\n'
        prompt += f'  "difficulty": "{difficulty}",\n'
        prompt += f'  "grammarType": "{grammar_type}",\n'
        prompt += '  "cefrReason": "A short 1-2 sentence explanation of why this exercise matches the requested CEFR difficulty level.",\n'
        prompt += '  "blanks": [\n'
        prompt += '    {\n'
        if active_tab == 0 and multi_blank:
            prompt += '      "blankId": "blank1" or "blank2",\n'
        else:
            prompt += '      "blankId": "blank",\n'
        prompt += '      "targetWord": "the correct answer for this blank",\n'
        prompt += '      "options": ["the targetWord", "distractor1", "distractor2", ...],\n'
        prompt += '      "hint": "a short hint for this blank",\n'
        prompt += f'      "explanation": "A serialized JSON string mapping each option in options to its specific explanation in the target language being studied ({language}). Example: \\"{{\\"option1\\": \\"explanation1\\", \\"option2\\": \\"explanation2\\"}}\\"",\n'
        prompt += '      "lemma": "the dictionary base form (lemma) of the target word",\n'
        prompt += '      "partOfSpeech": "the part of speech of the target word (e.g. verb, noun, adjective)",\n'
        prompt += '      "grammarPoint": "a short, specific label for the exact grammar rule being tested (more specific than grammarType)",\n'
        prompt += '      "commonMistake": "a brief note on a common mistake learners make with this word or grammar point",\n'
        prompt += '      "memoryTip": "a short memory hook or mnemonic to help remember the correct form",\n'
        prompt += '      "frequency": "how common this word/form is in everyday use (e.g. very common, common, rare)",\n'
        prompt += '      "register": "the formality register of the target word (e.g. formal, informal, neutral)",\n'
        prompt += '      "collocations": ["2-4 short common word pairings or phrases that use the target word naturally"]\n'
        prompt += '    }\n'
        prompt += '  ]\n'
        prompt += '}'
            
        self.gen_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        provider_name = "Gemini" if self.api_provider == "gemini" else "Mistral"
        self.loading_lbl.setText(f"Connecting to {provider_name} API... Analyzing grammar structures and drafting realistic distractors...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0) # Pulse mode
        
        # Launch Worker Thread
        self.worker = GeminiWorker(prompt, self.api_key, self.api_provider)
        self.worker.finished.connect(self.on_generation_success)
        self.worker.error.connect(self.on_generation_error)
        self.worker.start()
        
    def create_manual_card(self):
        import re
        
        sentence_raw = self.manual_sentence_input.toPlainText().strip()
        multi_blank = self.manual_multi_blank_chk.isChecked()
        
        if not sentence_raw:
            showWarning("Please enter a sentence.")
            return
        
        blank_count = len(re.findall(r'_{3,}', sentence_raw))
        expected = 2 if multi_blank else 1
        if blank_count != expected:
            if multi_blank:
                showWarning(f"'Two blanks' is checked, so the sentence needs exactly two ___ markers (found {blank_count}).")
            else:
                showWarning(f"The sentence needs exactly one ___ marker (found {blank_count}). Check 'This sentence has two blanks' if you want a double blank.")
            return
        
        def build_blank(answer_input, distractors_input, correct_expl_input, incorrect_expl_input, label):
            answer = answer_input.text().strip()
            if not answer:
                showWarning(f"Please enter the correct answer for {label}.")
                return None
            distractors = [d.strip() for d in distractors_input.text().split(",") if d.strip()]
            if not distractors:
                showWarning(f"Please add at least one wrong option (distractor) for {label}, separated by commas.")
                return None
            
            seen = set()
            all_options = []
            for opt in [answer] + distractors:
                key = opt.strip().lower()
                if key and key not in seen:
                    seen.add(key)
                    all_options.append(opt.strip())
            
            correct_expl = correct_expl_input.text().strip()
            incorrect_expl = incorrect_expl_input.text().strip()
            expl_data = {}
            for opt in all_options:
                expl_data[opt] = correct_expl if opt.lower() == answer.lower() else incorrect_expl
            
            return {
                "target": answer,
                "options_str": "|".join(all_options),
                "explanation": json.dumps(expl_data, ensure_ascii=False),
            }
        
        blank1 = build_blank(self.manual_answer1_input, self.manual_distractors1_input,
                              self.manual_correct_expl1_input, self.manual_incorrect_expl1_input, "Blank 1")
        if blank1 is None:
            return
        
        if not multi_blank:
            sentence = re.sub(r'_{3,}', '{{blank}}', sentence_raw, count=1)
            target_word = blank1["target"]
            options_str = blank1["options_str"]
            explanation = blank1["explanation"]
        else:
            blank2 = build_blank(self.manual_answer2_input, self.manual_distractors2_input,
                                  self.manual_correct_expl2_input, self.manual_incorrect_expl2_input, "Blank 2")
            if blank2 is None:
                return
            
            counter = [0]
            def repl(m):
                counter[0] += 1
                return "{{blank" + str(counter[0]) + "}}"
            sentence = re.sub(r'_{3,}', repl, sentence_raw, count=2)
            
            target_word = blank1["target"] + " || " + blank2["target"]
            options_str = blank1["options_str"] + " || " + blank2["options_str"]
            explanation = (f"<strong>Blank 'blank1':</strong> {blank1['explanation']}"
                            f"<br><br><strong>Blank 'blank2':</strong> {blank2['explanation']}")
        
        grammar_type = self.type_combo.currentText()
        difficulty = self.diff_combo.currentText()
        language = self.lang_combo.currentText()
        
        try:
            self.save_generated_card(sentence, target_word, options_str, explanation, grammar_type, difficulty, language, "")
        except Exception as e:
            showWarning(f"Database write error: {str(e)}")
        
    def on_generation_success(self, data):
        self.progress_bar.setVisible(False)
        self.stop_btn.setEnabled(False)
        self.loading_lbl.setText("Success! Card parsed. Saving...")
        
        try:
            status = data.get("status", "")
            if status == "ambiguous":
                self.loading_lbl.setText("Generation stopped: Lemma is ambiguous.")
                showWarning("The target word lemma is ambiguous in this context or could not be uniquely identified.\n\nGeneration stopped to prevent creating an incorrect card as requested.")
                self.gen_btn.setEnabled(True)
                return
                
            import re
            sentence = data.get("sentence", "")
            sentence = re.sub(r'[{]+blank(\d*)[}]+', lambda m: '{{blank' + m.group(1) + '}}', sentence)
            
            blanks = data.get("blanks", [])
            cefr_reason = data.get("cefrReason", "")
            if len(blanks) == 1:
                b = blanks[0]
                target_word = b.get("targetWord", "")
                options_str = "|".join(b.get("options", []))
                
                # Merge SLA fields into the JSON explanation string
                raw_expl = b.get("explanation", "{}")
                try:
                    import json
                    expl_data = json.loads(raw_expl)
                except Exception:
                    expl_data = {}
                
                expl_data["_lemma"] = b.get("lemma", "")
                expl_data["_partOfSpeech"] = b.get("partOfSpeech", "")
                expl_data["_grammarPoint"] = b.get("grammarPoint", "")
                expl_data["_commonMistake"] = b.get("commonMistake", "")
                expl_data["_memoryTip"] = b.get("memoryTip", "")
                expl_data["_frequency"] = b.get("frequency", "")
                expl_data["_register"] = b.get("register", "")
                expl_data["_collocations"] = b.get("collocations", [])
                expl_data["_cefrReason"] = cefr_reason
                
                explanation = json.dumps(expl_data, ensure_ascii=False)
            else:
                targets = []
                options_group = []
                explanations = []
                import json
                for b in blanks:
                    targets.append(b.get("targetWord", ""))
                    options_group.append("|".join(b.get("options", [])))
                    
                    # Merge SLA fields into the JSON explanation string for this blank
                    raw_expl = b.get("explanation", "{}")
                    try:
                        expl_data = json.loads(raw_expl)
                    except Exception:
                        expl_data = {}
                        
                    expl_data["_lemma"] = b.get("lemma", "")
                    expl_data["_partOfSpeech"] = b.get("partOfSpeech", "")
                    expl_data["_grammarPoint"] = b.get("grammarPoint", "")
                    expl_data["_commonMistake"] = b.get("commonMistake", "")
                    expl_data["_memoryTip"] = b.get("memoryTip", "")
                    expl_data["_frequency"] = b.get("frequency", "")
                    expl_data["_register"] = b.get("register", "")
                    expl_data["_collocations"] = b.get("collocations", [])
                    expl_data["_cefrReason"] = cefr_reason
                    
                    merged_expl_str = json.dumps(expl_data, ensure_ascii=False)
                    explanations.append(f"<strong>Blank '{b.get('blankId')}':</strong> {merged_expl_str}")
                    
                target_word = " || ".join(targets)
                options_str = " || ".join(options_group)
                explanation = "<br><br>".join(explanations)
                
            grammar_type = data.get("grammarType", self.type_combo.currentText())
            difficulty = data.get("difficulty", self.diff_combo.currentText())
            language = data.get("language", self.lang_combo.currentText())
            image_url = data.get("image", "")
            image_html = f'<img src="{image_url}">' if image_url else ""
            
            self.save_generated_card(sentence, target_word, options_str, explanation, grammar_type, difficulty, language, image_html)
                
        except Exception as e:
            showWarning(f"Database write error: {str(e)}")
            self.gen_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.loading_lbl.setText("")
            
    def save_generated_card(self, sentence, target_word, options_str, explanation, grammar_type, difficulty, language, image_html=""):
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
                ("BackAudio", ""),
                ("Image", image_html)
            ]:
                if field in note:
                    note[field] = val
                    fields_set.append(field)
            
            # Reload active editor representation to update GUI fields
            self.editor.loadNote()
            
            if fields_set:
                showInfo(f"Grammar Trainer card populated successfully!\n\nFields updated: {', '.join(fields_set)}")
            else:
                showInfo("Grammar Trainer card generated successfully!\n\nNote: The current note type does not have the expected fields (Sentence, TargetWord, etc.) so they could not be filled automatically.")
            
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
            if "Image" in note:
                note["Image"] = image_html
            
            # Add to active deck
            deck_id = mw.col.decks.active()
            if isinstance(deck_id, list):
                deck_id = deck_id[0] if deck_id else 1
            note.model()["did"] = deck_id
            mw.col.add_note(note, deck_id)
            
            # Reset and show feedback
            mw.reset()
            showInfo("Grammar Trainer card created successfully!")
            self.accept()
            
    def on_generation_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.gen_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.loading_lbl.setText("")
        showWarning(f"Gemini API failure:\n\n{error_msg}\n\nPlease verify your API key in Settings or try again.")

def show_generator_dialog(editor=None):
    from aqt.editor import Editor
    if not isinstance(editor, Editor):
        editor = None
    dialog = GeneratorDialog(mw, editor=editor)
    dialog.exec()
