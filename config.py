"""
Configuration file for the faithfulness benchmark pipeline.
Easy to modify models and settings here.
"""

# =============================================================================
# MODEL CONFIGURATION - Easy to swap and add models
# =============================================================================

# Models to use for summarization (via OpenRouter)
# Add or remove models as needed - just update this list
SUMMARIZATION_MODELS = [
    "google/gemini-2.5-flash-lite",
    "x-ai/grok-4.1-fast",
    "meta-llama/llama-4-maverick",
]

# Judge model for LLM-as-Judge evaluation (via OpenRouter)
# Primary judge model to use
JUDGE_MODEL = "google/gemini-3-flash-preview"
JUDGE_MODELS = [
    "anthropic/claude-opus-4.5",
    "google/gemini-3-flash-preview",
    "minimax/minimax-m2.1",
]

# =============================================================================
# LOCAL MODEL CONFIGURATION
# =============================================================================

# NLI model for contradiction detection (runs locally)
# Using MoritzLaurer's DeBERTa-v3 NLI model (publicly available)
NLI_MODEL = "MoritzLaurer/DeBERTa-v3-base-mnli-fever-anli"

# Sentence embedding model for coverage analysis (runs locally)
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# =============================================================================
# EVALUATION THRESHOLDS
# =============================================================================

# Cosine similarity threshold for embedding coverage
# Sentences below this threshold are flagged as omissions
COVERAGE_THRESHOLD = 0.5

# =============================================================================
# COMPOSITE SCORE WEIGHTS
# =============================================================================
# These should sum to 1.0

WEIGHT_NLI = 0.35       # NLI contradiction score
WEIGHT_JUDGE = 0.40     # LLM-as-Judge score
WEIGHT_COVERAGE = 0.25  # Embedding coverage score

# =============================================================================
# PATHS
# =============================================================================

OYEZ_DATA_DIR = "oyez-data"
OUTPUT_DIR = "outputs"

# =============================================================================
# API SETTINGS
# =============================================================================

# Delay between API requests in seconds (0 for paid tier, 10 for free tier)
API_DELAY = 0.0

