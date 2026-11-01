"""Repeated, traffic-bounded HTTPS throughput measurements; not line capacity."""
from dataclasses import asdict, dataclass
import math
import os
import re
import statistics
import time
import urllib.error
import urllib.request

from .net import opener, read_limited


@dataclass(frozen=True)
class Source:
    name: str
    region: str
    download_url: str
    upload_url: str | None = None
    use_range: bool = False
    capped_stream: bool = False
    carrier: str | None = None
    mainland: bool | None = None


# Fixed official test endpoints only. No arbitrary URLs, account keys or binaries.
SOURCES = {
    'cloudflare': Source('Cloudflare','Anycast','https://speed.cloudflare.com/__down',
                         'https://speed.cloudflare.com/__up'),
    'hetzner-fsn': Source('Hetzner','DE / Falkenstein','https://fsn1-speed.hetzner.com/100MB.bin',use_range=True),
    'ovh-rbx': Source('OVHcloud','FR / Roubaix','https://lil1-rbx.speedtest.network.ovh.net/files/100Mb.dat',use_range=True),
    'cn-telecom-sh': Source('China Telecom','CN / Shanghai','https://speedtest1.online.sh.cn:8080/speedtest/random4000x4000.jpg',
                            capped_stream=True,carrier='telecom',mainland=True),
    'cn-unicom-sh': Source('China Unicom','CN / Shanghai','https://mobile.shunicomtest.com:8080/speedtest/random4000x4000.jpg',
                           capped_stream=True,carrier='unicom',mainland=True),
    'cn-mobile-fz': Source('China Mobile','CN / Fuzhou','https://csfw.fj.chinamobile.com:8080/speedtest/random4000x4000.jpg',
                           capped_stream=True,carrier='mobile',mainland=True),
    'mobile-hk': Source('China Mobile Hong Kong','HK / not mainland China','https://speedtestbb.hk.chinamobile.com:8080/speedtest/random4000x4000.jpg',
                        capped_stream=True,carrier='mobile',mainland=False),
}
CHINA_SOURCES=('cn-telecom-sh','cn-unicom-sh','cn-mobile-fz')
# Keep the slower, environment-sensitive Hetzner endpoint explicitly selectable.
DEFAULT_SOURCES = ('cloudflare','ovh-rbx')


def source_ids(selected=None):
    selected = DEFAULT_SOURCES if selected is None else tuple(dict.fromkeys(selected))
    if not selected or any(identifier not in SOURCES for identifier in selected):
        raise ValueError('Invalid bandwidth source')
    return selected


def payload_budget(rounds, sample_mib, selected=None):
    return sum((2 if SOURCES[name].upload_url else 1) * (rounds * sample_mib * 1024**2 + 131072)
               for name in source_ids(selected))


@dataclass
class Sample:
    direction: str
    size_bytes: int
    elapsed_s: float = 0
    mbps: float | None = None
    error: str | None = None
    pop: str | None = None
    source: str = 'cloudflare'


def transfer(direction, size, source='cloudflare'):
    from .worker import enabled,invoke
    if enabled():
        result=invoke('transfer',{'direction':direction,'size':size,'source':source},timeout=25)
        return Sample(**result) if isinstance(result,dict) else Sample(direction,size,error='request_failed',source=source)
    if direction not in ('download', 'upload') or not 1 <= size <= 20 * 1024**2:
        raise ValueError('Invalid transfer limits')
    if source not in SOURCES:
        raise ValueError('Invalid bandwidth source')
    provider = SOURCES[source]
    result = Sample(direction, size, source=source)
    if direction == 'upload' and provider.upload_url is None:
        result.error = 'unsupported'
        return result
    headers = {'User-Agent': 'ProxyDoctor/0.4.1', 'Accept-Encoding': 'identity',
               'Cache-Control': 'no-cache'}
    url = provider.download_url
    if not provider.use_range and not provider.capped_stream:
        url += '?bytes=' + str(size)
    elif provider.use_range:
        headers['Range'] = f'bytes=0-{size-1}'
    data = None
    if direction == 'upload':
        url = provider.upload_url
        headers.pop('Range',None)
        data = os.urandom(size)  # Avoid compressible uploads artificially inflating results.
        headers['Content-Type'] = 'application/octet-stream'
    request = urllib.request.Request(url, data=data, headers=headers)
    start = time.monotonic()
    try:
        with opener().open(request, timeout=12) as response:
            ranged = direction == 'download' and provider.use_range
            if ranged and response.status == 200:
                # Never fall back to downloading an entire 100 MB test file.
                result.error = 'range_not_supported'
                return result
            if response.status != (206 if ranged else 200):
                result.error = 'http_' + str(response.status)
                return result
            if ranged:
                match = re.fullmatch(r'bytes 0-(\d+)/(\d+)',response.headers.get('Content-Range',''))
                length = response.headers.get('Content-Length')
                if (not match or int(match[1]) != size-1 or int(match[2]) < size
                        or (length is not None and length != str(size))):
                    result.error = 'invalid_content_range'
                    return result
            if ('text/html' in response.headers.get('Content-Type','').lower()
                    or response.headers.get('Content-Encoding','identity').lower() not in ('','identity')):
                result.error = 'unexpected_content'
                return result
            ray = response.headers.get('CF-Ray', '')
            pop = ray.rsplit('-', 1)[-1]
            if len(pop) == 3 and pop.isalpha():
                result.pop = pop.upper()
            if direction=='download' and provider.capped_stream:
                # Fixed public test images often ignore Range. Read exactly the
                # consented payload, then close; never consume the full object.
                if not response.headers.get('Content-Type','').lower().startswith('image/jpeg'):
                    result.error='unexpected_test_content';return result
                chunks=[];remaining=size
                while remaining:
                    if time.monotonic()-start>20:raise TimeoutError()
                    read=getattr(response,'read1',response.read)
                    block=read(min(65536,remaining))
                    if not block:break
                    chunks.append(block);remaining-=len(block)
                body=b''.join(chunks)
                if not body.startswith(b'\xff\xd8'):
                    result.error='unexpected_test_content';return result
            else:
                body = read_limited(response, size if direction == 'download' else 65536, start + 30)
            if direction == 'download' and len(body) != size:
                result.error = 'short_response'
                return result
        result.elapsed_s = time.monotonic() - start
        if result.elapsed_s <= 0 or not math.isfinite(result.elapsed_s):
            result.error = 'invalid_duration'
        else:
            result.mbps = round(size * 8 / result.elapsed_s / 1_000_000, 3)
    except urllib.error.HTTPError as exc:
        result.error = 'http_' + str(exc.code)
        exc.close()
    except ValueError:
        result.error = 'response_too_large'
    except (OSError, urllib.error.URLError):
        result.error = 'request_failed'
    finally:
        result.elapsed_s = round(max(0, time.monotonic() - start), 4)
    return result


def summarize(samples):
    good = [s for s in samples if s.error is None and s.mbps is not None and math.isfinite(s.mbps) and s.mbps > 0]
    speeds = [s.mbps for s in good]
    median = statistics.median(speeds) if speeds else None
    spread = (max(speeds) - min(speeds)) / median if median else None
    enough = len(good) >= 3 and len(good) == len(samples)
    return {'successful': len(good), 'attempted': len(samples),
            'median_mbps': round(median, 3) if median is not None else None,
            'min_mbps': min(speeds) if speeds else None, 'max_mbps': max(speeds) if speeds else None,
            'spread_percent': round(spread * 100, 1) if spread is not None else None,
            'quality': 'unavailable' if not speeds else 'insufficient' if not enough else
                       'short_samples' if any(s.elapsed_s < 1 for s in good) else
                       'variable' if spread > .3 else 'consistent',
            'samples': [asdict(s) for s in samples]}


def measure(rounds=3, sample_mib=4, on_sample=None, source='cloudflare'):
    if not 3 <= rounds <= 8 or not 1 <= sample_mib <= 20:
        raise ValueError('Invalid benchmark limits')
    source_ids((source,))
    provider = SOURCES[source]
    report = {'source':source,'provider':provider.name,'region':provider.region,
              'carrier_claim':provider.carrier,'mainland_china':provider.mainland,
              'provider_identity':'catalogue_claim' if provider.carrier else 'official_test_endpoint',
              'directions_scope':'download: node_to_this_host; upload: this_host_to_node',
              'download_url':provider.download_url,'upload_supported':provider.upload_url is not None,
              'method': 'sequential_https_wall_time',
              'payload_budget_bytes': payload_budget(rounds,sample_mib,(source,)),
              'warmups': {}, 'directions': {}}
    def sample_transfer(direction,size):
        # Preserve the original single-source Python API.
        return transfer(direction,size) if source=='cloudflare' else transfer(direction,size,source=source)
    for direction in (('download','upload') if provider.upload_url else ('download',)):
        warmup = sample_transfer(direction, 131072)
        report['warmups'][direction] = asdict(warmup)
        samples = []
        for number in range(1, rounds + 1):
            # Do not hammer an endpoint that explicitly refuses or rate-limits us.
            previous = samples[-1] if samples else warmup
            if previous.error in ('http_403','http_429','provider_refused'):
                sample = Sample(direction,sample_mib*1024**2,error='provider_refused',source=source)
            elif previous.error in ('range_not_supported','invalid_content_range','unexpected_content','source_unavailable'):
                sample = Sample(direction,sample_mib*1024**2,error=previous.error,source=source)
            elif samples and previous.error and (samples[-2].error if len(samples)>1 else warmup.error):
                sample = Sample(direction,sample_mib*1024**2,error='source_unavailable',source=source)
            else:
                sample = sample_transfer(direction,sample_mib*1024**2)
            samples.append(sample)
            if on_sample:
                on_sample(direction, number, rounds, sample)
        report['directions'][direction] = summarize(samples)
    return report


def measure_many(rounds=3, sample_mib=4, sources=None, on_source=None, on_sample=None):
    if not 3 <= rounds <= 8 or not 1 <= sample_mib <= 20:
        raise ValueError('Invalid benchmark limits')
    selected=source_ids(sources)
    report={'schema_version':2,'method':'sequential_https_wall_time',
            'payload_budget_bytes':payload_budget(rounds,sample_mib,selected),'sources':{}}
    for identifier in selected:
        if on_source: on_source(identifier,'start',None)
        callback=(lambda *args: on_sample(identifier,*args)) if on_sample else None
        result=measure(rounds,sample_mib,callback,source=identifier)
        report['sources'][identifier]=result
        if on_source: on_source(identifier,'complete',result)
    return report


def is_complete(report):
    return all(result['quality']=='consistent' for source in report['sources'].values()
               for result in source['directions'].values())


def run_console(lang='zh',color='auto',rounds=3,sample_mib=4,sources=None,destination=None,on_result=None,*,out=None):
    from .console import Console
    out=out if out is not None else Console(lang,color);tr=out.text
    selected=source_ids(sources)
    budget=payload_budget(rounds,sample_mib,selected)/1024**2
    out.line(tr(f'{len(selected)} 个来源 · 每方向 {rounds} 轮 × {sample_mib} MiB · 请求载荷最多 {budget:g} MiB',
                f'{len(selected)} sources · {rounds} rounds × {sample_mib} MiB/direction · requested payload ≤ {budget:g} MiB'))
    def source_output(identifier,event,result):
        provider=SOURCES[identifier]
        if event=='start':
            out.line(f'{provider.name} · {provider.region}','title')
            out.row(tr('测速方向','Direction'),tr('下载：节点 → 本机；上传：本机 → 节点','Download: node → this host; upload: this host → node'),'unknown')
            if not provider.upload_url: out.row(tr('上传','Upload'),tr('不支持（该来源仅提供下载）','Not supported (download-only source)'),'unknown')
            return
        for direction,summary in result['directions'].items():
            label=tr('下载统计','Download summary') if direction=='download' else tr('上传统计','Upload summary')
            median=summary['median_mbps']
            value=tr('无有效样本','No valid samples') if median is None else tr(
                f"中位 {median:.2f} · 范围 {summary['min_mbps']:.2f}–{summary['max_mbps']:.2f} Mbps · {summary['successful']}/{summary['attempted']} 成功",
                f"Median {median:.2f} · Range {summary['min_mbps']:.2f}–{summary['max_mbps']:.2f} Mbps · {summary['successful']}/{summary['attempted']} OK")
            out.row(label,value,'ok' if summary['quality']=='consistent' else 'unknown')
            note={'short_samples':tr('样本短于 1 秒，容量未知','Samples below 1s; capacity unknown'),
                  'variable':tr('轮间波动较大','High variation between rounds'),
                  'insufficient':tr('有效轮次不足','Insufficient successful rounds')}.get(summary['quality'])
            if note: out.row('',note,'unknown')
    def sample_output(identifier,direction,number,total,sample):
        if destination is not None:
            destination.setdefault('sample_events',[]).append(asdict(sample))
            if on_result is not None:on_result()
        label=tr('下载','Download') if direction=='download' else tr('上传','Upload')
        value=f'{sample.mbps:.2f} Mbps · {sample.elapsed_s:.2f}s' if sample.mbps is not None else tr('未成功','Failed')+' · '+str(sample.error)
        if sample.pop: value+=' · '+sample.pop
        out.row(f'{label} {number}/{total}',value,'ok' if sample.mbps is not None else 'unknown')
    result=measure_many(rounds,sample_mib,selected,source_output,sample_output)
    if destination is not None:
        destination.update(result)
        return destination
    return result
