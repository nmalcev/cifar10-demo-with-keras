import os, sys, time
import numpy as np
import cPickle as pickle
from mpi4py import MPI

import keras
from keras.utils import np_utils

from model import createCifarCNN, compile, loadModel, getDataGenerator
from prepare_data import load_data, load_train, predict
from libs.configure import configureHardware
from libs.timer import Timer
from dataset import restoreDatasetChunk, restoreTestDataset

# https://stackoverflow.com/questions/21088420/mpi4py-send-recv-with-tag

def average_weights(all_weights):
	new_weights = []
	for weights_list_tuple in zip(*all_weights):
		# new_weights.append([np.array(weights_).mean(axis=0) for weights_ in zip(*weights_list_tuple)])
		new_weights.append(np.array([np.array(weights_).mean(axis=0) for weights_ in zip(*weights_list_tuple)]))
	return new_weights


if __name__ == '__main__':
	configureHardware(num_cores=4, num_CPU=1, num_GPU=0)
	comm = MPI.COMM_WORLD
	size = comm.Get_size()
	rank = comm.Get_rank()
	status = MPI.Status() 
	

	
	test_path = 'data/test_x.pkl'
	train_x, train_y = restoreDatasetChunk(rank)
	datagen = getDataGenerator(train_x)

	if rank == 0:
		timer = Timer().start()
		print('STEP 0: Load model')
		model = compile(createCifarCNN())	
		# nb_train_items, input_dim, nb_classes = find_input_dim(file_dir+train_name)
        # model = build_model(input_dim, nb_classes)
		## Since keras 1.0.7
		#model.save('master_model.h5')
		model_json = model.to_json()   # transform the model in json format
		model_weights = model.get_weights()    # returns a list of all weight tensors in the model as Numpy arrays.
	else:
		model_json=None
		model_weights=None

	if rank == 0:
		print('STEP 1: Distribute model')
		for i in range(1, size):
			# comm.send(model_json, dest=i)
			req = comm.isend(model_json, dest=i)
			req.wait()
	else:
		# received_model_json = comm.irecv(source=0)
		req = comm.irecv(source=0)
		received_model_json = req.wait()
		model = compile(loadModel(received_model_json))
		print('Worker: {} model is ready'.format(rank))
	comm.barrier()


	if rank == 0:
		timer.\
			stop().\
			note('Preparation time').\
			start()

	# if rank == 0:
	# 	print('STEP2 : Master brodcast weights to all slave')
	# 	for i in range(1, size):
	# 		req = comm.send(model_weights, dest=i)
	# 		print('Send to {}'.format(i))
		
	# else:
	# 	received_model_json = comm.recv(source=0)
	# 	model.set_weights(received_model_json)
	# 	print('Worker: {} weights are ready'.format(rank))
	
	epoch_number = 2
	for epoch in range(epoch_number):
		print('Epoch {} rank {}'.format(epoch, rank))

		received_model_weights = comm.bcast(model_weights, root=0)
		model.set_weights(received_model_weights)

		model.fit_generator(
			datagen.flow(train_x, train_y, batch_size=16),
			len(train_x),
			# nb_epoch=1,
			1,
			# TODO
			# validation_data=validation_data,
		)

		update_weights =  model.get_weights()
		# model.save_weights('weights_r{}_e{}.h5'.format(rank,epoch))
		all_received_weights = comm.gather(update_weights, root=0)
		print(rank, "after gather weights")

		if rank == 0:
			print('Master received all weights {}'.format(len(all_received_weights)))
			model_weights = average_weights(all_received_weights)
	
	if rank == 0:
		timer.\
			stop().\
			note('Training time')

		print(rank, "Model Evaluation")
		model.set_weights(model_weights)
		model.save_weights('weights_r{}_e{}.h5'.format(rank, epoch_number))
		timer.start()
		test_x, test_y = restoreTestDataset()
		# batch_size = 32
		# traingen = getDataGenerator(test_x)

		# print('Test_x len', len(test_x))

		# score = model.evaluate_generator(
		# 	traingen,
		# 	len(test_x)//batch_size
		# )

		score = model.evaluate(test_x, test_y)

		print('Score:')
		print('Test loss:', score[0])
		print('Test accuracy:', score[1])
		timer.\
			stop().\
			note('Evaluation time')
		print('\n'.join(['{}: {}'.format(note, sec) for (note, sec) in timer.stack]))
	

