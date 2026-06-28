# -*- coding: utf-8 -*-
from aqt import mw

NOTE_TYPE_NAME = "Grammar Trainer"
FIELDS = ["Sentence", "TargetWord", "Options", "Explanation", "GrammarType", "Difficulty", "Language", "FrontAudio", "BackAudio"]

FRONT_TEMPLATE = """
<div class="anki-card-outer-container">
  <div class="top-right-audio" id="front-audio-container">
    {{FrontAudio}}
  </div>

  <div class="anki-grammar-card">
    <div class="card-meta">
      <span class="badge badge-lang">{{Language}}</span>
      <span class="badge badge-diff">{{Difficulty}}</span>
      <span class="badge badge-type">{{GrammarType}}</span>
    </div>

    <div class="sentence-container" id="sentence-container">
      {{Sentence}}
    </div>

    <div class="action-bar" id="action-bar">
      <button class="check-btn" id="check-btn" onclick="checkAnkiAnswers()">Check Answer</button>
      <button class="hint-btn" id="hint-btn" onclick="showAnkiHint()">Hint</button>
    </div>

    <div id="hint-box" class="hint-box hidden">
      <!-- Hint area -->
    </div>

    <div id="correct-banner-box" class="back-only-container hidden">
      <div class="correct-banner">
        Correct Answer Options: <strong class="correct-text">{{TargetWord}}</strong>
      </div>
    </div>

    <div id="result-box" class="result-box hidden">
      <div id="result-message" class="result-message"></div>
      
      <div class="explanation-container">
        <div class="explanation-header">Grammar Explanation</div>
        <div class="explanation-body">
          {{Explanation}}
        </div>
      </div>
    </div>
  </div>
</div>

<div id="target-raw" style="display:none;">{{TargetWord}}</div>
<div id="options-raw" style="display:none;">{{Options}}</div>

<script>
// Mobile-friendly inline JavaScript controller for Anki card interaction
var _correctAnswers = [];

function initDropdowns() {
  var sentenceArea = document.getElementById("sentence-container");
  var targetRaw = document.getElementById("target-raw").innerHTML.trim();
  var optionsRaw = document.getElementById("options-raw").innerHTML.trim();
  
  if (!sentenceArea || !targetRaw || !optionsRaw) return;
  
  // Parse targets and options group
  var targets = targetRaw.split("||").map(function(s) { return s.trim(); });
  var optionsGroup = optionsRaw.split("||").map(function(s) { return s.trim().split("|").map(function(o) { return o.trim(); }); });
  
  _correctAnswers = targets;
  var html = sentenceArea.innerHTML;
  
  // Detect if Python desktop add-on is loaded/installed
  var addonInstalled = (window.AI_GRAMMAR_ADDON_INSTALLED === true);
  
  if (!addonInstalled) {
    // Hide dropdown controls action bar since add-on is not installed
    var actionBar = document.getElementById("action-bar");
    if (actionBar) {
      actionBar.style.display = "none";
    }
    
    // Check if we are currently reviewing the Back side of the card
    var isBackSide = (document.getElementById("answer") !== null);
    
    if (isBackSide) {
      // BACK SIDE FALLBACK: show the correct answer filled in and highlighted
      for (var i = 0; i < targets.length; i++) {
        var placeholderSingle = "{" + "{blank" + "}";
        placeholderSingle += "}";
        var placeholderMulti = "{" + "{blank" + (i + 1);
        placeholderMulti += "}";
        var filledHtml = '<span class="correct-text-inline">' + escapeHtml(targets[i]) + '</span>';
        
        if (html.indexOf(placeholderMulti) !== -1) {
          html = html.replace(placeholderMulti, filledHtml);
        } else if (html.indexOf(placeholderSingle) !== -1) {
          html = html.replace(placeholderSingle, filledHtml);
        } else {
          html = html.replace(/________|_ _ _ _/, filledHtml);
        }
      }
      sentenceArea.innerHTML = html;
      
      // Auto-reveal the explanation block
      var resultBox = document.getElementById("result-box");
      if (resultBox) {
        resultBox.classList.remove("hidden");
      }
    } else {
      // FRONT SIDE FALLBACK: replace blanks with clean blank underlines
      for (var i = 0; i < targets.length; i++) {
        var placeholderSingle = "{" + "{blank" + "}";
        placeholderSingle += "}";
        var placeholderMulti = "{" + "{blank" + (i + 1);
        placeholderMulti += "}";
        var underlineHtml = '<span class="grammar-blank-underline">&nbsp;&nbsp;________&nbsp;&nbsp;</span>';
        
        if (html.indexOf(placeholderMulti) !== -1) {
          html = html.replace(placeholderMulti, underlineHtml);
        } else if (html.indexOf(placeholderSingle) !== -1) {
          html = html.replace(placeholderSingle, underlineHtml);
        } else {
          html = html.replace(/________|_ _ _ _/, underlineHtml);
        }
      }
      sentenceArea.innerHTML = html;
    }
    return;
  }
  
  // Standard drop-down interactive mode when add-on is installed
  for (var i = 0; i < targets.length; i++) {
    var placeholderSingle = "{" + "{blank" + "}";
    placeholderSingle += "}";
    var placeholderMulti = "{" + "{blank" + (i + 1);
    placeholderMulti += "}";
    var dropdownHtml = createDropdownHTML(i, optionsGroup[i] || []);
    
    if (html.indexOf(placeholderMulti) !== -1) {
      html = html.replace(placeholderMulti, dropdownHtml);
    } else if (html.indexOf(placeholderSingle) !== -1) {
      html = html.replace(placeholderSingle, dropdownHtml);
    } else {
      // Fallback: search for underscores
      html = html.replace(/________|_ _ _ _/, dropdownHtml);
    }
  }
  
  sentenceArea.innerHTML = html;
  restoreSelectedState();
}

function shuffleDropdownOptions(select) {
  if (select.disabled) return;
  var now = new Date().getTime();
  if (select.lastShuffleTime && (now - select.lastShuffleTime < 500)) {
    return;
  }
  select.lastShuffleTime = now;
  
  var selectedValue = select.value;
  var optionsArray = [];
  for (var i = 1; i < select.options.length; i++) {
    optionsArray.push({
      value: select.options[i].value,
      text: select.options[i].text
    });
  }
  optionsArray.sort(function() { return Math.random() - 0.5; });
  while (select.options.length > 1) {
    select.remove(1);
  }
  for (var j = 0; j < optionsArray.length; j++) {
    var opt = document.createElement("option");
    opt.value = optionsArray[j].value;
    opt.text = optionsArray[j].text;
    select.add(opt);
  }
  select.value = selectedValue;
}

function createDropdownHTML(index, options) {
  // Fisher-Yates Shuffle
  var shuffled = options.slice();
  shuffled.sort(function() { return Math.random() - 0.5; });
  
  var html = '<select class="grammar-dropdown" id="blank-select-' + index + '" onchange="dropdownChanged(' + index + ')" onmousedown="shuffleDropdownOptions(this)" onfocus="shuffleDropdownOptions(this)">';
  html += '<option value="">-- select --</option>';
  for (var i = 0; i < shuffled.length; i++) {
    html += '<option value="' + escapeHtml(shuffled[i]) + '">' + escapeHtml(shuffled[i]) + '</option>';
  }
  html += '</select>';
  return html;
}

function getCardKey() {
  var t = document.getElementById("target-raw");
  var o = document.getElementById("options-raw");
  var key = "anki-dropdown-";
  if (t) key += t.innerHTML.trim();
  if (o) key += o.innerHTML.trim();
  var hash = 0;
  for (var i = 0; i < key.length; i++) {
    var char = key.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return "anki-card-" + hash;
}

function dropdownChanged(index) {
  var select = document.getElementById("blank-select-" + index);
  if (select) {
    sessionStorage.setItem(getCardKey() + "-sel-" + index, select.value);
  }
  
  var config = window.AI_GRAMMAR_CONFIG || {};
  if (config.auto_flip) {
    var allSelected = true;
    for (var i = 0; i < _correctAnswers.length; i++) {
      var s = document.getElementById("blank-select-" + i);
      if (!s || !s.value) {
        allSelected = false;
        break;
      }
    }
    if (allSelected) {
      setTimeout(function() {
        if (typeof pycmd !== "undefined") {
          pycmd("ans");
        } else if (typeof showAnswer !== "undefined") {
          showAnswer();
        } else if (typeof AnkiDroidJS !== "undefined" && AnkiDroidJS.showAnswer) {
          AnkiDroidJS.showAnswer();
        } else if (window.AnkiDroidJS && window.AnkiDroidJS.showAnswer) {
          window.AnkiDroidJS.showAnswer();
        } else {
          window.location.href = "anki://showAnswer";
        }
      }, 250);
    }
  }
}

function restoreSelectedState() {
  for (var i = 0; i < _correctAnswers.length; i++) {
    var select = document.getElementById("blank-select-" + i);
    var savedVal = sessionStorage.getItem(getCardKey() + "-sel-" + i);
    if (select && savedVal) {
      select.value = savedVal;
    }
  }
}

function checkAnkiAnswers() {
  var allCorrect = true;
  var answeredCount = 0;
  
  for (var i = 0; i < _correctAnswers.length; i++) {
    var select = document.getElementById("blank-select-" + i);
    if (!select) continue;
    
    var selected = select.value;
    var correct = _correctAnswers[i];
    
    if (selected) answeredCount++;
    
    select.disabled = true;
    if (selected.toLowerCase() === correct.toLowerCase()) {
      select.className = "grammar-dropdown correct-val";
    } else {
      select.className = "grammar-dropdown incorrect-val";
      allCorrect = false;
    }
  }
  
  if (answeredCount === 0) {
    return;
  }
  
  var resultBox = document.getElementById("result-box");
  var resultMsg = document.getElementById("result-message");
  
  if (resultBox && resultMsg) {
    if (allCorrect) {
      // Keep evaluation but remove the printed success text as requested
      resultMsg.innerHTML = '';
      resultBox.classList.add("hidden");
    } else {
      resultBox.classList.remove("hidden");
      resultMsg.innerHTML = '<span style="color: #ef4444; font-weight: bold;">❌ Incorrect. Correct form: ' + escapeHtml(_correctAnswers.join(", ")) + '</span>';
    }
  }
  
  var checkBtn = document.getElementById("check-btn");
  if (checkBtn) checkBtn.disabled = true;
}

function showAnkiHint() {
  var hintBox = document.getElementById("hint-box");
  if (hintBox) {
    hintBox.classList.toggle("hidden");
    hintBox.innerHTML = "<strong>Hint:</strong> The correct term starts with '" + _correctAnswers[0].charAt(0).toUpperCase() + "' and consists of " + _correctAnswers[0].length + " letters.";
  }
}

function revealAnkiAnswers() {
  initDropdowns();
  var addonInstalled = (window.AI_GRAMMAR_ADDON_INSTALLED === true);
  if (addonInstalled) {
    checkAnkiAnswers();
  }
  
  // Reveal the correct banner on the back side
  var banner = document.getElementById("correct-banner-box");
  if (banner) {
    banner.classList.remove("hidden");
  }
  
  // Reveal the explanation box on the back side
  var resultBox = document.getElementById("result-box");
  if (resultBox) {
    resultBox.classList.remove("hidden");
  }
}

function escapeHtml(text) {
  var map = {
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  };
  return text.replace(/[&<>"']/g, function(m) { return map[m]; });
}

initDropdowns();
</script>
"""

BACK_TEMPLATE = """
{{FrontSide}}

<hr id="answer">

<div class="back-only-container">
  <div class="top-right-audio" id="back-audio-container">
    {{BackAudio}}
  </div>
</div>

<script>
var frontAudio = document.getElementById("front-audio-container");
if (frontAudio) {
  frontAudio.style.display = "none";
}
revealAnkiAnswers();
</script>
"""

CSS_STYLING = """
.card {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background-color: #ffffff;
  color: #1e293b;
  margin: 0;
  padding: 20px;
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: center;
  min-height: 100vh;
  box-sizing: border-box;
}

.nightMode .card {
  background-color: #0f172a;
  color: #f1f5f9;
}

.anki-card-outer-container {
  position: relative;
  width: 100%;
  max-width: 720px;
  margin: 0 auto;
  box-sizing: border-box;
}

.anki-grammar-card {
  width: 100%;
  max-width: 100%;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  padding: 24px;
  box-sizing: border-box;
  position: relative;
}

.top-right-audio {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 100;
}

.nightMode .anki-grammar-card {
  background: #1e293b;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.card-meta {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  justify-content: center;
}

.badge {
  font-size: 11px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 6px;
  text-transform: uppercase;
}

.badge-lang { background-color: #dbeafe; color: #1e40af; }
.badge-diff { background-color: #fee2e2; color: #991b1b; }
.badge-type { background-color: #fef3c7; color: #92400e; }

.nightMode .badge-lang { background-color: #1e3a8a; color: #93c5fd; }
.nightMode .badge-diff { background-color: #7f1d1d; color: #fca5a5; }
.nightMode .badge-type { background-color: #78350f; color: #fcd34d; }

.sentence-container {
  font-size: 20px;
  line-height: 1.6;
  margin-bottom: 24px;
  text-align: center;
}

.grammar-dropdown {
  font-size: 16px;
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  background-color: #ffffff;
  color: #1e293b;
  cursor: pointer;
  margin: 0 4px;
  font-weight: bold;
  transition: background-color 0.15s ease, border-color 0.15s ease;
}

.grammar-dropdown:hover {
  background-color: #f8fafc;
  border-color: #94a3b8;
}

.nightMode .grammar-dropdown {
  border-color: #475569;
  background-color: #334155;
  color: #f1f5f9;
}

#answer {
  border: none !important;
  margin: 0 !important;
  padding: 0 !important;
  height: 0 !important;
  background: transparent !important;
}

.grammar-dropdown.correct-val {
  border: 1.5px solid #10b981 !important;
  background-color: #ffffff !important;
  color: #1e293b !important;
  box-shadow: none !important;
}

.grammar-dropdown.incorrect-val {
  border: 1.5px solid #ef4444 !important;
  background-color: #ffffff !important;
  color: #1e293b !important;
  box-shadow: none !important;
}

.nightMode .grammar-dropdown.correct-val {
  border: 1.5px solid #10b981 !important;
  background-color: #334155 !important;
  color: #f1f5f9 !important;
  box-shadow: none !important;
}

.nightMode .grammar-dropdown.incorrect-val {
  border: 1.5px solid #ef4444 !important;
  background-color: #334155 !important;
  color: #f1f5f9 !important;
  box-shadow: none !important;
}

.action-bar {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  justify-content: center;
}

button {
  font-size: 14px;
  font-weight: 600;
  padding: 8px 16px;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: background-color 0.15s ease, opacity 0.15s ease;
}

button:hover {
  opacity: 0.9;
}

button:active {
  opacity: 0.8;
}

.check-btn {
  background-color: #2563eb;
  color: #ffffff;
}

.hint-btn {
  background-color: #cbd5e1;
  color: #334155;
}

.nightMode .hint-btn {
  background-color: #475569;
  color: #f1f5f9;
}

.hint-box {
  background-color: #eff6ff;
  border-left: 4px solid #3b82f6;
  border-radius: 0 8px 8px 0;
  padding: 12px;
  font-size: 14px;
  color: #1e40af;
  margin-bottom: 20px;
  text-align: left;
}

.nightMode .hint-box {
  background-color: #1e3a8a;
  color: #bfdbfe;
}

.result-box {
  border-top: 1px solid #e2e8f0;
  padding-top: 20px;
  text-align: left;
}

.nightMode .result-box {
  border-color: #334155;
}

.result-message {
  font-size: 16px;
  font-weight: bold;
  margin-bottom: 12px;
}

.explanation-container {
  background: #f1f5f9;
  border-radius: 8px;
  padding: 16px;
}

.nightMode .explanation-container {
  background: #334155;
}

.explanation-header {
  font-size: 12px;
  font-weight: bold;
  text-transform: uppercase;
  color: #64748b;
  margin-bottom: 8px;
}

.explanation-body {
  font-size: 14px;
  line-height: 1.5;
}

.back-only-container {
  margin-top: 20px;
}

.correct-banner {
  background-color: #ecfdf5;
  border: 1px solid #a7f3d0;
  padding: 12px;
  border-radius: 8px;
  color: #065f46;
}

.nightMode .correct-banner {
  background-color: #064e3b;
  color: #a7f3d0;
  border-color: #047857;
}

.hidden { display: none !important; }

.audio-btn {
  background-color: #f1f5f9;
  color: #0f172a;
}

.nightMode .audio-btn {
  background-color: #334155;
  color: #f8fafc;
}

.correct-text-inline {
  font-weight: bold !important;
  border-bottom: 2px solid #10b981 !important;
  padding: 0 4px !important;
}

.nightMode .correct-text-inline {
  border-bottom-color: #34d399 !important;
}

.grammar-blank-underline {
  border-bottom: 2px solid #64748b !important;
  padding-bottom: 2px !important;
  color: transparent !important;
  font-family: monospace !important;
}

.nightMode .grammar-blank-underline {
  border-bottom-color: #94a3b8 !important;
}
"""

def setup_note_type():
    col = mw.col
    models = col.models
    
    # Load configuration
    addon_name = __package__ or __name__.split('.')[0]
    config = mw.addonManager.getConfig(addon_name) or {}
    show_lang = config.get("show_language", False)
    show_diff = config.get("show_difficulty", False)
    show_type = config.get("show_grammar_type", False)
    show_hint = config.get("show_hint", False)
    show_check = config.get("show_check_answer", False)
    show_bg = config.get("show_white_background", False)
    center_horiz = config.get("center_horizontal", True)
    center_vert = config.get("center_vertical", True)
    auto_flip = config.get("auto_flip", True)
    
    # Append display overrides based on show/hide options
    css_with_toggles = CSS_STYLING
    if not show_lang:
        css_with_toggles += "\n.badge-lang { display: none !important; }"
    if not show_diff:
        css_with_toggles += "\n.badge-diff { display: none !important; }"
    if not show_type:
        css_with_toggles += "\n.badge-type { display: none !important; }"
    if not show_hint:
        css_with_toggles += "\n.hint-btn { display: none !important; }"
    if not show_check:
        css_with_toggles += "\n.check-btn { display: none !important; }"
    if not show_bg:
        css_with_toggles += "\n.anki-grammar-card { background: transparent !important; box-shadow: none !important; border: none !important; padding: 0 !important; }\n.nightMode .anki-grammar-card { background: transparent !important; box-shadow: none !important; border: none !important; padding: 0 !important; }"
    if not center_horiz:
        css_with_toggles += "\n.sentence-container { text-align: left !important; }\n.card-meta { justify-content: flex-start !important; }\n.action-bar { justify-content: flex-start !important; }\n.anki-grammar-card { align-items: flex-start !important; }\n.anki-card-outer-container { margin: 0 !important; }\n.card { align-items: flex-start !important; }"
    if center_vert:
        css_with_toggles += "\n.card { display: flex !important; flex-direction: column !important; justify-content: flex-start !important; min-height: 100vh !important; padding-top: 26vh !important; }"
    else:
        css_with_toggles += "\n.card { display: flex !important; flex-direction: column !important; justify-content: flex-start !important; min-height: 100vh !important; padding-top: 40px !important; }"
        
    font_size = config.get("font_size", 20)
    css_with_toggles += f"\n.sentence-container {{ font-size: {font_size}px !important; }}"
    
    card_max_width = config.get("card_max_width", 800)
    css_with_toggles += f"\n.anki-card-outer-container {{ max-width: {card_max_width}px !important; }}"

    explanation_align = config.get("explanation_align", "left")
    if explanation_align == "center":
        css_with_toggles += "\n.result-box { text-align: center !important; }\n.correct-banner { text-align: center !important; }\n.explanation-container { text-align: center !important; }\n.explanation-header { text-align: center !important; }\n.hint-box { text-align: center !important; }"
    else:
        css_with_toggles += "\n.result-box { text-align: left !important; }\n.correct-banner { text-align: left !important; }\n.explanation-container { text-align: left !important; }\n.explanation-header { text-align: left !important; }\n.hint-box { text-align: left !important; }"
        
    config_js = f'<script>window.AI_GRAMMAR_CONFIG = {{"auto_flip": {"true" if auto_flip else "false"}, "center_horizontal": {"true" if center_horiz else "false"}, "center_vertical": {"true" if center_vert else "false"}}};</script>\n'
    qfmt_with_config = config_js + FRONT_TEMPLATE
    afmt_with_config = config_js + BACK_TEMPLATE

    # Check if existing
    existing = models.by_name(NOTE_TYPE_NAME)
    if existing:
        # Migrate model if fields are missing (e.g. FrontAudio, BackAudio)
        current_fields = [f['name'] for f in existing['flds']]
        modified = False
        for field_name in FIELDS:
            if field_name not in current_fields:
                fm = models.new_field(field_name)
                models.add_field(existing, fm)
                modified = True
        
        # Always update the templates and CSS to ensure the latest styling/audio-display changes are applied
        t = existing['tmpls'][0]
        t["qfmt"] = qfmt_with_config
        t["afmt"] = afmt_with_config
        existing["css"] = css_with_toggles
        col.models.save(existing)
        return existing
        
    # Create new model
    model = models.new(NOTE_TYPE_NAME)
    
    # Add fields
    for field_name in FIELDS:
        fm = models.new_field(field_name)
        models.add_field(model, fm)
        
    # Add card template
    t = models.new_template("Dropdown Cloze Practice")
    t["qfmt"] = qfmt_with_config
    t["afmt"] = afmt_with_config
    model["css"] = css_with_toggles
    models.add_template(model, t)
    
    # Save to database
    models.add(model)
    col.models.save(model)
    return model
