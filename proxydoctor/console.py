"""Compact terminal output with optional ANSI colour."""
import os
import re
import sys
import unicodedata


def clean(value):
    return re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', str(value)).strip()


class Console:
    def __init__(self, lang='zh', color='auto'):
        self.lang=lang
        self.enabled=color=='always' or (color=='auto' and sys.stdout.isatty() and 'NO_COLOR' not in os.environ)

    def text(self,zh,en): return zh if self.lang=='zh' else en

    def paint(self,value,status='ok',preserve_space=False):
        value=re.sub(r'[\x00-\x1f\x7f-\x9f]',' ',str(value)) if preserve_space else clean(value)
        if not self.enabled: return value
        code={'ok':'32','bad':'31','unknown':'33','title':'36'}[status]
        return f'\033[{code}m{value}\033[0m'

    def row(self,label,value,status='ok'):
        label=clean(label)
        width=sum(2 if unicodedata.east_asian_width(ch) in ('W','F') else 1 for ch in label)
        print(label+' '*max(1,19-width)+self.paint(value,status),flush=True)

    def section(self,index,zh,en):
        print('\n'+self.paint(f'===== {index}. {self.text(zh,en)} =====','title'),flush=True)
