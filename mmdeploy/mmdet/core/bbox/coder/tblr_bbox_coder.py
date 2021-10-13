import torch

from mmdeploy.core import FUNCTION_REWRITER


@FUNCTION_REWRITER.register_rewriter(
    func_name='mmdet.core.bbox.coder.tblr_bbox_coder.tblr2bboxes',
    backend='default')
def tblr2bboxes(ctx,
                priors,
                tblr,
                normalizer=4.0,
                normalize_by_wh=True,
                max_shape=None,
                clip_border=True):
    """Rewrite for ONNX exporting of default backend."""
    if not isinstance(normalizer, float):
        normalizer = torch.tensor(normalizer, device=priors.device)
        assert len(normalizer) == 4, 'Normalizer must have length = 4'
    assert priors.size(0) == tblr.size(0)
    if priors.ndim == 3:
        assert priors.size(1) == tblr.size(1)

    loc_decode = tblr * normalizer
    prior_centers = (priors[..., 0:2] + priors[..., 2:4]) / 2
    if normalize_by_wh:
        wh = priors[..., 2:4] - priors[..., 0:2]

        w, h = torch.split(wh, 1, dim=-1)
        # Inplace operation with slice would fail for exporting to ONNX
        th = h * loc_decode[..., :2]  # tb
        tw = w * loc_decode[..., 2:]  # lr
        loc_decode = torch.cat([th, tw], dim=-1)
    top, bottom, left, right = loc_decode.split((1, 1, 1, 1), dim=-1)
    xmin = prior_centers[..., 0].unsqueeze(-1) - left
    xmax = prior_centers[..., 0].unsqueeze(-1) + right
    ymin = prior_centers[..., 1].unsqueeze(-1) - top
    ymax = prior_centers[..., 1].unsqueeze(-1) + bottom

    if clip_border and max_shape is not None:
        from mmdeploy.mmdet.export import clip_bboxes
        xmin, ymin, xmax, ymax = clip_bboxes(xmin, ymin, xmax, ymax, max_shape)
    bboxes = torch.cat([xmin, ymin, xmax, ymax], dim=-1).view(priors.size())

    return bboxes


@FUNCTION_REWRITER.register_rewriter(
    func_name='mmdet.core.bbox.coder.tblr_bbox_coder.tblr2bboxes',
    backend='ncnn')
def tblr2bboxes_ncnn(ctx,
                     priors,
                     tblr,
                     normalizer=4.0,
                     normalize_by_wh=True,
                     max_shape=None,
                     clip_border=True):
    """Rewrite for ONNX exporting of NCNN backend."""
    assert priors.size(0) == tblr.size(0)
    if priors.ndim == 3:
        assert priors.size(1) == tblr.size(1)

    loc_decode = tblr * normalizer
    prior_centers = (priors[..., 0:2] + priors[..., 2:4]) / 2
    if normalize_by_wh:
        w = priors[..., 2:3] - priors[..., 0:1]
        h = priors[..., 3:4] - priors[..., 1:2]
        _h = h.unsqueeze(0).unsqueeze(-1)
        _loc_h = loc_decode[..., 0:2].unsqueeze(0).unsqueeze(-1)
        _w = w.unsqueeze(0).unsqueeze(-1)
        _loc_w = loc_decode[..., 2:4].unsqueeze(0).unsqueeze(-1)
        th = (_h * _loc_h).reshape(1, -1, 2)
        tw = (_w * _loc_w).reshape(1, -1, 2)
        loc_decode = torch.cat([th, tw], dim=2)
    top = loc_decode[..., 0:1]
    bottom = loc_decode[..., 1:2]
    left = loc_decode[..., 2:3]
    right = loc_decode[..., 3:4]
    xmin = prior_centers[..., 0].unsqueeze(-1) - left
    xmax = prior_centers[..., 0].unsqueeze(-1) + right
    ymin = prior_centers[..., 1].unsqueeze(-1) - top
    ymax = prior_centers[..., 1].unsqueeze(-1) + bottom

    if clip_border and max_shape is not None:
        from mmdeploy.mmdet.export import clip_bboxes
        xmin, ymin, xmax, ymax = clip_bboxes(xmin, ymin, xmax, ymax, max_shape)
    bboxes = torch.cat([xmin, ymin, xmax, ymax], dim=-1).view(priors.size())

    return bboxes