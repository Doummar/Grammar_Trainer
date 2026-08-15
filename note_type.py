# -*- coding: utf-8 -*-
from aqt import mw

NOTE_TYPE_NAME = "Grammar Trainer"
FIELDS = ["Sentence", "TargetWord", "Options", "Explanation", "GrammarType", "Difficulty", "Language", "FrontAudio", "BackAudio", "Image"]

FRONT_TEMPLATE = """
<div class="anki-card-outer-container">
  <div class="top-right-audio" id="front-audio-container">
    {{FrontAudio}}
  </div>

  <div class="anki-grammar-card {{#Image}}has-image{{/Image}}">
    <div class="card-meta">
      <span class="badge badge-lang">{{Language}}</span>
      <span class="badge badge-diff">{{Difficulty}}</span>
      <span class="badge badge-type">{{GrammarType}}</span>
    </div>

    <div class="sentence-container" id="sentence-container">
      {{Sentence}}
    </div>

    <div id="image-container" class="image-container unrevealed">
      {{Image}}
    </div>

    <div class="action-bar" id="action-bar">
      <button class="check-btn" id="check-btn" onclick="checkAnkiAnswers()">Check Answer</button>
      <button class="hint-btn" id="hint-btn" onclick="showAnkiHint()">Hint</button>
    </div>

    <div id="hint-box" class="hint-box hidden">
      <!-- Hint area -->
    </div>

    <div id="correct-banner-box" class="back-only-container hidden">
    </div>

    <div id="result-box" class="result-box hidden">
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
<div id="language-raw" style="display:none;">{{Language}}</div>

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
  var isBackSide = (document.getElementById("answer") !== null);
  
  // Clear cached selections from sessionStorage if we are on the Front Side (not backside)
  if (!isBackSide) {
    for (var i = 0; i < targets.length; i++) {
      sessionStorage.removeItem(getCardKey() + "-sel-" + i);
    }
  }
  
  if (!addonInstalled) {
    // Hide dropdown controls action bar since add-on is not installed
    var actionBar = document.getElementById("action-bar");
    if (actionBar) {
      actionBar.style.display = "none";
    }
    
    if (isBackSide) {
      // BACK SIDE FALLBACK: show the correct answer filled in and highlighted
      for (var i = 0; i < targets.length; i++) {
        var placeholderSingle = "{" + "{blank" + "}";
        placeholderSingle += "}";
        var placeholderMulti = "{" + "{blank" + (i + 1);
        placeholderMulti += "}}";
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
        placeholderMulti += "}}";
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
    placeholderMulti += "}}";
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
  for (var s = 0; s < targets.length; s++) {
    setupCustomDropdown(s);
  }
  restoreSelectedState();

  // Run blank delay timers if any
  var config = window.AI_GRAMMAR_CONFIG || {};
  var blankTimer = config.blank_timer || 0;
  var hintTimer = config.hint_timer || 0;

  // Auto-open first dropdown if auto_open_dropdown is enabled and no delay timer is active
  if ((!blankTimer || blankTimer <= 0) && !isBackSide) {
    if (config.auto_open_dropdown === true) {
      setTimeout(function() {
        openCustomDropdown(0);
      }, 100);
    }
  }

  if (window.blankInterval) {
    clearInterval(window.blankInterval);
    window.blankInterval = null;
  }

  if (blankTimer > 0 && !isBackSide) {
    var currentBlankCountdown = blankTimer;
    window.blankInterval = setInterval(function() {
      currentBlankCountdown--;
      for (var k = 0; k < targets.length; k++) {
        var cdElem = document.getElementById("timer-countdown-" + k);
        if (cdElem) {
          if (currentBlankCountdown <= 0) {
            cdElem.style.display = "none";
            var selectElem = document.getElementById("blank-select-" + k);
            if (selectElem) {
              selectElem.style.display = "";
              var configObj = window.AI_GRAMMAR_CONFIG || {};
              if (configObj.auto_open_dropdown === true && k === 0) {
                setTimeout(function() {
                  openCustomDropdown(0);
                }, 100);
              }
            }
          } else {
            cdElem.innerHTML = "⏳ " + currentBlankCountdown + "s";
          }
        }
      }
      if (currentBlankCountdown <= 0) {
        clearInterval(window.blankInterval);
        window.blankInterval = null;
      }
    }, 1000);
  }

  // Configure Hint button and run delay timer if any
  var hintBtn = document.getElementById("hint-btn");
  if (hintBtn) {
    var langBadge = document.querySelector(".badge-lang");
    var lang = langBadge ? langBadge.innerText.trim().toLowerCase() : "english";
    var hintText = "Hint";
    if (lang === "danish" || lang === "dansk") hintText = "Hint";
    else if (lang === "german" || lang === "deutsch") hintText = "Hinweis";
    else if (lang === "french" || lang === "français") hintText = "Indice";
    else if (lang === "spanish" || lang === "español") hintText = "Pista";
    else if (lang === "italian" || lang === "italiano") hintText = "Suggerimento";
    else if (lang === "swedish" || lang === "svenska" || lang === "norwegian" || lang === "norsk") hintText = "Hint";

    if (window.hintInterval) {
      clearInterval(window.hintInterval);
      window.hintInterval = null;
    }

    if (hintTimer > 0 && !isBackSide) {
      hintBtn.innerHTML = "⏳ " + hintText + " (" + hintTimer + "s)";
      hintBtn.title = "Click to skip timer and show hint";
      
      var currentHintCountdown = hintTimer;
      window.hintInterval = setInterval(function() {
        currentHintCountdown--;
        if (currentHintCountdown <= 0) {
          hintBtn.innerHTML = hintText;
          hintBtn.title = "";
          clearInterval(window.hintInterval);
          window.hintInterval = null;
        } else {
          hintBtn.innerHTML = "⏳ " + hintText + " (" + currentHintCountdown + "s)";
        }
      }, 1000);
    } else {
      hintBtn.innerHTML = hintText;
      hintBtn.title = "";
    }
  }

  // Hide empty image-container completely
  var imgContainer = document.getElementById("image-container");
  if (imgContainer) {
    var hasImg = imgContainer.querySelector("img") !== null || imgContainer.innerHTML.trim() !== "";
    if (!hasImg) {
      imgContainer.style.display = "none";
    }
  }

  // Image position is handled cleanly using absolute CSS positioning
}

function shuffleDropdownOptions(wrapperEl) {
  if (wrapperEl.disabled) return;
  var now = new Date().getTime();
  if (wrapperEl.lastShuffleTime && (now - wrapperEl.lastShuffleTime < 500)) {
    return;
  }
  wrapperEl.lastShuffleTime = now;
  
  var list = wrapperEl.querySelector(".custom-dropdown-list");
  if (!list || list.children.length < 2) return;
  
  var placeholderOpt = list.children[0];
  var optionEls = Array.prototype.slice.call(list.children, 1);
  
  for (var k = optionEls.length - 1; k > 0; k--) {
    var m = Math.floor(Math.random() * (k + 1));
    var temp = optionEls[k];
    optionEls[k] = optionEls[m];
    optionEls[m] = temp;
  }
  
  while (list.firstChild) {
    list.removeChild(list.firstChild);
  }
  list.appendChild(placeholderOpt);
  for (var j = 0; j < optionEls.length; j++) {
    list.appendChild(optionEls[j]);
  }
}

function skipBlankTimer(index) {
  if (window.blankInterval) {
    clearInterval(window.blankInterval);
    window.blankInterval = null;
  }
  var wrappers = document.querySelectorAll(".dropdown-wrapper");
  for (var k = 0; k < wrappers.length; k++) {
    var cdElem = document.getElementById("timer-countdown-" + k);
    if (cdElem) {
      cdElem.style.display = "none";
    }
    var selectElem = document.getElementById("blank-select-" + k);
    if (selectElem) {
      selectElem.style.display = "";
    }
  }
  var selectElem = document.getElementById("blank-select-" + index);
  if (selectElem) {
    setTimeout(function() {
      openCustomDropdown(index);
    }, 100);
  }
}

function getLocalizedSelectText() {
  return '<span class="dropdown-placeholder-dash"></span>';
}

function shuffleDropdownOptionsOnFocus(select) {
  if (select.disabled || select.value) return;
  shuffleDropdownOptions(select);
}

function createDropdownHTML(index, options) {
  // Fisher-Yates Shuffle
  var shuffled = options.slice();
  for (var i = shuffled.length - 1; i > 0; i--) {
    var j = Math.floor(Math.random() * (i + 1));
    var temp = shuffled[i];
    shuffled[i] = shuffled[j];
    shuffled[j] = temp;
  }
  
  var config = window.AI_GRAMMAR_CONFIG || {};
  var blankTimer = config.blank_timer || 0;
  var isBackSide = (document.getElementById("answer") !== null);
  
  var wrapperStyle = "";
  var timerHtml = "";
  
  if (blankTimer > 0 && !isBackSide) {
    wrapperStyle = ' style="display:none;"';
    timerHtml = '<span class="timer-countdown" id="timer-countdown-' + index + '" onclick="skipBlankTimer(' + index + ')" title="Click to skip timer and open options" style="cursor: pointer;">⏳ ' + blankTimer + 's</span>';
  }
  
  var html = '<span class="dropdown-wrapper" id="dropdown-wrapper-' + index + '">';
  html += timerHtml;
  
  var storedVal = sessionStorage.getItem(getCardKey() + "-sel-" + index) || "";
  var extraClass = "";
  if (isBackSide) {
    var targetWord = _correctAnswers[index];
    var isCorrect = (storedVal === targetWord);
    extraClass = isCorrect ? " correct" : " incorrect";
  }
  
  // Custom dropdown widget: a div, not a native <select>. Native selects can only
  // be force-opened via showPicker(), which requires a fresh user click and will
  // never fire from a timer — this widget has no such restriction.
  html += '<div class="custom-dropdown styled-dropdown' + extraClass + '" id="blank-select-' + index + '"' + wrapperStyle +
          ' tabindex="0" role="combobox" aria-haspopup="listbox" aria-expanded="false"' +
          ' onclick="toggleCustomDropdown(' + index + ')"' +
          ' onkeydown="handleCustomDropdownKeydown(event, ' + index + ')"' +
          ' onfocus="shuffleDropdownOptionsOnFocus(this)">';
  html += '<span class="custom-dropdown-label" id="blank-select-' + index + '-label">' + getLocalizedSelectText() + '</span>';
  html += '<div class="custom-dropdown-list hidden" id="blank-select-' + index + '-list" role="listbox">';
  
  var placeholderSelected = (storedVal === "") ? " is-selected" : "";
  html += '<div class="custom-dropdown-option' + placeholderSelected + '" data-value="" role="option" onclick="event.stopPropagation(); selectCustomDropdownOption(' + index + ', this.getAttribute(`data-value`))">' + getLocalizedSelectText() + '</div>';
  
  for (var i = 0; i < shuffled.length; i++) {
    var optVal = shuffled[i];
    var selCls = (storedVal === optVal) ? " is-selected" : "";
    html += '<div class="custom-dropdown-option' + selCls + '" data-value="' + escapeHtml(optVal) + '" role="option" onclick="event.stopPropagation(); selectCustomDropdownOption(' + index + ', this.getAttribute(`data-value`))">' + escapeHtml(optVal) + '</div>';
  }
  html += '</div>'; // .custom-dropdown-list
  html += '</div>'; // .custom-dropdown
  html += '</span>'; // .dropdown-wrapper
  return html;
}

function setupCustomDropdown(index) {
  var wrapperEl = document.getElementById("blank-select-" + index);
  if (!wrapperEl || wrapperEl._customDropdownReady) return;
  wrapperEl._customDropdownReady = true;
  
  var initialOpt = wrapperEl.querySelector(".custom-dropdown-option.is-selected");
  var _value = initialOpt ? initialOpt.getAttribute("data-value") : "";
  var _disabled = false;
  
  Object.defineProperty(wrapperEl, "value", {
    get: function() { return _value; },
    set: function(v) {
      _value = v || "";
      var label = document.getElementById("blank-select-" + index + "-label");
      var opts = wrapperEl.querySelectorAll(".custom-dropdown-option");
      var matchedText = getLocalizedSelectText();
      for (var i = 0; i < opts.length; i++) {
        var isMatch = (opts[i].getAttribute("data-value") === _value);
        opts[i].classList.toggle("is-selected", isMatch);
        if (isMatch) matchedText = opts[i].innerHTML;
      }
      if (label) label.innerHTML = matchedText;
    },
    configurable: true
  });
  
  Object.defineProperty(wrapperEl, "disabled", {
    get: function() { return _disabled; },
    set: function(v) {
      _disabled = !!v;
      wrapperEl.classList.toggle("dropdown-disabled", _disabled);
      wrapperEl.setAttribute("tabindex", _disabled ? "-1" : "0");
      wrapperEl.setAttribute("aria-disabled", _disabled ? "true" : "false");
      if (_disabled) closeCustomDropdown(index);
    },
    configurable: true
  });
  
  if (isBackSideNow()) {
    wrapperEl.disabled = true;
  }
}

function isBackSideNow() {
  return document.getElementById("answer") !== null;
}

function closeAllCustomDropdownsExcept(exceptIndex) {
  var lists = document.querySelectorAll(".custom-dropdown-list");
  for (var i = 0; i < lists.length; i++) {
    var wrapperId = lists[i].id.slice(0, -("-list".length));
    if (exceptIndex !== null && exceptIndex !== undefined && wrapperId === "blank-select-" + exceptIndex) continue;
    if (!lists[i].classList.contains("hidden")) {
      lists[i].classList.add("hidden");
      var owner = document.getElementById(wrapperId);
      if (owner) owner.setAttribute("aria-expanded", "false");
    }
  }
}

function openCustomDropdown(index) {
  var wrapperEl = document.getElementById("blank-select-" + index);
  if (!wrapperEl || wrapperEl.disabled) return;
  closeAllCustomDropdownsExcept(index);
  var list = document.getElementById("blank-select-" + index + "-list");
  if (list) list.classList.remove("hidden");
  wrapperEl.setAttribute("aria-expanded", "true");
  wrapperEl.focus();
}

function closeCustomDropdown(index) {
  var list = document.getElementById("blank-select-" + index + "-list");
  if (list) {
    list.classList.add("hidden");
    var stale = list.querySelector(".kbd-highlight");
    if (stale) stale.classList.remove("kbd-highlight");
  }
  var wrapperEl = document.getElementById("blank-select-" + index);
  if (wrapperEl) wrapperEl.setAttribute("aria-expanded", "false");
}

function toggleCustomDropdown(index) {
  var wrapperEl = document.getElementById("blank-select-" + index);
  if (!wrapperEl || wrapperEl.disabled) return;
  var list = document.getElementById("blank-select-" + index + "-list");
  if (list && !list.classList.contains("hidden")) {
    closeCustomDropdown(index);
  } else {
    openCustomDropdown(index);
  }
}

function selectCustomDropdownOption(index, value) {
  var wrapperEl = document.getElementById("blank-select-" + index);
  if (!wrapperEl || wrapperEl.disabled) return;
  wrapperEl.value = value;
  closeCustomDropdown(index);
  dropdownChanged(index);
}

function handleCustomDropdownKeydown(event, index) {
  var wrapperEl = document.getElementById("blank-select-" + index);
  if (!wrapperEl || wrapperEl.disabled) return;
  var list = document.getElementById("blank-select-" + index + "-list");
  var isOpen = list && !list.classList.contains("hidden");
  var key = event.key;
  
  if (!isOpen) {
    var shouldOpenLocally = (key === " " || key === "ArrowDown" || key === "ArrowUp") ||
                             (key === "Enter" && !wrapperEl.value);
    if (shouldOpenLocally) {
      event.preventDefault();
      event.stopPropagation();
      openCustomDropdown(index);
    }
    return;
  }
  
  var opts = Array.prototype.slice.call(wrapperEl.querySelectorAll(".custom-dropdown-option"));
  var highlighted = wrapperEl.querySelector(".custom-dropdown-option.kbd-highlight");
  var curIdx = highlighted ? opts.indexOf(highlighted) : -1;
  if (curIdx === -1) {
    for (var i = 0; i < opts.length; i++) {
      if (opts[i].classList.contains("is-selected")) { curIdx = i; break; }
    }
  }
  
  if (key === "ArrowDown") {
    event.preventDefault();
    event.stopPropagation();
    if (highlighted) highlighted.classList.remove("kbd-highlight");
    curIdx = Math.min(curIdx + 1, opts.length - 1);
    opts[curIdx].classList.add("kbd-highlight");
    opts[curIdx].scrollIntoView({ block: "nearest" });
  } else if (key === "ArrowUp") {
    event.preventDefault();
    event.stopPropagation();
    if (highlighted) highlighted.classList.remove("kbd-highlight");
    curIdx = Math.max(curIdx - 1, 0);
    opts[curIdx].classList.add("kbd-highlight");
    opts[curIdx].scrollIntoView({ block: "nearest" });
  } else if (key === "Enter" || key === " ") {
    event.preventDefault();
    event.stopPropagation();
    var target = highlighted || opts[curIdx] || opts[0];
    if (target) selectCustomDropdownOption(index, target.getAttribute("data-value"));
  } else if (/^[1-9]$/.test(key) && (window.AI_GRAMMAR_CONFIG || {}).keyboard_shortcuts === true) {
    var n = parseInt(key, 10);
    if (opts[n]) {
      event.preventDefault();
      event.stopPropagation();
      selectCustomDropdownOption(index, opts[n].getAttribute("data-value"));
    }
  } else if (key === "Escape") {
    event.preventDefault();
    event.stopPropagation();
    closeCustomDropdown(index);
  }
}

document.addEventListener("keydown", function(event) {
  var config = window.AI_GRAMMAR_CONFIG || {};
  if (config.keyboard_shortcuts !== true) return;
  if (typeof isBackSideNow === "function" && isBackSideNow()) return;
  if (event.target && (event.target.tagName === "INPUT" || event.target.tagName === "TEXTAREA")) return;
  
  // If any dropdown is already open, its own keydown handler deals with digits/Enter/etc.
  if (document.querySelector(".custom-dropdown-list:not(.hidden)")) return;
  
  var key = event.key;
  if (/^[1-9]$/.test(key)) {
    var wrappers = document.querySelectorAll(".custom-dropdown");
    for (var i = 0; i < wrappers.length; i++) {
      var idxMatch = wrappers[i].id.match(/^blank-select-(\\d+)$/);
      if (!idxMatch) continue;
      if (wrappers[i].disabled || wrappers[i].value) continue;
      event.preventDefault();
      openCustomDropdown(parseInt(idxMatch[1], 10));
      break;
    }
  } else if (key === "Enter") {
    var checkBtn = document.getElementById("check-btn");
    if (checkBtn && !checkBtn.disabled) {
      event.preventDefault();
      checkBtn.click();
    }
  }
});

document.addEventListener("click", function(event) {
  var openLists = document.querySelectorAll(".custom-dropdown-list");
  for (var i = 0; i < openLists.length; i++) {
    if (openLists[i].classList.contains("hidden")) continue;
    var wrapperId = openLists[i].id.slice(0, -("-list".length));
    var wrapperEl = document.getElementById(wrapperId);
    if (wrapperEl && !wrapperEl.contains(event.target)) {
      closeCustomDropdown(wrapperId.replace("blank-select-", ""));
    }
  }
});

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
  for (var i = 0; i < _correctAnswers.length; i++) {
    var select = document.getElementById("blank-select-" + i);
    if (!select) continue;
    
    var selected = select.value;
    var correct = _correctAnswers[i];
    
    select.disabled = true;
    
    if (selected.toLowerCase() === correct.toLowerCase()) {
      select.classList.add("correct");
      select.classList.remove("incorrect");
    } else {
      select.classList.add("incorrect");
      select.classList.remove("correct");
      
      // AUTO-FILL UNANSWERED OR WRONG BLANK
      if (!selected) {
        select.value = correct;
      }
    }
  }
  
  var resultBox = document.getElementById("result-box");
  if (resultBox) {
    resultBox.classList.remove("hidden");
  }
  
  var checkBtn = document.getElementById("check-btn");
  if (checkBtn) checkBtn.disabled = true;
}

function showAnkiHint() {
  if (window.hintInterval) {
    clearInterval(window.hintInterval);
    window.hintInterval = null;
    var hintBtn = document.getElementById("hint-btn");
    if (hintBtn) {
      var langBadge = document.querySelector(".badge-lang");
      var lang = langBadge ? langBadge.innerText.trim().toLowerCase() : "english";
      var hintText = "Hint";
      if (lang === "danish" || lang === "dansk") hintText = "Hint";
      else if (lang === "german" || lang === "deutsch") hintText = "Hinweis";
      else if (lang === "french" || lang === "français") hintText = "Indice";
      else if (lang === "spanish" || lang === "español") hintText = "Pista";
      else if (lang === "italian" || lang === "italiano") hintText = "Suggerimento";
      else if (lang === "swedish" || lang === "svenska" || lang === "norwegian" || lang === "norsk") hintText = "Hint";
      
      hintBtn.innerHTML = hintText;
      hintBtn.title = "";
    }
  }
  var hintBox = document.getElementById("hint-box");
  if (hintBox) {
    hintBox.classList.toggle("hidden");
    
    var langBadge = document.querySelector(".badge-lang");
    var lang = langBadge ? langBadge.innerText.trim().toLowerCase() : "english";
    
    var firstChar = _correctAnswers[0].charAt(0).toUpperCase();
    var length = _correctAnswers[0].length;
    
    var hintLabel = "Hint";
    var hintText = "";
    
    if (lang === "danish" || lang === "dansk") {
      hintLabel = "Ledetråd";
      hintText = "Det rigtige ord starter med '" + firstChar + "' og består af " + length + " bogstaver.";
    } else if (lang === "german" || lang === "deutsch") {
      hintLabel = "Hinweis";
      hintText = "Der richtige Begriff beginnt mit '" + firstChar + "' und besteht aus " + length + " Buchstaben.";
    } else if (lang === "french" || lang === "français") {
      hintLabel = "Indice";
      hintText = "Le terme correct commence par '" + firstChar + "' et se compose de " + length + " lettres.";
    } else if (lang === "spanish" || lang === "español") {
      hintLabel = "Pista";
      hintText = "El término correcto comienza con '" + firstChar + "' y consta de " + length + " letras.";
    } else if (lang === "italian" || lang === "italiano") {
      hintLabel = "Suggerimento";
      hintText = "Il termine corretto inizia con '" + firstChar + "' e consiste di " + length + " lettere.";
    } else if (lang === "swedish" || lang === "svenska") {
      hintLabel = "Hint";
      hintText = "Det rätta ordet börjar med '" + firstChar + "' og består af " + length + " bokstäver.";
    } else if (lang === "norwegian" || lang === "norsk") {
      hintLabel = "Hint";
      hintText = "Det riktige ordet starter med '" + firstChar + "' og består av " + length + " bokstaver.";
    } else {
      hintLabel = "Hint";
      hintText = "The correct term starts with '" + firstChar + "' and consists of " + length + " letters.";
    }
    
    hintBox.innerHTML = "<strong>" + hintLabel + ":</strong> " + hintText;
  }
}

function formatAnkiExplanation() {
  var explContainer = document.querySelector(".explanation-body");
  if (!explContainer) return;
  
  var rawText = explContainer.innerHTML || "";
  if (!rawText) return;
  
  var langEl = document.getElementById("language-raw");
  var lang = langEl ? langEl.innerText.trim().toLowerCase() : "english";
  
  // Localization dictionary for UI fallback labels inside explanation block
  var labelsDict = {
    danish: { choice: "Dit valg", correct: "Korrekt svar", isCorrect: "er korrekt.", isCorrectAnswer: "er det korrekte svar." },
    dansk: { choice: "Dit valg", correct: "Korrekt svar", isCorrect: "er korrekt.", isCorrectAnswer: "er det korrekte svar." },
    german: { choice: "Deine Wahl", correct: "Richtige Antwort", isCorrect: "ist richtig.", isCorrectAnswer: "ist die richtige Antwort." },
    deutsch: { choice: "Deine Wahl", correct: "Richtige Antwort", isCorrect: "ist richtig.", isCorrectAnswer: "ist die richtige Antwort." },
    spanish: { choice: "Tu elección", correct: "Respuesta correcta", isCorrect: "es correcto.", isCorrectAnswer: "es la respuesta correcta." },
    español: { choice: "Tu elección", correct: "Respuesta correcta", isCorrect: "es correcto.", isCorrectAnswer: "es la respuesta correcta." },
    french: { choice: "Votre choix", correct: "Réponse correcte", isCorrect: "est correct.", isCorrectAnswer: "est la réponse correcte." },
    français: { choice: "Votre choix", correct: "Réponse correcte", isCorrect: "est correct.", isCorrectAnswer: "est la réponse correcte." },
    italian: { choice: "La tua scelta", correct: "Risposta corretta", isCorrect: "è corretto.", isCorrectAnswer: "è la risposta corretta." },
    italiano: { choice: "La tua scelta", correct: "Risposta corretta", isCorrect: "è corretto.", isCorrectAnswer: "è la risposta corretta." },
    swedish: { choice: "Ditt val", correct: "Rätt svar", isCorrect: "är rätt.", isCorrectAnswer: "är det rätta svaret." },
    svenska: { choice: "Ditt val", correct: "Rätt svar", isCorrect: "är rätt.", isCorrectAnswer: "är det rätta svaret." },
    norwegian: { choice: "Ditt valg", correct: "Riktig svar", isCorrect: "er riktig.", isCorrectAnswer: "er det riktige svaret." },
    norsk: { choice: "Ditt valg", correct: "Riktig svar", isCorrect: "er riktig.", isCorrectAnswer: "er det riktige svaret." },
    english: { choice: "Your choice", correct: "Correct answer", isCorrect: "is correct.", isCorrectAnswer: "is the correct answer." }
  };
  
  var currentLabels = labelsDict[lang] || labelsDict.english;
  
  var jsonMatches = [];
  var pos = 0;
  
  // Robust matching to extract { ... } JSON blocks
  while (true) {
    var startIdx = rawText.indexOf('{', pos);
    if (startIdx === -1) break;
    
    var braceCount = 1;
    var endIdx = -1;
    for (var i = startIdx + 1; i < rawText.length; i++) {
      if (rawText[i] === '{') {
        braceCount++;
      } else if (rawText[i] === '}') {
        braceCount--;
        if (braceCount === 0) {
          endIdx = i;
          break;
        }
      }
    }
    
    if (endIdx !== -1) {
      var jsonStr = rawText.substring(startIdx, endIdx + 1);
      
      // Decode HTML entities (e.g. &quot; to ")
      var tempDiv = document.createElement("div");
      tempDiv.innerHTML = jsonStr;
      var decoded = tempDiv.innerText || tempDiv.textContent || jsonStr;
      
      try {
        decoded = decoded.trim().replace(/^['"\\s]+|['"\\s]+$/g, "");
        var parsed = JSON.parse(decoded);
        if (parsed && typeof parsed === "object") {
          jsonMatches.push(parsed);
        }
      } catch (e) {
        try {
          var parsedOriginal = JSON.parse(jsonStr);
          if (parsedOriginal && typeof parsedOriginal === "object") {
            jsonMatches.push(parsedOriginal);
          }
        } catch (err) {}
      }
      pos = endIdx + 1;
    } else {
      pos = startIdx + 1;
    }
  }

  // Fallback single clean
  if (jsonMatches.length === 0) {
    var tempDivSingle = document.createElement("div");
    tempDivSingle.innerHTML = rawText;
    var decodedSingle = tempDivSingle.innerText || tempDivSingle.textContent || "";
    decodedSingle = decodedSingle.trim().replace(/^['"\\s]+|['"\\s]+$/g, "");
    try {
      var parsedSingle = JSON.parse(decodedSingle);
      if (parsedSingle && typeof parsedSingle === "object") {
        jsonMatches.push(parsedSingle);
      }
    } catch (e) {}
  }
  
  if (jsonMatches.length > 0) {
    var html = "";
    
    for (var i = 0; i < _correctAnswers.length; i++) {
      var correct = _correctAnswers[i] || "";
      var selected = sessionStorage.getItem(getCardKey() + "-sel-" + i) || "";
      
      var parsedBlock = jsonMatches[i] || jsonMatches[0];
      if (!parsedBlock) continue;
      
      var findKey = function(opt) {
        if (!opt) return "";
        var keys = Object.keys(parsedBlock);
        for (var j = 0; j < keys.length; j++) {
          if (keys[j].toLowerCase() === opt.toLowerCase()) {
            return keys[j];
          }
        }
        return opt;
      };
      
      var selectedKey = findKey(selected);
      var correctKey = findKey(correct);
      
      var selectedExpl = selectedKey ? parsedBlock[selectedKey] : "";
      var correctExpl = correctKey ? parsedBlock[correctKey] : "";
      
      var isCorrect = (selected.toLowerCase() === correct.toLowerCase());
      
      var sectionHtml = "";
      if (_correctAnswers.length > 1) {
        sectionHtml += '<div style="font-weight: bold; color: #8e8e93; margin-bottom: 5px; font-size: 0.85em; text-transform: uppercase;">Blank ' + (i + 1) + ' ("' + escapeHtml(correct) + '"):</div>';
      }
      
      if (!selected) {
        sectionHtml += '<div class="explanation-item" style="color: #34C759; margin-bottom: 12px; font-weight: 500;">' + (correctExpl ? escapeHtml(correctExpl) : '<strong>' + escapeHtml(correct) + '</strong> ' + currentLabels.isCorrectAnswer) + '</div>';
      } else if (isCorrect) {
        sectionHtml += '<div class="explanation-item" style="color: #34C759; margin-bottom: 12px; font-weight: 500;">' + (correctExpl ? escapeHtml(correctExpl) : '<strong>' + escapeHtml(correct) + '</strong> ' + currentLabels.isCorrect) + '</div>';
      } else {
        sectionHtml += '<div class="explanation-item" style="color: #FF5F57; margin-bottom: 8px;"><strong>' + currentLabels.choice + ' (' + escapeHtml(selected) + '):</strong> ' + (selectedExpl ? escapeHtml(selectedExpl) : 'Incorrect.') + '</div>';
        sectionHtml += '<div class="explanation-item" style="color: #34C759; margin-bottom: 12px; font-weight: 500; border-top: 1px dashed #e2e8f0; padding-top: 8px; margin-top: 8px;"><strong>' + currentLabels.correct + ' (' + escapeHtml(correct) + '):</strong> ' + (correctExpl ? escapeHtml(correctExpl) : 'Correct.') + '</div>';
      }

      // SLA metadata rendering
      var slaHtml = "";
      var lemma = parsedBlock["_lemma"] || "";
      var partOfSpeech = parsedBlock["_partOfSpeech"] || "";
      var grammarPoint = parsedBlock["_grammarPoint"] || "";
      var frequency = parsedBlock["_frequency"] || "";
      var register = parsedBlock["_register"] || "";
      var collocations = parsedBlock["_collocations"] || [];
      var memoryTip = parsedBlock["_memoryTip"] || "";
      var commonMistake = parsedBlock["_commonMistake"] || "";
      
      if (lemma || partOfSpeech || grammarPoint || frequency || register || (collocations && collocations.length > 0) || memoryTip || commonMistake) {
        slaHtml += '<div class="sla-container">';
        
        // Badges row
        slaHtml += '<div class="sla-badges-row">';
        if (lemma) {
          slaHtml += '<span class="sla-badge sla-badge-base">Base: <strong>' + escapeHtml(lemma) + '</strong></span>';
        }
        if (partOfSpeech) {
          slaHtml += '<span class="sla-badge sla-badge-pos">POS: ' + escapeHtml(partOfSpeech) + '</span>';
        }
        if (grammarPoint) {
          slaHtml += '<span class="sla-badge sla-badge-grammar">Grammar: ' + escapeHtml(grammarPoint) + '</span>';
        }
        if (frequency) {
          slaHtml += '<span class="sla-badge sla-badge-muted">Freq: ' + escapeHtml(frequency) + '</span>';
        }
        if (register) {
          slaHtml += '<span class="sla-badge sla-badge-muted">Reg: ' + escapeHtml(register) + '</span>';
        }
        slaHtml += '</div>';
        
        // Collocations
        if (collocations && collocations.length > 0) {
          slaHtml += '<div class="sla-collocations-row">';
          slaHtml += '<span class="sla-collocations-label">Collocations:</span>';
          for (var k = 0; k < collocations.length; k++) {
            slaHtml += '<span class="sla-collocation-chip">' + escapeHtml(collocations[k]) + '</span>';
          }
          slaHtml += '</div>';
        }
        
        // Memory tip
        if (memoryTip) {
          slaHtml += '<div class="sla-tip-box">';
          slaHtml += '<span>💡</span>';
          slaHtml += '<div><span class="sla-tip-label">Memory Hook / Tip</span><p class="sla-tip-text">' + escapeHtml(memoryTip) + '</p></div>';
          slaHtml += '</div>';
        }
        
        // Common mistake
        if (commonMistake) {
          slaHtml += '<div class="sla-mistake-box">';
          slaHtml += '<span>⚠️</span>';
          slaHtml += '<div><span class="sla-mistake-label">Common Learner Mistake</span><p class="sla-mistake-text">' + escapeHtml(commonMistake) + '</p></div>';
          slaHtml += '</div>';
        }
        
        slaHtml += '</div>';
      }
      
      sectionHtml += slaHtml;
      
      var boxClass = (isCorrect || !selected) ? "explanation-block-correct" : "explanation-block";
      html += '<div class="' + boxClass + '">' + sectionHtml + '</div>';
    }
    
    // Render high-level CEFR alignment details on card if available
    var firstBlock = jsonMatches[0] || {};
    var cefrReason = firstBlock["_cefrReason"] || "";
    if (cefrReason) {
      html += '<div class="cefr-box">';
      html += '<span class="cefr-label">CEFR Level Alignment Explanation:</span>';
      html += escapeHtml(cefrReason);
      html += '</div>';
    }
    
    explContainer.innerHTML = html;
  }
}

function revealAnkiAnswers() {
  initDropdowns();
  var addonInstalled = (window.AI_GRAMMAR_ADDON_INSTALLED === true);
  if (addonInstalled) {
    checkAnkiAnswers();
  }
  
  // Format the explanation body dynamically if it is JSON
  formatAnkiExplanation();
  
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
  
  // Reveal the image container on the back side
  var imgContainer = document.getElementById("image-container");
  if (imgContainer) {
    var hasImg = imgContainer.querySelector("img") !== null || imgContainer.innerHTML.trim() !== "";
    if (hasImg) {
      imgContainer.classList.remove("unrevealed");
    } else {
      imgContainer.style.display = "none";
    }
  }

  // Add revealed class to the card so that layout shifts/padding for image are only active on the back card
  var cardEl = document.querySelector(".anki-grammar-card");
  if (cardEl) {
    cardEl.classList.add("revealed");
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
  justify-content: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 24px;
  z-index: 10;
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

.dropdown-wrapper {
  position: relative;
  display: inline-block;
  min-width: 112px;
}

.styled-dropdown {
  box-sizing: border-box;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  position: relative;
  text-align:         center;
  font-family: inherit;
  font-size:   inherit;
  line-height: 1.2;
  font-weight: bold;
  padding:     4px 10px;
  border-radius: 6px;
  border: 2px solid rgba(128,128,128,0.4);
  background:  transparent;
  color:       inherit;
  margin: 0 3px;
  cursor: pointer;
  vertical-align: middle;
  min-width: 112px;
  user-select: none;
  transition: all 0.15s ease;
}

.styled-dropdown:focus {
  outline: none;
  border-color: #3b82f6 !important;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.3) !important;
}

.styled-dropdown.dropdown-disabled {
  opacity: 1;
  color:   inherit;
  background: transparent;
  cursor: default;
}

.custom-dropdown-list {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  width: max-content;
  min-width: 100%;
  background: #ffffff;
  color: #1e293b;
  border: 1px solid rgba(128,128,128,0.35);
  border-radius: 6px;
  box-shadow: 0 6px 16px rgba(0,0,0,0.25);
  z-index: 1000;
  text-align: center;
  font-weight: normal;
  padding: 4px 0;
}

.custom-dropdown-list.hidden {
  display: none;
}

.custom-dropdown-option {
  padding: 6px 14px;
  cursor: pointer;
  white-space: nowrap;
  color: inherit;
}

.dropdown-placeholder-dash {
  display: inline-block;
  width: 18px;
  height: 2px;
  background-color: currentColor;
  border-radius: 1px;
  vertical-align: middle;
}

.custom-dropdown-option:hover,
.custom-dropdown-option.kbd-highlight {
  background-color: rgba(59, 130, 246, 0.18);
}

.custom-dropdown-option.is-selected {
  font-weight: bold;
}

.nightMode .styled-dropdown {
  border-color: rgba(255,255,255,0.45);
  color: #f1f5f9;
}

.nightMode .custom-dropdown-list {
  background: #1e293b;
  color: #f1f5f9;
  border-color: rgba(255,255,255,0.3);
}

/* Optional feedback states — apply these classes once you know
   whether the chosen answer was right or wrong. Border only; text keeps
   its normal colour. */
.styled-dropdown.correct   { border-color: #22c55e !important; }
.styled-dropdown.incorrect { border-color: #ef4444 !important; }

.timer-countdown {
  box-sizing: border-box;
  font-size: inherit;
  line-height: 1.2;
  padding: 4px 8px;
  border-radius: 6px;
  border: 2px solid #cbd5e1;
  background-color: #f1f5f9;
  color: #64748b;
  margin: 0 3px;
  font-weight: bold;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 112px;
  vertical-align: middle;
  user-select: none;
  cursor: pointer;
  transition: all 0.15s ease-in-out;
}

.timer-countdown:hover {
  background-color: #e2e8f0;
  border-color: #94a3b8;
  color: #1e293b;
}

.nightMode .timer-countdown {
  border-color: #475569;
  background-color: #1e293b;
  color: #94a3b8;
}

.nightMode .timer-countdown:hover {
  background-color: #334155;
  border-color: #64748b;
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

.explanation-block {
  padding: 10px;
  background-color: transparent !important;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin-bottom: 10px;
  color: #1e293b;
}

.nightMode .explanation-block {
  background-color: transparent !important;
  border-color: #334155;
  color: #f1f5f9;
}

.explanation-block-correct {
  padding: 10px;
  background-color: transparent !important;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin-bottom: 10px;
  color: #1e293b;
}

.nightMode .explanation-block-correct {
  background-color: transparent !important;
  border-color: #334155;
  color: #f1f5f9;
}

.sla-container {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e5e5ea;
  font-size: 12px;
  color: #48484a;
  text-align: left;
}

.nightMode .sla-container {
  border-top-color: #334155;
  color: #cbd5e1;
}

.sla-badges-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.sla-badge {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
}

.sla-badge-base {
  font-family: monospace;
  background-color: #f2f2f7;
  color: #1c1c1e;
}

.nightMode .sla-badge-base {
  background-color: #334155;
  color: #f1f5f9;
}

.sla-badge-pos {
  font-weight: 600;
  background-color: #e8e6ff;
  color: #5856d6;
}

.nightMode .sla-badge-pos {
  background-color: #3730a3;
  color: #e0e7ff;
}

.sla-badge-grammar {
  font-weight: 600;
  background-color: #e5f1ff;
  color: #007aff;
}

.nightMode .sla-badge-grammar {
  background-color: #1e3a5f;
  color: #7cc4ff;
}

.sla-badge-muted {
  background-color: #f2f2f7;
  color: #8e8e93;
}

.nightMode .sla-badge-muted {
  background-color: #334155;
  color: #94a3b8;
}

.sla-collocations-row {
  margin-bottom: 8px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
}

.sla-collocations-label {
  font-weight: 600;
  font-size: 11px;
  color: #8e8e93;
  text-transform: uppercase;
}

.nightMode .sla-collocations-label {
  color: #94a3b8;
}

.sla-collocation-chip {
  padding: 1px 6px;
  background-color: #e5f1ff;
  color: #007aff;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 500;
}

.nightMode .sla-collocation-chip {
  background-color: #1e3a5f;
  color: #7cc4ff;
}

.sla-tip-box {
  margin-bottom: 8px;
  padding: 8px;
  background-color: #fff9e6;
  border: 1px solid #ffe0b2;
  border-radius: 8px;
  display: flex;
  gap: 6px;
}

.nightMode .sla-tip-box {
  background-color: #3f2f08;
  border-color: #7a5a13;
}

.sla-tip-label {
  font-weight: bold;
  color: #b78103;
  display: block;
  font-size: 10px;
  text-transform: uppercase;
}

.nightMode .sla-tip-label {
  color: #eab84f;
}

.sla-tip-text {
  margin: 2px 0 0 0;
  font-size: 11px;
  color: #5c4308;
}

.nightMode .sla-tip-text {
  color: #f0d999;
}

.sla-mistake-box {
  margin-bottom: 8px;
  padding: 8px;
  background-color: #fff5f5;
  border: 1px solid #ffd2d2;
  border-radius: 8px;
  display: flex;
  gap: 6px;
}

.nightMode .sla-mistake-box {
  background-color: #3f1f1f;
  border-color: #7a3a3a;
}

.sla-mistake-label {
  font-weight: bold;
  color: #c93b3b;
  display: block;
  font-size: 10px;
  text-transform: uppercase;
}

.nightMode .sla-mistake-label {
  color: #f19999;
}

.sla-mistake-text {
  margin: 2px 0 0 0;
  font-size: 11px;
  color: #7f2424;
}

.nightMode .sla-mistake-text {
  color: #f5c2c2;
}

.cefr-box {
  margin-top: 12px;
  padding: 8px;
  background-color: #f8f8fa;
  border: 1px solid #e5e5ea;
  border-radius: 8px;
  font-size: 11px;
  color: #8e8e93;
  text-align: left;
  width: 100%;
  box-sizing: border-box;
}

.nightMode .cefr-box {
  background-color: #1e293b;
  border-color: #334155;
  color: #94a3b8;
}

.cefr-label {
  font-weight: bold;
  color: #1c1c1e;
  display: block;
  font-size: 9px;
  text-transform: uppercase;
  margin-bottom: 3px;
}

.nightMode .cefr-label {
  color: #f1f5f9;
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

.image-container {
  margin-top: 20px;
  margin-bottom: 20px;
  text-align: center;
  transition: opacity 0.5s ease-out, transform 0.5s ease-out;
}

.image-container.unrevealed {
  opacity: 0;
  pointer-events: none;
  transform: translateY(24px) scale(0.96);
}

.image-container img {
  max-width: 100%;
  max-height: 240px;
  height: auto;
  border-radius: 8px;
  object-fit: contain;
}

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
        css_with_toggles += "\n.anki-grammar-card.has-image .image-container { position: absolute !important; bottom: calc(100% + 16px) !important; left: 0 !important; right: 0 !important; height: 220px !important; margin: 0 !important; display: flex !important; justify-content: center !important; align-items: center !important; }"
    else:
        css_with_toggles += "\n.card { display: flex !important; flex-direction: column !important; justify-content: flex-start !important; min-height: 100vh !important; padding-top: 40px !important; }"
        css_with_toggles += "\n.anki-grammar-card.has-image .image-container { position: absolute !important; top: calc(100% + 16px) !important; left: 0 !important; right: 0 !important; height: 220px !important; margin: 0 !important; display: flex !important; justify-content: center !important; align-items: center !important; }"
        
    font_size = config.get("font_size", 20)
    css_with_toggles += f"\n.sentence-container {{ font-size: {font_size}px !important; }}"
    
    card_max_width = config.get("card_max_width", 800)
    css_with_toggles += f"\n.anki-card-outer-container {{ max-width: {card_max_width}px !important; }}"

    explanation_align = config.get("explanation_align", "left")
    if explanation_align == "center":
        css_with_toggles += "\n.result-box { text-align: center !important; }\n.correct-banner { text-align: center !important; }\n.explanation-container { text-align: center !important; }\n.explanation-header { text-align: center !important; }\n.hint-box { text-align: center !important; }"
    else:
        css_with_toggles += "\n.result-box { text-align: left !important; }\n.correct-banner { text-align: left !important; }\n.explanation-container { text-align: left !important; }\n.explanation-header { text-align: left !important; }\n.hint-box { text-align: left !important; }"
        
    blank_timer = config.get("blank_timer", 0)
    hint_timer = config.get("hint_timer", 0)
    auto_open = "true" if config.get("auto_open_dropdown", False) else "false"
    keyboard_shortcuts = "true" if config.get("keyboard_shortcuts", False) else "false"
    config_js = f'<script>window.AI_GRAMMAR_CONFIG = {{"auto_flip": {"true" if auto_flip else "false"}, "center_horizontal": {"true" if center_horiz else "false"}, "center_vertical": {"true" if center_vert else "false"}, "blank_timer": {blank_timer}, "hint_timer": {hint_timer}, "auto_open_dropdown": {auto_open}, "keyboard_shortcuts": {keyboard_shortcuts}}};</script>\n'
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
