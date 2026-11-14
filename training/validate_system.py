# Created at: 2026-11-14 05:27 EST
# Created by: Codex
# Last Modified at: 2026-11-14 05:27 EST
# Last Modified by: Codex
# Verifies the pinned Volta runtime and real CPU/GPU model numerical alignment.

from __future__ import annotations

import argparse
import json
import platform

import torch

from training.config import load_config
from training.model import RecurrentActorCritic


def validate_system(config_path: str, expected_visible_gpus: int) -> dict[str, object]:
    config = load_config(config_path)
    runtime = config["runtime"]
    if platform.python_version()[:4] != runtime["python"]:
        raise RuntimeError("Python version does not match V100 runtime contract")
    if torch.__version__.split("+")[0] != runtime["torch"]:
        raise RuntimeError("PyTorch version does not match V100 runtime contract")
    if torch.version.cuda != runtime["cuda"]:
        raise RuntimeError("PyTorch CUDA version does not match V100 runtime contract")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is unavailable")
    if torch.cuda.device_count() != expected_visible_gpus:
        raise RuntimeError("visible CUDA device count does not match qualification request")

    devices: list[dict[str, object]] = []
    for index in range(torch.cuda.device_count()):
        properties = torch.cuda.get_device_properties(index)
        if "V100" not in properties.name or (properties.major, properties.minor) != (7, 0):
            raise RuntimeError(f"visible CUDA device {index} is not a Volta V100")
        if properties.total_memory < 15 * 1024**3:
            raise RuntimeError(f"visible CUDA device {index} has less than 15GB memory")
        devices.append(
            {
                "index": index,
                "name": properties.name,
                "compute_capability": [properties.major, properties.minor],
                "total_memory": properties.total_memory,
            }
        )

    torch.manual_seed(20261113)
    cpu_model = RecurrentActorCritic().eval()
    gpu_model = RecurrentActorCritic().cuda().eval()
    gpu_model.load_state_dict(cpu_model.state_dict())
    generator = torch.Generator().manual_seed(20261113)
    spatial = torch.randint(0, 2, (2, 4, 13, 5, 5), generator=generator).float()
    scalar = torch.rand((2, 4, 46), generator=generator)
    starts = torch.zeros((2, 4), dtype=torch.bool)
    with torch.no_grad():
        cpu_output = cpu_model(spatial, scalar, episode_starts=starts)
        gpu_output = gpu_model(
            spatial.cuda(), scalar.cuda(), episode_starts=starts.cuda()
        )
    torch.cuda.synchronize()
    logit_error = float((cpu_output.logits - gpu_output.logits.cpu()).abs().max())
    value_error = float((cpu_output.values - gpu_output.values.cpu()).abs().max())
    if logit_error > 1e-4 or value_error > 1e-4:
        raise RuntimeError("CPU/GPU forward parity exceeded 1e-4")

    gpu_model.train()
    train_output = gpu_model(
        spatial.cuda(), scalar.cuda(), episode_starts=starts.cuda()
    )
    loss = train_output.logits.square().mean() + train_output.values.square().mean()
    loss.backward()
    if not torch.isfinite(loss):
        raise RuntimeError("real CUDA forward/backward produced a non-finite loss")
    torch.cuda.synchronize()
    return {
        "python": platform.python_version(),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "devices": devices,
        "parameter_count": sum(parameter.numel() for parameter in gpu_model.parameters()),
        "max_logit_error": logit_error,
        "max_value_error": value_error,
        "loss": float(loss.detach().cpu()),
        "max_memory_allocated": torch.cuda.max_memory_allocated(),
        "max_memory_reserved": torch.cuda.max_memory_reserved(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/rl/ppo_16gb.yaml")
    parser.add_argument("--expected-visible-gpus", type=int, default=1)
    arguments = parser.parse_args()
    report = validate_system(arguments.config, arguments.expected_visible_gpus)
    print("SYSTEM_VALIDATION_OK " + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
