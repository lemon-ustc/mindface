# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================

"""Dataset for train and eval."""
import os
import copy
import cv2
import numpy as np
import mindspore.dataset as de
from mindspore.communication.management import init, get_rank, get_group_size

from mindface.detection.datasets.augmentation import Preproc

from mindface.detection.utils.box_utils import Bboxencode


class WiderFace():
    """
    A source dataset that reads and parses WIDERFace dataset.

    Args:
        label_path (String): Path to the root directory that contains the dataset.

    Examples:
        >>> wider_face_dir = "/path/to/wider_face_dataset"
        >>> dataset = WiderFace(label_path = wider_face_dir)
    """
    def __init__(self, label_path):
        self.images_list = []
        self.labels_list = []
        with open (label_path, mode = "r",encoding = "utf-8") as file:
            lines = file.readlines()
        first = True
        labels = []
        for line in lines:
            line = line.rstrip()
            if line.startswith('#'):
                if first is True:
                    first = False
                else:
                    c_labels = copy.deepcopy(labels)
                    self.labels_list.append(c_labels)
                    labels.clear()
                # remove '# '
                path = line[2:]
                path = label_path.replace('label.txt', 'images/') + path

                assert os.path.exists(path), 'image path is not exists.'

                self.images_list.append(path)
            else:
                line = line.split(' ')
                label = [float(x) for x in line]
                labels.append(label)
        # add the last label
        self.labels_list.append(labels)

        # del bbox which width is zero or height is zero
        for i in range(len(self.labels_list) - 1, -1, -1):
            labels = self.labels_list[i]
            for j in range(len(labels) - 1, -1, -1):
                label = labels[j]
                if label[2] <= 0 or label[3] <= 0:
                    labels.pop(j)
            if not labels:
                self.images_list.pop(i)
                self.labels_list.pop(i)
            else:
                self.labels_list[i] = labels

    def __len__(self):
        return len(self.images_list)

    def __getitem__(self, item):
        return self.images_list[item], self.labels_list[item]

def read_dataset(img_path, annotation):
    """
    Read the data from a python function.

    Args:
        img_path (String): The path of dataset.
        annotation (Dict): The annotation file related to image.

    Returns:
        img (Object), a batch of data.
        target (Object), a batch of label.

    Examples:
        >>> img_path = "/path/to/wider_face_dataset"
        >>> image, target = read_dataset(img_path, annotation)
    """
    cv2.setNumThreads(2)

    if isinstance(img_path, str):
        img = cv2.imread(img_path)
    else:
        img = cv2.imread(img_path.tostring().decode("utf-8"))

    labels = annotation
    anns = np.zeros((0, 15))
    if labels.shape[0] <= 0:
        return anns
    for _, label in enumerate(labels):
        ann = np.zeros((1, 15))

        # get bbox
        ann[0, 0:2] = label[0:2]  # x1, y1
        ann[0, 2:4] = label[0:2] + label[2:4]  # x2, y2

        # get landmarks
        ann[0, 4:14] = label[[4, 5, 7, 8, 10, 11, 13, 14, 16, 17]]

        # set flag
        if (ann[0, 4] < 0):
            ann[0, 14] = -1
        else:
            ann[0, 14] = 1

        anns = np.append(anns, ann, axis=0)
    target = np.array(anns).astype(np.float32)

    return img, target


def create_dataset(data_dir, variance=None, match_thresh=0.35, image_size=640, clip=False, batch_size=32,
                        repeat_num=1, shuffle=True, multiprocessing=True, num_worker=4, is_distribute=False):
    """
    Create a callable dataloader from a python function.

    This allows us to get all kinds of face-related data sets.

    Args:
        data_dir (String): The path of dataset.
        variance (List): The variance of the data. Default: None
        match_thresh (Float): The threshold of match the ground truth. Default: 0.35
        image_size (Int): The image size of per image. Default: 640
        clip (Bool): Whether to clip the image. Default: False
        batch_size (Int): The batch size of dataset. Default: 32
        repeat_num (Int): The repeat times of dataset. Default: 1
        shuffle (Bool): Whether to blend the dataset. Default: True
        multiprocessing (Bool): Parallelize Python function per_batch_map with multi-processing. Default: True
        num_worker (Int): The number of child processes that process data in parallel. Default: 4
        is_distribute (Bool): Distributed training parameters. Default: False

    Returns:
        de_dataset (Object): Data loader.

    Examples:
        >>> training_dataset = "/path/to/wider_face_dataset"
        >>> ds_train = create_dataset(data_dir, variance=[0.1,0.2], match_thresh=0.35, image_size=640, clip=False,
                batch_size=32, repeat_num=1, shuffle=True,multiprocessing=True, num_worker=4, is_distribute=False)
    """
    dataset = WiderFace(data_dir)
    variance = variance or [0.1, 0.2]
    if is_distribute:
        init("nccl")
        rank_id = get_rank()
        device_num = get_group_size()
    else:
        rank_id = 0
        device_num = 1

    if device_num == 1:
        de_dataset = de.GeneratorDataset(dataset, ["image", "annotation"],
                                         shuffle=shuffle,
                                         num_parallel_workers=num_worker)
    else:
        de_dataset = de.GeneratorDataset(dataset, ["image", "annotation"],
                                         shuffle=shuffle,
                                         num_parallel_workers=num_worker,
                                         num_shards=device_num,
                                         shard_id=rank_id)

    aug = Preproc(image_size)
    encode = Bboxencode(variance, match_thresh, image_size, clip)

    def read_data_from_dataset(image, annot):
        i, a = read_dataset(image, annot)
        return i, a

    def augmentation(image, annot):
        i, a = aug(image, annot)
        return i, a

    def encode_data(image, annot):
        out = encode(image, annot)
        return out

    de_dataset = de_dataset.map(input_columns=["image", "annotation"],
                                output_columns=["image", "annotation"],
                                column_order=["image", "annotation"],
                                operations=read_data_from_dataset,
                                python_multiprocessing=multiprocessing,
                                num_parallel_workers=num_worker)
    de_dataset = de_dataset.map(input_columns=["image", "annotation"],
                                output_columns=["image", "annotation"],
                                column_order=["image", "annotation"],
                                operations=augmentation,
                                python_multiprocessing=multiprocessing,
                                num_parallel_workers=num_worker)
    de_dataset = de_dataset.map(input_columns=["image", "annotation"],
                                output_columns=["image", "truths", "conf", "landm"],
                                column_order=["image", "truths", "conf", "landm"],
                                operations=encode_data,
                                python_multiprocessing=multiprocessing,
                                num_parallel_workers=num_worker)

    de_dataset = de_dataset.batch(batch_size, drop_remainder=True)
    de_dataset = de_dataset.repeat(repeat_num)


    return de_dataset
