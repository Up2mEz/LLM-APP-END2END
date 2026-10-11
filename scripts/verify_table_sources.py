"""Verify PDFs used for local table transcription without modifying originals."""
import json
from pathlib import Path
from ncd_gemma.config import ROOT
from ncd_gemma.retrieval import file_hash

manifest = json.loads((ROOT / 'private/table_context_manifest.json').read_text(encoding='utf-8'))
changed = [Path(r['path']).parent.name for r in manifest['source_pdfs'] if file_hash(Path(r['path'])) != r['sha256']]
report = {'source_pdfs_checked':len(manifest['source_pdfs']), 'changed':changed,
          'candidate_pages':manifest['candidate_pages'], 'tables':manifest['tables'],
          'table_context_sha256':file_hash(ROOT / 'data/table_context/tables.jsonl'),
          'matches_build':file_hash(ROOT / 'data/table_context/tables.jsonl') == manifest['sha256'],
          'scope':'Only source PDFs used by this table builder; not a whole-repository clean-tree claim'}
(ROOT / 'reports/table_context_integrity.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
if changed or not report['matches_build']:raise SystemExit(1)
