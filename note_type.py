# -*- coding: utf-8 -*-
from aqt import mw

NOTE_TYPE_NAME = "Grammar Trainer"
FIELDS = ["Sentence", "TargetWord", "Options", "Explanation", "GrammarType", "Difficulty", "Language", "FrontAudio", "BackAudio", "Image", "Translation", "Extra"]

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

    <div class="sentence-container" id="sentence-container" dir="auto">
      {{Sentence}}
    </div>

    <div id="image-container" class="image-container unrevealed">
      {{Image}}
    </div>

    <div class="action-bar" id="action-bar">
      <button class="check-btn" id="check-btn" onclick="checkAnkiAnswers()">Check Answer</button>
    </div>

    <div id="result-box" class="result-box hidden">
      <div class="explanation-container">
        <div class="explanation-body">
          {{Explanation}}
        </div>
        <div class="info-toggle-row hidden" id="info-toggle-row"></div>
      </div>
    </div>

    <div id="extra-container" class="extra-container hidden"></div>

    <div id="translation-panel" class="info-panel hidden"></div>
  </div>
</div>

<div id="target-raw" style="display:none;">{{TargetWord}}</div>
<div id="options-raw" style="display:none;">{{Options}}</div>
<div id="language-raw" style="display:none;">{{Language}}</div>
<div id="translation-raw" style="display:none;">{{Translation}}</div>
<div id="extra-raw" style="display:none;">{{Extra}}</div>

<script>
// Self-contained card controller: pure HTML/CSS/JS, no Python/add-on
// dependency at study time. Runs the same way on Anki Desktop, AnkiMobile
// and AnkiDroid — the Python add-on is only needed to *generate* cards.
var _correctAnswers = [];

// sessionStorage can throw, or simply be unavailable, in some restricted
// WebViews. Every read/write goes through these helpers so a storage
// failure degrades to an in-memory fallback for this viewing instead of
// breaking the card.
var _gtMemStore = {};
function safeStorageGet(key) {
  try { return sessionStorage.getItem(key); } catch (e) { return (key in _gtMemStore) ? _gtMemStore[key] : null; }
}
function safeStorageSet(key, val) {
  try { sessionStorage.setItem(key, val); } catch (e) { _gtMemStore[key] = val; }
}

// Holds whatever selection was already sitting in storage for this card at
// the moment *this page* started loading, captured once (see initDropdowns)
// before anything on this page can be clicked. isBackSide===true rendering
// reads the selection from here rather than from storage directly, so a
// user's own fresh selection on this page - always written straight to
// storage by dropdownChanged() - can never be raced by the capture step.
var _gtCarriedSelections = null;
var _gtCaptureDone = false;

function initDropdowns() {
  var sentenceArea = document.getElementById("sentence-container");
  var targetEl = document.getElementById("target-raw");
  var optionsEl = document.getElementById("options-raw");
  if (!sentenceArea || !targetEl || !optionsEl) return;

  var targetRaw = targetEl.innerHTML.trim();
  var optionsRaw = optionsEl.innerHTML.trim();
  if (!targetRaw || !optionsRaw) return;

  // Parse targets and options group
  var targets = targetRaw.split("||").map(function(s) { return s.trim(); });
  var optionsGroup = optionsRaw.split("||").map(function(s) { return s.trim().split("|").map(function(o) { return o.trim(); }); });
  _correctAnswers = targets;

  // {{FrontSide}} re-embeds this entire <script> into the back template, so
  // this function legitimately runs more than once per card: first as part
  // of the reused front HTML — at a point where back-only markup such as
  // #answer may not exist in the DOM yet, so this pass can look like the
  // front even when it isn't — and then for real via the back template's
  // own trailing script. To stay correct no matter how many times or in
  // what DOM state this runs, every call rebuilds the blanks from a
  // pristine, untouched copy of the sentence's token text (cached once on
  // the element itself) instead of re-parsing whatever an earlier call
  // already rendered. That makes the whole function idempotent: whichever
  // call actually has accurate information about which side is showing —
  // always the last one to run — produces the correct final markup,
  // regardless of what an earlier mistaken pass did.
  if (typeof sentenceArea._gtPristineHTML !== "string") {
    sentenceArea._gtPristineHTML = sentenceArea.innerHTML;
  }
  var pristineHtml = sentenceArea._gtPristineHTML;
  var isBackSide = (document.getElementById("answer") !== null);

  // A previous visit's selection must not leak into a new visit to the same
  // card, but it must still survive the front -> back flip of *this* visit
  // (checkAnkiAnswers/formatAnkiExplanation need it). This page - whether it
  // ends up being a front-only load or turns out to be the back (which
  // starts by misleadingly looking like the front too, see the comment
  // above) - captures whatever is currently in storage for this card
  // *once*, immediately, before renderInteractiveBlanks() below creates any
  // dropdown a user could possibly click. That ordering is what makes this
  // safe: nothing on this page has had a chance to write a fresh selection
  // yet, so what's captured here can only be left over from an earlier,
  // now-finished page (an earlier visit, or - for a real back page - the
  // front phase of this same visit, whose write is already done and gone
  // before this page even started loading). Storage is cleared right after
  // capturing, so a front-only page starts and stays clean, while a real
  // back page renders from the captured copy instead of storage (see
  // createDropdownHTML/restoreSelectedState/formatAnkiExplanation).
  if (!_gtCaptureDone) {
    _gtCaptureDone = true;
    _gtCarriedSelections = {};
    var _gtCaptureKey = getCardKey();
    for (var _gtCaptureI = 0; _gtCaptureI < targets.length; _gtCaptureI++) {
      _gtCarriedSelections[_gtCaptureI] = safeStorageGet(_gtCaptureKey + "-sel-" + _gtCaptureI) || "";
      safeStorageSet(_gtCaptureKey + "-sel-" + _gtCaptureI, "");
    }
  }

  try {
    renderInteractiveBlanks(sentenceArea, pristineHtml, targets, optionsGroup, isBackSide);
  } catch (e) {
    // Safety net only — used if something unexpected throws (e.g. a missing
    // DOM API on an unusual WebView) — so the card stays readable instead
    // of breaking outright.
    renderStaticFallback(sentenceArea, pristineHtml, targets, isBackSide);
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

// Matches the blank placeholder token (bare or numbered, e.g. blank / blank1 /
// blank2), and the Anki-style cloze hint form using a "::hint" suffix on that
// same token. Blanks are matched left-to-right in the order they appear in
// the sentence, independent of numbering, and that order lines up with the
// target/options arrays. Built fresh each time it's needed so no shared
// lastIndex state can leak between calls.
function makeBlankTokenRegex() {
  return /\\{\\{\\s*blank\\d*(?:::([\\s\\S]*?))?\\s*\\}\\}/g;
}

function renderInteractiveBlanks(sentenceArea, pristineHtml, targets, optionsGroup, isBackSide) {
  var html = pristineHtml;
  var idx = 0;
  var regex = makeBlankTokenRegex();
  if (regex.test(html)) {
    regex.lastIndex = 0;
    html = html.replace(regex, function(match, hint) {
      var dropdownHtml = createDropdownHTML(idx, optionsGroup[idx] || [], hint || "", isBackSide);
      idx++;
      return dropdownHtml;
    });
  } else {
    // Legacy cards using plain underscores instead of blank-placeholder tokens
    for (var i = 0; i < targets.length; i++) {
      var dropdownHtml2 = createDropdownHTML(i, optionsGroup[i] || [], "", isBackSide);
      html = html.replace(/________|_ _ _ _/, dropdownHtml2);
    }
  }

  sentenceArea.innerHTML = html;
  for (var s = 0; s < targets.length; s++) {
    setupCustomDropdown(s);
  }
  restoreSelectedState(isBackSide);

  // Run blank delay timer if any
  var config = window.AI_GRAMMAR_CONFIG || {};
  var blankTimer = config.blank_timer || 0;

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
}

function renderStaticFallback(sentenceArea, pristineHtml, targets, isBackSide) {
  var html = pristineHtml;
  var actionBar = document.getElementById("action-bar");
  if (actionBar) actionBar.style.display = "none";

  var regex = makeBlankTokenRegex();
  if (isBackSide) {
    // BACK SIDE FALLBACK: show the correct answer filled in and highlighted.
    var bIdx = 0;
    if (regex.test(html)) {
      regex.lastIndex = 0;
      html = html.replace(regex, function() {
        var filled = '<span class="correct-text-inline">' + escapeHtml(targets[bIdx] || "") + '</span>';
        bIdx++;
        return filled;
      });
    } else {
      for (var i = 0; i < targets.length; i++) {
        html = html.replace(/________|_ _ _ _/, '<span class="correct-text-inline">' + escapeHtml(targets[i]) + '</span>');
      }
    }
    sentenceArea.innerHTML = html;
    var resultBox = document.getElementById("result-box");
    if (resultBox) resultBox.classList.remove("hidden");
  } else {
    // FRONT SIDE FALLBACK: replace blanks with clean blank underlines
    if (regex.test(html)) {
      regex.lastIndex = 0;
      html = html.replace(regex, function() {
        return '<span class="grammar-blank-underline">&nbsp;&nbsp;________&nbsp;&nbsp;</span>';
      });
    } else {
      for (var j = 0; j < targets.length; j++) {
        html = html.replace(/________|_ _ _ _/, '<span class="grammar-blank-underline">&nbsp;&nbsp;________&nbsp;&nbsp;</span>');
      }
    }
    sentenceArea.innerHTML = html;
  }
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

function createDropdownHTML(index, options, hint, isBackSideParam) {
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
  var isBackSide = (typeof isBackSideParam === "boolean") ? isBackSideParam : (document.getElementById("answer") !== null);
  
  var wrapperStyle = "";
  var timerHtml = "";
  
  if (blankTimer > 0 && !isBackSide) {
    wrapperStyle = ' style="display:none;"';
    timerHtml = '<span class="timer-countdown" id="timer-countdown-' + index + '" onclick="skipBlankTimer(' + index + ')" title="Click to skip timer and open options" style="cursor: pointer;">⏳ ' + blankTimer + 's</span>';
  }
  
  var html = '';
  html += '<span class="dropdown-wrapper" id="dropdown-wrapper-' + index + '">';
  html += timerHtml;
  
  var storedVal = isBackSide ? ((_gtCarriedSelections && _gtCarriedSelections[index]) || "") : "";
  var extraClass = "";
  if (isBackSide) {
    var targetWord = _correctAnswers[index];
    var isCorrect = (storedVal === targetWord);
    extraClass = isCorrect ? " correct" : " incorrect";
  }
  
  // Anki-style cloze hint: a short hint acting as the default, unselected
  // choice shown inside the blank box (and at the top of its options list)
  // before the learner has answered. Plain text, no brackets. It stands in
  // for the usual placeholder dash and disappears the moment a real option
  // is chosen. Never shown on the back, where the real answer is revealed.
  //
  // The hint (and each option) can be in any script/direction — wrapped in
  // <bdi dir="auto"> so it renders in its own natural direction internally
  // without being able to reorder where it sits in the surrounding sentence
  // (the .dropdown-wrapper span itself is also bidi-isolated in CSS, so the
  // whole blank widget behaves as one fixed, opaque unit in the text flow).
  var hasHint = !!(hint && !isBackSide);
  var placeholderText = hasHint ? ('<bdi dir="auto">' + escapeHtml(hint) + '</bdi>') : getLocalizedSelectText();
  var hintAttr = hasHint ? ' data-hint="' + escapeHtml(hint) + '"' : '';
  
  // Custom dropdown widget: a div, not a native <select>. Native selects can only
  // be force-opened via showPicker(), which requires a fresh user click and will
  // never fire from a timer — this widget has no such restriction.
  html += '<div class="custom-dropdown styled-dropdown' + extraClass + '" id="blank-select-' + index + '"' + wrapperStyle + hintAttr +
          ' tabindex="0" role="combobox" aria-haspopup="listbox" aria-expanded="false"' +
          ' onclick="toggleCustomDropdown(' + index + ')"' +
          ' onkeydown="handleCustomDropdownKeydown(event, ' + index + ')"' +
          ' onfocus="shuffleDropdownOptionsOnFocus(this)">';
  html += '<span class="custom-dropdown-label' + (hasHint ? ' cloze-hint' : '') + '" id="blank-select-' + index + '-label">' + placeholderText + '</span>';
  html += '<div class="custom-dropdown-list hidden" id="blank-select-' + index + '-list" role="listbox">';
  
  var placeholderSelected = (storedVal === "") ? " is-selected" : "";
  html += '<div class="custom-dropdown-option' + placeholderSelected + (hasHint ? ' cloze-hint' : '') + '" data-value="" role="option" onclick="event.stopPropagation(); selectCustomDropdownOption(' + index + ', this.getAttribute(`data-value`))">' + placeholderText + '</div>';
  
  for (var i = 0; i < shuffled.length; i++) {
    var optVal = shuffled[i];
    var selCls = (storedVal === optVal) ? " is-selected" : "";
    html += '<div class="custom-dropdown-option' + selCls + '" data-value="' + escapeHtml(optVal) + '" role="option" onclick="event.stopPropagation(); selectCustomDropdownOption(' + index + ', this.getAttribute(`data-value`))"><bdi dir="auto">' + escapeHtml(optVal) + '</bdi></div>';
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
      var hintAttr = wrapperEl.getAttribute("data-hint");
      var placeholderText = hintAttr ? ('<bdi dir="auto">' + escapeHtml(hintAttr) + '</bdi>') : getLocalizedSelectText();
      var matchedText = placeholderText;
      var matchedIsHint = !!hintAttr;
      for (var i = 0; i < opts.length; i++) {
        var optValue = opts[i].getAttribute("data-value");
        var isMatch = (optValue === _value);
        opts[i].classList.toggle("is-selected", isMatch);
        if (isMatch && optValue !== "") {
          matchedText = opts[i].innerHTML;
          matchedIsHint = false;
        }
      }
      if (label) {
        label.innerHTML = matchedText;
        label.classList.toggle("cloze-hint", matchedIsHint);
      }
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
    safeStorageSet(getCardKey() + "-sel-" + index, select.value);
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

function restoreSelectedState(isBackSide) {
  // Only the back side is allowed to redisplay a stored selection (it needs
  // it for correct/incorrect grading). A front-side pass must never surface
  // a previous selection here, whether it's this card's genuine first
  // front render or the front-embedded pass that a real back-side load
  // also briefly (and misleadingly) looks like - see initDropdowns().
  if (!isBackSide) return;
  for (var i = 0; i < _correctAnswers.length; i++) {
    var select = document.getElementById("blank-select-" + i);
    var savedVal = (_gtCarriedSelections && _gtCarriedSelections[i]) || "";
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

function formatAnkiExplanation() {
  var explContainer = document.querySelector(".explanation-body");
  if (!explContainer) return;
  
  var rawText = explContainer.innerHTML || "";
  if (!rawText) return;
  
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
    var bodyHtml = "";
    // Collected per-group content across all blanks, rendered as a small
    // number of collapsible controls instead of always-visible badges.
    var groups = {
      grammar: [],
      word: [],
      usage: [],
      memory: []
    };
    
    for (var i = 0; i < _correctAnswers.length; i++) {
      var correct = _correctAnswers[i] || "";
      var selected = (_gtCarriedSelections && _gtCarriedSelections[i]) || "";
      
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
      var hasAnswered = !!selected;
      
      var sectionHtml = "";
      if (_correctAnswers.length > 1) {
        sectionHtml += '<div class="explanation-blank-label">Blank ' + (i + 1) + ' ("' + escapeHtml(correct) + '")</div>';
      }
      
      // Always show the correct answer's reasoning first — regardless of
      // whether the learner got it right or wrong. Lead with the actual word
      // itself (bold) rather than a "Why it is correct:" label, so the word
      // and its explanation read as one connected thought. If they chose
      // something wrong, additionally show that chosen word paired with its
      // own explanation the same way.
      var whyText = correctExpl ? escapeHtml(correctExpl) : "";
      sectionHtml += '<div class="explanation-why is-correct"><strong>' + escapeHtml(correct) + '</strong> ' + (whyText || '&mdash;') + '</div>';

      if (hasAnswered && !isCorrect) {
        var whyWrongText = selectedExpl ? escapeHtml(selectedExpl) : "";
        sectionHtml += '<div class="explanation-why is-incorrect"><strong>' + escapeHtml(selected) + '</strong> ' + (whyWrongText || '&mdash;') + '</div>';
      }

      bodyHtml += '<div class="explanation-block">' + sectionHtml + '</div>';

      // Group the extra AI information (hidden by default, revealed on click)
      var lemma = parsedBlock["_lemma"] || "";
      var partOfSpeech = parsedBlock["_partOfSpeech"] || "";
      var grammarPoint = parsedBlock["_grammarPoint"] || "";
      var frequency = parsedBlock["_frequency"] || "";
      var register = parsedBlock["_register"] || "";
      var collocations = parsedBlock["_collocations"] || [];
      var memoryTip = parsedBlock["_memoryTip"] || "";
      var commonMistake = parsedBlock["_commonMistake"] || "";
      var cefrReasonForBlank = (i === 0) ? (jsonMatches[0]["_cefrReason"] || "") : "";
      
      var blankLabel = (_correctAnswers.length > 1) ? ('Blank ' + (i + 1) + ': ') : "";
      var sectionsConfig = window.AI_GRAMMAR_CONFIG || {};
      
      if ((grammarPoint || cefrReasonForBlank) && sectionsConfig.show_grammar_section !== false) {
        var g = "";
        if (grammarPoint) g += '<div>' + blankLabel + escapeHtml(grammarPoint) + '</div>';
        if (cefrReasonForBlank) g += '<div>' + escapeHtml(cefrReasonForBlank) + '</div>';
        groups.grammar.push(g);
      }
      if ((lemma || partOfSpeech) && sectionsConfig.show_word_section !== false) {
        var w = "";
        if (lemma) w += '<div>' + blankLabel + 'Lemma: ' + escapeHtml(lemma) + '</div>';
        if (partOfSpeech) w += '<div>' + blankLabel + 'Part of speech: ' + escapeHtml(partOfSpeech) + '</div>';
        groups.word.push(w);
      }
      if ((frequency || register || (collocations && collocations.length > 0)) && sectionsConfig.show_usage_section !== false) {
        var u = "";
        if (frequency) u += '<div>' + blankLabel + 'Frequency: ' + escapeHtml(frequency) + '</div>';
        if (register) u += '<div>' + blankLabel + 'Register: ' + escapeHtml(register) + '</div>';
        if (collocations && collocations.length > 0) u += '<div>' + blankLabel + 'Collocations: ' + escapeHtml(collocations.join(", ")) + '</div>';
        groups.usage.push(u);
      }
      if ((memoryTip || commonMistake) && sectionsConfig.show_memory_section !== false) {
        var m = "";
        if (memoryTip) m += '<div>' + blankLabel + escapeHtml(memoryTip) + '</div>';
        if (commonMistake) m += '<div>' + blankLabel + 'Common mistake: ' + escapeHtml(commonMistake) + '</div>';
        groups.memory.push(m);
      }
    }
    
    explContainer.innerHTML = bodyHtml;
    renderInfoToggles(groups);
  }
}

function renderInfoToggles(groups) {
  var row = document.getElementById("info-toggle-row");
  if (!row) return;
  
  var labels = { grammar: "Grammar", word: "Word", usage: "Usage", memory: "Memory" };
  var order = ["grammar", "word", "usage", "memory"];
  var html = "";
  
  for (var i = 0; i < order.length; i++) {
    var key = order[i];
    var items = groups[key];
    if (!items || items.length === 0) continue;
    
    html += '<button type="button" class="info-toggle" onclick="toggleInfoPanel(\\'' + key + '\\')">' + labels[key] + '</button>';
  }
  row.innerHTML = html;
  row.classList.toggle("hidden", html === "");
  
  for (var j = 0; j < order.length; j++) {
    var k2 = order[j];
    var items2 = groups[k2];
    var existingPanel = document.getElementById("info-panel-" + k2);
    if (existingPanel) existingPanel.parentNode.removeChild(existingPanel);
    if (!items2 || items2.length === 0) continue;
    
    var panel = document.createElement("div");
    panel.className = "info-panel hidden";
    panel.id = "info-panel-" + k2;
    panel.innerHTML = items2.join("");
    row.parentNode.insertBefore(panel, row.nextSibling);
  }
}

function toggleInfoPanel(key) {
  var panel = document.getElementById("info-panel-" + key);
  if (!panel) return;
  panel.classList.toggle("hidden");
}

function revealAnkiAnswers() {
  // initDropdowns() always rebuilds the sentence from the pristine token
  // text (see initDropdowns for why), so by the time this line returns the
  // blanks are already correctly built for the back side — no hint text or
  // hidden-timer leftovers from an earlier mistaken pass can survive this
  // rebuild, since it replaces the sentence container's content wholesale
  // rather than patching it.
  initDropdowns();

  // Not gated on any add-on/desktop flag: this is plain DOM work, so it
  // must run identically on Desktop, AnkiMobile and AnkiDroid.
  checkAnkiAnswers();
  
  // Format the explanation body dynamically if it is JSON
  formatAnkiExplanation();
  
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

  revealAnkiTranslation();
  revealAnkiExtra();
}

function revealAnkiExtra() {
  // Extra is back-only supplementary content (notes, media, etc.). It always
  // renders in the same slot right after the image — whether or not an
  // image is present, so it visually sits "where the image would be" when
  // there's no image, and directly beneath the image when there is one.
  // Nothing is shown if the Extra field is empty.
  var rawEl = document.getElementById("extra-raw");
  var extraHtml = rawEl ? rawEl.innerHTML.trim() : "";
  var container = document.getElementById("extra-container");
  if (!container) return;
  if (!extraHtml) {
    container.classList.add("hidden");
    container.innerHTML = "";
    return;
  }
  container.innerHTML = extraHtml;
  container.classList.remove("hidden");
}

function revealAnkiTranslation() {
  // Translation is only surfaced once the answer has been revealed, so it
  // never spoils the exercise on the front. Nothing is shown if the
  // Translation field is empty.
  var rawEl = document.getElementById("translation-raw");
  var translation = rawEl ? rawEl.innerHTML.trim() : "";
  if (!translation) return;

  var toggleBtn = document.getElementById("translation-toggle-btn");
  var panel = document.getElementById("translation-panel");
  if (!panel) return;

  panel.innerHTML = escapeHtml(translation);

  var config = window.AI_GRAMMAR_CONFIG || {};
  if (config.translation_position === "toolbar") {
    // Small icon next to the audio controls; tapping/clicking it reveals
    // the panel in place. Panel starts hidden.
    if (toggleBtn) toggleBtn.classList.remove("hidden");
  } else {
    // Default: shown directly under the answer, no toolbar button needed.
    panel.classList.remove("hidden");
  }
}

function toggleTranslationPanel() {
  var panel = document.getElementById("translation-panel");
  if (!panel) return;
  panel.classList.toggle("hidden");
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
    <button class="translation-icon-btn hidden" id="translation-toggle-btn" onclick="toggleTranslationPanel()" title="Translation" aria-label="Translation">
      <svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><line x1="3" y1="12" x2="21" y2="12"/><path d="M12 3c2.5 2.5 4 5.6 4 9s-1.5 6.5-4 9c-2.5-2.5-4-5.6-4-9s1.5-6.5 4-9z"/></svg>
    </button>
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
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
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
  /* Keeps the whole blank widget pinned at its position in the sentence's
     reading order, regardless of the direction of a hint or option shown
     inside it (e.g. an Arabic hint inside a Danish sentence). */
  unicode-bidi: isolate;
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

.styled-dropdown.dropdown-disabled:focus {
  outline: none;
  box-shadow: none !important;
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
  display: none !important;
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

.cloze-hint {
  color: #64748b;
  font-weight: bold;
  font-size: inherit;
}

.nightMode .cloze-hint {
  color: #94a3b8;
}

.result-box {
  padding-top: 20px;
  text-align: left;
}

.explanation-container {
  background: #f1f5f9;
  border-radius: 8px;
  padding: 16px;
}

.nightMode .explanation-container {
  background: #334155;
}

.explanation-body {
  font-size: 14px;
  line-height: 1.5;
}

.explanation-block {
  padding: 0;
  margin-bottom: 10px;
  color: #1e293b;
}

.nightMode .explanation-block {
  color: #f1f5f9;
}

.explanation-blank-label {
  font-weight: 600;
  color: #64748b;
  font-size: 0.8em;
  text-transform: uppercase;
  letter-spacing: 0.02em;
  margin-bottom: 4px;
}

.nightMode .explanation-blank-label {
  color: #94a3b8;
}

.explanation-why {
  margin-bottom: 8px;
  line-height: 1.4;
}

.explanation-why.is-correct {
  color: #15803d;
}

.nightMode .explanation-why.is-correct {
  color: #4ade80;
}

.explanation-why.is-incorrect {
  color: #b91c1c;
}

.nightMode .explanation-why.is-incorrect {
  color: #f87171;
}

.info-toggle-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid #e5e5ea;
}

.nightMode .info-toggle-row {
  border-top-color: #334155;
}

.info-toggle {
  background: none;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 12px;
  color: #475569;
  cursor: pointer;
}

.info-toggle:hover {
  background-color: #f1f5f9;
}

.nightMode .info-toggle {
  border-color: #475569;
  color: #cbd5e1;
}

.nightMode .info-toggle:hover {
  background-color: #1e293b;
}

.info-panel {
  margin-top: 8px;
  padding: 10px 0;
  font-size: 12.5px;
  color: #475569;
  line-height: 1.5;
  unicode-bidi: plain-text;
}

.nightMode .info-panel {
  color: #cbd5e1;
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

.extra-container {
  margin-top: 16px;
  margin-bottom: 16px;
  line-height: 1.5;
  color: #475569;
  text-align: left;
  unicode-bidi: plain-text;
}

.nightMode .extra-container {
  color: #cbd5e1;
}

.extra-container img {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
}

.audio-btn {
  background-color: #f1f5f9;
  color: #0f172a;
}

.nightMode .audio-btn {
  background-color: #334155;
  color: #f8fafc;
}

.translation-icon-btn {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  border: 1px solid #d1d5db;
  background: rgba(255, 255, 255, 0.95);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
}

.translation-icon-btn svg {
  width: 16px;
  height: 16px;
  stroke: #64748b;
  fill: none;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.nightMode .translation-icon-btn {
  background: rgba(30, 30, 30, 0.95);
  border-color: #475569;
}

.nightMode .translation-icon-btn svg {
  stroke: #94a3b8;
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
    show_check = config.get("show_check_answer", False)
    show_bg = config.get("show_white_background", False)
    show_explanation_bg = config.get("show_explanation_background", False)
    center_horiz = config.get("center_horizontal", True)
    center_vert = config.get("center_vertical", True)
    auto_flip = config.get("auto_flip", True)
    
    # Append display overrides based on show/hide options
    css_with_toggles = CSS_STYLING
    if not show_lang:
        css_with_toggles += "\n.badge-lang { display: none !important; }"
    if not show_diff:
        css_with_toggles += "\n.badge-diff { display: none !important; }"
    # The grammar-type badge is no longer settings-controlled (Grammar is now
    # chosen per-card in the generator itself); keep it hidden by default.
    css_with_toggles += "\n.badge-type { display: none !important; }"
    if not show_check:
        css_with_toggles += "\n.check-btn { display: none !important; }"
    if not show_bg:
        css_with_toggles += "\n.anki-grammar-card { background: transparent !important; box-shadow: none !important; border: none !important; padding: 0 !important; }\n.nightMode .anki-grammar-card { background: transparent !important; box-shadow: none !important; border: none !important; padding: 0 !important; }"
    if not show_explanation_bg:
        css_with_toggles += "\n.explanation-container { background: transparent !important; padding: 0 !important; }\n.nightMode .explanation-container { background: transparent !important; }"
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
    css_with_toggles += f"\n#translation-panel {{ font-size: {font_size}px !important; }}"
    css_with_toggles += f"\n.explanation-body {{ font-size: {font_size}px !important; }}"
    css_with_toggles += f"\n.explanation-why {{ font-size: {font_size}px !important; }}"
    css_with_toggles += f"\n.extra-container {{ font-size: {font_size}px !important; }}"
    
    card_max_width = config.get("card_max_width", 800)
    css_with_toggles += f"\n.anki-card-outer-container {{ max-width: {card_max_width}px !important; }}"

    explanation_align = config.get("explanation_align", "left")
    if explanation_align == "center":
        css_with_toggles += "\n.result-box { text-align: center !important; }\n.explanation-container { text-align: center !important; }\n.info-toggle-row { justify-content: center !important; }\n.extra-container { text-align: center !important; }"
    else:
        css_with_toggles += "\n.result-box { text-align: left !important; }\n.explanation-container { text-align: left !important; }\n.info-toggle-row { justify-content: flex-start !important; }\n.extra-container { text-align: left !important; }"
        
    blank_timer = config.get("blank_timer", 0)
    auto_open = "true" if config.get("auto_open_dropdown", False) else "false"
    keyboard_shortcuts = "true" if config.get("keyboard_shortcuts", False) else "false"
    show_grammar_section = "true" if config.get("show_grammar_section", True) else "false"
    show_word_section = "true" if config.get("show_word_section", True) else "false"
    show_usage_section = "true" if config.get("show_usage_section", True) else "false"
    show_memory_section = "true" if config.get("show_memory_section", True) else "false"
    translation_position = config.get("translation_position", "under_answer")
    if translation_position not in ("under_answer", "toolbar"):
        translation_position = "under_answer"
    config_js = (
        '<script>window.AI_GRAMMAR_CONFIG = {'
        f'"auto_flip": {"true" if auto_flip else "false"}, '
        f'"center_horizontal": {"true" if center_horiz else "false"}, '
        f'"center_vertical": {"true" if center_vert else "false"}, '
        f'"blank_timer": {blank_timer}, '
        f'"auto_open_dropdown": {auto_open}, '
        f'"keyboard_shortcuts": {keyboard_shortcuts}, '
        f'"show_grammar_section": {show_grammar_section}, '
        f'"show_word_section": {show_word_section}, '
        f'"show_usage_section": {show_usage_section}, '
        f'"show_memory_section": {show_memory_section}, '
        f'"translation_position": "{translation_position}"'
        '};</script>\n'
    )
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
