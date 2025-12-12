"""Utility functions for tests"""
def consume_stream(response):
    """Consume a streaming response to prevent hanging"""
    if hasattr(response, 'response') and hasattr(response.response, '__iter__'):
        try:
            list(response.response)
        except Exception:
            pass
