"""
@FileName：   version_test.py
@Description：描述
@Author：     NGC2237
@Version:     1.0
@Time：       2025/3/9
@Software：   PyCharm
"""
import torch

print(torch.__version__)
print("是否可用：", torch.cuda.is_available())  # 查看GPU是否可用
print("GPU数量：", torch.cuda.device_count())  # 查看GPU数量
print("torch方法查看CUDA版本：", torch.version.cuda)  # torch方法查看CUDA版本
print("GPU索引号：", torch.cuda.current_device())  # 查看GPU索引号
print("GPU名称：", torch.cuda.get_device_name(0))  # 根据索引号得到GPU名称
print(f"cuDNN version: {torch.backends.cudnn.version()}")

