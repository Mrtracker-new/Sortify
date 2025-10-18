# PyInstaller hook for spaCy
from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os
import sys
import spacy

# Add spaCy data files
datas = collect_data_files('spacy')

# Add spaCy model data files
try:
    import en_core_web_sm
    model_path = en_core_web_sm.__path__[0]
    datas.append((model_path, 'en_core_web_sm'))
except ImportError:
    print("Warning: en_core_web_sm model not found. It will not be included in the package.")

# Add hidden imports for spaCy and its dependencies
hiddenimports = collect_submodules('spacy')
hiddenimports.extend([
    'en_core_web_sm',
    'spacy.kb',
    'spacy.tokens',
    'spacy.lang.en',
    'spacy.lang.en.stop_words',
    'spacy.lang.punctuation',
    'spacy.language',
    'spacy.lexeme',
    'spacy.tokens.underscore',
    'spacy.matcher.matcher',
    'spacy.pipeline',
    'spacy.syntax',
    'spacy.vocab',
    'spacy.attrs',
    'spacy.parts_of_speech',
    'spacy_legacy',
    'spacy_legacy.tokenizer_exceptions',
    'spacy_legacy.lookups',
    'spacy_legacy.lemmatizer',
    'spacy_legacy.architectures',
    'thinc',
    'thinc.api',
    'numpy.random.common',
    'numpy.random.bounded_integers',
    'numpy.random.entropy',
    'cymem',
    'cymem.cymem',
    'preshed',
    'preshed.maps',
    'blis',
    'blis.py',
    'catalogue',
    'srsly',
    'srsly.msgpack',
    'murmurhash',
    'thinc.extra.search',
])