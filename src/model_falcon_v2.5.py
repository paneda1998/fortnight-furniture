from keras.applications import InceptionV3
# from keras.applications.inception_v3 import preprocess_input
# from keras.preprocessing.image import img_to_array
# from keras.preprocessing.image import load_img

from keras.optimizers import Adam, SGD

# Keras imports
from keras.models import  Sequential, Model
from keras.layers import Dense, Dropout, Flatten, Activation, GlobalAveragePooling2D
from keras.layers.convolutional import Conv2D, MaxPooling2D
# from keras.callbacks import EarlyStopping
from keras import regularizers

# import glob
import json
import numpy as np

from loader_bot_omega import LoaderBot   # dynamic full image augmentation
# from loader_bot import LoaderBot

import time
from splitter import get_skfold_data

# import pandas as pd
# import numpy as np

import matplotlib
matplotlib.use('Agg')  # Must be before importing matplotlib.pyplot or pylab!
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, FormatStrFormatter


# https://github.com/DeepLearningSandbox/DeepLearningSandbox/blob/master/transfer_learning/fine-tune.py

def setup_to_transfer_learn(model, base_model, optimizer):
    """Freeze all layers and compile the model"""

    for layer in base_model.layers:
        layer.trainable = False

    model.compile(optimizer=optimizer, loss='categorical_crossentropy', metrics=['accuracy'])


def regular_brian_layers(base_model, num_classes, dropout=0.2, l1_reg=0.01):
    """Add last layer to the convnet
    Args:
    base_model: keras model excluding top
    nb_classes: # of classes
    Returns:
    new keras model with last layer
    """
    x = base_model.output
    x = GlobalAveragePooling2D()(x)
    x = Dense(1024,
              activation='relu',
              kernel_initializer='he_normal',
              kernel_regularizer=regularizers.l1(l1_reg))(x) #new FC layer, random init
    # x = Dense(1024, activation='relu')(x)
    x = Dropout(dropout)(x)

    x = Dense(512,
              activation='relu',
              kernel_initializer='he_normal',
              kernel_regularizer=regularizers.l1(l1_reg))(x) #new FC layer, random init
    # x = Dense(512, activation='relu')(x) #new FC layer, random init
    x = Dropout(dropout)(x)

    x = Dense(256,
              activation='relu',
              kernel_initializer='he_normal',
              kernel_regularizer=regularizers.l1(l1_reg))(x) #new FC layer, random init    # x = Dense(256, activation='relu')(x) #new FC layer, random init
    x = Dropout(dropout)(x)

    predictions = Dense(num_classes, activation='softmax')(x) #new softmax layer

    model = Model(inputs=base_model.input, outputs=predictions)

    return model


def double_regular_brian_layers(base_model, num_classes, dropout=0.2, l1_reg=0.01):
    """Add last layer to the convnet
    Args:
    base_model: keras model excluding top
    nb_classes: # of classes
    Returns:
    new keras model with last layer
    """
    x = base_model.output
    x = GlobalAveragePooling2D()(x)
    x = Dense(2048,
              activation='relu',
              kernel_initializer='he_normal',
              kernel_regularizer=regularizers.l1(l1_reg))(x) #new FC layer, random init
    # x = Dense(1024, activation='relu')(x)
    x = Dropout(dropout)(x)

    x = Dense(1024,
              activation='relu',
              kernel_initializer='he_normal',
              kernel_regularizer=regularizers.l1(l1_reg))(x) #new FC layer, random init
    # x = Dense(512, activation='relu')(x) #new FC layer, random init
    x = Dropout(dropout)(x)

    x = Dense(512,
              activation='relu',
              kernel_initializer='he_normal',
              kernel_regularizer=regularizers.l1(l1_reg))(x) #new FC layer, random init    # x = Dense(256, activation='relu')(x) #new FC layer, random init
    x = Dropout(dropout)(x)

    predictions = Dense(num_classes, activation='softmax')(x) #new softmax layer

    model = Model(inputs=base_model.input, outputs=predictions)

    return model


def add_brian_layers(base_model, num_classes, dropout=0.2):
    """Add last layer to the convnet
    Args:
    base_model: keras model excluding top
    nb_classes: # of classes
    Returns:
    new keras model with last layer
    """
    x = base_model.output
    x = GlobalAveragePooling2D()(x)
    x = Dense(1024, activation='relu', kernel_initializer='he_normal')(x) #new FC layer, random init
    # x = Dense(1024, activation='relu')(x)
    x = Dropout(dropout)(x)

    x = Dense(512, activation='relu', kernel_initializer='he_normal')(x) #new FC layer, random init
    # x = Dense(512, activation='relu')(x) #new FC layer, random init
    x = Dropout(dropout)(x)

    x = Dense(256, activation='relu', kernel_initializer='he_normal')(x) #new FC layer, random init
    # x = Dense(256, activation='relu')(x) #new FC layer, random init
    x = Dropout(dropout)(x)

    predictions = Dense(num_classes, activation='softmax')(x) #new softmax layer

    model = Model(inputs=base_model.input, outputs=predictions)

    return model


def add_new_last_layer(base_model, nb_classes):
    """Add last layer to the convnet
    Args:
    base_model: keras model excluding top
    nb_classes: # of classes
    Returns:
    new keras model with last layer
    """
    x = base_model.output
    x = GlobalAveragePooling2D()(x)
    x = Dense(FC_SIZE, activation='relu')(x) #new FC layer, random init

    predictions = Dense(nb_classes, activation='softmax')(x) #new softmax layer

    model = Model(inputs=base_model.input, outputs=predictions)

    return model


def setup_to_finetune(model, freeze, optimizer, weight_decay):
    """Freeze the bottom NB_IV3_LAYERS and retrain the remaining top layers.
    note: NB_IV3_LAYERS corresponds to the top 2 inception blocks in the inceptionv3 arch
    Args:
    model: keras model
    freeze: number of layers to keep frozen
    optimizer: which optimizer to use so the model can be compiled
    weight_decay: how much to regularize the thawed layers
    """
    for layer in model.layers[:freeze]:
        layer.trainable = False

    for layer in model.layers[freeze:]:
        layer.trainable = True
        # regularize unfrozen layers (new as of model v2.5)
        # https://github.com/keras-team/keras/issues/2717
        if hasattr(layer, 'kernel_regularizer'):
            layer.kernel_regularizer = regularizers.l2(weight_decay)
            # print("        adding regularization to thawed layer")

    # # regularize all layers:
    # for layer in model.layers:
    #     if hasattr(layer, 'kernel_regularizer'):
    #         layer.kernel_regularizer = regularizers.l2(WEIGHT_DECAY)

    # adam = Adam(lr=lr)
    # sgd = SGD(lr=lr, momentum=0.9)

    model.compile(optimizer=optimizer, loss='categorical_crossentropy', metrics=['accuracy'])


def activate_regularization(model):
    '''
    Adding regularization to pretrained model doesn't work unless you save the
    model and then reload it. At least according to:
    https://github.com/keras-team/keras/issues/9106

    So this function will save a model then reload it.

    INPUT:
    model: model that will be reloaded

    RETURNS:
    reloaded model
    '''
    print("Activate Regularization: Save Model...")
    model.save_weights("temp.h5")
    print("Activate Regularization: Save Model Complete.")

    print("Activate Regularization: Reload Model Weights...")
    model.load_weights("temp.h5")
    print("Activate Regularization: Reload Model Weights Complete.")

    return model


def plot_hist(history, info_str, epochs=2, augmentation=1, sprint=False):
    '''
    Make a plot of the rate of error as well as the accuracy of the model
    during training.  Also include a line at error 0.20 which was the original
    minimum acceptable error (self imposed) to submit results to the test
    set when doing 3-way split.
    Even after performance regularly exceeded the minimum requirement the line
    was unchanged so that all of the graphs would be relative to each other.
    Also it was still useful to see how a model's error was performing relative
    to this baseline.
    Also, the 2 charts written as a png had the filename coded to include
    hyperparameters that were used in the model when the chart was created.
    This allowed a simple visual evaluation of a model's performance when
    doing randomized hyperparameter search. If a model appeared to be high
    performing then the values could be reused in order to attempt to
    replicate the result.
    '''
    fig, axs = plt.subplots(1, 2, figsize=(16, 8))

    fig.suptitle("", fontsize=12, fontweight='normal')

    # stuff for marking the major and minor ticks dynamically relative
    # to the numper of epochs used to train
    major_ticks = int(epochs / 10.0)
    minor_ticks = int(epochs / 20.0)

    title_text = "Homewares and Furniture Image Identification\n Train Set and Dev Set"
    ACC = 0.817   # record accuracy
    if sprint is True:
        ACC = 0.750
        title_text = "SPRINT: Homewares and Furniture Image Identification\n Train Set and Dev Set"

    if major_ticks < 2:
        major_ticks = 2

    if minor_ticks < 1:
        minor_ticks = 1

    majorLocator = MultipleLocator(major_ticks)
    majorFormatter = FormatStrFormatter('%d')
    minorLocator = MultipleLocator(minor_ticks)

    # # determine how many zero layers there are
    # drop = np.sum([1 if loss == 0 else 0 for loss in history['loss']])
    #
    # if drop > 1:
    #     drop -= 1
    #
    # history['loss'] = history['loss'][drop:]
    # history['val_loss'] = history['val_loss'][drop:]
    # history['acc'] = history['acc'][drop:]
    # history['val_acc'] = history['val_acc'][drop:]

    # correct x axis
    history['loss'] = [0.0] + history['loss']
    history['val_loss'] = [0.0] + history['val_loss']
    history['acc'] = [0.0] + history['acc']
    history['val_acc'] = [0.0] + history['val_acc']

    x_line = [ACC] * (epochs + 1)  # this line is now for accuracy of test set

    # stuff for the loss chart
    axs[0].set_title(title_text)

    if augmentation > 1:
        axs[0].set_xlabel('Epochs\nAugmentation of {:3d}'.format(augmentation))
    else:
        axs[0].set_xlabel('Epochs')

    axs[0].set_xlim(1, epochs)
    axs[0].set_ylabel('Loss')
    axs[0].set_ylim(0, 5)

    axs[0].plot(history['loss'], color="blue", linestyle="--", alpha=0.8, lw=1.0)
    axs[0].plot(history['val_loss'], color="blue", alpha=0.8, lw=1.0)
    axs[0].legend(['Training', 'Validation'])
    axs[0].xaxis.set_major_locator(majorLocator)
    axs[0].xaxis.set_major_formatter(majorFormatter)

    # for the minor ticks, use no labels; default NullFormatter
    axs[0].xaxis.set_minor_locator(minorLocator)

    # stuff for the accuracy chart
    axs[1].set_title(title_text)

    if augmentation > 1:
        axs[1].set_xlabel('Epochs\nAugmentation of {:3d}'.format(augmentation))
    else:
        axs[1].set_xlabel('Epochs')

    axs[1].set_xlim(1, epochs)
    axs[1].set_ylabel('Accuracy')
    axs[1].set_ylim(0.0, 1.0)
    axs[1].plot(x_line, color="red", alpha=0.3, lw=4.0)
    axs[1].plot(history['acc'], color="blue", linestyle="--", alpha=0.5, lw=1.0)
    axs[1].plot(history['val_acc'], color="blue", alpha=0.8, lw=1.0)
    axs[1].plot(x_line, color="red", linestyle="--", alpha=0.8, lw=1.0)
    axs[1].legend(['Record Accuracy ({:1.2f})'.format(ACC), 'Training', 'Validation'], loc='lower right')
    axs[1].xaxis.set_major_locator(majorLocator)
    axs[1].xaxis.set_major_formatter(majorFormatter)

    # for the minor ticks, use no labels; default NullFormatter
    axs[1].xaxis.set_minor_locator(minorLocator)

    plt.savefig("../imgs/" + info_str, facecolor='w', edgecolor='w', transparent=False)
    # plt.show()


def temp_clean_history(hist):
    '''
    For whatever reason saving and loading weights prepends a 0 to the history
    of the model. (weird)

    This attempts to strip that padding so that the charts appear as they Should

    INPUTS:
    hist: dictionary with the history of a model (acc, val, etc)

    RETURNS:
    dictionary of lists with the padded zeros removed
    '''
    temp_hist = hist.copy()
    chop = sum([1 for item in hist["acc"] if item == 0])

    for key in temp_hist.keys():
        temp_hist[key] = temp_hist[key][chop:]

    return temp_hist


def run():
    # data_link_dict = get_skfold_data(path="../data/imgs/*.jpg")
    start_time = time.time()

    # decommisioned because inflight data augmentation solves a lot of these
    # problems

    # Use json to load the permanent dictionary that has been Created
    with open("../data/data_splits.json") as infile:
        data_link_dict = json.load(infile)

    EPOCHS = 5
    AUGMENTATION = 1    # could do 3 epochs of 10 augmentation or 30 of 1 which
                        # provides more data for plots to work with

    MINITRAINS = 30
    DO = 0.55  # drop out

    # for Adam inital LR of 0.0001 is a good starting point
    # for SGD initial LR of 0.001 is a good starting point
    LR = 0.00025
    DECAY = 0.5e-6
    L2_REG = 0.05
    OPTIMIZER = Adam(lr=LR, decay=DECAY)
    # OPTIMIZER = SGD(lr=LR, momentum=0.9, nesterov=True)

    NB_IV3_LAYERS_TO_FREEZE = 172
    MODEL_ID = 'v2_5o'

    plot_file = "model_{:}.png".format(MODEL_ID)
    weights_file = "weights/model_{:}_weights.h5".format(MODEL_ID)
    history_file = "histories/history_{:}.json".format(MODEL_ID)

    # # user parameters for LoaderBot v1.0
    # # Parameters for Generators
    # params = {'dim': (299, 299),
    #           'batch_size': 256,
    #           'n_classes': 128,
    #           'n_channels': 3,
    #           'shuffle': False}

    # These parameters are for LoaderBot v2.0
    # Parameters for Generators
    params = {'dim': (299, 299),
              'batch_size': 128,
              'n_classes': 128,
              'n_channels': 3,
              'augmentation': AUGMENTATION,
              'shuffle': True}
    #
    # Parameters for Generators
    test_params = {'dim': (299, 299),
                   'batch_size': 128,
                   'n_classes': 128,
                   'n_channels': 3,
                   'augmentation': 1,
                   'augment': False,
                   'shuffle': False}

    # Datasets
    X_train_img_paths = data_link_dict["X_test_1"]
    y_train = data_link_dict["y_test_1"]

    X_test_img_paths = data_link_dict["X_test_2"]
    y_test = data_link_dict["y_test_2"]

    print(X_train_img_paths[:5])

    # Generators
    training_generator = LoaderBot(X_train_img_paths, y_train, **params)
    validation_generator = LoaderBot(X_test_img_paths, y_test, **test_params)

    # setup model
    base_model = InceptionV3(weights='imagenet', include_top=False) #include_top=False excludes final FC layer
    model = regular_brian_layers(base_model, 128, DO, l1_reg=0.0005)

    # print(model.summary())

    # mini-train 1, like normal
    # transfer learning
    setup_to_transfer_learn(model, base_model, OPTIMIZER)

    history = {}   # preinitialize history log

    for mt in range(MINITRAINS):
        temp = mt + 1

        if temp == 1:
            # Run model
            new_history = model.fit_generator(generator=training_generator,
                                             validation_data=validation_generator,
                                             epochs=EPOCHS,
                                             use_multiprocessing=False)

            history["acc"] = new_history.history["acc"]
            history["val_acc"] = new_history.history["val_acc"]
            history["loss"] = new_history.history["loss"]
            history["val_loss"] = new_history.history["val_loss"]

        else:

            temp_lr = LR / (10.0**(mt / 5 - (mt // 7.5)))
            print("\n\nLearning rate for mini-train: {:2.8f}\n\n".format(temp_lr))
            # mini-train 2
            OPTIMIZER = Adam(lr=temp_lr, decay=0.0)
            # try to fine tune some of the InceptionV3 layers also

            thaw_count = int(2.5 * temp)
            if thaw_count > 50:
                thaw_count = 50

            thaw_count = NB_IV3_LAYERS_TO_FREEZE - thaw_count

            setup_to_finetune(model, thaw_count, OPTIMIZER, L2_REG)

            model = activate_regularization(model)

            print("\n\n        Starting epoch {:}\n\n".format(EPOCHS * mt + 1))

            # Run model
            new_history = model.fit_generator(generator=training_generator,
                                              validation_data=validation_generator,
                                              epochs=EPOCHS,
                                              use_multiprocessing=False)

            # save the weights in case we want to predict on them later
            model.save(weights_file)

            history["acc"] += new_history.history["acc"]
            history["val_acc"] += new_history.history["val_acc"]
            history["loss"] += new_history.history["loss"]
            history["val_loss"] += new_history.history["val_loss"]

        # seems to be prepending a 0 to the list so ignore that
        history["acc"] = history["acc"]
        history["val_acc"] = history["val_acc"]
        history["loss"] = history["loss"]
        history["val_loss"] = history["val_loss"]

        temp_hist = temp_clean_history(history)

        plot_hist(temp_hist, plot_file, epochs=len(history["acc"]), sprint=True)

    # try to save the history so models can be more easily compared and Also
    # to better log results if going back is needed
    with open(history_file, "w") as outfile:
        json.dump(history, outfile)

    print("\n\n\n\nCompleted in {:6.2f} hrs".format(((time.time() - start_time)) / 3600))  # convert to hours


if __name__ == "__main__":
    run()
