import os
import re
import pickle
import logging
import hashlib
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer  # Changed from CountVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, classification_report
from datetime import datetime

# Try to import textract, but make it optional
try:
    import textract  # For extracting text from various file formats
    TEXTRACT_AVAILABLE = True
except ImportError:
    logging.warning("textract module not found. Advanced text extraction will be limited.")
    TEXTRACT_AVAILABLE = False

class AIFileClassifier:
    """AI-based file classifier using Naive Bayes with content analysis"""
    def __init__(self, model_path=None, classifier_type='naive_bayes'):
        # Create a pipeline with improved vectorizer and classifier
        self.classifier_type = classifier_type
        self._create_pipeline()
        self.trained = False
        self.categories = []
        self.feature_cache = {}  # Cache for extracted features
        self.cache_hits = 0
        self.cache_misses = 0
        self.max_cache_size = 1000  # Maximum number of items in cache
        self.last_training_time = None
        self.training_accuracy = None
        self.model_version = 1
        
        # Load existing model if available
        if model_path and os.path.exists(model_path):
            self.load_model(model_path)
            
    def _create_pipeline(self):
        """Create the ML pipeline based on the selected classifier type"""
        if self.classifier_type == 'random_forest':
            self.model = Pipeline([
                ('vectorizer', TfidfVectorizer(analyzer='word', ngram_range=(1, 3), max_features=5000)),
                ('classifier', RandomForestClassifier(n_estimators=100, random_state=42))
            ])
        else:  # Default to naive_bayes
            self.model = Pipeline([
                ('vectorizer', TfidfVectorizer(analyzer='word', ngram_range=(1, 3), max_features=5000)),
                ('classifier', MultinomialNB())
            ])
    
    def extract_features(self, file_path):
        """Extract features from a file for classification including content analysis
        
        Args:
            file_path: Path to the file to extract features from
            
        Returns:
            str: Space-joined features extracted from the file
        """
        file_path = Path(file_path)
        features = []
        
        # Add filename as a feature
        features.append(file_path.name)
        
        # Add stem (filename without extension)
        features.append(file_path.stem)
        
        # Extract words from filename
        words = re.findall(r'[a-zA-Z]+', file_path.stem)
        features.extend(words)
        
        # Check if file exists before attempting to extract content
        if not file_path.exists():
            logging.warning(f"File does not exist: {file_path}")
            return ' '.join(features)
            
        # Try to extract content from various file types
        content_extracted = False
        
        # First try textract if available
        if TEXTRACT_AVAILABLE:
            try:
                # Use textract to extract text from many file formats
                content = textract.process(str(file_path), encoding='utf-8')
                if content:
                    # Limit content size to avoid memory issues
                    text_content = content.decode('utf-8')[:5000]
                    features.append(text_content)
                    content_extracted = True
                    logging.debug(f"Successfully extracted content with textract from {file_path}")
            except Exception as e:
                logging.debug(f"Could not extract content with textract from {file_path}: {e}")
        
        # Fall back to basic text extraction if content wasn't extracted with textract
        if not content_extracted and self._is_text_file(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(2000)  # Read first 2000 chars
                    features.append(content)
                    logging.debug(f"Successfully extracted content with basic method from {file_path}")
            except Exception as e:
                logging.debug(f"Could not extract content from {file_path}: {e}")
        
        return ' '.join(features)
    
    def _is_text_file(self, file_path):
        """Check if file is likely a text file based on extension
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if the file has a known text extension, False otherwise
        """
        text_extensions = [
            # Documentation formats
            '.txt', '.md', '.rst', '.rtf', '.tex', '.adoc', '.wiki',
            # Data formats
            '.csv', '.tsv', '.json', '.xml', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
            # Web formats
            '.html', '.htm', '.css', '.scss', '.sass', '.less', '.js', '.jsx', '.ts', '.tsx',
            # Programming languages
            '.py', '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.php', '.rb', '.pl', '.swift',
            '.go', '.rs', '.kt', '.scala', '.sh', '.bash', '.ps1', '.bat', '.sql',
            # Log and config files
            '.log', '.properties', '.env'
        ]
        return file_path.suffix.lower() in text_extensions
    
    def train(self, file_paths, categories):
        """Train the classifier on file examples
        
        Args:
            file_paths: List of file paths
            categories: List of corresponding categories
        """
        if len(file_paths) != len(categories):
            raise ValueError("Number of files and categories must match")
            
        # Extract features for each file
        features = [self.extract_features(f) for f in file_paths]
        
        # Store unique categories
        self.categories = list(set(categories))
        
        # Train the model
        self.model.fit(features, categories)
        self.trained = True
        logging.info(f"Trained AI classifier on {len(file_paths)} files with {len(self.categories)} categories")
    
    def predict(self, file_path):
        """Predict category for a file with confidence score
        
        Args:
            file_path: Path to the file to categorize
            
        Returns:
            dict: Prediction result containing category and confidence score,
                  or None if model is not trained
        """
        if not self.trained:
            logging.warning("AI classifier not trained yet")
            return None
        
        # Check if file exists
        if not Path(file_path).exists():
            logging.warning(f"File does not exist: {file_path}")
            return {
                'category': 'Unknown',
                'confidence': 0.0,
                'error': 'File not found'
            }
            
        try:
            # Extract features
            features = self.extract_features(file_path)
            
            # Get prediction and probability scores
            category = self.model.predict([features])[0]
            probabilities = self.model.predict_proba([features])[0]
            
            # Find the confidence score (probability) for the predicted category
            category_index = list(self.model.classes_).index(category)
            confidence = probabilities[category_index]
            
            # Get top 3 alternative categories with their confidence scores
            alternatives = []
            sorted_indices = probabilities.argsort()[::-1]  # Sort indices by probability (descending)
            
            for i in sorted_indices[:3]:  # Get top 3
                if self.model.classes_[i] != category:  # Skip the main prediction
                    alternatives.append({
                        'category': self.model.classes_[i],
                        'confidence': round(float(probabilities[i]), 3)
                    })
            
            return {
                'category': category,
                'confidence': round(float(confidence), 3),
                'alternatives': alternatives
            }
        except Exception as e:
            logging.error(f"Error predicting category for {file_path}: {e}")
            return {
                'category': 'Unknown',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def save_model(self, model_path):
        """Save the trained model to disk"""
        if not self.trained:
            logging.warning("Cannot save untrained model")
            return False
            
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            
            # Save model and categories
            with open(model_path, 'wb') as f:
                pickle.dump((self.model, self.categories), f)
                
            logging.info(f"Saved AI classifier model to {model_path}")
            return True
        except Exception as e:
            logging.error(f"Error saving model: {e}")
            return False
    
    def load_model(self, model_path):
        """Load a trained model from disk"""
        try:
            with open(model_path, 'rb') as f:
                self.model, self.categories = pickle.load(f)
                self.trained = True
                
            logging.info(f"Loaded AI classifier model from {model_path}")
            return True
        except Exception as e:
            logging.error(f"Error loading model: {e}")
            return False

    def evaluate(self, test_file_paths, test_categories):
        """Evaluate model performance on test data with detailed metrics
        
        Args:
            test_file_paths: List of file paths for testing
            test_categories: List of corresponding categories
            
        Returns:
            dict: Dictionary containing various performance metrics
                 (accuracy, precision, recall, f1_score)
        """
        if not self.trained:
            logging.warning("Cannot evaluate untrained model")
            return {'accuracy': 0.0}
            
        try:
            # Import metrics functions
            from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
            
            # Extract features for test files
            features = [self.extract_features(f) for f in test_file_paths]
            
            # Get predictions
            predictions = self.model.predict(features)
            
            # Calculate metrics
            accuracy = accuracy_score(test_categories, predictions)
            
            # For multi-class classification, we use weighted averaging
            precision = precision_score(test_categories, predictions, average='weighted', zero_division=0)
            recall = recall_score(test_categories, predictions, average='weighted', zero_division=0)
            f1 = f1_score(test_categories, predictions, average='weighted', zero_division=0)
            
            # Generate detailed report
            report = classification_report(test_categories, predictions, output_dict=True, zero_division=0)
            
            # Log results
            logging.info(f"AI classifier evaluation results:")
            logging.info(f"  Accuracy:  {accuracy:.3f}")
            logging.info(f"  Precision: {precision:.3f}")
            logging.info(f"  Recall:    {recall:.3f}")
            logging.info(f"  F1 Score:  {f1:.3f}")
            
            # Return comprehensive metrics
            return {
                'accuracy': round(float(accuracy), 3),
                'precision': round(float(precision), 3),
                'recall': round(float(recall), 3),
                'f1_score': round(float(f1), 3),
                'report': report,
                'categories': list(set(test_categories)),
                'test_size': len(test_file_paths)
            }
        except Exception as e:
            logging.error(f"Error during model evaluation: {e}")
            return {'accuracy': 0.0, 'error': str(e)}

    def train_with_split(self, file_paths, categories, test_size=0.2):
        """Train model with automatic train/test split and return detailed evaluation metrics
        
        Args:
            file_paths: List of file paths for training
            categories: List of corresponding categories
            test_size: Fraction of data to use for testing (default: 0.2)
            
        Returns:
            dict: Dictionary containing model performance metrics
        """
        if len(file_paths) < 5:
            logging.warning("Too few samples for reliable training and evaluation")
            return {'accuracy': 0.0, 'error': 'Too few samples'}
            
        try:
            # Split data into training and testing sets
            X_train, X_test, y_train, y_test = train_test_split(
                file_paths, categories, test_size=test_size, random_state=42, stratify=categories if len(set(categories)) > 1 else None
            )
            
            # Log split information
            logging.info(f"Split data into {len(X_train)} training and {len(X_test)} testing samples")
            
            # Train the model
            self.train(X_train, y_train)
            
            # Evaluate and get detailed metrics
            metrics = self.evaluate(X_test, y_test)
            
            # Add training information to metrics
            metrics['training_samples'] = len(X_train)
            metrics['testing_samples'] = len(X_test)
            metrics['categories_count'] = len(set(categories))
            
            return metrics
        except Exception as e:
            logging.error(f"Error during train_with_split: {e}")
            return {'accuracy': 0.0, 'error': str(e)}
        
    def train_from_directory(self, directory_path, test_size=0.2, min_samples_per_category=3):
        """Train the classifier using files from a directory structure
        
        The directory should be organized with subdirectories as categories
        and files within each subdirectory as examples of that category.
        
        Args:
            directory_path: Path to the root directory containing category subdirectories
            test_size: Fraction of data to use for testing (default: 0.2)
            min_samples_per_category: Minimum number of samples required per category
            
        Returns:
            dict: Dictionary containing model performance metrics or
                  error information if training failed
        """
        directory_path = Path(directory_path)
        if not directory_path.exists() or not directory_path.is_dir():
            logging.error(f"Training directory not found: {directory_path}")
            return {'error': 'Training directory not found', 'success': False}
            
        file_paths = []
        categories = []
        category_counts = {}
        
        # Iterate through category directories
        for category_dir in directory_path.iterdir():
            if category_dir.is_dir():
                category = category_dir.name
                category_files = []
                
                # Get all files in this category directory
                for file_path in category_dir.glob('*'):
                    if file_path.is_file():
                        file_paths.append(str(file_path))
                        categories.append(category)
                        category_files.append(str(file_path))
                
                # Track count of files per category
                category_counts[category] = len(category_files)
        
        if not file_paths:
            logging.warning(f"No training files found in {directory_path}")
            return {'error': 'No training files found', 'success': False}
        
        # Check if we have enough samples per category
        insufficient_categories = [cat for cat, count in category_counts.items() if count < min_samples_per_category]
        if insufficient_categories:
            logging.warning(f"Insufficient samples for categories: {', '.join(insufficient_categories)}")
            logging.warning(f"Each category needs at least {min_samples_per_category} samples for reliable training")
            return {
                'error': f"Insufficient samples for {len(insufficient_categories)} categories",
                'insufficient_categories': insufficient_categories,
                'category_counts': category_counts,
                'success': False
            }
            
        # Train the model with the collected files
        logging.info(f"Training from directory with {len(file_paths)} files in {len(set(categories))} categories")
        metrics = self.train_with_split(file_paths, categories, test_size)
        
        # Add category distribution information to metrics
        metrics['category_distribution'] = category_counts
        metrics['success'] = True
        
        return metrics