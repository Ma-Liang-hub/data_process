# -*- coding=utf-8 -*-
#!/usr/bin/python

import sys
import os
import shutil
import numpy as np
import json
import xml.etree.ElementTree as ET

# 检测框的ID起始值
START_BOUNDING_BOX_ID = 1
# 类别列表无必要预先创建，程序中会根据所有图像中包含的ID来创建并更新
PRE_DEFINE_CATEGORIES = {}
# If necessary, pre-define category and its id
PRE_DEFINE_CATEGORIES = {"plane":1}


def get(root, name):
    vars = root.findall(name)

    return vars


def get_and_check(root, name, length):
    vars = root.findall(name)
    if len(vars) == 0:
        raise NotImplementedError('Can not find %s in %s.'%(name, root.tag))
    if length > 0 and len(vars) != length:
        raise NotImplementedError('The size of %s is supposed to be %d, but is %d.'%(name, length, len(vars)))
    if length == 1:
        vars = vars[0]
    return vars


# 得到图片唯一标识号
def get_filename_as_int(filename):
    try:
        filename = os.path.splitext(filename)[0]
        return int(filename)
    except:
        raise NotImplementedError('Filename %s is supposed to be an integer.'%(filename))


def convert(xml_list, xml_dir, json_file):
    '''
    :param xml_list: 需要转换的XML文件列表
    :param xml_dir: XML的存储文件夹
    :param json_file: 导出json文件的路径
    :return: None
    '''
    list_fp = xml_list
    # 标注基本结构
    json_dict = {"images":[],
                 "type": "instances",
                 "annotations": [],
                 "categories": []}
    categories = PRE_DEFINE_CATEGORIES
    bnd_id = START_BOUNDING_BOX_ID
    for line in list_fp:
        line = line.strip()
        print("buddy~ Processing {}".format(line))
        # 解析XML
        xml_f = os.path.join(xml_dir, line)
        tree = ET.parse(xml_f)
        root = tree.getroot()
        path = get(root, 'path')
        # 取出图片名字
        if len(path) == 1:
            filename = os.path.basename(path[0].text)
        elif len(path) == 0:
            filename = get_and_check(root, 'filename', 1).text
        else:
            raise NotImplementedError('%d paths found in %s'%(len(path), line))
        ## The filename must be a number
        image_id = get_filename_as_int(filename)  # 图片ID
        size = get_and_check(root, 'size', 1)
        # 图片的基本信息
        width = int(get_and_check(size, 'width', 1).text)
        height = int(get_and_check(size, 'height', 1).text)
        image = {'file_name': filename,
                 'height': height,
                 'width': width,
                 'id':image_id}
        json_dict['images'].append(image)
        # 处理每个标注的检测框
        for obj in get(root, 'object'):
            # 取出检测框类别名称
            category = get_and_check(obj, 'name', 1).text
            # 更新类别ID字典
            if category not in categories:
                new_id = len(categories)
                categories[category] = new_id
            category_id = categories[category]
            bndbox = get_and_check(obj, 'bndbox', 1)
            xmin = int(get_and_check(bndbox, 'xmin', 1).text) - 1
            ymin = int(get_and_check(bndbox, 'ymin', 1).text) - 1
            xmax = int(get_and_check(bndbox, 'xmax', 1).text)
            ymax = int(get_and_check(bndbox, 'ymax', 1).text)
            assert(xmax > xmin)
            assert(ymax > ymin)
            o_width = abs(xmax - xmin)
            o_height = abs(ymax - ymin)
            annotation = dict()
            annotation['area'] = o_width*o_height
            annotation['iscrowd'] = 0
            annotation['image_id'] = image_id
            annotation['bbox'] = [xmin, ymin, o_width, o_height]
            annotation['category_id'] = category_id
            annotation['id'] = bnd_id
            annotation['ignore'] = 0
            # 设置分割数据，点的顺序为逆时针方向
            annotation['segmentation'] = [[xmin,ymin,xmin,ymax,xmax,ymax,xmax,ymin]]

            json_dict['annotations'].append(annotation)
            bnd_id = bnd_id + 1

    # 写入类别ID字典
    for cate, cid in categories.items():
        cat = {'supercategory': 'none', 'id': cid, 'name': cate}
        json_dict['categories'].append(cat)
    # 导出到json
    json_fp = open(json_file, 'w')
    json_str = json.dumps(json_dict)
    json_fp.write(json_str)
    json_fp.close()


if __name__ == '__main__':
    root_path = os.getcwd()
    patch_path = os.path.join(root_path, 'voc_type/mmdetection/600_10')
    xml_dir = os.path.join(patch_path, 'Annotations')

    xml_labels = os.listdir(os.path.join(patch_path, 'Annotations'))
    np.random.shuffle(xml_labels)
    train_labels = xml_labels

    save_path = os.path.join(root_path, 'mmdet_type/600_10')
    split_point = int(len(train_labels)/10)

    # validation data
    xml_list = train_labels[0:split_point]
    if not os.path.exists(save_path+'/annotations'):
        os.makedirs(save_path+'/annotations')
    if not os.path.exists(save_path+'/train'):
        os.makedirs(save_path+'/train')
    if not os.path.exists(save_path+'/val'):
        os.makedirs(save_path+'/val')

    json_file = save_path + '/annotations/valset.json'
    convert(xml_list, xml_dir, json_file)
    for xml_file in xml_list:
        img_name = xml_file[:-4] + '.tif'
        shutil.copy(os.path.join(patch_path, 'JPEGImages', img_name),
                    os.path.join(save_path, 'val', img_name))

    # train data
    xml_list = train_labels[split_point:]
    json_file = save_path + '/annotations/trainset.json'
    convert(xml_list, xml_dir, json_file)
    for xml_file in xml_list:
        img_name = xml_file[:-4] + '.tif'
        shutil.copy(os.path.join(patch_path, 'JPEGImages', img_name),
                    os.path.join(save_path, 'train', img_name))

    # # test data
    # # xml_list = xml_labels[split_point:3*split_point]
    # json_file = save_path + '/annotations/testset.json'
    # convert(test_labels, xml_dir, json_file)
    # for xml_file in test_labels:
    #     img_name = xml_file[:-4] + '.tif'
    #     shutil.copy(os.path.join(patch_path, 'JPEGImages', img_name),
    #                 os.path.join(save_path, 'test', img_name))