import cPickle as pickle
import numpy as np
import os
from PIL import Image
import six

train_files = ['data_batch_{}'.format(i+1) for i in six.moves.range(5)]
test_files = ['test_batch']


def load_file(file_path):
    with open(file_path, 'rb') as f:
        data = pickle.load(f)
    return data['data'].astype(np.float32), np.asarray(data['labels'], dtype=np.int32)


def load(data_dir):
    train_data = [load_file(os.path.join(data_dir, file_name)) for file_name in train_files]
    images, labels = zip(*train_data)
    train_images = np.concatenate(images)
    train_labels = np.concatenate(labels)
    test_data = [load_file(os.path.join(data_dir, file_name)) for file_name in test_files]
    images, labels = zip(*test_data)
    test_images = np.concatenate(images)
    test_labels = np.concatenate(labels)

    return train_images, train_labels, test_images, test_labels


def normalize_contrast(x):
    mean = np.mean(x, axis=1).reshape((-1, 1))
    std = np.std(x, axis=1).reshape((-1, 1))

    return (x - mean) / std


def calc_zca(x):
    n = x.shape[0]

    mean = np.mean(x, axis=0)
    x = x - mean

    c = np.dot(x.T, x)
    u, lam, v = np.linalg.svd(c)

    eps = 0
    sqlam = np.sqrt(lam + eps)
    uzca = np.dot(u / sqlam[np.newaxis, :], u.T)
    return uzca, mean


def save_image(x, path, normalize=True):
    image = x[:100, ]
    if normalize:
        max_value = np.max(np.abs(image), axis=1).reshape((100, 1))
        image = image / max_value * 127
    image = (image + 128).clip(0, 255).astype(np.uint8)
    image = image.reshape((10, 10, 3, 32, 32))
    image = np.pad(image, ((0, 0), (0, 0), (0, 0), (2, 2), (2, 2)), mode='constant', constant_values=0)
    image = image.transpose((0, 3, 1, 4, 2)).reshape((360, 360, 3))
    Image.fromarray(image).save(path)

def main(dataset_path, output_path):
    raw_train_x, raw_train_y, raw_test_x, raw_test_y = load(dataset_path)
    
    # Create destination path if it does not exist
    if not os.path.exists('output_path'):
        os.mkdir(output_path)
        
    labels = {'train': raw_train_y, 'test': raw_test_y}
    with open(os.path.join(output_path, 'label.pkl'), 'wb') as f:
        pickle.dump(labels, f, pickle.HIGHEST_PROTOCOL)

    # subtract mean
    mean = np.mean(raw_train_x)
    train_x = raw_train_x - mean
    test_x = raw_test_x - mean
    images = {'train': train_x, 'test': test_x}
    with open(os.path.join(output_path, 'image.pkl'), 'wb') as f:
        pickle.dump(images, f, pickle.HIGHEST_PROTOCOL)
    with open(os.path.join(output_path, 'mean.txt'), 'w') as f:
        f.write(np.array_str(np.array(mean)))
    save_image(train_x, os.path.join(output_path, 'sample.png'))

    # ZCA whitening
    zca, mean = calc_zca(raw_train_x)
    train_x = np.dot(raw_train_x - mean, zca.T)
    test_x = np.dot(raw_test_x - mean, zca.T)
    with open(os.path.join(output_path, 'image_zca.pkl'), 'wb') as f:
        pickle.dump(images, f, pickle.HIGHEST_PROTOCOL)
    save_image(train_x, os.path.join(output_path, 'sample_zca.png'), normalize=True)

    # contrast normalization and ZCA whitening
    train_x = normalize_contrast(raw_train_x)
    test_x = normalize_contrast(raw_test_x)
    zca, mean = calc_zca(train_x)
    train_x = np.dot(train_x - mean, zca.T)
    test_x = np.dot(test_x- mean, zca.T)
    with open(os.path.join(output_path, 'image_norm_zca.pkl'), 'wb') as f:
        pickle.dump(images, f, pickle.HIGHEST_PROTOCOL)
    save_image(train_x, os.path.join(output_path, 'sample_norm_zca.png'), normalize=True)
    

if __name__ == '__main__':
    dataset_path = '/root/tfplayground/datasets/cifar-10-batches-py'
    # dataset_path = '/media/cluster_files/dev/cifar/cifar-10-batches-py'
    main(dataset_path, 'data')
