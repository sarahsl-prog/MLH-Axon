MODEL TRAINING GUIDE

This guide covers training your ML model on collected honeypot data and deploying it to Workers AI.

OVERVIEW

The training pipeline:
1. COLLECT data from your honeypot (Friday night -> Saturday morning)
2. EXPORT data from D1
3. FEATURE ENGINEERING and preprocessing
4. TRAIN model (Random Forest -> XGBoost -> Neural Net)
5. EXPORT to ONNX format
6. DEPLOY to Workers AI
7. UPDATE classification logic

PREREQUISITES

pip install pandas scikit-learn xgboost onnx onnxruntime


STEP 1: EXPORT TRAINING DATA

Export data from D1:

# Export to CSV
wrangler d1 execute axon-db --command="
SELECT 
    timestamp,
    path,
    method,
    country,
    user_agent,
    prediction as label,
    confidence,
    bot_score
FROM traffic
WHERE timestamp > $(date -d '24 hours ago' +%s)000
" --json > training_data.json

# Convert to CSV using Python
python scripts/json_to_csv.py training_data.json training_data.csv


scripts/json_to_csv.py:

import json
import pandas as pd
import sys

with open(sys.argv[1]) as f:
    data = json.load(f)

df = pd.DataFrame(data[0]['results'])
df.to_csv(sys.argv[2], index=False)
print(f"Exported {len(df)} rows to {sys.argv[2]}")


STEP 2: FEATURE ENGINEERING

scripts/prepare_features.py:

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


Run feature engineering:

python scripts/prepare_features.py


STEP 3: TRAIN MODEL

scripts/train_model.py:

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
import xgboost as xgb
import pickle


# Load features and labels
X = pd.read_csv('features.csv')
y = pd.read_csv('labels.csv').values.ravel()

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"Training set: {X_train.shape[0]} samples")
print(f"Test set: {X_test.shape[0]} samples")

# ====================
# Model 1: Random Forest (Baseline)
# ====================
print("\n=== Training Random Forest ===")
rf_model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    random_state=42,
    n_jobs=-1
)
rf_model.fit(X_train, y_train)

# Evaluate
rf_pred = rf_model.predict(X_test)
print("\nRandom Forest Results:")
print(classification_report(y_test, rf_pred, 
                          target_names=['Legit', 'Attack']))

# Feature importance
feature_importance = pd.DataFrame({
    'feature': X.columns,
    'importance': rf_model.feature_importances_
}).sort_values('importance', ascending=False)
print("\nTop 10 Features:")
print(feature_importance.head(10))

# ====================
# Model 2: XGBoost (Better Performance)
# ====================
print("\n=== Training XGBoost ===")
xgb_model = xgb.XGBClassifier(
    n_estimators=100,
    max_depth=6,
    learning_rate=0.1,
    random_state=42,
    use_label_encoder=False,
    eval_metric='logloss'
)
xgb_model.fit(X_train, y_train)

# Evaluate
xgb_pred = xgb_model.predict(X_test)
print("\nXGBoost Results:")
print(classification_report(y_test, xgb_pred,
                          target_names=['Legit', 'Attack']))

# Save best model
print("\n=== Saving Model ===")
with open('axon_model.pkl', 'wb') as f:
    pickle.dump(xgb_model, f)
print("Model saved to axon_model.pkl")

# Confusion Matrix
print("\nConfusion Matrix:")
print(confusion_matrix(y_test, xgb_pred))


Train the model:

python scripts/train_model.py


STEP 4: EXPORT TO ONNX

scripts/export_onnx.py:

import pickle
import onnx
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
import pandas as pd


# Load trained model
with open('axon_model.pkl', 'rb') as f:
    model = pickle.load(f)

# Load feature names
X = pd.read_csv('features.csv')
feature_names = X.columns.tolist()
num_features = len(feature_names)

print(f"Exporting model with {num_features} features")

# Define input type
initial_type = [('float_input', FloatTensorType([None, num_features]))]

# Convert to ONNX
onnx_model = convert_sklearn(
    model,
    initial_types=initial_type,
    target_opset=12
)

# Save ONNX model
with open('axon_model.onnx', 'wb') as f:
    f.write(onnx_model.SerializeToString())

print("Model exported to axon_model.onnx")

# Verify ONNX model
onnx_model_check = onnx.load('axon_model.onnx')
onnx.checker.check_model(onnx_model_check)
print("ONNX model verified successfully!")

# Save feature names for later use
with open('feature_names.txt', 'w') as f:
    f.write('\n'.join(feature_names))
print(f"Feature names saved ({num_features} features)")


Export to ONNX:

pip install skl2onnx onnx
python scripts/export_onnx.py


STEP 5: DEPLOY TO WORKERS AI

Upload Model

# Upload ONNX model to Workers AI
wrangler ai models upload axon_model.onnx \
  --name axon-classifier \
  --type onnx

# Note the model ID (e.g., @cf/your-account/axon-classifier)


Update Classification Logic

src/honeypot.py:

async def classify_with_workers_ai(features, env):
    """Classify using deployed ML model"""
    
    # Prepare features in correct order
    feature_vector = [
        features['path_length'],
        features['path_entropy'],
        features['has_query_params'],
        features['num_slashes'],
        features['num_dots'],
        features['has_admin'],
        features['has_wp-'],
        # ... all other features in same order as training
    ]
    
    # Run inference
    result = await env.AI.run('@cf/your-account/axon-classifier', {
        'input': feature_vector
    })
    
    return {
        'label': 'attack' if result['prediction'] > 0.5 else 'legit',
        'confidence': abs(result['prediction'] - 0.5) * 2,  # Scale to 0-1
        'model_score': result['prediction']
    }


async def handle_honeypot_request(request, env):
    # ... extract features ...
    
    # Classify with ML model
    prediction = await classify_with_workers_ai(features, env)
    
    # ... rest of logging and broadcasting ...


Deploy updated worker:

uv run pywrangler deploy


STEP 6: EVALUATE IN PRODUCTION

A/B Testing

Run both heuristic and ML model, compare results:

# Get both predictions
heuristic_pred = classify_heuristic(features)
ml_pred = await classify_with_workers_ai(features, env)

# Log both for comparison
await log_predictions(features, {
    'heuristic': heuristic_pred,
    'ml': ml_pred
})

# Use ML prediction for actual classification
return ml_pred


Monitor Performance

# Check accuracy over time
wrangler d1 execute axon-db --command="
SELECT 
    DATE(created_at) as date,
    prediction,
    AVG(confidence) as avg_confidence,
    COUNT(*) as count
FROM traffic
WHERE created_at > datetime('now', '-7 days')
GROUP BY date, prediction
ORDER BY date DESC
"


MODEL ITERATION

Collect More Data

Let it run for a few days, then:

# Export larger dataset
wrangler d1 execute axon-db --command="
SELECT * FROM traffic 
WHERE timestamp > $(date -d '7 days ago' +%s)000
" --json > training_data_v2.json


Retrain

python scripts/prepare_features.py
python scripts/train_model.py
python scripts/export_onnx.py
wrangler ai models upload axon_model.onnx --name axon-classifier-v2


Deploy New Version

Update model name in code and deploy:

uv run pywrangler deploy


ADVANCED: NEURAL NETWORK

For even better performance, try a simple neural network:

scripts/train_neural_net.py:

import tensorflow as tf
from tensorflow import keras
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split


# Load data
X = pd.read_csv('features.csv').values
y = pd.read_csv('labels.csv').values

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# Build model
model = keras.Sequential([
    keras.layers.Dense(64, activation='relu', input_shape=(X.shape[1],)),
    keras.layers.Dropout(0.3),
    keras.layers.Dense(32, activation='relu'),
    keras.layers.Dropout(0.3),
    keras.layers.Dense(16, activation='relu'),
    keras.layers.Dense(1, activation='sigmoid')
])

model.compile(
    optimizer='adam',
    loss='binary_crossentropy',
    metrics=['accuracy', keras.metrics.Precision(), keras.metrics.Recall()]
)

# Train
history = model.fit(
    X_train, y_train,
    validation_split=0.2,
    epochs=50,
    batch_size=32,
    verbose=1
)

# Evaluate
loss, accuracy, precision, recall = model.evaluate(X_test, y_test)
print(f"\nTest Accuracy: {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall: {recall:.4f}")

# Save
model.save('axon_nn_model.h5')
print("Model saved to axon_nn_model.h5")


Convert to ONNX:

pip install tf2onnx
python -m tf2onnx.convert \
  --saved-model axon_nn_model.h5 \
  --output axon_nn_model.onnx


TIPS FOR GOOD MODELS

1. Balanced Dataset: Ensure roughly equal attacks and legit traffic
2. Feature Engineering: More features != better (focus on meaningful ones)
3. Cross-Validation: Use k-fold CV to validate model
4. Regularization: Prevent overfitting with dropout/L2
5. Hyperparameter Tuning: Use grid search for best params


NEXT STEPS

- Deployment Guide (deployment.txt) - Deploy to production
- API Reference (api-reference.txt) - Understand the API
