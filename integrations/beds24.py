import requests
from flask import current_app
import json
pms_token = "9ZKVmZHUdgKKPWpl/tBmF4SP9QIBOY72Iw99ARUho3RHTkcnZnAnly3CLKTopaIp8a7pcTIi2z5IPc5zMPJwdqDAp1vrwK7zRjnh0K3PU8IZYFnGFrv19DJy0ldCU/6IwxI5WMlb4vPXNf0YRNel0f4R5CUFNZGrzVWC0Zoeb38="

def get_users():
    url = "https://beds24.com/api/v2/accounts"
    headers = {
        "accept": "application/json",
        "token": pms_token
    }
    params = {}
    response = requests.get(url, headers=headers, params=params)
    result = json.loads(response.text)
    data = result['data']
    return data

def get_hotels():
    url = "https://beds24.com/api/v2/properties"
    headers = {
        "accept": "application/json",
        "token": pms_token
    }
    params = {}
    response = requests.get(url, headers=headers, params=params)
    result = json.loads(response.text)
    data = result['data']
    return data

def get_auto_bookings():
    url = "https://api.beds24.com/v2/bookings"

    headers = {
        "accept": "application/json",
        "token": pms_token
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
    
    
    
    def get_bookings(self, payload = None):
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
            "token": pms_token
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