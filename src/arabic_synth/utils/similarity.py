# --- utils/similarity.py ---
import re, json, hashlib
from typing import List, Dict, Any, Tuple
from collections import Counter

AR_DIAC = re.compile(r'[\u0617-\u061A\u064B-\u0652\u0670\u0653-\u065F]')
AR_PUNCT = re.compile(r'[^\w\s\u0600-\u06FF]')
AR_TATWEEL = re.compile(r'[\u0640]')
SPACE = re.compile(r'\s+')

def norm_ar(text: str) -> str:
    if not text: return ""
    t = text
    t = t.replace("أ","ا").replace("إ","ا").replace("آ","ا")
    t = t.replace("ى","ي").replace("ۀ","ه").replace("ة","ه")
    t = AR_TATWEEL.sub("", t)
    t = AR_DIAC.sub("", t)
    t = AR_PUNCT.sub(" ", t)
    t = SPACE.sub(" ", t).strip()
    return t

def tokens(text: str) -> List[str]:
    return [w for w in norm_ar(text).split() if w]

def jaccard(a: List[str], b: List[str]) -> float:
    if not a or not b: return 0.0
    A, B = set(a), set(b)
    return len(A & B) / max(1, len(A | B))

def char_ngrams(s: str, n: int = 5) -> Counter:
    s = norm_ar(s)
    return Counter([s[i:i+n] for i in range(max(0, len(s)-n+1))])

def ngram_jaccard(a: str, b: str, n: int = 5) -> float:
    A, B = set(char_ngrams(a, n).keys()), set(char_ngrams(b, n).keys())
    if not A or not B: return 0.0
    return len(A & B) / len(A | B)

NUM_PATTERN = re.compile(r'\d+')

def numeric_overlap(a: str, b: str) -> float:
    A, B = set(NUM_PATTERN.findall(a)), set(NUM_PATTERN.findall(b))
    if not A or not B: return 0.0
    return len(A & B) / len(A | B)

def canonical_json(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",",":"))

def stable_hash(obj: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()[:16]
