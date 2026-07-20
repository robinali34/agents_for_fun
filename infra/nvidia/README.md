# NVIDIA GPU 唤醒（Optimus 笔记本）

部分 MSI / Optimus 笔记本上，GPU 会停在 D3cold，导致 `nvidia-smi` / Ollama GPU 失败。  
可用本单元在开机时尝试唤醒。

## 安装

```bash
# 在 agents_for_fun 仓库根目录
sudo cp infra/nvidia/nvidia-gpu-wake.service /etc/systemd/system/
```

按需编辑 PCI 地址（默认示例为 `0000:01:00.0`）：

```bash
lspci | grep -i nvidia
sudo systemctl edit --full nvidia-gpu-wake.service   # 或直接改 unit 文件
sudo systemctl daemon-reload
sudo systemctl enable --now nvidia-gpu-wake.service
```

## 验证

```bash
nvidia-smi -L
systemctl status nvidia-gpu-wake.service
```

Dify / Ollama 启动前，`infra/dify/deploy.sh` 也会尝试唤醒 GPU。
