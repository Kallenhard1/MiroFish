"""
Usage tracking API routes
"""

from flask import jsonify
from . import usage_bp
from ..services.usage_tracker import UsageTracker
from ..utils.logger import get_logger

logger = get_logger('mirofish.api.usage')


@usage_bp.route('/<project_id>', methods=['GET'])
def get_usage(project_id: str):
    try:
        data = UsageTracker.get_usage(project_id)
        return jsonify({"success": True, "data": data})
    except Exception as e:
        logger.error(f"get_usage failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
