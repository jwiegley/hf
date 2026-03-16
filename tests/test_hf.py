"""Tests for hf model management utility."""

from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from hf import ModelConfig, ModelManager


class TestModelConfig:
    """Tests for ModelConfig dataclass."""

    def test_defaults(self):
        config = ModelConfig(name="test-model")
        assert config.name == "test-model"
        assert config.draft == ""
        assert config.context == ""
        assert config.temp == ""
        assert config.minp == ""
        assert config.topp == ""
        assert config.aliases == ""
        assert config.args == ""

    def test_full_config(self):
        config = ModelConfig(
            name="model",
            draft="draft-model",
            context="4096",
            temp="0.7",
            minp="0.05",
            topp="0.9",
            aliases="alias1",
            args="--extra",
        )
        assert config.name == "model"
        assert config.draft == "draft-model"
        assert config.context == "4096"
        assert config.temp == "0.7"
        assert config.args == "--extra"


class TestLookupCsv:
    """Tests for CSV lookup functionality."""

    def test_lookup_existing_key(self, tmp_path):
        csv_file = tmp_path / "models.csv"
        csv_file.write_text("model1,draft1,4096,0.7,0.05,0.9,alias1,--extra\n")

        manager = ModelManager()
        result = manager.lookup_csv(csv_file, "model1")

        assert result is not None
        assert result.name == "model1"
        assert result.draft == "draft1"
        assert result.context == "4096"

    def test_lookup_missing_key(self, tmp_path):
        csv_file = tmp_path / "models.csv"
        csv_file.write_text("model1,draft1,4096\n")

        manager = ModelManager()
        result = manager.lookup_csv(csv_file, "nonexistent")

        assert result is None

    def test_lookup_missing_file(self, tmp_path):
        manager = ModelManager()
        result = manager.lookup_csv(tmp_path / "nonexistent.csv", "key")

        assert result is None

    def test_lookup_partial_row(self, tmp_path):
        csv_file = tmp_path / "models.csv"
        csv_file.write_text("model1,draft1\n")

        manager = ModelManager()
        result = manager.lookup_csv(csv_file, "model1")

        assert result is not None
        assert result.name == "model1"
        assert result.draft == "draft1"
        assert result.context == ""

    def test_lookup_custom_key_column(self, tmp_path):
        csv_file = tmp_path / "models.csv"
        csv_file.write_text("model1,draft1,4096\n")

        manager = ModelManager()
        result = manager.lookup_csv(csv_file, "draft1", key_column=1)

        assert result is not None
        assert result.name == "model1"


class TestGetGguf:
    """Tests for GGUF file selection priority."""

    @staticmethod
    def _create_gguf(path: Path, size_mb: int = 200):
        """Create a fake GGUF file of the given size."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.seek(size_mb * 1024 * 1024 - 1)
            f.write(b"\0")

    def test_prefers_higher_quality(self, tmp_path):
        model_dir = tmp_path / "test-model"
        self._create_gguf(model_dir / "model-Q4_K_M.gguf")
        self._create_gguf(model_dir / "model-Q8_0.gguf")

        manager = ModelManager()
        result = manager.get_gguf(str(model_dir))

        assert result is not None
        assert "Q8" in result.name

    def test_quality_ordering(self, tmp_path):
        model_dir = tmp_path / "test-model"
        self._create_gguf(model_dir / "model-Q4_K_M.gguf")
        self._create_gguf(model_dir / "model-F16_0.gguf")

        manager = ModelManager()
        result = manager.get_gguf(str(model_dir))

        assert result is not None
        assert "F16" in result.name

    def test_skips_small_files(self, tmp_path):
        model_dir = tmp_path / "test-model"
        small = model_dir / "model-Q8_0.gguf"
        small.parent.mkdir(parents=True, exist_ok=True)
        small.write_bytes(b"small")

        manager = ModelManager()
        result = manager.get_gguf(str(model_dir))

        assert result is None

    def test_no_gguf_files(self, tmp_path):
        model_dir = tmp_path / "test-model"
        model_dir.mkdir()

        manager = ModelManager()
        result = manager.get_gguf(str(model_dir))

        assert result is None


class TestFindModel:
    """Tests for find_model pattern matching."""

    @staticmethod
    def _create_gguf(path: Path, size_mb: int = 200):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "wb") as f:
            f.seek(size_mb * 1024 * 1024 - 1)
            f.write(b"\0")

    def test_finds_matching_pattern(self, tmp_path):
        self._create_gguf(tmp_path / "model-Q8_0.gguf")

        manager = ModelManager()
        result = manager.find_model(tmp_path, r"[Qq]8_")

        assert result is not None
        assert "Q8" in result.name

    def test_returns_none_for_no_match(self, tmp_path):
        self._create_gguf(tmp_path / "model-Q4_K.gguf")

        manager = ModelManager()
        result = manager.find_model(tmp_path, r"[Qq]8_")

        assert result is None


class TestListAllModels:
    """Tests for model listing."""

    def test_empty_directories(self, tmp_path):
        manager = ModelManager()
        manager.mlx_models = tmp_path / "mlx"
        manager.gguf_models = tmp_path / "gguf"
        manager.mlx_models.mkdir()
        manager.gguf_models.mkdir()

        result = manager.list_all_models()
        assert result == []

    def test_lists_gguf_models(self, tmp_path):
        manager = ModelManager()
        manager.mlx_models = tmp_path / "mlx"
        manager.gguf_models = tmp_path / "gguf"
        manager.mlx_models.mkdir()
        manager.gguf_models.mkdir()

        (manager.gguf_models / "org_model-GGUF").mkdir()

        result = manager.list_all_models()
        assert "org_model-GGUF" in result

    def test_transforms_mlx_names(self, tmp_path):
        manager = ModelManager()
        manager.mlx_models = tmp_path / "mlx"
        manager.gguf_models = tmp_path / "gguf"
        manager.mlx_models.mkdir()
        manager.gguf_models.mkdir()

        (manager.mlx_models / "models--org--model-name").mkdir()

        result = manager.list_all_models()
        assert "org_model-name" in result

    def test_skips_locks_directory(self, tmp_path):
        manager = ModelManager()
        manager.mlx_models = tmp_path / "mlx"
        manager.gguf_models = tmp_path / "gguf"
        manager.mlx_models.mkdir()
        manager.gguf_models.mkdir()

        (manager.mlx_models / ".locks").mkdir()

        result = manager.list_all_models()
        assert result == []

    def test_results_are_sorted(self, tmp_path):
        manager = ModelManager()
        manager.mlx_models = tmp_path / "mlx"
        manager.gguf_models = tmp_path / "gguf"
        manager.mlx_models.mkdir()
        manager.gguf_models.mkdir()

        (manager.gguf_models / "zebra-model").mkdir()
        (manager.gguf_models / "alpha-model").mkdir()

        result = manager.list_all_models()
        assert result == sorted(result)


class TestFuzz:
    """Fuzz tests using Hypothesis."""

    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(
        name=st.text(min_size=1, max_size=100),
        draft=st.text(max_size=50),
        context=st.text(max_size=20),
    )
    def test_model_config_roundtrip(self, name, draft, context):
        config = ModelConfig(name=name, draft=draft, context=context)
        assert config.name == name
        assert config.draft == draft
        assert config.context == context

    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(search_key=st.text(min_size=1, max_size=100))
    def test_lookup_csv_missing_file_never_crashes(self, search_key):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            manager = ModelManager()
            result = manager.lookup_csv(Path(td) / "nonexistent.csv", search_key)
            assert result is None

    @settings(suppress_health_check=[HealthCheck.too_slow])
    @given(pattern=st.from_regex(r"[a-zA-Z0-9_]+", fullmatch=True))
    def test_find_model_empty_dir_never_crashes(self, pattern):
        import tempfile

        with tempfile.TemporaryDirectory() as td:
            manager = ModelManager()
            result = manager.find_model(Path(td), pattern)
            assert result is None
