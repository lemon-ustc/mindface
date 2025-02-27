import os
import sys
sys.path.append(os.getcwd())
sys.path.append(os.path.join(os.getcwd(),'mindface/recognition'))
import mindspore.numpy as np
import mindspore as ms
from mindspore.parallel import _cost_model_context as cost_model_context
from mindspore import context, Tensor

from mindface.recognition.models.iresnet import iresnet50, iresnet100

# iresnet
__all__ = ['iresnet50', 'iresnet100']
context.set_context(mode=context.PYNATIVE_MODE,
                    device_target='GPU', save_graphs=False)

def test_model():
    net = iresnet100()
    x = ms.Tensor(np.ones([4, 3, 112, 112]), ms.float32)
    print(x.shape)
    output = net(x)
    print(output.shape)
test_model()