from functools import wraps
from typing import Callable, Any
from flask import session, redirect, url_for, abort

def login_required(f: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator that ensures the user is authenticated.
    Uses @wraps to maintain function metadata for introspection.
    """
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        # SAST check: session management
        if 'username' not in session:
            # We redirect to the login entry point of your app
            # Avoid using request.args.get('next') directly to prevent Open Redirects
            return redirect(url_for('auth.index'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(required_role: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator that ensures the user has a specific role.
    Uses abort(403) for proper HTTP signaling of Forbidden access.
    """
    def decorator(f: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            # Check user role against required role
            if session.get('role') != required_role:
                # Proper HTTP error code for Forbidden access
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator