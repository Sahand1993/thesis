# [(bs1, lr1), (bs2, lr2), (bs3, lr3)] (params)
# [1.17, 1.19, 2.20] (colours)

import os
import re
import pickle
from typing import List, Tuple
import matplotlib.pyplot as plt
from math import log2

regex = r"model_bs([0-9]+)_lr(.*)"

def plot(folder):
    params: List[Tuple[int, float]] = []
    maxAccs: List[float] = []
    minAccs: List[float] = []
    minLosses: List[float] = []
    for dir in os.listdir(folder):
        matchObj = re.match(regex, dir)
        params.append((float(matchObj.group(2)), log2(int(matchObj.group(1)))))

        # get the smallest validation loss achieved for the parameter pair
        losses: List[float] = pickle.load(open(folder + "/" + dir + "/pickles/val_losses.pic", "rb"))
        accs: List[float] = pickle.load(open(folder + "/" + dir + "/pickles/val_epoch_accs.pic", "rb"))
        maxAccs.append(max(accs))
        minAccs.append(min(accs))
        minLosses.append(min(losses))

    print("params: " +str(params))
    print("maxAccs" + str(maxAccs))
    print("minLosses" + str(minLosses))
    maxAcc: float = max(maxAccs)
    minAcc: float = min(minAccs)

    fig, ax = plt.subplots()
    ax.scatter(x=list(map(lambda t: t[0], params)), y=list(map(lambda t: t[1], params)), c=list(map(lambda acc: (acc - minAcc)/(maxAcc - minAcc), maxAccs)), cmap="YlOrRd")
    ax.set_xlabel("learning rate")
    ax.set_ylabel("log2(batch size)")
    ax.ticklabel_format(axis = "x", style = "sci", scilimits = (0,0))
#    for lr, bs in params:
#        ax.annotate("{:.2E}".format(lr) + "," + str(bs), (lr, bs))

    plt.show()