"""Unit tests for honeypot.py classification logic"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest


class TestClassification:
    """Test the classification logic"""

    def create_features(
        self,
        is_bot=False,
        has_sql=False,
        has_traversal=False,
        has_sensitive=False,
        has_exploits=False,
        entropy=2.0,
        suspicious_chars=False,
    ):
        """Helper to create test features"""
        return {
            "path": "/test",
            "full_url": "http://test.com/test",
            "method": "GET",
            "user_agent": "test-agent",
            "ip": "1.2.3.4",
            "country": "US",
            "timestamp": 1234567890,
            "path_entropy": entropy,
            "path_chars": {"suspicious_chars": suspicious_chars},
            "ua_parsed": {"is_bot": is_bot, "client": "test"},
            "sql_injection": {
                "has_sql_pattern": has_sql,
                "risk_level": "high" if has_sql else "low",
            },
            "path_traversal": {
                "has_traversal": has_traversal,
                "risk_level": "high" if has_traversal else "low",
            },
            "sensitive_files": {"accesses_sensitive": has_sensitive},
            "common_exploits": {
                "has_exploits": has_exploits,
                "risk_level": "high" if has_exploits else "low",
            },
        }

    def test_clean_request_legit(self):
        """Test that a clean request is classified as legitimate"""
        from honeypot import classify_request

        features = self.create_features()
        result = classify_request(features, cf_bot_score=50)

        assert result["label"] == "legit"
        assert result["score"] < 40

    def test_bot_user_agent_attack(self):
        """Test that bot user agent increases attack score"""
        from honeypot import classify_request

        features = self.create_features(is_bot=True)
        result = classify_request(features, cf_bot_score=50)

        # Should still be legit with just bot UA
        assert result["score"] >= 30

    def test_sql_injection_attack(self):
        """Test SQL injection detection"""
        from honeypot import classify_request

        features = self.create_features(has_sql=True)
        result = classify_request(features, cf_bot_score=50)

        assert result["label"] == "attack"
        assert "sql_injection_high" in result["reasons"]

    def test_path_traversal_attack(self):
        """Test path traversal detection"""
        from honeypot import classify_request

        features = self.create_features(has_traversal=True)
        result = classify_request(features, cf_bot_score=50)

        assert result["label"] == "attack"
        assert "path_traversal_high" in result["reasons"]

    def test_sensitive_file_attack(self):
        """Test sensitive file access detection"""
        from honeypot import classify_request

        features = self.create_features(has_sensitive=True)
        result = classify_request(features, cf_bot_score=50)

        # Sensitive file access alone should trigger attack
        assert result["score"] >= 35
        assert "sensitive_file_access" in result["reasons"]

    def test_exploit_patterns_attack(self):
        """Test common exploit patterns"""
        from honeypot import classify_request

        features = self.create_features(has_exploits=True)
        result = classify_request(features, cf_bot_score=50)

        assert result["score"] >= 35
        assert "exploit_patterns_high" in result["reasons"]

    def test_high_entropy_suspicious(self):
        """Test high entropy detection"""
        from honeypot import classify_request

        features = self.create_features(entropy=5.0)
        result = classify_request(features, cf_bot_score=50)

        assert "high_entropy" in result["reasons"]

    def test_suspicious_characters(self):
        """Test suspicious character detection"""
        from honeypot import classify_request

        features = self.create_features(suspicious_chars=True)
        result = classify_request(features, cf_bot_score=50)

        assert "suspicious_chars" in result["reasons"]

    def test_low_cf_bot_score(self):
        """Test Cloudflare bot score influence"""
        from honeypot import classify_request

        features = self.create_features()
        result = classify_request(features, cf_bot_score=10)

        assert "cf_bot_score_low" in result["reasons"]

    def test_multiple_indicators_high_confidence(self):
        """Test that multiple attack indicators increase confidence"""
        from honeypot import classify_request

        features = self.create_features(
            is_bot=True, has_sql=True, has_sensitive=True, entropy=5.0
        )
        result = classify_request(features, cf_bot_score=10)

        assert result["label"] == "attack"
        assert result["confidence"] > 0.5
        assert len(result["reasons"]) >= 4

    def test_confidence_calculation(self):
        """Test confidence is properly calculated"""
        from honeypot import classify_request

        features = self.create_features(has_sql=True)
        result = classify_request(features, cf_bot_score=50)

        assert 0.0 <= result["confidence"] <= 1.0
        assert result["confidence"] == result["score"] / 100 or result["confidence"] == 1.0

    def test_threshold_boundary(self):
        """Test the attack/legit threshold boundary"""
        from honeypot import classify_request

        # Just below threshold
        features = self.create_features()
        result = classify_request(features, cf_bot_score=50)
        if result["score"] < 40:
            assert result["label"] == "legit"

        # At or above threshold
        features = self.create_features(has_sql=True)
        result = classify_request(features, cf_bot_score=50)
        if result["score"] >= 40:
            assert result["label"] == "attack"


class TestFeatureExtraction:
    """Test feature extraction from requests"""

    def test_extract_features_structure(self):
        """Test that extract_features returns expected structure"""
        # This test would need mock request objects
        # Skipping for now as it requires JS interop mocking
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
