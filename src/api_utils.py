"""Shared API response utilities - eliminates duplicate response helpers across modules"""
from typing import Any, Dict, Optional


def success_response(
    data: Any = None,
    message: str = None,
    meta: Optional[Dict[str, Any]] = None,
    use_legacy_format: bool = False
) -> Dict[str, Any]:
    """Build a standardized success response envelope.
    
    Supports both legacy and new calling conventions:
    - success_response(data=..., message=...) - new format
    - success_response(message=...) - legacy format from main.py
    
    Args:
        data: Response data payload
        message: Success message (default: "OK" for new format, None for legacy)
        meta: Optional metadata dictionary
        use_legacy_format: If True, uses {"ok": True} format instead of {"success": True}
    
    Returns:
        Standardized success response dictionary
    """
    if use_legacy_format:
        # Legacy format from main.py
        response = {"ok": True}
        if data is not None:
            response["data"] = data
        if message is not None:
            response["message"] = message
        return response
    
    # New format from task_manager.py
    response = {
        "success": True,
        "message": message if message else "OK",
    }
    if data is not None:
        response["data"] = data
    if meta:
        response["meta"] = meta
    return response


def error_response(
    message: str = None,
    code: str = "ERROR",
    details: Optional[Dict[str, Any]] = None,
    use_legacy_format: bool = False
) -> Dict[str, Any]:
    """Build a standardized error response envelope.
    
    Supports two calling conventions:
    - error_response(message, code) - new format (message first)
    - error_response(code, message) - legacy format from main.py
    
    Args:
        message: Error message (or second arg if using legacy format)
        code: Error code (default: "ERROR") (or first arg if using legacy format)
        details: Optional error details dictionary
        use_legacy_format: If True, uses {"ok": False} format instead of {"success": False}
    
    Returns:
        Standardized error response dictionary
    """
    # Handle legacy format: error_response(code, message) where code is int
    # In legacy format, first arg is code (int), second is message (str)
    if isinstance(message, int):
        # Legacy format: error_response(400, "message")
        actual_code = str(message)
        actual_message = code if isinstance(code, str) else "Unknown error"
    else:
        actual_code = code
        actual_message = message if message else "Unknown error"
    
    if use_legacy_format:
        # Legacy format from main.py
        return {
            "ok": False,
            "error": {
                "code": actual_code,
                "message": actual_message
            }
        }
    
    # New format from task_manager.py
    response = {
        "success": False,
        "error": {
            "code": actual_code,
            "message": actual_message,
        }
    }
    if details:
        response["error"]["details"] = details
    return response


def legacy_result_response(result: Any, **kwargs: Any) -> Dict[str, Any]:
    """Wrapper for legacy {"result": ...} responses - maintains compatibility.
    
    Args:
        result: The result payload
        **kwargs: Additional fields to include in response
    
    Returns:
        Legacy format response dictionary
    """
    return {"result": result, **kwargs}