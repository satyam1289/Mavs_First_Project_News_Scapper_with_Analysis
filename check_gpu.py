import torch
import sys

print("Python Executable:", sys.executable)
print("PyTorch Version:", torch.__version__)
print("CUDA Available:", torch.cuda.is_available())

if torch.cuda.is_available():
    print("Device Name:", torch.cuda.get_device_name(0))
    print("CUDA Version:", torch.version.cuda)
else:
    print("\n❌ GPU NOT DETECTED")
    print("Possible reasons:")
    print("1. NVIDIA Drivers are outdated (Update via GeForce Experience).")
    print("2. You installed the CPU version of PyTorch by mistake.")
    print("3. System needs a restart after driver update.") 
