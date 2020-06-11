'''ResNet in PyTorch.

For Pre-activation ResNet, see 'preact_resnet.py'.

Reference:
[1] Kaiming He, Xiangyu Zhang, Shaoqing Ren, Jian Sun
    Deep Residual Learning for Image Recognition. arXiv:1512.03385
'''

import torch
import torch.nn as nn
import numpy as np
from collections import defaultdict


def conv3x3(in_planes, out_planes, stride=1):
    """3x3 convolution with padding"""
    return nn.Conv2d(in_planes, out_planes, kernel_size=3, stride=stride,
                     padding=1, bias=False)


def conv1x1(in_planes, out_planes, stride=1):
    """1x1 convolution"""
    return nn.Conv2d(in_planes, out_planes, kernel_size=1, stride=stride, bias=False)


class FixupBasicBlock(nn.Module):
    expansion = 1

    def __init__(self, inplanes, planes, stride=1, downsample=None):
        super(FixupBasicBlock, self).__init__()
        # Both self.conv1 and self.downsample layers downsample the input when stride != 1
        self.bias1a = nn.Linear(1, 1, bias=False) #nn.Parameter(torch.zeros(1))
        self.conv1 = conv3x3(inplanes, planes, stride)
        self.bias1b = nn.Linear(1, 1, bias=False) #nn.Parameter(torch.zeros(1))
        self.relu = nn.LeakyReLU(inplace=True)
        self.bias2a = nn.Linear(1, 1, bias=False) #nn.Parameter(torch.zeros(1))
        self.conv2 = conv3x3(planes, planes)
        self.scale = nn.Linear(1, 1, bias=False) #nn.Parameter(torch.ones(1))
        self.bias2b = nn.Linear(1, 1, bias=False) #nn.Parameter(torch.zeros(1))
        self.downsample = downsample
        self.stride = stride

    def forward(self, x):
        identity = x

        out = self.conv1(x + self.bias1a.weight)
        out = self.relu(out + self.bias1b.weight)

        out = self.conv2(out + self.bias2a.weight)
        out = out * self.scale.weight + self.bias2b.weight
        if self.downsample is not None:
            identity = self.downsample(x + self.bias1a.weight)

        out += identity
        out = self.relu(out)
        return out


class FixupResNet(nn.Module):
    def __init__(self, block, layers, num_classes=10):
        super(FixupResNet, self).__init__()
        self.num_layers = sum(layers)
        self.inplanes = 64
        self.conv1 = nn.Conv2d(3, 64, kernel_size=3, stride=1, padding=1, bias=False)
        self.bias1 = nn.Linear(1, 1, bias=False)  # nn.Parameter(torch.zeros(1))
        self.relu = nn.LeakyReLU(inplace=True)
        self.layer1 = self._make_layer(block, 64, layers[0])
        self.layer2 = self._make_layer(block, 128, layers[1], stride=2)
        self.layer3 = self._make_layer(block, 256, layers[2], stride=2)
        self.layer4 = self._make_layer(block, 512, layers[3], stride=2)
        self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
        self.bias2 = nn.Linear(1, 1, bias=False)  # nn.Parameter(torch.zeros(1))
        self.fc = nn.Linear(512 * block.expansion, num_classes)

        self.stats = defaultdict(list)

        for name, m in self.named_modules():
            if isinstance(m, FixupBasicBlock):
                bound = np.sqrt(2 / (m.conv1.weight.shape[0] * np.prod(m.conv1.weight.shape[2:]))) * self.num_layers ** (-0.5)
                nn.init.normal_(m.conv1.weight, mean=0, std=bound)
                nn.init.constant_(m.conv2.weight, 0)
                if m.downsample is not None:
                    bound = np.sqrt(2 / (m.downsample.weight.shape[0] * np.prod(m.downsample.weight.shape[2:])))
                    nn.init.normal_(m.downsample.weight, mean=0, std=bound)

            # Here biases, scales and linear layers are initialized
            elif isinstance(m, nn.Linear):
                nn.init.constant_(m.weight, 0)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)
                if 'scale' in name:
                    nn.init.constant_(m.weight, 1)

    def _make_layer(self, block, planes, blocks, stride=1):
        downsample = None
        if stride != 1 or self.inplanes != planes * block.expansion:
            downsample = conv1x1(self.inplanes, planes * block.expansion, stride)

        layers = [block(self.inplanes, planes, stride, downsample)]
        self.inplanes = planes * block.expansion
        for _ in range(1, blocks):
            layers.append(block(self.inplanes, planes))

        return nn.Sequential(*layers)

    def forward(self, x):
        x = self.conv1(x)
        x = self.relu(x + self.bias1.weight)

        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)

        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x + self.bias2.weight)
        return x


def FixupResNet18(**kwargs):
    """Constructs a Fixup-ResNet-18 model.
    """
    model = FixupResNet(FixupBasicBlock, [2, 2, 2, 2], **kwargs)
    return model


def FixupResNet34(**kwargs):
    """Constructs a Fixup-ResNet-34 model.
    """
    model = FixupResNet(FixupBasicBlock, [3, 4, 6, 3], **kwargs)
    return model


def FixupResNet50(**kwargs):
    """Constructs a Fixup-ResNet-50 model.
    """
    model = FixupResNet(FixupBottleneck, [3, 4, 6, 3], **kwargs)
    return model


def FixupResNet101(**kwargs):
    """Constructs a Fixup-ResNet-101 model.
    """
    model = FixupResNet(FixupBottleneck, [3, 4, 23, 3], **kwargs)
    return model


def FixupResNet152(**kwargs):
    """Constructs a Fixup-ResNet-152 model.
    """
    model = FixupResNet(FixupBottleneck, [3, 8, 36, 3], **kwargs)
    return model


def test():
    net = FixupResNet()
    y = net(torch.randn(1,3,32,32))
    print(y.size())

# test()