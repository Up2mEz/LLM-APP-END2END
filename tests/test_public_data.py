import hashlib
import json
import shutil

import pytest

from scripts import public_data


def test_release_bundle_round_trip_and_existing_data_guard(tmp_path, monkeypatch):
    root = tmp_path / 'project'
    root.mkdir()
    monkeypatch.setattr(public_data, 'ROOT', root)
    monkeypatch.setattr(public_data, 'DATA', root / 'data')
    monkeypatch.setattr(public_data, 'PROVENANCE', root / 'provenance/source_snapshot.json')
    monkeypatch.setattr(public_data, 'MANIFEST', root / 'provenance/public_data_release.json')
    monkeypatch.setattr(public_data, 'ARCHIVE', root / 'output/public_data/ncd-data-v12.zip')
    monkeypatch.setattr(public_data, 'ASSET_URL', public_data.ARCHIVE.as_uri())
    records = []
    for category in sorted(public_data.CATEGORIES):
        path = root / 'data' / category / 'sample.txt'
        path.parent.mkdir(parents=True)
        content = f'{category}\n'.encode()
        path.write_bytes(content)
        records.append({'destination': path.relative_to(root).as_posix(),
                        'sha256': hashlib.sha256(content).hexdigest()})
    public_data.PROVENANCE.parent.mkdir()
    public_data.PROVENANCE.write_text(json.dumps({'files': records}), encoding='utf-8')
    result = public_data.package()
    assert result['files'] == 5
    assert public_data.fetch()['status'] == 'already_present'
    canonical_json = public_data.PROVENANCE.read_text(encoding='utf-8')
    public_data.PROVENANCE.write_bytes(canonical_json.replace('\n', '\r\n').encode('utf-8'))
    assert public_data.fetch()['status'] == 'already_present'
    shutil.rmtree(root / 'data')
    assert public_data.fetch() == {'status': 'downloaded', 'files': 5}
    assert (root / 'data/index/sample.txt').read_text() == 'index\n'
    (root / 'data/index/sample.txt').write_text('changed')
    with pytest.raises(ValueError, match='Existing data differs'):
        public_data.fetch()
