import re
from difflib import SequenceMatcher

DIAGNOSIS_SIMILARITY_THRESHOLD = 0.85
PURPOSE_SIMILARITY_THRESHOLD = 0.72
PURPOSE_MIN_LENGTH = 24


def normalize_text(value):
    text = re.sub(r"[^\w\s]+", " ", (value or "").casefold(), flags=re.UNICODE)
    return re.sub(r"\s+", " ", text).strip()


def similar_enough(left, right, threshold):
    if not left or not right:
        return False
    if left == right:
        return True
    return SequenceMatcher(None, left, right).ratio() >= threshold


def diagnoses_are_similar(left, right):
    return similar_enough(normalize_text(left), normalize_text(right), DIAGNOSIS_SIMILARITY_THRESHOLD)


def purposes_are_similar(left, right):
    normalized_left = normalize_text(left)
    normalized_right = normalize_text(right)
    if min(len(normalized_left), len(normalized_right)) < PURPOSE_MIN_LENGTH:
        return False
    return similar_enough(normalized_left, normalized_right, PURPOSE_SIMILARITY_THRESHOLD)
