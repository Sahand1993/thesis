import re

from datasetiterators.fileiterators import *
from dssm.model_dense_ngram import *
import os
from helpers.helpers import correct_guesses_of_dssm
from tqdm import tqdm
import pickle

def get_feed_dict(batch):
    q_batch = batch.get_q_dense()
    p_batch = batch.get_relevant_dense()
    n1_batch, n2_batch, n3_batch, n4_batch = batch.get_irrelevant_dense()

    feed_dict = {
        x_q: q_batch,
        x_p: p_batch,
        x_n1: n1_batch,
        x_n2: n2_batch,
        x_n3: n3_batch,
        x_n4: n4_batch
    }

    return feed_dict


EPOCHS = 20
BATCH_SIZE = 16
LEARNING_RATE = 0.00011702251629896198

pretrainedDir = "pretrain_squad"
pattern = re.compile("dssm-([0-9]+).*")
dirs = filter(lambda _dir: _dir != ".DS_Store", os.listdir(pretrainedDir))
for i, _dir in enumerate(dirs):
    print()
    print(_dir)
    modelPath = "finetune_pretrained_squad/finetune_pretrained_squad_{}/model_bs".format(_dir) + str(BATCH_SIZE) + "_lr" + str(LEARNING_RATE)

    try:
        os.mkdir("finetune_pretrained_squad")
    except:
        pass
    try:
        os.mkdir("finetune_pretrained_squad/finetune_pretrained_squad_{}".format(_dir))
        os.mkdir(modelPath)
        os.mkdir(modelPath + "/pickles")
        os.mkdir(modelPath + "/tf")
    except FileExistsError:
        pass

    optimizer = tf.compat.v1.train.AdamOptimizer(LEARNING_RATE).minimize(logloss)
    saver = tf.compat.v1.train.Saver(max_to_keep=20)

    with tf.compat.v1.Session() as sess:
        try:
            # https://www.easy-tensorflow.com/tf-tutorials/basics/save-and-restore
            modelFiles = os.listdir(os.path.join(pretrainedDir, _dir, "model_bs".format(_dir) + str(BATCH_SIZE) + "_lr" + str(LEARNING_RATE), "tf"))
            fileName = list(filter(lambda name: name != "checkpoint" and name != ".DS_Store", modelFiles))[0]
            pretrainedModelNo = pattern.match(fileName).group(1)
            path = os.path.join(pretrainedDir, _dir, "model_bs".format(_dir) + str(BATCH_SIZE) + "_lr" + str(LEARNING_RATE), "tf", "dssm-" + pretrainedModelNo)
            saver.restore(sess, path)
            print("restored model")
        except Exception as err:
            print("Couldn't restore model")
            init = tf.compat.v1.global_variables_initializer()
            sess.run(init)
            print("Initializing new model")

        DENSE = True

        trainingSet = WikiQAFileIterator(
            "datasets/wikiqa/data.csv",
            "datasets/wikiqa/train.csv",
            batch_size=BATCH_SIZE,
            no_of_irrelevant_samples=4,
            encodingType="NGRAM",
            dense=DENSE,
            shuffle=True)

        validationSet = WikiQAFileIterator(
            "datasets/wikiqa/data.csv",
            "datasets/wikiqa/val.csv",
            batch_size=BATCH_SIZE,
            no_of_irrelevant_samples=4,
            encodingType="NGRAM",
            dense=DENSE,
            shuffle=True)

        try:
            iterations_done = pickle.load(open(modelPath + "/pickles/i.pic", "rb"))
            train_epoch_accuracies = pickle.load(open(modelPath + "/pickles/train_epoch_accs.pic", "rb"))
            train_losses = pickle.load(open(modelPath + "/pickles/train_losses.pic", "rb"))
            val_epoch_accuracies = pickle.load(open(modelPath + "/pickles/val_epoch_accs.pic", "rb"))
            val_losses = pickle.load(open(modelPath + "/pickles/val_losses.pic", "rb"))
            print("Got pickles:")
            print("iterations_done: {}".format(iterations_done))
            print("train_epoch_accuracies: {}".format(train_epoch_accuracies))
            print("val_epoch_accuracies: {}".format(val_epoch_accuracies))
            print("train_losses: {}".format(train_losses))
            print("val_losses: {}".format(val_losses))
            print("Starting on epoch " + str(iterations_done + 1))
        except FileNotFoundError as e:
            iterations_done = 0
            train_epoch_accuracies = []
            train_losses = []
            val_epoch_accuracies = []
            val_losses = []
            print("Couldn't find pickles: {}".format(e))
            print("Starting fresh")
            # evaluate on validation set
            ll_val_overall = 0
            correct_val = 0
            print("Calculating initial val acc")
            for batch in tqdm(validationSet):
                feed_dict = get_feed_dict(batch)
                (ll_val,) = sess.run([logloss], feed_dict=feed_dict)
                batch_correct = correct_guesses_of_dssm(sess, feed_dict, prob_p, prob_n1, prob_n2, prob_n3, prob_n4)
                correct_val += batch_correct
                ll_val_overall += ll_val
            validationSet.restart()
            print("initial val acc: {}".format(correct_val / validationSet.getNoOfDataPoints()))

        for epoch in range(iterations_done + 1, EPOCHS + 1):
            print("Epoch {}".format(epoch))
            if epoch > 1: # Should be larger than 1, since we're starting on epoch 1.
                trainingSet.restart()
                validationSet.restart()

            ll_train_overall = 0
            correct_train = 0
            for batch in tqdm(trainingSet):
                feed_dict = get_feed_dict(batch)
                _, ll = sess.run([optimizer, logloss], feed_dict=feed_dict)
                ll_train_overall += ll
                batch_correct = correct_guesses_of_dssm(sess, feed_dict, prob_p, prob_n1, prob_n2, prob_n3, prob_n4)
                correct_train += batch_correct

            # evaluate on validation set
            ll_val_overall = 0
            correct_val = 0
            for batch in tqdm(validationSet):
                feed_dict = get_feed_dict(batch)
                (ll_val,) = sess.run([logloss], feed_dict=feed_dict)
                batch_correct = correct_guesses_of_dssm(sess, feed_dict, prob_p, prob_n1, prob_n2, prob_n3, prob_n4)
                correct_val += batch_correct
                ll_val_overall += ll_val

            print(correct_train / trainingSet.getNoOfDataPoints())
            print(correct_val / validationSet.getNoOfDataPoints())
            val_losses.append(ll_val_overall / validationSet.getNoOfDataPoints())
            val_epoch_accuracies.append(correct_val / validationSet.getNoOfDataPoints())
            train_losses.append(ll_train_overall / trainingSet.getNoOfDataPoints())
            train_epoch_accuracies.append(correct_train / trainingSet.getNoOfDataPoints())

            pickle.dump(train_losses, open(modelPath + "/pickles/train_losses.pic", "wb"))
            pickle.dump(val_epoch_accuracies, open(modelPath + "/pickles/val_epoch_accs.pic", "wb"))
            pickle.dump(val_losses, open(modelPath + "/pickles/val_losses.pic", "wb"))
            pickle.dump(train_epoch_accuracies, open(modelPath + "/pickles/train_epoch_accs.pic", "wb"))
            pickle.dump(epoch, open(modelPath + "/pickles/i.pic", "wb"))
            print("Dumped losses and accuracies")

            saver.save(sess, modelPath + "/tf/dssm", global_step=epoch)
            print("saved model")

            print("overall train loss " + str(ll_train_overall / trainingSet.getNoOfDataPoints()))
            print("overall val loss " + str(ll_val_overall / validationSet.getNoOfDataPoints()))