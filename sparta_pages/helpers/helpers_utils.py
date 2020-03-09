"""
Custom Common utilities for the course experience, including course outline.
"""
from completion.models import BlockCompletion

from .helpers_api import get_blocks
from lms.djangoapps.course_blocks.utils import get_student_module_as_dict
from opaque_keys.edx.keys import CourseKey
# from openedx.core.djangoapps.request_cache.middleware import request_cached
from xmodule.modulestore.django import modulestore

import logging
logger = logging.getLogger(__name__)


# @request_cached
def get_course_outline_block_tree(user, course_id):
    """
    Returns the root block of the course outline, with children as blocks.
    """

    def populate_children(block, all_blocks):
        """
        Replace each child id with the full block for the child.

        Given a block, replaces each id in its children array with the full
        representation of that child, which will be looked up by id in the
        passed all_blocks dict. Recursively do the same replacement for children
        of those children.
        """
        try:
            children = block.get('children', [])

            for i in range(len(children)):
                child_id = block['children'][i]
                child_detail = populate_children(all_blocks[child_id], all_blocks)
                block['children'][i] = child_detail

            return block
        except Exception as e:
            raise Exception("populate_children.ERROR: {}".format(str(e)))

    def set_last_accessed_default(block):
        """
        Set default of False for resume_block on all blocks.
        """
        try:
            block['resume_block'] = False
            block['complete'] = False
            for child in block.get('children', []):
                set_last_accessed_default(child)
        except Exception as e:
            raise Exception("set_last_accessed_default.ERROR: {}".format(str(e)))

    def mark_blocks_completed(block, user, course_key):
        """
        Walk course tree, marking block completion.
        Mark 'most recent completed block as 'resume_block'

        """
        try:
            last_completed_child_position = BlockCompletion.get_latest_block_completed(user, course_key)

            if last_completed_child_position:
                # Mutex w/ NOT 'course_block_completions'
                recurse_mark_complete(
                    course_block_completions=BlockCompletion.get_course_completions(user, course_key),
                    latest_completion=last_completed_child_position,
                    block=block
                )
        except Exception as e:
            raise Exception("mark_blocks_completed.ERROR: {}".format(str(e)))

    def recurse_mark_complete(course_block_completions, latest_completion, block):
        """
        Helper function to walk course tree dict,
        marking blocks as 'complete' and 'last_complete'

        If all blocks are complete, mark parent block complete
        mark parent blocks of 'last_complete' as 'last_complete'

        :param course_block_completions: dict[course_completion_object] =  completion_value
        :param latest_completion: course_completion_object
        :param block: course_outline_root_block block object or child block

        :return:
            block: course_outline_root_block block object or child block
        """
        try:
            block_key = block.serializer.instance

            if course_block_completions.get(block_key):
                block['complete'] = True
                if block_key == latest_completion.full_block_key:
                    block['resume_block'] = True

            if block.get('children'):
                for idx in range(len(block['children'])):
                    recurse_mark_complete(
                        course_block_completions,
                        latest_completion,
                        block=block['children'][idx]
                    )
                    if block['children'][idx]['resume_block'] is True:
                        block['resume_block'] = True

                completable_blocks = []
                for child in block['children']:
                    logger.info("recurse_mark_complete.child: {}".format(str(child)))
                    if 'type@discussion' not in child.get('id') and 'type@html' not in child.get('id'):
                        completable_blocks.append(child)
                if len([child['complete'] for child in block['children']
                        if child['complete']]) >= len(completable_blocks):
                    block['complete'] = True
        except Exception as e:
            raise Exception("recurse_mark_complete.ERROR: {}".format(str(e)))

    def mark_last_accessed(user, course_key, block):
        """
        Recursively marks the branch to the last accessed block.
        """
        try:
            block_key = block.serializer.instance
            student_module_dict = get_student_module_as_dict(user, course_key, block_key)

            last_accessed_child_position = student_module_dict.get('position')
            if last_accessed_child_position and block.get('children'):
                block['resume_block'] = True
                if last_accessed_child_position <= len(block['children']):
                    last_accessed_child_block = block['children'][last_accessed_child_position - 1]
                    last_accessed_child_block['resume_block'] = True
                    mark_last_accessed(user, course_key, last_accessed_child_block)
                else:
                    # We should be using an id in place of position for last accessed.
                    # However, while using position, if the child block is no longer accessible
                    # we'll use the last child.
                    block['children'][-1]['resume_block'] = True
        except Exception as e:
            raise Exception("mark_last_accessed.ERROR: {}".format(str(e)))

    course_key = CourseKey.from_string(course_id)
    course_usage_key = modulestore().make_course_usage_key(course_key)

    # Deeper query for course tree traversing/marking complete
    # and last completed block
    block_types_filter = [
        'course',
        'chapter',
        'sequential',
        'vertical',
        'html',
        'problem',
        'video',
        'discussion',
        'drag-and-drop-v2',
        'poll',
        'word_cloud',
        'survey'
    ]
    try:
        all_blocks = get_blocks(
            course_usage_key,
            nav_depth=3,
            requested_fields=[
                'children',
            ],
            block_types_filter=block_types_filter
        )
    except Exception as e:
        raise Exception("get_blocks.ERROR: {}".format(str(e)))

    course_outline_root_block = all_blocks['blocks'].get(all_blocks['root'], None)
    if course_outline_root_block:
        populate_children(course_outline_root_block, all_blocks['blocks'])
        set_last_accessed_default(course_outline_root_block)

        mark_blocks_completed(
            block=course_outline_root_block,
            user=user,
            course_key=course_key
        )
    return course_outline_root_block
