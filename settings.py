# -*- coding: utf-8 -*-
import os
from aqt import mw
from aqt.qt import *

class ConnectionTester(QThread):
    finished = pyqtSignal(bool, str) # success, message
    
    def __init__(self, api_key, provider):
        super().__init__()
        self.api_key = api_key.strip()
        self.provider = provider
        
    def run(self):
        import urllib.request
        import urllib.error
        import json
        import time
        
        if not self.api_key:
            self.finished.emit(False, "API Key is empty. Please enter an API key.")
            return
            
        if self.provider == "gemini":
            configs = [
                {"model": "gemini-2.5-flash", "version": "v1beta"},
                {"model": "gemini-2.0-flash", "version": "v1beta"},
                {"model": "gemini-1.5-flash", "version": "v1"},
                {"model": "gemini-1.5-flash", "version": "v1beta"},
            ]
            errors = []
            
            for config in configs:
                model = config["model"]
                version = config["version"]
                url = f"https://generativelanguage.googleapis.com/{version}/models/{model}:generateContent?key={self.api_key}"
                payload = {
                    "contents": [{"parts": [{"text": "Hello"}]}],
                    "generationConfig": {
                        "maxOutputTokens": 5
                    }
                }
                try:
                    req = urllib.request.Request(
                        url,
                        data=json.dumps(payload).encode("utf-8"),
                        headers={"Content-Type": "application/json"},
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=8) as response:
                        res_data = json.loads(response.read().decode("utf-8"))
                        if "candidates" in res_data and len(res_data["candidates"]) > 0:
                            self.finished.emit(True, f"Successfully connected using model: {model} ({version})!")
                            return
                except urllib.error.HTTPError as e:
                    try:
                        error_body = e.read().decode("utf-8")
                        error_json = json.loads(error_body)
                        error_detail = error_json.get("error", {}).get("message", error_body)
                    except Exception:
                        error_detail = str(e)
                    errors.append(f"{model} ({version}): {error_detail} (HTTP {e.code})")
                except Exception as e:
                    errors.append(f"{model} ({version}): {str(e)}")
                    
            combined = "\n".join([f"- {err}" for err in errors])
            self.finished.emit(False, combined)
        else: # mistral
            url = "https://api.mistral.ai/v1/chat/completions"
            payload = {
                "model": "mistral-small-latest",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 5
            }
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
                with urllib.request.urlopen(req, timeout=8) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    if "choices" in res_data and len(res_data["choices"]) > 0:
                        self.finished.emit(True, "Successfully connected to Mistral AI!")
                        return
            except urllib.error.HTTPError as e:
                try:
                    error_body = e.read().decode("utf-8")
                    error_json = json.loads(error_body)
                    error_detail = error_json.get("message", error_body)
                except Exception:
                    error_detail = str(e)
                self.finished.emit(False, f"Mistral API Error (HTTP {e.code}): {error_detail}")
            except Exception as e:
                self.finished.emit(False, f"Connection Error: {str(e)}")

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Grammar Trainer Settings")
        self.resize(560, 520)
        
        # Detect Anki theme (dark/night mode vs light mode)
        self.is_dark = False
        try:
            self.is_dark = mw.theme_manager.night_mode
        except Exception:
            try:
                self.is_dark = mw.pm.night_mode()
            except Exception:
                pass
        
        # Load existing configuration
        addon_name = __package__ or __name__.split('.')[0]
        self.config = mw.addonManager.getConfig(addon_name) or {}
        
        self.init_ui()
        
    def init_ui(self):
        # Determine stylesheets based on theme
        if self.is_dark:
            btn_style = "QPushButton { padding: 6px 12px; }"
            cancel_btn_style = "QPushButton { padding: 6px 18px; }"
            save_btn_style = "QPushButton { padding: 6px 20px; font-weight: bold; }"
            note_style = "font-size: 11px; color: #f2f2f7; background-color: #2c2c2e; padding: 8px; border-radius: 6px; border-left: 4px solid #3b82f6; margin-top: 10px;"
            tab_style = """
                QTabWidget::pane {
                    border: 1px solid #3a3a3c;
                    background: #1c1c1e;
                    border-radius: 8px;
                }
                QTabBar::tab {
                    background: #2d2d2f;
                    color: #8e8e93;
                    border: 1px solid #3a3a3c;
                    padding: 8px 16px;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QTabBar::tab:selected {
                    background: #1c1c1e;
                    color: #ffffff;
                    border-bottom-color: #1c1c1e;
                }
            """
        else:
            btn_style = "QPushButton { padding: 6px 12px; }"
            cancel_btn_style = "QPushButton { padding: 6px 18px; }"
            save_btn_style = "QPushButton { padding: 6px 20px; font-weight: bold; }"
            note_style = "font-size: 11px; color: #1e293b; background-color: #f1f5f9; padding: 8px; border-radius: 6px; border-left: 4px solid #3b82f6; margin-top: 10px;"
            tab_style = """
                QTabWidget::pane {
                    border: 1px solid #e5e5e7;
                    background: #ffffff;
                    border-radius: 8px;
                }
                QTabBar::tab {
                    background: #f2f2f7;
                    color: #8e8e93;
                    border: 1px solid #e5e5e7;
                    padding: 8px 16px;
                    border-top-left-radius: 6px;
                    border-top-right-radius: 6px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QTabBar::tab:selected {
                    background: #ffffff;
                    color: #1c1c1e;
                    border-bottom-color: #ffffff;
                }
            """

        layout = QVBoxLayout()
        
        # Title Header
        title = QLabel("Grammar Trainer Configuration")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px; color: #2563eb;")
        layout.addWidget(title)
        
        # 1. API Provider Dropdown
        self.provider_combo = QComboBox()
        self.provider_combo.addItem("Google Gemini (Global, 15 req/min)", "gemini")
        self.provider_combo.addItem("Mistral AI (European, 100% Free for Students worldwide, No Credit Card!)", "mistral")
        
        # Set current provider
        current_provider = self.config.get("api_provider", "gemini")
        if current_provider == "mistral":
            self.provider_combo.setCurrentIndex(1)
        else:
            self.provider_combo.setCurrentIndex(0)
            
        self.provider_combo.currentIndexChanged.connect(self.on_provider_changed)
        
        # 2. Gemini API Key Field (row)
        self.gemini_label = QLabel("Gemini API Key:")
        self.gemini_key_widget = QWidget()
        gemini_key_layout = QHBoxLayout()
        gemini_key_layout.setContentsMargins(0, 0, 0, 0)
        
        self.gemini_key_input = QLineEdit()
        self.gemini_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.gemini_key_input.setText(self.config.get("api_key", ""))
        self.gemini_key_input.setPlaceholderText("Paste your Gemini API Key here")
        
        self.gemini_test_btn = QPushButton("🔌 Test Key")
        self.gemini_test_btn.clicked.connect(self.test_gemini_key)
        self.gemini_test_btn.setStyleSheet("font-weight: bold; padding: 4px 10px;")
        
        gemini_key_layout.addWidget(self.gemini_key_input)
        gemini_key_layout.addWidget(self.gemini_test_btn)
        self.gemini_key_widget.setLayout(gemini_key_layout)
        
        # 3. Mistral API Key Field (row)
        self.mistral_label = QLabel("Mistral API Key:")
        self.mistral_key_widget = QWidget()
        mistral_key_layout = QHBoxLayout()
        mistral_key_layout.setContentsMargins(0, 0, 0, 0)
        
        self.mistral_key_input = QLineEdit()
        self.mistral_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.mistral_key_input.setText(self.config.get("mistral_api_key", ""))
        self.mistral_key_input.setPlaceholderText("Paste your Mistral API Key here")
        
        self.mistral_test_btn = QPushButton("🔌 Test Key")
        self.mistral_test_btn.clicked.connect(self.test_mistral_key)
        self.mistral_test_btn.setStyleSheet("font-weight: bold; padding: 4px 10px;")
        
        mistral_key_layout.addWidget(self.mistral_key_input)
        mistral_key_layout.addWidget(self.mistral_test_btn)
        self.mistral_key_widget.setLayout(mistral_key_layout)
        
        # 4. Default Language ComboBox
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["English", "Danish", "German", "Swedish", "Norwegian", "French", "Spanish", "Italian"])
        self.lang_combo.setCurrentText(self.config.get("default_language", "English"))
        
        # 5. Default Difficulty ComboBox
        self.diff_combo = QComboBox()
        self.diff_combo.addItems(["A1", "A2", "B1", "B2", "C1", "C2"])
        self.diff_combo.setCurrentText(self.config.get("default_difficulty", "A1"))
        
        # 6. Default Distractors
        self.dist_spin = QSpinBox()
        self.dist_spin.setRange(2, 7)
        self.dist_spin.setValue(self.config.get("default_distractors", 5))
        
        # 7. Auto Flip QCheckBox
        self.auto_flip_cb = QCheckBox("Auto-flip card to back when an answer is selected")
        self.auto_flip_cb.setChecked(self.config.get("auto_flip", True))
        
        # 8. Show Language QCheckBox
        self.show_lang_cb = QCheckBox("Show target language badge on cards")
        self.show_lang_cb.setChecked(self.config.get("show_language", False))
        
        # 9. Show Difficulty QCheckBox
        self.show_diff_cb = QCheckBox("Show proficiency difficulty level on cards")
        self.show_diff_cb.setChecked(self.config.get("show_difficulty", False))
        
        # 10. Show Grammar Type QCheckBox
        self.show_type_cb = QCheckBox("Show grammar focus type badge on cards")
        self.show_type_cb.setChecked(self.config.get("show_grammar_type", False))
        
        # 11. Show Check Answer QCheckBox
        self.show_check_cb = QCheckBox("Show Check Answer button on cards")
        self.show_check_cb.setChecked(self.config.get("show_check_answer", False))
        
        # 12. Show Hint QCheckBox
        self.show_hint_cb = QCheckBox("Show Hint button on cards")
        self.show_hint_cb.setChecked(self.config.get("show_hint", False))
        
        # 13. Card White Background QCheckBox
        self.show_bg_cb = QCheckBox("Display cards with a clean white background container")
        self.show_bg_cb.setChecked(self.config.get("show_white_background", False))
        
        # 14. Center Horizontally QCheckBox
        self.center_horiz_cb = QCheckBox("Center text horizontally")
        self.center_horiz_cb.setChecked(self.config.get("center_horizontal", True))
 
        # 15. Center Vertically QCheckBox
        self.center_vert_cb = QCheckBox("Center text vertically (midcenter)")
        self.center_vert_cb.setChecked(self.config.get("center_vertical", True))
 
        # 16. Card Font Size QSpinBox
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(12, 48)
        self.font_size_spin.setValue(self.config.get("font_size", 20))
 
        # 17. Card Max Width QSpinBox
        self.card_max_width_spin = QSpinBox()
        self.card_max_width_spin.setRange(400, 1600)
        self.card_max_width_spin.setSingleStep(50)
        self.card_max_width_spin.setValue(self.config.get("card_max_width", 800))
 
        # 18. Explanation Alignment QComboBox
        self.explanation_align_combo = QComboBox()
        self.explanation_align_combo.addItems(["left", "center"])
        self.explanation_align_combo.setCurrentText(self.config.get("explanation_align", "left"))
 
        # Help components
        self.help_guide_btn = QPushButton("Open Help Guide")
        self.help_guide_btn.setStyleSheet(btn_style)
        self.help_guide_btn.clicked.connect(self.open_help_guide)
        
        self.report_issue_btn = QPushButton("⚑  Report an Issue")
        self.report_issue_btn.setStyleSheet(btn_style)
        self.report_issue_btn.clicked.connect(self.report_issue)
 
        self.reset_default_btn = QPushButton("↺  Reset to Default")
        self.reset_default_btn.setStyleSheet(btn_style)
        self.reset_default_btn.clicked.connect(self.reset_defaults)
        
        # Dynamic Note
        self.info_note = QLabel("")
        self.info_note.setStyleSheet(note_style)
        self.info_note.setWordWrap(True)
        
        # Create Tab Widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(tab_style)
        
        # Tab 1: General
        tab_general = QWidget()
        general_layout = QVBoxLayout(tab_general)
        general_layout.setContentsMargins(15, 15, 15, 15)
        general_form = QFormLayout()
        general_form.addRow(QLabel("API Provider:"), self.provider_combo)
        general_form.addRow(self.gemini_label, self.gemini_key_widget)
        general_form.addRow(self.mistral_label, self.mistral_key_widget)
        general_form.addRow(QLabel("Default Language:"), self.lang_combo)
        general_form.addRow(QLabel("Default Difficulty:"), self.diff_combo)
        general_form.addRow(QLabel("Number of Distractors:"), self.dist_spin)
        general_form.addRow(QLabel("Auto-Flip Card:"), self.auto_flip_cb)
        general_form.addRow(QLabel("Card White BG:"), self.show_bg_cb)
        general_layout.addLayout(general_form)
        general_layout.addWidget(self.info_note)
        general_layout.addStretch()
        
        # Tab 2: Layout
        tab_layout = QWidget()
        layout_tab_layout = QVBoxLayout(tab_layout)
        layout_tab_layout.setContentsMargins(15, 15, 15, 15)
        layout_form = QFormLayout()
        layout_form.addRow(QLabel("Align Horizontal:"), self.center_horiz_cb)
        layout_form.addRow(QLabel("Align Vertical:"), self.center_vert_cb)
        layout_form.addRow(QLabel("Card Font Size (px):"), self.font_size_spin)
        layout_form.addRow(QLabel("Card Max Width (px):"), self.card_max_width_spin)
        layout_form.addRow(QLabel("Explanation Align:"), self.explanation_align_combo)
        layout_tab_layout.addLayout(layout_form)
        layout_tab_layout.addStretch()
        
        # Tab 3: Badges
        tab_badges = QWidget()
        badges_layout = QVBoxLayout(tab_badges)
        badges_layout.setContentsMargins(15, 15, 15, 15)
        badges_form = QFormLayout()
        badges_form.addRow(QLabel("Show Language:"), self.show_lang_cb)
        badges_form.addRow(QLabel("Show Difficulty:"), self.show_diff_cb)
        badges_form.addRow(QLabel("Show Grammar Type:"), self.show_type_cb)
        badges_form.addRow(QLabel("Show Check Answer:"), self.show_check_cb)
        badges_form.addRow(QLabel("Show Hint:"), self.show_hint_cb)
        badges_layout.addLayout(badges_form)
        badges_layout.addStretch()
        
        # Tab 4: Help
        tab_help = QWidget()
        help_layout = QVBoxLayout(tab_help)
        help_layout.setContentsMargins(15, 15, 15, 15)
        help_header = QLabel("HELP")
        help_header.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748b; margin-bottom: 10px;")
        help_layout.addWidget(help_header)
        help_layout.addWidget(self.help_guide_btn)
        help_layout.addWidget(self.report_issue_btn)
        help_layout.addWidget(self.reset_default_btn)
        help_layout.addStretch()
        
        self.tabs.addTab(tab_general, "General")
        self.tabs.addTab(tab_layout, "Layout")
        self.tabs.addTab(tab_badges, "Badges")
        self.tabs.addTab(tab_help, "Help")
        
        layout.addWidget(self.tabs)
        
        # Update visibility initially
        self.on_provider_changed()
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 10, 0, 0)
        btn_layout.setSpacing(8)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setStyleSheet(cancel_btn_style)
        
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.save_settings)
        self.save_btn.setStyleSheet(save_btn_style)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)
        
        self.setLayout(layout)
        
    def on_provider_changed(self):
        provider = self.provider_combo.currentData()
        if provider == "gemini":
            self.gemini_label.setVisible(True)
            self.gemini_key_widget.setVisible(True)
            self.mistral_label.setVisible(False)
            self.mistral_key_widget.setVisible(False)
            self.info_note.setVisible(False)
        else:
            self.gemini_label.setVisible(False)
            self.gemini_key_widget.setVisible(False)
            self.mistral_label.setVisible(True)
            self.mistral_key_widget.setVisible(True)
            self.info_note.setVisible(True)
            self.info_note.setText(
                "🎓 <strong>Mistral AI (Recommended for Students in Europe):</strong><br/>"
                "• <strong>100% Free</strong> with no credit card required, even for European/UK students!<br/>"
                "• <strong>How to get key:</strong> Sign up at <strong>https://console.mistral.ai</strong> (or admin.mistral.ai) using Google/GitHub, click 'API keys' on the left menu, and click 'Create new key'. No billing setup needed!"
            )
            
    def test_gemini_key(self):
        api_key = self.gemini_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "API Key Required", "Please paste your Gemini API Key before testing.")
            return
            
        self.gemini_test_btn.setEnabled(False)
        self.gemini_test_btn.setText("Testing...")
        
        self.tester = ConnectionTester(api_key, "gemini")
        self.tester.finished.connect(self.on_gemini_test_finished)
        self.tester.start()
        
    def on_gemini_test_finished(self, success, message):
        self.gemini_test_btn.setEnabled(True)
        self.gemini_test_btn.setText("🔌 Test Key")
        
        if success:
            QMessageBox.information(
                self, 
                "Connection Successful!", 
                f"🎉 Success!\n\n{message}\n\nYour Gemini API key is working perfectly and is ready to generate grammar cards!"
            )
        else:
            troubleshooting = ""
            if "429" in message or "Quota exceeded" in message or "quota" in message.lower() or "limit" in message.lower():
                troubleshooting = (
                    "⚠️ DIAGNOSIS: Rate Limit or Quota Exceeded (EU/EEA/UK Free Limit is 0)\n\n"
                    "Google disables the completely free tier for European IP addresses. "
                    "To fix this 100% free with no credit card, connect a free VPN to the United States before generating, "
                    "or switch the API Provider to 'Mistral AI' which is 100% free with no limits in Europe!"
                )
            else:
                troubleshooting = "Please check your internet connection and verify your key is correct."
                
            QMessageBox.critical(
                self,
                "Gemini Connection Failed",
                f"❌ Connection Failed!\n\n{message}\n\n{troubleshooting}"
            )
            
    def test_mistral_key(self):
        api_key = self.mistral_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "API Key Required", "Please paste your Mistral API Key before testing.")
            return
            
        self.mistral_test_btn.setEnabled(False)
        self.mistral_test_btn.setText("Testing...")
        
        self.tester = ConnectionTester(api_key, "mistral")
        self.tester.finished.connect(self.on_mistral_test_finished)
        self.tester.start()
        
    def on_mistral_test_finished(self, success, message):
        self.mistral_test_btn.setEnabled(True)
        self.mistral_test_btn.setText("🔌 Test Key")
        
        if success:
            QMessageBox.information(
                self, 
                "Connection Successful!", 
                f"🎉 Success!\n\n{message}\n\nYour Mistral API key is working perfectly and is ready to generate grammar cards!"
            )
        else:
            QMessageBox.critical(
                self,
                "Mistral Connection Failed",
                f"❌ Connection Failed!\n\n{message}\n\nMake sure you copied your Mistral API key correctly from https://console.mistral.ai"
            )
            
    def save_settings(self):
        # Update config mapping
        self.config["api_provider"] = self.provider_combo.currentData()
        self.config["api_key"] = self.gemini_key_input.text().strip()
        self.config["mistral_api_key"] = self.mistral_key_input.text().strip()
        self.config["default_language"] = self.lang_combo.currentText()
        self.config["default_difficulty"] = self.diff_combo.currentText()
        self.config["default_distractors"] = self.dist_spin.value()
        self.config["auto_flip"] = self.auto_flip_cb.isChecked()
        self.config["show_language"] = self.show_lang_cb.isChecked()
        self.config["show_difficulty"] = self.show_diff_cb.isChecked()
        self.config["show_grammar_type"] = self.show_type_cb.isChecked()
        self.config["show_check_answer"] = self.show_check_cb.isChecked()
        self.config["show_hint"] = self.show_hint_cb.isChecked()
        self.config["show_white_background"] = self.show_bg_cb.isChecked()
        self.config["center_horizontal"] = self.center_horiz_cb.isChecked()
        self.config["center_vertical"] = self.center_vert_cb.isChecked()
        self.config["font_size"] = self.font_size_spin.value()
        self.config["card_max_width"] = self.card_max_width_spin.value()
        self.config["explanation_align"] = self.explanation_align_combo.currentText()
        
        # Write config persistently
        addon_name = __package__ or __name__.split('.')[0]
        mw.addonManager.writeConfig(addon_name, self.config)
        
        # Instantly update Anki note type template/styling to reflect show/hide selections
        try:
            from .note_type import setup_note_type
            setup_note_type()
            mw.reset()
        except Exception:
            pass
            
        self.accept()

    def open_help_guide(self):
        dialog = GuideDialog(self)
        dialog.exec()

    def report_issue(self):
        QDesktopServices.openUrl(QUrl("https://github.com/Doummar/Grammar_Trainer/issues"))

    def reset_defaults(self):
        reply = QMessageBox.question(
            self,
            "Reset Defaults",
            "Are you sure you want to reset all settings to their default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.provider_combo.setCurrentIndex(0)
            self.gemini_key_input.setText("")
            self.mistral_key_input.setText("")
            self.lang_combo.setCurrentText("English")
            self.diff_combo.setCurrentText("A1")
            self.dist_spin.setValue(5)
            self.auto_flip_cb.setChecked(True)
            self.show_lang_cb.setChecked(False)
            self.show_diff_cb.setChecked(False)
            self.show_type_cb.setChecked(False)
            self.show_check_cb.setChecked(False)
            self.show_hint_cb.setChecked(False)
            self.show_bg_cb.setChecked(False)
            self.center_horiz_cb.setChecked(True)
            self.center_vert_cb.setChecked(True)
            self.font_size_spin.setValue(20)
            self.card_max_width_spin.setValue(800)
            self.explanation_align_combo.setCurrentText("left")

class CollapsibleSection(QWidget):
    def __init__(self, title, content_widget, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 4, 0, 4)
        self.layout.setSpacing(0)
        
        # Detect Anki theme
        is_dark = False
        try:
            from aqt import mw
            is_dark = mw.theme_manager.night_mode
        except Exception:
            try:
                is_dark = mw.pm.night_mode()
            except Exception:
                pass
        
        self.header_btn = QPushButton(f"▶  {title}")
        self.header_btn.setCheckable(True)
        if is_dark:
            self.header_btn.setStyleSheet(
                "QPushButton {"
                "  text-align: left;"
                "  font-weight: bold;"
                "  padding: 10px 14px;"
                "  background-color: #2d2d2f;"
                "  border: 1px solid #3a3a3c;"
                "  border-radius: 6px;"
                "  color: #ffffff;"
                "  font-size: 11px;"
                "}"
                "QPushButton:checked {"
                "  background-color: #1e293b;"
                "  color: #93c5fd;"
                "  border-color: #3b82f6;"
                "}"
            )
        else:
            self.header_btn.setStyleSheet(
                "QPushButton {"
                "  text-align: left;"
                "  font-weight: bold;"
                "  padding: 10px 14px;"
                "  background-color: #f3f4f6;"
                "  border: 1px solid #e5e7eb;"
                "  border-radius: 6px;"
                "  color: #1f2937;"
                "  font-size: 11px;"
                "}"
                "QPushButton:checked {"
                "  background-color: #bfdbfe;"
                "  color: #1e3a8a;"
                "  border-color: #93c5fd;"
                "}"
            )
        self.header_btn.clicked.connect(self.toggle)
        self.layout.addWidget(self.header_btn)
        
        self.content = content_widget
        self.content.setVisible(False)
        self.layout.addWidget(self.content)
        self.title_text = title

    def toggle(self):
        is_visible = self.content.isVisible()
        self.content.setVisible(not is_visible)
        self.header_btn.setChecked(not is_visible)
        arrow = "▼" if not is_visible else "▶"
        self.header_btn.setText(f"{arrow}  {self.title_text}")

class GuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Grammar Trainer - Guide")
        self.resize(540, 660)
        
        # Detect Anki theme (dark/night mode vs light mode)
        self.is_dark = False
        try:
            self.is_dark = mw.theme_manager.night_mode
        except Exception:
            try:
                self.is_dark = mw.pm.night_mode()
            except Exception:
                pass
                
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Title
        title_label = QLabel("Grammar Trainer: Guide")
        if self.is_dark:
            title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff; margin-bottom: 2px;")
        else:
            title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #111827; margin-bottom: 2px;")
        layout.addWidget(title_label)
        
        desc_label = QLabel("Click any section to expand.")
        if self.is_dark:
            desc_label.setStyleSheet("font-size: 11px; color: #9ca3af; margin-bottom: 10px;")
        else:
            desc_label.setStyleSheet("font-size: 11px; color: #6b7280; margin-bottom: 10px;")
        layout.addWidget(desc_label)
        
        # Determine stylesheets based on theme
        if self.is_dark:
            section_style = "font-size: 11px; color: #f2f2f7; background-color: #2c2c2e; border: 1px solid #3e3e40; border-radius: 6px; padding: 12px; margin-top: 2px;"
            sep_style = "color: #3e3e40;"
            settings_btn_style = "QPushButton { padding: 6px 14px; font-weight: bold; }"
            got_it_btn_style = "QPushButton { padding: 6px 18px; font-weight: bold; }"
        else:
            section_style = "font-size: 11px; color: #374151; background-color: #f9fafb; border: 1px solid #e5e7eb; border-radius: 6px; padding: 12px; margin-top: 2px;"
            sep_style = "color: #e5e7eb;"
            settings_btn_style = "QPushButton { padding: 6px 14px; font-weight: bold; }"
            got_it_btn_style = "QPushButton { padding: 6px 18px; font-weight: bold; }"

        # Scroll Area for sections
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        scroll_widget = QWidget()
        scroll_widget.setStyleSheet("background: transparent;")
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(4)
        
        # Section 1: HOW IT WORKS
        how_it_works_content = QLabel(
            "• <b>Automatic Cloze:</b> This add-on automatically converts target grammar fields into interactive fill-in-the-blank dropdown lists.<br/><br/>"
            "• <b>Double Blank (Multi-Cloze):</b> Check the multi-cloze option in the generator to create sentences with two dropdown fields on a single card!<br/><br/>"
            "• <b>Smart Generation:</b> Gemini or Mistral AI will analyze your prompt to generate contextually relevant, grammatically appropriate distractors (options)."
        )
        how_it_works_content.setWordWrap(True)
        how_it_works_content.setStyleSheet(section_style)
        
        self.sec1 = CollapsibleSection("HOW IT WORKS", how_it_works_content)
        scroll_layout.addWidget(self.sec1)
        
        # Section: HOW TO ADD CARDS
        add_cards_content = QLabel(
            "• <b>Option 1: Using the AI Cloze Generator (Recommended)</b><br/>"
            "1. Click the brain icon (🧠) in Anki's editor toolbar or press <b>Ctrl+Shift+G</b> to open the generator.<br/>"
            "2. Fill in the Language, Difficulty, and specify your grammar topic (e.g. 'Spanish Subjunctive').<br/>"
            "3. Click <b>Generate Card & Open Fields</b>. Review or edit any fields, then click <b>Add</b> to save.<br/><br/>"
            "• <b>Option 2: Creating Cards Manually</b><br/>"
            "1. In Anki, click <b>Add</b> in the main window toolbar.<br/>"
            "2. Set the Note Type to <b>Grammar Trainer</b>.<br/>"
            "3. In the <b>Sentence</b> field, write your sentence and use <b>{blank}</b> where the dropdown cloze should appear. For a double-cloze card, use <b>{blank1}</b> and <b>{blank2}</b>.<br/>"
            "4. In the <b>TargetWord</b> field, enter the correct answers (separated by <b>||</b> for double-cloze).<br/>"
            "5. In the <b>Options</b> field, write incorrect choices separated by <b>|</b> (and use <b>||</b> to separate distractor lists for double-cloze)."
        )
        add_cards_content.setWordWrap(True)
        add_cards_content.setStyleSheet(section_style)
        
        self.sec_add_card = CollapsibleSection("HOW TO ADD CARDS", add_cards_content)
        scroll_layout.addWidget(self.sec_add_card)
        
        # Section 2: CLOZE KEYBOARD SHORTCUTS
        shortcuts_content = QLabel(
            "• <b>Select Options:</b> Use your keyboard number keys <b>1</b>, <b>2</b>, <b>3</b>... to quickly choose dropdown items without using a mouse.<br/><br/>"
            "• <b>Check Answers:</b> Press the <b>Enter</b> key to instantly validate your selections and see visual correct/incorrect boundaries.<br/><br/>"
            "• <b>Flip Card:</b> Press <b>Spacebar</b> to flip the card to the back and reveal the full explanation/translation."
        )
        shortcuts_content.setWordWrap(True)
        shortcuts_content.setStyleSheet(section_style)
        
        self.sec2 = CollapsibleSection("CLOZE KEYBOARD SHORTCUTS", shortcuts_content)
        scroll_layout.addWidget(self.sec2)
        
        # Section 3: AUDIO & TTS PLAYBACK
        audio_content = QLabel(
            "• <b>Google Translate TTS:</b> If enabled, high-quality native Text-to-Speech audio will automatically play upon showing the front/back card.<br/><br/>"
            "• <b>On-demand Playback:</b> You can click the audio speaker icon in the top-right corner of the card to replay the native audio at any time.<br/><br/>"
            "• <b>Anki Native Audio:</b> Fully compatible with Anki's native TTS tags and audio field attachments."
        )
        audio_content.setWordWrap(True)
        audio_content.setStyleSheet(section_style)
        
        self.sec3 = CollapsibleSection("AUDIO & TTS PLAYBACK", audio_content)
        scroll_layout.addWidget(self.sec3)
        
        # Section 4: CARD THEMING & BADGES
        theming_content = QLabel(
            "• <b>Badges Toggle:</b> You can individually show/hide the Language, Difficulty, and Grammar Category badges to declutter your review screen.<br/><br/>"
            "• <b>White BG Container:</b> Displays a gorgeous, responsive card container with a subtle shadow. Toggle it off to use a transparent container.<br/><br/>"
            "• <b>Dark Mode Support:</b> Fully optimized for Anki's Night Mode with automatic color inversion and high-contrast styling."
        )
        theming_content.setWordWrap(True)
        theming_content.setStyleSheet(section_style)
        
        self.sec4 = CollapsibleSection("CARD THEMING & BADGES", theming_content)
        scroll_layout.addWidget(self.sec4)
        
        # Section: AI PROVIDERS & SETUP
        ai_setup_content = QLabel(
            "• <b>Mistral AI (Recommended for Students in Europe):</b><br/>"
            "  - 100% Free with no credit card required, even for European/UK students!<br/>"
            "  - <b>How to get key:</b> Sign up at <a href='https://console.mistral.ai' style='color: #2563eb;'>https://console.mistral.ai</a> (or admin.mistral.ai) using Google/GitHub, click 'API keys' on the left menu, and click 'Create new key'. No billing setup needed!<br/><br/>"
            "• <b>Google Gemini API Key:</b><br/>"
            "  - High-performance models with generous free-tier allocation.<br/>"
            "  - Obtain your API key from Google AI Studio."
        )
        ai_setup_content.setWordWrap(True)
        ai_setup_content.setOpenExternalLinks(True)
        ai_setup_content.setStyleSheet(section_style)
        
        self.sec_ai_setup = CollapsibleSection("AI PROVIDERS & SETUP", ai_setup_content)
        scroll_layout.addWidget(self.sec_ai_setup)
        
        # Section 5: TIPS FOR OPTIMAL GENERATION
        tips_content = QLabel(
            "• <b>Be Descriptive:</b> When generating cards, specify the exact grammar topic (e.g., 'German Accusative Prepositions' or 'Spanish Subjunctive Mood').<br/><br/>"
            "• <b>Provide Context:</b> Providing a short hint or target word ensures the AI generates realistic and practical sentences.<br/><br/>"
            "• <b>Verify API Key:</b> Always run the 'Test Key' utility in settings if card generation fails to verify server connectivity."
        )
        tips_content.setWordWrap(True)
        tips_content.setStyleSheet(section_style)
        
        self.sec5 = CollapsibleSection("TIPS FOR OPTIMAL GENERATION", tips_content)
        scroll_layout.addWidget(self.sec5)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Horizontal Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        sep.setStyleSheet(sep_style)
        layout.addWidget(sep)
        
        # Bottom Buttons Layout
        btn_layout = QHBoxLayout()
        self.settings_btn = QPushButton("Open Settings")
        self.settings_btn.setStyleSheet(settings_btn_style)
        self.settings_btn.clicked.connect(self.open_settings)
        btn_layout.addWidget(self.settings_btn)
        
        btn_layout.addStretch()
        
        self.got_it_btn = QPushButton("Got it ✔")
        self.got_it_btn.setStyleSheet(got_it_btn_style)
        self.got_it_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.got_it_btn)
        
        layout.addLayout(btn_layout)
        
        # Second Horizontal Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setFrameShadow(QFrame.Shadow.Sunken)
        sep2.setStyleSheet(sep_style)
        layout.addWidget(sep2)
        
        # Footer
        footer_layout = QHBoxLayout()
        footer_left = QLabel("Grammar Trainer v1.0.0 — Created by Adel")
        footer_left.setStyleSheet("font-size: 10px; color: #9ca3af; margin-top: 2px;")
        footer_right = QLabel("Since 2026")
        footer_right.setStyleSheet("font-size: 10px; color: #9ca3af; margin-top: 2px;")
        footer_layout.addWidget(footer_left)
        footer_layout.addStretch()
        footer_layout.addWidget(footer_right)
        layout.addLayout(footer_layout)

    def accept(self):
        parent_dialog = self.parent()
        super().accept()
        if parent_dialog and isinstance(parent_dialog, SettingsDialog):
            parent_dialog.accept()

    def open_settings(self):
        super().accept()
        # If the parent is not already SettingsDialog, open it
        if not isinstance(self.parent(), SettingsDialog):
            dialog = SettingsDialog(mw)
            dialog.exec()

def show_settings_dialog():
    dialog = SettingsDialog(mw)
    dialog.exec()

def show_guide_dialog():
    dialog = GuideDialog(mw)
    dialog.exec()
