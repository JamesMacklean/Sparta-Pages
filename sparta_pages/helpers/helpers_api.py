"""
API function for retrieving course blocks data
"""

import lms.djangoapps.course_blocks.api as course_blocks_api
from lms.djangoapps.course_blocks.transformers.hidden_content import HiddenContentTransformer
from openedx.core.djangoapps.content.block_structure.transformers import BlockStructureTransformers

from .helpers_serializers import CoursebankBlockSerializer, CoursebankBlockDictSerializer
from lms.djangoapps.course_api.blocks.transformers.blocks_api import BlocksAPITransformer
from lms.djangoapps.course_api.blocks.transformers.block_completion import BlockCompletionTransformer
from lms.djangoapps.course_api.blocks.transformers.milestones import MilestonesAndSpecialExamsTransformer

import logging
logger = logging.getLogger(__name__)


def get_blocks(
        usage_key,
        user=None,
        depth=None,
        nav_depth=None,
        requested_fields=None,
        block_counts=None,
        student_view_data=None,
        return_type='dict',
        block_types_filter=None,
):
    """
    Return a serialized representation of the course blocks.

    Arguments:
        usage_key (UsageKey): Identifies the starting block of interest.
        user (User): Optional user object for whom the blocks are being
            retrieved. If None, blocks are returned regardless of access checks.
        depth (integer or None): Identifies the depth of the tree to return
            starting at the root block.  If None, the entire tree starting at
            the root is returned.
        nav_depth (integer): Optional parameter that indicates how far deep to
            traverse into the block hierarchy before bundling all the
            descendants for navigation.
        requested_fields (list): Optional list of names of additional fields
            to return for each block.  Supported fields are listed in
            transformers.SUPPORTED_FIELDS.
        block_counts (list): Optional list of names of block types for which to
            return an aggregate count of blocks.
        student_view_data (list): Optional list of names of block types for
            which blocks to return their student_view_data.
        return_type (string): Possible values are 'dict' or 'list'. Indicates
            the format for returning the blocks.
        block_types_filter (list): Optional list of block type names used to filter
            the final result of returned blocks.
    """
    # create ordered list of transformers, adding BlocksAPITransformer at end.
    transformers = BlockStructureTransformers()

    transformers += [
        BlocksAPITransformer(
            block_counts,
            student_view_data,
            depth,
            nav_depth
        )
    ]

    transformers += [BlockCompletionTransformer()]

    # transform
    try:
        blocks = course_blocks_api.get_course_blocks(user, usage_key, transformers)
    except Exception as e:
        raise Exception("course_blocks_api.get_course_blocks.ERROR: {}".format(str(e)))

    # filter blocks by types
    try:
        if block_types_filter:
            block_keys_to_remove = []
            for block_key in blocks:
                block_type = blocks.get_xblock_field(block_key, 'category')
                if block_type not in block_types_filter:
                    block_keys_to_remove.append(block_key)
            for block_key in block_keys_to_remove:
                blocks.remove_block(block_key, keep_descendants=True)
    except Exception as e:
        raise Exception("block_types_filter.ERROR: {}".format(str(e)))

    # serialize
    serializer_context = {
        'block_structure': blocks,
        'requested_fields': requested_fields or [],
    }

    try:
        if return_type == 'dict':
            serializer = CoursebankBlockDictSerializer(blocks, context=serializer_context, many=False)
        else:
            serializer = CoursebankBlockSerializer(blocks, context=serializer_context, many=True)
    except Exception as e:
        raise Exception("CoursebankBlockSerializer.ERROR: {}".format(str(e)))

    # return serialized data
    return serializer.data
