import pandas as pd
import numpy as np
from urllib.parse import urlparse
import re


def calculate_entropy(s):
    """Calculate Shannon entropy"""
    if not s:
        return 0
    prob = [s.count(c) / len(s) for c in set(s)]
    return -sum(p * np.log2(p) for p in prob)


def extract_features(df):
    """Extract ML features from raw data"""

    features = pd.DataFrame()

    # Path-based features
    features['path_length'] = df['path'].str.len()
    features['path_entropy'] = df['path'].apply(calculate_entropy)
    features['has_query_params'] = df['path'].str.contains('\?').astype(int)
    features['num_slashes'] = df['path'].str.count('/')
    features['num_dots'] = df['path'].str.count('\.')

    # Suspicious path patterns
    attack_patterns = ['admin', 'wp-', 'php', '.env', 'sql', 'etc/passwd']
    for pattern in attack_patterns:
        features[f'has_{pattern}'] = df['path'].str.contains(
            pattern, case=False, na=False
        ).astype(int)

    # Method
    features['method_get'] = (df['method'] == 'GET').astype(int)
    features['method_post'] = (df['method'] == 'POST').astype(int)

    # User-Agent features
    features['ua_length'] = df['user_agent'].str.len()
    features['ua_is_bot'] = df['user_agent'].str.contains(
        'bot|crawler|spider|curl|wget|python',
        case=False, na=False
    ).astype(int)
    features['ua_is_browser'] = df['user_agent'].str.contains(
        'mozilla|chrome|firefox|safari',
        case=False, na=False
    ).astype(int)

    # Cloudflare bot score (if available)
    if 'bot_score' in df.columns:
        features['bot_score'] = df['bot_score'].fillna(50)

    # Country risk (simplified)
    high_risk_countries = ['CN', 'RU', 'KP', 'IR']
    features['high_risk_country'] = df['country'].isin(high_risk_countries).astype(int)

    return features


# Load and process data
df = pd.read_csv('training_data.csv')
X = extract_features(df)
y = (df['label'] == 'attack').astype(int)  # Binary: 1 = attack, 0 = legit

# Save processed features
X.to_csv('features.csv', index=False)
y.to_csv('labels.csv', index=False)

print(f"Features shape: {X.shape}")
print(f"Attack rate: {y.mean():.2%}")
print(f"\nFeatures:\n{X.head()}")
