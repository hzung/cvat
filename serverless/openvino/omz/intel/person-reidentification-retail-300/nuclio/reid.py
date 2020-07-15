# Copyright (C) 2018 Intel Corporation
#
# SPDX-License-Identifier: MIT

import math
import numpy

from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import euclidean, cosine

from model_loader import ModelLoader

class ReID:
    def __init__(self, model_xml, model_bin):
        self.model = ModelLoader(model_xml, model_bin)

    def infer(self, image0, boxes0, image1, boxes1, threshold, distance):
        similarity_matrix = self._compute_similarity_matrix(image0,
            boxes0, image1, boxes1, distance)
        row_idx, col_idx = linear_sum_assignment(similarity_matrix)
        results = [-1] * len(boxes0)
        for idx0, idx1 in zip(row_idx, col_idx):
            if similarity_matrix[idx0, idx1] <= threshold:
                results[idx0] = idx1

        return results

    def _match_boxes(self, box0, box1, distance):
        cx0 = (box0["points"][0] + box0["points"][2]) / 2
        cy0 = (box0["points"][1] + box0["points"][3]) / 2
        cx1 = (box1["points"][0] + box1["points"][2]) / 2
        cy1 = (box1["points"][1] + box1["points"][3]) / 2
        is_good_distance = euclidean([cx0, cy0], [cx1, cy1]) <= distance
        is_same_label = box0["label_id"] == box1["label_id"]

        return is_good_distance and is_same_label

    def _match_crops(self, crop0, crop1):
        embedding0 = self.model.infer(crop0)
        embedding1 = self.model.infer(crop1)

        embedding0 = embedding0.reshape(embedding0.size)
        embedding1 = embedding1.reshape(embedding1.size)

        return cosine(embedding0, embedding1)

    def _compute_similarity_matrix(self, image0, boxes0, image1, boxes1,
        distance):
        def _int(number, upper):
            return math.floor(numpy.clip(number, 0, upper - 1))

        DISTANCE_INF = 1000.0

        matrix = numpy.full([len(boxes0), len(boxes1)], DISTANCE_INF, dtype=float)
        for row, box0 in enumerate(boxes0):
            h0, w0 = image0.shape[:2]
            xtl0, xbr0, ytl0, ybr0 = (
                _int(box0["points"][0], w0), _int(box0["points"][2], w0),
                _int(box0["points"][1], h0), _int(box0["points"][3], h0)
            )

            for col, box1 in enumerate(boxes1):
                h1, w1 = image1.shape[:2]
                xtl1, xbr1, ytl1, ybr1 = (
                    _int(box1["points"][0], w1), _int(box1["points"][2], w1),
                    _int(box1["points"][1], h1), _int(box1["points"][3], h1)
                )

                if not self._match_boxes(box0, box1, distance):
                    continue

                crop0 = image0[ytl0:ybr0, xtl0:xbr0]
                crop1 = image1[ytl1:ybr1, xtl1:xbr1]
                matrix[row][col] = self._match_crops(crop0, crop1)

        return matrix