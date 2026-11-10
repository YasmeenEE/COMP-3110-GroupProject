
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def calculate_context_similarity(old_context, new_context):
    """
    Compare two contexts using TF-IDF and Cosine Similarity.

    old_context and new_context are dictionaries
    containing 'above' and 'below' lists.
    """

    old_text = " ".join(
        old_context["above"] + old_context["below"]
    )

    new_text = " ".join(
        new_context["above"] + new_context["below"]
    )

    # Handle empty contexts
    if not old_text.strip() and not new_text.strip():
        return 1.0

    if not old_text.strip() or not new_text.strip():
        return 0.0

    # Convert contexts into TF-IDF vectors
    vectorizer = TfidfVectorizer(
        token_pattern=r"(?u)\b\w+\b"
    )

    vectors = vectorizer.fit_transform([
        old_text,
        new_text
    ])

    # Calculate cosine similarity
    score = cosine_similarity(
        vectors[0:1],
        vectors[1:2]
    )[0][0]

    return float(score)
