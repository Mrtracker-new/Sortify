"""
Test async spaCy model loading functionality.

This module tests that the FileCategorizationAI class can:
1. Work without a spaCy model (basic pattern matching)
2. Accept a spaCy model after initialization via set_nlp_model()
3. Properly categorize files using both basic and AI modes
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from core.categorization import FileCategorizationAI


class MockNLP:
    """Mock spaCy NLP model for testing"""
    def __call__(self, text):
        return MockDoc()


class MockDoc:
    """Mock spaCy document"""
    def __init__(self):
        self.ents = []  # Named entities


class TestCategorizerWithoutSpacy:
    """Test categorizer functionality without spaCy model"""
    
    def test_categorizer_init_without_spacy(self):
        """Test categorizer can initialize without spaCy model"""
        cat = FileCategorizationAI(nlp=None)
        assert cat.nlp is None
        assert not cat.ai_enabled
    
    def test_categorize_pdf_without_spacy(self):
        """Test PDF categorization works without spaCy"""
        cat = FileCategorizationAI(nlp=None)
        # Create temporary test file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            test_file = Path(f.name)
        
        try:
            result = cat.categorize_file(str(test_file))
            assert result == "documents/pdf"
        finally:
            test_file.unlink()
    
    def test_categorize_image_without_spacy(self):
        """Test image categorization works without spaCy"""
        cat = FileCategorizationAI(nlp=None)
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            test_file = Path(f.name)
        
        try:
            result = cat.categorize_file(str(test_file))
            assert result == "images/jpg"
        finally:
            test_file.unlink()
    
    def test_categorize_code_without_spacy(self):
        """Test code file categorization works without spaCy"""
        cat = FileCategorizationAI(nlp=None)
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
            test_file = Path(f.name)
        
        try:
            result = cat.categorize_file(str(test_file))
            assert result == "code/python"
        finally:
            test_file.unlink()


class TestCategorizerSpacyInjection:
    """Test spaCy model injection after initialization"""
    
    def test_nlp_model_injection(self):
        """Test injecting spaCy model after initialization"""
        cat = FileCategorizationAI(nlp=None)
        assert not cat.ai_enabled
        assert cat.nlp is None
        
        # Inject mock spaCy model
        mock_nlp = MockNLP()
        cat.set_nlp_model(mock_nlp)
        
        assert cat.ai_enabled
        assert cat.nlp is not None
    
    def test_nlp_injection_with_none(self):
        """Test that injecting None doesn't enable AI"""
        cat = FileCategorizationAI(nlp=None)
        cat.set_nlp_model(None)
        
        # Should remain disabled
        assert not cat.ai_enabled
        assert cat.nlp is None
    
    def test_categorizer_init_with_nlp(self):
        """Test categorizer can be initialized with spaCy model"""
        mock_nlp = MockNLP()
        cat = FileCategorizationAI(nlp=mock_nlp)
        
        assert cat.ai_enabled
        assert cat.nlp is not None


class TestPatternBasedCategorization:
    """Test pattern-based categorization for various file types"""
    
    def test_ai_image_detection(self):
        """Test AI-generated image detection by filename pattern"""
        cat = FileCategorizationAI(nlp=None)
        
        # Create a temporary file with AI pattern in name
        with tempfile.NamedTemporaryFile(
            suffix='.png', 
            prefix='chatgpt_image_',
            delete=False
        ) as f:
            test_file = Path(f.name)
        
        try:
            result = cat.categorize_file(str(test_file))
            assert result.startswith("ai_images/")
        finally:
            test_file.unlink()
    
    def test_whatsapp_image_detection(self):
        """Test WhatsApp image detection by filename pattern"""
        cat = FileCategorizationAI(nlp=None)
        
        with tempfile.NamedTemporaryFile(
            suffix='.jpg',
            prefix='whatsapp_',
            delete=False
        ) as f:
            test_file = Path(f.name)
        
        try:
            result = cat.categorize_file(str(test_file))
            assert result == "images/whatsapp"
        finally:
            test_file.unlink()
    
    def test_archive_categorization(self):
        """Test archive file categorization"""
        cat = FileCategorizationAI(nlp=None)
        
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as f:
            test_file = Path(f.name)
        
        try:
            result = cat.categorize_file(str(test_file))
            assert result == "archives/compressed"
        finally:
            test_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
