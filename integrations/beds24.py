import requests
from flask import current_app
from models import User
from extensions import db
from datetime import datetime, timezone, timedelta
import json
pms_token = ""

def set_pms(token):
    global pms_token
    pms_token = token

def update_token(refreshToken):
    url = "https://beds24.com/api/v2/authentication/token"
    # code = invite_code
    headers = {
        "accept": "application/json",
        "refreshToken" : refreshToken
    }
    params = {}
    response = requests.get(url, headers=headers, params=params)
    status = response.status_code
    result = json.loads(response.text)
    final_result={}
    if status==200:
        final_result = {
            "success":"success",
            "token":result["token"]
        }
    else:
        final_result = {
            "success":"error",
        }
    return final_result
    
def check_and_refresh_token(pms):
    if pms != "":
        # Find the user with the matching token
        user = User.query.filter_by(token=pms).first()
        if user and hasattr(user, 'token_refresh_date'):
            now = datetime.now(timezone.utc)
            # Ensure token_refresh_date is timezone-aware
            refresh_date = user.token_refresh_date
            if refresh_date.tzinfo is None:
                refresh_date = refresh_date.replace(tzinfo=timezone.utc)
            diff = now - refresh_date
            if diff > timedelta(hours=23):
                result = update_token(user.refresh_token)
                if result["success"]=="success":
                    user.token = result["token"]
                    user.token_refresh_date = now
                    set_pms(result["token"])
                    db.session.commit()
                    return result["token"]
                else:
                    return "error"
            else:
                return "success"
                    
     
def get_token_from_invite_code(invite_code):
    url = "https://beds24.com/api/v2/authentication/setup"
    code = invite_code
    headers = {
        "accept": "application/json",
        "code" : code
    }
    params = {}
    response = requests.get(url, headers=headers, params=params)
    status = response.status_code
    result = json.loads(response.text)

    final_result = {}
    print(result)
    if status==200: 
        final_result = {
            "success":"valid",
            "token":result["token"],
            "refreshToken":result["refreshToken"]
        }
    else:
        final_result = {
            "success":"invalid",
            "msg":result["error"]
        }
    return final_result

def get_users(pms):
    # print("0000000000000000")
    # print(pms_token)
    url = "https://beds24.com/api/v2/accounts"
    headers = {
        "accept": "application/json",
        "token": pms
    }
    params = {}
    response = requests.get(url, headers=headers, params=params)
    result = json.loads(response.text)
    data = result['data']
    return data

def get_hotels(pms):
    print(pms)
    url = "https://beds24.com/api/v2/properties"
    headers = {
        "accept": "application/json",
        "token": pms
    }
    params = {}
    response = requests.get(url, headers=headers, params=params)
    result = json.loads(response.text)
    data = result['data']
    return data

def get_auto_bookings(pms):
    url = "https://api.beds24.com/v2/bookings"

    headers = {
        "accept": "application/json",
        "token": pms
    }
    params = { }
    response = requests.get(url, headers=headers, params=params)
    result = json.loads(response.text)
    data = result['data']
    return data

class Beds24Client:
    """Minimal Beds24 client. Adjust headers/params per actual API spec.
    Store per-hotel propKey and apiKey in DB; base URL in app config.
    """

    def __init__(self, api_key: str, prop_key: str, base_url = None):
        self.api_key = api_key
        self.prop_key = prop_key
        self.base_url = base_url or current_app.config['BEDS24_BASE_URL']

    def _headers(self):
        # Depending on Beds24, API key may be in header or query. Adjust as needed.
        return {
            'Content-Type': 'application/json',
            'X-API-KEY': self.api_key,
        }
    
    
    
    def get_bookings(self, payload = None, pms = None):
        """Fetch bookings filtered by property and optional date window.
        NOTE: Endpoint path/params may differ; verify with Swagger.
        """
        url = f"{self.base_url}/bookings"
        params = {
        }
        # if start_iso:
        #     params['bookingTimeFrom'] = start_iso
        # if end_iso:
        #     params['bookingTimeTo'] = end_iso
        # params['propertyId'] = property_id
        url = f"{self.base_url}/bookings"
        headers = {
            "accept": "application/json",
            "token": pms
        }
        # print("999999")
        # print(payload)
        # payload.pop("hotelId", None)
        response = requests.get(url, headers=headers, params=payload)
        result = json.loads(response.text)
        data = result['data']
        # print("~~~~~~~~~~~~~~~")
        print(url)
        print(params)
        # print(data)
        return data