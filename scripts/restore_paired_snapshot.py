"""Restore verified historical source bytes in a fresh reproduction checkout."""
import json
from paired_agent_eval import ROOT,OUT,PRIVATE,old_files,verify

def main():
    manifest=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
    snap=PRIVATE/'old';snap.mkdir(parents=True,exist_ok=True)
    for name,content in old_files().items():
        p=snap/name
        if p.exists() and p.read_bytes()!=content:raise ValueError('Refuse replacing changed historical file: '+name)
        if not p.exists():p.write_bytes(content)
    verify(manifest)
    print('PASS historical source restored and paired manifest verified')

if __name__=='__main__':main()
