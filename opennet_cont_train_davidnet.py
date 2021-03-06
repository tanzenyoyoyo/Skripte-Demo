# -*- coding: utf-8 -*-
"""opennet_cifar10_cont_train_davidnet_new_loss_part1.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/15Tomc-pmqMIUEr-brP3g_hAW4VvEGtoS
"""

!apt-get install -y -qq software-properties-common python-software-properties module-init-tools
!add-apt-repository -y ppa:alessandro-strada/ppa 2>&1 > /dev/null
!apt-get update -qq 2>&1 > /dev/null
!apt-get -y install -qq google-drive-ocamlfuse fuse
from google.colab import auth
auth.authenticate_user()
from oauth2client.client import GoogleCredentials
creds = GoogleCredentials.get_application_default()
import getpass
!google-drive-ocamlfuse -headless -id={creds.client_id} -secret={creds.client_secret} < /dev/null 2>&1 | grep URL
vcode = getpass.getpass()
!echo {vcode} | google-drive-ocamlfuse -headless -id={creds.client_id} -secret={creds.client_secret}

!mkdir -p drive
!google-drive-ocamlfuse drive

!pip install tensorflow-gpu==2.0.0

# Commented out IPython magic to ensure Python compatibility.
from __future__ import absolute_import, division, print_function, unicode_literals

import tensorflow as tf
from tensorflow import keras
import numpy as np

from tensorflow.keras import datasets, layers
from tensorflow.keras.models import Sequential, load_model, Model
from tensorflow.keras.layers import InputLayer, Dense, Conv2D, Flatten, Dropout, concatenate, MaxPooling2D, BatchNormalization, LeakyReLU, Add, Softmax
from tensorflow.keras.preprocessing.image import ImageDataGenerator

from tensorflow.keras.utils import plot_model
from tensorflow.keras.callbacks import ModelCheckpoint

from tensorflow.python.ops import array_ops
from tensorflow.python.ops import math_ops
from tensorflow.python.framework import dtypes

import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
import seaborn as sns
import pandas as pd
# %matplotlib inline

from tensorflow.keras import backend as K

import time

from tensorflow.keras.utils import to_categorical

from tensorflow.keras.datasets import cifar10, mnist, cifar100, fashion_mnist

from sklearn.metrics import precision_score, recall_score, multilabel_confusion_matrix, classification_report, accuracy_score, balanced_accuracy_score, f1_score, roc_auc_score

import umap

import os
os.environ["PATH"] += os.pathsep + 'C:/Program Files (x86)/Graphviz2.38/bin/'

## get data

from drive.code.datapreprocessing import data_preprocessing

x_train, y_train, x_train_without_normalization, y_train_without_ohc, x_test, y_test_without_ohc, y_test = data_preprocessing(cifar10)

x_train = np.reshape(x_train, [len(x_train), 32, 32, 3])
x_test = np.reshape(x_test, [len(x_test), 32, 32, 3])

class_names = ['airplane', 'automobile', 'bird', 'cat', 'deer',
               'dog', 'frog', 'horse', 'ship', 'truck']

plt.figure(figsize=(10,10))
for i in range(25):
    plt.subplot(5,5,i+1)
    plt.xticks([])
    plt.yticks([])
    plt.grid(False)
    plt.imshow(x_train[i], cmap=plt.cm.binary)
    # The CIFAR labels happen to be arrays, 
    # which is why you need the extra index
    plt.xlabel(class_names[y_train_without_ohc[i][0]])
plt.show()

y_test = tf.argmax(y_test, axis=1)

y_test_new = y_test.numpy()
for i in range(y_test_new.shape[0]):
  if y_test_new[i] > 6:
    y_test_new[i] = 6
y_test_new_auc = y_test.numpy()
for i in range(y_test_new_auc.shape[0]):
  if y_test_new_auc[i] < 6:
    y_test_new_auc[i] = 11
  if 10 > y_test_new_auc[i] >= 6:
    y_test_new_auc[i] = 0

for i in range(y_test_new_auc.shape[0]):
  if y_test_new_auc[i] == 11:
    y_test_new_auc[i] = 1

input_image_shape = (32, 32, 3)
z_dim = 6

## Define loss function

def bucket_mean(data, bucket_ids, num_buckets):
    """calculate classwise_mean
    """
    total = tf.math.unsorted_segment_sum(data, bucket_ids, num_buckets)
    count = tf.math.unsorted_segment_sum(tf.ones_like(data), bucket_ids, num_buckets)
    return total / count


def sq_difference_from_mean(data, class_mean): # data: [128 * 64]
    """ Calculates the squared difference of all data from class mean. Return [batch_size * y_dim] tensor
    """
    sq_diff_list = []
    for i in range(y_dim):
        sq_diff_list.append(tf.reduce_mean(
            tf.math.squared_difference(data, class_mean[i]), axis=1)) # [6 * 128]

    return tf.stack(sq_diff_list, axis=1) # [128 * 6], 每个sample到每个class_mean的距离矩阵


def inter_intra_diff(data, labels, class_mean):
    """ Calculates the intra-class and inter-class distance
    as the average distance from the class means.
    """
    sq_diff = sq_difference_from_mean(data, class_mean) # [128 * 6]

    inter_intra_sq_diff = bucket_mean(sq_diff, labels, 2) # sq_diff [128 * 6], labels [128 * 6] = tf.cast(y, tf.int32)    --> result[2,]
    inter_class_sq_diff = inter_intra_sq_diff[0] # useless
    intra_class_sq_diff = inter_intra_sq_diff[1] # intra_c_loss, explain in block paper!
    return intra_class_sq_diff, inter_class_sq_diff


def inter_separation_intra_spred(data, labels, class_mean):  # Lables 是 one-hot-coding [128 * 6]
    """ Calculates intra-class spread as average distance from class means.
    Calculates inter-class separation as the distance between the two closest class means.
    Returns:
    intra-class spread and inter-class separation.
    """
    intra_class_sq_diff, _ = inter_intra_diff(data, labels, class_mean) # intra_c_loss

    ap_dist = all_pair_distance(class_mean) #class中心间的距离 class_mean = bucket_mean(z, tf.argmax(y, axis=1), y_dim) y:one-hot-coding
    dim = tf.shape(class_mean)[0]
    not_diag_mask = tf.logical_not(tf.cast(tf.eye(dim), dtype=tf.bool))
    inter_separation = tf.reduce_min(tf.boolean_mask(tensor=ap_dist, mask=not_diag_mask)) #class_mean距离矩阵中非对角最小元素作为inter_spreration

    min_to_origin = minimum_to_origin(class_mean)

    inter_separation = inter_separation + min_to_origin
    return intra_class_sq_diff, inter_separation


def all_pair_distance(A):
    r = tf.reduce_sum(A*A, 1)

    # turn r into column vector
    r = tf.reshape(r, [-1, 1])
    D = r - 2*tf.matmul(A, A, transpose_b=True) + tf.transpose(r)
    return D

def minimum_to_origin(A):
    r = tf.math.sqrt(tf.reduce_sum(A*A, 1))
    D = tf.reduce_min(r)
    return D

def log10(x):
    numerator = tf.math.log(x)
    denominator = tf.math.log(tf.constant(10, dtype=numerator.dtype))
    return numerator / denominator

def inter_intra_loss(y_true, y_pred):
    y = y_true

    y = tf.cast(y, tf.int32)

    z = y_pred
    z = tf.cast(z, tf.float64)

    
    class_means = bucket_mean(z, tf.argmax(y, axis=1), y_dim)  # 反one-hot-coding    y是one-hot-coding
    # Calculate intra class and inter class distance
    intra_c_loss, inter_c_loss = inter_separation_intra_spred(
        z, tf.cast(y, tf.int32), class_means)

    # Calculate reconstruction loss
    # The correct ii-loss
    loss = tf.reduce_mean(log10(intra_c_loss) - log10(inter_c_loss))
#    loss = intra_c_loss

    return loss

## load model

y_dim = 6
batch_size = 256
num_iterations = 1501
step = 10
step_unknown_class = 5
num_visualization = 0

no_of_components = 2  # for visualization -> PCA.fit_transform()

def david_conv(x, filters, weights_init, alpha):

    x = Conv2D(filters=filters, kernel_size=3, padding='same',
               kernel_initializer=weights_init, use_bias=False)(x)
    x = BatchNormalization()(x)
    x = LeakyReLU(alpha)(x)

    return x


def david_resblock(x, filters, weights_init, alpha):
    x = david_conv(x, filters, weights_init, alpha)
    x = MaxPooling2D()(x)
    x_res = david_conv(x, filters, weights_init, alpha)
    x_res = david_conv(x_res, filters, weights_init, alpha)
    x = Add()([x, x_res])

    return x


def build_cnn(img_shape, reg=None, latent_fea=None, num_outputs=None):

    # ==================== Constants Definition ====================
    weights_init = 'he_normal'

    # ==================== CNN ====================
    input_layer = keras.Input(shape=img_shape)
    x = david_conv(input_layer, filters=64, weights_init=weights_init, alpha=0)
    x = david_resblock(x, filters=128, weights_init=weights_init, alpha=0)
    x = david_conv(x, filters=256, weights_init=weights_init, alpha=0)
    x = MaxPooling2D()(x)
    x = david_resblock(x, filters=512, weights_init=weights_init, alpha=0)
    x = MaxPooling2D((4, 4))(x)
    x = Flatten()(x)
    x_logit = Dense(units=num_outputs + 1, kernel_initializer=weights_init, use_bias=False)(x)
    x_output = Softmax()(x_logit)

    base_network = Model(inputs=input_layer, outputs=x_logit)
    plot_model(base_network, to_file='drive.code.base_network.png', show_shapes=True, show_layer_names=True)

    full_network = Model(inputs=input_layer, outputs=x_output)
    plot_model(full_network, to_file='drive.code.full_network.png', show_shapes=True, show_layer_names=True)

    return base_network, full_network

img_shape = (32, 32, 3)
base_network, full_network = build_cnn(img_shape, num_outputs=5)
base_network = tf.keras.models.load_model('drive/code/models/opennet_cifar10_pretrain_david_net.h5', custom_objects={'inter_intra_loss': inter_intra_loss})
base_network.summary()

base_network.compile(optimizer=tf.keras.optimizers.Adam(0.001, beta_1=0.5),
                     loss=inter_intra_loss)

## predicion & evaluation

def latent(X):
    """ Computes the z-layer output.
    """   
    z = np.zeros((X.shape[0], z_dim))
    batch = batch_size
    for i in range(0, X.shape[0], batch):
        start = i
        end =  min(i+batch, X.shape[0])
        z[start: end] = base_network.predict(X[start: end])
    return z


def update_class_stats(X, y):
    """ Recalculates class means.
    """
    z = latent(X)

    c_means = bucket_mean(z, tf.argmax(y, axis=1), y_dim)
    if decision_dist_fn == 'mahalanobis':
        c_cov, c_cov_inv = class_covarience(z, y)
        
    return c_means

def class_covarience(Z, y):
    dim = z_dim

    per_class_cov = np.zeros((y.shape[1], dim, dim))
    per_class_cov_inv = np.zeros_like(per_class_cov)
    for c in range(y.shape[1]):
        per_class_cov[c, :, :] = np.cov((Z[y[:, c].astype(bool)]).T)
        per_class_cov_inv[c, :, :] = np.linalg.pinv(per_class_cov[c, :, :])

    return per_class_cov, per_class_cov_inv


def distance_from_all_classes(X):
    """ Computes the distance of each instance from all class means.
    """
    z = latent(X)
    dist = np.zeros((z.shape[0], y_dim))
    for j in range(y_dim):
        if decision_dist_fn == 'euclidean': # squared euclidean
            dist[:, j] = np.sum(np.square(z - c_means[j]), axis=1)
        elif decision_dist_fn == 'mahalanobis':
            dist[:, j] = scipy.spatial.distance.cdist(
                z, c_means[j][None, :],
                'mahalanobis', VI=c_cov_inv[j]).reshape((z.shape[0]))
    return dist

def decision_function(X):
    """ Computes the outlier score. The larger the score the more likely it is an outlier.
    """
    dist = distance_from_all_classes(X)
    return np.amin(dist, axis=1)

def thresholds(X):
    """ Computes thresholds. Shouldn't be called from outside.
    """
    score = decision_function(X)

    threshold = np.ones(y_dim)
    cutoff_idx = max(1, int(score.shape[0] * 0.01))
    threshold *= sorted(score)[-cutoff_idx]

    return threshold

def predict_prob(X):
    """ Predicts class probabilities for X over known classes.
    """

    dist = distance_from_all_classes(X)

#    prob = np.exp(-dist)
    prob = np.reciprocal(np.log(dist+1))
    prob = prob / prob.sum(axis=1)[:,None]

    return prob

def predict(X):
    """ Performs closed set classification (i.e. prediction over known classes).
    """
    prob = predict_prob(X)
    return np.argmax(prob, axis=1)

def predict_open(X):
    """ Performs open set recognition/classification.
    """
    pred = predict(X)
    unknown_class_label = y_dim
    score = decision_function(X)
    for i in range(X.shape[0]):
        if score[i] > threshold[pred[i]]:
            pred[i] = unknown_class_label

    return pred

def visualization():
    # Test the network
    global num_visualization, y_test, x_embeddings_before_train
    # creating an empty network
    testing_embeddings = create_network(input_image_shape)
    
    if num_visualization == 0:
        x_embeddings_before_train = base_network.predict(x_test)

    # Grabbing the weights from the trained network
    for layer_target, layer_source in zip(testing_embeddings.layers, base_network.layers):
        weights = layer_source.get_weights()
        layer_target.set_weights(weights)
        del weights

    # Visualizing the effect of embeddings -> using PCA!

    x_embeddings = testing_embeddings.predict(x_test)
    dict_embeddings = {}
    dict_gray = {}
    test_class_labels = np.unique(y_test)

    pca = PCA(n_components=no_of_components)
    decomposed_embeddings = pca.fit_transform(x_embeddings)
    decomposed_gray = pca.fit_transform(x_embeddings_before_train)


    fig = plt.figure(figsize=(16, 8))
    for label in(test_class_labels):
        decomposed_embeddings_class = decomposed_embeddings[y_test == label]
        decomposed_gray_class = decomposed_gray[y_test == label]

        plt.subplot(1,2,1)
        plt.scatter(decomposed_gray_class[::step,1], decomposed_gray_class[::step,0],label=str(label))
        plt.title('before training (embeddings)')
        plt.legend()

        plt.subplot(1,2,2)
        plt.scatter(decomposed_embeddings_class[::step, 1], decomposed_embeddings_class[::step, 0], label=str(label))
        plt.title('after @%d itararions' % i)
        plt.legend()
    fig.suptitle('No.{} visualization'.format(num_visualization + 1), fontsize=20)
    plt.show() 
    num_visualization += 1

def visualization_unknown_class():
    # Test the network
    global num_visualization, y_test_new, x_embeddings_before_train
    # creating an empty network
    testing_embeddings = create_network(input_image_shape,)
    if num_visualization == 0:
        x_embeddings_before_train = base_network.predict(x_test)
#        y_test = tf.argmax(y_test, axis=1)

    # Grabbing the weights from the trained network
    for layer_target, layer_source in zip(testing_embeddings.layers, base_network.layers):
        weights = layer_source.get_weights()
        layer_target.set_weights(weights)
        del weights

    # Visualizing the effect of embeddings -> using PCA!

    x_embeddings = testing_embeddings.predict(x_test)
    dict_embeddings = {}
    dict_gray = {}
    test_class_labels = np.unique(y_test_new)

    pca = PCA(n_components=no_of_components)
    decomposed_embeddings = pca.fit_transform(x_embeddings)
    decomposed_gray = pca.fit_transform(x_embeddings_before_train)


    fig = plt.figure(figsize=(16, 8))
    for label in(test_class_labels):
        decomposed_embeddings_class = decomposed_embeddings[y_test_new == label]
        decomposed_gray_class = decomposed_gray[y_test_new == label]

        plt.subplot(1,2,1)
        plt.scatter(decomposed_gray_class[::step_unknown_class,1], decomposed_gray_class[::step_unknown_class,0],label=str(label))
        plt.title('before training (embeddings)')
        plt.legend()

        plt.subplot(1,2,2)
        plt.scatter(decomposed_embeddings_class[::step_unknown_class, 1], decomposed_embeddings_class[::step_unknown_class, 0], label=str(label))
        plt.title('after @%d itararions' % i)
        plt.legend()
    fig.suptitle('No.{} visualization'.format(num_visualization + 1), fontsize=20)
    plt.show() 
    num_visualization += 1

def Umap():
  sns.set(style='white', context='notebook', rc={'figure.figsize':(14,10)})
  reducer = umap.UMAP()
  embedding = reducer.fit_transform(base_network.predict(x_test))

  plt.scatter(embedding[:, 0], embedding[:, 1], c=y_test_new, cmap='Spectral', s=3)
  plt.gca().set_aspect('equal', 'datalim')
  plt.colorbar(boundaries=np.arange(8)-0.5).set_ticks(np.arange(6))
  plt.title('UMAP projection of the cifar10 dataset', fontsize=20)
  plt.show()

def calcula_roc_auc_score(y_test, y_score):
    return roc_auc_score(y_test, y_score, average='macro', multi_class='ovo')

def clasification_report(y_test, y_predicted):
    return clasification_report(y_test, y_predicted)

def calcula_balanced_acc(y_test, y_perdicted):
    matrix = multilabel_confusion_matrix(y_test, y_perdicted)
    tn = matrix[:, 0, 0]
    tp = matrix[:, 1, 1]
    fn = matrix[:, 1, 0]
    fp = matrix[:, 0, 1]
    recall = tp / (tp + fn)
    return 0.5 * (np.mean(recall[:6]) + recall[-1:])

#train the model

def _next_batch(x, y):
    index = np.random.randint(0, high=x.shape[0], size=batch_size)
    return x[index], y[index]

aucplt = []
balanced_accplt = []
itera = []

import warnings
 
warnings.filterwarnings('ignore')

for i in range(num_iterations):
    x, y = _next_batch(x_train, y_train)
    z = base_network.predict(x)

    start = time.time()
    
    base_network.train_on_batch(x, y)
    loss = inter_intra_loss(y, z)
    class_means = bucket_mean(z, tf.argmax(y, axis=1), y_dim)
    intra_c_loss, inter_c_loss = inter_separation_intra_spred(z, tf.cast(y, tf.int32), class_means) 
    
    if i % 100 == 0:
        print ('Time for iteration {} is {} sec'.format(i + 1, time.time()-start))
        print('Intra_c_loss is {}, Inter_c_loss is {}, Loss is {}'.format(intra_c_loss, inter_c_loss, loss))
    
        decision_dist_fn = 'euclidean'
        c_means = update_class_stats(x_train, y_train)

        threshold = thresholds(x_train)

        B = predict_open(x_test)
        y_score = np.amax(predict_prob(x_test), -1)
        auc = calcula_roc_auc_score(y_test_new_auc, y_score)
        balanced_acc = calcula_balanced_acc(y_test_new, B)

        aucplt.append(auc)
        balanced_accplt.append(balanced_acc)
        itera.append(i)


        print('auc is {}'.format(auc))
        print('balanced accuracy is {}'.format(balanced_acc))
        print('classification_report: {}'.format(classification_report(y_test_new, B)))

    if i % 500 == 0:

        Umap()

balanced_accplt = np.concatenate(balanced_accplt)
plt.plot(itera, aucplt, color="b", marker="o", label='auc_lr=0.001')
plt.plot(itera, balanced_accplt, color="b", marker="o", label='balanced_acc_lr=0.001')

plt.xticks(np.arange(0, 1000, step=100))
plt.yticks(np.arange(0, 1, step=0.1))
plt.legend(loc='upper left')
plt.grid(False)

# learning rate = 0.0001

base_network_0, full_network_0 = build_cnn(img_shape, num_outputs=5)
base_network_0 = tf.keras.models.load_model('drive/code/models/opennet_cifar10_pretrain_david_net.h5', custom_objects={'inter_intra_loss': inter_intra_loss})

base_network_0.compile(optimizer=tf.keras.optimizers.Adam(0.0001, beta_1=0.5),
                     loss=inter_intra_loss)

def Umap_0():
  sns.set(style='white', context='notebook', rc={'figure.figsize':(14,10)})
  reducer = umap.UMAP()
  embedding = reducer.fit_transform(base_network_0.predict(x_test))

  plt.scatter(embedding[:, 0], embedding[:, 1], c=y_test_new, cmap='Spectral', s=3)
  plt.gca().set_aspect('equal', 'datalim')
  plt.colorbar(boundaries=np.arange(8)-0.5).set_ticks(np.arange(6))
  plt.title('UMAP projection of the cifar10 dataset', fontsize=20)
  plt.show()

def latent(X):
    """ Computes the z-layer output.
    """   
    z = np.zeros((X.shape[0], z_dim))
    batch = batch_size
    for i in range(0, X.shape[0], batch):
        start = i
        end =  min(i+batch, X.shape[0])
        z[start: end] = base_network_0.predict(X[start: end])
    return z

aucplt_0 = []
balanced_accplt_0 = []
itera_0 = []
for i in range(num_iterations):
    x, y = _next_batch(x_train, y_train)
    z = base_network_0.predict(x)

    start = time.time()
    
    base_network_0.train_on_batch(x, y)
    loss = inter_intra_loss(y, z)
    class_means = bucket_mean(z, tf.argmax(y, axis=1), y_dim)
    intra_c_loss, inter_c_loss = inter_separation_intra_spred(z, tf.cast(y, tf.int32), class_means) 
    
    if i % 100 == 0:
        print ('Time for iteration {} is {} sec'.format(i + 1, time.time()-start))
        print('Intra_c_loss is {}, Inter_c_loss is {}, Loss is {}'.format(intra_c_loss, inter_c_loss, loss))
    
        decision_dist_fn = 'euclidean'
        c_means = update_class_stats(x_train, y_train)

        threshold = thresholds(x_train)

        B = predict_open(x_test)
        y_score = np.amax(predict_prob(x_test), -1)
        auc = calcula_roc_auc_score(y_test_new_auc, y_score)
        balanced_acc = calcula_balanced_acc(y_test_new, B)

        aucplt_0.append(auc)
        balanced_accplt_0.append(balanced_acc)
        itera_0.append(i)


        print('auc is {}'.format(auc))
        print('balanced accuracy is {}'.format(balanced_acc))
        print('classification_report: {}'.format(classification_report(y_test_new, B)))

    if i % 500 == 0:

        Umap_0()

balanced_accplt_0 = np.concatenate(balanced_accplt_0)
plt.plot(itera, aucplt, color="b", marker="o", label='auc_lr=0.001')
plt.plot(itera, balanced_accplt, color="b", marker="o", label='balanced_acc_lr=0.001')
plt.plot(itera_0, aucplt_0, color="r", marker="*", label='auc_lr=0.0001')
plt.plot(itera_0, balanced_accplt_0, color="r", marker="*", label='balanced_acc_lr=0.0001')

plt.xticks(np.arange(0, 1000, step=100))
plt.yticks(np.arange(0, 1, step=0.1))
plt.legend(loc='upper left')
plt.grid(False)

# learning rate=0.001
# auc is 0.7929596666666667
# balanced accuracy is [0.57520833]

# learning rate=0.0001
# auc is 0.7453094166666667
# balanced accuracy is [0.66320833]