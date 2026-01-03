"""Unit tests for features.py module"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest
from features import (
    get_request_entropy,
    parse_user_agent,
    detect_sql_injection,
    detect_path_traversal,
    detect_sensitive_files,
    detect_common_exploits,
    analyze_path_characteristics,
)


class TestRequestEntropy:
    """Test entropy calculation"""

    def test_empty_string(self):
        assert get_request_entropy("") == 0

    def test_low_entropy_repeated_chars(self):
        # Repeated characters should have low entropy
        assert get_request_entropy("aaaaaaa") < 1.0

    def test_high_entropy_random(self):
        # Random mix should have higher entropy
        assert get_request_entropy("/a1B2c3D4e5F6") > 2.0

    def test_normal_url(self):
        # Normal URL should have moderate entropy
        entropy = get_request_entropy("/api/users/123")
        assert 1.0 < entropy < 4.0


class TestUserAgentParsing:
    """Test user agent parsing"""

    def test_empty_user_agent(self):
        result = parse_user_agent("")
        assert result["is_bot"] == True
        assert result["client"] == "unknown"

    def test_chrome_browser(self):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        result = parse_user_agent(ua)
        assert result["is_bot"] == False
        assert result["client"] == "chrome"

    def test_firefox_browser(self):
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0"
        result = parse_user_agent(ua)
        assert result["is_bot"] == False
        assert result["client"] == "firefox"

    def test_googlebot(self):
        ua = "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        result = parse_user_agent(ua)
        assert result["is_bot"] == True

    def test_curl(self):
        ua = "curl/7.68.0"
        result = parse_user_agent(ua)
        assert result["is_bot"] == True

    def test_python_requests(self):
        ua = "python-requests/2.28.0"
        result = parse_user_agent(ua)
        assert result["is_bot"] == True


class TestSQLInjectionDetection:
    """Test SQL injection detection"""

    def test_clean_path(self):
        result = detect_sql_injection("/api/users")
        assert result["has_sql_pattern"] == False
        assert result["sql_pattern_count"] == 0
        assert result["risk_level"] == "low"

    def test_union_select(self):
        result = detect_sql_injection("/api/users?id=1 UNION SELECT * FROM passwords")
        assert result["has_sql_pattern"] == True
        assert result["sql_pattern_count"] >= 2
        assert result["risk_level"] in ["medium", "high"]

    def test_or_one_equals_one(self):
        result = detect_sql_injection("/login?user=admin&pass=' OR 1=1--")
        assert result["has_sql_pattern"] == True
        assert result["risk_level"] in ["medium", "high"]

    def test_multiple_patterns(self):
        result = detect_sql_injection("/api?q='; DROP TABLE users; --")
        assert result["has_sql_pattern"] == True
        assert result["sql_pattern_count"] >= 2


class TestPathTraversalDetection:
    """Test path traversal detection"""

    def test_clean_path(self):
        result = detect_path_traversal("/api/files/document.pdf")
        assert result["has_traversal"] == False
        assert result["risk_level"] == "low"

    def test_dotdot_attack(self):
        result = detect_path_traversal("/api/files/../../etc/passwd")
        assert result["has_traversal"] == True
        assert result["traversal_count"] >= 1
        assert result["risk_level"] in ["medium", "high"]

    def test_encoded_dotdot(self):
        result = detect_path_traversal("/api/files/%2e%2e/%2e%2e/etc/passwd")
        assert result["has_traversal"] == True
        assert result["risk_level"] in ["medium", "high"]

    def test_windows_path(self):
        result = detect_path_traversal("/api/files/c:\\windows\\system32\\config")
        assert result["has_traversal"] == True

    def test_etc_passwd(self):
        result = detect_path_traversal("/etc/passwd")
        assert result["has_traversal"] == True


class TestSensitiveFileDetection:
    """Test sensitive file detection"""

    def test_clean_path(self):
        result = detect_sensitive_files("/api/users")
        assert result["accesses_sensitive"] == False
        assert result["count"] == 0

    def test_env_file(self):
        result = detect_sensitive_files("/.env")
        assert result["accesses_sensitive"] == True
        assert ".env" in result["sensitive_files"]

    def test_git_directory(self):
        result = detect_sensitive_files("/.git/config")
        assert result["accesses_sensitive"] == True
        assert ".git" in result["sensitive_files"]

    def test_htaccess(self):
        result = detect_sensitive_files("/.htaccess")
        assert result["accesses_sensitive"] == True

    def test_multiple_sensitive(self):
        result = detect_sensitive_files("/backup/.env.bak")
        assert result["accesses_sensitive"] == True
        assert result["count"] >= 2


class TestCommonExploitsDetection:
    """Test common exploit detection"""

    def test_clean_path(self):
        result = detect_common_exploits("/api/users")
        assert result["has_exploits"] == False
        assert result["total_patterns"] == 0
        assert result["risk_level"] == "low"

    def test_wordpress_scan(self):
        result = detect_common_exploits("/wp-admin/")
        assert result["has_exploits"] == True
        assert "wordpress" in result["exploit_categories"]

    def test_php_exploit(self):
        result = detect_common_exploits("/phpinfo.php")
        assert result["has_exploits"] == True
        assert "php_exploits" in result["exploit_categories"]

    def test_admin_scan(self):
        result = detect_common_exploits("/admin/login")
        assert result["has_exploits"] == True
        assert "admin_scans" in result["exploit_categories"]

    def test_shell_access(self):
        result = detect_common_exploits("/cgi-bin/shell.cgi")
        assert result["has_exploits"] == True
        assert "shell_access" in result["exploit_categories"]

    def test_xss_injection(self):
        result = detect_common_exploits("/<script>alert(1)</script>")
        assert result["has_exploits"] == True
        assert "injection" in result["exploit_categories"]

    def test_multiple_exploits(self):
        result = detect_common_exploits("/wp-admin/shell.php")
        assert result["has_exploits"] == True
        assert result["total_patterns"] >= 2
        assert result["risk_level"] in ["medium", "high"]


class TestPathCharacteristics:
    """Test path characteristics analysis"""

    def test_simple_path(self):
        result = analyze_path_characteristics("/api/users")
        assert result["length"] > 0
        assert result["num_slashes"] == 2
        assert result["has_query"] == False
        assert result["suspicious_chars"] == False

    def test_path_with_query(self):
        result = analyze_path_characteristics("/api/users?id=123&name=test")
        assert result["has_query"] == True
        assert result["num_params"] == 2

    def test_path_with_fragment(self):
        result = analyze_path_characteristics("/page#section")
        assert result["has_fragment"] == True

    def test_suspicious_characters(self):
        result = analyze_path_characteristics("/api/test?q=<script>")
        assert result["suspicious_chars"] == True

    def test_full_url(self):
        result = analyze_path_characteristics("https://example.com/api/users")
        assert result["num_slashes"] == 2  # Should strip protocol

    def test_complex_path(self):
        result = analyze_path_characteristics("/api/v1/users/123/posts?sort=date&limit=10")
        assert result["num_slashes"] == 5
        assert result["has_query"] == True
        assert result["num_params"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
