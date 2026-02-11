"""
Test for FL-002: Untrained Model Usage Fix
==========================================

This test verifies that calling predict() on an untrained AIFileClassifier
raises a ValueError with a clear message instead of silently returning None.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path to import ai_categorizer
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.ai_categorizer import AIFileClassifier


def test_predict_untrained_naive_bayes_raises_exception():
    """Test that calling predict() on untrained Naive Bayes model raises ValueError"""
    classifier = AIFileClassifier(classifier_type='naive_bayes')
    
    with pytest.raises(ValueError, match="must be trained before prediction"):
        classifier.predict("test_file.pdf")


def test_predict_untrained_random_forest_raises_exception():
    """Test that calling predict() on untrained Random Forest model raises ValueError"""
    classifier = AIFileClassifier(classifier_type='random_forest')
    
    with pytest.raises(ValueError, match="must be trained before prediction"):
        classifier.predict("test_file.pdf")


def test_predict_untrained_sentence_transformer_raises_exception():
    """Test that calling predict() on untrained Sentence Transformer model raises ValueError"""
    try:
        classifier = AIFileClassifier(classifier_type='sentence_transformer')
        
        with pytest.raises(ValueError, match="must be trained before prediction"):
            # Create a dummy file for testing
            test_file = Path(__file__).parent / "test_dummy.txt"
            test_file.touch()
            
            try:
                classifier.predict(str(test_file))
            finally:
                # Clean up
                if test_file.exists():
                    test_file.unlink()
                    
    except ImportError:
        pytest.skip("sentence-transformers not installed")


def test_predict_after_training_works():
    """Test that predict() works normally after training the model"""
    classifier = AIFileClassifier(classifier_type='naive_bayes')
    
    # Train with sample data
    sample_files = ["invoice.pdf", "photo.jpg", "script.py"]
    sample_categories = ["Documents", "Photos", "Code"]
    
    classifier.train(sample_files, sample_categories)
    
    # Prediction should work now
    result = classifier.predict("new_invoice.pdf")
    
    # Should return a dict with category and confidence
    assert result is not None
    assert 'category' in result
    assert 'confidence' in result
    assert result['category'] in sample_categories


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
