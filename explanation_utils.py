# -*- coding: utf-8 -*-
"""Qt-free helpers for the Grammar Trainer manual-first card workflow.

Everything in here is pure Python (no Anki / Qt imports) so it can be unit
tested on its own. It covers:

* option de-duplication (same rules as the original Manual Entry tab),
* serialising per-option explanations into the EXISTING ``Explanation`` field
  format (one JSON object per blank) without touching the review templates,
* building / validating the optional "Generate Missing Explanations" AI call,
* the field-preservation rule used when the dialog writes into an editor note.
"""
import html
import json
import re

# Fields that the dialog never has a way to clear on purpose. When no
# replacement value is supplied they are left exactly as they are.
PROTECTED_FIELDS = ("FrontAudio", "BackAudio", "Image", "Translation")


# ---------------------------------------------------------------------------
# Small text helpers
# ---------------------------------------------------------------------------

def is_blank_text(text):
    """True for None, "" and whitespace-only strings."""
    return text is None or not str(text).strip()


def dedupe_options(answer, distractors_text):
    """Build the option list for one blank.

    Mirrors the original Manual Entry logic: correct answer first, then the
    comma-separated distractors, de-duplicated case-insensitively (the first
    spelling wins). Returns ``(options, ignored_duplicates)``.
    """
    answer = (answer or "").strip()
    distractors = [d.strip() for d in (distractors_text or "").split(",") if d.strip()]
    seen = set()
    options = []
    ignored = []
    for opt in [answer] + distractors:
        opt = opt.strip()
        key = opt.lower()
        if not key:
            continue
        if key in seen:
            ignored.append(opt)
            continue
        seen.add(key)
        options.append(opt)
    return options, ignored


# ---------------------------------------------------------------------------
# Explanation serialisation (existing field format, brace/HTML safe)
# ---------------------------------------------------------------------------

def escape_text(text):
    """Escape the characters the review parser would otherwise mangle.

    The review template decodes the field through an HTML round-trip, so a
    literal ``<``, ``>`` or ``&`` must be stored as an entity to survive as
    text. ``&`` MUST be escaped first so the entities produced for ``<`` and
    ``>`` are not escaped a second time.
    """
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def encode_string(text):
    """JSON-encode one string token.

    ``{`` / ``}`` are written as the JSON escapes ``\\u007b`` / ``\\u007d`` so
    the review parser's brace scanner only ever sees the structural braces of
    the object. ``JSON.parse`` turns the escapes back into real characters.
    """
    token = json.dumps(escape_text(text), ensure_ascii=False)
    return token.replace("{", "\\u007b").replace("}", "\\u007d")


def build_explanation_json(options, explanations):
    """Serialise one blank's explanations as the existing ``{option: text}`` JSON.

    ``options`` is the ordered option list (correct answer first).
    ``explanations`` maps ``option.lower()`` -> text. Missing/blank entries
    are stored as ``""`` so every blank always gets a complete object.
    Output is byte-identical to ``json.dumps(..., ensure_ascii=False)`` for
    text that contains none of ``& < > { }``.
    """
    parts = []
    for opt in options:
        text = (explanations.get(opt.lower(), "") or "").strip()
        parts.append(encode_string(opt) + ": " + encode_string(text))
    return "{" + ", ".join(parts) + "}"


# ---------------------------------------------------------------------------
# "Generate Missing Explanations" support
# ---------------------------------------------------------------------------

def find_missing(blanks):
    """List ``(blank_index, option)`` pairs whose explanation cell is blank.

    ``blanks`` is a list of ``{"options": [...], "explanations": {lower: text}}``.
    """
    missing = []
    for idx, blank in enumerate(blanks):
        expl = blank.get("explanations", {})
        for opt in blank.get("options", []):
            if is_blank_text(expl.get(opt.lower(), "")):
                missing.append((idx, opt))
    return missing


def display_sentence(sentence_raw):
    """Number the ___ markers so the AI can tell the blanks apart."""
    counter = [0]

    def repl(_m):
        counter[0] += 1
        return "[BLANK %d]" % counter[0]

    return re.sub(r"_{3,}", repl, sentence_raw)


def build_explanation_prompt(language, sentence_raw, blanks):
    """Prompt for the explanations-only AI request.

    ``blanks`` is a list of ``{"correct": str, "options": [...], "missing": [...]}``.
    The AI is only asked for the options in ``missing``.
    """
    lines = [
        "You are a grammar teacher. Below is a fill-in-the-blank grammar exercise in %s." % language,
        "Write short explanations ONLY. Do not change, rewrite or extend the sentence, the blanks, "
        "the correct answers or the wrong options.",
        "",
        "Sentence: " + display_sentence(sentence_raw),
        "",
    ]
    for i, blank in enumerate(blanks, start=1):
        lines.append("[BLANK %d]" % i)
        lines.append("  Correct answer: " + blank["correct"])
        lines.append("  All options: " + " | ".join(blank["options"]))
        if blank["missing"]:
            lines.append("  Explanations needed for: " + " | ".join(blank["missing"]))
        else:
            lines.append("  Explanations needed for: (none)")
    lines += [
        "",
        "Rules:",
        "- Write every explanation in %s." % language,
        "- For the correct answer: explain in 1-2 short sentences why it is correct in THIS sentence.",
        "- For each incorrect option: explain in 1-2 short sentences why it is wrong in THIS sentence.",
        "- Only write explanations for the options listed under 'Explanations needed for'.",
        "- Use the option text EXACTLY as written above. Do not rely on the order of the options.",
        "- Plain text only: no HTML, no markdown, no quotation of these instructions.",
        "",
        "Return ONLY a JSON object of this form:",
        '{"explanations": [{"blank": "1", "option": "<exact option text>", "explanation": "<text>"}]}',
    ]
    return "\n".join(lines)


def parse_explanation_reply(parsed, blanks):
    """Validate the AI reply and map it onto the requested cells.

    ``blanks`` is the same structure given to ``build_explanation_prompt``.
    Returns ``(generated, unfilled)`` where ``generated`` maps
    ``(blank_index, option.lower())`` -> text and ``unfilled`` lists the
    requested ``(blank_index, option)`` pairs the reply did not cover.
    Raises ``ValueError`` when the reply is not in the expected shape or
    contains nothing usable. Items for options that were not requested are
    ignored, so an existing explanation can never be targeted.
    """
    if not isinstance(parsed, dict) or not isinstance(parsed.get("explanations"), list):
        raise ValueError("The AI reply was not in the expected format.")

    requested = {}
    for idx, blank in enumerate(blanks):
        for opt in blank.get("missing", []):
            requested[(idx, opt.lower())] = opt

    generated = {}
    for item in parsed["explanations"]:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(str(item.get("blank", "")).strip()) - 1
        except ValueError:
            continue
        option = item.get("option")
        text = item.get("explanation")
        if not isinstance(option, str) or not isinstance(text, str):
            continue
        key = (idx, option.strip().lower())
        if key not in requested or key in generated:
            continue
        text = " ".join(text.split())
        if not text:
            continue
        generated[key] = text

    if not generated:
        raise ValueError("The AI reply did not contain any usable explanations.")

    unfilled = [(k[0], requested[k]) for k in requested if k not in generated]
    return generated, unfilled


def apply_generated(current, generated):
    """Choose which generated explanations may be written.

    ``current`` maps ``(blank_index, option.lower())`` -> the text that is in
    the cell RIGHT NOW (at the moment the AI response arrived). Only cells
    that still exist and are still blank are returned.
    """
    return {k: v for k, v in generated.items() if k in current and is_blank_text(current[k])}


# ---------------------------------------------------------------------------
# Editor-note field preservation
# ---------------------------------------------------------------------------

def normalize_sentence(sentence):
    """Normalise a Sentence field value for an "is it the same sentence?" check."""
    text = re.sub(r"<[^>]*>", " ", sentence or "")
    text = html.unescape(text).replace("\xa0", " ")
    return " ".join(text.split())


def plan_protected_fields(existing, supplied, old_sentence, new_sentence):
    """Decide how to treat FrontAudio / BackAudio / Image / Translation.

    ``existing`` maps each protected field PRESENT ON THE NOTE to its current
    value; ``supplied`` maps field -> the value the dialog wants to write.

    * A non-blank supplied value replaces the field (deliberate replacement).
    * A blank supplied value never writes: existing content is kept.
    * ``stale`` is True when content was kept AND the old sentence was
      non-empty AND the sentence is now different, i.e. the kept content may
      belong to the previous sentence.

    Returns ``(to_write, kept, stale)``.
    """
    to_write = {}
    kept = []
    for field in PROTECTED_FIELDS:
        if field not in existing:
            continue
        new_value = supplied.get(field, "") or ""
        if new_value.strip():
            to_write[field] = new_value
        elif (existing[field] or "").strip():
            kept.append(field)
    old = normalize_sentence(old_sentence)
    stale = bool(kept) and bool(old) and old != normalize_sentence(new_sentence)
    return to_write, kept, stale
