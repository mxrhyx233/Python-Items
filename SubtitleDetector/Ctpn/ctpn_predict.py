import os
os.environ['CUDA_VISIBLE_DEVICES'] = '0'
import numpy as np
import torch
import torch.nn.functional as F
from Ctpn.ctpn_utils import gen_anchor, bbox_transfor_inv, clip_box, filter_bbox,nms, TextProposalConnectorOriented
import Ctpn.config as config
prob_thresh = 0.5
def get_det_boxes(image,model,device):

    image_c = image.copy()
    h, w = image.shape[:2]
    image = image.astype(np.float32) - config.IMAGE_MEAN
    image = torch.from_numpy(image.transpose(2, 0, 1)).unsqueeze(0).float()

    with torch.no_grad():
        image = image.to(device)
        cls, regr = model(image)
        cls_prob = F.softmax(cls, dim=-1).cpu().numpy()
        regr = regr.cpu().numpy()
        anchor = gen_anchor((int(h / 16), int(w / 16)), 16)
        bbox = bbox_transfor_inv(anchor, regr)
        bbox = clip_box(bbox, [h, w])

        fg = np.where(cls_prob[0, :, 1] > prob_thresh)[0]

        select_anchor = bbox[fg, :]
        select_score = cls_prob[0, fg, 1]
        select_anchor = select_anchor.astype(np.int32)

        keep_index = filter_bbox(select_anchor, 16)

        # nms
        select_anchor = select_anchor[keep_index]
        select_score = select_score[keep_index]
        select_score = np.reshape(select_score, (select_score.shape[0], 1))
        nmsbox = np.hstack((select_anchor, select_score))
        keep = nms(nmsbox, 0.3)

        select_anchor = select_anchor[keep]
        select_score = select_score[keep]

        # text line-
        textConn = TextProposalConnectorOriented()
        text = textConn.get_text_lines(select_anchor, select_score, [h, w])

        image_total = []
        for i in text:
            xmin = int(i[0])
            xmax = int(i[2])
            ymin = int(i[1])
            ymax = int(i[5])
            if xmin<=0 or xmax<=0 or ymin<=0 or ymax<=0:
                continue
            img = image_c[ymin:ymax,xmin:xmax]
            image_total.append(img)
        return image_total
