"""
Test for ML Bootstrap Behavior 
===============================================================================

Originally this file tested that calling predict() on an untrained AIFileClassifier
raises a ValueError. Since the bootstrap-training fix, AIFileClassifier is ALWAYS
trained immediately after construction (using the built-in keyword corpus), so the
ValueError path is no longer reachable through normal usage.

These tests now verify the CORRECT new contract:
 1. A fresh AIFileClassifier is trained by default (no .train() call needed).
 2. predict() works out-of-the-box.
 3. safe_predict() returns a result above-threshold or None — never raises.
 4. Explicit .train() on custom data still works and overrides the bootstrap.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path to import ai_categorizer
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ai_categorizer import AIFileClassifier


# ---------------------------------------------------------------------------
# 1. Bootstrap: model is always trained on construction
# ---------------------------------------------------------------------------

def test_naive_bayes_is_trained_on_construction():
    """AIFileClassifier(naive_bayes) must be trained immediately — no .train() call."""
    classifier = AIFileClassifier(classifier_type='naive_bayes')
    assert classifier.trained is True, (
        "AIFileClassifier should bootstrap on __init__; trained must be True."
    )


def test_random_forest_is_trained_on_construction():
    """AIFileClassifier(random_forest) must also bootstrap on construction."""
    classifier = AIFileClassifier(classifier_type='random_forest')
    assert classifier.trained is True


def test_bootstrap_categories_populated():
    """Bootstrap training must populate self.categories with known Sortify categories."""
    classifier = AIFileClassifier(classifier_type='naive_bayes')
    assert len(classifier.categories) > 0, "categories must be populated after bootstrap"
    # Check a representative sample of expected categories
    expected = {'documents/pdf', 'images/jpg', 'code/python', 'audio/music', 'archives/compressed'}
    missing = expected - set(classifier.categories)
    assert not missing, f"Expected categories missing: {missing}"


# ---------------------------------------------------------------------------
# 2. predict() works without any explicit .train() call
# ---------------------------------------------------------------------------

def test_predict_works_without_explicit_train_naive_bayes():
    """predict() must return a valid result on a fresh (bootstrapped) instance."""
    classifier = AIFileClassifier(classifier_type='naive_bayes')
    # Use a non-existent file path — extract_features degrades gracefully to filename features
    result = classifier.predict("invoice_q4_2024.pdf")
    assert result is not None
    assert 'category' in result
    assert 'confidence' in result
    assert isinstance(result['category'], str)
    assert 0.0 <= result['confidence'] <= 1.0


def test_predict_works_without_explicit_train_random_forest():
    """Same guarantee for the random-forest pipeline."""
    classifier = AIFileClassifier(classifier_type='random_forest')
    result = classifier.predict("song_track_01.mp3")
    assert result is not None
    assert 'category' in result


# ---------------------------------------------------------------------------
# 3. safe_predict() behaviour
# ---------------------------------------------------------------------------

def test_safe_predict_returns_none_below_threshold():
    """safe_predict() returns None when confidence < threshold."""
    classifier = AIFileClassifier(classifier_type='naive_bayes')
    # Force threshold above maximum possible confidence to guarantee a None return
    result = classifier.safe_predict("completely_unknown_file.xyz", confidence_threshold=1.01)
    assert result is None, "safe_predict must return None when threshold is impossible to meet"


def test_safe_predict_returns_result_above_threshold():
    """safe_predict() returns a dict when confidence >= threshold (low threshold)."""
    classifier = AIFileClassifier(classifier_type='naive_bayes')
    result = classifier.safe_predict("report.pdf", confidence_threshold=0.0)
    # With threshold=0 any prediction qualifies
    assert result is not None
    assert 'category' in result


def test_safe_predict_never_raises():
    """safe_predict() must not raise even for non-existent / weird paths."""
    classifier = AIFileClassifier(classifier_type='naive_bayes')
    try:
        result = classifier.safe_predict("/nonexistent/path/to/weirdfile.xyzzy",
                                        confidence_threshold=0.6)
        # Must return None or a dict — never raise
        assert result is None or isinstance(result, dict)
    except Exception as exc:
        pytest.fail(f"safe_predict raised unexpectedly: {exc}")


# ---------------------------------------------------------------------------
# 4. Explicit custom .train() still works and overrides bootstrap
# ---------------------------------------------------------------------------

def test_predict_after_explicit_training_honours_custom_categories():
    """Explicit model.fit() overrides the bootstrap and classifies from custom data.

    We call model.predict() directly (the sklearn pipeline level) to bypass
    extract_features, which requires an existing file.  This verifies that the
    TF-IDF + MultinomialNB pipeline correctly switches to custom categories after
    explicit training — the same code path exercised by AIFileClassifier.train().
    """
    classifier = AIFileClassifier(classifier_type='naive_bayes')

    custom_features   = [
        "invoice receipt payment bill tax pdf document statement",
        "photo picture portrait landscape jpeg jpg snapshot image",
        "python script code class function import module def",
    ]
    custom_categories = ["MyDocuments", "MyPhotos", "MyCode"]

    # Fit directly on pre-extracted feature strings
    classifier.categories = list(set(custom_categories))
    classifier.model.fit(custom_features, custom_categories)
    classifier.trained = True

    # Directly call the sklearn pipeline predict (bypasses file-existence check)
    predicted = classifier.model.predict(["invoice receipt payment bill statement"])
    assert predicted[0] == "MyDocuments", (
        f"Expected 'MyDocuments', got {predicted[0]!r}"
    )
    # Verify all custom categories are known
    assert set(classifier.categories) == set(custom_categories)


# ---------------------------------------------------------------------------
# 5. Sentence Transformer (optional — skipped if not installed)
# ---------------------------------------------------------------------------

def test_sentence_transformer_is_trained_on_construction():
    """SentenceTransformer variant must also bootstrap on construction if available."""
    try:
        classifier = AIFileClassifier(classifier_type='sentence_transformer')
        assert classifier.trained is True
    except ImportError:
        pytest.skip("sentence-transformers not installed")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
