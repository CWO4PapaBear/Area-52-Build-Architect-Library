from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from catalog import page,overview,render
from library import make_record,store,decode
from test_library import sample


class CatalogTests(unittest.TestCase):
    def test_code_and_untrusted_text(self):
        build=sample();build['Name']='[fake](https://example.com)';build['Description']='```\n<img src="x">\n```'
        record=make_record(build,'<script>','v1')
        result=page(record)
        self.assertNotIn('# [fake](',result)
        self.assertIn('&lt;script&gt;',result)
        self.assertIn('````text\n',result)
        code=next(line for line in result.splitlines() if line.startswith('A52B1:'))
        self.assertEqual(decode(code),record['build'])

    def test_latest_overview_and_preserved_revisions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'repo';output=Path(tmp)/'rendered'
            first=make_record(sample(),'alias','v1');second=make_record(dict(sample(),Name='Updated'),'alias','v1',first['id'],2)
            store(root,first);store(root,second);render(root,output)
            text=(output/'CATALOG.md').read_text(encoding='utf-8')
            self.assertIn('Updated',text);self.assertNotIn('Frost healer',text)
            self.assertTrue((output/'catalog'/first['id']/'1.md').exists())
            self.assertTrue((output/'catalog'/first['id']/'2.md').exists())


if __name__=='__main__':unittest.main()
