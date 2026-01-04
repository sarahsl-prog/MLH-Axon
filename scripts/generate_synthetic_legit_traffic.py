#!/usr/bin/env python3
"""
Generate synthetic legitimate traffic data for training

This script creates realistic legitimate web traffic patterns to balance
the attack-heavy dataset collected from the honeypot.

Usage:
    python3 scripts/generate_synthetic_legit_traffic.py
    python3 scripts/generate_synthetic_legit_traffic.py --count 100 --output legit_traffic.jsonl
"""

import json
import random
import argparse
from datetime import datetime, timedelta


# Legitimate paths for a typical web application
LEGIT_PATHS = [
    "/",
    "/index.html",
    "/about",
    "/about.html",
    "/contact",
    "/contact.html",
    "/products",
    "/services",
    "/blog",
    "/blog/post-1",
    "/blog/post-2",
    "/blog/how-to-secure-your-website",
    "/api/users",
    "/api/posts",
    "/api/products",
    "/api/status",
    "/api/health",
    "/static/css/style.css",
    "/static/js/app.js",
    "/static/images/logo.png",
    "/static/images/banner.jpg",
    "/assets/favicon.ico",
    "/robots.txt",
    "/sitemap.xml",
    "/privacy-policy",
    "/terms-of-service",
    "/faq",
    "/help",
    "/docs",
    "/docs/getting-started",
    "/docs/api-reference",
    "/login",
    "/logout",
    "/register",
    "/profile",
    "/settings",
    "/search",
    "/cart",
    "/checkout",
]

# Legitimate user agents (real browser user agents)
LEGIT_USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    # Chrome on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    # Firefox on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    # Safari on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    # Safari on iPhone
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    # Chrome on Android
    "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.43 Mobile Safari/537.36",
]

# Legitimate referrers
LEGIT_REFERRERS = [
    "",  # Direct traffic
    "https://www.google.com/",
    "https://www.bing.com/",
    "https://duckduckgo.com/",
    "https://www.linkedin.com/",
    "https://twitter.com/",
    "https://www.facebook.com/",
    "https://news.ycombinator.com/",
    "https://www.reddit.com/",
]

# Common legitimate query parameters
LEGIT_QUERY_PARAMS = [
    "",
    "page=1",
    "page=2",
    "sort=date",
    "sort=popularity",
    "category=technology",
    "category=news",
    "q=search+term",
    "utm_source=newsletter",
    "utm_medium=email",
    "utm_campaign=product_launch",
    "ref=homepage",
]

# Legitimate IP addresses (RFC 1918 private ranges and public examples)
LEGIT_IPS = [
    "192.168.1.100",
    "192.168.1.101",
    "192.168.1.102",
    "10.0.0.50",
    "10.0.0.51",
    "172.16.0.25",
    "172.16.0.26",
    # Public IPs (examples - these would be real user IPs)
    "203.0.113.45",
    "198.51.100.23",
    "203.0.113.78",
]

# Countries
LEGIT_COUNTRIES = [
    "US",
    "GB",
    "CA",
    "AU",
    "DE",
    "FR",
    "JP",
    "IN",
    "BR",
]

# Hosts
LEGIT_HOSTS = [
    "example.com",
    "www.example.com",
    "api.example.com",
    "blog.example.com",
]


def generate_legit_request():
    """Generate a single legitimate traffic record"""

    # Pick random values
    path = random.choice(LEGIT_PATHS)
    method = random.choices(
        ["GET", "POST", "HEAD", "OPTIONS"],
        weights=[85, 10, 3, 2]  # GET is most common
    )[0]
    user_agent = random.choice(LEGIT_USER_AGENTS)
    referer = random.choice(LEGIT_REFERRERS)
    ip = random.choice(LEGIT_IPS)
    country = random.choice(LEGIT_COUNTRIES)
    host = random.choice(LEGIT_HOSTS)
    query_string = random.choice(LEGIT_QUERY_PARAMS)

    # Headers for legitimate request
    headers = {
        "Host": host,
        "User-Agent": user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    # Add referer if present
    if referer:
        headers["Referer"] = referer

    # Add X-Forwarded-For and X-Real-IP
    headers["X-Forwarded-For"] = ip
    headers["X-Real-IP"] = ip

    # POST requests have content
    body = ""
    content_length = ""
    if method == "POST":
        # Simulate form data or JSON
        if random.random() > 0.5:
            # Form data
            body = "username=john&email=john@example.com&message=Hello"
            content_length = str(len(body))
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            # JSON data
            body = '{"name": "John Doe", "email": "john@example.com"}'
            content_length = str(len(body))
            headers["Content-Type"] = "application/json"

    # Generate timestamp (spread over last 7 days)
    days_ago = random.randint(0, 7)
    hours_ago = random.randint(0, 23)
    minutes_ago = random.randint(0, 59)
    timestamp = datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago, minutes=minutes_ago)

    record = {
        "timestamp": timestamp.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "path": path,
        "method": method,
        "ip": ip,
        "user_agent": user_agent,
        "referer": referer,
        "host": host,
        "content_length": content_length,
        "query_string": query_string,
        "prediction": "legit",  # Label as legitimate
        "headers": headers,
        "body": body,
    }

    return record


def generate_synthetic_traffic(count, output_file):
    """Generate multiple legitimate traffic records"""

    print(f"Generating {count} synthetic legitimate traffic records...")

    records = []
    for i in range(count):
        record = generate_legit_request()
        records.append(record)

        if (i + 1) % 25 == 0:
            print(f"  Generated {i + 1}/{count} records...")

    # Write to JSONL file
    print(f"\nWriting records to: {output_file}")
    with open(output_file, 'w') as f:
        for record in records:
            f.write(json.dumps(record) + '\n')

    # Statistics
    print("\n" + "="*60)
    print("SYNTHETIC DATA GENERATION COMPLETE")
    print("="*60)
    print(f"Total records: {count}")
    print(f"Output file: {output_file}")

    # Method distribution
    method_counts = {}
    for record in records:
        method = record['method']
        method_counts[method] = method_counts.get(method, 0) + 1

    print("\nHTTP Method Distribution:")
    for method, count in sorted(method_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(records)) * 100
        print(f"  {method}: {count} ({percentage:.1f}%)")

    # Path types
    api_paths = sum(1 for r in records if '/api/' in r['path'])
    static_paths = sum(1 for r in records if '/static/' in r['path'] or '/assets/' in r['path'])

    print("\nPath Distribution:")
    print(f"  API endpoints: {api_paths} ({api_paths/count*100:.1f}%)")
    print(f"  Static resources: {static_paths} ({static_paths/count*100:.1f}%)")
    print(f"  Regular pages: {count - api_paths - static_paths} ({(count - api_paths - static_paths)/count*100:.1f}%)")

    print("\n" + "="*60)


def main():
    parser = argparse.ArgumentParser(
        description='Generate synthetic legitimate traffic for ML training'
    )
    parser.add_argument(
        '--count', '-c',
        type=int,
        default=75,
        help='Number of legitimate requests to generate (default: 75)'
    )
    parser.add_argument(
        '--output', '-o',
        default='legit_traffic.jsonl',
        help='Output JSONL file (default: legit_traffic.jsonl)'
    )

    args = parser.parse_args()

    try:
        generate_synthetic_traffic(args.count, args.output)
        return 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
