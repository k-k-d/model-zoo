import matplotlib.animation as animation
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import torch.utils.data as data
import torchvision.datasets as dsets
import torchvision.transforms as transforms
import torchvision.utils as vutils
from IPython.display import HTML
from torch.optim import Adam
from torchgan.losses import (AuxiliaryClassifierDiscriminatorLoss,
                             AuxiliaryClassifierGeneratorLoss,
                             MinimaxDiscriminatorLoss, MinimaxGeneratorLoss)
from torchgan.models import ACGANDiscriminator, ACGANGenerator
from torchgan.trainer import Trainer

dataset = dsets.MNIST(root='./mnist',
                      train=True,
                      transform=transforms.Compose([
                          transforms.Resize((32, 32)),
                          transforms.ToTensor(),
                          transforms.Normalize(mean=(0.5, ), std=(0.5, ))
                      ]),
                      download=True)

dataloader = data.DataLoader(dataset,
                             batch_size=64,
                             shuffle=True,
                             num_workers=2)

real_batch = next(iter(dataloader))
plt.figure(figsize=(8, 8))
plt.axis("off")
plt.title("Training Images")
plt.imshow(
    np.transpose(
        vutils.make_grid(real_batch[0][:64], padding=2, normalize=True).cpu(),
        (1, 2, 0)))
plt.show()

acgan = {
    "generator": {
        "name": ACGANGenerator,
        "args": {
            "encoding_dims": 100,
            "num_classes": 10,
            "out_channels": 1,
            "step_channels": 32,
            "out_size": 32,
            "nonlinearity": nn.LeakyReLU(0.2),
            "last_nonlinearity": nn.Tanh()
        },
        "optimizer": {
            "name": Adam,
            "args": {
                "lr": 0.0009,
                "betas": (0.5, 0.999)
            }
        }
    },
    "discriminator": {
        "name": ACGANDiscriminator,
        "args": {
            "in_channels": 1,
            "step_channels": 32,
            "in_size": 32,
            "num_classes": 10,
            "nonlinearity": nn.LeakyReLU(0.2),
            "last_nonlinearity": nn.Sigmoid()
        },
        "optimizer": {
            "name": Adam,
            "args": {
                "lr": 0.0002,
                "betas": (0.5, 0.999)
            }
        }
    }
}

loss = [
    MinimaxDiscriminatorLoss(),
    MinimaxGeneratorLoss(),
    AuxiliaryClassifierGeneratorLoss(),
    AuxiliaryClassifierDiscriminatorLoss(),
]

if torch.cuda.is_available():
    device = torch.device("cuda:0")
    torch.backends.cudnn.deterministic = True
    epochs = 20
else:
    device = torch.device("cpu")
    epochs = 5

print("Device: {}".format(device))
print("Epochs: {}".format(epochs))

trainer = Trainer(acgan, loss, sample_size=64, epochs=epochs, device=device)

trainer(dataloader)

fig = plt.figure(figsize=(8, 8))
plt.axis("off")
ims = [[
    plt.imshow(plt.imread("{}/epoch{}_generator.png".format(trainer.recon, i)))
] for i in range(1, trainer.epochs + 1)]
ani = animation.ArtistAnimation(fig,
                                ims,
                                interval=1000,
                                repeat_delay=1000,
                                blit=True)
HTML(ani.to_jshtml())

gen = trainer.generator

dis = trainer.discriminator

for i in range(10):
    x = torch.randn([1, 100], device=device)
    for k in range(1000):
        xk = torch.randn([1, 100], device=device)
        a = 1 / dis(gen(x, torch.Tensor([i]).cuda()))
        b = 1 / dis(gen(xk, torch.Tensor([i]).cuda()))
        d = (a - 1) / (b - 1)
        p = torch.rand([1, 1], device=device)
        if (p < min(1, d)):
            x = xk
    image = gen(x, torch.Tensor([i]).cuda())
    plt.figure()
    plt.axis("off")
    plt.title(i)
    plt.imshow(np.transpose(vutils.make_grid(image.detach()).cpu(), (1, 2, 0)))
