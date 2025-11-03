"""
Qwen2-VL 圖片分析 - 精簡自動安裝版
自動檢測顯卡並安裝對應的 PyTorch
"""

import os
os.environ["TRANSFORMERS_NO_TF"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

import sys
import subprocess
import re
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# ==================== 工具函數 ====================
def run_pip(args, silent=True):
    """執行 pip 命令"""
    cmd = [sys.executable, "-m", "pip"] + args
    if silent:
        return subprocess.run(cmd, capture_output=True, text=True)
    return subprocess.run(cmd)

def get_gpu_info():
    """獲取 GPU 資訊（CUDA 版本和型號）"""
    try:
        result = subprocess.run(['nvidia-smi', '--query-gpu=name,driver_version',
                               '--format=csv,noheader'],
                              capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            gpu_name = result.stdout.strip().split(',')[0]

            # 獲取 CUDA 版本
            result2 = subprocess.run(['nvidia-smi'], capture_output=True, text=True)
            match = re.search(r'CUDA Version:\s+(\d+\.\d+)', result2.stdout)
            cuda_ver = match.group(1) if match else None

            return gpu_name, cuda_ver
    except:
        pass
    return None, None

def get_pytorch_index(cuda_version):
    """根據 CUDA 版本返回 PyTorch 下載源"""
    if not cuda_version:
        return None

    major = int(cuda_version.split('.')[0])
    minor = int(cuda_version.split('.')[1])

    if major == 11:
        return "https://download.pytorch.org/whl/cu118"
    elif major == 12 and minor <= 1:
        return "https://download.pytorch.org/whl/cu121"
    elif major >= 12:
        return "https://download.pytorch.org/whl/cu124"
    return None

# ==================== 初始化 ====================
print("="*70)
print("Qwen2-VL 圖片分析工具")
print("="*70)

# 檢測 GPU
gpu_name, cuda_version = get_gpu_info()

if gpu_name:
    print(f"✓ 檢測到 GPU: {gpu_name}")
    print(f"✓ CUDA 版本: {cuda_version}")
else:
    print("⚠ 未檢測到 NVIDIA GPU，將使用 CPU 模式")

# ==================== 檢查並安裝 PyTorch ====================
pytorch_needs_install = False

try:
    import torch

    # 檢查 CUDA 可用性
    if gpu_name and not torch.cuda.is_available():
        print(f"\n⚠ PyTorch 無法使用 CUDA，需要重新安裝")
        pytorch_needs_install = True
    else:
        print(f"✓ PyTorch {torch.__version__}")
        if torch.cuda.is_available():
            print(f"✓ CUDA 可用")

except (ImportError, OSError):
    print("⚠ PyTorch 未安裝或版本不匹配")
    pytorch_needs_install = True

if pytorch_needs_install:
    print("\n正在安裝 PyTorch...")
    run_pip(["uninstall", "torch", "torchvision", "torchaudio", "-y"])

    if gpu_name and cuda_version:
        index_url = get_pytorch_index(cuda_version)
        print(f"安裝 GPU 版本（這需要幾分鐘）...")
        result = run_pip(["install", "torch", "torchvision", "torchaudio",
                         "--index-url", index_url], silent=False)
    else:
        print(f"安裝 CPU 版本...")
        result = run_pip(["install", "torch", "torchvision", "torchaudio"],
                        silent=False)

    if result.returncode == 0:
        print("\n✓ PyTorch 安裝完成，請重新執行此程式")
        sys.exit(0)
    else:
        print("\n✗ 安裝失敗")
        sys.exit(1)

# ==================== 檢查依賴套件 ====================
required_packages = {
    'transformers': 'transformers>=4.43.0',
    'qwen_vl_utils': 'qwen-vl-utils',
    'accelerate': 'accelerate',
}

for module, package in required_packages.items():
    try:
        __import__(module)
        print(f"✓ {module}")
    except ImportError:
        print(f"⚠ 安裝 {module}...")
        run_pip(["install", package, "-q"])
        print(f"✓ {module} 安裝完成，請重新執行")
        sys.exit(0)

# 檢查 bitsandbytes（量化，可選）
try:
    import bitsandbytes
    HAS_BNB = True
    print("✓ bitsandbytes（量化支援）")
except ImportError:
    HAS_BNB = False
    if gpu_name:
        print("⚠ bitsandbytes 未安裝（可選，用於節省 VRAM）")

print()

# ==================== 自動配置 ====================
import torch

CUDA_AVAILABLE = torch.cuda.is_available()

if CUDA_AVAILABLE:
    GPU_MEMORY = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    print(f"GPU VRAM: {GPU_MEMORY:.1f} GB")

    # 根據 VRAM 選擇配置
    if GPU_MEMORY >= 12:
        MODEL_NAME = "Qwen/Qwen2-VL-7B-Instruct"
        USE_QUANT = HAS_BNB
        print(f"配置: 7B 模型 {'+ 4bit 量化' if USE_QUANT else ''}")
    elif GPU_MEMORY >= 6:
        MODEL_NAME = "Qwen/Qwen2-VL-2B-Instruct"
        USE_QUANT = False
        print(f"配置: 2B 模型")
    else:
        MODEL_NAME = "Qwen/Qwen2-VL-2B-Instruct"
        USE_QUANT = HAS_BNB
        print(f"配置: 2B 模型 {'+ 4bit 量化' if USE_QUANT else ''}")
else:
    MODEL_NAME = "Qwen/Qwen2-VL-2B-Instruct"
    USE_QUANT = False
    GPU_MEMORY = 0
    print("配置: CPU 模式 (2B 模型)")

DEVICE = "cuda" if CUDA_AVAILABLE else "cpu"

# ==================== 尋找圖片 ====================
IMAGE_PATH = 'hello.jpg'

if not IMAGE_PATH:
    for ext in ['.jpg', '.jpeg', '.png', '.bmp', '.webp']:
        images = list(Path('.').glob(f'*{ext}'))
        if images:
            IMAGE_PATH = str(images[0])
            break

if not IMAGE_PATH:
    print("\n✗ 找不到圖片檔案")
    print("請將圖片（.jpg/.png 等）放在程式目錄")
    sys.exit(1)

print(f"✓ 圖片: {IMAGE_PATH}\n")

# ==================== 載入模型 ====================
print("="*70)
print("載入模型（首次執行會自動下載，約 1-3 分鐘）")
print("="*70)

from transformers import Qwen2VLForConditionalGeneration, AutoProcessor
from qwen_vl_utils import process_vision_info
from PIL import Image

try:
    processor = AutoProcessor.from_pretrained(MODEL_NAME, trust_remote_code=True)

    if USE_QUANT:
        from transformers import BitsAndBytesConfig
        model = Qwen2VLForConditionalGeneration.from_pretrained(
            MODEL_NAME,
            torch_dtype=torch.float16,
            device_map="auto",
            quantization_config=BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            ),
            trust_remote_code=True
        )
    else:
        dtype = torch.float16 if CUDA_AVAILABLE else torch.float32
        model = Qwen2VLForConditionalGeneration.from_pretrained(
            MODEL_NAME,
            torch_dtype=dtype,
            device_map="auto" if CUDA_AVAILABLE else None,
            trust_remote_code=True
        )
        if not CUDA_AVAILABLE:
            model = model.to("cpu")

    model.eval()
    print("✓ 模型載入完成\n")

    if CUDA_AVAILABLE:
        mem_used = torch.cuda.memory_allocated() / (1024**3)
        print(f"VRAM 使用: {mem_used:.2f} GB\n")

except Exception as e:
    print(f"\n✗ 載入失敗: {e}")
    sys.exit(1)

# 載入圖片
try:
    image = Image.open(IMAGE_PATH)
    print(f"圖片尺寸: {image.width}x{image.height}\n")
except Exception as e:
    print(f"✗ 無法載入圖片: {e}")
    sys.exit(1)

# ==================== 問答函數 ====================
def ask(image_path, max_tokens=256, use_sampling=False):
    """輸入圖片路徑，生成分析結果"""

    # 檢查圖片是否存在
    if not Path(image_path).exists():
        return f"✗ 找不到圖片：{image_path}"

    # 嘗試開啟圖片
    try:
        image = Image.open(image_path)
    except Exception as e:
        return f"✗ 無法開啟圖片：{e}"

    prompt = """
請從這張圖片中挑出 7 到 10 個最具代表性的中或英文關鍵字。
若可能超過，請只保留最必要、最具代表性的部分。
關鍵字應聚焦於具體可見的內容，例如主要物體、背景、顏色、情緒、主題、構圖風格或文字重點。
用逗號分隔，只輸出關鍵字，不要解釋或補充句子。
"""

    messages = [{
        "role": "user",
        "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": prompt},
        ],
    }]

    text = processor.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    image_inputs, video_inputs = process_vision_info(messages)

    inputs = processor(
        text=[text],
        images=image_inputs,
        videos=video_inputs,
        padding=True,
        return_tensors="pt"
    )
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}

    gen_kwargs = {
        "max_new_tokens": max_tokens,
        "repetition_penalty": 1.15,
        "no_repeat_ngram_size": 2,
        "do_sample": use_sampling,
    }

    with torch.no_grad():
        generated_ids = model.generate(**inputs, **gen_kwargs)

    generated_ids_trimmed = [
        out[len(inp):] for inp, out in zip(inputs["input_ids"], generated_ids)
    ]

    return processor.batch_decode(
        generated_ids_trimmed,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False
    )[0]


# ==================== 互動模式 ====================
print("\n" + "="*70)
print("💬 互動模式（請輸入欲處理圖片的完整路徑，輸入 q 結束）")
print("="*70)

while True:
    try:
        user_input = input("\n請輸入圖片路徑（或 q 離開）: ").strip()
        if user_input.lower() in ['q', 'quit', 'exit', '退出']:
            print("👋 已結束。")
            break
        if not user_input:
            continue

        answer = ask(user_input)
        print(f"\nAI 關鍵字：{answer}\n")

    except KeyboardInterrupt:
        print("\n👋 已中斷。")
        break
    except Exception as e:
        print(f"錯誤: {e}")

# ==================== 完成 ====================
print("\n" + "="*70)
print("✓ 完成")
print("="*70)

if CUDA_AVAILABLE:
    mem_peak = torch.cuda.max_memory_allocated() / (1024**3)
    print(f"VRAM 峰值: {mem_peak:.2f} GB")