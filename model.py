import os

import tensorflow as tf
import keras.models as KM
import keras.layers as KL
import keras.layers.convolutional as KLC
import keras.layers.normalization as KLN
import keras.optimizers as KO
from keras.utils import np_utils
from keras.preprocessing.image import ImageDataGenerator

def createCifarCNN(nb_classes=10, img_row=32, img_column=32, img_channel=3):
	m = KM.Sequential()
	# Convolution layers
	m.add(KLC.ZeroPadding2D(input_shape=(img_channel, img_row, img_column), padding=(2, 2)))
	m.add(KLC.Convolution2D(64, 5, 5, border_mode='valid', activation='relu'))
	m.add(KLN.BatchNormalization())
	m.add(KLC.MaxPooling2D(pool_size=(3, 3), strides=(2, 2), border_mode='same'))
	m.add(KLC.ZeroPadding2D(padding=(2, 2)))
	m.add(KLC.Convolution2D(64, 5, 5, border_mode='valid', activation='relu'))
	m.add(KLN.BatchNormalization())
	m.add(KLC.MaxPooling2D(pool_size=(3, 3), strides=(2, 2), border_mode='same'))

	# Posible to turn off this block
	# with tf.device('/cpu:0'):
	m.add(KLC.ZeroPadding2D(padding=(2, 2)))
	m.add(KLC.Convolution2D(128, 5, 5, border_mode='valid', activation='relu'))
	m.add(KLN.BatchNormalization())
	m.add(KLC.MaxPooling2D(pool_size=(3, 3), strides=(2, 2), border_mode='same'))

	# Fully connected layer
	m.add(KL.Flatten())
	m.add(KL.Dense(1000))
	m.add(KL.Dropout(0.25))
	m.add(KL.Activation('relu'))
	m.add(KL.Dense(nb_classes))
	m.add(KL.Activation('softmax'))
	return m

class Trainer:
	def __init__(self, model_name, model_instance, nb_epoch=1, batch_size=16):
		self.model = model_instance
		self.model_name = model_name
		self.batch_size = batch_size
		self.nb_epoch = nb_epoch
		self.x_train = []
		self.y_train = []
		self.x_test = []
		self.y_test = []
		self.prepared = False
		self.trained = False
		self.optimizer = KO.Adam(lr=0.0001, epsilon=1e-8)
		
	def set_train_data(self, x, y):
		# input x is 2d matrix. y is vector
		self.y_train = np_utils.to_categorical(y)
		self.x_train = x
		print('Successfully set train data. Train model.')
		self.prepared = True

	def save_m(self, file_path='./'):
		# super(Model, self).save(os.path.join(file_path, self.model_name))
		# serialize model to JSON
		if self.model.loss is None:
			raise Exception('Loss function is not defined. Please execute `model.compile(...)`')
		
		path_s = os.path.join(file_path, self.model_name)
		model_json = self.model.to_json()
		with open(path_s + '.json', 'w') as json_file:
			json_file.write(model_json)
		# serialize weights to HDF5
		self.model.save_weights(path_s + '.h5', overwrite=True)
		print('Model saved to disk `%s`' % (path_s))

	def train(self, validation_data=None):
		if not self.prepared:
			print('Please set data to train model.')
			return
		self.model.compile(
			loss='categorical_crossentropy',
			optimizer=self.optimizer,
			metrics=['accuracy']
		)
		self.model.fit(
			self.x_train,
			self.y_train,
			batch_size=self.batch_size,
			nb_epoch=self.nb_epoch,
			#  validation_split=0.1,
			validation_data=validation_data,
			shuffle=True
		)

	def train_gen(self, validation_data=None, callbacks=None):
		if not self.prepared:
			print('Please set data to train model.')
			return

		# This will do preprocessing and realtime data augmentation:
		datagen = ImageDataGenerator(
			featurewise_center=False,  # set input mean to 0 over the dataset
			samplewise_center=False,  # set each sample mean to 0
			featurewise_std_normalization=False,  # divide inputs by std of the dataset
			samplewise_std_normalization=False,  # divide each input by its std
			zca_whitening=False,  # apply ZCA whitening
			rotation_range=0,  # randomly rotate images in the range (degrees, 0 to 180)
			# randomly shift images horizontally (fraction of total width)
			width_shift_range=0.1,
			# randomly shift images vertically (fraction of total height)
			height_shift_range=0.1,
			shear_range=0.,  # set range for random shear
			zoom_range=0.,  # set range for random zoom
			channel_shift_range=0.,  # set range for random channel shifts
			# set mode for filling points outside the input boundaries
			fill_mode='nearest',
			cval=0.,  # value used for fill_mode = "constant"
			horizontal_flip=True,  # randomly flip images
			vertical_flip=False,  # randomly flip images
			# set rescaling factor (applied before any other transformation)
			rescale=None,
		)

		# Compute quantities required for feature-wise normalization
		# (std, mean, and principal components if ZCA whitening is applied).
		datagen.fit(self.x_train)
		
		self.model.compile(
			loss='categorical_crossentropy',
			optimizer=self.optimizer,
			metrics=['accuracy']
		)
		# Arguments:
		# generator, samples_per_epoch, nb_epoch, verbose=1, callbacks=[],
		# validation_data=None, nb_val_samples=None, class_weight=None, max_q_size=10
		self.model.fit_generator(
			datagen.flow(self.x_train, self.y_train, batch_size=self.batch_size),
			len(self.x_train),
			self.nb_epoch,
			validation_data=validation_data,
			callbacks=callbacks
		)

def compile(model):
	model.compile(
		loss='categorical_crossentropy',
		optimizer=KO.Adam(lr=0.0001, epsilon=1e-8),
		metrics=['accuracy']
	)
	return model

def loadModel(json_s):
	return KM.model_from_json(json_s)

# https://machinelearningmastery.com/save-load-keras-deep-learning-models/
def importModel(path_s):
	# load json and create model
	json_file = open(path_s + '.json', 'r')
	loaded_model_json = json_file.read()
	json_file.close()
	
	print('loaded_model_json')
	print(loaded_model_json)
	loaded_model = KM.model_from_json(loaded_model_json)
			# import json
			# loaded_model = KM.model_from_json(json.dumps(loaded_model_json))
	# load weights into new model
	loaded_model.load_weights(path_s + '.h5')
	print('Loaded model from disk')
	return loaded_model  
	# evaluate loaded model on test data
	# loaded_model.compile(loss='binary_crossentropy', optimizer='rmsprop', metrics=['accuracy'])
	
	# score = loaded_model.evaluate(X, Y, verbose=0)
	# print("%s: %.2f%%" % (loaded_model.metrics_names[1], score[1]*100))



def getDataGenerator(x_train):
	# This will do preprocessing and realtime data augmentation:
	datagen = ImageDataGenerator(
		featurewise_center=False,  # set input mean to 0 over the dataset
		samplewise_center=False,  # set each sample mean to 0
		featurewise_std_normalization=False,  # divide inputs by std of the dataset
		samplewise_std_normalization=False,  # divide each input by its std
		zca_whitening=False,  # apply ZCA whitening
		rotation_range=0,  # randomly rotate images in the range (degrees, 0 to 180)
		# randomly shift images horizontally (fraction of total width)
		width_shift_range=0.1,
		# randomly shift images vertically (fraction of total height)
		height_shift_range=0.1,
		shear_range=0.,  # set range for random shear
		zoom_range=0.,  # set range for random zoom
		channel_shift_range=0.,  # set range for random channel shifts
		# set mode for filling points outside the input boundaries
		fill_mode='nearest',
		cval=0.,  # value used for fill_mode = "constant"
		horizontal_flip=True,  # randomly flip images
		vertical_flip=False,  # randomly flip images
		# set rescaling factor (applied before any other transformation)
		rescale=None,
	)

	# Compute quantities required for feature-wise normalization
	# (std, mean, and principal components if ZCA whitening is applied).
	datagen.fit(x_train)
	return datagen
	