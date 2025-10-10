from transformers import AutoTokenizer, AutoModel
from optimum.exporters.onnx import OnnxConfig, OnnxConverter
from optimum.exporters.tasks import TasksManager
from pathlib import Path

model_id = "sentence-transformers/all-MiniLM-L6-v2"
output_dir = Path("onnx")
output_dir.mkdir(parents=True, exist_ok=True)

# Load tokenizer and model
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModel.from_pretrained(model_id)

# Prepare config for ONNX export
task = "feature-extraction"
exporter = "onnx"

# Get ONNX config for model
onnx_config_constructor = TasksManager.get_exporter_config_constructor(
    exporter=exporter,
    model=model,
    task=task,
    library_name="transformers",  # explicit to suppress warning
)
onnx_config = onnx_config_constructor(model.config)

# Set up the ONNX exporter
onnx_converter = OnnxConverter(
    model=model,
    task=task,
    onnx_config=onnx_config,
    tokenizer=tokenizer,
    feature="default",  # used for feature-extraction tasks
)

# Run export
onnx_converter.export(output_dir=output_dir, show_progress_bar=False)
