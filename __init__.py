# -*- coding: utf-8 -*-
# Grammar Trainer
# Created by Adel Aitah
# GitHub: https://github.com/Doummar/Grammar_Trainer
# Copyright (c) 2026 Adel Aitah — All rights reserved
"""
Grammar Trainer — AI Grammar & Sentence Trainer
An interactive grammar trainer that uses Google Gemini or Mistral AI
to automatically generate grammar exercises, sentence distractors,
and smart hints inside Anki.
"""

from aqt import mw, gui_hooks
from aqt.qt import *

ADDON_NAME = "Grammar Trainer"
ADDON_AUTHOR  = "Adel Aitah"
ADDON_VERSION = "1.0.0"
ADDON_URL     = "https://github.com/Doummar/Grammar_Trainer"
HANDLE = 12

import os
from aqt.utils import showInfo

from .settings import show_settings_dialog, show_guide_dialog
from .generator import show_generator_dialog
from .note_type import setup_note_type

def on_webview_will_set_content(web_content, context):
    web_content.head += "<script>window.AI_GRAMMAR_ADDON_INSTALLED = true;</script>"

def on_editor_did_init_buttons(buttons, editor):
    # Load our custom brain icon file path
    icon_path = os.path.join(os.path.dirname(__file__), "brain.svg")
    
    # Add our button to the editor toolbar
    btn = editor.addButton(
        icon_path,
        "ai_grammar_dropdown_gen",
        func=lambda ed: show_generator_dialog(ed),
        tip="Open Grammar Trainer (Ctrl+Shift+G)",
        keys="Ctrl+Shift+G",
        id="ai_grammar_dropdown_gen"
    )
    buttons.append(btn)

def check_first_run():
    addon_name = __package__ or __name__.split('.')[0]
    config = mw.addonManager.getConfig(addon_name) or {}
    if not config.get("guide_shown_v1", False):
        config["guide_shown_v1"] = True
        mw.addonManager.writeConfig(addon_name, config)
        QTimer.singleShot(1000, show_guide_dialog)

def init_addon():
    # Register the note type setup when profile is opened (mw.col is ready)
    gui_hooks.profile_did_open.append(setup_note_type)
    gui_hooks.profile_did_open.append(check_first_run)
    gui_hooks.webview_will_set_content.append(on_webview_will_set_content)
    gui_hooks.editor_did_init_buttons.append(on_editor_did_init_buttons)
    
    # Locate/create an Anki tools menu action
    menu = mw.form.menuTools
    
    # Settings Item
    action_settings = QAction("Grammar Trainer Settings", mw)
    action_settings.triggered.connect(show_settings_dialog)
    menu.addAction(action_settings)

# Execute initialization on load
init_addon()
