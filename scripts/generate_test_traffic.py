#!/usr/bin/env python3
"""
Generate test traffic for Axon honeypot dashboard
Sends a mix of legitimate and attack-like requests
"""

import requests
import time
import random
from datetime import datetime

# Your deployed worker URL
WORKER_URL = "https://axon.sarahsl.workers.dev"

# Legitimate request patterns
LEGIT_PATHS = [
    "/",
    "/api/users",
    "/api/posts",
    "/about",
    "/contact",
    "/products/123",
    "/blog/hello-world",
    "/dashboard",
]

LEGIT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# Attack patterns
ATTACK_PATHS = [
    "/wp-admin/admin.php",
    "/wp-login.php",
    "/../../../etc/passwd",
    "/admin/login?user=admin' OR '1'='1",
    "/.env",
    "/.git/config",
    "/phpMyAdmin/",
    "/admin' UNION SELECT * FROM users--",
    "/shell.php",
    "/%2e%2e/%2e%2e/etc/passwd",
    "/cgi-bin/admin",
]

ATTACK_USER_AGENTS = [
    "curl/7.68.0",
    "python-requests/2.28.0",
    "sqlmap/1.0",
    "Googlebot/2.1",
    "Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1)",
]


def send_request(path, user_agent, request_type="legit"):
    """Send a single request to the worker"""
    try:
        response = requests.get(
            f"{WORKER_URL}{path}",
            headers={"User-Agent": user_agent},
            timeout=5,
        )
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {request_type.upper():6} | {response.status_code} | {path[:50]}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


def main():
    """Generate continuous test traffic"""
    print(f"Generating test traffic for: {WORKER_URL}")
    print("Press Ctrl+C to stop\n")

    request_count = 0

    try:
        while True:
            # Randomly choose legit or attack (70% legit, 30% attack)
            if random.random() < 0.7:
                # Legitimate request
                path = random.choice(LEGIT_PATHS)
                user_agent = random.choice(LEGIT_USER_AGENTS)
                request_type = "legit"
            else:
                # Attack request
                path = random.choice(ATTACK_PATHS)
                user_agent = random.choice(ATTACK_USER_AGENTS)
                request_type = "attack"

            if send_request(path, user_agent, request_type):
                request_count += 1

            # Random delay between 1-3 seconds
            time.sleep(random.uniform(1, 3))

    except KeyboardInterrupt:
        print(f"\n\nGenerated {request_count} test requests")
        print("Check your dashboard to see the traffic!")


if __name__ == "__main__":
    main()
