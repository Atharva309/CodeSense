# app/http_client.py
import requests
from requests.adapters import HTTPAdapter, Retry

DEFAULT_TIMEOUT = 10

_session = requests.Session()
_retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 502, 503, 504])
_session.mount("https://", HTTPAdapter(max_retries=_retries))
_session.mount("http://",  HTTPAdapter(max_retries=_retries))

def get(url, **kwargs):
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    return _session.get(url, **kwargs)

def post(url, **kwargs):
    kwargs.setdefault("timeout", DEFAULT_TIMEOUT)
    return _session.post(url, **kwargs)