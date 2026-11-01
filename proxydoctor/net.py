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


def request_json(url, *, payload=None, headers=None):
    request_headers = {'Accept': 'application/json', 'Accept-Encoding': 'identity',
                       'User-Agent': 'ProxyDoctor/0.4'}
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
            result = json.loads(read_limited(response, 65536, deadline))
        if not isinstance(result, dict):
            return None, 'invalid_response'
        return result, 'ok'
    except urllib.error.HTTPError as exc:
        exc.close()
        return None, {401: 'invalid_key', 403: 'denied', 429: 'rate_limited'}.get(exc.code, 'http_' + str(exc.code))
    except (ValueError, OSError, urllib.error.URLError):
        return None, 'request_failed'
