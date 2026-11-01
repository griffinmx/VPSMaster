import subprocess
import sys


def test_nodequality_missing_script_fails(tmp_path):
    result = subprocess.run([sys.executable, '-m', 'proxydoctor', 'nodequality', '--lang', 'en', '--script', str(tmp_path / 'missing')], capture_output=True, text=True)
    assert result.returncode == 2
    assert 'workflow may upload reports and is disabled' in result.stderr


def test_nodequality_disabled_never_executes_local_script(tmp_path, monkeypatch, capsys):
    from proxydoctor import cli
    script = tmp_path / 'script with spaces.sh'
    script.write_text('# test', encoding='utf-8')
    captured = []
    monkeypatch.setattr(cli.shutil, 'which', lambda name: '/bin/bash')
    def fake_run(args, **kwargs):
        captured.append((args, kwargs))
        print('LIVE OUTPUT')
        return subprocess.CompletedProcess(args, 7)
    monkeypatch.setattr(cli.subprocess, 'run', fake_run)
    monkeypatch.setattr(sys, 'argv', ['proxydoctor', 'nodequality', '--lang', 'en', '--script', str(script)])
    try:
        cli.main()
    except SystemExit as exc:
        assert exc.code == 2
    else:
        raise AssertionError('expected exit')
    assert captured == []
    assert 'LIVE OUTPUT' not in capsys.readouterr().out
