
import hashlib
import os
from pathlib import Path

os.environ.setdefault("MLFLOW_DISABLE_AGENT_HINT", "1")

import mlflow
import mlflow.sklearn

EXPERIMENT = "maintai"
TRUSTED_TYPES = ["sklearn.tree._tree.Tree"]


def file_md5(path: Path) -> str:
    """Calculate the MD5 hash of the data file."""
    h = hashlib.md5()

    with open(path, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)

    return h.hexdigest()


def log_run(params: dict, metrics: dict, model, X_example, data_path: Path) -> str:
    """Log training parameters, data version, metrics and model in MLflow."""

    # 1. Select experiment
    mlflow.set_experiment(EXPERIMENT)

    # 2. Start a new run
    with mlflow.start_run() as run:

        # 3. Log parameters
        mlflow.log_params(params)

        # 4. Log dataset version
        data_md5 = file_md5(data_path)
        mlflow.log_param("data_md5", data_md5)

        # 5. Log metrics
        mlflow.log_metrics(metrics)

        # 6. Log trained model
        mlflow.sklearn.log_model(
            model,
            name="model",
            input_example=X_example,
            skops_trusted_types=TRUSTED_TYPES
        )

        # 7. Return run ID
        return run.info.run_id
