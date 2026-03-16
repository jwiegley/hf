"""Performance benchmarks for hf model management utility."""

from hf import ModelConfig, ModelManager


def test_bench_model_config_creation(benchmark):
    """Benchmark ModelConfig dataclass creation."""
    benchmark(ModelConfig, name="test-model", context="4096", temp="0.7")


def test_bench_csv_lookup_hit(benchmark, tmp_path):
    """Benchmark CSV lookup with a matching key."""
    csv_file = tmp_path / "models.csv"
    csv_file.write_text("model1,draft1,4096,0.7,0.05,0.9,alias1,--extra\n")
    manager = ModelManager()
    benchmark(manager.lookup_csv, csv_file, "model1")


def test_bench_csv_lookup_miss(benchmark, tmp_path):
    """Benchmark CSV lookup with a non-matching key."""
    csv_file = tmp_path / "models.csv"
    csv_file.write_text("model1,draft1,4096,0.7,0.05,0.9,alias1,--extra\n")
    manager = ModelManager()
    benchmark(manager.lookup_csv, csv_file, "nonexistent")


def test_bench_list_all_models_empty(benchmark, tmp_path):
    """Benchmark list_all_models with empty directories."""
    manager = ModelManager()
    manager.mlx_models = tmp_path / "mlx"
    manager.gguf_models = tmp_path / "gguf"
    manager.mlx_models.mkdir()
    manager.gguf_models.mkdir()
    benchmark(manager.list_all_models)


def test_bench_get_gguf_empty(benchmark, tmp_path):
    """Benchmark get_gguf with no matching files."""
    model_dir = tmp_path / "test-model"
    model_dir.mkdir()
    manager = ModelManager()
    benchmark(manager.get_gguf, str(model_dir))
