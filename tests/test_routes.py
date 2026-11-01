import socket
import struct

from proxydoctor import routes


def test_native_trace_recognizes_destination_port_unreachable(monkeypatch):
    monkeypatch.setattr(routes.GeoLocator,'lookup',lambda self,address:'Test location')
    monkeypatch.setattr(routes.sys,'platform','linux')
    class FakeSocket:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def setsockopt(self,*args): pass
        def setblocking(self,*args): pass
        def sendto(self,data,address): self.dest=address
        def recvmsg(self,*args):
            error=struct.pack('=IBBBBII',111,2,3,3,0,0,0)
            offender=b'\x02\x00\x00\x00'+socket.inet_aton('1.1.1.1')+b'\x00'*8
            return b'',[(socket.IPPROTO_IP,11,error+offender)],0,self.dest
    monkeypatch.setattr(routes.socket,'socket',lambda *args: FakeSocket())
    output=[]
    assert routes.trace('1.1.1.1',emit=lambda text,**kwargs: output.append(text))==0
    assert '1.1.1.1' in output[0]


def test_unsupported_platform_does_not_open_sockets(monkeypatch):
    monkeypatch.setattr(routes.sys,'platform','win32')
    monkeypatch.setattr(routes.socket,'socket',lambda *args: (_ for _ in ()).throw(AssertionError()))
    assert routes.trace('1.1.1.1',emit=lambda *args,**kwargs: None)==1


def test_trace_can_reach_a_destination_after_twelve_hops(monkeypatch):
    monkeypatch.setattr(routes.sys,'platform','linux')
    monkeypatch.setattr(routes.GeoLocator,'lookup',lambda self,address:'Test location')
    class FakeSocket:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def setsockopt(self,level,option,value):
            if option==socket.IP_TTL: self.ttl=value
        def setblocking(self,*args): pass
        def sendto(self,data,address): self.dest=address
        def recvmsg(self,*args):
            reached=self.ttl==20
            error=struct.pack('=IBBBBII',111,2,3 if reached else 11,3 if reached else 0,0,0,0)
            offender=b'\x02\x00\x00\x00'+socket.inet_aton('1.1.1.1' if reached else '192.0.2.1')+b'\x00'*8
            return b'',[(socket.IPPROTO_IP,11,error+offender)],0,self.dest
    monkeypatch.setattr(routes.socket,'socket',lambda *args:FakeSocket())
    output=[]
    assert routes.trace('1.1.1.1',emit=lambda text,**kwargs:output.append(text))==0
    assert len(output)==20
