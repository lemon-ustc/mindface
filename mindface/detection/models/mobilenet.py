# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================

"""Network."""
from mindspore import nn
from mindspore.ops import operations as P

# MobileNet0.25
def conv_bn(inp, oup, stride=1, leaky=0):
    """conv_bn"""
    return nn.SequentialCell([
        nn.Conv2d(in_channels=inp, out_channels=oup, kernel_size=3, stride=stride,
                  pad_mode='pad', padding=1, has_bias=False),
        nn.BatchNorm2d(num_features=oup, momentum=0.9),
        nn.LeakyReLU(alpha=leaky)  # ms official: nn.get_activation('relu6')
        # nn.get_activation('relu6'),
    ])

def conv_dw(inp, oup, stride, leaky=0.1):
    """conv_dw"""
    return nn.SequentialCell([
        nn.Conv2d(in_channels=inp, out_channels=inp, kernel_size=3, stride=stride,
                  pad_mode='pad', padding=1, group=inp, has_bias=False),
        nn.BatchNorm2d(num_features=inp, momentum=0.9),
        nn.LeakyReLU(alpha=leaky),  # ms official: nn.get_activation('relu6')

        nn.Conv2d(in_channels=inp, out_channels=oup, kernel_size=1, stride=1,
                  pad_mode='pad', padding=0, has_bias=False),
        nn.BatchNorm2d(num_features=oup, momentum=0.9),
        nn.LeakyReLU(alpha=leaky),  # ms official: nn.get_activation('relu6')
        # nn.get_activation('relu6'),
    ])


class MobileNetV1(nn.Cell):
    """
    MobileNetV1 architecture, returns last 3 layers outputs

    Args:s
        classnum (int): num of classes.

    Examples:
        >>> mobilenet025 = MobileNetV1(1000)
    """
    def __init__(self, num_classes):
        super().__init__()
        self.stage1 = nn.SequentialCell([
            conv_bn(3, 8, 2, leaky=0.1),  # 3
            conv_dw(8, 16, 1),  # 7
            conv_dw(16, 32, 2),  # 11
            conv_dw(32, 32, 1),  # 19
            conv_dw(32, 64, 2),  # 27
            conv_dw(64, 64, 1),  # 43
        ])
        self.stage2 = nn.SequentialCell([
            conv_dw(64, 128, 2),  # 43 + 16 = 59
            conv_dw(128, 128, 1),  # 59 + 32 = 91
            conv_dw(128, 128, 1),  # 91 + 32 = 123
            conv_dw(128, 128, 1),  # 123 + 32 = 155
            conv_dw(128, 128, 1),  # 155 + 32 = 187
            conv_dw(128, 128, 1),  # 187 + 32 = 219
        ])
        self.stage3 = nn.SequentialCell([
            conv_dw(128, 256, 2),  # 219 +3 2 = 241
            conv_dw(256, 256, 1),  # 241 + 64 = 301
        ])
        self.avg = P.ReduceMean()
        self.fc = nn.Dense(in_channels=256, out_channels=num_classes)

    def construct(self, x):
        """construct"""
        x1 = self.stage1(x)
        x2 = self.stage2(x1)
        x3 = self.stage3(x2)
        out = self.avg(x3, (2, 3))
        out = self.fc(out)
        return x1, x2, x3


def mobilenet025(class_num=1000):
    """
    mobilenet025 model, returns last 3 layers outputs

    Args:
        classnum (int): num of classes

    Examples:
        >>> backbone = mobilenet025(1000)
    """
    return MobileNetV1(class_num)
