import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from src.utils.logger import structlog


def test_logger_configuration():
    """Test logger configuration and basic logging functionality"""
    logger = structlog.get_logger()

    # Test different log levels
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")

    # Test with additional context
    logger = logger.bind(request_id="test-123")
    logger.info("Message with context",
                additional_field="test",
                numeric_value=42)

    # Test error logging with exception
    try:
        raise ValueError("Test exception")
    except Exception as e:
        logger.error("Error occurred",
                     exc_info=True,
                     error=str(e))


def test_logger_with_different_contexts():
    """Test logger with different context combinations"""
    logger = structlog.get_logger()

    # Test with dictionary context
    context = {
        "user_id": "user-123",
        "action": "test",
        "timestamp": "2024-01-01"
    }
    logger.info("Action performed", **context)

    # Test with nested context
    nested_context = {
        "request": {
            "method": "GET",
            "path": "/test",
            "params": {"id": "123"}
        },
        "response": {
            "status": 200,
            "time": "100ms"
        }
    }
    logger.info("API request", **nested_context)


def test_logger_error_handling():
    """Test logger error handling capabilities"""
    logger = structlog.get_logger()

    # Test with exception chain
    try:
        try:
            raise ValueError("Inner error")
        except ValueError as e:
            raise RuntimeError("Outer error") from e
    except RuntimeError as e:
        logger.error("Chained error occurred",
                     exc_info=True,
                     error=str(e))
