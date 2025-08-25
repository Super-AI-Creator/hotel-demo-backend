import requests
from flask import current_app
from typing import Optional
from datetime import datetime, timezone, timedelta
import hashlib


def get_pms_token(client_id, client_secret, user_id, user_password, prop_key):
    """Get PMS token (access token) for hotel API using username/password and propKey."""
    password_md5 = hashlib.md5(user_password.encode('utf-8')).hexdigest()
    url = "https://euapi.ttlock.com/oauth2/token"
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "username": user_id,
        "password": password_md5,
        "grant_type": "password",
        "prop_key":prop_key
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    resp = requests.post(url, data=payload, headers=headers)
    resp.raise_for_status()
    token_data = resp.json()
    if "access_token" not in token_data:
        raise Exception(f"Failed to get PMS token: {token_data}")
    return token_data["access_token"]

class TTLockClient:
    """Minimal TTLock client wrapper for Python 3.9."""
    

    def __init__(self, client_id: str, client_secret: str, user_id: str,  user_password: str,prop_key : str,  base_url: Optional[str] = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = get_pms_token(client_id,client_secret,user_id, user_password, prop_key)
        self.base_url = base_url or current_app.config['TTLOCK_BASE_URL']

    def _params(self):
        return {
            'clientId': self.client_id,
            'accessToken': self.access_token,
        }

    def create_or_update_pin(self, lock_id: str, pin_code: str, start_ts_ms: int, end_ts_ms: int, name: Optional[str] = None, prop_key: str = ""):
        """Create a time-limited keyboard password (PIN) for a lock."""
        url = f"{self.base_url}/v3/keyboardPwd/add"
        lock_tz = timezone(timedelta(hours=2))  # UTC+2 example for Europe
        current_date = int(datetime.now(lock_tz).timestamp() * 1000)
        payload = {
            **self._params(),
            'lockId': lock_id,
            'keyboardPwd': pin_code,
            'startDate': start_ts_ms,
            'endDate': end_ts_ms,
            'date': current_date,
            'addType': 2,
            "keyboardPwdName": name,
            'prop_key': prop_key
        }
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        try:
            
            r = requests.post(url, data=payload, timeout=30, headers=headers)
            r.raise_for_status()
            print("-----------------------")
            print(r.json())
            return r.json()
        
        except Exception as e:
            print("-------------**********----------")
            print(str(e))

            return {'error': True, 'message': str(e), 'body': getattr(r, 'text', None)}
    def get_locks(self):
        """Fetch all locks for the account (requires valid access token)."""
        url = "https://euapi.ttlock.com/v3/lock/list"
        params = {
            **self._params(),
            "pageNo": 1,
            "pageSize": 50,
            "date": int(datetime.now(timezone.utc).timestamp() * 1000),
        }

        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

        # TTLock returns either {"list": [...]} or {"errcode": N}
        if "errcode" in data and data["errcode"] != 0:
            raise Exception(f"Failed to fetch locks: {data}")

        return data.get("list", [])