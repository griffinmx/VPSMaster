import pytest

from proxydoctor.media import Page, classify


@pytest.mark.parametrize('service,message',[
    ('Netflix','Netflix is not available in your country'),
    ('Disney+','Disney+ is not available in your region'),
    ('YouTube Premium','Premium is not available in your country'),
])
def test_explicit_region_restriction(service,message):
    assert classify(service,Page(200,'<p>'+message+'</p>'))['state']=='restricted'


@pytest.mark.parametrize('status',[200,301,403,404,429,503,None])
def test_status_alone_never_means_playback_or_geoblock(status):
    assert classify('Netflix',Page(status,'<h1>Hello</h1>'))['state']=='unknown'


def test_translations_in_scripts_are_not_geoblock_evidence():
    page=Page(200,'<script>"Netflix is not available in your country"</script><p>Join now</p>')
    assert classify('Netflix',page)['state']=='unknown'


def test_partial_response_does_not_support_classification():
    page=Page(200,'Netflix is not available in your country',reason='response_too_large')
    assert classify('Netflix',page)['state']=='unknown'


@pytest.mark.parametrize('attribute',['hidden','aria-hidden="true"','style="display: none"'])
def test_explicitly_hidden_region_messages_are_not_evidence(attribute):
    page=Page(200,f'<div {attribute}>Netflix is not available in your country</div><p>Welcome</p>')
    assert classify('Netflix',page)['state']=='unknown'
