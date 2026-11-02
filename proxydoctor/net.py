"""Bounded HTTPS JSON requests. Never return provider errors or credentials."""
import json
import time
import urllib.error
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())


def read_limited(response, limit, deadline):
    chunks = []
    total = 0
    while total <= limit:
        if time.monotonic() >= deadline:
            raise TimeoutError()
        # read1 returns after one underlying read instead of filling a huge buffer.
        read = getattr(response, 'read1', response.read)
        block = read(min(65536, limit + 1 - total))
        if not block:
            return b''.join(chunks)
        total += len(block)
        chunks.append(block)
    raise ValueError('response_too_large')


def request_json(url, *, payload=None, headers=None, max_bytes=65536):
    if not isinstance(max_bytes,int) or not 1<=max_bytes<=524288:
        raise ValueError('Invalid JSON response limit')
    from .worker import enabled,invoke
    if enabled():
        result=invoke('json',{'url':url,'payload':payload,'headers':headers,'max_bytes':max_bytes})
        return tuple(result) if isinstance(result,list) and len(result)==2 else (None,'request_failed')
    request_headers = {'Accept': 'application/json', 'Accept-Encoding': 'identity',
                       'User-Agent': 'VPSMaster/1.0.0b1'}
    request_headers.update(headers or {})
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        request_headers['Content-Type'] = 'application/json'
    request = urllib.request.Request(url, data=data, headers=request_headers)
    deadline = time.monotonic() + 15
    try:
        with opener().open(request, timeout=8) as response:
            if response.status != 200:
                return None, 'http_' + str(response.status)
            result = json.loads(read_limited(response, max_bytes, deadline))
        if not isinstance(result, dict):
            return None, 'invalid_response'
        return result, 'ok'
    except urllib.error.HTTPError as exc:
        exc.close()
        return None, {401: 'invalid_key', 403: 'denied', 429: 'rate_limited'}.get(exc.code, 'http_' + str(exc.code))
    except (ValueError, OSError, urllib.error.URLError):
        return None, 'request_failed'
