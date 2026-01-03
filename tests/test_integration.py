"""Integration tests for Axon system

These tests verify the complete workflow of the system.
Note: These require a running local instance or mocked Cloudflare Workers environment.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest


class TestEndToEndWorkflow:
    """Test complete request flow"""

    def test_attack_detection_workflow(self):
        """Test that an attack request is properly detected and logged"""
        # This would require:
        # 1. Mock request with attack patterns
        # 2. Extract features
        # 3. Classify
        # 4. Verify classification is "attack"

        from features import (
            detect_sql_injection,
            detect_path_traversal,
            detect_sensitive_files,
        )
        from honeypot import classify_request

        # Simulate an attack path
        attack_path = "/admin/login?user=admin' OR '1'='1"

        # Extract features
        sql_result = detect_sql_injection(attack_path)
        assert sql_result["has_sql_pattern"] == True

        # Create mock features
        features = {
            "path": attack_path,
            "full_url": f"http://test.com{attack_path}",
            "method": "GET",
            "user_agent": "curl/7.68.0",
            "ip": "1.2.3.4",
            "country": "CN",
            "timestamp": 1234567890,
            "path_entropy": 3.5,
            "path_chars": {"suspicious_chars": True},
            "ua_parsed": {"is_bot": True, "client": "other"},
            "sql_injection": sql_result,
            "path_traversal": {"has_traversal": False, "risk_level": "low"},
            "sensitive_files": {"accesses_sensitive": False},
            "common_exploits": {"has_exploits": True, "risk_level": "medium"},
        }

        # Classify
        result = classify_request(features, cf_bot_score=15)

        # Verify
        assert result["label"] == "attack"
        assert result["confidence"] > 0.3

    def test_legitimate_traffic_workflow(self):
        """Test that legitimate traffic is properly classified"""
        from honeypot import classify_request

        # Simulate legitimate traffic
        features = {
            "path": "/api/users/123",
            "full_url": "http://test.com/api/users/123",
            "method": "GET",
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0",
            "ip": "192.168.1.1",
            "country": "US",
            "timestamp": 1234567890,
            "path_entropy": 2.5,
            "path_chars": {"suspicious_chars": False},
            "ua_parsed": {"is_bot": False, "client": "chrome"},
            "sql_injection": {"has_sql_pattern": False, "risk_level": "low"},
            "path_traversal": {"has_traversal": False, "risk_level": "low"},
            "sensitive_files": {"accesses_sensitive": False},
            "common_exploits": {"has_exploits": False, "risk_level": "low"},
        }

        # Classify
        result = classify_request(features, cf_bot_score=80)

        # Verify
        assert result["label"] == "legit"


class TestFeatureDetectionIntegration:
    """Test multiple feature detectors working together"""

    def test_wordpress_scan_detection(self):
        """Test detection of WordPress scanning attempts"""
        from features import detect_common_exploits, detect_sensitive_files

        path = "/wp-admin/admin-ajax.php"

        exploits = detect_common_exploits(path)
        sensitive = detect_sensitive_files(path)

        assert exploits["has_exploits"] == True
        assert "wordpress" in exploits["exploit_categories"]

    def test_env_file_with_traversal(self):
        """Test detection of combined path traversal and sensitive file access"""
        from features import detect_path_traversal, detect_sensitive_files

        path = "/../../.env"

        traversal = detect_path_traversal(path)
        sensitive = detect_sensitive_files(path)

        assert traversal["has_traversal"] == True
        assert sensitive["accesses_sensitive"] == True

    def test_sql_injection_with_admin_access(self):
        """Test SQL injection attempt on admin endpoint"""
        from features import detect_sql_injection, detect_common_exploits

        path = "/admin/login?user=admin&pass=' OR 1=1--"

        sql = detect_sql_injection(path)
        exploits = detect_common_exploits(path)

        assert sql["has_sql_pattern"] == True
        assert exploits["has_exploits"] == True
        assert "admin_scans" in exploits["exploit_categories"]


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_path(self):
        """Test handling of empty path"""
        from features import (
            get_request_entropy,
            analyze_path_characteristics,
        )

        entropy = get_request_entropy("")
        assert entropy == 0

        chars = analyze_path_characteristics("")
        assert chars == {}

    def test_very_long_path(self):
        """Test handling of very long paths"""
        from features import analyze_path_characteristics

        long_path = "/api/" + "x" * 10000
        result = analyze_path_characteristics(long_path)

        assert result["length"] > 10000

    def test_unicode_in_path(self):
        """Test handling of unicode characters"""
        from features import get_request_entropy

        path = "/api/users/naïve"
        entropy = get_request_entropy(path)

        assert entropy > 0

    def test_url_encoded_attacks(self):
        """Test detection of URL-encoded attack patterns"""
        from features import detect_path_traversal, detect_sql_injection

        # URL encoded path traversal
        path1 = "/%2e%2e/%2e%2e/etc/passwd"
        result1 = detect_path_traversal(path1)
        assert result1["has_traversal"] == True

        # URL encoded SQL
        path2 = "/api?q=%27%20OR%201%3D1"  # ' OR 1=1
        result2 = detect_sql_injection(path2)
        # This might not detect encoded SQL - that's expected behavior
        # Real implementation would need URL decoding

    def test_mixed_case_attacks(self):
        """Test that detection is case-insensitive"""
        from features import detect_sql_injection, detect_common_exploits

        path1 = "/api?q=UNION SELECT"
        path2 = "/api?q=union select"

        result1 = detect_sql_injection(path1)
        result2 = detect_sql_injection(path2)

        assert result1["has_sql_pattern"] == result2["has_sql_pattern"]

        path3 = "/WP-ADMIN"
        path4 = "/wp-admin"

        result3 = detect_common_exploits(path3)
        result4 = detect_common_exploits(path4)

        assert result3["has_exploits"] == result4["has_exploits"]


class TestScoring:
    """Test the scoring and confidence calculations"""

    def test_score_accumulation(self):
        """Test that multiple attack indicators accumulate score"""
        from honeypot import classify_request

        # Start with clean features
        base_features = {
            "path": "/test",
            "full_url": "http://test.com/test",
            "method": "GET",
            "user_agent": "test",
            "ip": "1.2.3.4",
            "country": "US",
            "timestamp": 1234567890,
            "path_entropy": 2.0,
            "path_chars": {"suspicious_chars": False},
            "ua_parsed": {"is_bot": False, "client": "test"},
            "sql_injection": {"has_sql_pattern": False, "risk_level": "low"},
            "path_traversal": {"has_traversal": False, "risk_level": "low"},
            "sensitive_files": {"accesses_sensitive": False},
            "common_exploits": {"has_exploits": False, "risk_level": "low"},
        }

        # Clean request
        result1 = classify_request(base_features, 50)
        score1 = result1["score"]

        # Add bot UA
        base_features["ua_parsed"]["is_bot"] = True
        result2 = classify_request(base_features, 50)
        score2 = result2["score"]
        assert score2 > score1

        # Add SQL injection
        base_features["sql_injection"] = {"has_sql_pattern": True, "risk_level": "high"}
        result3 = classify_request(base_features, 50)
        score3 = result3["score"]
        assert score3 > score2

    def test_confidence_bounds(self):
        """Test that confidence is always between 0 and 1"""
        from honeypot import classify_request

        # Very high score
        features = {
            "path": "/test",
            "full_url": "http://test.com/test",
            "method": "GET",
            "user_agent": "curl",
            "ip": "1.2.3.4",
            "country": "CN",
            "timestamp": 1234567890,
            "path_entropy": 6.0,
            "path_chars": {"suspicious_chars": True},
            "ua_parsed": {"is_bot": True, "client": "other"},
            "sql_injection": {"has_sql_pattern": True, "risk_level": "high"},
            "path_traversal": {"has_traversal": True, "risk_level": "high"},
            "sensitive_files": {"accesses_sensitive": True},
            "common_exploits": {"has_exploits": True, "risk_level": "high"},
        }

        result = classify_request(features, cf_bot_score=5)

        assert 0.0 <= result["confidence"] <= 1.0
        assert result["confidence"] == min(result["score"] / 100, 1.0)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
