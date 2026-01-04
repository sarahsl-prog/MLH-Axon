#!/usr/bin/env python3
"""
Convert traffic_log.jsonl to CSV format for ML training

This script processes honeypot traffic logs and extracts features for training
a machine learning model to classify traffic as attack vs legitimate.

Usage:
    python3 scripts/convert_traffic_to_csv.py
    python3 scripts/convert_traffic_to_csv.py --input traffic_data/traffic_log.jsonl --output training_data.csv
"""

import json
import csv
import argparse
import re
import math
from pathlib import Path
from collections import Counter
from urllib.parse import unquote


def calculate_entropy(text):
    """Calculate Shannon entropy of a string"""
    if not text:
        return 0.0

    counter = Counter(text)
    length = len(text)
    entropy = -sum((count/length) * math.log2(count/length) for count in counter.values())
    return entropy


def detect_sql_patterns(text):
    """Detect SQL injection patterns"""
    if not text:
        return False

    text_lower = text.lower()
    sql_keywords = ['select', 'union', 'insert', 'update', 'delete', 'drop', 'exec', 'script']
    sql_chars = ["'", '"', '--', ';', '/*', '*/', 'xp_']

    keyword_count = sum(1 for kw in sql_keywords if kw in text_lower)
    char_count = sum(1 for char in sql_chars if char in text)

    return keyword_count >= 2 or char_count >= 2


def detect_path_traversal(path):
    """Detect path traversal attempts"""
    if not path:
        return False

    patterns = ['../', '..\\', '%2e%2e', '....', '/etc/', '/proc/', '/bin/', '/var/']
    return any(p in path.lower() for p in patterns)


def detect_command_injection(text):
    """Detect command injection patterns"""
    if not text:
        return False

    patterns = [
        r'[;&|`].*(?:wget|curl|nc|bash|sh|python|perl|ruby)',
        r'(?:exec|system|shell_exec|passthru|popen)',
        r'base64_decode',
        r'\$\(.*\)',
        r'`.*`'
    ]

    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def detect_xss(text):
    """Detect XSS patterns"""
    if not text:
        return False

    patterns = [
        r'<script',
        r'javascript:',
        r'onerror=',
        r'onload=',
        r'eval\(',
        r'alert\(',
        r'<iframe'
    ]

    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


def detect_php_exploit(path, body, query):
    """Detect PHP-specific exploits"""
    all_text = f"{path} {body} {query}".lower()

    patterns = [
        'phpunit',
        'eval-stdin.php',
        'shell.php',
        '<?php',
        'base64_decode',
        'shell_exec',
        'system(',
        'passthru(',
        'allow_url_include'
    ]

    return any(p in all_text for p in patterns)


def analyze_user_agent(ua):
    """Analyze user agent characteristics"""
    if not ua:
        return {
            'is_bot': True,
            'is_scanner': True,
            'is_suspicious': True,
            'ua_length': 0
        }

    ua_lower = ua.lower()

    # Known scanners/bots
    scanners = ['nmap', 'sqlmap', 'nikto', 'masscan', 'zgrab', 'shodan', 'censys', 'scanner']
    is_scanner = any(s in ua_lower for s in scanners)

    # Suspicious UAs
    suspicious = ['curl', 'wget', 'python', 'perl', 'ruby', 'java', 'go-http']
    is_suspicious_tool = any(s in ua_lower for s in suspicious)

    # Very short or very long UAs are suspicious
    is_suspicious_length = len(ua) < 20 or len(ua) > 500

    # Missing standard browser indicators
    browser_indicators = ['mozilla', 'chrome', 'safari', 'firefox', 'edge']
    has_browser_indicator = any(b in ua_lower for b in browser_indicators)

    return {
        'is_bot': is_scanner or not has_browser_indicator,
        'is_scanner': is_scanner,
        'is_suspicious': is_suspicious_tool or is_suspicious_length or not has_browser_indicator,
        'ua_length': len(ua)
    }


def count_special_chars(text):
    """Count special characters that might indicate an attack"""
    if not text:
        return 0

    special_chars = set('<>&;"\'()[]{}$`|;\\')
    return sum(1 for c in text if c in special_chars)


def extract_features(record):
    """Extract ML features from a traffic record"""

    # Get basic fields
    path = record.get('path', '')
    method = record.get('method', 'GET')
    user_agent = record.get('user_agent', '')
    body = record.get('body', '')
    query_string = record.get('query_string', '')
    ip = record.get('ip', '')
    content_length = record.get('content_length', '0')

    # Decode URL-encoded strings
    decoded_query = unquote(query_string) if query_string else ''
    decoded_path = unquote(path)

    # Combine all text for analysis
    all_text = f"{decoded_path} {decoded_query} {body}"

    # Extract features
    features = {
        # Basic features
        'method': method,
        'path_length': len(path),
        'path_depth': path.count('/'),
        'query_length': len(query_string),
        'body_length': len(body),
        'content_length': int(content_length) if content_length.isdigit() else 0,

        # Entropy features
        'path_entropy': calculate_entropy(decoded_path),
        'query_entropy': calculate_entropy(decoded_query),
        'url_entropy': calculate_entropy(decoded_path + decoded_query),

        # User agent features
        'ua_length': len(user_agent),
        'ua_is_bot': analyze_user_agent(user_agent)['is_bot'],
        'ua_is_scanner': analyze_user_agent(user_agent)['is_scanner'],
        'ua_is_suspicious': analyze_user_agent(user_agent)['is_suspicious'],

        # Special character counts
        'special_chars_path': count_special_chars(decoded_path),
        'special_chars_query': count_special_chars(decoded_query),
        'special_chars_body': count_special_chars(body),

        # Attack pattern detection (binary features)
        'has_sql_injection': int(detect_sql_patterns(all_text)),
        'has_path_traversal': int(detect_path_traversal(decoded_path)),
        'has_command_injection': int(detect_command_injection(all_text)),
        'has_xss': int(detect_xss(all_text)),
        'has_php_exploit': int(detect_php_exploit(path, body, decoded_query)),

        # Method analysis
        'is_post': int(method == 'POST'),
        'is_get': int(method == 'GET'),
        'is_uncommon_method': int(method not in ['GET', 'POST', 'HEAD', 'OPTIONS']),

        # Path analysis
        'has_extension': int('.' in path.split('/')[-1] if '/' in path else False),
        'suspicious_extension': int(any(ext in path.lower() for ext in ['.php', '.asp', '.jsp', '.cgi'])),
        'common_exploit_path': int(any(p in path.lower() for p in ['admin', 'phpunit', 'eval', 'shell', 'config', '.git', '.env'])),

        # Label (from prediction field)
        'label': 'attack' if record.get('prediction') == 'suspicious' else 'legit'
    }

    return features


def convert_jsonl_to_csv(input_file, output_file):
    """Convert JSONL traffic log to CSV for ML training"""

    print(f"Reading traffic data from: {input_file}")

    records = []
    with open(input_file, 'r') as f:
        for line_num, line in enumerate(f, 1):
            try:
                record = json.loads(line.strip())
                features = extract_features(record)
                records.append(features)
            except json.JSONDecodeError as e:
                print(f"Warning: Skipping invalid JSON on line {line_num}: {e}")
            except Exception as e:
                print(f"Warning: Error processing line {line_num}: {e}")

    if not records:
        print("Error: No valid records found!")
        return

    # Get all feature names (excluding label)
    feature_names = [k for k in records[0].keys() if k != 'label']
    fieldnames = feature_names + ['label']

    # Write to CSV
    print(f"Writing {len(records)} records to: {output_file}")

    with open(output_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    # Print statistics
    print("\n" + "="*60)
    print("Conversion Complete!")
    print("="*60)
    print(f"Total records: {len(records)}")

    label_counts = Counter(r['label'] for r in records)
    for label, count in label_counts.items():
        percentage = (count / len(records)) * 100
        print(f"{label.capitalize()}: {count} ({percentage:.1f}%)")

    print(f"\nFeatures extracted: {len(feature_names)}")
    print(f"Output file: {output_file}")
    print("\nFeature list:")
    for i, feat in enumerate(feature_names, 1):
        print(f"  {i:2d}. {feat}")


def main():
    parser = argparse.ArgumentParser(
        description='Convert honeypot traffic logs to CSV for ML training'
    )
    parser.add_argument(
        '--input', '-i',
        default='traffic_data/traffic_log.jsonl',
        help='Input JSONL file (default: traffic_data/traffic_log.jsonl)'
    )
    parser.add_argument(
        '--output', '-o',
        default='training_data.csv',
        help='Output CSV file (default: training_data.csv)'
    )

    args = parser.parse_args()

    # Check input file exists
    if not Path(args.input).exists():
        print(f"Error: Input file not found: {args.input}")
        return 1

    try:
        convert_jsonl_to_csv(args.input, args.output)
        return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
