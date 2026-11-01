import subprocess
import sys


def test_nodequality_missing_script_fails(tmp_path):
    result = subprocess.run([sys.executable, '-m', 'proxydoctor', 'nodequality', '--lang', 'en', '--script', str(tmp_path / 'missing')], capture_output=True, text=True)
    assert result.returncode == 2
    assert 'Local script file not found' in result.stderr


def test_nodequality_streams_output_and_propagates_exit(tmp_path, monkeypatch, capsys):
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
        assert exc.code == 7
    else:
        raise AssertionError('expected exit')
    assert captured == [(['/bin/bash', str(script.resolve())], {'check': False})]
    assert 'LIVE OUTPUT' in capsys.readouterr().out
