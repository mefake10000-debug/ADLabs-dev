"""Small-install operator access. Deploy behind HTTPS; device keys stay server-side."""
import base64
import binascii
import os
import secrets


def access_settings():
    return {key: os.environ.get(key, '') for key in (
        'EDGESIGHT_SECURE_MODE', 'EDGESIGHT_OPERATOR_USER', 'EDGESIGHT_OPERATOR_PASSWORD',
        'EDGESIGHT_VIEWER_USER', 'EDGESIGHT_VIEWER_PASSWORD')}


def configuration_error(settings, api_key):
    user, password = settings['EDGESIGHT_OPERATOR_USER'], settings['EDGESIGHT_OPERATOR_PASSWORD']
    secure = settings['EDGESIGHT_SECURE_MODE'].lower() in {'1', 'true', 'yes'}
    if bool(user) != bool(password):
        return 'Both operator username and password are required'
    if secure and (not user or not password or not api_key):
        return 'Secure mode requires operator credentials and a device API key'
    if bool(settings['EDGESIGHT_VIEWER_USER']) != bool(settings['EDGESIGHT_VIEWER_PASSWORD']):
        return 'Both viewer username and password are required'
    if settings['EDGESIGHT_VIEWER_USER'] and not user:
        return 'Viewer access requires an operator account'
    return None


def operator_role(authorization, settings):
    if not authorization or not authorization.startswith('Basic '):
        return None
    try:
        decoded = base64.b64decode(authorization[6:], validate=True).decode('utf-8')
        user, password = decoded.split(':', 1)
    except (ValueError, UnicodeError, binascii.Error):
        return None
    for role, prefix in (('admin', 'EDGESIGHT_OPERATOR'), ('viewer', 'EDGESIGHT_VIEWER')):
        expected_user, expected_password = settings[prefix + '_USER'], settings[prefix + '_PASSWORD']
        user_ok = secrets.compare_digest(user.encode(), expected_user.encode())
        pass_ok = secrets.compare_digest(password.encode(), expected_password.encode())
        if expected_user and expected_password and user_ok and pass_ok:
            return role
    return None
