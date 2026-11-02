"""Compact terminal output with optional ANSI colour and an iprisk-style theme."""
import os
import re
import sys
import unicodedata
import shutil

_UNSAFE = re.compile(r'[\x00-\x1f\x7f-\x9f\u202a-\u202e\u2066-\u2069]')

# ANSI SGR codes used by the themed renderer.
_RESET = '\033[0m'
_CODES = {
    'ok': '32', 'bad': '31', 'warn': '33', 'unknown': '33',
    'title': '36', 'muted': '90',
    # block / badge colours for the iprisk theme
    'b_green': '32', 'b_yellow': '33', 'b_red': '31', 'b_cyan': '36',
}
# Reverse-video badge text is rendered with background colours.
_BG = {'b_green': '42', 'b_yellow': '43', 'b_red': '41', 'b_cyan': '46'}


def clean(value):
    return _UNSAFE.sub(' ', str(value)).strip()


def _cwidth(ch):
    """Display width of one character (2 for wide CJK, 0 for combining)."""
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ('W', 'F') else 1


def width(value):
    return sum(_cwidth(ch) for ch in str(value))


def _pad(value, target):
    return value + ' ' * max(0, target - width(value))


def wrap_columns(value, columns):
    """Wrap without losing text or splitting a wide character across columns."""
    if columns < 2:
        raise ValueError('At least two columns are required')
    chunk = ''; used = 0
    for ch in clean(value):
        size = _cwidth(ch)
        if used + size > columns:
            yield chunk
            chunk = ''; used = 0
        chunk += ch; used += size
    yield chunk


def can_render_cjk():
    """Best-effort detection of a console that can draw CJK glyphs.

    Returns False when we are confident the terminal cannot render Chinese
    (e.g. the Linux kernel framebuffer console tty1..tty63, which only ships
    ASCII/Latin fonts). Returns True otherwise (we are NOT certain, so this is
    a conservative "probably fine" answer).
    """
    if sys.platform == 'win32':
        return True
    tty = ''
    try:
        tty = os.ttyname(0)
    except OSError:
        tty = ''
    if re.match(r'^/dev/(tty|vc/)\d+', tty):
        return False
    return True


class Console:
    def __init__(self, lang='zh', color='auto', hide_unavailable=False):
        self.lang = lang
        self.hide_unavailable = hide_unavailable
        self.enabled = color == 'always' or (color == 'auto' and sys.stdout.isatty() and 'NO_COLOR' not in os.environ)
        self._framed = False  # when True, row/keyvalue/section render inside a box

    def text(self, zh, en):
        return zh if self.lang == 'zh' else en

    # ---- basic paint ----
    def paint(self, value, status='ok', preserve_space=False):
        value = _UNSAFE.sub(' ', str(value)) if preserve_space else clean(value)
        if not self.enabled:
            return value
        code = {'ok': '32', 'bad': '31', 'unknown': '33', 'title': '36', 'muted': '90', 'warn': '33'}[status]
        return f'\033[{code}m{value}\033[0m'

    def row(self, label, value, status='ok'):
        # Hide empty observations only, never a measured failure or a limitation.
        if self.hide_unavailable and status == 'unknown' and clean(value).casefold() in {
            'unknown', 'unavailable', 'not available', 'skipped', 'skipped offline',
            '未知', '无法判断', '不可用', '未获取', '已跳过', '离线跳过',
        }:
            return
        if self._framed:
            self.frame_keyvalue(label, value, status)
            return
        label = clean(label)
        w = width(label)
        print(label + ' ' * max(1, 19 - w) + self.paint(value, status), flush=True)

    def line(self, value='', status='ok'):
        if self._framed:
            self.frame_line(value, status)
        else:
            print(self.paint(value, status, preserve_space=True), flush=True)

    def section(self, index, zh, en):
        if self._framed:
            self.frame_section(index, zh, en)
            return
        print('\n' + self.paint(f'===== {index}. {self.text(zh, en)} =====', 'title'), flush=True)

    # ---- iprisk-themed primitives ----
    def block(self, value, kind='b_green', pad=None):
        """A solid colour badge like the iprisk report blocks."""
        value = clean(value)
        pad = (pad if pad is not None else 14) - width(value)
        if pad > 0:
            value = ' ' * (pad // 2) + value + ' ' * (pad - pad // 2)
        if not self.enabled:
            return value
        return f'\033[{_BG[kind]}m\033[30m{value}\033[0m'

    def chip(self, value, status='ok'):
        """A small coloured status chip (绿/黄/红)."""
        value = clean(value)
        if not self.enabled:
            return f'[{value}]'
        return f'\033[{_CODES[status]}m[{value}]\033[0m'

    def banner(self, text):
        """A large ASCII-art title line, e.g. VPSMASTER."""
        text = clean(text)
        if not self.enabled:
            print(text, flush=True)
            return
        print('\033[1;36m' + text + _RESET, flush=True)

    def hrule(self, ch='=', n=64, status='muted'):
        print(self.paint(ch * n, status), flush=True)

    # ---- the theme's section header: 「一、基础信息」 with a colour block ----
    CN_NUM = ('一', '二', '三', '四', '五', '六', '七', '八', '九', '十',
              '十一', '十二', '十三', '十四', '十五', '十六')

    def theme_section(self, number, zh, en, kind='b_cyan'):
        num = self.CN_NUM[number - 1] if 1 <= number <= len(self.CN_NUM) else str(number)
        if self.lang == 'zh':
            title = f'{num}、{zh}'
        else:
            title = f'{number}. {en}'
        print()
        print(self.block(title, kind, pad=width(title) + 2), flush=True)

    def keyvalue(self, label, value, status='ok'):
        """Aligned `label：value` line used by the theme."""
        label = clean(label)
        sep = '：' if self.lang == 'zh' else ': '
        print('  ' + self.paint(label, 'title') + sep + self.paint(value, status), flush=True)

    def panel(self, title, rows, width=76):
        """A compact overview; wrap by terminal columns, including CJK text."""
        if not 40 <= width <= 120:
            raise ValueError('Panel width must be 40..120')
        if sys.stdout.isatty():
            width = min(width, max(12, shutil.get_terminal_size().columns))
        if self._framed:
            self.frame_line(title, 'title')
            for label, value, status in rows:
                self.frame_keyvalue(label, value, status)
            return

        def pieces(value, limit):
            chunk = ''; used = 0
            for ch in clean(value):
                size = _cwidth(ch)
                if used + size > limit and chunk:
                    yield chunk; chunk = ''; used = 0
                chunk += ch; used += size
            yield chunk

        def line(value, status):
            value = clean(value)
            vw = sum(_cwidth(ch) for ch in value)
            print(self.paint('|', 'title') + ' ' + self.paint(value, status) + ' ' * (width - 4 - vw) + ' ' + self.paint('|', 'title'), flush=True)

        print(self.paint('+' + '-' * (width - 2) + '+', 'title'), flush=True)
        for value in pieces(title, width - 4):
            line(value, 'title')
        print(self.paint('+' + '-' * (width - 2) + '+', 'title'), flush=True)
        for label, value, status in rows:
            text = clean(label) + ': ' + clean(value)
            for piece in pieces(text, width - 4):
                line(piece, status)
        print(self.paint('+' + '-' * (width - 2) + '+', 'title'), flush=True)

    # ---- framed theme: the whole report inside one double-line box ----
    # Box glyphs: ╔ ═ ╗ ║ ╚ ╝ ╠ ╣
    # NOTE: the module-level `width()` helper is shadowed by parameter names in
    # some methods, so we keep a local alias `_cw` to the width function.
    _cw = staticmethod(width)

    def _box(self, left, fill, right, n, status='title'):
        """One horizontal box edge, e.g. ╔═══╗ of width n+2."""
        return self.paint(left + fill * n + right, status)

    def frame_open(self, title, box_w=76, subtitle=None):
        """Top edge + centered title + optional subtitle, all inside the box."""
        if not 40 <= box_w <= 118:
            raise ValueError('Frame inner width must be 40..118')
        if sys.stdout.isatty():
            box_w = min(box_w, max(10, shutil.get_terminal_size().columns - 2))
        cw = self._cw
        self._box_w = box_w
        self._framed = True
        print(self._box('╔', '═', '╗', box_w), flush=True)
        for text, status in ((title, 'title'), (subtitle, 'muted')):
            if text is None:
                continue
            for piece in wrap_columns(text, box_w):
                left = (box_w - cw(piece)) // 2
                right = box_w - cw(piece) - left
                print(self.paint('║', 'title') + ' ' * left + self.paint(piece, status, preserve_space=True) + ' ' * right + self.paint('║', 'title'), flush=True)
        print(self._box('╠', '═', '╣', box_w), flush=True)

    def frame_line(self, text, status='ok', pad=1):
        """A plain line inside the box (left border + text + right border)."""
        cw = self._cw
        if not 0 <= pad <= (self._box_w - 2) // 2:
            raise ValueError('Invalid frame padding')
        for piece in wrap_columns(text, self._box_w - 2 * pad):
            print(self.paint('║', 'title') + ' ' * pad + self.paint(piece, status, preserve_space=True) +
                  ' ' * (self._box_w - pad - cw(piece)) + self.paint('║', 'title'), flush=True)

    def frame_keyvalue(self, label, value, status='ok'):
        """Aligned `label：value` line inside the box."""
        sep = '：' if self.lang == 'zh' else ': '
        self.frame_line(clean(label) + sep + clean(value), status, pad=2)

    def frame_section(self, number, zh, en):
        """A yellow section heading inside the box, e.g. 一、基础信息."""
        num = self.CN_NUM[number - 1] if 1 <= number <= len(self.CN_NUM) else str(number)
        title = f'{num}、{zh}' if self.lang == 'zh' else f'{number}. {en}'
        self.frame_line(title, 'warn', pad=2)

    def frame_close(self):
        """Bottom edge of the box."""
        print(self._box('╚', '═', '╝', self._box_w), flush=True)
        self._framed = False
