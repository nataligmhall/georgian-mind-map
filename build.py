#!/usr/bin/env python3
"""Build dictionary data, per-theme pages, and optional TTS audio."""

import argparse
import asyncio
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).parent
THEMES_DIR = ROOT / "themes"
AUDIO_DIR = ROOT / "audio"
FILES = {
    "noun": ROOT / "kaikki.org-dictionary-Georgian-by-pos-noun.jsonl",
    "verb": ROOT / "kaikki.org-dictionary-Georgian-by-pos-verb.jsonl",
    "adj": ROOT / "kaikki.org-dictionary-Georgian-by-pos-adj.jsonl",
    "adv": ROOT / "kaikki.org-dictionary-Georgian-by-pos-adv.jsonl",
    "phrase": ROOT / "kaikki.org-dictionary-Georgian-by-pos-phrase.jsonl",
    "proverb": ROOT / "kaikki.org-dictionary-Georgian-by-pos-proverb.jsonl",
}
OUTPUT = ROOT / "dictionary.json"
OUTPUT_JS = ROOT / "dictionary.js"
CORRECTIONS = ROOT / "corrections.json"

TTS_VOICE = "ka-GE-EkaNeural"

MORPH_PATTERN = re.compile(
    r"suffixed|prefixed|circumfixed|pluralia|ordinal numbers|undefined derivations|"
    r"collocations|entries with|links with|Pages with|Forms linking|etymon with|"
    r"Guria Georgian|Imereti Georgian|Old Georgian|Grammatical cases|"
    r"Sexual orientations|Demonyms|Ethnonyms|Nationalities",
    re.I,
)

SKIP_CATEGORIES = {
    "Grammar", "Linguistics", "Pages using etymon with no ID", "Humanities",
    "Pathology", "Monarchy", "Government", "Business", "Geology", "Astronomy",
    "Botany", "Biology", "Medicine", "Vitamins", "Physics", "Chemistry",
    "Chemical elements", "Politics", "Economics", "Computing", "Mathematics",
    "Finance", "Law", "Christianity", "LGBTQ", "Military", "Anatomy", "Chess",
}

THEME_META = {
    "Colors": {"ka": "ფერები", "icon": "◉"},
    "Days of the week": {"ka": "კვირის დღეები", "icon": "☀"},
    "Family": {"ka": "ოჯახი", "icon": "♡"},
    "Family members": {"ka": "ოჯახის წევრები", "icon": "♡"},
    "Male family members": {"ka": "მამრობითი ოჯახი", "icon": "♂"},
    "Female family members": {"ka": "მდედრობითი ოჯახი", "icon": "♀"},
    "Foods": {"ka": "საჭმელები", "icon": "◈"},
    "Food and drink": {"ka": "საჭმელი და სასმელი", "icon": "◈"},
    "Fruits": {"ka": "ხილი", "icon": "◎"},
    "Vegetables": {"ka": "ბოსტნეული", "icon": "❧"},
    "Animals": {"ka": "ცხოველები", "icon": "✦"},
    "Baby animals": {"ka": "პატარა ცხოველები", "icon": "✦"},
    "Mammals": {"ka": "ძუძუმწოვრები", "icon": "✦"},
    "Birds": {"ka": "ფრინველები", "icon": "✧"},
    "Trees": {"ka": "ხეები", "icon": "🌲"},
    "Flowers": {"ka": "ყვავილები", "icon": "✿"},
    "Clothing": {"ka": "ტანისამოსი", "icon": "◐"},
    "Buildings": {"ka": "შენობები", "icon": "⌂"},
    "Furniture": {"ka": "ავეჯი", "icon": "▣"},
    "Tools": {"ka": "ხელსაწყოები", "icon": "⚒"},
    "Occupations": {"ka": "პროფესიები", "icon": "⚙"},
    "Sports": {"ka": "სპორტი", "icon": "⚑"},
    "Music": {"ka": "მუსიკა", "icon": "♪"},
    "Musical instruments": {"ka": "მუსიკალური ინსტრუმენტები", "icon": "♫"},
    "Musical genres": {"ka": "მუსიკალური ჟანრები", "icon": "♫"},
    "Time": {"ka": "დრო", "icon": "◷"},
    "Weather": {"ka": "ამინდი", "icon": "☁"},
    "Seasons": {"ka": "სეზონები", "icon": "❄"},
    "Months": {"ka": "თვეები", "icon": "☽"},
    "Numbers": {"ka": "რიცხვები", "icon": "#"},
    "Body parts": {"ka": "სხეულის ნაწილები", "icon": "○"},
    "Face": {"ka": "სახე", "icon": "◯"},
    "Emotions": {"ka": "ემოციები", "icon": "☺"},
    "Languages": {"ka": "ენები", "icon": "ა"},
    "Countries": {"ka": "ქვეყნები", "icon": "⊕"},
    "Cities": {"ka": "ქალაქები", "icon": "●"},
    "Landforms": {"ka": "რელიეფი", "icon": "△"},
    "Bodies of water": {"ka": "სათავსო წყლები", "icon": "≋"},
    "Geography": {"ka": "გეოგრაფია", "icon": "⊕"},
    "Transport": {"ka": "ტრანსპორტი", "icon": "➤"},
    "Vehicles": {"ka": "ტრანსპორტი", "icon": "➤"},
    "Household": {"ka": "საყოფაცხოვრებო", "icon": "⌂"},
    "School": {"ka": "სკოლა", "icon": "✎"},
    "Religion": {"ka": "რელიგია", "icon": "✝"},
    "Light sources": {"ka": "სინათლე", "icon": "✴"},
    "People": {"ka": "ხალხი", "icon": "☺"},
    "Phrases": {"ka": "ფრაზები", "icon": "💬"},
    "Proverbs": {"ka": "ანდაზები", "icon": "📜"},
    "Verbs": {"ka": "ზმნები", "icon": "⚡"},
}

FORM_GLOSS = re.compile(
    r"(form of|participle of|indicative of|imperative of|aorist of|"
    r"verbal noun of|plural of|diminutive of|comparative of|superlative of|"
    r"first-person|second-person|third-person|singular of|plural of)",
    re.I,
)

MAX_WORDS_PER_THEME = 150
MAX_VERBS = 200
MIN_THEME_WORDS = 3

# Learner-priority verbs (matched first when building the Verbs theme).
PRIORITY_VERBS = [
    "არის", "აქვს", "უნდა", "მოდის", "წავს", "მიდის", "ჭამს", "სვამს", "იცის",
    "მადლობს", "წერს", "კითხულობს", "სწავლობს", "მუშაობს", "ძლებს", "ხედავს",
    "ისმის", "სურს", "ფიქრობს", "იძახის", "ყიდულობს", "ყიდის", "იღებს", "აძლევს",
    "გვაქვს", "გვინდა", "გვჭირდება", "შეძლებს", "იწყებს", "ამთავრებს", "ცეკვავს",
    "მღერს", "თამაშობს", "მოყვარის", "სძალვს", "იწვევს", "ჭრის", "იძიებს",
    "ნიშნავს", "წავა", "გადის", "ეძებს", "ელის", "იღვწის", "სწორდება", "ჯდება",
    "დგება", "წევს", "იძვრის", "ჩამოდის", "ადის", "ტოვებს", "უბრუნდება", "შედის",
    "გამოდის", "იცვამს", "იბანება",
]

TENSE_LABELS = [
    ("present", "Present"),
    ("imperfect", "Imperfect"),
    ("future", "Future"),
    ("aorist", "Aorist"),
    ("perfect", "Perfect"),
    ("pluperfect", "Pluperfect"),
    ("imperative", "Imperative"),
    ("subjunctive", "Subjunctive"),
    ("conditional", "Conditional"),
    ("optative", "Optative"),
]

PERSON_ROWS = [
    (("first-person", "singular"), "1sg"),
    (("second-person", "singular"), "2sg"),
    (("third-person", "singular"), "3sg"),
    (("first-person", "plural"), "1pl"),
    (("second-person", "plural"), "2pl"),
    (("third-person", "plural"), "3pl"),
]

THEMATIC_SKIP_POS = {"phrase", "proverb", "verb"}
SPECIAL_THEMES = {"Phrases", "Proverbs", "Verbs"}
THEME_SKIP_GLOSS: Dict[str, re.Pattern] = {
    "Trees": re.compile(r"\b(gold|silver|platinum|copper|iron|steel|metal)\b", re.I),
    "Fruits": re.compile(r"\b(color|colored|colour)\b", re.I),
    "Flowers": re.compile(r"\b(color|colored|colour)\b", re.I),
    "Animals": re.compile(r"\b(color|colored|colour)\b", re.I),
}

# Add words whose gloss matches even when Wiktionary omits the theme category.
GLOSS_THEME_HINTS: Dict[str, List[str]] = {
    "Trees": ["elm", "oak", "beech", "maple", "birch", "pine", "fir", "cypress", "walnut-tree", "poplar", "willow", "alder"],
}


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def is_form_of(sense: dict) -> bool:
    return "form-of" in (sense.get("tags") or [])


def get_roman(entry: dict) -> str:
    for form in entry.get("forms") or []:
        if "romanization" in (form.get("tags") or []):
            return form.get("form", "")
    return ""


def get_wiktionary_audio(entry: dict) -> Optional[str]:
    for sound in entry.get("sounds") or []:
        url = sound.get("mp3_url") or sound.get("ogg_url")
        if url:
            return url
    return None


def get_ipa(entry: dict) -> Optional[str]:
    for sound in entry.get("sounds") or []:
        if sound.get("ipa"):
            return sound["ipa"]
    return None


def clean_gloss(sense: dict) -> Optional[str]:
    glosses = sense.get("glosses") or []
    if not glosses:
        return None
    gloss = glosses[0].strip()
    if FORM_GLOSS.search(gloss):
        return None
    if len(gloss) > 120:
        return None
    return gloss


def get_all_glosses(entry: dict) -> List[str]:
    seen = set()
    glosses = []
    for sense in entry.get("senses") or []:
        if is_form_of(sense):
            continue
        for g in sense.get("glosses") or []:
            g = g.strip()
            if g and g not in seen and not FORM_GLOSS.search(g) and len(g) <= 120:
                seen.add(g)
                glosses.append(g)
    return glosses[:6]


def get_examples(entry: dict) -> List[dict]:
    examples = []
    for sense in entry.get("senses") or []:
        for ex in sense.get("examples") or []:
            text = ex.get("text", "").strip()
            if not text:
                continue
            examples.append({
                "ka": text,
                "roman": ex.get("roman", ""),
                "en": ex.get("translation") or ex.get("english") or "",
            })
    return examples[:3]


def get_etymology(entry: dict) -> Optional[str]:
    text = (entry.get("etymology_text") or "").strip()
    if not text or len(text) > 400:
        return text[:400] + "…" if text else None
    return text or None


def thematic_categories(sense: dict) -> List[str]:
    cats = []
    for cat in sense.get("categories") or []:
        name = cat.get("name", "")
        if not name or name.startswith("Georgian "):
            continue
        if MORPH_PATTERN.search(name) or name in SKIP_CATEGORIES:
            continue
        cats.append(name)
    return cats


def pick_best_sense(entry: dict) -> Tuple[Optional[str], List[str]]:
    best_gloss = None
    best_cats: List[str] = []
    best_score = -1

    for sense in entry.get("senses") or []:
        if is_form_of(sense):
            continue
        gloss = clean_gloss(sense)
        if not gloss:
            continue
        cats = thematic_categories(sense)
        score = len(cats) * 10 + (5 if len(gloss) < 40 else 0)
        if score > best_score:
            best_score = score
            best_gloss = gloss
            best_cats = cats

    return best_gloss, best_cats


def audio_rel_path(theme_id: str, index: int) -> str:
    return f"audio/{theme_id}/{index:03d}.mp3"


def gloss_fits_theme(theme: str, gloss: str) -> bool:
    pattern = THEME_SKIP_GLOSS.get(theme)
    if pattern and pattern.search(gloss):
        return False
    return True


def gloss_exact_theme_hint(theme: str, gloss: str) -> bool:
    """True when gloss is essentially a member of this theme (e.g. 'elm' for Trees)."""
    hints = GLOSS_THEME_HINTS.get(theme, [])
    g = gloss.lower().strip()
    if g in hints:
        return True
    return any(g.startswith(h + " ") or g.startswith(h + ",") for h in hints)


def pick_sense_for_category(entry: dict, theme: str) -> Optional[dict]:
    """Best sense from this entry for a specific theme."""
    best = None
    best_score = -1

    for sense in entry.get("senses") or []:
        if is_form_of(sense):
            continue
        gloss = clean_gloss(sense)
        if not gloss or not gloss_fits_theme(theme, gloss):
            continue

        cats = thematic_categories(sense)
        in_theme = theme in cats
        exact_hint = gloss_exact_theme_hint(theme, gloss)

        if not in_theme and not exact_hint:
            continue

        score = 0
        if in_theme:
            score += 100
        if exact_hint:
            score += 60
        if "alt-of" in (sense.get("tags") or []):
            score -= 40
        score += max(0, 15 - len(gloss) // 6)

        if score > best_score:
            best_score = score
            best = {"gloss": gloss, "sense": sense, "score": score}

    if best and best["score"] >= 50:
        return best
    return None


def load_corrections() -> dict:
    if not CORRECTIONS.exists():
        return {}
    with CORRECTIONS.open(encoding="utf-8") as f:
        return json.load(f)


def apply_corrections(theme_words: Dict[str, List[dict]], corrections: dict) -> None:
    """Apply manual fixes: corrections[ka][theme_name] = {en, glosses?, etymology?}"""
    theme_id_by_name = {name: slugify(name) for name in THEME_META}

    for ka, themes in corrections.items():
        for theme_name, fix in themes.items():
            if theme_name not in THEME_META:
                continue
            theme_id = theme_id_by_name[theme_name]
            words_list = theme_words.setdefault(theme_name, [])
            existing = next((w for w in words_list if w["ka"] == ka), None)

            if existing:
                existing["en"] = fix.get("en", existing["en"])
                if fix.get("glosses"):
                    existing["glosses"] = fix["glosses"]
                if fix.get("etymology"):
                    existing["etymology"] = fix["etymology"]
                existing["_corrected"] = True
            else:
                words_list.append({
                    "ka": ka,
                    "roman": fix.get("roman", ""),
                    "en": fix["en"],
                    "glosses": fix.get("glosses", [fix["en"]]),
                    "pos": fix.get("pos", "noun"),
                    "ipa": fix.get("ipa"),
                    "audio": fix.get("audio"),
                    "audioLocal": None,
                    "audioSource": None,
                    "examples": fix.get("examples", []),
                    "etymology": fix.get("etymology"),
                    "_theme_id": theme_id,
                    "_corrected": True,
                })


def build_word_record(entry: dict, pos: str, theme_id: str, index: int, sense_info: Optional[dict] = None) -> dict:
    if sense_info:
        gloss = sense_info["gloss"]
        sense = sense_info["sense"]
        glosses = [g.strip() for g in sense.get("glosses") or [] if g.strip()][:6] or [gloss]
        examples = []
        for ex in sense.get("examples") or []:
            text = ex.get("text", "").strip()
            if text:
                examples.append({
                    "ka": text,
                    "roman": ex.get("roman", ""),
                    "en": ex.get("translation") or ex.get("english") or "",
                })
    else:
        gloss, _ = pick_best_sense(entry)
        glosses = get_all_glosses(entry)
        examples = get_examples(entry)

    wiktionary = get_wiktionary_audio(entry)
    return {
        "ka": entry.get("word", "").strip(),
        "roman": get_roman(entry),
        "en": gloss or "",
        "glosses": glosses,
        "pos": pos,
        "ipa": get_ipa(entry),
        "audio": wiktionary,
        "audioLocal": audio_rel_path(theme_id, index),
        "audioSource": "wiktionary" if wiktionary else None,
        "examples": examples[:3],
        "etymology": get_etymology(entry),
    }


def slim_word(word: dict, theme_id: str) -> dict:
    """Lightweight record for the globe index."""
    audio = word.get("audio")
    if audio and not str(audio).startswith("http"):
        if not (ROOT / audio).exists():
            audio = None
    if not audio:
        local = word.get("audioLocal")
        if local and (ROOT / local).exists():
            audio = local
    return {
        "ka": word["ka"],
        "roman": word["roman"],
        "en": word["en"],
        "pos": word["pos"],
        "ipa": word["ipa"],
        "audio": audio,
        "audioSource": word.get("audioSource"),
        "page": f"themes/{theme_id}.html",
    }


def is_lemma_verb_gloss(gloss: str) -> bool:
    g = gloss.strip().lower()
    return g.startswith("to ") and "form of" not in g


def conjugation_form_count(entry: dict) -> int:
    count = 0
    for form in entry.get("forms") or []:
        if form.get("source") != "conjugation":
            continue
        tags = set(form.get("tags") or [])
        if tags & {"table-tags", "inflection-template", "error-unrecognized-form", "noun-from-verb"}:
            continue
        ka = (form.get("form") or "").strip()
        if not ka or ka in {"no-table-tags", "q", "-"}:
            continue
        count += 1
    return count


def extract_conjugation(entry: dict) -> Optional[dict]:
    """Group conjugation forms by tense into a compact grid."""
    by_tense: Dict[str, Dict[str, dict]] = defaultdict(dict)

    for form in entry.get("forms") or []:
        if form.get("source") != "conjugation":
            continue
        tags = set(form.get("tags") or [])
        if tags & {"table-tags", "inflection-template", "error-unrecognized-form", "noun-from-verb"}:
            continue

        ka = (form.get("form") or "").strip()
        if not ka or ka in {"no-table-tags", "q", "-"}:
            continue

        tense = next((key for key, _ in TENSE_LABELS if key in tags), None)
        if not tense:
            continue

        label = next(
            (lbl for keys, lbl in PERSON_ROWS if all(k in tags for k in keys)),
            None,
        )
        if not label:
            continue

        by_tense[tense][label] = {
            "ka": ka,
            "roman": form.get("roman", ""),
        }

    if not by_tense:
        return None

    groups = []
    for tense_key, tense_label in TENSE_LABELS:
        rows = by_tense.get(tense_key)
        if not rows:
            continue
        forms = [rows[lbl] for _, lbl in PERSON_ROWS if lbl in rows]
        if forms:
            groups.append({"tense": tense_label, "forms": forms})
        if len(groups) >= 8:
            break

    return {"groups": groups} if groups else None


def verb_priority_score(word: str, entry: dict, gloss: str) -> int:
    score = 0
    if word in PRIORITY_VERBS:
        score += 1000 - PRIORITY_VERBS.index(word) * 5
    score += min(conjugation_form_count(entry), 120)
    score += max(0, 40 - len(gloss))
    return score


def process_phrases_and_proverbs() -> Dict[str, List[dict]]:
    result: Dict[str, List[dict]] = {}

    for theme_name, pos_key in [("Phrases", "phrase"), ("Proverbs", "proverb")]:
        path = FILES[pos_key]
        if not path.exists():
            print(f"Skipping missing file: {path}")
            continue

        theme_id = slugify(theme_name)
        records = []
        with path.open(encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line)
                word = entry.get("word", "").strip()
                if not word:
                    continue
                gloss, _ = pick_best_sense(entry)
                if not gloss:
                    continue
                rec = build_word_record(entry, pos_key, theme_id, len(records))
                rec["_theme_id"] = theme_id
                records.append(rec)

        records.sort(key=lambda w: w["ka"])
        for i, w in enumerate(records):
            w["audioLocal"] = audio_rel_path(theme_id, i)
        result[theme_name] = records

    return result


def process_verbs() -> Dict[str, List[dict]]:
    path = FILES["verb"]
    if not path.exists():
        return {}

    theme_id = slugify("Verbs")
    best: Dict[str, dict] = {}

    with path.open(encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            word = entry.get("word", "").strip()
            if not word:
                continue

            gloss, _ = pick_best_sense(entry)
            if not gloss or not is_lemma_verb_gloss(gloss):
                continue

            score = verb_priority_score(word, entry, gloss)
            prev = best.get(word)
            if prev is None or score > prev["score"]:
                best[word] = {"entry": entry, "gloss": gloss, "score": score}

    ranked = sorted(best.values(), key=lambda x: (-x["score"], x["entry"]["word"]))
    records = []
    for i, info in enumerate(ranked[:MAX_VERBS]):
        entry = info["entry"]
        rec = build_word_record(entry, "verb", theme_id, i)
        rec["conjugation"] = extract_conjugation(entry)
        rec["_theme_id"] = theme_id
        records.append(rec)

    return {"Verbs": records}


def process_thematic_files() -> Dict[str, List[dict]]:
    # Collect best (entry, sense) candidate per (theme, word)
    candidates: Dict[str, Dict[str, dict]] = defaultdict(dict)

    for pos, path in FILES.items():
        if pos in THEMATIC_SKIP_POS:
            continue
        if not path.exists():
            print(f"Skipping missing file: {path}")
            continue

        with path.open(encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line)
                word = entry.get("word", "").strip()
                if not word:
                    continue

                for theme_name in THEME_META:
                    if theme_name in SPECIAL_THEMES:
                        continue
                    sense_info = pick_sense_for_category(entry, theme_name)
                    if not sense_info:
                        continue

                    theme_id = slugify(theme_name)
                    prev = candidates[theme_name].get(word)
                    if prev is None or sense_info["score"] > prev["sense_info"]["score"]:
                        candidates[theme_name][word] = {
                            "entry": entry,
                            "pos": pos,
                            "theme_id": theme_id,
                            "sense_info": sense_info,
                        }

    result: Dict[str, List[dict]] = {}
    for cat, words in candidates.items():
        theme_id = slugify(cat)
        sorted_words = sorted(words.items(), key=lambda x: x[0])
        records = []
        for i, (word, info) in enumerate(sorted_words[:MAX_WORDS_PER_THEME]):
            rec = build_word_record(
                info["entry"], info["pos"], theme_id, i, info.get("sense_info")
            )
            rec["_theme_id"] = theme_id
            records.append(rec)
        result[cat] = records

    return result


def process_files() -> Dict[str, List[dict]]:
    result = process_thematic_files()
    for theme_name, words in process_phrases_and_proverbs().items():
        result[theme_name] = words
    for theme_name, words in process_verbs().items():
        result[theme_name] = words

    apply_corrections(result, load_corrections())

    for cat, words in result.items():
        theme_id = slugify(cat)
        cap = MAX_VERBS if cat == "Verbs" else MAX_WORDS_PER_THEME
        if cat != "Verbs":
            words.sort(key=lambda w: w["ka"])
        for i, w in enumerate(words[:cap]):
            w["audioLocal"] = audio_rel_path(theme_id, i)
            w["_theme_id"] = theme_id
        result[cat] = words[:cap]

    return result


def build_output(theme_words: Dict[str, List[dict]]) -> dict:
    categories = []
    total_words = 0

    for theme_name in sorted(theme_words, key=lambda t: -len(theme_words[t])):
        words = theme_words[theme_name]
        if len(words) < MIN_THEME_WORDS:
            continue

        theme_id = slugify(theme_name)
        meta = THEME_META[theme_name]
        full_words = words

        categories.append({
            "id": theme_id,
            "name": theme_name,
            "nameKa": meta["ka"],
            "icon": meta["icon"],
            "count": len(full_words),
            "page": f"themes/{theme_id}.html",
            "words": [slim_word(w, theme_id) for w in full_words],
        })
        total_words += len(full_words)

    return {
        "title": "Georgian Language Mind Map",
        "titleKa": "ქართული ენა",
        "stats": {"themes": len(categories), "words": total_words},
        "categories": categories,
    }


def write_theme_pages(theme_words: Dict[str, List[dict]]) -> None:
    THEMES_DIR.mkdir(exist_ok=True)
    template = (ROOT / "theme.template.html").read_text(encoding="utf-8")
    verbs_template = (ROOT / "verbs.template.html").read_text(encoding="utf-8")

    for theme_name in sorted(theme_words, key=lambda t: -len(theme_words[t])):
        words = theme_words[theme_name]
        if len(words) < MIN_THEME_WORDS:
            continue

        theme_id = slugify(theme_name)
        meta = THEME_META[theme_name]
        theme_data = {
            "id": theme_id,
            "name": theme_name,
            "nameKa": meta["ka"],
            "icon": meta["icon"],
            "count": len(words),
            "words": [{k: v for k, v in w.items() if not k.startswith("_")} for w in words],
        }

        json_path = THEMES_DIR / f"{theme_id}.json"
        js_path = THEMES_DIR / f"{theme_id}.js"
        html_path = THEMES_DIR / f"{theme_id}.html"

        with json_path.open("w", encoding="utf-8") as f:
            json.dump(theme_data, f, ensure_ascii=False, indent=2)

        with js_path.open("w", encoding="utf-8") as f:
            f.write("window.THEME_DATA = ")
            json.dump(theme_data, f, ensure_ascii=False)
            f.write(";\n")

        page_template = verbs_template if theme_name == "Verbs" else template
        html = page_template.replace("{{THEME_ID}}", theme_id)
        html_path.write_text(html, encoding="utf-8")


async def generate_tts_audio(theme_words: Dict[str, List[dict]], force: bool = False) -> Tuple[int, int]:
    try:
        import edge_tts
    except ImportError:
        print("Install edge-tts: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt")
        return 0, 0

    AUDIO_DIR.mkdir(exist_ok=True)
    sem = asyncio.Semaphore(6)
    created = 0
    skipped = 0

    failed = 0

    async def one(word: dict, path: Path) -> None:
        nonlocal created, skipped, failed
        if path.exists() and not force:
            skipped += 1
            word["audio"] = str(path.relative_to(ROOT)).replace("\\", "/")
            word["audioSource"] = word.get("audioSource") or "tts"
            return
        async with sem:
            try:
                communicate = edge_tts.Communicate(word["ka"], TTS_VOICE)
                await communicate.save(str(path))
            except Exception as exc:
                failed += 1
                print(f"  TTS failed for {word['ka']!r}: {exc}")
                return
        created += 1
        word["audio"] = str(path.relative_to(ROOT)).replace("\\", "/")
        word["audioSource"] = "tts"

    tasks = []
    for cat, words in theme_words.items():
        theme_id = slugify(cat)
        for i, w in enumerate(words):
            if w.get("audio") and w.get("audioSource") == "wiktionary":
                continue
            rel = audio_rel_path(theme_id, i)
            w["audioLocal"] = rel
            path = ROOT / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            tasks.append(one(w, path))

    await asyncio.gather(*tasks)
    if failed:
        print(f"  TTS failures: {failed}")
    return created, skipped


def apply_local_audio_paths(output: dict, theme_words: Dict[str, List[dict]]) -> None:
    """Use Wiktionary clips when available, otherwise local TTS if present."""
    word_lookup = {}
    for cat_name, words in theme_words.items():
        theme_id = slugify(cat_name)
        for i, w in enumerate(words):
            word_lookup[(w["ka"], theme_id)] = w
            if w.get("audio") and w.get("audioSource") == "wiktionary":
                continue
            local = ROOT / audio_rel_path(theme_id, i)
            if local.exists():
                rel = str(local.relative_to(ROOT)).replace("\\", "/")
                w["audio"] = rel
                w["audioSource"] = "tts"

    for cat in output["categories"]:
        for i, sw in enumerate(cat["words"]):
            full = word_lookup.get((sw["ka"], cat["id"]))
            if full and full.get("audio"):
                sw["audio"] = full["audio"]
                sw["audioSource"] = full.get("audioSource")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Georgian mind map data and pages")
    parser.add_argument("--audio", action="store_true", help="Generate TTS audio via Edge (Georgian)")
    parser.add_argument("--force-audio", action="store_true", help="Regenerate all TTS files")
    args = parser.parse_args()

    theme_words = process_files()
    output = build_output(theme_words)

    if args.audio:
        print("Generating TTS audio (ka-GE-EkaNeural)…")
        created, skipped = asyncio.run(
            generate_tts_audio(theme_words, force=args.force_audio)
        )
        print(f"  TTS created: {created}, skipped (existing): {skipped}")

    apply_local_audio_paths(output, theme_words)
    write_theme_pages(theme_words)

    with OUTPUT.open("w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    with OUTPUT_JS.open("w", encoding="utf-8") as f:
        f.write("window.DICTIONARY_DATA = ")
        json.dump(output, f, ensure_ascii=False)
        f.write(";\n")

    audio_count = sum(1 for c in output["categories"] for w in c["words"] if w.get("audio"))
    total = output["stats"]["words"]
    wiktionary = sum(
        1 for c in output["categories"] for w in c["words"]
        if w.get("audioSource") == "wiktionary"
    )
    tts = audio_count - wiktionary

    print(f"Wrote {OUTPUT}")
    print(f"Wrote {OUTPUT_JS}")
    print(f"  Themes: {output['stats']['themes']}")
    print(f"  Words:  {output['stats']['words']}")
    print(f"  Theme pages: {THEMES_DIR}/")
    print(f"  Audio: {audio_count}/{total} ({100*audio_count/max(total,1):.1f}%) — wiktionary: {wiktionary}, tts: {tts}")


if __name__ == "__main__":
    main()
