from coco import COCO2014
from torch.utils.data import DataLoader
import torchvision.transforms as transforms
import torch.nn as nn
import torch
from tqdm import tqdm
import os
from models import *

def train():
    pass

def mean_ap(scores, targets):
    if scores.numel() == 0:
        return 0
    ap = torch.zeros(scores.size(1))
    rg = torch.arange(1, scores.size(0)).float()
    for k in range(scores.size(1)):
        score = scores[:, k]
        target = targets[:, k]
        #print(score.shape)
        #print(target.shape)
        ap[k] = average_precision(score, target)
    #print(ap)
    return ap

def average_precision(output, target, difficult_examples=True):
    #import pdb
    #pdb.set_trace()
    sorted, indices = torch.sort(output, dim=0, descending=True)
    #import pdb
    #pdb.set_trace()
    pos_count = 0.
    total_count = 0.
    precision_at_i = 0.
    for i in indices:
        label = target[i]
        #print(label)
        #if label == 0:
        #    continue
        if label == 1:
            pos_count += 1
        total_count += 1
        if label == 1:
            precision_at_i += pos_count / total_count
    #print(precision_at_i)
    #print(pos_count, total_count)
    if pos_count == 0:
        return 0
    precision_at_i /= pos_count
    #print(pos_count)
    return precision_at_i


def test(model, test_loader):

    predicts = []
    targets = []
    for idx, ((imgs, img_names, word_embedding),labels) in tqdm(enumerate(test_loader)):
        imgs, labels = imgs.cuda(), labels.cuda()
        with torch.no_grad():
            predict = model(imgs, word_embedding)
        #print(predict)
        #print(labels)
        targets.append(labels)
        predicts.append(predict)

    predicts = torch.cat(predicts, dim=0)
    targets = torch.cat(targets, dim=0)
    #import pdb
    #pdb.set_trace()
    ap = mean_ap(predicts, targets)
    return torch.mean(ap).item()


mean = [0.485, 0.456, 0.406]
std = [0.229, 0.224, 0.225]

if __name__ == "__main__":
    os.environ['CUDA_VISIBLE_DEVICES'] = '0,1,2,3'
    train_transform = transforms.Compose([
        transforms.Resize((448, 448)),
        transforms.RandomHorizontalFlip(),
        transforms.ToTensor(),
        transforms.Normalize(mean=mean, std=std),
    ])
    test_transform = transforms.Compose([
        transforms.Resize((448, 448)),
        transforms.ToTensor(),
        transforms.Normalize(mean=mean, std=std),
    ])
    train_set = COCO2014(root='/raid/home/bravolu/data/coco/', phase='train', transform=train_transform)
    test_set = COCO2014(root='/raid/home/bravolu/data/coco/', phase='val', transform=test_transform)
    train_loader = DataLoader(
        train_set,
        batch_size=64,
        num_workers=0,
        pin_memory=True
    )
    test_loader = DataLoader(
        test_set,
        batch_size=128,
        num_workers=0,
        pin_memory=True
    )
    device = 'cuda' if torch.cuda.is_available() else 'cpu'

    model = KSSNet().to(device)
    #model = resnet101(pretrained=False, num_classes=80).to(device)
    #model.load_state_dict(torch.load('tmp.pth').state_dict())
    model = nn.DataParallel(model)
    #mAP = test(model, test_loader)
    #print('mAP: {:.2f}'.format(mAP))

    criterion = nn.BCELoss().to(device)
    #criterion = nn.MultiLabelSoftMarginLoss()
    optimizer = torch.optim.SGD(model.parameters(),
                                lr=0.1,
                                momentum=0.9,
                                weight_decay=1e-4)
    for epoch in range(200):
        for idx, ((imgs, img_names, word_embedding), targets) in tqdm(enumerate(train_loader)):
            imgs, targets = imgs.to(device), targets.to(device)
            #import pdb
            #pdb.set_trace()
            predicts = model(imgs, word_embedding)
            #print(predicts)
            loss = criterion(predicts, targets)
            #print('Epoch: {} | loss: {:.2f} |'.format(epoch+1, loss.item()))
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        if isinstance(model, nn.DataParallel):
            torch.save(model.module, 'tmp.pth')
        else:
            torch.save(model, 'tmp.pth')
        if epoch % 5 == 0:
            mAP = test(model, test_loader)
            print("Epoch: {} | mAP: {}".format(epoch, mAP))






