"""
meridian.journal
Creative writing and journal management for autonomous agents.
Track poems, journals, and push to website.
"""

import os
import re
import glob
import subprocess
from datetime import datetime
from typing import Optional, List, Tuple


BASE_DIR = '/home/joel/autonomous-ai'
WEBSITE_DIR = f'{BASE_DIR}/website'


class JournalManager:
    """
    Manage journals, poems, and website content.

    Example:
        jm = JournalManager('/home/joel/autonomous-ai')
        count = jm.poem_count()
        next_num = jm.next_poem_number()
        jm.write_poem('My Title', 'poem content here')
    """

    def __init__(self, base_dir: str = BASE_DIR):
        self.base_dir    = base_dir
        self.website_dir = os.path.join(base_dir, 'website')

    def poem_count(self) -> int:
        return len(glob.glob(os.path.join(self.base_dir, 'poem-*.md')))

    def journal_count(self) -> int:
        return len(glob.glob(os.path.join(self.base_dir, 'journal-*.md')))

    def next_poem_number(self) -> int:
        return self.poem_count() + 1

    def next_journal_number(self) -> int:
        return self.journal_count() + 1

    def write_poem(self, title: str, content: str,
                   loop_num: Optional[int] = None) -> str:
        """Write a poem file. Returns the file path."""
        n = self.next_poem_number()
        filename = f'poem-{n:03d}.md'
        path = os.path.join(self.base_dir, filename)
        header = f'# Poem {n:03d}: {title}\n\n'
        with open(path, 'w') as f:
            f.write(header + content)
        return path

    def write_journal(self, title: str, content: str,
                      loop_num: Optional[int] = None) -> str:
        """Write a journal entry. Returns the file path."""
        n = self.next_journal_number()
        filename = f'journal-{n:03d}.md'
        path = os.path.join(self.base_dir, filename)
        header = f'# Journal {n:03d}: {title}\n\n'
        with open(path, 'w') as f:
            f.write(header + content)
        return path

    def add_to_website(self, title: str, content: str,
                       entry_type: str, loop_num: int,
                       date_str: Optional[str] = None) -> bool:
        """
        Add a poem or journal to the website index.html.
        entry_type: 'poem' or 'journal'
        Returns True on success.
        """
        index_path = os.path.join(self.website_dir, 'index.html')
        if not os.path.exists(index_path):
            return False

        if date_str is None:
            date_str = datetime.now().strftime('%Y-%m-%d')

        try:
            with open(index_path) as f:
                html = f.read()

            # Update count in filter bar
            type_cap = entry_type.capitalize() + 's'
            count = self.poem_count() if entry_type == 'poem' else self.journal_count()
            html = re.sub(
                rf'({type_cap}: )\d+',
                rf'\g<1>{count}',
                html
            )

            # Create new article block
            content_escaped = content.replace('</pre>', '<\\/pre>')
            new_article = f'''      <article>
        <div class="entry-meta">{type_cap[:-1]} — {date_str} — Loop #{loop_num}</div>
        <h2>{title}</h2>
        <pre>\n{content}\n</pre>
      </article>\n\n'''

            # Insert before first <article>
            html = html.replace('<article>\n', new_article + '      <article>\n', 1)

            with open(index_path, 'w') as f:
                f.write(html)
            return True
        except Exception as e:
            print(f'Website update error: {e}')
            return False

    def get_recent_poems(self, n: int = 5) -> List[Tuple[str, str]]:
        """Return (filename, first_line) for the n most recent poems."""
        files = sorted(glob.glob(os.path.join(self.base_dir, 'poem-*.md')))[-n:]
        result = []
        for f in reversed(files):
            try:
                with open(f) as fp:
                    first_line = fp.readline().strip()
                result.append((os.path.basename(f), first_line))
            except:
                pass
        return result

    def read_entry(self, filename: str) -> Optional[str]:
        """Read a journal or poem file."""
        path = os.path.join(self.base_dir, filename)
        try:
            with open(path) as f:
                return f.read()
        except:
            return None
