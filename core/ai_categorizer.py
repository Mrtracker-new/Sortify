import os
import re
import pickle
import logging
import hashlib
import numpy as np
from pathlib import Path
from collections import OrderedDict
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


class LRUCache:
    """LRU (Least Recently Used) Cache implementation with automatic eviction.
    
    This cache maintains a maximum size and automatically evicts the oldest
    item when the cache exceeds max_size. Uses OrderedDict for efficient
    O(1) operations and proper ordering.
    """
    def __init__(self, max_size=1000):
        """Initialize LRU cache with maximum size.
        
        Args:
            max_size: Maximum number of items to store in cache (default: 1000)
        """
        self.cache = OrderedDict()
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def get(self, key):
        """Get an item from cache and mark it as recently used.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Cached value if found, None otherwise
        """
        if key in self.cache:
            # Move to end to mark as recently used
            self.cache.move_to_end(key)
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None
    
    def put(self, key, value):
        """Add or update an item in cache.
        
        If the item exists, it's moved to the end (most recent).
        If cache exceeds max_size, the oldest item is evicted.
        
        Args:
            key: Cache key
            value: Value to store
        """
        if key in self.cache:
            # Update existing item and move to end
            self.cache.move_to_end(key)
        self.cache[key] = value
        
        # Evict oldest item if cache size exceeded
        if len(self.cache) > self.max_size:
            self.cache.popitem(last=False)  # Remove oldest (first) item
    
    def clear(self):
        """Clear all items from cache."""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self):
        """Get cache statistics.
        
        Returns:
            dict: Dictionary with cache hits, misses, size, and hit rate
        """
        total = self.hits + self.misses
        hit_rate = (self.hits / total * 100) if total > 0 else 0
        return {
            'hits': self.hits,
            'misses': self.misses,
            'size': len(self.cache),
            'max_size': self.max_size,
            'hit_rate': round(hit_rate, 2)
        }


class ContentCache:
    """Cache for textract-extracted content to avoid repeated slow processing.
    
    Uses file hash (based on path, size, and modification time) as cache key.
    This prevents repeated expensive textract operations on the same files.
    """
    def __init__(self, max_size=500):
        """Initialize content cache with LRU eviction.
        
        Args:
            max_size: Maximum number of content items to cache (default: 500)
        """
        self.cache = LRUCache(max_size=max_size)
    
    def get_file_hash(self, file_path):
        """Generate a unique hash for a file based on path, size, and mtime.
        
        Args:
            file_path: Path object for the file
            
        Returns:
            str: MD5 hash of file metadata
        """
        try:
            stat = file_path.stat()
            hash_input = f"{file_path}_{stat.st_size}_{stat.st_mtime}"
            return hashlib.md5(hash_input.encode()).hexdigest()
        except Exception as e:
            logging.debug(f"Error generating file hash for {file_path}: {e}")
            return None
    
    def get_content(self, file_path):
        """Retrieve cached content for a file.
        
        Args:
            file_path: Path object for the file
            
        Returns:
            str: Cached content if available, None otherwise
        """
        file_hash = self.get_file_hash(file_path)
        if file_hash is None:
            return None
        return self.cache.get(file_hash)
    
    def set_content(self, file_path, content):
        """Cache extracted content for a file.
        
        Args:
            file_path: Path object for the file
            content: Extracted content to cache
        """
        file_hash = self.get_file_hash(file_path)
        if file_hash is not None:
            self.cache.put(file_hash, content)
    
    def get_stats(self):
        """Get cache statistics.
        
        Returns:
            dict: Cache statistics including hits, misses, and hit rate
        """
        return self.cache.get_stats()
    
    def clear(self):
        """Clear all cached content."""
        self.cache.clear()


class AIFileClassifier:
    """AI-based file classifier using Naive Bayes with content analysis"""
    def __init__(self, model_path=None, classifier_type='naive_bayes'):
        # Create a pipeline with improved vectorizer and classifier
        self.classifier_type = classifier_type
        self._create_pipeline()
        self.trained = False
        self.categories = []
        # Use LRU cache with automatic eviction to prevent memory leaks
        self.feature_cache = LRUCache(max_size=1000)
        # Add content cache specifically for textract-extracted content
        self.content_cache = ContentCache(max_size=500)
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
        
        # Create cache key using file path and modification time (if file exists)
        try:
            if file_path.exists():
                mtime = file_path.stat().st_mtime
                cache_key = f"{file_path}:{mtime}"
                
                # Check cache first
                cached_features = self.feature_cache.get(cache_key)
                if cached_features is not None:
                    logging.debug(f"Cache hit for {file_path}")
                    return cached_features
            else:
                cache_key = None
        except Exception as e:
            logging.debug(f"Error checking cache for {file_path}: {e}")
            cache_key = None
        
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
                # Check content cache first to avoid slow textract processing
                cached_content = self.content_cache.get_content(file_path)
                if cached_content is not None:
                    logging.debug(f"Content cache hit for {file_path}")
                    features.append(cached_content)
                    content_extracted = True
                else:
                    # Use textract to extract text from many file formats
                    content = textract.process(str(file_path), encoding='utf-8')
                    if content:
                        # Limit content size to avoid memory issues
                        text_content = content.decode('utf-8')[:5000]
                        # Cache the extracted content for future use
                        self.content_cache.set_content(file_path, text_content)
                        features.append(text_content)
                        content_extracted = True
                        logging.debug(f"Successfully extracted and cached content with textract from {file_path}")
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
        
        # Join features and cache the result
        result = ' '.join(features)
        
        # Store in cache if we have a valid cache key
        if cache_key is not None:
            self.feature_cache.put(cache_key, result)
            logging.debug(f"Cached features for {file_path}")
        
        return result
    
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
        
    def train_from_directory(self, directory_path, test_size=0.2, min_samples_per_category=3, recursive=True, label_depth=None):
        """Train the classifier using files from a directory structure
        
        By default, this will recursively scan subfolders under the root and use the
        relative folder path as the category label (e.g., "ai_images/chatgpt").
        
        Args:
            directory_path: Path to the root directory containing category subdirectories
            test_size: Fraction of data to use for testing (default: 0.2)
            min_samples_per_category: Minimum number of samples required per category
            recursive: Whether to scan nested subfolders (default: True)
            label_depth: Limit label to the first N path components relative to root (default: None = full path)
        
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
        
        if recursive:
            # Recursively walk all files and derive labels from relative parent path
            for file_path in directory_path.rglob('*'):
                if file_path.is_file():
                    try:
                        rel_parent = file_path.parent.relative_to(directory_path)
                    except ValueError:
                        # Should not happen, but guard anyway
                        continue
                    # Ignore files that are directly under the root (no category)
                    if rel_parent == Path('.') or str(rel_parent).strip() == '':
                        continue
                    parts = rel_parent.parts
                    if label_depth is not None and isinstance(label_depth, int) and label_depth > 0:
                        parts = parts[:label_depth]
                    category = '/'.join(parts)
                    file_paths.append(str(file_path))
                    categories.append(category)
                    category_counts[category] = category_counts.get(category, 0) + 1
        else:
            # Backward-compatible non-recursive behavior (immediate subfolders only)
            for category_dir in directory_path.iterdir():
                if category_dir.is_dir():
                    category = category_dir.name
                    category_files = []
                    for file_path in category_dir.glob('*'):
                        if file_path.is_file():
                            file_paths.append(str(file_path))
                            categories.append(category)
                            category_files.append(str(file_path))
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
        logging.info(
            f"Training from directory with {len(file_paths)} files in {len(set(categories))} categories (recursive={recursive}, label_depth={label_depth})"
        )
        metrics = self.train_with_split(file_paths, categories, test_size)
        
        # Add category distribution information to metrics
        metrics['category_distribution'] = category_counts
        metrics['success'] = True
        
        return metrics
