# AXON Training Data Documentation

## Overview

This directory contains training data for the AXON honeypot traffic classification system.

## Files

### Raw Traffic Logs (JSONL format)
- `traffic_data/traffic_log.jsonl` - 75 real attack samples from honeypot
- `legit_traffic.jsonl` - 75 synthetic legitimate traffic samples
- `combined_traffic.jsonl` - 150 combined samples (attack + legit)

### Training Data (CSV format)
- `training_data.csv` - Attack-only dataset (75 samples)
- `balanced_training_data.csv` - **Balanced dataset (150 samples)** ⭐ USE THIS

## Dataset Statistics

### Balanced Training Data (`balanced_training_data.csv`)

**Total samples**: 150
- **Attack samples**: 75 (50.0%)
- **Legitimate samples**: 75 (50.0%)
- **Features**: 27
- **Label column**: `label` (values: "attack" or "legit")

### Attack Pattern Distribution
From the 75 real honeypot attack samples:
- **SQL Injection**: 42 samples (56.0%)
- **PHP Exploits**: 39 samples (52.0%)
  - CVE-2024-4577 exploits
  - PHPUnit RCE attempts
- **Command Injection**: 6 samples (8.0%)
  - Base64-encoded payloads
  - Reverse shell attempts

### Feature Comparison

| Metric | Attack Avg | Legit Avg | Notes |
|--------|------------|-----------|-------|
| URL Entropy | 2.67 | 3.66 | Attacks often have simpler patterns |
| Special Chars (Body) | 6.3 | 0.8 | Attacks contain more special chars |
| Suspicious UAs | 66.7% | 0.0% | Clear discriminator |

## Feature Descriptions

### Structural Features (9)
1. `method` - HTTP method (GET, POST, etc.)
2. `path_length` - Length of URL path
3. `path_depth` - Number of slashes in path
4. `query_length` - Length of query string
5. `body_length` - Length of request body
6. `content_length` - Content-Length header value
7. `path_entropy` - Shannon entropy of path
8. `query_entropy` - Shannon entropy of query
9. `url_entropy` - Shannon entropy of full URL

### User Agent Features (4)
10. `ua_length` - User agent string length
11. `ua_is_bot` - Detected as bot/crawler
12. `ua_is_scanner` - Detected as security scanner
13. `ua_is_suspicious` - Suspicious UA characteristics

### Character Analysis (3)
14. `special_chars_path` - Count of special chars in path
15. `special_chars_query` - Count of special chars in query
16. `special_chars_body` - Count of special chars in body

### Attack Detection Features (5)
17. `has_sql_injection` - SQL injection patterns detected
18. `has_path_traversal` - Path traversal patterns detected
19. `has_command_injection` - Command injection patterns detected
20. `has_xss` - XSS patterns detected
21. `has_php_exploit` - PHP-specific exploit patterns detected

### Method Analysis (3)
22. `is_post` - Is POST request
23. `is_get` - Is GET request
24. `is_uncommon_method` - Uncommon HTTP method

### Path Analysis (3)
25. `has_extension` - Path has file extension
26. `suspicious_extension` - Has suspicious extension (.php, .asp, etc.)
27. `common_exploit_path` - Contains common exploit path patterns

### Label (1)
28. `label` - Ground truth label ("attack" or "legit")

## Scripts

### Data Generation & Conversion
- `scripts/generate_synthetic_legit_traffic.py` - Generate synthetic legitimate traffic
- `scripts/convert_traffic_to_csv.py` - Convert JSONL to CSV with feature extraction

### Usage

Generate synthetic legitimate traffic:
```bash
python3 scripts/generate_synthetic_legit_traffic.py --count 75 --output legit_traffic.jsonl
```

Convert to CSV:
```bash
# Attack data only
python3 scripts/convert_traffic_to_csv.py \
  --input traffic_data/traffic_log.jsonl \
  --output training_data.csv

# Balanced dataset
cat traffic_data/traffic_log.jsonl legit_traffic.jsonl > combined_traffic.jsonl
python3 scripts/convert_traffic_to_csv.py \
  --input combined_traffic.jsonl \
  --output balanced_training_data.csv
```

## Data Quality Notes

### Real Attack Data
- Collected from actual honeypot deployment
- Contains real-world attack patterns including:
  - CVE exploits (CVE-2024-4577)
  - PHPUnit RCE attempts
  - SQL injection probes
  - Command injection attempts
  - Reverse shell payloads

### Synthetic Legitimate Data
- Generated with realistic patterns:
  - Common browser User-Agents (Chrome, Firefox, Safari, Edge)
  - Typical web application paths
  - Realistic referrers (Google, Bing, social media)
  - Normal HTTP method distribution (85% GET, 10% POST)
  - Legitimate query parameters

## Next Steps for ML Training

### 1. Data Exploration
```python
import pandas as pd
df = pd.read_csv('balanced_training_data.csv')
print(df.describe())
print(df['label'].value_counts())
```

### 2. Train/Test Split
```python
from sklearn.model_selection import train_test_split
X = df.drop('label', axis=1)
y = df['label']
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
```

### 3. Model Training
Recommended models:
- **Random Forest** - Good baseline, handles mixed feature types
- **XGBoost** - High performance for tabular data
- **Logistic Regression** - Simple, interpretable baseline

### 4. Deployment
Once trained, deploy to Cloudflare Workers AI or convert to ONNX format for edge deployment.

## Data Collection Tips

To improve the dataset:
1. **Add more attack diversity** - Different attack types, tools, techniques
2. **Collect real legitimate traffic** - From your production applications
3. **Add temporal features** - Time of day, day of week patterns
4. **Expand synthetic data** - More path variations, user agent diversity
5. **Label verification** - Manual review of edge cases

## License

This training data is for educational and research purposes.
