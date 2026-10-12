from pathlib import Path

from scripts import prepare_models


def test_prepare_models_pins_project_cache_main_ref(tmp_path, monkeypatch):
    cache = tmp_path / 'hub'
    monkeypatch.setattr(prepare_models, 'CACHE', cache)

    def fake_download(*, repo_id, revision, cache_dir):
        assert cache_dir == cache
        model_dir = cache / ('models--' + repo_id.replace('/', '--')) / 'snapshots' / revision
        model_dir.mkdir(parents=True)
        return str(model_dir)

    monkeypatch.setattr(prepare_models, 'snapshot_download', fake_download)
    prepare_models.main()
    main_ref = cache / 'models--BAAI--bge-m3/refs/main'
    assert main_ref.read_text() == prepare_models.MODELS['BAAI/bge-m3']
