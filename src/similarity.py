from rapidfuzz import fuzz

def calculate_content_similarity(old_line, new_line):
    score = fuzz.ratio(old_line, new_line)
    return score / 100