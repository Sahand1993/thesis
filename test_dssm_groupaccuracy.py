import numpy as np
from typing import Dict
from tqdm import tqdm

from batchiterators.fileiterators import WikiQAFileIterator
from helpers.helpers import correct_guesses_of_dssm

LEARNING_RATE = 0.00011702251629896198

def cosine_sim(a, b, norm_a, norm_b):
    a = np.squeeze(a)
    b = np.squeeze(b)
    return np.dot(a, b) / (norm_a * norm_b)


from dssm.model_dense_ngram import *


optimizer = tf.compat.v1.train.AdamOptimizer(LEARNING_RATE).minimize(logloss)

query_vecs: Dict[int, float] = {}  # The vectorized questions as (id, q_vec)
doc_vecs: Dict[int, float] = {}  # The vectorized documents as (id, doc_vec)

# Load test set

dssmTestSetTotal = WikiQAFileIterator(
    "datasets/wikiqa/data.csv",
    "datasets/wikiqa/test.csv",
    batch_size=1,
    no_of_irrelevant_samples=4,
    encodingType="NGRAM",
    dense=True,
    shuffle=False)


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


# Load model
modelPaths = []

saver = tf.compat.v1.train.Saver()
sess = tf.compat.v1.Session()

def test_group_acc(modelPath: str):
    print("\n " + modelPath)
    dssmTestSetTotal.restart()
    saver.restore(sess, modelPath)
    # init = tf.compat.v1.global_variables_initializer()
    # sess.run(init)

    ll_val_overall = 0
    correct_test = 0
    print("Calculating group accuracy...")
    for batch in tqdm(dssmTestSetTotal):
        feed_dict = get_feed_dict(batch)
        (ll_val,) = sess.run([logloss], feed_dict=feed_dict)
        batch_correct = correct_guesses_of_dssm(sess, feed_dict, prob_p, prob_n1, prob_n2, prob_n3, prob_n4)
        correct_test += batch_correct
        ll_val_overall += ll_val

    print(correct_test / dssmTestSetTotal.getNoOfDataPoints())

for modelPath in modelPaths:
    test_group_acc(modelPath)