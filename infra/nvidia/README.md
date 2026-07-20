# NVIDIA GPU wake (Optimus laptops)

On some MSI / Optimus machines the dGPU stays in D3cold, so `nvidia-smi` and Ollama GPU fail.  
This oneshot unit tries to wake the GPU at boot.

## Install

From the `agents_for_fun` repo root:

```bash
sudo cp infra/nvidia/nvidia-gpu-wake.service /etc/systemd/system/
```

Edit the PCI address if needed (default example: `0000:01:00.0`):

```bash
lspci | grep -i nvidia
sudo systemctl edit --full nvidia-gpu-wake.service
sudo systemctl daemon-reload
sudo systemctl enable --now nvidia-gpu-wake.service
```

## Verify

```bash
nvidia-smi -L
systemctl status nvidia-gpu-wake.service
```

`infra/dify/deploy.sh` also attempts a GPU wake before starting Dify / Ollama.
